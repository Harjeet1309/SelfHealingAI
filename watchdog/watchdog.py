"""
Remediation Engine Watchdog
============================
Fixes the "single point of failure" problem.

The remediation_engine is the service that heals everything else —
but if IT crashes, there is nothing to heal it. This watchdog runs
as a separate lightweight process that monitors the remediation_engine
and alerts / restarts it if it stops responding.

How it works:
    1. Polls the remediation_engine health endpoint every N seconds
    2. If N consecutive polls fail, it restarts the remediation_engine
       container via the Docker SDK
    3. Sends an alert webhook (Slack / generic HTTP) on failure AND recovery
    4. Writes its own log to logs/watchdog.log with rotation
    5. Exposes a tiny health endpoint so the watchdog itself can be monitored
       by an external system (e.g. Docker healthcheck in docker-compose)

Runs as a SEPARATE Docker service — completely independent of the
remediation_engine it monitors.
"""

import os
import time
import json
import datetime
import threading
import requests
import docker
import logging
from logging.handlers import RotatingFileHandler
from http.server import HTTPServer, BaseHTTPRequestHandler


# ─────────────────────────────────────────────
# CONFIG (all overridable via environment vars)
# ─────────────────────────────────────────────

TARGET_CONTAINER    = os.getenv("WATCHDOG_TARGET_CONTAINER", "remediation_engine")
HEALTH_URL          = os.getenv("WATCHDOG_HEALTH_URL",        "http://remediation_engine:5001/health")
POLL_INTERVAL       = int(os.getenv("WATCHDOG_POLL_INTERVAL_SECONDS",      "15"))
FAILURE_THRESHOLD   = int(os.getenv("WATCHDOG_FAILURE_THRESHOLD",          "3"))   # consecutive failures before restart
RESTART_COOLDOWN    = int(os.getenv("WATCHDOG_RESTART_COOLDOWN_SECONDS",   "120"))
HEALTH_TIMEOUT      = int(os.getenv("WATCHDOG_HEALTH_TIMEOUT_SECONDS",     "5"))
DOCKER_SOCKET       = os.getenv("DOCKER_SOCKET_URL",                       "unix:///var/run/docker.sock")
ALERT_WEBHOOK_URL   = os.getenv("WATCHDOG_ALERT_WEBHOOK_URL",              "")    # Slack/Teams/generic
WATCHDOG_PORT       = int(os.getenv("WATCHDOG_PORT",                       "5003"))
LOG_FILE            = os.getenv("WATCHDOG_LOG_FILE",                       "/app/logs/watchdog.log")
LOG_MAX_BYTES       = int(os.getenv("LOG_MAX_BYTES",                       str(5 * 1024 * 1024)))  # 5 MB
LOG_BACKUP_COUNT    = int(os.getenv("LOG_BACKUP_COUNT",                    "3"))   # keep 3 rotated files


# ─────────────────────────────────────────────
# LOGGING (with rotation — fixes unbounded log growth)
# ─────────────────────────────────────────────

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=LOG_MAX_BYTES,
    backupCount=LOG_BACKUP_COUNT,
)
handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[handler, logging.StreamHandler()])
logger = logging.getLogger("watchdog")


# ─────────────────────────────────────────────
# STATE
# ─────────────────────────────────────────────

failure_count       = 0
last_restart_time   = 0.0
is_healthy          = True
total_restarts      = 0
watchdog_start_time = time.time()


# ─────────────────────────────────────────────
# ALERT SENDER
# ─────────────────────────────────────────────

def send_alert(subject: str, body: str, level: str = "warning"):
    """Send alert to configured webhook (Slack-compatible payload)."""
    if not ALERT_WEBHOOK_URL:
        return
    try:
        emoji = {"critical": "🔴", "warning": "🟡", "ok": "🟢"}.get(level, "⚪")
        payload = {
            "text": f"{emoji} *[Watchdog Alert]* {subject}\n{body}"
        }
        requests.post(ALERT_WEBHOOK_URL, json=payload, timeout=5)
        logger.info(f"Alert sent: {subject}")
    except Exception as e:
        logger.warning(f"Failed to send alert: {e}")


