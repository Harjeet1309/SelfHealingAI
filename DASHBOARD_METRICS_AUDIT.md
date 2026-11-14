# Dashboard Metrics Audit - Expert Presentation Ready

## Current State (Problems)

### 1. Error Rate: 0.0%
**Problem:** Shows 0% even when faults are injected
**Root Cause:** Inference engine queries Prometheus for REAL request metrics, but there's no actual HTTP traffic
**What Experts Will Ask:** "Why is error rate 0 when you just injected a 503 error?"

### 2. Request Rate: 0/s  
**Problem:** Shows 0 requests/second
**Root Cause:** Same - no real HTTP traffic to the API
**What Experts Will Ask:** "How can the AI detect anomalies with no traffic?"

### 3. P95 Latency: 0ms
**Problem:** Shows 0ms latency
**Root Cause:** No real requests = no latency data
**What Experts Will Ask:** "Is this system even running?"

### 4. Memory/CPU: 0MB / 0%
**Problem:** Shows 0 even though containers are running
**Root Cause:** Inference engine isn't collecting container stats properly
**What Experts Will Ask:** "How do you distinguish overload from deadlock with no CPU data?"

### 5. Graph Spike: Too Subtle
**Problem:** Y-axis was capped at 0.5, spikes to 2.24 looked flat
**Status:** FIXED - Now scales to 5
**What Experts Will See:** Dramatic visual spike when anomaly occurs ✅

## The Core Problem

**Traffic Pump vs Real Metrics:**
- Traffic pump: Increments Prometheus counters (fake traffic for alerting)
- Inference engine: Queries Prometheus for rate() calculations (real traffic)
- Result: Counters increment, but rate() = 0 because no time-series data

## Solutions

### Option 1: Generate Real HTTP Traffic (Recommended)
Create a background traffic generator that makes actual HTTP requests:
- Simulates realistic user behavior
- Generates real metrics (latency, error rates, etc.)
- Makes the demo look production-ready

### Option 2: Query Prometheus Counters Directly
Instead of rate(), query the raw counter values:
- Shows that metrics are being collected
- But doesn't show realistic rates
- Less convincing for experts

### Option 3: Hybrid Approach (Best for Demo)
- Use traffic pump for fault scenarios (high burst)
- Add light background traffic for baseline metrics
- Shows both normal operation and fault response

## What Experts Will Expect to See

### During Normal Operation:
- Request Rate: 5-20 req/s (realistic baseline)
- Error Rate: 0-1% (occasional errors are normal)
- P95 Latency: 50-200ms (realistic API latency)
- CPU: 5-15% (light load)
- Memory: 50-100MB (Python app)
- AI MSE Score: 0.3-0.6 (below threshold)

### During Fault Injection:
- Request Rate: Spikes to 50-100 req/s (traffic pump)
- Error Rate: Jumps to 80-95% (fault active)
- P95 Latency: Spikes to 2000-5000ms (timeouts)
- CPU: Varies (high for overload, low for deadlock)
- Memory: Stable or increases
- AI MSE Score: Spikes to 2-10 (above threshold)

### During AI Remediation:
- Error Rate: Drops back to 0-1%
- Latency: Returns to normal
- AI MSE Score: Drops below threshold
- Action Pulse: Shows detection → remediation → recovery

## Implementation Plan

1. ✅ Fix graph Y-axis scaling (DONE)
2. ⏳ Add background traffic generator
3. ⏳ Fix container stats collection (CPU/Memory)
4. ⏳ Ensure Prometheus queries return real data
5. ⏳ Add metric validation checks
6. ⏳ Test full cycle with all metrics updating

## Questions Experts Will Ask

**Q: "How does the AI distinguish between different error types?"**
A: Combines rule-based detection (Prometheus alerts for specific status codes) with LSTM anomaly detection (behavioral patterns). CPU usage helps distinguish overload (high CPU) from deadlock (low CPU).

**Q: "What's your false positive rate?"**
A: Currently 81% precision, 81% recall based on 49 real test runs. 19% false positives due to health check timing issues, which we're addressing.

**Q: "Why is error rate 0 when there's clearly a fault?"**
A: (Current answer is bad) Need to fix this - should show real error rates.

**Q: "How do you prevent the AI from restarting during legitimate traffic spikes?"**
A: Multi-layer approach: 60-second cooldown between restarts, CPU-based overload detection (suppresses restart if CPU >70%), and corroboration requirement (both rules and AI must agree).

**Q: "What happens if the AI fails to remediate?"**
A: Escalation webhook fires after 3 consecutive failures, alerting human operators. Health verification ensures we don't clear faults unless recovery is confirmed.

## Next Steps

Implement the fixes in priority order to make the dashboard expert-ready.
