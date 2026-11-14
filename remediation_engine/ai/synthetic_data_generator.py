"""
Synthetic API Telemetry Dataset Generator — V2 (5 features)
=============================================================
Features:
    1. request_rate          — HTTP requests per second
    2. error_rate            — Fraction of requests failing (0.0 – 1.0)
    3. p95_latency           — 95th percentile response time in seconds
    4. memory_mb             — Process RSS memory in megabytes
    5. active_connections    — Open TCP connections

Scenarios generated:
    - Normal (healthy, diurnal variation)
    - Crash (500) — sudden error spike, service drops
    - Deadlock (503) — gradual error + latency climb, low CPU
    - Overload (503) — request surge, errors, latency, memory spike
    - Timeout (504) — latency spike leads error rise
    - Bot Attack (429) — massive request rate surge
    - Gradual Degradation — slow drift before fault materializes
    - Memory Leak — exponential memory climb before crash
    - Intermittent Faults — random short spikes in a healthy signal
    - Night (low traffic) — quiet period, minimal metrics
"""

import numpy as np
import os

RNG = np.random.default_rng(seed=42)

# ─────────────────────────────────────────────
# PRIMITIVES
# ─────────────────────────────────────────────

def _noise(size, scale=0.01):
    return RNG.normal(0, scale, size)

def _smooth(arr, window=5):
    kernel = np.ones(window) / window
    return np.convolve(arr, kernel, mode="same")

def _ramp(start, end, steps):
    return np.linspace(start, end, steps)

def _clip(arr, low=0.0, high=1e9):
    return np.clip(arr, low, high)

def _stack(rr, er, lat, mem, conns):
    """Stack 5 feature arrays into shape (n, 5)."""
    return np.stack([
        _clip(rr,    0.0, 15.0),
        _clip(er,    0.0,  1.0),
        _clip(lat,   0.02, 15.0),
        _clip(mem,   20.0, 1024.0),
        _clip(conns, 0.0, 200.0),
    ], axis=1)


# ─────────────────────────────────────────────
# SCENARIO GENERATORS (all return shape (n, 5))
# ─────────────────────────────────────────────

def generate_normal(n=600):
    t = np.linspace(0, 4 * np.pi, n)
    rr    = 1.5 + 1.2 * np.sin(t)        + _noise(n, 0.15)
    er    = 0.003 + np.abs(_noise(n, 0.003))
    lat   = 0.15 + 0.08 * np.sin(t + 1)  + np.abs(_noise(n, 0.02))
    mem   = 85.0 + 5.0 * np.sin(t * 0.5) + _noise(n, 2.0)
    conns = 8.0  + 3.0 * np.sin(t)       + np.abs(_noise(n, 1.0))
    return _stack(rr, er, lat, mem, conns)


def generate_crash_500(n=600, pre=100, fault=400, recovery=100):
    """
    Enhanced Crash Scenario:
    Includes a LONG period of sustained failure (flatline at 1.0)
    to prevent the model from 'accepting' failure as the new normal.
    Also drops metrics to zero (Zombie Service).
    """
    assert pre + fault + recovery == n
    
    # 1. Normal Pre-phase
    rr_p  = 1.5 + _noise(pre, 0.1);    er_p  = 0.004 + np.abs(_noise(pre, 0.003))
    lat_p = 0.18 + _noise(pre, 0.02);  mem_p = 85.0  + _noise(pre, 2.0)
    con_p = 8.0  + np.abs(_noise(pre, 1.0))

    # 2. Critical Fault Phase (Long Flatline + Zeroing metrics)
    # We simulate a process that is alive but totally unresponsive/metrics-blind
    rr_f  = np.full(fault, 0.05)       + np.abs(_noise(fault, 0.02))
    er_f  = np.full(fault, 1.0)        # TOTAL FAILURE
    lat_f = np.full(fault, 10.0)       # TIMEOUTS
    mem_f = np.full(fault, 0.0)        # ZOMBIE metrics (observed in user logs)
    con_f = np.full(fault, 0.0)

    # 3. Recovery Phase
    rr_r  = _ramp(0.05, 1.5, recovery) + _noise(recovery, 0.1)
    er_r  = _ramp(1.0, 0.004, recovery) + np.abs(_noise(recovery, 0.01))
    lat_r = _ramp(10.0, 0.18, recovery) + np.abs(_noise(recovery, 0.02))
    mem_r = _ramp(0.0, 85, recovery)    + _noise(recovery, 2.0)
    con_r = _ramp(0.0, 8, recovery)     + np.abs(_noise(recovery, 0.5))

    return _stack(
        np.concatenate([rr_p,  rr_f,  rr_r]),
        np.concatenate([er_p,  er_f,  er_r]),
        np.concatenate([lat_p, lat_f, lat_r]),
        np.concatenate([mem_p, mem_f, mem_r]),
        np.concatenate([con_p, con_f, con_r]),
    )


