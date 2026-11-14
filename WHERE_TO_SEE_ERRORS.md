# Where to See Errors and AI Detection

## 🎯 Quick Answer

**To see AI detecting and healing errors, watch the remediation_engine logs:**

```powershell
docker-compose logs -f remediation_engine
```

---

## 📺 Three Places to Monitor

### 1️⃣ **Remediation Engine Terminal (MAIN - AI Brain)**

**Command:**
```powershell
docker-compose logs -f remediation_engine
```

**What you'll see:**
```
════════════════════════════════════════════════════════════════════
[ MONITORING PULSE ] - 14:23:45
════════════════════════════════════════════════════════════════════
📊 REQUESTS: 2.34/s | ERRORS:  0.4% | LATENCY:  125.3ms
⚙️  MEMORY: 245.6MB | CONNS:  18 | CPU:  5.2%
🟢 AI STATUS: HEALTHY | AI SCORE: 0.004320 | THRESHOLD: 0.047100
────────────────────────────────────────────────────────────────────

# When error is detected:
════════════════════════════════════════════════════════════════════
[ MONITORING PULSE ] - 14:25:12
════════════════════════════════════════════════════════════════════
📊 REQUESTS: 0.20/s | ERRORS: 85.0% | LATENCY: 2340.1ms
⚙️  MEMORY: 245.6MB | CONNS:  18 | CPU:  3.2%
🔴 AI STATUS: STATE CRITICAL | AI SCORE: 2.456789 | THRESHOLD: 0.047100
🔎 CONFIRMING: [████░░] (4/5)

🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥
⚡ [REMEDIATION] TRIGGERING ACTION via STATE_CRITICAL_DEADLOCK (503)
🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥

🔎 [DIAGNOSIS] Identified STATE CRITICAL DEADLOCK (503) signature. Executing Recovery.
```

**This is THE MAIN terminal to watch!** ⭐

---

### 2️⃣ **API Service Terminal (Application Logs)**

**Command:**
```powershell
docker-compose logs -f api_service
```

**What you'll see:**
```
# Normal requests
INFO:     127.0.0.1:52134 - "GET /products HTTP/1.1" 200 OK

# When fault is injected
INFO:     127.0.0.1:52135 - "POST /inject/500_checkout HTTP/1.1" 200 OK

# Errors being generated
ERROR:    127.0.0.1:52136 - "POST /checkout HTTP/1.1" 500 Internal Server Error
ERROR:    127.0.0.1:52137 - "POST /checkout HTTP/1.1" 500 Internal Server Error
ERROR:    127.0.0.1:52138 - "POST /checkout HTTP/1.1" 500 Internal Server Error

# After restart (container restarts, logs reset)
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

---

### 3️⃣ **All Services Combined**

**Command:**
```powershell
docker-compose logs -f
```

**What you'll see:**
- All services mixed together
- Can be overwhelming but shows full picture
- Good for debugging complex issues

---

## 🎬 Step-by-Step Demo

### Step 1: Open Terminal for AI Logs

```powershell
# Open PowerShell and run:
docker-compose logs -f remediation_engine
```

**Keep this terminal open and visible!**

---

### Step 2: Inject a Fault (in a NEW terminal)

```powershell
# Open a SECOND PowerShell window and run:
curl -X POST http://localhost:8000/inject/500_checkout

# Generate error traffic
for ($i=1; $i -le 30; $i++) {
    curl -s -X POST http://localhost:8000/checkout
}
```

---

### Step 3: Watch the FIRST Terminal

**You'll see this sequence:**

**Phase 1: Normal Operation (before fault)**
```
[ MONITORING PULSE ] - 14:23:45
🟢 AI STATUS: HEALTHY
```

**Phase 2: Errors Start**
```
[ MONITORING PULSE ] - 14:23:50
📊 REQUESTS: 0.20/s | ERRORS: 85.0% | LATENCY: 2340.1ms
🔴 AI STATUS: STATE CRITICAL
```

**Phase 3: AI Confirms Anomaly**
```
🔎 CONFIRMING: [████░░] (4/5)
```

**Phase 4: AI Triggers Remediation**
```
🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥
⚡ [REMEDIATION] TRIGGERING ACTION
🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥
```

**Phase 5: Container Restarts**
```
════════════════════════════════════════════════════════════════
🔎 [DETECTION] 
════════════════════════════════════════════════════════════════
DIAGNOSIS: Localized application crash.
════════════════════════════════════════════════════════════════

