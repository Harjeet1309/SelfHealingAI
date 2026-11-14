# Complete Self-Healing AI Test Guide

## 🚀 Step-by-Step Testing Instructions

### Prerequisites Check
Before starting, ensure:
- Docker Desktop is running
- Ports are available: 8000, 9090, 9093, 3001, 5001, 5002, 5003
- No previous containers running: `docker-compose down -v`

---

## Phase 1: System Startup

### 1.1 Start All Services
```powershell
docker-compose up --build -d
```

### 1.2 Verify All Containers Running
```powershell
docker-compose ps
```

Expected output - ALL should show "Up":
- api_service
- prometheus
- alertmanager
- remediation_engine
- chaos_engine
- toxiproxy
- watchdog
- grafana

### 1.3 Check Remediation Engine Logs
```powershell
docker-compose logs -f remediation_engine
```

Look for:
```
[V4] AI Engine initialized. input_size=5, threshold=X.XXXXXX
[V4] Autonomous Monitoring Loop Active.
[V4] Features: request_rate, error_rate, p95_latency, memory_mb, active_connections
```

Press `Ctrl+C` to exit logs.

---

## Phase 2: Baseline Verification

### 2.1 Open Shopping Site
**URL**: http://localhost:8000/

**Expected**: 
- Site loads normally
- Shows "LUXE AI - Autonomous Boutique"
- Status badge shows "Stable" (green)

### 2.2 Test Normal Operations
1. Click "Acquire Item" on any product
2. Should navigate to cart successfully
3. Click "Proceed to Review"
4. Click "Complete Acquisition"
5. All should work without errors

### 2.3 Open Dashboard
**URL**: http://localhost:8000/dashboard

**Expected**:
- "SELF-HEALING NOC v4.0" header
- "MONITORING ACTIVE" with uptime counter
- AI MSE SCORE showing low value (< 0.1)
- "NOMINAL STATE" verdict
- Action Pulse showing initialization logs

---

## Phase 3: Error Testing - 503 DEADLOCK

### 3.1 Inject 503 Deadlock Error
**On Dashboard**:
1. Click "Execute Deadlock" button (503 IDLE)
2. Should see confirmation in browser console

