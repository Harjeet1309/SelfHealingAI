# AI Faking Detection - Debug Report

## 🔴 CRITICAL FINDINGS

### Problem 1: Dynamic Threshold Self-Defeating Loop

**Status:** ❌ CONFIRMED - AI IS FAKING IT

**Evidence:**
```
Current State:
- Error Rate: 48.4% (CRITICAL!)
- AI Score: 0.000000 (not detecting!)
- AI Threshold: 22.481945 (way too high!)
- Static Threshold: 14.987963 (reasonable)
```

**Root Cause:**
The dynamic threshold calculation creates a feedback loop:

```python
# From inference.py line 287-291
if len(self.score_history) >= 20:
    dynamic_threshold = float(
        torch.tensor(list(self.score_history), dtype=torch.float32)
        .quantile(0.98).item()  # ← PROBLEM!
    )
```

**The Feedback Loop:**
1. Fault injected → Error rate spikes to 48%
2. AI calculates MSE scores from the faulty data
3. score_history fills with HIGH scores (because system is broken)
4. Dynamic threshold = 98th percentile of HIGH scores = 22.48
5. AI can't detect anomaly because threshold is now higher than the scores!

**This is like:**
- A smoke detector that raises its sensitivity threshold when it smells smoke
- A thermometer that recalibrates itself to call 100°F "normal" when you have a fever

### Problem 2: No Auto-Expiry Was Actually Helping!

**Irony:** The auto-expiry we removed was actually MASKING this problem by clearing faults before the dynamic threshold could rise too high.

**Now that we removed auto-expiry:**
- Faults stay active indefinitely
- AI keeps seeing high scores
- Dynamic threshold keeps rising
- AI becomes blind to the problem

## 📊 Actual Metrics vs AI Detection

### Prometheus Metrics (REAL):
```
http_requests_total{status="200"} = 201
http_requests_total{status="503"} = 200
http_errors_total{status="503"} = 200

Real Error Rate = 200/(200+201) = 49.9%
```

### AI Detection (FAKE):
```
AI Score: 0.000000
AI Status: HEALTHY
Threshold: 22.481945

AI thinks everything is fine! 🤦
```

## 🔍 Why This Happens

### The Score History Problem

The `score_history` deque stores recent MSE scores:
- When system is healthy: scores are low (0.001 - 0.01)
- When system is broken: scores are high (5.0 - 20.0)
- Dynamic threshold = 98th percentile of ALL recent scores

**Scenario:**
```
Time 0: System healthy, scores = [0.001, 0.002, 0.003, ...]
        Threshold = 0.98 percentile = 0.003 ✓

Time 1: Fault injected, scores = [15.2, 18.5, 19.1, ...]
        Threshold = 0.98 percentile = 19.0 ✗

Time 2: Still broken, scores = [20.1, 22.3, 21.5, ...]
        Threshold = 0.98 percentile = 22.3 ✗✗

AI is now blind!
```

## 🛠️ The Fix

### Option 1: Use Separate Clean/Anomaly Histories (RECOMMENDED)

Only use CLEAN samples (when no fault is active) to calculate the dynamic threshold:

```python
def _get_effective_ai_threshold(self):
    static_threshold = self.threshold * AI_THRESHOLD_MULTIPLIER
    
    # Only use clean samples for threshold calculation
    clean_scores = [s for s in self.score_history if s < static_threshold]
    
    if len(clean_scores) >= 20:
        dynamic_threshold = float(
            torch.tensor(clean_scores, dtype=torch.float32)
            .quantile(0.98).item()
        )
        return max(static_threshold, dynamic_threshold), dynamic_threshold
    
    return static_threshold, None
```

### Option 2: Disable Dynamic Threshold (SIMPLE)

Just use the static threshold:

```python
def _get_effective_ai_threshold(self):
    static_threshold = self.threshold * AI_THRESHOLD_MULTIPLIER
    return static_threshold, None  # No dynamic adjustment
```

### Option 3: Cap the Dynamic Threshold (BAND-AID)

Prevent the threshold from rising too high:

```python
def _get_effective_ai_threshold(self):
    static_threshold = self.threshold * AI_THRESHOLD_MULTIPLIER
    dynamic_threshold = None
    
    if len(self.score_history) >= 20:
        dynamic_threshold = float(
            torch.tensor(list(self.score_history), dtype=torch.float32)
            .quantile(0.98).item()
        )
        # Cap at 2x static threshold
        dynamic_threshold = min(dynamic_threshold, static_threshold * 2.0)
    
    if dynamic_threshold is None:
        return static_threshold, None
    
    return max(static_threshold, dynamic_threshold), dynamic_threshold
```

## 🎯 Recommended Solution

**Use Option 1** - Only calculate dynamic threshold from clean samples.

This ensures:
1. Threshold adapts to normal operational variance
2. Threshold doesn't rise during faults
3. AI remains sensitive to anomalies
4. No false positives from normal traffic spikes

## 📝 Additional Issues Found

### Issue 1: Traffic Pump Duration
The traffic pump runs for `duration_s` but we removed the expiry, so it keeps pumping errors even after the duration ends.

**Fix:** Stop the traffic pump when fault is cleared via reset.

### Issue 2: No Fault State Visibility
The dashboard doesn't show which faults are currently active.

**Fix:** Add a fault status indicator to the dashboard.

## ✅ Verification Steps

After applying fixes:

1. **Reset everything:**
   ```powershell
   .\reset_stats.ps1
   ```

2. **Inject a fault:**
   ```powershell
   Invoke-WebRequest -Method POST -Headers @{"Authorization"="Bearer changeme-local-dev"} -Uri http://localhost:8000/inject/503_deadlock -UseBasicParsing
   ```

3. **Watch for detection (should happen in 10-20 seconds):**
   ```powershell
   docker-compose logs -f remediation_engine | Select-String "ERROR DETECTED|REMEDIATION"
   ```

4. **Verify threshold stays reasonable:**
   - Should stay around 15-20, not jump to 22+
   - AI score should spike above threshold
   - Container should restart

5. **Verify recovery:**
   - Fault should be cleared after restart
   - Error rate should drop to 0%
   - AI score should return to near 0

## 🎓 Lessons Learned

1. **Dynamic thresholds need careful design** - Can't just use percentiles of all data
2. **Feedback loops are dangerous** - System behavior affects its own detection
3. **Auto-expiry had a hidden benefit** - Prevented threshold drift
4. **Always verify with real metrics** - Don't trust the AI's self-assessment

## 🚨 Current Status

**The AI is currently FAKING detection.**

It's not actually detecting the 48% error rate because the dynamic threshold has risen too high. The system needs the fixes above to work properly.

---

**Next Steps:**
1. Apply Option 1 fix (clean samples only)
2. Add fault state visibility
3. Fix traffic pump lifecycle
4. Re-test with fresh injection
5. Verify real detection and remediation
