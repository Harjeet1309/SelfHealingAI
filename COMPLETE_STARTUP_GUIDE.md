# Complete Startup Guide - Self-Healing AI System

## Quick Start (3 Steps)

```powershell
# 1. Start the system
docker-compose up -d

# 2. Wait 30 seconds for services to initialize
Start-Sleep -Seconds 30

# 3. Open the application
# Browser: http://localhost:8000
```

---

## Detailed Step-by-Step Guide

### Step 1: Start All Services

```powershell
docker-compose up -d
```

**What this does:**
- Starts 8 containers (API, Prometheus, Grafana, AlertManager, Remediation Engine, Chaos Engine, Watchdog, Toxiproxy)
- Runs in detached mode (background)
- Takes about 10-15 seconds

**Expected output:**
```
[+] Running 9/9
 ✔ Network selfhealingai_selfheal_net  Created
 ✔ Container api_service               Started
 ✔ Container prometheus                Started
 ✔ Container grafana                   Started
 ✔ Container alertmanager              Started
 ✔ Container remediation_engine        Started
 ✔ Container chaos_engine              Started
 ✔ Container watchdog                  Started
 ✔ Container toxiproxy                 Started
```

---

### Step 2: Verify All Services Are Running

```powershell
docker-compose ps
```

**Expected output:**
All containers should show "Up" status:
```
NAME                 STATUS
api_service          Up X minutes
prometheus           Up X minutes
grafana              Up X minutes
alertmanager         Up X minutes
remediation_engine   Up X minutes
chaos_engine         Up X minutes
watchdog             Up X minutes (healthy)
toxiproxy            Up X minutes
```

---

### Step 3: Access the Application

Open your browser and navigate to:

#### Main Application
**URL:** http://localhost:8000

**What you'll see:**
- Luxury e-commerce store interface
- "THE ATELIER" heading
- 4 product cards with "Acquire Item" buttons
- Status badge in top-right (should show "Stable")

#### AI Dashboard
**URL:** http://localhost:8000/dashboard

**What you'll see:**
- Real-time metrics and graphs
- Error injection buttons
- AI performance statistics
- System health indicators

#### Monitoring Dashboards
- **Prometheus:** http://localhost:9090
- **Grafana:** http://localhost:3001
- **AlertManager:** http://localhost:9093

---

## Testing the System

### Test 1: Normal Operation (No Errors)

1. Go to http://localhost:8000
2. Click "Acquire Item" on any product
3. Click "Proceed to Review"
4. Click "Complete Acquisition"
5. Click "Verify Biometrics"

**Expected:** All steps complete successfully, you return to the store

---

### Test 2: Inject and Test Each Error

#### A. Test 500 CRASH (Checkout Error)

```powershell
# Inject the error
Invoke-WebRequest -Uri "http://localhost:8000/inject/500_checkout?token=changeme-local-dev" -Method POST -UseBasicParsing
```

**Manual Test:**
1. Go to http://localhost:8000
2. Click "Acquire Item" → Works fine ✅
3. Click "Proceed to Review" → Works fine ✅
4. Click "Complete Acquisition" → **500 ERROR OVERLAY** ❌
5. Wait 5 seconds → Page auto-reloads
6. AI should detect and heal the error

**What you'll see:**
- Large "500" on screen
- "CRITICAL DISRUPTION IDENTIFIED"
- "AI_ENGINE: SELF-HEALING IN PROGRESS"
- Animated scanning line

---

#### B. Test 503 DEADLOCK (Cart Error)

```powershell
# Reset first
Invoke-WebRequest -Uri "http://localhost:8000/inject/reset?target=all&token=changeme-local-dev" -Method POST -UseBasicParsing

# Inject deadlock
Invoke-WebRequest -Uri "http://localhost:8000/inject/503_deadlock?token=changeme-local-dev" -Method POST -UseBasicParsing
```

**Manual Test:**
1. Go to http://localhost:8000
2. Click "Acquire Item" → **503 ERROR OVERLAY** ❌
3. Wait 5 seconds → Page auto-reloads
4. AI should detect and heal the error

---

#### C. Test 503 OVERLOAD (High Traffic)

```powershell
# Reset first
Invoke-WebRequest -Uri "http://localhost:8000/inject/reset?target=all&token=changeme-local-dev" -Method POST -UseBasicParsing

# Inject overload
Invoke-WebRequest -Uri "http://localhost:8000/inject/503_overload?token=changeme-local-dev" -Method POST -UseBasicParsing
```

