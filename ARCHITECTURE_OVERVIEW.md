# 🏗️ Self-Healing AI: System Architecture & Workflow

This document explains the internal mechanics of the V3 Self-Healing System, following the industry-standard **MAPE-K** (Monitor, Analyze, Plan, Execute, Knowledge) autonomy loop.

---

## 🧩 1. System Component Directory

### 🛒 A. Luxe Shopping Portal (`api_service`)
*   **Role**: The "Victim" app. It provides the user interface and business logic for the storefront.
*   **Key Feature**: It includes a **Fault Injection Engine** used for the demonstration. It exposes a `/metrics` endpoint that reflects its health in real-time.

### 📊 B. Prometheus Monitoring Suite
*   **Role**: The "Sensory System."
*   **Function**: It continuously "scrapes" metrics (HTTP error rates, CPU usage, Latency) from the Shopping Portal every 15 seconds and stores them as time-series data.

### 🧠 C. Remediation Engine (The AI Agent)
This is the heart of the project. It consists of two sub-layers:
1.  **Inference Engine**: Queries Prometheus using PromQL. It uses a rule-based threshold and a statistical anomaly model to detect if the system is "Red," "Orange," or "Green."
2.  **Decision Engine**: The logic layer (Plan). It performs **Signal Correlation** to decide the best fix (e.g., Restart vs. Suppress).

### 🐳 D. Docker Infrastructure
*   **Role**: The "Execution Layer." 
*   **Function**: The AI talks directly to the Docker Socket (via Python SDK) to stop and start containers. This is how the "Heal" actually happens.

---

## 🚀 2. The Step-by-Step Workflow

When a failure occurs (e.g., a **503 Deadlock** scenario), the following 5-step loop triggers automatically:

### Step 1: MONITOR (Sensory Input)
*   The system is running. Prometheus scrapes the `/metrics` endpoint.
*   The `api_service` is returning 503 errors and CPU is at 2%.

### Step 2: ANALYZE (Alert Classification)
*   The **Inference Engine** detects a spike in 503 errors.
*   It asks Prometheus: *"What is the CPU usage during this spike?"*
*   Data returned: `Error_Rate: 100%`, `CPU_Usage: 2%`.

### Step 3: PLAN (Root Cause Diagnosis)
*   The **Decision Engine** correlates the two signals: 
    *   *Logic*: "If Status=503 AND CPU=Low THEN Diagnostic=Deadlock."
    *   *Strategy*: "Action required: Prompt Restart."

### Step 4: EXECUTE (Autonomous Remediation)
*   The AI issues a command to the Docker API: `api_service.restart()`.
*   The container is killed and a fresh instance starts in < 3 seconds.

### Step 5: OBSERVE (Verification)
*   The AI continues to watch the metrics.
*   Once HTTP errors drop to 0% and 200 OKs return, the system logs: `SUCCESS: System Healed.`

---

## 💡 3. Why this is "Smart" (Viva Points)
*   **No "Blind" Restarts**: A traditional script would restart the server for an Overload, which would actually make the problem worse (Restart Storm). Our AI **suppresses** restarts if it detects High CPU.
*   **Unified Telemetry**: By using Prometheus, we bridge the gap between "App Logic" and "Hardware Performance." 
*   **Zero-Touch Recovery**: The entire timeline from detection to resolution (approx. 60-90s) happens with **zero human intervention**.
