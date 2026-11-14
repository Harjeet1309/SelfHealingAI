# SelfHealingAI - Complete Implementation Guide
## Critical Fixes & Improvements

**Date:** February 2026  
**Version:** V4.1 - Production Ready  
**Priority:** CRITICAL → HIGH → MEDIUM → LOW

---

## 🚨 EXECUTIVE SUMMARY

Your system has **critical bugs** preventing anomaly detection:

1. ❌ **Threshold 1000x too high** - AI can't detect 100% error rates
2. ❌ **Cooldown not enforced** - Allows rapid-fire restarts
3. ❌ **Corroboration disabled** - Triggers on zero errors
4. ❌ **Model predicts zeros** - Learned trivial solution

**Impact:** System shows "Normal operation" while error_rate=1.0 (100% failures)

**Fix Time:** 2-3 hours total  
**Risk Level:** LOW - All changes are configuration/code fixes

---

## 📋 PHASE-BY-PHASE IMPLEMENTATION PLAN

---

## 🔴 PHASE 1: CRITICAL FIXES (30 minutes)

### Fix #1: Threshold Multiplier - ROOT CAUSE

**File:** `remediation_engine/ai/inference.py`  
**Line:** 59  
**Current Value:** 4.0  
**New Value:** 1.5

```python
# Line 59 - CHANGE THIS:
AI_THRESHOLD_MULTIPLIER = _env_float("AI_THRESHOLD_MULTIPLIER", 1.5)
```

**Why This Matters:**
- Current: 0.0314 × 4.0 = **0.1256** threshold
- Normal MSE: **0.004** during healthy operation
- Anomaly MSE: **2.0-5.0** during faults
- **Problem:** Threshold was 30x higher than normal, making detection impossible

**Expected Impact:** AI will now detect anomalies with MSE > 0.047 instead of > 0.126

---

### Fix #2: Cooldown Enforcement - CRITICAL BUG

**File:** `remediation_engine/ai/inference.py`  
**Lines:** 383-400 (in the `run()` method)

**REPLACE the entire anomaly trigger block (lines 383-400) with:**

```python
                # ── Anomaly trigger ────────────────────────────────────
                should_trigger_ai = (
                    AI_ENABLE_REMEDIATION
                    and score > effective_threshold
                    and score > 0.05  # Ignore tiny noise
                    and not is_warming_up
                    and not is_in_cooldown  # ← KEY FIX: Actually block during cooldown
                    and (corroborated or not AI_REQUIRE_CORROBORATION)
                    and not rule_precedence
                )

                if should_trigger_ai:
                    self.anomaly_counter += 1
                    if self.anomaly_counter == ANOMALY_CONFIRMATION_COUNT:
                        result = self.decision_engine.determine_remediation("AI_ANOMALY_DETECTED")
                        # Reset counter only after successful remediation
                        self.anomaly_counter = 0
                else:
                    if not is_warming_up:
                        self.anomaly_counter = 0
```

**Why This Matters:**
- Old code checked `is_in_cooldown` but didn't use it to block triggers
- Result: Multiple restarts within seconds (logs show restarts at 13:52:45 and 13:52:48)
- **Fix:** Actually prevents triggering during cooldown period

**Expected Impact:** Maximum 1 restart per 60-second cooldown window

---

### Fix #3: Enable Corroboration by Default

**File:** `remediation_engine/ai/inference.py`  
**Line:** 58

```python
# Line 58 - CHANGE THIS:
AI_REQUIRE_CORROBORATION = _env_bool("AI_REQUIRE_CORROBORATION", True)
```

**Why This Matters:**
- When corroboration is disabled, AI triggers on any MSE spike (even with 0% error rate)
- Your logs show: "Corroborated: ✅ YES" even when error_rate=0.0
- **Fix:** Require both traffic AND errors before triggering

**Expected Impact:** No more false positives during low-traffic periods

---

### Fix #4: Add Minimum Error Rate Check

**File:** `remediation_engine/ai/inference.py`  
**Lines:** 249-255 (the `_is_corroborated` method)

**REPLACE the entire method with:**