**Manual Test:**
1. Go to http://localhost:8000
2. Click "Acquire Item" → **503 ERROR OVERLAY** ❌
3. CPU usage will spike (check dashboard)
4. AI should detect high CPU and scale/heal

---

#### D. Test 504 TIMEOUT (Payment Error)

```powershell
# Reset first
Invoke-WebRequest -Uri "http://localhost:8000/inject/reset?target=all&token=changeme-local-dev" -Method POST -UseBasicParsing

# Inject timeout
Invoke-WebRequest -Uri "http://localhost:8000/inject/504_timeout?token=changeme-local-dev" -Method POST -UseBasicParsing
```

**Manual Test:**
1. Go to http://localhost:8000
2. Click "Acquire Item" → Works fine ✅
3. Click "Proceed to Review" → Works fine ✅
4. Click "Complete Acquisition" → Works fine ✅
5. Click "Verify Biometrics" → **504 ERROR OVERLAY** ❌
6. Wait 5 seconds → Page auto-reloads
7. AI should detect and heal the error

---

#### E. Test 429 BOT DEFENSE (Rate Limiting)

```powershell
# Reset first
Invoke-WebRequest -Uri "http://localhost:8000/inject/reset?target=all&token=changeme-local-dev" -Method POST -UseBasicParsing

# Inject bot defense
Invoke-WebRequest -Uri "http://localhost:8000/inject/429_bot?token=changeme-local-dev" -Method POST -UseBasicParsing
```

**Manual Test:**
1. Go to http://localhost:8000
2. Click "Acquire Item" → Works fine ✅
3. Click "Proceed to Review" → Works fine ✅
4. Click "Complete Acquisition" → **429 ERROR** ❌
5. Error shows in browser console/network tab
6. AI logs the event (no restart needed for rate limiting)

---

### Test 3: Automated Test Scripts

#### Test All Errors Automatically
```powershell
./test_error_isolation.ps1
```

#### Test 429 Specifically
```powershell
./test_429_working.ps1
```

---

## Monitoring AI Behavior

### Watch AI Logs in Real-Time

```powershell
# Remediation Engine logs
docker-compose logs -f remediation_engine

# API Service logs
docker-compose logs -f api_service

# All logs
docker-compose logs -f
```

**What to look for:**
- `🔴 ERROR DETECTED` - AI detected an anomaly
- `⚡ REMEDIATION` - AI is taking action
- `✅ RECOVERY` - AI verified the fix worked
- `MSE Score` - AI confidence metric

---

### Check AI Dashboard

Go to http://localhost:8000/dashboard

**Key Metrics:**
- **AI Confidence** - Should be 95%+ when healthy
- **Success Rate** - Percentage of successful requests
- **Active Latency** - Response time (should be <0.1s normally)
- **Learning Buffer** - Number of samples in AI memory
- **Precision** - How accurate AI healing is
- **Recall** - How many errors AI catches

**Charts:**
- **System Pulse** - Shows latency and AI anxiety over time
- **Failure Classification** - Breakdown of error types
- **Action Ledger** - Real-time log of AI actions

---

## Common Commands

### Start/Stop/Restart

```powershell
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart a specific service
docker-compose restart api_service
docker-compose restart remediation_engine

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### View Logs

```powershell
# Last 50 lines
docker-compose logs --tail=50 api_service

# Follow logs (real-time)
docker-compose logs -f remediation_engine

# All services
docker-compose logs -f
```

### Check Status

```powershell
# Container status
docker-compose ps

# Resource usage
docker stats

# Check fault status
Invoke-WebRequest -Uri "http://localhost:8000/inject/status" -Method GET -UseBasicParsing
```

### Reset Everything

```powershell
# Reset all faults
Invoke-WebRequest -Uri "http://localhost:8000/inject/reset?target=all&token=changeme-local-dev" -Method POST -UseBasicParsing

# Reset AI statistics
./reset_stats.ps1

# Full system reset
docker-compose down
docker-compose up -d
```

---

## Error Injection Reference

### All Available Errors

```powershell
$token = "changeme-local-dev"
$base = "http://localhost:8000"

