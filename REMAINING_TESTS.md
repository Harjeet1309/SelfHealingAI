# Remaining Tests - Quick Guide

## ✅ Test 1: 503 Overload - PASSED!
- CPU: 80-84% (high)
- AI Decision: SUPPRESS restart
- Behavior: Correct! (overload needs scaling, not restart)

---

## 🔄 Test 2: 504 Timeout - RUN NOW

```powershell
.\test_single_error.ps1 -ErrorType 504_timeout
```

### What to Expect:
1. **Dashboard**: Click "Execute Timeout" button
2. **Shopping Site**: Go through checkout → Try payment
3. **Error**: Should see 504 Gateway Timeout
4. **AI Detection** (10-20 seconds):
   - 🔴 ERROR DETECTED: 504 TIMEOUT | Gateway Timeout
   - ⚡ REMEDIATION: Restarting api_service container
   - POST-REMEDIATION: Waiting for container to stabilize...
   - POST-REMEDIATION: Health VERIFIED
   - ✅ RECOVERY: Service restored successfully
5. **Site Recovery**: Try payment again - should work!

### Expected Timeline:
- Detection: 10-20 seconds
- Restart + Health Check: 15-20 seconds
- Total: ~30-40 seconds

---

## 🔄 Test 3: 500 Crash - RUN AFTER TEST 2

```powershell
.\test_single_error.ps1 -ErrorType 500_crash
```

### What to Expect:
1. **Dashboard**: Click "Execute App Crash" button
2. **Shopping Site**: Add to cart → Checkout → Click "Complete Acquisition"
3. **Error**: Should see 500 Internal Server Error
4. **AI Detection** (5-15 seconds):
   - 🔴 ERROR DETECTED: 500 CRASH | Localized application crash
   - ⚡ REMEDIATION: Restarting api_service container
   - POST-REMEDIATION: Health VERIFIED
   - ✅ RECOVERY: Service restored successfully
5. **Site Recovery**: Try checkout again - should work!

### Expected Timeline:
- Detection: 5-15 seconds (fastest - crash is immediate)
- Restart + Health Check: 15-20 seconds
- Total: ~25-35 seconds

---

## Key Differences Between Error Types

| Error Type | CPU | AI Decision | Why |
|------------|-----|-------------|-----|
| 503 Deadlock | Low (<30%) | RESTART | Threads blocked |
| 503 Overload | High (>70%) | SUPPRESS | Need to scale |
| 504 Timeout | Normal | RESTART | Clear stuck connections |
| 500 Crash | Varies | RESTART | App crashed |

---

## After All Tests Complete

Check your dashboard metrics:
- **Total Detections**: 4
- **Precision**: 90-100%
- **Recall**: 90-100%
- **Error Breakdown**:
  - 500_CRASH: 1
  - 503_DEADLOCK: 1
  - 503_OVERLOAD: 1
  - 504_TIMEOUT: 1

---

## Start Test 2 Now!

```powershell
.\test_single_error.ps1 -ErrorType 504_timeout
```

The script will guide you through each step.
