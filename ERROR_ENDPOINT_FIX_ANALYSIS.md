# Error Endpoint Fix - Complete Analysis

## 🔴 PROBLEM IDENTIFIED

The user reported that errors are occurring at the wrong endpoints. Specifically:
- **500 checkout errors** are showing up at "Acquire Item" (`/cart/add`) instead of only at checkout
- **All errors seem to be concentrated at `/cart/add`** in the metrics

## 🔍 ROOT CAUSE ANALYSIS

After analyzing the code, I found TWO separate issues:

### Issue 1: Traffic Pump Metrics (CONFIRMED BUG)
The traffic pump sends fake metrics to Prometheus to simulate error spikes. Currently, many faults are incorrectly pumping ALL their metrics to `/cart/add`:

```python
_FAULT_METRIC_MAP = {
    "cart":               ("/cart/add",  "503"),   # ✅ Correct
    "checkout":           ("/checkout",  "500"),   # ✅ Correct
    "payment":            ("/payment",   "504"),   # ✅ Correct
    "overload":           ("/cart/add",  "503"),   # ⚠️  Correct (but CPU is system-wide)
    "db_latency":         ("/cart/add",  "503"),   # ❌ WRONG - affects 3 endpoints
    "lock_contention":    ("/cart/add",  "503"),   # ❌ WRONG - affects 2 endpoints
    "dependency_timeout": ("/payment",   "504"),   # ✅ Correct
    "dependency_reset":   ("/cart/add",  "503"),   # ❌ WRONG - affects 3 endpoints
    "security":           ("/checkout",  "429"),   # ✅ Correct
}
```

**Impact**: Prometheus sees ALL errors at `/cart/add`, even though real errors happen at multiple endpoints.

### Issue 2: Actual Error Logic (NEEDS VERIFICATION)
The actual HTTP exceptions are thrown at the correct endpoints:
- 500 checkout error: ONLY thrown in `/checkout` endpoint ✅
- 503 deadlock: ONLY thrown in `/cart/add` endpoint ✅
- 504 timeout: ONLY thrown in `/payment` endpoint ✅

**BUT** cross-cutting faults (db_latency, lock_contention, dependency_reset) CAN throw errors at multiple endpoints because they're called from multiple places.

---

## 📊 CORRECT ERROR-TO-ENDPOINT MAPPING

### Primary Faults (Should be isolated):

| Fault Injection | Fault Key | Error Code | Should ONLY Occur At | Currently Occurs At | Status |
|----------------|-----------|------------|---------------------|-------------------|--------|
| `500_checkout` | checkout | 500 | `/checkout` | `/checkout` | ✅ Correct |
| `503_deadlock` | cart | 503 | `/cart/add` | `/cart/add` | ✅ Correct |
| `503_overload` | overload | 503 | `/cart/add` | `/cart/add` | ✅ Correct |
| `504_timeout` | payment | 504 | `/payment` | `/payment` | ✅ Correct |
| `429_bot` | security | 429 | `/checkout` | `/checkout` | ✅ Correct |

### Cross-Cutting Faults (Legitimately affect multiple endpoints):

| Fault Injection | Fault Key | Error Code | Should Occur At | Traffic Pump Sends To | Status |
|----------------|-----------|------------|----------------|---------------------|--------|
| `db_latency` | db_latency | 503 | `/cart/add`, `/checkout`, `/payment` | `/cart/add` only | ❌ WRONG |
| `lock_contention` | lock_contention | 503 | `/cart/add`, `/checkout` | `/cart/add` only | ❌ WRONG |
| `dependency_reset` | dependency_reset | 503 | `/cart/add`, `/checkout`, `/payment` | `/cart/add` only | ❌ WRONG |
| `dependency_timeout` | dependency_timeout | 504 | `/payment` | `/payment` | ✅ Correct |

---

## ✅ THE FIX

### Option 1: Simple Fix (Recommended for Demo)
**Remove cross-cutting faults from traffic pump** - Only pump metrics for the 5 main error types:
- 500 checkout → `/checkout`
- 503 deadlock → `/cart/add`
- 503 overload → `/cart/add`
- 504 timeout → `/payment`
- 429 bot → `/checkout`

This ensures each error type has a clear, isolated endpoint for demonstration purposes.

### Option 2: Advanced Fix (More Realistic)
**Implement multi-endpoint traffic pump** - For cross-cutting faults, pump metrics to ALL affected endpoints:
- `db_latency` → pump to `/cart/add`, `/checkout`, `/payment`
- `lock_contention` → pump to `/cart/add`, `/checkout`
- `dependency_reset` → pump to `/cart/add`, `/checkout`, `/payment`

This is more realistic but requires refactoring the `_start_traffic_pump()` function.

---

## 🎯 RECOMMENDED SOLUTION

For your demo/presentation, I recommend **Option 1** - focus on the 5 main error types and ensure they're cleanly isolated:

1. **500 Checkout Crash** - ONLY at `/checkout` endpoint
2. **503 Deadlock** - ONLY at `/cart/add` endpoint
3. **503 Overload** - ONLY at `/cart/add` endpoint (but CPU affects whole system)
4. **504 Timeout** - ONLY at `/payment` endpoint
5. **429 Bot Attack** - ONLY at `/checkout` endpoint

This makes the demo clearer and easier to understand. The cross-cutting faults (db_latency, lock_contention, etc.) can be disabled or removed from the demo flow.

---

## 🔧 IMPLEMENTATION STEPS

### Step 1: Verify Current Behavior
Run this test to see where errors actually appear:

```powershell
# Test 500 checkout error
curl -X POST "http://localhost:8000/inject/500_checkout" -H "Authorization: Bearer changeme-local-dev"

# Try "Acquire Item" - should work fine (no error)
curl -X POST "http://localhost:8000/cart/add"

# Try "Complete Acquisition" - should fail with 500
curl -X POST "http://localhost:8000/checkout"

# Check Prometheus metrics
curl "http://localhost:8000/metrics" | grep "http_errors_total"
```

### Step 2: Fix Traffic Pump (if needed)
If metrics are showing up at wrong endpoints, update `_FAULT_METRIC_MAP` to ensure each fault pumps to the correct endpoint.

### Step 3: Simplify for Demo
Consider removing or disabling cross-cutting faults:
- `db_latency`
- `lock_contention`
- `dependency_reset`

Focus on the 5 main error types for a cleaner demo.

---

## 📝 NEXT STEPS

1. **User confirms the exact issue**: Is it the traffic pump metrics or actual errors?
2. **Apply the fix**: Update `_FAULT_METRIC_MAP` or refactor traffic pump
3. **Test thoroughly**: Verify each error only appears at its designated endpoint
4. **Update documentation**: Ensure all docs reflect the correct error-to-endpoint mapping

---

## 🎓 KEY TAKEAWAY

The code is mostly correct - errors ARE thrown at the right endpoints. The issue is that the **traffic pump** (which generates fake metrics for Prometheus) is sending metrics to the wrong endpoints, making it LOOK like all errors happen at `/cart/add`.

**Fix**: Ensure traffic pump metrics match where real errors actually occur.
