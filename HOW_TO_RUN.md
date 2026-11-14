# How to Run and Test the Application

## 🚀 Quick Start (Automated)

### Option 1: Run Everything Automatically
```powershell
# This will start the app and run all tests
.\test_application.ps1
```

### Option 2: Manual Step-by-Step
Follow the sections below for detailed manual testing.

---

## 📋 Manual Step-by-Step Guide

### Step 1: Start the Application

```powershell
# Stop any existing containers
docker-compose down

# Start all services (this will take 2-3 minutes)
docker-compose up -d --build

# Wait for services to initialize
Start-Sleep -Seconds 30
```

**What this does:**
- Builds Docker images for all services
- Starts 7 containers: api_service, prometheus, alertmanager, remediation_engine, chaos_engine, watchdog, grafana
- Initializes the AI model and monitoring systems

---

### Step 2: Check Container Status

```powershell
# View running containers
docker-compose ps
```

**Expected output:**
```
NAME                  STATUS
api_service           Up
prometheus            Up
alertmanager          Up
remediation_engine    Up
chaos_engine          Up
watchdog              Up
grafana               Up
```

**If any container shows "Exited":**
```powershell
# Check logs for that container
docker-compose logs <container_name>
```

---

### Step 3: Verify Services are Healthy

#### Test API Service
```powershell
curl http://localhost:8000/health
```
**Expected:** `{"status":"healthy"}`

#### Test Prometheus
```powershell
curl http://localhost:9090/-/healthy
```
**Expected:** `Prometheus is Healthy.`

#### Test in Browser
Open these URLs in your browser:
- **Main App:** http://localhost:8000
- **AI Dashboard:** http://localhost:8000/dashboard
- **Prometheus:** http://localhost:9090
- **Grafana:** http://localhost:3001

---

### Step 4: Validate Metrics Collection

```powershell
# Run the validation script
docker exec -it api_service python /app/validate_metrics_fix.py
```

**Expected output:**
```
✅ SUCCESS: Memory RSS = 245.6 MB
✅ SUCCESS: Active TCP connections = 18
✅ SUCCESS: process_memory_mb = 245.6 MB
✅ SUCCESS: process_active_connections = 18.0

All tests passed! Metrics collection is working correctly.
```

**If tests fail:**
- Check if SYS_PTRACE capability is added in docker-compose.yml
- Rebuild: `docker-compose down && docker-compose up --build -d`

---

### Step 5: Check Metrics Endpoint

```powershell
# Fetch metrics
curl http://localhost:8000/metrics
```

**Look for these metrics:**
```
process_memory_mb 245.6
process_active_connections 18.0
http_requests_total{...} 42
http_request_duration_seconds_bucket{...} 0.15
```

**Check specific metrics:**
```powershell
# Memory metric
curl http://localhost:8000/metrics | Select-String "process_memory_mb"

# Connection metric
curl http://localhost:8000/metrics | Select-String "process_active_connections"
```

---

### Step 6: Verify AI Engine is Running

```powershell
# Check remediation engine logs
docker-compose logs remediation_engine | Select-String "AI Engine initialized"
```

**Expected output:**
```
[V4] AI Engine initialized. input_size=5, threshold=0.047100
[V4] Autonomous Monitoring Loop Active.
```

**Check recent monitoring activity:**
```powershell
docker-compose logs remediation_engine --tail 20
```

**Expected to see:**
```
[ MONITORING PULSE ] - 14:23:45
📊 REQUESTS: 2.34/s | ERRORS:  0.4% | LATENCY:  125.3ms
⚙️  MEMORY: 245.6MB | CONNS:  18 | CPU:  5.2%
🟢 AI STATUS: HEALTHY | AI SCORE: 0.004320 | THRESHOLD: 0.047100
```

---

### Step 7: Generate Test Traffic

```powershell
# Generate 50 requests to the API
for ($i=1; $i -le 50; $i++) {
    curl -s http://localhost:8000/products | Out-Null
    Write-Host "Request $i sent"
}
```

**Then check metrics updated:**
```powershell
curl http://localhost:8000/metrics | Select-String "http_requests_total"
```

---

### Step 8: Test the Dashboard

Open in browser: http://localhost:8000/dashboard

**You should see:**
- ✅ Live telemetry pulse chart (latency + AI score)
- ✅ Failure classification doughnut chart
- ✅ Action ledger (log stream)
- ✅ Infrastructure telemetry (CPU, Memory)
- ✅ Real-time updates every 2 seconds

---

### Step 9: Test Fault Injection (Optional)

#### Test 1: Inject a 500 Crash
```powershell
# Inject fault
curl -X POST http://localhost:8000/inject/500_checkout

# Generate error traffic
for ($i=1; $i -le 30; $i++) {
    curl -s -X POST http://localhost:8000/checkout | Out-Null
}

# Wait and watch AI detect it
Start-Sleep -Seconds 20
docker-compose logs remediation_engine --tail 30
```

**Expected:**
- AI detects anomaly within 10-20 seconds
- Logs show: `🔴 ANOMALY DETECTED!`
- Container restarts automatically
- Dashboard updates with remediation action