```python
    def _is_corroborated(self, features: Dict[str, float]) -> bool:
        has_traffic = features.get("request_rate", 0.0) >= AI_MIN_REQUEST_RATE_FOR_SIGNAL
        has_failure = (
            features.get("error_rate", 0.0)   >= AI_MIN_ERROR_RATE_FOR_SIGNAL
            or features.get("p95_latency", 0.0) >= AI_MIN_P95_FOR_SIGNAL
        )
        
        # ADD THIS - Ensure errors are significant (at least 5%)
        error_rate = features.get("error_rate", 0.0)
        has_significant_errors = error_rate >= 0.05
        
        return has_traffic and has_failure and has_significant_errors
```

**Why This Matters:**
- Current logic: Triggers on 2% error rate (could be transient blip)
- New logic: Requires 5%+ error rate (real failure)
- **Your logs show:** error_rate=1.0 (100%) but still no detection because other checks fail

**Expected Impact:** Immune to transient network glitches, only triggers on real failures

---

### ✅ Phase 1 Validation

After making these 4 changes:

1. **Restart the remediation engine:**
   ```powershell
   docker-compose restart remediation_engine
   ```

2. **Watch the logs:**
   ```powershell
   docker-compose logs -f remediation_engine
   ```

3. **Look for these confirmation messages:**
   ```
   [V4] AI Engine initialized. input_size=5, threshold=0.0471
   [V4-AI] [ACTIVE] score=0.0043 thr=0.0471 dyn=n/a
   ```

4. **Inject a fault:**
   ```powershell
   curl -X POST http://localhost:8000/inject/500_checkout
   ```

5. **Expected result within 10-20 seconds:**
   ```
   🔴 error_rate: 0.8500
   🧠 MSE Score: 2.456789
   🔴 ANOMALY DETECTED!
   ⚡ TRIGGER REMEDIATION!
   ```

---

## 🟠 PHASE 2: DATA & MODEL IMPROVEMENTS (1 hour)

### Fix #5: Fix Metric Clipping Ranges

**File:** `remediation_engine/ai/synthetic_data_generator.py`  
**Lines:** 46-54 (the `_stack` function)

**REPLACE with:**

```python
def _stack(rr, er, lat, mem, conns):
    """Stack 5 feature arrays into shape (n, 5)."""
    return np.stack([
        _clip(rr,    0.0, 20.0),     # Increased from 15.0 (handles traffic spikes)
        _clip(er,    0.0,  1.0),      # Keep as-is (error rate is 0-1)
        _clip(lat,   0.01, 20.0),    # Increased from 15.0 (handles timeout scenarios)
        _clip(mem,   50.0, 1024.0),  # Changed from 20.0 (realistic min 50MB, not 20MB)
        _clip(conns, 0.0, 300.0),    # Increased from 200.0 (handles high load)
    ], axis=1)
```

**Why This Matters:**
- Your current model clips memory at 20MB minimum, but real processes use 200-400MB
- Model learned that "memory=0" is normal, causing it to ignore real memory patterns
- **Fix:** Use realistic ranges based on actual production metrics

**Expected Impact:** Model will learn realistic patterns, not artificial clipped values

---

### Fix #6: Regenerate Synthetic Dataset

**Run this command:**

```powershell
cd C:\Users\gudde\Desktop\SelfHealingAI\remediation_engine\ai
python synthetic_data_generator.py
```

**Expected output:**
```
[DATAGEN] Segment breakdown:
  Segment 01: 523 timesteps  shape=(523, 5)
  Segment 02: 300 timesteps  shape=(300, 5)
  ...
[DATAGEN] Total: 8,234 timesteps x 5 features
  request_rate         min=0.015  max=12.345  mean=1.234
  error_rate           min=0.001  max=0.998  mean=0.089
  p95_latency          min=0.010  max=8.765  mean=0.456
  memory_mb            min=50.123  max=512.345  mean=187.654
  active_conns         min=0.000  max=156.789  mean=23.456

[DATAGEN] Saved to ./synthetic_dataset.npy
```

**Verify the file exists:**
```powershell
ls ./synthetic_dataset.npy
# Should be ~300-500KB
```

---

### Fix #7: Retrain LSTM Model

**Run this command:**

```powershell
cd C:\Users\gudde\Desktop\SelfHealingAI\remediation_engine\ai
python train.py --verbose
```

