# Error Injection Guide - Both Methods

Your dashboard now has BOTH button-based and terminal-based error injection!

## 🎯 Access the Dashboard

Open in your browser: **http://localhost:8000/dashboard**

You'll see:
- **Chaos Injection Panel** (left side) with buttons for each error type
- **Neural Telemetry** (center) with real-time AI monitoring charts
- **Precision Analytics** (right side) with detection stats and action logs

---

## 🔴 Method 1: Button-Based Injection (UI)

Simply click the buttons in the dashboard's "Chaos Injection" panel:

- **Execute Deadlock** - Injects 503 IDLE error
- **Execute Overload** - Injects 503 SAT error  
- **Execute Timeout** - Injects 504 DB error
- **Execute App Crash** - Injects 500 error
- **Force Total Recovery** - Resets all faults

The buttons will trigger the injection and you'll see:
1. Immediate log entry in the "Action Pulse" section
2. AI detection within 10-20 seconds
3. Automatic remediation action
4. Recovery verification

---

## 💻 Method 2: Terminal-Based Injection (PowerShell)

Use these commands in your terminal:

### Inject Specific Errors

```powershell
# 503 Deadlock
Invoke-WebRequest -Method POST -Headers @{"Authorization"="Bearer changeme-local-dev"} -Uri http://localhost:8000/inject/503_deadlock -UseBasicParsing

# 503 Overload
Invoke-WebRequest -Method POST -Headers @{"Authorization"="Bearer changeme-local-dev"} -Uri http://localhost:8000/inject/503_overload -UseBasicParsing

# 504 Timeout
Invoke-WebRequest -Method POST -Headers @{"Authorization"="Bearer changeme-local-dev"} -Uri http://localhost:8000/inject/504_timeout -UseBasicParsing

# 500 App Crash
Invoke-WebRequest -Method POST -Headers @{"Authorization"="Bearer changeme-local-dev"} -Uri http://localhost:8000/inject/500_checkout -UseBasicParsing

# 429 Bot Defense
Invoke-WebRequest -Method POST -Headers @{"Authorization"="Bearer changeme-local-dev"} -Uri http://localhost:8000/inject/429_bot -UseBasicParsing
```

### Reset All Faults

```powershell
Invoke-WebRequest -Method POST -Headers @{"Authorization"="Bearer changeme-local-dev"} -Uri "http://localhost:8000/inject/reset?target=all" -UseBasicParsing
```

### Advanced: Custom Duration and Intensity

```powershell
# Inject with custom duration (60 seconds) and intensity (1.5x)
Invoke-WebRequest -Method POST -Headers @{"Authorization"="Bearer changeme-local-dev"} -Uri "http://localhost:8000/inject/503_deadlock?duration_s=60&intensity=1.5" -UseBasicParsing
```

---

## 📊 What to Watch For

After injecting an error (via button OR terminal):

1. **Action Pulse Log** (right panel) - Shows injection confirmation
2. **Neural Telemetry Chart** (center) - AI MSE score will spike
3. **AI Verdict** - Changes from "NOMINAL STATE" to "🚨 ANOMALY DETECTED"
4. **Remediation Engine Logs** - Check with:
   ```powershell
   docker-compose logs -f remediation_engine
   ```
5. **Container Restart** - AI will restart the api_service container
6. **Recovery Verification** - Health check confirms service is back

---

## 🎮 Quick Test Scenarios

### Scenario 1: Test AI Detection (Button Method)
1. Open dashboard: http://localhost:8000/dashboard
2. Click "Execute App Crash" button
3. Watch the AI detect and remediate within 20 seconds

### Scenario 2: Test AI Detection (Terminal Method)
1. Open dashboard in browser
2. Run in terminal:
   ```powershell
   Invoke-WebRequest -Method POST -Headers @{"Authorization"="Bearer changeme-local-dev"} -Uri http://localhost:8000/inject/500_checkout -UseBasicParsing
   ```
3. Watch the dashboard update in real-time

### Scenario 3: Test Overload Suppression
1. Click "Execute Overload" button (or use terminal)
2. AI should detect high CPU but SUPPRESS restart (smart!)
3. Check logs to see "DIAGNOSIS: Overload condition. Suppressing restart"

---

## 🔧 Troubleshooting

### Button clicks don't work
- Check browser console for errors (F12)
- Verify auth token in static/index.html matches your INJECT_TOKEN

### Terminal commands fail with 401
- Check your INJECT_TOKEN in docker-compose.yml
- Default is: `changeme-local-dev`
- Update the Authorization header if you changed it

### Dashboard not loading
- Verify api_service is running: `docker ps`
- Check logs: `docker-compose logs api_service`
- Restart: `docker-compose restart api_service`

---

## 📝 Notes

- Both methods use the SAME backend endpoints
- Both methods require the same authentication token
- Both methods trigger the SAME AI detection and remediation
- Default injection duration: 120 seconds
- Default intensity: 1.0 (can be adjusted 0.1 to 2.0)

---

**Dashboard URL:** http://localhost:8000/dashboard
**Prometheus:** http://localhost:9090
**Grafana:** http://localhost:3001

Enjoy your dual-mode error injection system! 🚀