#### Test 2: Inject Overload (Should Suppress Restart)
```powershell
# Inject overload
curl -X POST http://localhost:8000/inject/503_overload

# Generate high traffic
for ($i=1; $i -le 100; $i++) {
    curl -s http://localhost:8000/health | Out-Null
}

# Check AI response
docker-compose logs remediation_engine --tail 30
```

**Expected:**
- AI detects high CPU
- Logs show: `DIAGNOSIS: Overload condition. Suppressing restart`
- No container restart (smart decision!)

---

## 🔍 Verification Checklist

Use this checklist to verify everything is working:

- [ ] All 7 containers are running
- [ ] API service responds to /health
- [ ] Prometheus is collecting metrics
- [ ] Memory metric shows non-zero value (200-400 MB)
- [ ] Connection metric shows non-zero value (10-50)
- [ ] AI engine initialized with threshold ~0.047
- [ ] Dashboard loads and shows live data
- [ ] Traffic generation updates metrics
- [ ] Fault injection triggers AI detection
- [ ] Overload suppression works correctly

---

## 📊 Expected Behavior

### Normal Operation (No Faults)
```
🟢 AI STATUS: HEALTHY
   Score (0.004) <= Threshold (0.047)
   
📊 METRICS:
   Requests: 2.5/s
   Errors: 0.3%
   Latency: 120ms
   Memory: 245 MB
   Connections: 18
```

### During Fault (500 Crash)
```
🔴 AI STATUS: STATE CRITICAL
   Score (2.456) > Threshold (0.047)
   
⚡ REMEDIATION TRIGGERED
   Action: Restart api_service
   Reason: State Corruption
   
✅ RECOVERY VERIFIED
   Service healthy after restart
```

### During Overload (High CPU)
```
🟡 AI STATUS: BEHAVIOR ANOMALY
   Score (1.234) > Threshold (0.047)
   CPU: 85.2% (HIGH)
   
🛡️ DIAGNOSIS: Overload condition
   Action: SUPPRESS RESTART
   Reason: Protects user sessions
```

---

## 🐛 Troubleshooting

### Problem: Containers won't start

**Solution:**
```powershell
# Check if ports are in use
netstat -ano | findstr "8000 9090 9093 5001"

# If ports are busy, stop other services or change ports in docker-compose.yml
```

### Problem: Metrics show 0.0

**Solution:**
```powershell
# Verify SYS_PTRACE capability
docker inspect api_service | Select-String "SYS_PTRACE"

# If not found, rebuild
docker-compose down
docker-compose up --build -d
```

### Problem: AI not detecting faults

**Solution:**
```powershell
# Check AI configuration
docker-compose logs remediation_engine | Select-String "threshold="

# Should show threshold around 0.047, not 0.126
# If wrong, verify fixes were applied in inference.py
```

### Problem: Dashboard not loading

**Solution:**
```powershell
# Check API service logs
docker-compose logs api_service

# Restart API service
docker-compose restart api_service
```

---

## 📝 Useful Commands

### View Logs
```powershell
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f remediation_engine
docker-compose logs -f api_service

# Last 50 lines
docker-compose logs --tail 50 remediation_engine
```

### Restart Services
```powershell
# Restart specific service
docker-compose restart api_service

# Restart all services
docker-compose restart

# Full rebuild
docker-compose down
docker-compose up --build -d
```

### Check Resource Usage
```powershell
# Container stats
docker stats

# Specific container
docker stats api_service
```

### Clean Up
```powershell
# Stop all containers
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Remove all images
docker-compose down --rmi all
```

---

## 🎯 Success Indicators

Your application is working correctly if:

1. ✅ All containers show "Up" status
2. ✅ /health endpoint returns 200 OK
3. ✅ Metrics show non-zero values
4. ✅ AI engine initialized successfully
5. ✅ Dashboard displays live data
6. ✅ Fault injection triggers detection
7. ✅ Overload suppression works
8. ✅ No permission errors in logs

---

## 🚀 Next Steps

Once everything is working:

1. **Explore the Dashboard**
   - Open http://localhost:8000/dashboard
   - Watch real-time metrics
   - Review action logs

2. **Test Different Fault Scenarios**
   - 500 Crash: `curl -X POST http://localhost:8000/inject/500_checkout`
   - 503 Deadlock: `curl -X POST http://localhost:8000/inject/503_deadlock`
   - 504 Timeout: `curl -X POST http://localhost:8000/inject/504_timeout`

3. **Monitor for 24 Hours**
   - Check logs periodically
   - Verify no false positives
   - Confirm metrics stay healthy

4. **Review Documentation**
   - `FIXES_APPLIED.md` - Detailed fix documentation
   - `PROJECT_DOCUMENTATION.md` - Full system architecture
   - `IMPLEMENTATION_GUIDE.md` - Advanced configuration

---

## 📞 Need Help?

If you encounter issues:

1. Run the automated test: `.\test_application.ps1`
2. Check logs: `docker-compose logs -f`
3. Review troubleshooting section above
4. Check `FIXES_APPLIED.md` for detailed guidance

---

**Last Updated:** February 25, 2026
**Status:** Production Ready ✅
