from datetime import datetime, timedelta, timezone
from typing import Dict
import asyncio
import math
import random
import time
import threading

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from .auth import require_token

from .metrics import REQUEST_COUNT, ERROR_COUNT, REQUEST_LATENCY

router = APIRouter()


def _now() -> float:
    return time.time()


def _new_fault(code: int, msg: str) -> Dict:
    return {
        "pending": False,
        "active": False,
        "expires_at": 0.0,
        "intensity": 1.0,
        "code": code,
        "msg": msg,
    }


import os
import json

# Persistent fault state file
FAULT_STATE_FILE = "/app/logs/fault_state.json"

def _load_fault_state():
    """Load fault state from persistent storage"""
    if os.path.exists(FAULT_STATE_FILE):
        try:
            with open(FAULT_STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_fault_state():
    """Save fault state to persistent storage"""
    try:
        state_to_save = {}
        for key, state in system_state.items():
            if state["active"]:
                state_to_save[key] = {
                    "active": state["active"],
                    "intensity": state["intensity"],
                    "code": state["code"],
                    "msg": state["msg"]
                }
        print(f"[FAULT-STATE] Saving {len(state_to_save)} active faults to {FAULT_STATE_FILE}")
        print(f"[FAULT-STATE] State to save: {state_to_save}")
        with open(FAULT_STATE_FILE, 'w') as f:
            json.dump(state_to_save, f, indent=2)
        print(f"[FAULT-STATE] Successfully saved fault state")
    except Exception as e:
        print(f"[FAULT-STATE] ERROR: Could not save fault state: {e}")

# --- V4 FAULT MODEL ---
# Each fault can expire automatically and accepts an "intensity" knob.
system_state = {
    "checkout": _new_fault(500, "Internal Server Error"),
    "cart": _new_fault(503, "Service Unavailable (Deadlock)"),
    "overload": _new_fault(503, "High Traffic Mode"),
    "payment": _new_fault(504, "Gateway Timeout"),
    "security": _new_fault(429, "Bot Defense Active"),
    "db_latency": _new_fault(503, "Database latency spike"),
    "lock_contention": _new_fault(503, "Database lock contention"),
    "dependency_timeout": _new_fault(504, "Payment dependency timeout"),
    "dependency_reset": _new_fault(503, "Upstream connection reset"),
}


def _clear_fault(fault_key: str):
    state = system_state[fault_key]
    state["pending"] = False
    state["active"] = False
    state["expires_at"] = 0.0
    state["intensity"] = 1.0
    _save_fault_state()  # Persist the change


def _activate_fault(
    fault_key: str,
    duration_s: int,
    intensity: float,
    *,
    pending: bool = False,
):
    state = system_state[fault_key]
    state["pending"] = pending
    state["active"] = not pending
    state["intensity"] = intensity
    # REMOVED: Auto-expiry - faults stay active until AI remediates them
    # This prevents fake healing where the timer just runs out
    state["expires_at"] = 0.0  # No expiry - only AI can clear this
    _save_fault_state()  # Persist the change
    if not pending:
        _start_traffic_pump(fault_key, duration_s)


# Map fault keys to the (endpoint, status_code) tuple for metric pumping
# FIXED: Each fault now pumps metrics to the CORRECT endpoint(s) where errors actually occur
_FAULT_METRIC_MAP = {
    # Primary faults (isolated to one endpoint)
    "cart":               ("/cart/add",  "503"),   # 503 deadlock at cart
    "checkout":           ("/checkout",  "500"),   # 500 crash at checkout
    "payment":            ("/payment",   "504"),   # 504 timeout at payment
    "security":           ("/checkout",  "429"),   # 429 bot attack at checkout
    
    # Overload affects the cart endpoint (but CPU is system-wide)
    "overload":           ("/cart/add",  "503"),
    
    # Cross-cutting faults - these need special handling (see _start_traffic_pump_multi)
    # For now, we'll pump to the primary endpoint where they're most likely to be triggered
    "db_latency":         ("/cart/add",  "503"),   # TODO: Should affect /cart/add, /checkout, /payment
    "lock_contention":    ("/cart/add",  "503"),   # TODO: Should affect /cart/add, /checkout
    "dependency_timeout": ("/payment",   "504"),   # Only affects payment
    "dependency_reset":   ("/cart/add",  "503"),   # TODO: Should affect /cart/add, /checkout, /payment
}

def _start_traffic_pump(fault_key: str, duration_s: int):
    """Directly increment Prometheus counters in-process so the AI and
       Alertmanager see a real error-rate spike — no HTTP needed.
       
       FIXED: Pump runs continuously while fault is active, not just for duration_s
    """
    mapping = _FAULT_METRIC_MAP.get(fault_key)
    if not mapping:
        return
    endpoint, status = mapping

    pump_name = f"pump-{fault_key}"
    if not any(t.name == pump_name and t.is_alive() for t in threading.enumerate()):
        def _pump():
            # Run continuously while fault is active
            while True:
                if not _is_fault_active(fault_key):
                    break # Exit thread cleanly when fault is cleared
                # Simulate a realistic burst: ~3 requests/s with ~90% error rate
                REQUEST_COUNT.labels(method="POST", endpoint=endpoint, status=status).inc()
                REQUEST_COUNT.labels(method="POST", endpoint=endpoint, status="200").inc()
                ERROR_COUNT.labels(  method="POST", endpoint=endpoint, status=status).inc()
                
                # IMPORTANT: Inject high latency so the P95 sensor spikes on the dashboard
                latency_spike = 1.2 + (random.random() * 1.3) # 1.2s to 2.5s
                REQUEST_LATENCY.labels(method="POST", endpoint=endpoint).observe(latency_spike)
                
                time.sleep(0.33)  # ~3 Hz

        t = threading.Thread(target=_pump, daemon=True, name=pump_name)
        t.start()
    
    # For overload fault, also start a CPU burner thread to simulate high CPU
    if fault_key == "overload":
        cpu_burner_name = "cpu-burner-overload"
        if not any(t.name == cpu_burner_name and t.is_alive() for t in threading.enumerate()):
            def _cpu_burner():
                import math
                while _is_fault_active(fault_key):
                    # Burn CPU to simulate overload condition
                    intensity = system_state["overload"]["intensity"]
                    loops = int(2_000_000 + (4_000_000 * intensity))
                    acc = 0.0
                    for i in range(loops):
                        acc += math.sqrt(i)
                    time.sleep(0.1)  # Brief pause between bursts
            
            cpu_thread = threading.Thread(target=_cpu_burner, daemon=True, name=cpu_burner_name)
            cpu_thread.start()


def _is_fault_active(fault_key: str) -> bool:
    state = system_state[fault_key]
    if not state["active"]:
        return False
    
    # REMOVED: Auto-expiry check - faults don't expire on their own
    # Only AI remediation (via /inject/reset) can clear faults
    # This ensures we're testing REAL healing, not fake timer-based recovery
    return True


def _promote_pending_if_needed(fault_key: str):
    state = system_state[fault_key]
    if state["pending"]:
        state["pending"] = False
        state["active"] = True


def _format_expiry(epoch_seconds: float) -> str:
    if not epoch_seconds:
        return "n/a"
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).isoformat()


