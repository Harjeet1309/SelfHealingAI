# Test All Error Types - Quick Guide

## System is Ready! ✅

All services are running and the fixes are applied.

---

## Automated Test (Recommended)

Run this script to test all 4 error types automatically:

```powershell
.\test_all_error_types.ps1
```

**What it does**:
- Tests 503 Deadlock → Expects RESTART
- Tests 503 Overload → Expects SUPPRESS  
- Tests 504 Timeout → Expects RESTART
- Tests 500 Crash → Expects RESTART
- Shows pass/fail for each
- Provides detailed summary

**Time**: ~5-6 minutes total

---

## Manual Test (If You Prefer)

### Test 1: 503 Deadlock (IDLE)
1. Dashboard → Click **"Execute Deadlock"**
2. Shopping Site → Click "Acquire Item"
3. Should get 503 error
4. Wait 30-45 seconds
5. Watch Dashboard logs for:
   - 🔴 ERROR DETECTED: 503 DEADLOCK
   - ⚡ REMEDIATION: Restarting container
   - ✅ RECOVERY: Service restored
6. Site should work again

---

### Test 2: 503 Overload (SAT)
1. Dashboard → Click **"Execute Overload"**
2. Shopping Site → Try any action
3. Should get 503 error
4. Wait 30 seconds
5. Watch Dashboard logs for:
   - 🔴 ERROR DETECTED: 503 OVERLOAD
   - ⚡ REMEDIATION: Suppressing restart (High CPU)
   - ℹ️  ACTION: SUPPRESS_RESTART_FOR_SCALING
6. **Manual reset needed**:
   ```powershell
   curl -X POST "http://localhost:8000/inject/reset?target=all" `
     -H "Authorization: Bearer changeme-local-dev"
   ```

---

### Test 3: 504 Timeout
1. Dashboard → Click **"Execute Timeout"**
2. Shopping Site → Go through checkout flow to payment
3. Should get 504 error
4. Wait 30-45 seconds
5. Watch Dashboard logs for:
   - 🔴 ERROR DETECTED: 504 TIMEOUT
   - ⚡ REMEDIATION: Restarting container
   - ✅ RECOVERY: Service restored
6. Site should work again

---

### Test 4: 500 Crash
1. Dashboard → Click **"Execute App Crash"**
2. Shopping Site → Try checkout
3. Should get 500 error
4. Wait 30-45 seconds
5. Watch Dashboard logs for:
   - 🔴 ERROR DETECTED: 500 CRASH
   - ⚡ REMEDIATION: Restarting container
   - ✅ RECOVERY: Service restored
6. Site should work again

---

## Key Differences

| Error | CPU | Action | Why |
|-------|-----|--------|-----|
| 503 Deadlock | Low | Restart | Threads blocked |
| 503 Overload | High | Suppress | Need to scale |
| 504 Timeout | Normal | Restart | Clear connections |
| 500 Crash | Varies | Restart | App crashed |

---

## Expected Results

After testing all 4 error types:

**Dashboard Metrics**:
- Total Detections: 4
- Precision: 90-100%
- Recall: 90-100%
- Error Breakdown: 1 of each type

**Action Pulse Logs**:
- Should show complete cycle for each error
- Detection → Remediation → Recovery (or Suppress for overload)

---

## What Makes This REAL Self-Healing

✅ **Faults persist** until AI clears them (no auto-expiry)
✅ **Site stays broken** until AI acts (no fake recovery)
✅ **Health verification** confirms restart worked
✅ **Smart decisions** (restart vs suppress based on CPU)
✅ **Complete logging** (every step visible in dashboard)

---

## Troubleshooting

### If health checks fail:
- Container needs 8 seconds to initialize
- Check: `docker logs api_service --tail 20`

### If faults don't clear:
- Check: `docker exec api_service cat /app/logs/fault_state.json`
- Should be `{}` after successful remediation

### If AI doesn't detect:
- Check: `docker logs remediation_engine --tail 30`
- Should see "MONITORING PULSE" every 5 seconds

---

## Ready to Test!

Choose your method:
- **Automated**: `.\test_all_error_types.ps1`
- **Manual**: Follow steps above for each error type

Both will verify that your self-healing AI works correctly across all error scenarios!
