# Testing Sequence - Run These Commands

## Test 1: 503 Overload (SAT) - AI Should SUPPRESS Restart

```powershell
.\test_single_error.ps1 -ErrorType 503_overload
```

**Expected Behavior:**
- Site breaks with 503 error
- AI detects: "503 OVERLOAD | Overload condition"
- AI checks CPU: HIGH (>70%)
- AI decision: "SUPPRESS_RESTART_FOR_SCALING"
- Site does NOT auto-recover (correct - needs scaling, not restart)
- You manually clear fault at end

**Key Point:** This is the ONLY error type that should NOT restart!

---

## Test 2: 504 Timeout - AI Should RESTART

```powershell
.\test_single_error.ps1 -ErrorType 504_timeout
```

**Expected Behavior:**
- Site breaks with 504 error on payment
- AI detects: "504 TIMEOUT | Gateway Timeout"
- AI restarts container
- Health verification passes
- Site recovers automatically

---

## Test 3: 500 Crash - AI Should RESTART

```powershell
.\test_single_error.ps1 -ErrorType 500_crash
```

**Expected Behavior:**
- Site breaks with 500 error on checkout
- AI detects: "500 CRASH | Application crash"
- AI restarts container
- Health verification passes
- Site recovers automatically

---

## Summary After All Tests

**Expected Dashboard Metrics:**
- Total Detections: 4 (including the 503 Deadlock you already tested)
- Precision: 90-100%
- Recall: 90-100%
- Error Breakdown:
  - 500_CRASH: 1
  - 503_DEADLOCK: 1
  - 503_OVERLOAD: 1
  - 504_TIMEOUT: 1

---

## Start Now!

Run the first command:
```powershell
.\test_single_error.ps1 -ErrorType 503_overload
```

The script will guide you through each step interactively.