import os
import json

# --- AI PERFORMANCE TRACKER (PERSISTENT) ---
class AIStats(BaseModel):
    total_detections: int = 0

    # ── Restart outcome breakdown (for precision / recall) ─────────────
    # A "verified" restart = health check confirmed the service recovered.
    # An "unverified" restart = service didn't come back healthy — likely a FP.
    restarts_verified: int = 0        # True Positives  (real fault, fixed)
    restarts_unverified: int = 0      # False Positives (restarted for no good reason)

    # Non-restart actions the AI took deliberately
    remediations_suppressed: int = 0  # high-CPU overload — correctly NOT restarted
    log_only_actions: int = 0         # 429 bot — log only (correct)

    # Legacy compat fields kept for the dashboard chart
    remediations_fixed: int = 0       # alias: restarts_verified (updated in sync)
    false_positives: int = 0          # alias: restarts_unverified (updated in sync)
    total_incidents: int = 0          # ground truth (injections)

    error_counts: Dict[str, int] = Field(
        default_factory=lambda: {
            "500_CRASH": 0,
            "503_DEADLOCK": 0,
            "503_OVERLOAD": 0,
            "504_TIMEOUT": 0,
            "429_SECURITY": 0,
        }
    )

    # ── Computed metrics (read-only, derived on get) ───────────────────
    @property
    def precision(self) -> float:
        """
        Precision = TP / (TP + FP)
        = verified restarts / total restart attempts
        Answers: "Of all the times we restarted, how often did it actually fix things?"
        """
        total_restarts = self.restarts_verified + self.restarts_unverified
        if total_restarts == 0:
            return 1.0  # No restarts yet — optimistically 100%
        return round(self.restarts_verified / total_restarts, 4)

    @property
    def recall(self) -> float:
        """
        Recall = TP / (TP + FN)
        = verified restarts / total real incidents injected
        Answers: "Of all the real faults, how many did we catch AND fix?"
        FN = incidents we detected but couldn't verify recovery for.
        """
        if self.total_incidents == 0:
            return 0.0
        return round(self.restarts_verified / self.total_incidents, 4)

    @property
    def f1_score(self) -> float:
        """Harmonic mean of precision and recall."""
        p, r = self.precision, self.recall
        if p + r == 0:
            return 0.0
        return round(2 * p * r / (p + r), 4)


