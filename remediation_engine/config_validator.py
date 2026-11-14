"""
Config Validator — Startup Gate
=================================
Validates all environment variables at process startup.
If a required variable is missing or has an invalid value, the service
prints a clear error and exits immediately (rather than failing later
with a cryptic runtime error).

Design
------
- REQUIRED_VARS: must be present and non-empty
- TYPED_VARS:    must be parseable as the given Python type
- RANGE_VARS:    numeric vars that must fall within [min, max]
- WARN_VARS:     should be set in production; warnings (not fatal) if missing

Usage
-----
Call validate() at the very top of your entry point:

    from config_validator import validate
    validate()          # exits with code 1 on any hard failure
"""

import os
import sys
import logging

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# RULES
# ─────────────────────────────────────────────────────────────

# (env_var_name, description)
REQUIRED_VARS = [
    ("PROMETHEUS_URL",      "Prometheus base URL (e.g. http://prometheus:9090)"),
    ("API_REPORT_URL",      "URL to POST AI actions to (e.g. http://api_service:8000/ai/report)"),
    ("API_RESET_URL",       "URL to POST fault resets to"),
    ("TARGET_CONTAINER_NAME", "Docker container name the remediation engine manages"),
    ("DOCKER_SOCKET_URL",   "Docker socket URL (e.g. unix:///var/run/docker.sock)"),
]

# (env_var_name, python_type, description)
TYPED_VARS = [
    ("REMEDIATION_COOLDOWN_SECONDS",        int,   "Cooldown between restarts in seconds"),
    ("HIGH_CPU_THRESHOLD",                  float, "CPU % above which overload is assumed (0-100)"),
    ("HEALTH_CHECK_RETRIES",                int,   "Number of health check retries after restart"),
    ("HEALTH_CHECK_DELAY_SECONDS",          float, "Seconds to wait between health check retries"),
    ("AI_WARMUP_SECONDS",                   int,   "Seconds to wait before AI inference fires"),
    ("AI_THRESHOLD_MULTIPLIER",             float, "Multiplier on static anomaly threshold"),
    ("AI_DYNAMIC_WINDOW_SAMPLES",           int,   "Rolling window size for dynamic threshold"),
    ("ONLINE_FINE_TUNE_TRIGGER",            int,   "Clean samples required before a fine-tune pass"),
    ("RULE_LOOKBACK_SECONDS",               int,   "Look-back window for rule-based spike checks"),
    ("ESCALATION_THRESHOLD",                int,   "Consecutive failures before escalation webhook fires"),
    ("WATCHDOG_POLL_INTERVAL_SECONDS",      int,   "Watchdog polling interval in seconds"),
    ("WATCHDOG_FAILURE_THRESHOLD",          int,   "Consecutive watchdog failures before restart"),
    ("WATCHDOG_RESTART_COOLDOWN_SECONDS",   int,   "Watchdog restart cooldown in seconds"),
]

# (env_var_name, python_type, min_value, max_value)
RANGE_VARS = [
    ("REMEDIATION_COOLDOWN_SECONDS",    int,   5,    3600),
    ("HIGH_CPU_THRESHOLD",              float, 1.0,  100.0),
    ("AI_THRESHOLD_MULTIPLIER",         float, 0.1,  20.0),
    ("ONLINE_FINE_TUNE_TRIGGER",        int,   10,   100_000),
    ("WATCHDOG_POLL_INTERVAL_SECONDS",  int,   5,    600),
    ("WATCHDOG_FAILURE_THRESHOLD",      int,   1,    20),
]

# (env_var_name, warning_message)
WARN_VARS = [
    ("INJECT_TOKEN",              "INJECT_TOKEN is not set — /inject/* and /ai/report endpoints are UNPROTECTED"),
    ("ESCALATION_WEBHOOK_URL",    "ESCALATION_WEBHOOK_URL is not set — no human alert will fire on repeated failures"),
    ("WATCHDOG_ALERT_WEBHOOK_URL","WATCHDOG_ALERT_WEBHOOK_URL is not set — watchdog alerts will be silent"),
]


# ─────────────────────────────────────────────────────────────
# VALIDATOR
# ─────────────────────────────────────────────────────────────

def validate(exit_on_failure: bool = True) -> bool:
    """
    Run all config checks. Returns True if everything is valid.
    If exit_on_failure is True (default), calls sys.exit(1) on any hard error.
    """
    errors   = []
    warnings = []

    # 1. Required vars
    for var, desc in REQUIRED_VARS:
        val = os.getenv(var, "").strip()
        if not val:
            errors.append(f"  MISSING: {var} — {desc}")

    # 2. Type checks
    for var, typ, desc in TYPED_VARS:
        raw = os.getenv(var)
        if raw is None:
            continue  # Not present — not a type error (may have default)
        try:
            typ(raw)
        except (ValueError, TypeError):
            errors.append(
                f"  INVALID TYPE: {var}={raw!r} — expected {typ.__name__}. {desc}"
            )

    # 3. Range checks
    for var, typ, lo, hi in RANGE_VARS:
        raw = os.getenv(var)
        if raw is None:
            continue
        try:
            val = typ(raw)
            if not (lo <= val <= hi):
                errors.append(
                    f"  OUT OF RANGE: {var}={val} — must be between {lo} and {hi}"
                )
        except (ValueError, TypeError):
            pass  # Already caught by type check above

    # 4. Warnings
    for var, msg in WARN_VARS:
        raw = os.getenv(var, "").strip()
        if not raw:
            warnings.append(f"  [WARN] {msg}")

    # ── Report ──────────────────────────────────────────────────────────
    if warnings:
        logger.warning("[ConfigValidator] ⚠️  Configuration warnings:")
        for w in warnings:
            logger.warning(w)

    if errors:
        logger.critical("[ConfigValidator] ❌  FATAL: Configuration errors found — refusing to start:")
        for e in errors:
            logger.critical(e)
        logger.critical("[ConfigValidator] Fix the above env vars and restart the service.")
        if exit_on_failure:
            sys.exit(1)
        return False

    logger.info(f"[ConfigValidator] ✅  All {len(REQUIRED_VARS)} required vars present, "
                f"{len(TYPED_VARS)} type checks passed, {len(RANGE_VARS)} range checks passed.")
    return True