# ─────────────────────────────────────────────
# DOCKER INTERACTION
# ─────────────────────────────────────────────

def restart_target():
    """Restart the monitored container via Docker SDK."""
    global last_restart_time, total_restarts
    try:
        client    = docker.DockerClient(base_url=DOCKER_SOCKET)
        container = client.containers.get(TARGET_CONTAINER)
        logger.warning(f"Restarting {TARGET_CONTAINER} ...")
        container.restart()
        last_restart_time = time.time()
        total_restarts   += 1
        logger.info(f"Restart #{total_restarts} of {TARGET_CONTAINER} issued.")
        send_alert(
            subject=f"Watchdog restarted {TARGET_CONTAINER}",
            body=(
                f"The remediation engine failed {FAILURE_THRESHOLD} consecutive "
                f"health checks and was automatically restarted.\n"
                f"Total restarts today: {total_restarts}"
            ),
            level="critical",
        )
        return True
    except Exception as e:
        logger.error(f"Failed to restart {TARGET_CONTAINER}: {e}")
        send_alert(
            subject=f"Watchdog FAILED to restart {TARGET_CONTAINER}",
            body=(
                f"After {FAILURE_THRESHOLD} failed health checks, the watchdog "
                f"attempted a restart but encountered an error: {e}\n"
                f"**Manual intervention required.**"
            ),
            level="critical",
        )
        return False


# ─────────────────────────────────────────────
# HEALTH MONITOR LOOP
# ─────────────────────────────────────────────

def monitor_loop():
    global failure_count, is_healthy

    logger.info(
        f"Watchdog started. Monitoring {TARGET_CONTAINER} at {HEALTH_URL} "
        f"every {POLL_INTERVAL}s (threshold={FAILURE_THRESHOLD} failures)."
    )

    while True:
        try:
            resp = requests.get(HEALTH_URL, timeout=HEALTH_TIMEOUT)
            alive = resp.status_code == 200
        except Exception:
            alive = False

        if alive:
            if not is_healthy:
                logger.info(f"{TARGET_CONTAINER} has recovered. Failure streak cleared.")
                send_alert(
                    subject=f"{TARGET_CONTAINER} has recovered",
                    body="The remediation engine is responding to health checks again.",
                    level="ok",
                )
            failure_count = 0
            is_healthy    = True
        else:
            failure_count += 1
            is_healthy     = False
            logger.warning(
                f"Health check failed for {TARGET_CONTAINER} "
                f"({failure_count}/{FAILURE_THRESHOLD})"
            )

            if failure_count >= FAILURE_THRESHOLD:
                cooldown_elapsed = time.time() - last_restart_time
                if cooldown_elapsed >= RESTART_COOLDOWN:
                    restarted = restart_target()
                    if restarted:
                        failure_count = 0     # Reset after restart attempt
                else:
                    remaining = RESTART_COOLDOWN - cooldown_elapsed
                    logger.info(
                        f"Restart suppressed — cooldown active for {remaining:.0f}s more."
                    )

        time.sleep(POLL_INTERVAL)


# ─────────────────────────────────────────────
# TINY HEALTH ENDPOINT (so watchdog can be monitored)
# ─────────────────────────────────────────────

class WatchdogHealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        uptime = time.time() - watchdog_start_time
        payload = {
            "status":          "ok",
            "target":          TARGET_CONTAINER,
            "target_healthy":  is_healthy,
            "failure_count":   failure_count,
            "failure_threshold": FAILURE_THRESHOLD,
            "total_restarts":  total_restarts,
            "uptime_seconds":  round(uptime),
        }
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # Suppress HTTP server noise


def run_health_server():
    server = HTTPServer(("0.0.0.0", WATCHDOG_PORT), WatchdogHealthHandler)
    logger.info(f"Watchdog health endpoint: http://0.0.0.0:{WATCHDOG_PORT}/")
    server.serve_forever()


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # Start health endpoint in background
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()

    # Main monitor loop (blocking)
    try:
        monitor_loop()
    except KeyboardInterrupt:
        logger.info("Watchdog shutting down.")
