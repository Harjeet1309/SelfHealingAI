"""
Chaos Controller — Professional Fault Injection Engine
=======================================================
Injects failures at the INFRASTRUCTURE level — not inside application code.
The target application (api_service) knows nothing about these faults.

Supported Fault Methods:
    container_kill       → SIGKILL / SIGTERM the container process (real crash)
    resource_constraint  → Docker CPU/memory limits (real resource pressure)
    network_disconnect   → Remove container from Docker network (real partition)
    container_pause      → Pause container execution (real freeze/deadlock sim)
    toxiproxy            → Network-level latency/jitter/packet-loss via Toxiproxy

Architecture:
    - Reads scenario definitions from scenarios/*.yml
    - REST API for triggering, listing, and monitoring scenarios
    - Each scenario runs in a background thread with auto-cleanup on timeout
    - Full audit log of every chaos event with result verification

Usage:
    POST /chaos/run/{scenario_name}          → Start a scenario
    GET  /chaos/scenarios                    → List all available scenarios
    GET  /chaos/status                       → Current running scenarios
    POST /chaos/abort                        → Emergency stop all active scenarios
    GET  /chaos/history                      → Audit log of past runs
"""

import os
import time
import json
import signal
import threading
import datetime
import traceback
from pathlib import Path
from typing import Dict, Optional, List

import docker
import requests
import yaml
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

SCENARIOS_DIR    = Path(__file__).parent / "scenarios"
DOCKER_SOCKET    = os.getenv("DOCKER_SOCKET_URL", "unix:///var/run/docker.sock")
TOXIPROXY_URL    = os.getenv("TOXIPROXY_URL", "http://toxiproxy:8474")
LOG_FILE         = "/app/logs/chaos.log"

os.makedirs("/app/logs", exist_ok=True)

app = FastAPI(title="Chaos Controller", version="1.0.0")
docker_client = docker.DockerClient(base_url=DOCKER_SOCKET)


# ─────────────────────────────────────────────
# STATE
# ─────────────────────────────────────────────

active_scenarios: Dict[str, dict] = {}   # scenario_name → run metadata
history: List[dict]                = []   # audit log


# ─────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────

class ScenarioRunResult(BaseModel):
    scenario:   str
    started_at: str
    method:     str
    status:     str
    message:    str


# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────

def _log(msg: str, level: str = "INFO"):
    ts    = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{ts}] [{level}] {msg}"
    print(entry)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(entry + "\n")
    except Exception:
        pass


# ─────────────────────────────────────────────
# SCENARIO LOADER
# ─────────────────────────────────────────────

def load_scenarios() -> Dict[str, dict]:
    scenarios = {}
    for path in SCENARIOS_DIR.glob("*.yml"):
        try:
            with open(path) as f:
                data = yaml.safe_load(f)
            scenarios[data["name"]] = data
        except Exception as e:
            _log(f"Failed to load scenario {path.name}: {e}", "WARN")
    return scenarios


# ─────────────────────────────────────────────
# FAULT INJECTORS
# ─────────────────────────────────────────────