STATS_FILE = "logs/dashboard_stats.json"
os.makedirs("logs", exist_ok=True)

def _load_stats() -> AIStats:
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r") as f:
                return AIStats(**json.load(f))
        except Exception:
            return AIStats()
    return AIStats()

def _save_stats(stats: AIStats):
    with open(STATS_FILE, "w") as f:
        # Exclude computed properties (not serialisable via .json())
        f.write(stats.model_dump_json(exclude={"precision", "recall", "f1_score"}))

performance_data = _load_stats()

@router.post("/ai/report")
async def report_ai_action(data: Dict, _: None = Depends(require_token)):
    global performance_data
    performance_data.total_detections += 1
    action    = data.get("action")
    error_key = data.get("error_key")

    # ── Precision / recall tracking ────────────────────────────────────
    if action in {"RESTART_SUCCESS", "RESTART_SUCCESS_VERIFIED"}:
        # Health check confirmed the service recovered — True Positive
        performance_data.restarts_verified    += 1
        performance_data.remediations_fixed   += 1  # legacy alias
    elif action == "RESTART_SUCCESS_UNVERIFIED":
        # We restarted but couldn't confirm recovery — treat as False Positive
        performance_data.restarts_unverified  += 1
        performance_data.false_positives      += 1  # legacy alias
    elif action in {"SUPPRESS_RESTART_FOR_SCALING"}:
        performance_data.remediations_suppressed += 1
    elif action == "LOG_ONLY":
        performance_data.log_only_actions += 1

    # ── Ground-truth incident counter ─────────────────────────────────
    # Any non-suppressed, non-log detection is a real incident
    if action not in {"LOG_ONLY", "SUPPRESS_RESTART_FOR_SCALING",
                      "COOLDOWN_ACTIVE", "NO_ACTION_MAPPED",
                      "REMEDIATION_IN_PROGRESS"}:
        performance_data.total_incidents += 1

    if error_key in performance_data.error_counts:
        performance_data.error_counts[error_key] += 1

    _save_stats(performance_data)
    return {"status": "Stats Persisted"}

# --- LIVE TELEMETRY (REAL-TIME PULSE) ---
live_telemetry = {
    "mse_score": 0.0,
    "threshold": 0.1,
    "request_rate": 0.0,
    "error_rate": 0.0,
    "p95_latency": 0.0,
    "cpu_percent": 0.0,
    "memory_mb": 0.0,
    "active_conns": 0,
    "online_buffer": 0,
    "last_updated": 0,
}

@router.post("/ai/telemetry/push")
async def push_telemetry(data: Dict, _: None = Depends(require_token)):
    global live_telemetry
    live_telemetry.update(data)
    live_telemetry["last_updated"] = time.time()
    return {"status": "Telemetry Received"}

@router.get("/ai/telemetry")
async def get_telemetry():
    return live_telemetry

@router.get("/ai/stats")
async def get_ai_stats():
    # Return stats enriched with computed precision / recall / F1
    base = performance_data.model_dump(exclude={"precision", "recall", "f1_score"})
    base["precision"] = performance_data.precision
    base["recall"]    = performance_data.recall
    base["f1_score"]  = performance_data.f1_score
    return base

@router.get("/ai/logs")
async def get_ai_logs(lines: int = 15):
    log_path = "logs/remediation.log"
    if not os.path.exists(log_path):
        return []
    try:
        with open(log_path, "r") as f:
            content = f.readlines()
            return [l.strip() for l in content[-lines:]]
    except Exception:
        return []


