# Error Types Reference Guide

## Overview

Your self-healing AI system handles 4 main error types. Each has different characteristics and remediation strategies.

---

## 1. 503 Deadlock (IDLE)

### Characteristics:
- **Status Code**: 503 Service Unavailable
- **Root Cause**: Application deadlock (threads waiting on each other)
- **CPU Usage**: LOW (threads are blocked, not consuming CPU)
- **Latency**: HIGH (requests hang before timing out)

### Dashboard Button:
**"Execute Deadlock"** - 503 (IDLE)

### Test Endpoint:
`POST /cart/add`

### AI Detection:
```
Rule Layer: 503 spike detected
AI Layer: Anomaly + low CPU
Diagnosis: "Deadlock recognized. Restarting."
```

### Expected Remediation:
✅ **RESTART** container (deadlock can only be fixed by restart)

### Logs You'll See:
```
🔴 ERROR DETECTED: 503 DEADLOCK/OVERLOAD | Deadlock recognized
⚡ REMEDIATION: Restarting api_service container
POST-REMEDIATION: Waiting for container to stabilize...
POST-REMEDIATION: Health VERIFIED on attempt 2-3
✅ RECOVERY: Service restored successfully
```

### Timeline:
- Detection: 5-15 seconds
- Restart: 8 seconds wait
- Health check: 6-12 seconds (2-4 attempts)
- **Total**: ~30-45 seconds

---

## 2. 503 Overload (SAT)

### Characteristics:
- **Status Code**: 503 Service Unavailable
- **Root Cause**: CPU saturation (too much traffic/load)
- **CPU Usage**: HIGH (>70% threshold)
- **Latency**: HIGH (slow processing due to CPU contention)

### Dashboard Button:
**"Execute Overload"** - 503 (SAT)

### Test Endpoint:
`GET /health`

### AI Detection:
```
Rule Layer: 503 spike detected
AI Layer: Anomaly + HIGH CPU
Diagnosis: "Overload condition. Suppressing restart."
```

### Expected Remediation:
⚠️ **SUPPRESS** restart (overload needs scaling, not restart)

### Logs You'll See:
```
🔴 ERROR DETECTED: 503 DEADLOCK/OVERLOAD | Overload condition
⚡ REMEDIATION: Suppressing restart (High CPU detected)
ℹ️  ACTION: SUPPRESS_RESTART_FOR_SCALING
```

### Key Difference from Deadlock:
| Metric | Deadlock | Overload |
|--------|----------|----------|
| CPU | Low (<30%) | High (>70%) |
| Action | Restart | Suppress |
| Reason | Threads blocked | Too much load |
| Solution | Restart | Scale horizontally |

### Manual Recovery:
Since overload is suppressed, you need to manually reset:
```powershell
curl -X POST "http://localhost:8000/inject/reset?target=all" `
  -H "Authorization: Bearer changeme-local-dev"