**Watch for these success indicators:**

```
[TRAIN] Epoch 1/200: train_loss=0.0234, val_loss=0.0245
[TRAIN] Epoch 50/200: train_loss=0.0089, val_loss=0.0092
[TRAIN] Epoch 100/200: train_loss=0.0045, val_loss=0.0048
[TRAIN] ✅ Best model saved at epoch 113 (val_loss=0.0043)
[TRAIN] Computing anomaly threshold...
[TRAIN] Static threshold (p99): 0.0314
[TRAIN] ✅ Model training complete!
```

**Critical Checks:**
- ✅ Final validation loss < 0.01
- ✅ Threshold in range 0.02 - 0.05
- ✅ Model file size: ~500KB - 2MB

**If training fails or loss > 0.1:**
- Your data has issues (likely all zeros or NaN values)
- Re-run Fix #6 and check the dataset statistics

---

### ✅ Phase 2 Validation

1. **Check new model files:**
   ```powershell
   ls ../../models/
   # lstm_model.pt should have recent timestamp
   # threshold.json should show threshold ~0.047
   ```

2. **Inspect threshold.json:**
   ```powershell
   cat ../../models/threshold.json | ConvertFrom-Json | Format-List
   ```
   
   **Expected content:**
   ```json
   {
     "threshold": 0.0471,
     "static_threshold": 0.0314,
     "live_threshold": null,
     "fine_tune_count": 0
   }
   ```

3. **Restart remediation engine:**
   ```powershell
   docker-compose restart remediation_engine
   ```

4. **Run debugger:**
   ```powershell
   python ../../debug_inference_live.py
   ```

5. **Wait 3 minutes, then check:**
   ```
   🧠 AI ANOMALY DETECTION:
     MSE Score: 0.004320
     Static Threshold: 0.047100  ← Should match threshold.json
     Effective Threshold: 0.047100
     
     🟢 Normal operation
   ```

---

## 🟡 PHASE 3: METRICS COLLECTION FIXES (30 minutes)

### Fix #8: Debug Memory & Connection Metrics

**File:** `api_service/app/middleware.py`

**ADD debug logging after lines 36-46:**

```python
        # --- Update system-level metrics ---
        # Memory: RSS in MB
        try:
            mem_mb = _PROCESS.memory_info().rss / (1024 * 1024)
            MEMORY_USAGE_MB.set(mem_mb)
            # DEBUG PRINT - remove after testing
            print(f"[METRICS] Memory: {mem_mb:.1f}MB")
        except Exception as e:
            print(f"[METRICS ERROR] Memory: {e}")

        # Active TCP connections held by this process
        try:
            conns = len(_PROCESS.net_connections(kind="tcp"))
            ACTIVE_CONNECTIONS.set(conns)
            # DEBUG PRINT - remove after testing
            print(f"[METRICS] Connections: {conns}")
        except Exception as e:
            print(f"[METRICS ERROR] Connections: {e}")
```

**Why This Matters:**
- Your debugger shows: `memory_mb: 0.0000`, `active_connections: 0.0000`
- These should be: 200-400MB memory, 10-50 connections
- Zeros mean either: psutil can't access process info, or metrics aren't being exposed

**Expected output in logs:**
```
[METRICS] Memory: 245.3MB
[METRICS] Connections: 18
```

**If you see errors:**
- `[METRICS ERROR] Memory: Access denied` → Run Docker with `--privileged` flag
- `[METRICS ERROR] Connections: No TCP connections` → Normal for idle service

---

### Fix #9: Verify Prometheus Scraping

**Test Prometheus directly:**

```powershell
# Test 1: Check if Prometheus is scraping api_service
curl "http://localhost:9090/api/v1/targets" | ConvertFrom-Json | ConvertTo-Json -Depth 5

# Expected output:
# {
#   "data": {
#     "activeTargets": [
#       {
#         "labels": { "job": "api_service" },
#         "health": "up"
#       }
#     ]
#   }
# }

# Test 2: Query memory metric directly
curl "http://localhost:9090/api/v1/query?query=process_memory_mb" | ConvertFrom-Json | ConvertTo-Json -Depth 5

# Expected: Non-zero value like 245.6
# If empty []: MetricsMiddleware isn't exposing the metric
```

