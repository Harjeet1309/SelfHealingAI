# AI Threshold Bug - Root Cause and Fix

## The Problem

**Current Behavior:**
- AI MSE Score: 0.48 (normal)
- Threshold: 14.98
- Even when score reaches 0.5666, it shows "NOMINAL STATE"

**Why:**
- Base threshold: 9.991976 (hardcoded default, way too high)
- Multiplier: 1.5
- Effective threshold: 9.991976 × 1.5 = 14.987964

## Why This is Wrong

Normal MSE scores are around 0.3-0.5. During faults, they might spike to 2-10. A threshold of 14.98 means:
- The AI will NEVER detect anomalies
- Even a massive fault with MSE=10 would show as "NOMINAL"
- The AI is essentially blind

## The Correct Threshold

Based on typical LSTM anomaly detection:
- Normal scores: 0.1-0.5
- Anomaly scores: 1.0-20.0
- **Threshold should be: 0.5-1.0**

## The Fix

We need to:
1. Set base threshold to 0.067 (so 0.067 × 1.5 = 0.1)
2. Or set multiplier to 0.01 (so 9.99 × 0.01 = 0.1)
3. Or create threshold.json with correct value

**Option 1: Fix via threshold.json (Recommended)**
```bash
docker exec remediation_engine bash -c 'echo "{\"threshold\": 0.067}" > /models/threshold.json'
docker restart remediation_engine
```

**Option 2: Fix via environment variable**
Add to docker-compose.yml:
```yaml
remediation_engine:
  environment:
    - AI_THRESHOLD_MULTIPLIER=0.01
```

## After Fix

With threshold = 0.1:
- MSE < 0.1: "NOMINAL STATE" (green)
- MSE > 0.1: "ANOMALY DETECTED" (red)
- This will correctly detect faults

## Current Status

The threshold file creation didn't work properly. Need to:
1. Stop containers
2. Manually create threshold.json with correct value
3. Restart containers
4. Verify threshold is 0.1-0.15 (not 14.98)