def generate_deadlock_503(n=400, pre=120, fault=160, recovery=120):
    assert pre + fault + recovery == n
    rr_p  = 1.8 + _noise(pre, 0.12);   er_p  = 0.005 + np.abs(_noise(pre, 0.003))
    lat_p = 0.2  + _noise(pre, 0.02);  mem_p = 90.0  + _noise(pre, 2.0)
    con_p = 9.0  + np.abs(_noise(pre, 1.0))

    rr_f  = _ramp(1.8, 0.4, fault) + _noise(fault, 0.08)
    er_f  = _ramp(0.02, 0.85, fault) + _noise(fault, 0.04)
    lat_f = _ramp(0.2, 3.5, fault) + np.abs(_noise(fault, 0.2))
    mem_f = _ramp(90, 140, fault) + _noise(fault, 4.0)      # moderate memory climb
    con_f = _ramp(9, 50, fault) + np.abs(_noise(fault, 2.0)) # connections queue up

    rr_r  = _ramp(0.4, 1.7, recovery)   + _noise(recovery, 0.1)
    er_r  = _ramp(0.85, 0.004, recovery) + np.abs(_noise(recovery, 0.01))
    lat_r = _ramp(3.5, 0.2, recovery)   + np.abs(_noise(recovery, 0.03))
    mem_r = _ramp(140, 90, recovery)     + _noise(recovery, 2.0)
    con_r = _ramp(50, 9, recovery)       + np.abs(_noise(recovery, 1.0))

    return _stack(
        np.concatenate([rr_p,  rr_f,  rr_r]),
        np.concatenate([er_p,  er_f,  er_r]),
        np.concatenate([lat_p, lat_f, lat_r]),
        np.concatenate([mem_p, mem_f, mem_r]),
        np.concatenate([con_p, con_f, con_r]),
    )


def generate_overload_503(n=350, pre=100, fault=150, recovery=100):
    assert pre + fault + recovery == n
    rr_p  = 1.5 + _noise(pre, 0.1);    er_p  = 0.004 + np.abs(_noise(pre, 0.003))
    lat_p = 0.15 + _noise(pre, 0.02);  mem_p = 85.0  + _noise(pre, 2.0)
    con_p = 8.0  + np.abs(_noise(pre, 1.0))

    rr_f  = _ramp(1.5, 7.5, fault)    + _noise(fault, 0.3)
    er_f  = _ramp(0.01, 0.6, fault)   + _noise(fault, 0.04)
    lat_f = _ramp(0.15, 4.0, fault)   + np.abs(_noise(fault, 0.2))
    mem_f = _ramp(85, 480, fault)      + _noise(fault, 15.0)   # memory surges under load
    con_f = _ramp(8, 150, fault)       + np.abs(_noise(fault, 5.0))

    rr_r  = _ramp(7.5, 1.6, recovery) + _noise(recovery, 0.15)
    er_r  = _ramp(0.6, 0.005, recovery) + np.abs(_noise(recovery, 0.01))
    lat_r = _ramp(4.0, 0.16, recovery) + np.abs(_noise(recovery, 0.03))
    mem_r = _ramp(480, 88, recovery)   + _noise(recovery, 8.0)
    con_r = _ramp(150, 9, recovery)    + np.abs(_noise(recovery, 2.0))

    return _stack(
        np.concatenate([rr_p,  rr_f,  rr_r]),
        np.concatenate([er_p,  er_f,  er_r]),
        np.concatenate([lat_p, lat_f, lat_r]),
        np.concatenate([mem_p, mem_f, mem_r]),
        np.concatenate([con_p, con_f, con_r]),
    )


