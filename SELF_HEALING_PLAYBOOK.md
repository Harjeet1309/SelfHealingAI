# 🏆 V3 Autonomous Self-Healing Guide (PowerShell Edition)

Use these PowerShell loops to demonstrate the AI's detection and remediation. Using loops creates a clear traffic spike in the Prometheus telemetry.

---

### 1️⃣ Error: 500 Internal Server Error (Checkout Crash)
*   **Why it occurs**: A localized logic crash in the Checkout Service.
*   **Remedy**: **Service Restart**.
*   **🚀 Demonstration Step**:
    1. **Inject Fault**: `Invoke-RestMethod -Method POST "http://localhost:8000/inject/500_checkout"`
    2. **Trigger Failure (PowerShell Loop)**:
       ```powershell
       1..30 | ForEach-Object { try { Invoke-RestMethod -Method POST "http://localhost:8000/checkout" } catch { $_.Exception.Message }; Start-Sleep -Milliseconds 100 }
       ```
    *Wait 1 minute for AI to heal the site back to Green.*

---

### 2️⃣ Error: 503 Service Unavailable (App Deadlock)
*   **Why it occurs**: The process is frozen/stuck. Requests hang and CPU remains low.
*   **Remedy**: **Health-Check Restart** (Low CPU Correlation).
*   **🚀 Demonstration Step**:
    1. **Inject Fault**: `Invoke-RestMethod -Method POST "http://localhost:8000/inject/503_deadlock"`
    2. **Trigger Failure (PowerShell Loop)**:
       ```powershell
       1..30 | ForEach-Object { try { Invoke-RestMethod -Method POST "http://localhost:8000/cart/add" } catch { $_.Exception.Message }; Start-Sleep -Milliseconds 100 }
       ```
    *Observe AI identifies "Deadlock recognized (Low CPU)" in logs.*

---

### 3️⃣ Error: 503 Service Unavailable (Resource Overload)
*   **Why it occurs**: Server CPU exhausted due to heavy traffic.
*   **Remedy**: **RESTART SUPPRESSION** (Protects shopper sessions).
*   **🚀 Demonstration Step**:
    1. **Trigger Overload (PowerShell Loop)**:
       ```powershell
       1..100 | ForEach-Object { try { Invoke-RestMethod -Method POST "http://localhost:8000/inject/503_overload"; Invoke-RestMethod "http://localhost:8000/health" } catch { $_.Exception.Message } }
       ```
    *Observe AI identifies "Overload condition (High CPU)" and wisely suppresses the restart.*

---

### 4️⃣ Error: 504 Gateway Timeout (Hanging Payment)
*   **Why it occurs**: External payment dependency is slow, clogging the application threads.
*   **Remedy**: **Connection Pool Flush (Restart)**.
*   **🚀 Demonstration Step**:
    1. **Inject Fault**: `Invoke-RestMethod -Method POST "http://localhost:8000/inject/504_timeout"`
    2. **Trigger Failure (PowerShell Loop)**:
       ```powershell
       1..20 | ForEach-Object { try { Invoke-RestMethod -Method POST "http://localhost:8000/payment" -TimeoutSec 2 } catch { $_.Exception.Message } }
       ```
    *AI detects "Clogged Payment Pipeline" and clears the hang via restart.*

---

### 5️⃣ Error: 429 Too Many Requests (Bot Attack)
*   **Why it occurs**: A bot hitting the API too fast, triggering the rate limiter.
*   **Remedy**: **Log & Observe Only** (Protects system from unnecessary restarts).
*   **🚀 Demonstration Step**:
    1. **Trigger Attack (PowerShell Loop)**:
       ```powershell
       1..100 | ForEach-Object { try { Invoke-RestMethod -Method POST "http://localhost:8000/inject/429_bot"; Invoke-RestMethod "http://localhost:8000/health" } catch { $_.Exception.Message } }
       ```
    *Observe AI logs: "Intentional high-frequency access (Scraping/Bot). Core services remain untouched."*

---

## 🎓 Why use these Loops?
*   **Sustained Signals**: Prometheus calculates "Rate" over time. A single request might disappear, but a loop of 30-100 requests creates a huge visible spike.
*   **Proof of Concept**: Shows that even under "constant fire," the AI can keep its head and apply the correct recovery strategy without human help.

---

## V4 Realistic Chaos Profiles (Senior Demo)
These scenarios are closer to real production failure modes. All injections support:
* `duration_s` (default: 120 seconds)
* `intensity` (0.1 to 2.0)

### A) Database Latency (degraded, intermittent)
```powershell
Invoke-RestMethod -Method POST "http://localhost:8000/inject/db_latency?duration_s=180&intensity=1.2"
1..40 | ForEach-Object { try { Invoke-RestMethod -Method POST "http://localhost:8000/checkout" } catch { $_.Exception.Message }; Start-Sleep -Milliseconds 150 }
```

### B) Lock Contention (transaction wait timeouts)
```powershell
Invoke-RestMethod -Method POST "http://localhost:8000/inject/lock_contention?duration_s=150&intensity=1.1"
1..40 | ForEach-Object { try { Invoke-RestMethod -Method POST "http://localhost:8000/cart/add" } catch { $_.Exception.Message }; Start-Sleep -Milliseconds 120 }
```

### C) Dependency Timeout (payment provider slowness)
```powershell
Invoke-RestMethod -Method POST "http://localhost:8000/inject/dependency_timeout?duration_s=120&intensity=1.0"
1..20 | ForEach-Object { try { Invoke-RestMethod -Method POST "http://localhost:8000/payment" -TimeoutSec 2 } catch { $_.Exception.Message } }
```

### D) Dependency Reset (upstream connection resets)
```powershell
Invoke-RestMethod -Method POST "http://localhost:8000/inject/dependency_reset?duration_s=120&intensity=1.0"
1..35 | ForEach-Object { try { Invoke-RestMethod -Method POST "http://localhost:8000/checkout" } catch { $_.Exception.Message }; Start-Sleep -Milliseconds 120 }
```

### Reset Faults Manually
```powershell
Invoke-RestMethod -Method POST "http://localhost:8000/inject/reset?target=all"
```