class FaultInjector:
    """Implements each fault method at the infrastructure level."""

    def __init__(self, scenario: dict):
        self.s       = scenario
        self.target  = scenario["target_container"]
        self.method  = scenario["method"]
        self.duration = scenario.get("duration_seconds", 60)
        self._stop   = threading.Event()

    def run(self):
        """Dispatch to the appropriate fault method."""
        _log(f"[CHAOS] Starting scenario '{self.s['name']}' via method='{self.method}' "
             f"on container='{self.target}' for {self.duration}s")

        try:
            if self.method == "container_kill":
                self._container_kill()
            elif self.method == "resource_constraint":
                self._resource_constraint()
            elif self.method == "network_disconnect":
                self._network_disconnect()
            elif self.method == "container_pause":
                self._container_pause()
            elif self.method == "toxiproxy":
                self._toxiproxy_inject()
            else:
                _log(f"[CHAOS] Unknown method: {self.method}", "ERROR")
        except Exception as e:
            _log(f"[CHAOS] Error in scenario '{self.s['name']}': {e}", "ERROR")
            _log(traceback.format_exc(), "ERROR")
        finally:
            active_scenarios.pop(self.s["name"], None)
            _log(f"[CHAOS] Scenario '{self.s['name']}' completed.")

    def abort(self):
        self._stop.set()

    # ── Method: Container Kill ─────────────────────────────────────────
    def _container_kill(self):
        sig = self.s.get("signal", "SIGKILL")
        try:
            container = docker_client.containers.get(self.target)
            _log(f"[CHAOS] Sending {sig} to {self.target}")
            container.kill(signal=sig)
            _log(f"[CHAOS] {sig} sent. Container will auto-restart via Docker restart policy.")
        except Exception as e:
            _log(f"[CHAOS] Kill failed: {e}", "ERROR")

    # ── Method: Resource Constraint ────────────────────────────────────
    def _resource_constraint(self):
        resource = self.s.get("resource", {})
        cpus        = resource.get("cpus")
        memory      = resource.get("memory")
        restore_cpus   = resource.get("restore_cpus")
        restore_memory = resource.get("restore_memory")

        try:
            container = docker_client.containers.get(self.target)

            # Apply constraints
            update_kwargs = {}
            if cpus:
                # Docker SDK uses nano_cpus (1 CPU = 1e9 nano_cpus)
                update_kwargs["nano_cpus"] = int(float(cpus) * 1e9)
            if memory:
                # Convert string like "80m" to bytes
                update_kwargs["mem_limit"] = self._parse_memory(memory)

            if update_kwargs:
                container.update(**update_kwargs)
                _log(f"[CHAOS] Applied resource constraints to {self.target}: {update_kwargs}")

            # Hold the constraint for duration_seconds
            self._stop.wait(timeout=self.duration)

        finally:
            # Restore original constraints
            self._restore_resources(restore_cpus, restore_memory)

    def _restore_resources(self, restore_cpus, restore_memory):
        try:
            container = docker_client.containers.get(self.target)
            restore_kwargs = {}
            if restore_cpus:
                restore_kwargs["nano_cpus"] = int(float(restore_cpus) * 1e9)
            if restore_memory:
                restore_kwargs["mem_limit"] = self._parse_memory(restore_memory)
                restore_kwargs["memswap_limit"] = self._parse_memory(restore_memory)
            if restore_kwargs:
                container.update(**restore_kwargs)
                _log(f"[CHAOS] Restored resources on {self.target}: {restore_kwargs}")
        except Exception as e:
            _log(f"[CHAOS] Resource restore failed: {e}", "WARN")

    @staticmethod
    def _parse_memory(mem_str: str) -> int:
        """Parse memory string like '80m' or '1g' to bytes."""
        mem_str = str(mem_str).strip().lower()
        if mem_str.endswith("g"):
            return int(float(mem_str[:-1]) * 1024 ** 3)
        if mem_str.endswith("m"):
            return int(float(mem_str[:-1]) * 1024 ** 2)
        if mem_str.endswith("k"):
            return int(float(mem_str[:-1]) * 1024)
        return int(mem_str)

    # ── Method: Network Disconnect ─────────────────────────────────────
    def _network_disconnect(self):
        network_name = self.s.get("network", "selfheal_net")
        try:
            network   = docker_client.networks.get(network_name)
            container = docker_client.containers.get(self.target)

            _log(f"[CHAOS] Disconnecting {self.target} from network {network_name}")
            network.disconnect(container, force=True)

            self._stop.wait(timeout=self.duration)

        finally:
            try:
                network   = docker_client.networks.get(network_name)
                container = docker_client.containers.get(self.target)
                network.connect(container)
                _log(f"[CHAOS] Reconnected {self.target} to network {network_name}")
            except Exception as e:
                _log(f"[CHAOS] Network reconnect failed: {e}", "ERROR")

    # ── Method: Container Pause ────────────────────────────────────────
    def _container_pause(self):
        try:
            container = docker_client.containers.get(self.target)
            _log(f"[CHAOS] Pausing {self.target} (simulates deadlock/freeze)")
            container.pause()

            self._stop.wait(timeout=self.duration)

        finally:
            try:
                container = docker_client.containers.get(self.target)
                container.unpause()
                _log(f"[CHAOS] Unpaused {self.target}")
            except Exception as e:
                _log(f"[CHAOS] Unpause failed: {e}", "ERROR")

    # ── Method: Toxiproxy Network Fault ───────────────────────────────
    def _toxiproxy_inject(self):
        cfg         = self.s.get("toxiproxy", {})
        proxy_name  = cfg.get("proxy_name", f"{self.target}_proxy")
        upstream    = cfg.get("upstream", f"{self.target}:8000")
        listen      = cfg.get("listen", "0.0.0.0:8001")
        toxic_cfg   = cfg.get("toxic", {})

        try:
            # Create Toxiproxy proxy if not exists
            proxy_url = f"{TOXIPROXY_URL}/proxies/{proxy_name}"
            resp = requests.get(proxy_url, timeout=3)

            if resp.status_code == 404:
                requests.post(
                    f"{TOXIPROXY_URL}/proxies",
                    json={"name": proxy_name, "listen": listen, "upstream": upstream},
                    timeout=3,
                )
                _log(f"[CHAOS] Created Toxiproxy proxy: {proxy_name}")

            # Add toxic
            toxic_type = toxic_cfg.get("type", "latency")
            toxic_payload = {
                "type": toxic_type,
                "toxicity": 1.0,
                "attributes": {
                    k: v for k, v in toxic_cfg.items() if k != "type"
                },
            }
            requests.post(
                f"{TOXIPROXY_URL}/proxies/{proxy_name}/toxics",
                json=toxic_payload,
                timeout=3,
            )
            _log(f"[CHAOS] Injected {toxic_type} toxic: {toxic_payload}")

            self._stop.wait(timeout=self.duration)

        finally:
            try:
                # Remove all toxics from the proxy
                requests.delete(
                    f"{TOXIPROXY_URL}/proxies/{proxy_name}/toxics/{toxic_type}_{proxy_name}",
                    timeout=3,
                )
                _log(f"[CHAOS] Removed Toxiproxy toxic from {proxy_name}")
            except Exception as e:
                _log(f"[CHAOS] Toxiproxy cleanup failed (non-fatal): {e}", "WARN")