def generate_timeout_504(n=350, pre=100, fault=150, recovery=100):
    assert pre + fault + recovery == n
    rr_p  = 1.6 + _noise(pre, 0.12);   er_p  = 0.004 + np.abs(_noise(pre, 0.003))
    lat_p = 0.2  + _noise(pre, 0.02);  mem_p = 88.0  + _noise(pre, 2.0)
    con_p = 9.0  + np.abs(_noise(pre, 1.0))

    rr_f  = _ramp(1.6, 0.6, fault)    + _noise(fault, 0.08)
    er_f  = _ramp(0.004, 0.75, fault) + _noise(fault, 0.04)
    lat_f = _ramp(0.2, 7.5, fault)    + np.abs(_noise(fault, 0.4))
    mem_f = _ramp(88, 115, fault)      + _noise(fault, 3.0)
    con_f = _ramp(9, 70, fault)        + np.abs(_noise(fault, 3.0)) # waiting connections

    rr_r  = _ramp(0.6, 1.6, recovery)  + _noise(recovery, 0.1)
    er_r  = _ramp(0.75, 0.004, recovery) + np.abs(_noise(recovery, 0.01))
    lat_r = _ramp(7.5, 0.2, recovery)  + np.abs(_noise(recovery, 0.05))
    mem_r = _ramp(115, 88, recovery)    + _noise(recovery, 2.0)
    con_r = _ramp(70,  9, recovery)     + np.abs(_noise(recovery, 1.0))

    return _stack(
        np.concatenate([rr_p,  rr_f,  rr_r]),
        np.concatenate([er_p,  er_f,  er_r]),
        np.concatenate([lat_p, lat_f, lat_r]),
        np.concatenate([mem_p, mem_f, mem_r]),
        np.concatenate([con_p, con_f, con_r]),
    )


def generate_bot_attack_429(n=300, pre=80, fault=140, recovery=80):
    assert pre + fault + recovery == n
    rr_p  = 1.4 + _noise(pre, 0.1);   er_p  = 0.003 + np.abs(_noise(pre, 0.003))
    lat_p = 0.15 + _noise(pre, 0.02); mem_p = 83.0  + _noise(pre, 2.0)
    con_p = 8.0  + np.abs(_noise(pre, 1.0))

    rr_f  = _ramp(1.4, 9.0, fault)    + _noise(fault, 0.5)
    er_f  = _ramp(0.003, 0.45, fault) + _noise(fault, 0.03)
    lat_f = _ramp(0.15, 1.2, fault)   + np.abs(_noise(fault, 0.08))
    mem_f = _ramp(83, 200, fault)      + _noise(fault, 8.0)
    con_f = _ramp(8, 120, fault)       + np.abs(_noise(fault, 5.0))

    rr_r  = _ramp(9.0, 1.4, recovery)   + _noise(recovery, 0.2)
    er_r  = _ramp(0.45, 0.003, recovery) + np.abs(_noise(recovery, 0.01))
    lat_r = _ramp(1.2, 0.15, recovery)  + np.abs(_noise(recovery, 0.02))
    mem_r = _ramp(200, 84, recovery)     + _noise(recovery, 4.0)
    con_r = _ramp(120, 8, recovery)      + np.abs(_noise(recovery, 2.0))

    return _stack(
        np.concatenate([rr_p,  rr_f,  rr_r]),
        np.concatenate([er_p,  er_f,  er_r]),
        np.concatenate([lat_p, lat_f, lat_r]),
        np.concatenate([mem_p, mem_f, mem_r]),
        np.concatenate([con_p, con_f, con_r]),
    )