**If Prometheus returns empty results:**

1. **Check if api_service is exposing metrics:**
   ```powershell
   curl http://localhost:8000/metrics
   ```
   
   Look for these lines in output:
   ```
   process_memory_mb 245.6
   process_active_connections 18.0
   ```

2. **If metrics are missing:**
   - Restart api_service: `docker-compose restart api_service`
   - Check middleware is installed in `main.py` line 11:
     ```python
     app.add_middleware(MetricsMiddleware)
     ```

---

## 🟢 PHASE 4: REAL DATA EXTRACTION (Optional - Future Enhancement)

### Fix #10: Extract Real Production Telemetry

**Create new file:** `extract_real_telemetry.py`

```python
"""
Extract real Prometheus data for training.
Run this while injecting faults to capture actual failure patterns.
"""

import requests
import numpy as np
from datetime import datetime, timedelta
import os

def extract_prometheus_data(minutes=60):
    prometheus_url = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(minutes=minutes)
    
    queries = {
        'request_rate': 'sum(rate(http_requests_total[30s]))',
        'error_rate': '''
            sum(rate(http_requests_total{status!="200"}[30s])) 
            / sum(rate(http_requests_total[30s]))
        ''',
        'p95_latency': '''
            histogram_quantile(0.95, 
                sum(rate(http_request_duration_seconds_bucket[30s])) by (le)
            )
        ''',
        'memory_mb': 'process_memory_mb',
        'active_connections': 'process_active_connections'
    }
    
    results = {}
    for name, query in queries.items():
        try:
            resp = requests.get(
                f"{prometheus_url}/api/v1/query_range",
                params={
                    'query': query,
                    'start': start_time.isoformat() + 'Z',
                    'end': end_time.isoformat() + 'Z',
                    'step': '5s'
                },
                timeout=10
            )
            data = resp.json()['data']['result']
            if data:
                values = [float(v[1]) for v in data[0]['values']]
                results[name] = values
                print(f"✅ {name}: {len(values)} points")
            else:
                print(f"⚠️  {name}: No data")
                results[name] = []
        except Exception as e:
            print(f"❌ {name}: {e}")
            results[name] = []
    
    # Align lengths
    min_len = min(len(v) for v in results.values()) if results.values() else 0
    if min_len == 0:
        print("❌ No data collected!")
        return None
    
    # Build array
    data = np.stack([results[name][:min_len] for name in [
        'request_rate', 'error_rate', 'p95_latency', 'memory_mb', 'active_connections'
    ]], axis=1)
    
    print(f"\n✅ Extracted {data.shape[0]} timesteps!")
    save_path = "./remediation_engine/ai/real_telemetry.npy"
    np.save(save_path, data)
    print(f"💾 Saved to {save_path}")
    
    return data

if __name__ == "__main__":
    print("🔍 Extracting real Prometheus telemetry...")
    data = extract_prometheus_data(minutes=60)
```

**How to use:**

1. **Start full stack:**
   ```powershell
   docker-compose up -d
   ```

2. **Run extraction script:**
   ```powershell
   python extract_real_telemetry.py
   ```

3. **While it's running, inject faults:**
   ```powershell
   # Every 2 minutes, inject a different fault
   curl -X POST http://localhost:8000/inject/500_checkout
   Start-Sleep -Seconds 120
   
   curl -X POST http://localhost:8000/inject/503_deadlock
   Start-Sleep -Seconds 120
   
   curl -X POST http://localhost:8000/inject/504_timeout
   ```

4. **Result:** File with real failure patterns for training

---

## 📊 EXPECTED RESULTS - BEFORE vs AFTER

### ❌ BEFORE FIXES (Current State):

```
================================================================================
[12:34:27] Iteration #46
📈 LATEST METRICS FROM PROMETHEUS:
  ⚪ request_rate        : 0.2009
  🔴 error_rate          : 1.0000    ← 100% FAILURES!
  ⚪ p95_latency         : 0.0425
  ⚪ memory_mb           : 0.0000    ← Wrong!
  ⚪ active_connections  : 0.0000    ← Wrong!

🧠 AI ANOMALY DETECTION:
  MSE Score:           0.000000    ← Impossible!
  Static Threshold:    5.592787    ← Way too high!
  
  🟢 Normal operation     ← SYSTEM IS LYING!
     Score (0.0000) <= Threshold (5.5928)

🛠️  REMEDIATION STATUS:
  ✅ No action needed - system healthy    ← WRONG!
```