════════════════════════════════════════════════════════════════
🛠️ [REMEDIATION] 
════════════════════════════════════════════════════════════════
ACTION: Restarting api_service. REASON: State Corruption
════════════════════════════════════════════════════════════════
```

**Phase 6: Recovery Verified**
```
════════════════════════════════════════════════════════════════
✅ [RECOVERY] 
════════════════════════════════════════════════════════════════
POST-REMEDIATION: Health VERIFIED on attempt 3. Recovery confirmed.
════════════════════════════════════════════════════════════════
```

**Phase 7: Back to Normal**
```
[ MONITORING PULSE ] - 14:24:30
🟢 AI STATUS: HEALTHY
```

---

## 🖥️ Visual Dashboard (Browser)

**Best way to see everything visually:**

Open: http://localhost:8000/dashboard

**You'll see:**
- 📊 **Live Telemetry Chart** - Shows latency and AI anxiety in real-time
- 🔴 **Failure Classification** - Pie chart of error types
- 📝 **Action Ledger** - Live log stream of AI actions
- 📈 **Infrastructure Telemetry** - CPU, Memory, Connections

**When error occurs:**
- Chart spikes
- AI anxiety increases
- Action appears in ledger
- Status changes to "ANOMALY DETECTED"

---

## 🎯 Recommended Setup

**For best monitoring experience:**

### Terminal Layout:

**Terminal 1 (Main - Keep visible):**
```powershell
docker-compose logs -f remediation_engine
```

**Terminal 2 (For commands):**
```powershell
# Use this to inject faults and run commands
curl -X POST http://localhost:8000/inject/500_checkout
```

**Browser:**
```
http://localhost:8000/dashboard
```

---

## 📋 Quick Commands Reference

### View AI Detection Logs
```powershell
# Live stream (recommended)
docker-compose logs -f remediation_engine

# Last 50 lines
docker-compose logs --tail 50 remediation_engine

# Search for specific events
docker-compose logs remediation_engine | Select-String "ANOMALY"
docker-compose logs remediation_engine | Select-String "REMEDIATION"
docker-compose logs remediation_engine | Select-String "RECOVERY"
```

### View Application Errors
```powershell
# Live stream
docker-compose logs -f api_service

# Search for errors
docker-compose logs api_service | Select-String "ERROR"
docker-compose logs api_service | Select-String "500"
docker-compose logs api_service | Select-String "503"
```

### View All Services
```powershell
# Everything at once
docker-compose logs -f

# Specific time range
docker-compose logs --since 5m

# Follow multiple services
docker-compose logs -f api_service remediation_engine
```

---

## 🔍 What to Look For

### Signs of Error Detection:

✅ **In remediation_engine logs:**
- `🔴 AI STATUS: STATE CRITICAL`
- `ANOMALY DETECTED`
- `TRIGGERING ACTION`
- `Restarting api_service`
- `Health VERIFIED`

✅ **In api_service logs:**
- `500 Internal Server Error`
- `503 Service Unavailable`
- `504 Gateway Timeout`
- Container restart (logs reset)

✅ **In dashboard:**
- Red status indicator
- Spike in telemetry chart
- New entry in action ledger
- Error count increases

---

## 🎬 Complete Demo Script

**Run this to see the full cycle:**

```powershell
# Terminal 1: Start watching AI logs
docker-compose logs -f remediation_engine

# Terminal 2: Inject fault and generate errors
curl -X POST http://localhost:8000/inject/500_checkout
for ($i=1; $i -le 30; $i++) {
    curl -s -X POST http://localhost:8000/checkout
    Start-Sleep -Milliseconds 100
}

# Browser: Watch dashboard
# http://localhost:8000/dashboard
```

**Timeline:**
- **0s:** Fault injected
- **0-10s:** Errors being generated
- **10-20s:** AI detects anomaly
- **20s:** AI triggers restart
- **20-25s:** Container restarts
- **25-30s:** Health verified
- **30s+:** Back to normal

---

## 💡 Pro Tips

1. **Use multiple terminals side-by-side**
   - Left: `docker-compose logs -f remediation_engine`
   - Right: Command terminal
   - Browser: Dashboard

2. **Use color-coded search**
   ```powershell
   # Highlight errors
   docker-compose logs -f remediation_engine | Select-String "ERROR|ANOMALY|REMEDIATION"
   ```

3. **Save logs for analysis**
   ```powershell
   docker-compose logs remediation_engine > ai_logs.txt
   ```

4. **Watch specific time window**
   ```powershell
   # Last 5 minutes
   docker-compose logs --since 5m remediation_engine
   ```

---

## 🎯 Summary

**To see errors being caught:**

1. **Primary:** `docker-compose logs -f remediation_engine` ⭐
2. **Secondary:** http://localhost:8000/dashboard (dashboard)
3. **Optional:** `docker-compose logs -f api_service` (see raw errors)

**The remediation_engine logs are where the magic happens!** This is where you'll see:
- AI detecting anomalies
- Decision-making process
- Remediation actions
- Recovery verification

---

**Ready to see it in action?**

```powershell
# Terminal 1
docker-compose logs -f remediation_engine

# Terminal 2
curl -X POST http://localhost:8000/inject/500_checkout
```

Watch the AI work! 🤖✨