# --- PRODUCT CATALOG ---
products = [
    {
        "id": 1,
        "name": "Urban Charcoal Shirt",
        "price": 89.99,
        "category": "Apparel",
        "image": "https://images.unsplash.com/photo-1596755094514-f87e32f85e2c?auto=format&fit=crop&w=500&q=80",
        "description": "Premium charcoal long-sleeve shirt.",
    },
    {
        "id": 2,
        "name": "Classic Denim Button-Down",
        "price": 129.00,
        "category": "Casual",
        "image": "https://images.unsplash.com/photo-1578932750355-5eb30face488?auto=format&fit=crop&w=500&q=80",
        "description": "Durable blue denim shirt.",
    },
    {
        "id": 3,
        "name": "Linen Summer Blouse",
        "price": 75.00,
        "category": "Premium",
        "image": "https://images.unsplash.com/photo-1601924994987-69e26d50dc26?auto=format&fit=crop&w=500&q=80",
        "description": "Breathable linen-blend shirt.",
    },
    {
        "id": 4,
        "name": "Elegant Burgundy Blouse",
        "price": 110.00,
        "category": "Women",
        "image": "https://images.unsplash.com/photo-1503342394128-c104d54dba01?auto=format&fit=crop&w=500&q=80",
        "description": "Tailored burgundy 3/4 sleeve blouse.",
    },
]


async def _maybe_apply_db_latency():
    if not _is_fault_active("db_latency"):
        return

    intensity = system_state["db_latency"]["intensity"]
    delay = random.uniform(0.25, 1.5) * intensity
    await asyncio.sleep(min(delay, 4.0))


async def _maybe_apply_lock_contention():
    if not _is_fault_active("lock_contention"):
        return

    intensity = system_state["lock_contention"]["intensity"]
    fail_probability = min(0.25 + (0.6 * intensity), 0.95)
    wait_delay = min(0.5 + (1.2 * intensity), 4.0)

    if random.random() < fail_probability:
        await asyncio.sleep(wait_delay)
        raise HTTPException(
            status_code=503,
            detail="Database lock wait timeout exceeded",
        )

    await asyncio.sleep(wait_delay * 0.5)


def _maybe_raise_dependency_reset(component: str):
    if not _is_fault_active("dependency_reset"):
        return

    intensity = system_state["dependency_reset"]["intensity"]
    fail_probability = min(0.2 + (0.65 * intensity), 0.95)
    if random.random() < fail_probability:
        raise HTTPException(
            status_code=503,
            detail=f"{component} upstream connection reset by peer",
        )


async def _maybe_raise_dependency_timeout(component: str):
    if not _is_fault_active("dependency_timeout"):
        return

    intensity = system_state["dependency_timeout"]["intensity"]
    await asyncio.sleep(min(1.8 + (3.0 * intensity), 7.0))
    raise HTTPException(
        status_code=504,
        detail=f"{component} upstream timeout",
    )


@router.get("/health")
def health(bypass_faults: bool = Query(False, description="Bypass fault checks for remediation verification")):
    # The health endpoint should ONLY report if the container is alive.
    # We no longer intentionally sabotage the health endpoint during application-level faults.
    # Faults will now exclusively affect the actual user-facing application endpoints.
    return {"status": "healthy"}


@router.get("/products")
def get_products():
    return {"products": products}


@router.post("/cart/add")
async def add_to_cart():
    await _maybe_apply_db_latency()
    await _maybe_apply_lock_contention()
    _maybe_raise_dependency_reset("cart")

    _promote_pending_if_needed("cart")
    if _is_fault_active("cart"):
        raise HTTPException(status_code=503, detail="Service Unavailable (Deadlock)")

    # Overload fault — high traffic / CPU saturation
    if _is_fault_active("overload"):
        raise HTTPException(status_code=503, detail="Service Unavailable (Overloaded)")

    return {"message": "Added to cart"}


@router.post("/checkout")
async def checkout():
    await _maybe_apply_db_latency()
    await _maybe_apply_lock_contention()
    _maybe_raise_dependency_reset("checkout")

    # Security / bot-defense fault — rate limit at checkout
    if _is_fault_active("security"):
        raise HTTPException(status_code=429, detail="Too Many Requests — Bot Defense Active")

    _promote_pending_if_needed("checkout")
    if _is_fault_active("checkout"):
        raise HTTPException(status_code=500, detail="Checkout crash")

    return {"message": "Checkout Success"}


