"""
Decision Engine — V3
======================
Improvements over V2:
  - Thread lock on determine_remediation() — prevents race conditions when
    two alerts fire simultaneously (e.g. 500 spike + AI anomaly in same cycle)
  - Log rotation — RotatingFileHandler caps remediation.log at 5 MB
  - Escalation webhook — fires after N consecutive failed restarts so a human
    is notified when the self-healing system cannot recover the service
  - Multi-container routing, health verification (inherited from V2)
"""

import os
import time
import threading
import docker
import datetime
import requests
import logging
from logging.handlers import RotatingFileHandler

logger = logging.getLogger(__name__)


class DecisionEngine:
    def __init__(self, api_url=None, api_reset_url=None, health_url_template=None, token=None):
        self.docker_client = docker.DockerClient(
            base_url=os.getenv("DOCKER_SOCKET_URL", "npipe:////./pipe/docker_engine")
        )
        self.cooldown_period        = int(os.getenv("REMEDIATION_COOLDOWN_SECONDS", "60"))
        self.high_cpu_threshold     = float(os.getenv("HIGH_CPU_THRESHOLD", "70"))
        self.cooldown_log_interval  = int(os.getenv("COOLDOWN_LOG_INTERVAL_SECONDS", "10"))
        self.last_action_time       = 0
        self.last_cooldown_log_time = 0

        # ── Default container (backward compatible) ──────────────────
        self.container_name = os.getenv("TARGET_CONTAINER_NAME", "api_service")

        # ── Multi-container routing map ───────────────────────────────
        self.container_routing = {
            "HTTP_500_SPIKE"      : os.getenv("CONTAINER_ROUTE_HTTP_500_SPIKE",      self.container_name),
            "HTTP_503_SPIKE"      : os.getenv("CONTAINER_ROUTE_HTTP_503_SPIKE",      self.container_name),
            "HTTP_504_SPIKE"      : os.getenv("CONTAINER_ROUTE_HTTP_504_SPIKE",      self.container_name),
            "HTTP_429_SPIKE"      : os.getenv("CONTAINER_ROUTE_HTTP_429_SPIKE",      self.container_name),
            "AI_ANOMALY_DETECTED" : os.getenv("CONTAINER_ROUTE_AI_ANOMALY_DETECTED", self.container_name),
            "STATE_CRITICAL"      : os.getenv("CONTAINER_ROUTE_STATE_CRITICAL",      self.container_name),
        }

        # ── Health verification ───────────────────────────────────────
        self.health_check_enabled   = os.getenv("HEALTH_CHECK_ENABLED", "true").lower() == "true"
        self.health_check_retries   = int(os.getenv("HEALTH_CHECK_RETRIES", "10"))
        self.health_check_delay     = float(os.getenv("HEALTH_CHECK_DELAY_SECONDS", "2.0"))
        self.health_check_timeout   = float(os.getenv("HEALTH_CHECK_TIMEOUT_SECONDS", "3.0"))
        # Map container name → health URL (default pattern)
        self._health_url_template   = health_url_template or os.getenv("HEALTH_URL_TEMPLATE", "http://{container}:8000/health")

        # ── API reporting & fault reset ───────────────────────────────
        self.api_url        = api_url or os.getenv("API_REPORT_URL",  "http://api_service:8000/ai/report")
        self.api_reset_url  = api_reset_url or os.getenv("API_RESET_URL",   "http://api_service:8000/inject/reset?target=all")
        self.reset_retries  = int(os.getenv("AUTO_RESET_RETRIES", "8"))
        self.reset_retry_delay = float(os.getenv("AUTO_RESET_RETRY_DELAY_SECONDS", "1.0"))

        # ── Auth token ──
        final_token = token or os.getenv("INJECT_TOKEN", "").strip()
        self._auth_headers = {"Authorization": f"Bearer {final_token}"} if final_token else {}

        self.log_file = "logs/remediation.log"
        os.makedirs("logs", exist_ok=True)

        # ── Thread safety ─────────────────────────────────────────────
        # Prevents two alerts firing simultaneously from both triggering
        # a container restart — only one thread can remediate at a time.
        self._remediation_lock = threading.Lock()

        # ── Log rotation ──────────────────────────────────────────────
        # Caps remediation.log at 5 MB with 3 rotated backups.
        # Fixes the unbounded log growth reliability gap.
        _log_max_bytes   = int(os.getenv("LOG_MAX_BYTES",    str(5 * 1024 * 1024)))
        _log_backup_count = int(os.getenv("LOG_BACKUP_COUNT", "3"))
        self._file_handler = RotatingFileHandler(
            self.log_file,
            maxBytes=_log_max_bytes,
            backupCount=_log_backup_count,
        )
        self._file_handler.setFormatter(
            logging.Formatter("[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        )

        # ── Escalation webhook ────────────────────────────────────────
        # If self-healing fails N times in a row, alert a human.
        self._escalation_webhook    = os.getenv("ESCALATION_WEBHOOK_URL", "")
        self._escalation_threshold  = int(os.getenv("ESCALATION_THRESHOLD", "3"))
        self._consecutive_failures  = 0

    # ──────────────────────────────────────────────────────────────────
    # LOGGING
    # ──────────────────────────────────────────────────────────────────

    def _log(self, message):
        timestamp = datetime.datetime.utcnow().strftime("%H:%M:%S")
        
        # High-visibility banner for demonstrations
        prefix = ""
        if "DIAGNOSIS" in message:
            prefix = "\n" + "═"*60 + "\n🔎 [DETECTION] "
        elif "ACTION" in message:
            prefix = "\n" + "═"*60 + "\n🛠️ [REMEDIATION] "
        elif "Health VERIFIED" in message:
            prefix = "\n" + "═"*60 + "\n✅ [RECOVERY] "
            
        log_entry = f"{prefix}[{timestamp}] {message}"
        if prefix:
            log_entry += "\n" + "═"*60 + "\n"
            
        print(log_entry)
        # Use RotatingFileHandler to write — caps file at LOG_MAX_BYTES
        record = logging.LogRecord(
            name="remediation", level=logging.INFO,
            pathname="", lineno=0, msg=message, args=(), exc_info=None
        )
        self._file_handler.emit(record)
    
    def _log_with_error_type(self, alert_type: str, message: str):
        """Enhanced logging that includes error type for dashboard visibility."""
        # Map alert types to user-friendly error names
        error_type_map = {
            "HTTP_500_SPIKE": "500 CRASH",
            "HTTP_503_SPIKE": "503 DEADLOCK/OVERLOAD",
            "HTTP_504_SPIKE": "504 TIMEOUT",
            "HTTP_429_SPIKE": "429 BOT ATTACK",
            "AI_ANOMALY_DETECTED": "AI ANOMALY",
            "STATE_CRITICAL": "CRITICAL STATE"
        }
        error_name = error_type_map.get(alert_type, alert_type)
        
        # Create user-friendly message for dashboard
        if "DIAGNOSIS" in message:
            dashboard_msg = f"🔴 ERROR DETECTED: {error_name} | {message.replace('DIAGNOSIS:', '').strip()}"
        elif "ACTION" in message:
            dashboard_msg = f"⚡ REMEDIATION: {error_name} | {message.replace('ACTION:', '').strip()}"
        elif "Health VERIFIED" in message:
            dashboard_msg = f"✅ RECOVERY: {error_name} | Service restored successfully"
        else:
            dashboard_msg = f"[{error_name}] {message}"
            
        self._log(dashboard_msg)

    def _escalate(self, subject: str, body: str):
        """Send escalation alert to webhook (Slack-compatible) when self-healing fails."""
        if not self._escalation_webhook:
            return
        try:
            requests.post(
                self._escalation_webhook,
                json={"text": f"🔴 *[Self-Healing Escalation]* {subject}\n{body}"},
                timeout=3,
            )
            self._log(f"ESCALATION SENT: {subject}")
        except Exception as e:
            self._log(f"ESCALATION FAILED to send: {e}")

    def _report(self, error_key, action):
        try:
            requests.post(
                self.api_url,
                json={"error_key": error_key, "action": action},
                headers=self._auth_headers,
                timeout=1,
            )
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────────────
    # CONTAINER STATS
    # ──────────────────────────────────────────────────────────────────

    def _get_container_stats(self, container_name: str = None):
        name = container_name or self.container_name
        try:
            container    = self.docker_client.containers.get(name)
            stats        = container.stats(stream=False)
            cpu_stats    = stats.get("cpu_stats", {})
            precpu_stats = stats.get("precpu_stats", {})

            cpu_total    = cpu_stats.get("cpu_usage", {}).get("total_usage", 0)
            precpu_total = precpu_stats.get("cpu_usage", {}).get("total_usage", 0)
            cpu_delta    = cpu_total - precpu_total

            system_total    = cpu_stats.get("system_cpu_usage", 0)
            pre_system_total = precpu_stats.get("system_cpu_usage", 0)
            system_delta     = system_total - pre_system_total

            online_cpus = cpu_stats.get("online_cpus")
            if not online_cpus:
                percpu      = cpu_stats.get("cpu_usage", {}).get("percpu_usage") or []
                online_cpus = len(percpu) if percpu else 1

            if cpu_delta <= 0 or system_delta <= 0:
                cpu_percent = 0.0
            else:
                raw         = (cpu_delta / system_delta) * online_cpus * 100.0
                cpu_percent = max(0.0, min(raw, online_cpus * 100.0))

            return {"cpu_percent": cpu_percent}
        except Exception:
            return {"cpu_percent": 0.0}

    # ──────────────────────────────────────────────────────────────────
    # HEALTH VERIFICATION (NEW)
    # ──────────────────────────────────────────────────────────────────

    def _verify_health(self, container_name: str) -> bool:
        """
        Poll the container's /health endpoint after restart.
        Returns True if health check passes within the retry window.
        This closes the feedback loop — we KNOW the restart worked.
        
        Uses bypass_faults=true to check if container is actually healthy,
        not just if faults are cleared.
        """
        if not self.health_check_enabled:
            return True  # Assume success if checks are disabled

        health_url = self._health_url_template.format(container=container_name)
        # Add bypass parameter to check actual container health, not fault state
        health_url_with_bypass = f"{health_url}?bypass_faults=true"
        self._log(f"POST-REMEDIATION: Verifying health at {health_url_with_bypass} ...")

        for attempt in range(1, self.health_check_retries + 1):
            time.sleep(self.health_check_delay)
            try:
                resp = requests.get(health_url_with_bypass, timeout=self.health_check_timeout)
                if resp.status_code == 200:
                    self._log(
                        f"POST-REMEDIATION: Health VERIFIED on attempt {attempt}. "
                        f"Recovery confirmed."
                    )
                    return True
                else:
                    self._log(
                        f"POST-REMEDIATION: Health check attempt {attempt} → "
                        f"HTTP {resp.status_code}. Retrying..."
                    )
            except requests.exceptions.ConnectionError as e:
                self._log(
                    f"POST-REMEDIATION: Health check attempt {attempt} → "
                    f"Connection refused (container still starting). Retrying..."
                )
            except Exception as e:
                self._log(
                    f"POST-REMEDIATION: Health check attempt {attempt} failed: {e}. Retrying..."
                )

        self._log(
            f"WARNING: Health could NOT be verified after {self.health_check_retries} attempts. "
            f"Restart may have failed or container is slow to come up."
        )
        return False

    # ──────────────────────────────────────────────────────────────────
    # COOLDOWN
    # ──────────────────────────────────────────────────────────────────

    def _is_cooldown_active(self):
        return (time.time() - self.last_action_time) < self.cooldown_period

    def _log_cooldown_skip(self, alert_type):
        now = time.time()
        if (now - self.last_cooldown_log_time) < self.cooldown_log_interval:
            return
        remaining = max(self.cooldown_period - (now - self.last_action_time), 0.0)
        self._log(f"Skipping restart for {alert_type}; cooldown active for {remaining:.1f}s.")
        self.last_cooldown_log_time = now

    # ──────────────────────────────────────────────────────────────────
    # FAULT RESET
    # ──────────────────────────────────────────────────────────────────

    def _auto_reset_faults(self):
        for attempt in range(1, self.reset_retries + 1):
            try:
                response = requests.post(
                    self.api_reset_url,
                    headers=self._auth_headers,
                    timeout=2,
                )
                if response.status_code < 300:
                    self._log("POST-REMEDIATION: Injected faults auto-reset completed.")
                    return
                self._log(
                    f"POST-REMEDIATION: reset attempt {attempt} returned {response.status_code}."
                )
            except Exception:
                pass
            time.sleep(self.reset_retry_delay)

        self._log("WARNING: Post-remediation auto-reset did not complete after retries.")

    # ──────────────────────────────────────────────────────────────────
    # RESTART WITH VERIFICATION
    # ──────────────────────────────────────────────────────────────────

    def _restart_with_cooldown(self, reason, error_key, alert_type):
        if self._is_cooldown_active():
            self._log_cooldown_skip(alert_type)
            return "COOLDOWN_ACTIVE"

        # Resolve which container handles this alert type
        target_container = self.container_routing.get(alert_type, self.container_name)
        
        # Log the remediation action BEFORE executing it
        self._log_with_error_type(alert_type, f"[REMEDIATION] ACTION: Restarting {target_container} container | Reason: {reason}")

        result = self._execute_restart(reason, container_name=target_container)
        if result == "RESTART_SUCCESS":
            # Wait longer for container to fully restart and initialize
            self._log("POST-REMEDIATION: Waiting for container to stabilize...")
            time.sleep(8)  # Increased from 3 to 8 seconds
            
            # Verify health WITHOUT clearing faults first (using bypass_faults=true)
            verified = self._verify_health(target_container)
            if verified:
                # Only NOW clear the faults after confirming container is healthy
                self._auto_reset_faults()
                
                self._consecutive_failures = 0   # reset escalation counter on success
                self._report(error_key, "RESTART_SUCCESS_VERIFIED")
                # Log recovery with error type context
                self._log_with_error_type(alert_type, "[RECOVERY] Health VERIFIED - System recovered successfully")
                return "RESTART_SUCCESS_VERIFIED"
            else:
                # Health check failed - DO NOT clear faults, they're still real
                self._consecutive_failures += 1
                self._report(error_key, "RESTART_SUCCESS_UNVERIFIED")
                if self._consecutive_failures >= self._escalation_threshold:
                    self._escalate(
                        subject=f"{target_container} cannot be verified healthy after restart",
                        body=(
                            f"Alert: {alert_type}\n"
                            f"Reason: {reason}\n"
                            f"Consecutive unverified recoveries: {self._consecutive_failures}\n"
                            f"Manual intervention required."
                        ),
                    )
                return "RESTART_SUCCESS_UNVERIFIED"

        # Restart itself failed
        self._consecutive_failures += 1
        self._report(error_key, result)
        if self._consecutive_failures >= self._escalation_threshold:
            self._escalate(
                subject=f"CRITICAL: Restart of {target_container} failed {self._consecutive_failures} times",
                body=(
                    f"Alert: {alert_type}\n"
                    f"Error: restart command returned '{result}'\n"
                    f"Self-healing is NOT functioning. Immediate attention required."
                ),
            )
        return result

    # ──────────────────────────────────────────────────────────────────
    # REMEDIATION DECISION
    # ──────────────────────────────────────────────────────────────────

    def determine_remediation(self, alert_type, metadata=None):
        # Acquire lock — if another alert is already being remediated,
        # this call blocks rather than triggering a second simultaneous restart.
        if not self._remediation_lock.acquire(blocking=False):
            self._log(f"LOCK: Remediation already in progress — skipping {alert_type}")
            return "REMEDIATION_IN_PROGRESS"
        try:
            return self._determine_remediation_inner(alert_type, metadata)
        finally:
            self._remediation_lock.release()

    def _determine_remediation_inner(self, alert_type, metadata=None):
        if self._is_cooldown_active():
            self._log_cooldown_skip(alert_type)
            return "COOLDOWN_ACTIVE"

        target = self.container_routing.get(alert_type, self.container_name)
        stats  = self._get_container_stats(container_name=target)
        cpu    = stats["cpu_percent"]
        self._log_with_error_type(alert_type, f"Analyzing Alert | Target: {target} | CPU: {cpu:.2f}%")

        if alert_type == "HTTP_500_SPIKE":
            self._log_with_error_type(alert_type, "[DETECTION] Localized application crash detected via Rule-Engine.")
            return self._restart_with_cooldown(
                reason="App Crash", error_key="500_CRASH", alert_type=alert_type
            )

        if alert_type == "STATE_CRITICAL":
            self._log_with_error_type(alert_type, "[DETECTION] Direct critical state failure. FORCE RESTART.")
            return self._restart_with_cooldown(
                reason="Direct State Failure", error_key="CRITICAL_STATE", alert_type=alert_type
            )

        if alert_type == "AI_ANOMALY_DETECTED":
            if cpu > self.high_cpu_threshold:
                self._log_with_error_type(alert_type, "[DETECTION] AI Anomaly + High CPU. Classifying as Overload. Suppressing.")
                self._report("503_OVERLOAD", "SUPPRESS_RESTART_FOR_SCALING")
                return "SUPPRESS_RESTART_FOR_SCALING"
            else:
                self._log_with_error_type(alert_type, "[DETECTION] AI Behavioral Anomaly (Low CPU). Classifying as Potential Deadlock.")
                return self._restart_with_cooldown(
                    reason="App Deadlock", error_key="503_DEADLOCK", alert_type=alert_type
                )

        if alert_type == "HTTP_503_SPIKE":
            if cpu > self.high_cpu_threshold:
                self._log_with_error_type(alert_type, "[DETECTION] Overload condition. Suppressing restart.")
                self._report("503_OVERLOAD", "SUPPRESS_RESTART_FOR_SCALING")
                return "SUPPRESS_RESTART_FOR_SCALING"
            else:
                self._log_with_error_type(alert_type, "[DETECTION] Deadlock recognized. Restarting.")
                return self._restart_with_cooldown(
                    reason="App Deadlock", error_key="503_DEADLOCK", alert_type=alert_type
                )

        if alert_type == "HTTP_504_SPIKE":
            self._log_with_error_type(alert_type, "[DETECTION] Gateway Timeout. Clearing connections.")
            return self._restart_with_cooldown(
                reason="504 Timeout Cleanup", error_key="504_TIMEOUT", alert_type=alert_type
            )

        if alert_type == "HTTP_429_SPIKE":
            self._log_with_error_type(alert_type, "[DETECTION] Bot Attack. Logging only.")
            self._report("429_SECURITY", "LOG_ONLY")
            return "LOG_ONLY"

        self._log(f"WARNING: No remediation mapped for alert type '{alert_type}'.")
        return "NO_ACTION_MAPPED"

    # ──────────────────────────────────────────────────────────────────
    # RESTART EXECUTION
    # ──────────────────────────────────────────────────────────────────

    def _execute_restart(self, reason, container_name: str = None):
        name = container_name or self.container_name
        try:
            self._log(f"ACTION: Restarting {name}. REASON: {reason}")
            container = self.docker_client.containers.get(name)
            container.restart()
            self.last_action_time = time.time()
            return "RESTART_SUCCESS"
        except Exception as e:
            self._log(f"ERROR: Restart of {name} failed: {e}")
            return "RESTART_FAILED"