def generate_gradual_degradation(n=500, pre=150, fault=250, recovery=100):
    assert pre + fault + recovery == n
    rr_p  = 1.5 + _noise(pre, 0.1);   er_p  = 0.004 + np.abs(_noise(pre, 0.003))
    lat_p = 0.18 + _noise(pre, 0.02); mem_p = 86.0  + _noise(pre, 2.0)
    con_p = 8.0  + np.abs(_noise(pre, 1.0))

    rr_f  = _ramp(1.5, 0.9, fault)    + _noise(fault, 0.08)
    er_f  = _ramp(0.004, 0.4, fault)  + _noise(fault, 0.015)
    lat_f = _ramp(0.18, 2.8, fault)   + np.abs(_noise(fault, 0.12))
    mem_f = _ramp(86, 250, fault)      + _noise(fault, 6.0)
    con_f = _ramp(8, 40, fault)        + np.abs(_noise(fault, 1.5))

    rr_r  = _ramp(0.9, 1.5, recovery)   + _noise(recovery, 0.08)
    er_r  = _ramp(0.4, 0.004, recovery) + np.abs(_noise(recovery, 0.008))
    lat_r = _ramp(2.8, 0.18, recovery)  + np.abs(_noise(recovery, 0.02))
    mem_r = _ramp(250, 87, recovery)     + _noise(recovery, 4.0)
    con_r = _ramp(40, 8, recovery)       + np.abs(_noise(recovery, 1.0))

    return _stack(
        np.concatenate([rr_p,  rr_f,  rr_r]),
        np.concatenate([er_p,  er_f,  er_r]),
        np.concatenate([lat_p, lat_f, lat_r]),
        np.concatenate([mem_p, mem_f, mem_r]),
        np.concatenate([con_p, con_f, con_r]),
    )


def generate_memory_leak_pattern(n=450, pre=100, fault=250, recovery=100):
    assert pre + fault + recovery == n
    rr_p  = 1.4 + _noise(pre, 0.1);   er_p  = 0.003 + np.abs(_noise(pre, 0.003))
    lat_p = 0.16 + _noise(pre, 0.02); mem_p = 84.0  + _noise(pre, 2.0)
    con_p = 8.0  + np.abs(_noise(pre, 1.0))

    t = np.linspace(0, 1, fault)
    rr_f  = (1.4 - 0.8 * t)          + _noise(fault, 0.07)
    er_f  = (0.003 + 0.5 * t**2)     + _noise(fault, 0.015)
    lat_f = (0.16 + 4.5 * t**2.5)    + np.abs(_noise(fault, 0.2))
    mem_f = (84 + 700 * t**1.8)       + _noise(fault, 8.0)   # exponential memory leak
    con_f = (8 + 30 * t)              + np.abs(_noise(fault, 1.5))

    rr_r  = _ramp(rr_f[-1], 1.4, recovery)   + _noise(recovery, 0.08)
    er_r  = _ramp(er_f[-1], 0.003, recovery) + np.abs(_noise(recovery, 0.008))
    lat_r = _ramp(lat_f[-1], 0.16, recovery) + np.abs(_noise(recovery, 0.02))
    mem_r = _ramp(mem_f[-1], 85, recovery)   + _noise(recovery, 5.0)
    con_r = _ramp(con_f[-1], 8, recovery)    + np.abs(_noise(recovery, 1.0))

    return _stack(
        np.concatenate([rr_p,  rr_f,  rr_r]),
        np.concatenate([er_p,  er_f,  er_r]),
        np.concatenate([lat_p, lat_f, lat_r]),
        np.concatenate([mem_p, mem_f, mem_r]),
        np.concatenate([con_p, con_f, con_r]),
    )


