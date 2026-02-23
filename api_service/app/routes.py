from datetime import datetime, timedelta, timezone
from typing import Dict
import asyncio
import math
import random
import time

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .metrics import REQUEST_COUNT

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
    state["expires_at"] = _now() + duration_s


def _is_fault_active(fault_key: str) -> bool:
    state = system_state[fault_key]
    if not state["active"]:
        return False

    if state["expires_at"] and _now() >= state["expires_at"]:
        _clear_fault(fault_key)
        return False

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
    remediations_fixed: int = 0
    remediations_suppressed: int = 0
    false_positives: int = 0
    total_incidents: int = 0 # Ground truth
    error_counts: Dict[str, int] = Field(
        default_factory=lambda: {
            "500_CRASH": 0,
            "503_DEADLOCK": 0,
            "503_OVERLOAD": 0,
            "504_TIMEOUT": 0,
            "429_SECURITY": 0,
        }
    )

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
        f.write(stats.json())

performance_data = _load_stats()

@router.post("/ai/report")
async def report_ai_action(data: Dict):
    global performance_data
    performance_data.total_detections += 1
    action = data.get("action")
    error_key = data.get("error_key")

    if action == "RESTART_SUCCESS":
        performance_data.remediations_fixed += 1
    elif action in {"SUPPRESS_RESTART_FOR_SCALING", "LOG_ONLY"}:
        performance_data.remediations_suppressed += 1

    if error_key in performance_data.error_counts:
        performance_data.error_counts[error_key] += 1
    
    _save_stats(performance_data)
    return {"status": "Stats Persisted"}

@router.get("/ai/stats")
async def get_ai_stats():
    return performance_data

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
        "image": "/dashboard/image.png",
        "description": "Premium charcoal long-sleeve shirt.",
    },
    {
        "id": 2,
        "name": "Classic Denim Button-Down",
        "price": 129.00,
        "category": "Casual",
        "image": "/dashboard/image%20copy.png",
        "description": "Durable blue denim shirt.",
    },
    {
        "id": 3,
        "name": "Linen Summer Blouse",
        "price": 75.00,
        "category": "Premium",
        "image": "/dashboard/image%20copy%202.png",
        "description": "Breathable linen-blend shirt.",
    },
    {
        "id": 4,
        "name": "Elegant Burgundy Blouse",
        "price": 110.00,
        "category": "Women",
        "image": "/dashboard/image%20copy%203.png",
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
def health():
    if _is_fault_active("security"):
        REQUEST_COUNT.labels(method="GET", endpoint="/health", status="429").inc()
        raise HTTPException(status_code=429, detail="Too Many Requests")

    if _is_fault_active("overload"):
        REQUEST_COUNT.labels(method="GET", endpoint="/health", status="503").inc()

        # Real CPU pressure to make infrastructure telemetry realistic.
        intensity = system_state["overload"]["intensity"]
        loops = int(4_000_000 + (8_000_000 * intensity))
        acc = 0.0
        for i in range(loops):
            acc += math.sqrt(i)

        raise HTTPException(status_code=503, detail="Service Overloaded")

    for key in ["checkout", "cart", "payment"]:
        if _is_fault_active(key):
            status_code = str(system_state[key]["code"])
            REQUEST_COUNT.labels(method="GET", endpoint="/health", status=status_code).inc()
            raise HTTPException(status_code=int(status_code), detail="Unhealthy")

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
        raise HTTPException(status_code=503, detail="Service Unavailable")

    return {"message": "Added to cart"}


@router.post("/checkout")
async def checkout():
    await _maybe_apply_db_latency()
    await _maybe_apply_lock_contention()
    _maybe_raise_dependency_reset("checkout")

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
):
    # Legacy scenarios retained for compatibility with existing demos.
    legacy_map = {
        "500_checkout": ("checkout", True),
        "503_deadlock": ("cart", True),
        "503_overload": ("overload", False),
        "504_timeout": ("payment", True),
        "429_bot": ("security", False),
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
        "message": f"Fault {fault_type} injected.",
        "fault_key": key,
        "duration_s": duration_s,
        "intensity": intensity,
        "pending": state["pending"],
        "expires_at_utc": _format_expiry(state["expires_at"]),
    }


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