@router.post("/payment")
async def payment():
    await _maybe_apply_db_latency()
    _maybe_raise_dependency_reset("payment")
    await _maybe_raise_dependency_timeout("payment")

    _promote_pending_if_needed("payment")
    if _is_fault_active("payment"):
        await asyncio.sleep(4)
        raise HTTPException(status_code=504, detail="Gateway Timeout")

    return {"message": "Payment Success"}


@router.post("/inject/reset")
def reset_faults(
    target: str = Query("all", description="Fault key or 'all'"),
    _: None = Depends(require_token),
):
    if target == "all":
        for key in system_state:
            _clear_fault(key)
        return {"message": "All faults reset."}

    if target not in system_state:
        raise HTTPException(status_code=400, detail=f"Unknown fault target: {target}")

    _clear_fault(target)
    return {"message": f"Fault {target} reset."}


@router.post("/inject/{fault_type}")
def inject_fault(
    fault_type: str,
    duration_s: int = Query(120, ge=5, le=3600),
    intensity: float = Query(1.0, ge=0.1, le=2.0),
    _: None = Depends(require_token),
):
    # Legacy scenarios retained for compatibility with existing demos.
    legacy_map = {
        "500_checkout": ("checkout", False),
        "503_deadlock": ("cart",     False),
        "503_overload": ("overload", False),
        "504_timeout":  ("payment",  False),
        "429_bot":      ("security", False),
    }

    # Real-world style scenarios.
    realistic_map = {
        "db_latency": ("db_latency", False),
        "lock_contention": ("lock_contention", False),
        "dependency_timeout": ("dependency_timeout", False),
        "dependency_reset": ("dependency_reset", False),
    }

    if fault_type in legacy_map:
        key, pending = legacy_map[fault_type]
        _activate_fault(key, duration_s, intensity, pending=pending)
    elif fault_type in realistic_map:
        key, pending = realistic_map[fault_type]
        _activate_fault(key, duration_s, intensity, pending=pending)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown fault type: {fault_type}")

    state = system_state[key]
    return {
        "message": f"Fault {fault_type} injected. Active until AI remediates.",
        "fault_key": key,
        "intensity": intensity,
        "pending": state["pending"],
        "note": "Fault will remain active until AI detection and remediation (no auto-expiry)",
    }


@router.get("/inject/status")
def inject_status():
    """Return current fault state for all keys — no auth required (read-only)."""
    result = {}
    for key, state in system_state.items():
        result[key] = {
            "active":  _is_fault_active(key),
            "pending": state["pending"],
            "code":    state["code"],
        }
    return result


@router.get("/status")
def get_ui_status():
    if _is_fault_active("checkout"):
        return {"status": "FAULT", "code": 500, "message": system_state["checkout"]["msg"]}
    if _is_fault_active("cart"):
        return {"status": "FAULT", "code": 503, "message": system_state["cart"]["msg"]}
    if _is_fault_active("payment"):
        return {"status": "FAULT", "code": 504, "message": system_state["payment"]["msg"]}

    degraded_faults = [
        ("overload", "High Traffic Mode"),
        ("db_latency", "Database Under Stress"),
        ("lock_contention", "Transaction Lock Contention"),
        ("dependency_timeout", "Payment Provider Slow"),
        ("dependency_reset", "Upstream Connection Instability"),
    ]
    for key, msg in degraded_faults:
        if _is_fault_active(key):
            return {"status": "DEGRADED", "code": system_state[key]["code"], "message": msg}

    if _is_fault_active("security"):
        return {"status": "HEALTHY", "code": 200, "message": "Bot Defense Active"}

    return {"status": "HEALTHY", "code": 200, "message": "Stable"}


# Restore fault state from persistent storage on startup
_persisted_state = _load_fault_state()
for key, saved_state in _persisted_state.items():
    if key in system_state:
        system_state[key].update(saved_state)
        print(f"[STARTUP] Restored fault state: {key} = active")
        # Restart traffic pump for active faults
        if saved_state.get("active"):
            _start_traffic_pump(key, 999999)  # Run indefinitely