### ✅ AFTER FIXES (Expected):

```
================================================================================
[12:40:15] Iteration #12
📈 LATEST METRICS FROM PROMETHEUS:
  ⚪ request_rate        : 2.3400
  🔴 error_rate          : 0.8500    ← High error rate detected
  🟠 p95_latency         : 2.3400    ← Latency spike
  ⚪ memory_mb           : 248.1000   ← Real value!
  ⚪ active_connections  : 18.0000    ← Real value!

🧠 AI ANOMALY DETECTION:
  MSE Score:           2.456789    ← Detects anomaly!
  Static Threshold:    0.047100    ← Reasonable threshold
  Dynamic Threshold:   0.052341
  
  🔴 ANOMALY DETECTED!    ← CAUGHT IT!
     Score (2.4568) > Threshold (0.0471)

🔍 CORROBORATION CHECK:
  Has Traffic:      ✅ (rate=2.340)
  Has Errors:       ✅ (rate=0.850)
  High Latency:     ✅ (latency=2.34s)
  Corroborated:     ✅ YES

🛠️  REMEDIATION STATUS:
  ⚡ TRIGGER REMEDIATION!
     → Action: Restart api_service container
     → Reason: AI detected behavioral anomaly
```

---

## 🧪 COMPLETE TESTING WORKFLOW

### Step 1: Apply All Phase 1 Fixes
- Edit `inference.py` (4 changes)
- Save and commit changes

### Step 2: Restart Services
```powershell
docker-compose down
docker-compose up -d
```

### Step 3: Wait for Warmup (3 minutes)
```powershell
docker-compose logs -f remediation_engine
# Wait until you see: "[V4] Autonomous Monitoring Loop Active"
```

### Step 4: Run Debugger
```powershell
python debug_inference_live.py
```

### Step 5: Inject Faults (after 3-minute warmup)

**Test Case 1: 500 Crash**
```powershell
# Terminal 2 - Inject fault
curl -X POST http://localhost:8000/inject/500_checkout

# Generate error traffic
for ($i=1; $i -le 30; $i++) { 
    curl -s -X POST http://localhost:8000/checkout 
    Start-Sleep -Milliseconds 100 
}
```

**Expected in debugger (within 10-20 seconds):**
```
🔴 error_rate: 0.XXXX
🔴 ANOMALY DETECTED!
⚡ TRIGGER REMEDIATION!
```

**Test Case 2: 503 Deadlock**
```powershell
curl -X POST http://localhost:8000/inject/503_deadlock
for ($i=1; $i -le 30; $i++) { 
    curl -s -X POST http://localhost:8000/cart/add 
    Start-Sleep -Milliseconds 100 
}
```

**Expected:**
```
🔴 error_rate: 0.XXXX
🔴 ANOMALY DETECTED!
DIAGNOSIS: Deadlock recognized (Low CPU)
🛠️ ACTION: Restarting api_service
```

**Test Case 3: 503 Overload (Should SUPPRESS)**
```powershell
curl -X POST http://localhost:8000/inject/503_overload
for ($i=1; $i -le 100; $i++) { 
    curl -s http://localhost:8000/health 
    Start-Sleep -Milliseconds 50 
}
```

**Expected:**
```
🔴 error_rate: 0.XXXX
🟠 CPU: 85.2% (HIGH)
🛠️ DIAGNOSIS: Overload condition (High CPU)
🛠️ ACTION: SUPPRESS RESTART (protects users!)
```

---

## 🎯 SUCCESS CRITERIA

Your system is working correctly when:

1. ✅ **Normal Operation:**
   - MSE < 0.05
   - error_rate < 0.02
   - No remediation triggered

2. ✅ **Fault Detection (500/503/504):**
   - Detects within 10-20 seconds
   - MSE spikes to 1.0-5.0
   - Triggers restart (unless overload)