### 3.2 Trigger the Error
**On Shopping Site** (http://localhost:8000/):
1. Click "Acquire Item" on any product
2. **Expected**: Get 503 error overlay
   - Shows "503" in large text
   - "CRITICAL DISRUPTION IDENTIFIED"
   - "AI_ENGINE: SELF-HEALING IN PROGRESS"

### 3.3 Monitor Dashboard Action Pulse
**Switch to Dashboard** (http://localhost:8000/dashboard):

**Expected logs sequence** (appears within 10-30 seconds):
```
⚡ FAULT INJECTED: 503_DEADLOCK — Active until AI remediates
🔴 ERROR DETECTED: 503 DEADLOCK/OVERLOAD | DIAGNOSIS: Deadlock recognized
⚡ REMEDIATION: 503 DEADLOCK/OVERLOAD | Restarting api_service container
✅ RECOVERY: 503 DEADLOCK/OVERLOAD | Service restored successfully
```

### 3.4 Verify Recovery
**On Shopping Site**:
1. Wait for auto-reload (or refresh manually)
2. Try "Acquire Item" again
3. **Expected**: Works normally, no error

### 3.5 Check Metrics
**On Dashboard**:
- AI MSE SCORE should return to low value
- "NOMINAL STATE" verdict restored
- TOTAL DETECTIONS counter incremented
- PRECISION should show 100%

---

## Phase 4: Error Testing - 503 OVERLOAD

### 4.1 Inject 503 Overload Error
**On Dashboard**:
1. Click "Execute Overload" button (503 SAT)

### 4.2 Trigger the Error
**On Shopping Site**:
1. Click "Acquire Item"
2. **Expected**: Slow response, then 503 error

### 4.3 Monitor Dashboard
**Expected logs**:
```
🔴 ERROR DETECTED: 503 DEADLOCK/OVERLOAD | DIAGNOSIS: Overload condition
⚡ REMEDIATION: Suppressing restart (High CPU detected)
```

**Note**: This error should be SUPPRESSED (not restarted) because it's classified as overload.

### 4.4 Manual Recovery
Since overload is suppressed, manually reset:
**On Dashboard**:
1. Click "Force Total Recovery" button

---

## Phase 5: Error Testing - 504 TIMEOUT

### 5.1 Inject 504 Timeout Error
**On Dashboard**:
1. Click "Execute Timeout" button (504 DB)

### 5.2 Trigger the Error
**On Shopping Site**:
1. Navigate through: Acquire Item → Cart → Review → Complete Acquisition
2. **Expected**: Long wait, then 504 error on payment

### 5.3 Monitor Dashboard
**Expected logs**:
```
🔴 ERROR DETECTED: 504 TIMEOUT | DIAGNOSIS: Gateway Timeout
⚡ REMEDIATION: 504 TIMEOUT | Restarting api_service container
✅ RECOVERY: 504 TIMEOUT | Service restored successfully
```

### 5.4 Verify Recovery
Retry the payment flow - should work.

---

## Phase 6: Error Testing - 500 CRASH

### 6.1 Inject 500 Crash Error
**On Dashboard**:
1. Click "Execute App Crash" button (500)

### 6.2 Trigger the Error
**On Shopping Site**:
1. Navigate to checkout and click "Complete Acquisition"
2. **Expected**: 500 error overlay

### 6.3 Monitor Dashboard
**Expected logs**:
```
🔴 ERROR DETECTED: 500 CRASH | DIAGNOSIS: Localized application crash
⚡ REMEDIATION: 500 CRASH | Restarting api_service container
✅ RECOVERY: 500 CRASH | Service restored successfully
```

### 6.4 Verify Recovery
Retry checkout - should work.

---

## Phase 7: Advanced Monitoring

### 7.1 Check Prometheus
**URL**: http://localhost:9090/

Query examples:
```
rate(http_requests_total[1m])
rate(http_errors_total[1m])
http_request_duration_seconds
```

### 7.2 Check Grafana
**URL**: http://localhost:3001/

- Should show "Self-Healing AI: Industrial Overlook" dashboard
- Real-time metrics visualization

### 7.3 Check Alertmanager
**URL**: http://localhost:9093/

- Shows active alerts during fault injection
- Shows resolved alerts after recovery

---

## Troubleshooting

### Issue: Dashboard shows no logs
**Check**:
```powershell
docker-compose logs remediation_engine | Select-String "ERROR|WARNING"
```

### Issue: Errors not clearing
**Manual reset**:
```powershell
curl -X POST "http://localhost:8000/inject/reset?target=all" -H "Authorization: Bearer changeme-local-dev"
```

### Issue: Container not restarting
**Check Docker permissions**:
```powershell
docker-compose logs remediation_engine | Select-String "restart"
```

### Issue: Metrics not showing
**Check Prometheus targets**:
http://localhost:9090/targets
- api_service should be "UP"

---

## Success Criteria

✅ All 4 error types inject successfully
✅ Dashboard shows error detection logs
✅ Dashboard shows remediation action logs
✅ Dashboard shows recovery confirmation logs
✅ Shopping site returns to normal after each error
✅ Precision/Recall metrics update correctly
✅ No manual intervention needed (except for overload)

---

## Quick Commands Reference

```powershell
# Start system
docker-compose up --build -d

# View all logs
docker-compose logs -f

# View specific service
docker-compose logs -f remediation_engine

# Stop system
docker-compose down

# Full cleanup
docker-compose down -v

# Restart specific service
docker-compose restart api_service

# Check container status
docker-compose ps

# Manual fault reset
curl -X POST "http://localhost:8000/inject/reset?target=all" -H "Authorization: Bearer changeme-local-dev"
```

---

## Expected Timeline

- **Startup**: 30-60 seconds for all containers
- **AI Warmup**: 30 seconds (collecting baseline data)
- **Error Detection**: 5-15 seconds after fault injection
- **Remediation**: 5-10 seconds (container restart)
- **Recovery Verification**: 3-5 seconds (health checks)
- **Total per error**: ~30-45 seconds from injection to recovery

---

## Next Steps After Testing

1. Document any issues found
2. Check precision/recall metrics
3. Review remediation logs for patterns
4. Test chaos scenarios (optional)
5. Verify watchdog functionality (optional)
