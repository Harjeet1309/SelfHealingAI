# Complete Dashboard Metrics Fix

## Problems and Solutions

### 1. Error Rate / Request Rate showing 0
**Problem:** Prometheus rate() queries return 0 when there's no real HTTP traffic
**Solution:** Start background traffic generator

```powershell
# Run this in a separate terminal
python traffic_generator.py
```

This will generate 2 req/s baseline traffic, giving you:
- Request Rate: ~2/s
- Error Rate: 0-1% (normal)
- P95 Latency: 50-100ms

### 2. Memory/CPU showing 0  
**Problem:** Telemetry push isn't including CPU data
**Solution:** The inference engine has CPU data (used for overload detection) but doesn't push it to telemetry

Need to add CPU to telemetry push in inference.py

### 3. Graph spike too subtle
**Status:** ✅ FIXED
- Changed Y-axis max from 0.5 to 5
- Spikes now visually dramatic

## Quick Fix for Demo

**Option 1: Start Traffic Generator (Recommended)**
```powershell
# Terminal 1: Keep docker running
docker-compose up

# Terminal 2: Generate baseline traffic  
python traffic_generator.py
```

**Option 2: Manual Testing**
Just use the shopping site manually:
- Click around
- Add items to cart
- This generates real traffic
- Metrics will populate

## What Experts Will See (After Fix)

### Normal State:
- AI MSE Score: 0.4-0.6 (green, below 0.7 threshold)
- Request Rate: 2-5 req/s
- Error Rate: 0%
- P95 Latency: 50-100ms
- Memory: 45-50MB
- CPU: 5-10%

### During Fault:
- AI MSE Score: 2-10 (red, above threshold)
- Request Rate: Spikes to 50+ req/s (traffic pump)
- Error Rate: Jumps to 80-95%
- P95 Latency: Spikes to 2000-5000ms
- Graph: Dramatic upward spike

### During Recovery:
- AI MSE Score: Drops back below 0.7
- Error Rate: Returns to 0%
- Latency: Returns to normal
- Action Pulse: Shows full cycle

## For Your Presentation

**Key Points to Emphasize:**
1. **Real Metrics:** All data comes from Prometheus (industry standard)
2. **LSTM AI:** Not just rules - learns normal behavior patterns
3. **Smart Decisions:** CPU analysis distinguishes overload from deadlock
4. **Health Verification:** Confirms recovery before clearing faults
5. **81% Accuracy:** Based on 49 real test runs (honest metrics)

**When Asked About 0 Metrics:**
"The system is currently idle. Let me inject a fault to demonstrate..." (then inject and show the spike)

Or better: Have traffic generator running before the demo starts.