3. ✅ **Smart Suppression (Overload):**
   - Detects high CPU (>70%)
   - Suppresses restart
   - Logs "Protects shopper sessions"

4. ✅ **Cooldown Enforcement:**
   - Maximum 1 restart per 60 seconds
   - No rapid-fire restarts

5. ✅ **Real Metrics:**
   - memory_mb: 200-400 (not 0.0)
   - active_connections: 10-50 (not 0.0)

---

## 🐛 TROUBLESHOOTING GUIDE

### Problem: Still seeing MSE=0.0000

**Diagnosis:** Model learned to predict zeros

**Solution:**
1. Delete old model: `rm ./models/lstm_model.pt`
2. Regenerate dataset with Fix #6
3. Retrain with Fix #7
4. Ensure training loss < 0.01

---

### Problem: Threshold still too high (>1.0)

**Diagnosis:** Old threshold.json cached

**Solution:**
```powershell
# Delete old threshold
rm ./models/threshold.json

# Force regeneration by restarting
docker-compose restart remediation_engine

# Or manually set in threshold.json:
{
  "threshold": 0.0471,
  "static_threshold": 0.0314
}
```

---

### Problem: Cooldown not working

**Diagnosis:** Fix #2 not applied correctly

**Check:**
```powershell
# Search for the bug pattern
grep -n "is_in_cooldown" ./remediation_engine/ai/inference.py

# Should appear in should_trigger_ai check
# If it appears elsewhere, fix wasn't applied
```

---

### Problem: No detection even after fixes

**Diagnosis:** Multiple possible causes

**Debug checklist:**
1. ✅ Check threshold: `cat ./models/threshold.json`
2. ✅ Check MSE in debugger output
3. ✅ Check error_rate in debugger
4. ✅ Verify corroboration is enabled: `grep AI_REQUIRE_CORROBORATION inference.py`
5. ✅ Verify minimum error check added
6. ✅ Restart remediation_engine

---

## 📝 CONFIGURATION CHEAT SHEET

### Optimal Environment Variables

```yaml
# docker-compose.yml - remediation_engine section

environment:
  # Core AI settings
  - AI_THRESHOLD_MULTIPLIER=1.5          # Critical fix
  - AI_REQUIRE_CORROBORATION=true         # Critical fix
  - AI_MIN_ERROR_RATE_FOR_SIGNAL=0.05    # New minimum
  - AI_WARMUP_SECONDS=90
  
  # Cooldown & safety
  - REMEDIATION_COOLDOWN_SECONDS=60
  - HIGH_CPU_THRESHOLD=70
  - HEALTH_CHECK_ENABLED=true
  - HEALTH_CHECK_RETRIES=10
  
  # Online learning
  - ONLINE_FINE_TUNE_TRIGGER=500
  - THRESHOLD_PERSIST_INTERVAL=100
```

---

## 📊 PERFORMANCE METRICS TO TRACK

After all fixes, monitor these KPIs:

| Metric | Target | Current (Before) | After Fix |
|--------|--------|------------------|-----------|
| **Precision** | >85% | 87.5% | >90% |
| **Recall** | >80% | Unknown | >85% |
| **Detection Time** | <20s | Not detecting | 10-20s |
| **False Positives** | <5% | 2/16 = 12.5% | <5% |
| **Cooldown Violations** | 0 | Multiple | 0 |

---

## 🚀 NEXT STEPS AFTER FIXES

Once Phase 1-3 are complete and tests pass:

1. **Monitor for 24 hours** - Watch for edge cases
2. **Collect real telemetry** - Run Fix #10
3. **Retrain on real data** - Hybrid approach (Fix #9)
4. **Enable online learning** - Fine-tune in production
5. **Add more chaos scenarios** - Expand test coverage

---

## 📞 SUPPORT

If you encounter issues not covered here:

1. Check logs: `docker-compose logs -f remediation_engine`
2. Inspect metrics: `curl http://localhost:9090/api/v1/query?query=up`
3. Validate config: `python validate_system.py` (create this script)
4. Review this guide Section-by-Section

---

**Document Version:** 1.0  
**Last Updated:** February 2026  
**Maintained By:** Development Team