```

---

## 3. 504 Gateway Timeout

### Characteristics:
- **Status Code**: 504 Gateway Timeout
- **Root Cause**: Slow dependency (database, payment gateway, etc.)
- **CPU Usage**: NORMAL
- **Latency**: VERY HIGH (requests timeout waiting for dependency)

### Dashboard Button:
**"Execute Timeout"** - 504 (DB)

### Test Endpoint:
`POST /payment`

### AI Detection:
```
Rule Layer: 504 spike detected
AI Layer: Anomaly + high latency
Diagnosis: "Gateway Timeout. Clearing connections."
```

### Expected Remediation:
✅ **RESTART** container (clears stuck connections)

### Logs You'll See:
```
🔴 ERROR DETECTED: 504 TIMEOUT | Gateway Timeout
⚡ REMEDIATION: Restarting api_service container | Reason: 504 Timeout Cleanup
POST-REMEDIATION: Health VERIFIED
✅ RECOVERY: Service restored successfully
```

### Timeline:
Similar to 503 Deadlock (~30-45 seconds)

---

## 4. 500 Internal Server Error (Crash)

### Characteristics:
- **Status Code**: 500 Internal Server Error
- **Root Cause**: Application crash (unhandled exception, OOM, etc.)
- **CPU Usage**: VARIES
- **Latency**: IMMEDIATE (fails fast)

### Dashboard Button:
**"Execute App Crash"** - 500

### Test Endpoint:
`POST /checkout`

### AI Detection:
```
Rule Layer: 500 spike detected
AI Layer: Anomaly + error rate spike
Diagnosis: "Localized application crash."
```

### Expected Remediation:
✅ **RESTART** container (crash requires restart)

### Logs You'll See:
```
🔴 ERROR DETECTED: 500 CRASH | Localized application crash
⚡ REMEDIATION: Restarting api_service container | Reason: State Corruption
POST-REMEDIATION: Health VERIFIED
✅ RECOVERY: Service restored successfully
```

### Timeline:
Fastest recovery (~25-35 seconds) because crash is detected immediately

---

## Decision Matrix

The AI uses this logic to decide remediation:

```
┌─────────────────────────────────────────────────────────────┐
│                    ERROR DETECTED                           │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ Check CPU     │
                    └───────────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
            CPU > 70%               CPU < 70%
                │                       │
                ▼                       ▼
        ┌──────────────┐        ┌──────────────┐
        │  SUPPRESS    │        │   RESTART    │
        │  (Scale)     │        │  Container   │
        └──────────────┘        └──────────────┘
                                        │
                                        ▼
                                ┌──────────────┐
                                │ Wait 8 sec   │
                                └──────────────┘
                                        │
                                        ▼
                                ┌──────────────┐
                                │ Health Check │
                                │ (bypass=true)│
                                └──────────────┘
                                        │
                            ┌───────────┴───────────┐
                            │                       │
                        Success                  Fail
                            │                       │
                            ▼                       ▼
                    ┌──────────────┐        ┌──────────────┐
                    │ Clear Faults │        │ Keep Faults  │
                    │ Site Works   │        │ Escalate     │
                    └──────────────┘        └──────────────┘
```

---

## Testing All Error Types

### Automated Test:
```powershell
.\test_all_error_types.ps1
```

This will:
1. Test each error type sequentially
2. Verify fault injection
3. Monitor AI detection
4. Confirm remediation
5. Validate recovery
6. Show summary report

### Manual Test:
For each error type:
1. Dashboard → Click corresponding button
2. Shopping Site → Trigger error on test endpoint
3. Observe error (site breaks)
4. Wait 30-45 seconds
5. Watch Dashboard "Action Pulse" logs
6. Verify site recovers

---

## Expected Metrics After Testing All 4

**Dashboard Metrics**:
- **Total Detections**: 4
- **Precision**: 90-100% (3 restarts succeeded, 1 suppressed correctly)
- **Recall**: 90-100% (caught all 4 errors)
- **Error Breakdown**:
  - 500 CRASH: 1
  - 503 DEADLOCK: 1
  - 503 OVERLOAD: 1
  - 504 TIMEOUT: 1

---

## Troubleshooting

### Issue: 503 Overload is being restarted instead of suppressed
**Check**: CPU simulation might not be working
```powershell
docker exec api_service python -c "import psutil; print(f'CPU: {psutil.cpu_percent()}%')"
```

### Issue: Health checks failing
**Check**: Container initialization time
```powershell
docker logs api_service --tail 20
# Should see: "Application startup complete"
```

### Issue: Faults not clearing after remediation
**Check**: Fault state file
```powershell
docker exec api_service cat /app/logs/fault_state.json
# Should be: {} after successful remediation
```

---

## Key Takeaways

1. **503 has TWO types**: Deadlock (low CPU) vs Overload (high CPU)
2. **AI is smart**: Checks CPU to distinguish between them
3. **Overload is special**: Only error type that gets suppressed
4. **All others restart**: 500, 504, and 503 Deadlock all trigger restart
5. **Health verification**: Ensures restart actually worked (no fake healing)

---

**Run the automated test to verify all error types work correctly!**

```powershell
.\test_all_error_types.ps1
```
