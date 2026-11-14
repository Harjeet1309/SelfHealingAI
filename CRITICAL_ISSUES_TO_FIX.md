# Critical Issues Preventing LSTM from Working

## Issue 1: AI Score Always 0.0
**Symptom:** `AI SCORE: 0.000000` even with traffic
**Root Cause:** Inference engine not building sequences or computing MSE
**Impact:** Graph never spikes, LSTM never detects anomalies

## Issue 2: Threshold Overwritten to 0.0
**Symptom:** `Threshold persisted → 0.000000 (dynamic=0.000000, static=2.449630)`
**Root Cause:** Dynamic threshold calculation overwrites trained threshold
**Impact:** Even if MSE computed, threshold is wrong

## Issue 3: Premature Recovery (Old Bug Back)
**Symptom:** "Focus Total Recovery" button, system recovers before AI acts
**Root Cause:** Faults cleared before health verification
**Impact:** Looks like fake self-healing

## Issue 4: No Traffic = No Detection
**Symptom:** LSTM needs traffic to analyze patterns
**Root Cause:** System design requires external traffic generator
**Impact:** Can't demo without running separate script

## What We Need:

### Immediate Fixes:
1. Fix MSE computation in inference engine (currently returns 0.0)
2. Prevent dynamic threshold from overwriting trained threshold
3. Ensure enough samples collected before LSTM runs
4. Fix premature fault clearing (again)

### For Your Presentation:
You need the LSTM graph to spike when errors occur. This requires:
- LSTM computing non-zero MSE scores
- Correct threshold (2.45, not 0.0 or 0.17)
- Traffic generation (either manual or automated)
- Graph visualization showing spike from ~2.4 to 200+

## Current State:
- ✅ LSTM trained successfully (100% detection on test data)
- ✅ Model loaded in Docker
- ❌ Inference engine not computing MSE
- ❌ Threshold corrupted to 0.0
- ❌ Graph stuck at 0.0

## Next Steps:
1. Debug why `_compute_ai_score()` returns 0.0
2. Fix threshold persistence logic
3. Test with traffic generator
4. Verify graph spikes when error injected