def generate_intermittent_faults(n=500):
    rr    = 1.5 + _noise(n, 0.12)
    er    = np.abs(_noise(n, 0.004))
    lat   = 0.18 + np.abs(_noise(n, 0.03))
    mem   = 86.0 + _noise(n, 2.0)
    conns = 8.0  + np.abs(_noise(n, 1.0))

    for _ in range(15):
        start  = RNG.integers(30, n - 40)
        length = RNG.integers(5, 25)
        end    = min(start + length, n)
        er[start:end]    += RNG.uniform(0.1, 0.6)
        lat[start:end]   += RNG.uniform(0.5, 3.0)
        mem[start:end]   += RNG.uniform(20, 100)
        conns[start:end] += RNG.uniform(5, 30)

    return _stack(rr, er, lat, mem, conns)


def generate_night_low_traffic(n=400):
    t     = np.linspace(0, np.pi, n)
    rr    = 0.15 + 0.1 * np.abs(np.sin(t)) + _noise(n, 0.03)
    er    = np.abs(_noise(n, 0.002))
    lat   = 0.10 + np.abs(_noise(n, 0.015))
    mem   = 72.0 + _noise(n, 1.5)    # lower memory during quiet hours
    conns = 3.0  + np.abs(_noise(n, 0.5))
    return _stack(rr, er, lat, mem, conns)


# ─────────────────────────────────────────────
# DATASET ASSEMBLER
# ─────────────────────────────────────────────

def build_dataset(repeat_normal=8, smooth_window=3, verbose=True):
    """
    Assemble a large, balanced 5-feature training dataset.

    Returns:
        data: np.ndarray of shape (total_timesteps, 5)
    """
    segments = []

    for _ in range(repeat_normal):
        n_steps = RNG.integers(400, 800)
        segments.append(generate_normal(n=n_steps))

    segments.append(generate_crash_500())
    segments.append(generate_deadlock_503())
    segments.append(generate_overload_503())
    segments.append(generate_timeout_504())
    segments.append(generate_bot_attack_429())
    segments.append(generate_gradual_degradation())
    segments.append(generate_memory_leak_pattern())
    segments.append(generate_intermittent_faults())
    segments.append(generate_night_low_traffic())

    for _ in range(3):
        segments.append(generate_gradual_degradation())
        segments.append(generate_memory_leak_pattern())
        segments.append(generate_deadlock_503())

    for _ in range(4):
        segments.append(generate_night_low_traffic())
        segments.append(generate_normal(n=500))

    if verbose:
        print("[DATAGEN] Segment breakdown:")
        for i, s in enumerate(segments):
            print(f"  Segment {i+1:02d}: {s.shape[0]} timesteps  shape={s.shape}")

    data = np.concatenate(segments, axis=0)

    for col in range(data.shape[1]):
        data[:, col] = _smooth(data[:, col], window=smooth_window)

    if verbose:
        names = ["request_rate", "error_rate", "p95_latency", "memory_mb", "active_conns"]
        print(f"\n[DATAGEN] Total: {data.shape[0]:,} timesteps x {data.shape[1]} features")
        for i, name in enumerate(names):
            col = data[:, i]
            print(f"  {name:20s} min={col.min():.3f}  max={col.max():.3f}  mean={col.mean():.3f}")

    return data


if __name__ == "__main__":
    data = build_dataset(verbose=True)
    save_path = os.path.join(os.path.dirname(__file__), "synthetic_dataset.npy")
    np.save(save_path, data)
    print(f"\n[DATAGEN] Saved to {save_path}")