# ─────────────────────────────────────────────
# API ENDPOINTS
# ─────────────────────────────────────────────

@app.get("/chaos/scenarios")
def list_scenarios():
    """List all available chaos scenarios with their metadata."""
    scenarios = load_scenarios()
    return {
        "available_scenarios": list(scenarios.keys()),
        "details": {
            name: {
                "description":      s.get("description", "").strip(),
                "method":           s.get("method"),
                "target_container": s.get("target_container"),
                "duration_seconds": s.get("duration_seconds"),
                "expected_alert":   s.get("expected_alert"),
                "expected_action":  s.get("expected_action"),
                "severity":         s.get("severity"),
                "tags":             s.get("tags", []),
            }
            for name, s in scenarios.items()
        },
    }


@app.post("/chaos/run/{scenario_name}", response_model=ScenarioRunResult)
def run_scenario(scenario_name: str):
    """Trigger a chaos scenario by name."""
    scenarios = load_scenarios()

    if scenario_name not in scenarios:
        raise HTTPException(
            status_code=404,
            detail=f"Scenario '{scenario_name}' not found. "
                   f"Available: {list(scenarios.keys())}",
        )

    if scenario_name in active_scenarios:
        raise HTTPException(
            status_code=409,
            detail=f"Scenario '{scenario_name}' is already running. "
                   f"Abort it first with POST /chaos/abort.",
        )

    scenario = scenarios[scenario_name]
    injector = FaultInjector(scenario)

    run_meta = {
        "scenario":   scenario_name,
        "started_at": datetime.datetime.utcnow().isoformat() + "Z",
        "method":     scenario["method"],
        "injector":   injector,
    }
    active_scenarios[scenario_name] = run_meta

    # Record in audit history
    history.append({
        "scenario":   scenario_name,
        "started_at": run_meta["started_at"],
        "method":     scenario["method"],
        "target":     scenario["target_container"],
        "severity":   scenario.get("severity"),
    })

    # Run in background thread — non-blocking
    thread = threading.Thread(target=injector.run, daemon=True)
    thread.start()

    _log(f"[CHAOS] Scenario '{scenario_name}' started via API.")

    return ScenarioRunResult(
        scenario=scenario_name,
        started_at=run_meta["started_at"],
        method=scenario["method"],
        status="RUNNING",
        message=(
            f"Chaos scenario '{scenario_name}' is now active. "
            f"Duration: {scenario.get('duration_seconds', '?')}s. "
            f"Expected alert: {scenario.get('expected_alert', 'unknown')}."
        ),
    )


@app.get("/chaos/status")
def get_status():
    """Return all currently active chaos scenarios."""
    return {
        "active_count": len(active_scenarios),
        "active": [
            {
                "scenario":   name,
                "method":     meta["method"],
                "started_at": meta["started_at"],
            }
            for name, meta in active_scenarios.items()
        ],
    }


@app.post("/chaos/abort")
def abort_all():
    """Emergency stop — abort all running chaos scenarios immediately."""
    aborted = []
    for name, meta in list(active_scenarios.items()):
        try:
            meta["injector"].abort()
            aborted.append(name)
        except Exception as e:
            _log(f"[CHAOS] Abort error for {name}: {e}", "WARN")

    _log(f"[CHAOS] Emergency abort triggered. Aborted: {aborted}")
    return {"aborted": aborted, "message": "All scenarios signaled to stop."}


@app.post("/chaos/abort/{scenario_name}")
def abort_scenario(scenario_name: str):
    """Abort a specific running scenario."""
    if scenario_name not in active_scenarios:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_name}' is not running.")
    active_scenarios[scenario_name]["injector"].abort()
    _log(f"[CHAOS] Abort requested for scenario '{scenario_name}'.")
    return {"aborted": scenario_name, "message": "Scenario abort signal sent."}


@app.get("/chaos/history")
def get_history(limit: int = 50):
    """Return audit log of all past chaos runs."""
    return {"history": history[-limit:], "total_runs": len(history)}


@app.get("/health")
def health():
    return {"status": "ok", "service": "chaos_controller"}


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    _log("[CHAOS] Chaos Controller starting up...")
    uvicorn.run(app, host="0.0.0.0", port=5002)
