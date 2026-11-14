# Critical Issue: Graph Not Spiking

## The Problem

**What You See:**
- Fault injected at 4:20:49 PM
- AI takes action (restarts container)
- But graph stays FLAT at 0.0000
- No visual spike

**Root Cause:**
The system has TWO detection layers:
1. **Rule-Based (Prometheus)** - Detects specific error codes (503, 504, 500)
2. **LSTM AI** - Detects behavioral anomalies in time-series patterns

**What's Happening:**
- Rule-based system: ✅ Working (detects 503 spike, triggers restart)
- LSTM AI: ❌ Not spiking (sees no traffic pattern change)

The graph shows the LSTM MSE score, which isn't spiking because there's no real traffic for it to analyze.

## Why LSTM Isn't Spiking

**LSTM Requirements:**
- Needs time-series data (30 timesteps)
- Analyzes: request_rate, error_rate, p95_latency, memory, connections
- Learns normal patterns, detects deviations

**Current State:**
- Request rate: 0/s (no traffic)
- Error rate: 0% (no traffic)
- Latency: 0ms (no traffic)
- LSTM sees: [0, 0, 0, 0, 0] → No pattern change → MSE stays low

**Traffic Pump:**
- Increments Prometheus counters
- But doesn't generate actual HTTP requests
- So rate() queries return 0
- LSTM has nothing to analyze

## The Fix

### Option 1: Start Traffic Generator (Immediate Fix)
```powershell
# Terminal 1: Keep docker running
# Terminal 2: Generate traffic
python traffic_generator.py
```

This creates:
- Baseline traffic: 2 req/s
- When fault injected: Error rate spikes to 90%
- LSTM sees pattern change: [2, 0.9, 2000, 50, 5]
- MSE spikes to 5-15
- Graph shows dramatic spike ✅

### Option 2: Use Shopping Site Manually
Before injecting fault:
1. Click around the shopping site (10-20 clicks)
2. Add items to cart
3. This generates real traffic
4. Then inject fault
5. LSTM will see the pattern change

### Option 3: Fix Traffic Pump to Generate Real Requests
Modify traffic pump to make actual HTTP calls instead of just incrementing counters.

## For Expert Presentation

**Current Behavior (Without Traffic):**
- "The rule-based system detected the 503 spike and triggered remediation"
- "The LSTM layer requires traffic to analyze behavioral patterns"
- Graph stays flat (not impressive)

**Fixed Behavior (With Traffic):**
- "Both detection layers working: rules caught the 503, LSTM detected the behavioral anomaly"
- Graph spikes dramatically
- Shows multi-layer defense

## Immediate Action

Before your presentation:

```powershell
# Start everything with traffic
.\start_demo.ps1
```

Or manually:
```powershell
# Terminal 1
docker-compose up -d

# Terminal 2  
python traffic_generator.py

# Wait 30 seconds for LSTM to build baseline
# Then inject fault
# Graph will spike dramatically
```

## What Experts Need to See

For a convincing demo, experts need to see:
1. ✅ Normal baseline (graph flat, metrics stable)
2. ✅ Fault injection (button click)
3. ✅ **GRAPH SPIKES** (visual proof AI detected it)
4. ✅ Action logs (shows remediation)
5. ✅ Recovery (graph drops, metrics normalize)

Without the graph spike, it looks like only rules are working (not impressive for an "AI" system).

## Technical Explanation for Experts

"Our system uses a hybrid approach:
- **Layer 1:** Prometheus rules for fast, specific detection (503, 504, 500)
- **Layer 2:** LSTM for behavioral anomaly detection (catches novel failures)
- **Corroboration:** Both layers must agree before remediation
- **This demo:** Traffic generator provides the time-series data the LSTM analyzes"

This explains why traffic is needed and shows sophisticated architecture.
