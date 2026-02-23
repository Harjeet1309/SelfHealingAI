from fastapi import FastAPI, Request
import uvicorn
import datetime
import os
import subprocess
import time
import requests
from typing import Dict

app = FastAPI()

# =============================
# Configuration
# =============================

LOG_FILE = "logs/remediation.log"
COOLDOWN_SECONDS = 60
MAX_RETRIES = 3
HEALTH_URL = "http://api_service:8000/health"

# Track restart attempts per alert
alert_state: Dict[str, int] = {}
last_restart_time = 0


# =============================
# Logging
# =============================

def log_action(message: str, level: str = "INFO"):
    timestamp = datetime.datetime.utcnow().isoformat()
    log_entry = f"[{timestamp}] [{level}] {message}"
    os.makedirs("logs", exist_ok=True)

    with open(LOG_FILE, "a") as f:
        f.write(log_entry + "\n")

    print(log_entry)


# =============================
# Infrastructure Utilities
# =============================

def restart_container(container_name: str):
    subprocess.run(["docker", "restart", container_name], check=True)


def verify_health() -> bool:
    try:
        response = requests.get(HEALTH_URL, timeout=5)
        return response.status_code == 200
    except Exception:
        return False


# =============================
# Escalation Logic
# =============================

def escalate(alert_name: str):
    log_action(
        f"ESCALATION TRIGGERED for {alert_name}. Manual intervention required.",
        level="CRITICAL"
    )


# =============================
# Core Remediation Engine
# =============================

def controlled_restart(alert_name: str, container_name: str):
    global last_restart_time

    current_time = time.time()

    # Cooldown protection
    if current_time - last_restart_time < COOLDOWN_SECONDS:
        log_action("Restart skipped due to cooldown protection.")
        return

    retry_count = 0
    success = False

    log_action(f"{alert_name} detected. Starting controlled restart sequence.")

    while retry_count < MAX_RETRIES:
        try:
            retry_count += 1
            log_action(f"Restart attempt {retry_count} of {MAX_RETRIES}")

            restart_container(container_name)
            last_restart_time = time.time()

            time.sleep(5)

            if verify_health():
                log_action("Service recovered successfully after restart.")
                success = True
                alert_state[alert_name] = 0
                break
            else:
                log_action("Health check failed after restart.", level="WARNING")

        except Exception as e:
            log_action(f"Restart attempt failed: {str(e)}", level="ERROR")

    if not success:
        alert_state[alert_name] = alert_state.get(alert_name, 0) + 1
        log_action(
            f"Max restart attempts exceeded for {alert_name}.",
            level="ERROR"
        )

        if alert_state[alert_name] >= 2:
            escalate(alert_name)


# =============================
# Alert Handlers
# =============================

def remedy_high_error_rate():
    controlled_restart("HighErrorRate", "api_service")


def remedy_service_down():
    controlled_restart("APIServiceDown", "api_service")


def remedy_high_latency():
    log_action("HighLatency detected. Suggesting performance scaling.", level="WARNING")


def remedy_high_active_requests():
    log_action("HighActiveRequests detected. Suggesting horizontal scaling.", level="WARNING")


# =============================
# Webhook Endpoint
# =============================

@app.post("/webhook")
async def receive_alert(request: Request):
    data = await request.json()
    alerts = data.get("alerts", [])

    for alert in alerts:
        alert_name = alert.get("labels", {}).get("alertname")
        status = alert.get("status")

        log_action(f"Received alert: {alert_name} | Status: {status}")

        if status != "firing":
            log_action(f"Alert {alert_name} resolved.")
            alert_state[alert_name] = 0
            continue

        if alert_name == "HighErrorRate":
            remedy_high_error_rate()

        elif alert_name == "APIServiceDown":
            remedy_service_down()

        elif alert_name == "HighLatency":
            remedy_high_latency()

        elif alert_name == "HighActiveRequests":
            remedy_high_active_requests()

    return {"status": "received"}


# =============================
# Entry Point
# =============================

if __name__ == "__main__":
    uvicorn.run(
        "remediation_engine.webhook_server:app",
        host="0.0.0.0",
        port=5001,
        reload=True
    )