# Primary Faults
Invoke-WebRequest -Uri "$base/inject/500_checkout?token=$token" -Method POST -UseBasicParsing
Invoke-WebRequest -Uri "$base/inject/503_deadlock?token=$token" -Method POST -UseBasicParsing
Invoke-WebRequest -Uri "$base/inject/503_overload?token=$token" -Method POST -UseBasicParsing
Invoke-WebRequest -Uri "$base/inject/504_timeout?token=$token" -Method POST -UseBasicParsing
Invoke-WebRequest -Uri "$base/inject/429_bot?token=$token" -Method POST -UseBasicParsing

# Cross-Cutting Faults
Invoke-WebRequest -Uri "$base/inject/db_latency?token=$token" -Method POST -UseBasicParsing
Invoke-WebRequest -Uri "$base/inject/lock_contention?token=$token" -Method POST -UseBasicParsing
Invoke-WebRequest -Uri "$base/inject/dependency_timeout?token=$token" -Method POST -UseBasicParsing
Invoke-WebRequest -Uri "$base/inject/dependency_reset?token=$token" -Method POST -UseBasicParsing

# Reset
Invoke-WebRequest -Uri "$base/inject/reset?target=all&token=$token" -Method POST -UseBasicParsing
```

---

## Troubleshooting

### Services Won't Start

```powershell
# Check if ports are in use
netstat -ano | findstr "8000"
netstat -ano | findstr "9090"
netstat -ano | findstr "3001"

# Force remove old containers
docker-compose down -v
docker-compose up -d
```

### AI Not Detecting Errors

```powershell
# Check remediation engine logs
docker-compose logs remediation_engine

# Verify Prometheus is scraping metrics
# Go to http://localhost:9090/targets
# All targets should be "UP"

# Check if fault is actually active
Invoke-WebRequest -Uri "http://localhost:8000/inject/status" -Method GET -UseBasicParsing
```

### Container Keeps Restarting

```powershell
# Check logs for errors
docker-compose logs api_service

# This might be the AI healing it (which is good!)
# Check remediation logs
docker-compose logs remediation_engine
```

### Dashboard Not Loading

```powershell
# Restart Grafana
docker-compose restart grafana

# Check if Grafana is running
docker-compose ps grafana

# Access Grafana directly
# http://localhost:3001
```

---

## Performance Tips

### For Demonstrations

1. **Reset everything first:**
   ```powershell
   docker-compose down
   docker-compose up -d
   Start-Sleep -Seconds 30
   ```

2. **Open all dashboards in separate tabs:**
   - http://localhost:8000 (Main app)
   - http://localhost:8000/dashboard (AI dashboard)
   - http://localhost:9090 (Prometheus)
   - http://localhost:3001 (Grafana)

3. **Have injection commands ready in a script**

4. **Watch logs in a separate terminal:**
   ```powershell
   docker-compose logs -f remediation_engine
   ```

### For Development

1. **Use hot reload for code changes:**
   ```powershell
   # Edit files in api_service/app/
   # Container will auto-reload
   ```

2. **Check logs frequently:**
   ```powershell
   docker-compose logs --tail=20 api_service
   ```

3. **Reset faults between tests:**
   ```powershell
   Invoke-WebRequest -Uri "http://localhost:8000/inject/reset?target=all&token=changeme-local-dev" -Method POST -UseBasicParsing
   ```

---

## Summary

✅ **Start:** `docker-compose up -d`  
✅ **Access:** http://localhost:8000  
✅ **Dashboard:** http://localhost:8000/dashboard  
✅ **Inject Error:** Use PowerShell commands above  
✅ **Watch AI:** `docker-compose logs -f remediation_engine`  
✅ **Reset:** `Invoke-WebRequest -Uri "http://localhost:8000/inject/reset?target=all&token=changeme-local-dev" -Method POST -UseBasicParsing`  
✅ **Stop:** `docker-compose down`  

---

## Next Steps

1. Start the system: `docker-compose up -d`
2. Open http://localhost:8000
3. Try the normal flow (no errors)
4. Inject an error and watch the AI heal it
5. Check the dashboard to see AI metrics
6. Review logs to understand AI decision-making

**For detailed error information, see:**
- `ERROR_ENDPOINT_ANALYSIS.md` - Complete error mapping
- `429_ERROR_WORKING.md` - 429 error details
- `FINAL_SUMMARY.md` - System overview
