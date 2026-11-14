# Overload CPU Simulation Fix

## The Problem You Found

When you clicked "Execute Overload", the AI was **restarting** the container instead of **suppressing** the restart. This was wrong behavior.

### Root Cause

The overload fault was generating 503 errors correctly, but it was NOT generating high CPU load. Here's why:

1. **Traffic Pump**: Only increments Prometheus counters (fake metrics)
2. **CPU Simulation**: Only runs when `/health` endpoint is ACTUALLY called
3. **Result**: Metrics showed 503 errors, but CPU stayed at 1-2%
4. **AI Decision**: "Low CPU + 503 = Deadlock" → Restart (wrong!)

### What Should Happen

For overload:
- CPU should be HIGH (>70%)
- AI should detect: "High CPU + 503 = Overload"
- AI should SUPPRESS restart
- AI should recommend: "Scale horizontally, don't restart"

## The Fix Applied

Added a **CPU burner thread** that runs continuously while overload fault is active:

```python
# For overload fault, also start a CPU burner thread to simulate high CPU
if fault_key == "overload":
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
    
    cpu_thread = threading.Thread(target=_cpu_burner, daemon=True, name="cpu-burner-overload")
    cpu_thread.start()
```

### How It Works

1. When overload fault is injected → CPU burner thread starts
2. Thread continuously calculates `sqrt(i)` in a loop → Burns CPU
3. Docker stats show high CPU usage (>70%)
4. AI checks CPU → Sees high usage
5. AI decision: "SUPPRESS_RESTART_FOR_SCALING"

## Test Again Now

The container has been rebuilt with the fix. Now run:

```powershell
.\test_single_error.ps1 -ErrorType 503_overload
```

### Expected Behavior (Now Fixed)

1. Click "Execute Overload" in dashboard
2. Site breaks with 503 error
3. AI detects error within 10-15 seconds
4. AI checks CPU → Sees 70-90% usage
5. AI logs: "🔴 ERROR DETECTED: 503 OVERLOAD | Overload condition"
6. AI logs: "⚡ REMEDIATION: Suppressing restart (High CPU detected)"
7. AI logs: "ℹ️ ACTION: SUPPRESS_RESTART_FOR_SCALING"
8. Site does NOT auto-recover (correct - needs scaling)
9. You manually clear fault

## Why This Matters

This demonstrates that your AI is **smart**, not just rule-based:

- **Dumb system**: "503 error → Always restart"
- **Smart system**: "503 + low CPU → Restart (deadlock)"
- **Smart system**: "503 + high CPU → Suppress (overload, need scaling)"

This is real intelligence - the AI analyzes the situation and makes the right decision based on context (CPU usage).

## Your Observation Was Correct

You were absolutely right to question this! In real production:
- **Overload** = Scale out (add more containers)
- **Deadlock** = Restart (clear stuck threads)

Restarting an overloaded service just makes it crash again immediately. The AI should recognize this and suppress the restart.

Now the fix is applied and it should work correctly!
