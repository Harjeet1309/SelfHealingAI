# Self-Healing AI Agent
## Complete Project Documentation

**Project Title:** Self-Healing AI Agent for Automated API Endpoint Monitoring and Remediation
**Version:** V4 — Final
**Date:** February 2026
**Author:** Gudde

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Technology Stack](#2-technology-stack)
3. [System Architecture](#3-system-architecture)
4. [Directory Structure](#4-directory-structure)
5. [Service 1 — API Service](#5-service-1--api-service)
6. [Service 2 — Remediation Engine](#6-service-2--remediation-engine)
7. [Service 3 — Prometheus](#7-service-3--prometheus)
8. [Service 4 — Alertmanager](#8-service-4--alertmanager)
9. [LSTM Model and Training Pipeline](#9-lstm-model-and-training-pipeline)
10. [Fault Injection System](#10-fault-injection-system)
11. [AI Detection Strategy](#11-ai-detection-strategy)
12. [Decision Engine and Remediation Logic](#12-decision-engine-and-remediation-logic)
13. [Dashboard and Performance Tracking](#13-dashboard-and-performance-tracking)
14. [Docker Deployment](#14-docker-deployment)
15. [Configuration Reference](#15-configuration-reference)
16. [End-to-End Workflow](#16-end-to-end-workflow)
17. [Demo Scenarios](#17-demo-scenarios)
18. [Key Design Decisions](#18-key-design-decisions)
19. [Limitations and Future Work](#19-limitations-and-future-work)

---

## 1. Project Overview

The Self-Healing AI Agent is an autonomous infrastructure monitoring and remediation system. It continuously observes a live e-commerce API using real-time Prometheus metrics, detects failures through a combination of a trained LSTM neural network and rule-based spike detectors, and automatically remediates faults by restarting Docker containers or suppressing restarts intelligently based on system context.

### Core Objectives

| Objective | Description |
| --- | --- |
| Autonomous Monitoring | Poll and analyze API Golden Signals every 5 seconds without human involvement |
| AI-Based Detection | Use a trained LSTM model to identify behavioral anomalies beyond known error signatures |
| Rule-Based Classification | Deterministically detect well-known fault types such as crashes, deadlocks, and timeouts |
| Context-Aware Remediation | Use real-time CPU telemetry to distinguish overload from deadlock before taking action |
| Observable Dashboard | Display live anomaly charts, action logs, and healing metrics on the AI Insights page |
| Zero-Touch Recovery | After a restart, automatically clear faults and update the dashboard with no human input |

---

## 2. Technology Stack

| Layer | Technology |
| --- | --- |
| API Service Framework | Python 3.11, FastAPI, Uvicorn |
| AI and ML Engine | PyTorch (LSTM model), scikit-learn (StandardScaler), NumPy |
| Metrics Collection | Prometheus, prometheus-client Python library |
| Alert Routing | Prometheus Alertmanager |
| Container Orchestration | Docker, Docker Compose |
| Container Control | Docker SDK for Python (docker-py) |
| Dashboard Frontend | HTML5, Chart.js, CSS3 rendered server-side via FastAPI |
| Data Communication | REST HTTP (requests library), Prometheus HTTP API |

---

## 3. System Architecture

The system consists of four Docker containers running on a shared internal network called `selfheal_net`.

### Container Overview

| Container | Port | Role |
| --- | --- | --- |
| api_service | 8000 | Target monitored application (LUXE AI boutique) |
| prometheus | 9090 | Time-series metrics store and alert evaluator |
| alertmanager | 9093 | Alert routing and webhook dispatcher |
| remediation_engine | 5001 | AI inference loop, decision engine, and webhook server |

### Data Flow Between Services

| Step | From | To | What Happens |
| --- | --- | --- | --- |
| 1 | api_service | (self) | MetricsMiddleware records request count, latency, and errors |
| 2 | prometheus | api_service | Scrapes /metrics endpoint every 5 seconds |
| 3 | prometheus | (self) | Evaluates alert rules against stored time-series data |
| 4 | prometheus | alertmanager | Sends firing alert notifications |
| 5 | alertmanager | remediation_engine | Forwards alerts via HTTP webhook to port 5001 |
| 6 | remediation_engine | prometheus | Queries /api/v1/query_range for historical metric windows |
| 7 | remediation_engine | Docker daemon | Sends container.restart() via mounted socket |
| 8 | remediation_engine | api_service | POST /ai/report to update dashboard stats |
| 9 | remediation_engine | api_service | POST /inject/reset to clear injected faults after restart |

---

## 4. Directory Structure

| Path | Type | Purpose |
| --- | --- | --- |
| api_service/ | Directory | FastAPI boutique application |
| api_service/Dockerfile | File | Docker build instructions for api_service |
| api_service/requirements.txt | File | Python dependencies for api_service |
| api_service/app/main.py | File | FastAPI app definition and all HTML UI pages |
| api_service/app/routes.py | File | Business endpoints, fault injection engine, AI stats API |
| api_service/app/middleware.py | File | Prometheus metrics recording middleware |
| api_service/app/metrics.py | File | Prometheus metric object definitions |
| api_service/app/static/ | Directory | Product images for boutique UI |
| remediation_engine/ | Directory | AI monitoring and remediation service |
| remediation_engine/Dockerfile | File | Docker build instructions for remediation_engine |
| remediation_engine/webhook_server.py | File | Alertmanager webhook receiver (legacy backup path) |
| remediation_engine/ai/inference.py | File | Main InferenceEngine class and monitoring loop |
| remediation_engine/ai/decision_engine.py | File | DecisionEngine class — fault classification and actions |
| remediation_engine/ai/data_collector.py | File | PrometheusDataCollector — fetches metric time-series |
| remediation_engine/ai/feature_builder.py | File | SequenceBuilder — sliding window sequence construction |
| remediation_engine/ai/lstm_model.py | File | LSTMForecastModel — PyTorch neural network definition |
| remediation_engine/ai/train.py | File | Model training script |
| models/ | Directory | Pre-trained model artifacts mounted at runtime |
| models/lstm_model.pt | File | Trained LSTM weights (208 KB) |
| models/scaler.pkl | File | Fitted StandardScaler for input normalization |
| models/threshold.json | File | Anomaly detection threshold value |
| configs/ | Directory | Infrastructure configuration files |
| configs/prometheus.yml | File | Scrape targets and alertmanager location |
| configs/alert.rules.yml | File | Prometheus alerting rules written in PromQL |
| configs/alertmanager.yml | File | Alert grouping and routing to webhook |
| logs/ | Directory | Shared volume between api_service and remediation_engine |
| logs/remediation.log | File | Per-action AI engine log entries |
| logs/dashboard_stats.json | File | Persistent AI performance counters |
| docker-compose.yml | File | Full stack service orchestration |
| requirements.txt | File | Python dependencies for remediation_engine |

---

## 5. Service 1 — API Service

**Container name:** api_service
**Port:** 8000
**Framework:** FastAPI + Uvicorn

The API service is a luxury e-commerce boutique called LUXE AI. It is the monitored subject of the self-healing system. It serves realistic web pages to users while simultaneously exposing Prometheus metrics and a fault injection API for the monitoring stack.

---

### 5.1 Prometheus Metric Definitions (metrics.py)

This file defines four Prometheus instruments that capture the application's health signals. They are imported by the middleware and routes files.

| Metric Name | Type | Description | Labels |
| --- | --- | --- | --- |
| http_requests_total | Counter | Total HTTP requests processed | method, endpoint, status |
| http_errors_total | Counter | Total error responses with status >= 400 | method, endpoint, status |
| http_request_duration_seconds | Histogram | Per-request latency measured in seconds | method, endpoint |
| http_active_requests | Gauge | Number of in-flight requests at any moment | none |

---

### 5.2 Metrics Middleware (middleware.py)

A Starlette BaseHTTPMiddleware that intercepts every request and records it into the Prometheus metrics defined in metrics.py.

**Excluded paths (not recorded into metrics):**

| Path | Reason for Exclusion |
| --- | --- |
| /metrics | Prometheus scrape traffic — would pollute Golden Signals |
| /health | Internal health polling — not user-generated traffic |
| /dashboard | Static file serving — not business logic |
| /favicon.ico | Browser auto-request — not meaningful traffic |

**Request recording steps:**

| Step | Action |
| --- | --- |
| 1 | Increment http_active_requests gauge |
| 2 | Record start time |
| 3 | Call the actual endpoint handler |
| 4 | Calculate duration = end time minus start time |
| 5 | Observe duration into http_request_duration_seconds histogram |
| 6 | Increment http_requests_total with method, endpoint, status code |
| 7 | If status >= 400, also increment http_errors_total |
| 8 | Decrement http_active_requests gauge |

---

### 5.3 Fault Injection Engine (routes.py)

This is the core of the API service. It manages a fault state model and exposes injection and business endpoints.

#### Fault State Model

Each fault is a dictionary object with the following fields:

| Field | Type | Description |
| --- | --- | --- |
| pending | bool | Fault is staged but not yet active — activates on the first real request |
| active | bool | Fault is currently firing and affecting responses |
| expires_at | float | Unix timestamp at which the fault auto-expires |
| intensity | float | Severity scale from 0.1 to 2.0 — amplifies delay, probability, or CPU burn |
| code | int | HTTP status code this fault returns |
| msg | str | Human-readable description shown in UI status badge |

#### Defined Fault Types

| Fault Key | HTTP Code | Description |
| --- | --- | --- |
| checkout | 500 | Application crash during checkout processing |
| cart | 503 | Service unavailable due to deadlock |
| overload | 503 | High traffic causing CPU saturation |
| payment | 504 | Gateway timeout on payment processing |
| security | 429 | Bot defense — rate limiting active |
| db_latency | 503 | Database response latency spike |
| lock_contention | 503 | Database row-level lock contention causing waits |
| dependency_timeout | 504 | Payment provider upstream timeout |
| dependency_reset | 503 | Upstream connection reset by peer |

#### Fault Lifecycle Functions

| Function | Purpose |
| --- | --- |
| _activate_fault() | Set a fault to active or pending with a duration and intensity |
| _clear_fault() | Reset a fault completely to inactive state |
| _is_fault_active() | Check if fault is active and auto-expire it if past expires_at |
| _promote_pending_if_needed() | Transition a pending fault to active when a real request arrives |

#### Realistic Fault Simulators

| Function | Fault It Simulates | Behaviour |
| --- | --- | --- |
| _maybe_apply_db_latency() | db_latency | Adds async sleep of 0.25 to 1.5 seconds scaled by intensity |
| _maybe_apply_lock_contention() | lock_contention | Probabilistic 503 error with configurable wait before raising |
| _maybe_raise_dependency_reset() | dependency_reset | Probabilistic connection reset error based on intensity |
| _maybe_raise_dependency_timeout() | dependency_timeout | Async sleep then raises 504 — simulates real network timeout |

#### Business API Endpoints

| Endpoint | Method | Fault Checks Applied |
| --- | --- | --- |
| /health | GET | security, overload, checkout, cart, payment faults |
| /products | GET | None — always returns catalog |
| /cart/add | POST | db_latency, lock_contention, dependency_reset, cart fault |
| /checkout | POST | db_latency, lock_contention, dependency_reset, checkout fault |
| /payment | POST | db_latency, dependency_reset, dependency_timeout, payment fault |

#### Fault Injection Endpoints

| Endpoint | Method | Purpose |
| --- | --- | --- |
| /inject/{fault_type} | POST | Activate a named fault with optional duration_s and intensity parameters |
| /inject/reset | POST | Clear faults — use target=all or a specific fault key |

#### Legacy Fault Type Mapping (for demo scripts)

| Fault Type Parameter | Maps to Fault Key | Pending Mode |
| --- | --- | --- |
| 500_checkout | checkout | Yes — activates on first request |
| 503_deadlock | cart | Yes — activates on first request |
| 503_overload | overload | No — activates immediately |
| 504_timeout | payment | Yes — activates on first request |
| 429_bot | security | No — activates immediately |

#### AI Stats and Log Endpoints

| Endpoint | Method | Purpose |
| --- | --- | --- |
| /ai/report | POST | Receive action report from remediation engine and persist to dashboard_stats.json |
| /ai/stats | GET | Return full AIStats model including all counters and error type breakdown |
| /ai/logs | GET | Return last N lines from remediation.log for live dashboard streaming |
| /status | GET | Return UI status object with status, code, and message fields |

---

### 5.4 UI Pages (main.py)

All pages are server-side rendered HTML using Python f-strings. The navigation bar shows a live status badge based on which faults are active.

| Route | Page Name | Description |
| --- | --- | --- |
| GET / | THE ATELIER | Product grid showing the luxury boutique catalog |
| GET /cart | YOUR BAG | Cart review page with checkout button |
| GET /checkout-page | REVIEW | Order summary with total and confirm button |
| GET /payment-page | NEURAL GATEWAY | Payment authorization screen |
| GET /performance | AI INSIGHTS | Live AI dashboard with charts, stats, and action log |
| GET /metrics | Raw Prometheus | Prometheus scrape endpoint — not a user-facing page |

#### UI Status Badge States

| State | Color | Triggered By |
| --- | --- | --- |
| HEALTHY | Green | No active faults |
| DEGRADED | Orange | Overload, db_latency, lock_contention, dependency faults |
| FAULT | Red | checkout (500), cart (503), or payment (504) faults active |

When state is FAULT, a full-screen overlay appears showing the error code and a running animation labeled "AI ENGINE: SELF-HEALING IN PROGRESS". The page auto-reloads every 4 seconds until the restart completes and the fault clears.

---

## 6. Service 2 — Remediation Engine

**Container name:** remediation_engine
**Port:** 5001
**Entry point:** inference.py (InferenceEngine) and webhook_server.py

The remediation engine is the autonomous intelligence core. It runs two parallel processes: the primary AI inference loop and a legacy webhook receiver.

---

### 6.1 Prometheus Data Collector (data_collector.py)

The PrometheusDataCollector class fetches time-series metric data from Prometheus's HTTP API.

#### Golden Signal Queries

| Signal Name | PromQL Query |
| --- | --- |
| request_rate | sum(rate(http_requests_total[30s])) or vector(0) |
| error_rate | (sum(rate(http_requests_total{status!="200"}[30s])) or vector(0)) / (sum(rate(http_requests_total[30s])) > 0 or vector(1)) |
| p95_latency | histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[30s])) by (le)) or vector(0) |

#### fetch_window() Method

| Parameter | Default | Description |
| --- | --- | --- |
| minutes | 20 | How far back to query from the current time |
| step_seconds | 5 | Data resolution — one data point per this many seconds |

The method queries all three signals, aligns them to the same length (shortest series wins), and returns a NumPy array of shape (timesteps, 3). If Prometheus returns no data for a signal, a zero-filled array of the correct shape is returned to prevent crashes during cold start.

---

### 6.2 Sequence Builder (feature_builder.py)

The SequenceBuilder class transforms the flat time-series array into supervised learning sequences for the LSTM model.

| Property | Value |
| --- | --- |
| Default sequence length | 30 timesteps |
| Input shape | (timesteps, 3) |
| Output X shape | (samples, 30, 3) — sliding windows of input |
| Output y shape | (samples, 3) — the timestep following each window |

Each sample is a window of 30 consecutive timesteps (X) paired with the 31st timestep as the prediction target (y). This structure is used during both training (all windows) and inference (only the most recent window).

---

### 6.3 LSTM Neural Network (lstm_model.py)

The LSTMForecastModel is a PyTorch neural network designed for next-timestep forecasting of the three Golden Signals.

#### Model Architecture

| Layer | Details |
| --- | --- |
| Input | Shape (batch, 30, 3) — 30 timesteps of 3 features |
| LSTM | hidden_size=64, num_layers=2, batch_first=True |
| Output extraction | Takes only the last hidden state from the LSTM output |
| Fully connected | Linear(64, 3) — maps hidden state back to 3 features |
| Output | Shape (batch, 3) — predicted next timestep values |

#### Anomaly Scoring

The model is used as a forecasting reconstruction engine, not a classifier. At inference time, the MSE between the model's prediction and the actual next timestep is computed. Low MSE indicates normal behavior. High MSE indicates the current telemetry pattern deviates significantly from learned baseline — which signals an anomaly.

---

### 6.4 Model Training Script (train.py)

This script is run once to produce the three model artifacts saved in the models/ directory.

| Step | Action |
| --- | --- |
| 1 | Fetch 20 minutes of Prometheus data at 15-second resolution |
| 2 | Fit StandardScaler to normalize all three signals to zero mean and unit variance |
| 3 | Build supervised sequences using SequenceBuilder with sequence_length=30 |
| 4 | Train LSTM for 20 epochs using Adam optimizer and MSELoss |
| 5 | Run all training sequences through the trained model to collect MSE values |
| 6 | Compute threshold as mean(MSE) + 3 * std(MSE) — the 3-sigma upper bound |
| 7 | Save lstm_model.pt, scaler.pkl, and threshold.json to /models/ |

The 3-sigma threshold ensures approximately 99.7 percent of normal-operation MSE scores fall below it. Only genuine anomalies should cross this line.

---

### 6.5 Inference Engine (inference.py)

The InferenceEngine class is the heart of the autonomous system. On startup it loads all model artifacts and enters a continuous monitoring loop that runs every 5 seconds.

#### Global Configuration Parameters

| Parameter | Default | Description |
| --- | --- | --- |
| SEQUENCE_LENGTH | 30 | Number of timesteps fed to LSTM per inference call |
| WINDOW_MINUTES | 20 | Lookback window fetched from Prometheus |
| STEP_SECONDS | 5 | Data resolution of metric queries |
| POLL_INTERVAL | 5 | Seconds between each loop iteration |
| AI_WARMUP_SECONDS | 90 | Silence period after engine starts to suppress cold-start noise |
| ANOMALY_CONFIRMATION_COUNT | 1 | Consecutive anomalous scores required before acting |
| AI_ENABLE_REMEDIATION | true | Master switch to enable or disable all remediation actions |
| AI_REQUIRE_CORROBORATION | false | If true, require traffic and failure signal before AI triggers |
| AI_THRESHOLD_MULTIPLIER | 1.5 | Multiplier applied to static threshold from threshold.json |
| AI_DYNAMIC_WINDOW_SAMPLES | 240 | Maximum number of clean scores kept in rolling baseline history |
| AI_DYNAMIC_MIN_SAMPLES | 100 | Minimum samples before dynamic threshold is trusted |
| AI_DYNAMIC_PERCENTILE | 99.0 | Percentile of baseline history used for dynamic threshold |
| AI_MIN_REQUEST_RATE_FOR_SIGNAL | 0.05 | Minimum request rate for corroboration to pass |
| AI_MIN_ERROR_RATE_FOR_SIGNAL | 0.02 | Minimum error rate for corroboration to pass |
| AI_MIN_P95_FOR_SIGNAL | 1.5 | Minimum p95 latency in seconds for corroboration to pass |
| RULE_PRECEDENCE_SECONDS | 30 | Time LSTM layer is silenced after a rule fires |

#### Monitoring Loop — Each Iteration

| Step | Layer | Action |
| --- | --- | --- |
| 1 | Rule-Based | Query Prometheus for HTTP 500, 503, 504, and 429 spike rates over the last 60 seconds |
| 2 | Rule-Based | Compare peak rate against configured spike threshold for each status code |
| 3 | Rule-Based | If spike confirmed, call DecisionEngine.determine_remediation(alert_type) |
| 4 | Rule-Based | Record last_rule_detection_time to enforce rule precedence window |
| 5 | LSTM AI | Fetch 20-minute metric window from Prometheus |
| 6 | LSTM AI | Normalize data using fitted StandardScaler |
| 7 | LSTM AI | Build sequences using SequenceBuilder and take only the last sequence |
| 8 | LSTM AI | Run forward pass through LSTM model to get predicted next timestep |
| 9 | LSTM AI | Compute MSE between prediction and actual — this is the anomaly score |
| 10 | LSTM AI | Check score against effective threshold (higher of static or dynamic) |
| 11 | LSTM AI | Check corroboration conditions — traffic present and failure signal visible |
| 12 | LSTM AI | If score exceeds threshold and all guards pass, call DecisionEngine |
| 13 | LSTM AI | If score is normal and not corroborated, append score to baseline history |

#### Dynamic Threshold Mechanism

| Property | Value |
| --- | --- |
| Storage | Rolling deque of up to 240 recent clean MSE scores |
| Computation | 98th percentile of all scores in the deque |
| Activation | Requires at least 20 samples before being considered |
| Final effective threshold | max(static threshold, dynamic threshold) |

Only scores from non-anomalous periods (when corroboration fails) are added to the baseline. This prevents the baseline from learning anomaly behavior and raising its own floor.

#### Corroboration Check

Both conditions must be true for the AI layer to trigger remediation:

| Condition | Requirement |
| --- | --- |
| Traffic present | request_rate must be greater than or equal to 0.05 requests per second |
| Failure signal visible | error_rate >= 0.02 OR p95_latency >= 1.5 seconds |

This prevents false positives during idle or zero-traffic periods when MSE scores can be mathematically elevated but reflect no real service problem.

---

### 6.6 Decision Engine (decision_engine.py)

The DecisionEngine class translates a confirmed alert type into a concrete infrastructure action.

#### Initialization Settings (from environment)

| Setting | Default | Description |
| --- | --- | --- |
| cooldown_period | 60 seconds | Minimum gap between container restarts |
| high_cpu_threshold | 70 percent | CPU usage above this means overload, not deadlock |
| cooldown_log_interval | 10 seconds | How often to log cooldown skip messages |
| container_name | api_service | Docker container name to restart |
| api_url | http://api_service:8000/ai/report | Where to send action reports |
| api_reset_url | http://api_service:8000/inject/reset?target=all | Where to reset faults after restart |
| reset_retries | 8 | Number of fault reset attempts after restart |
| reset_retry_delay | 1.0 seconds | Delay between each retry attempt |

#### Remediation Decision Matrix

| Alert Type | CPU Above Threshold | Action Taken | Dashboard Key Reported |
| --- | --- | --- | --- |
| HTTP_500_SPIKE | Not checked | Restart container — state corruption | 500_CRASH |
| HTTP_503_SPIKE | Yes | Suppress restart — classify as overload | 503_OVERLOAD |
| HTTP_503_SPIKE | No | Restart container — deadlock | 503_DEADLOCK |
| HTTP_504_SPIKE | Not checked | Restart container — timeout cleanup | 504_TIMEOUT |
| HTTP_429_SPIKE | Not checked | Log only — bot attack, restart won't help | 429_SECURITY |
| AI_ANOMALY_DETECTED | Yes | Suppress restart — classify as overload | 503_OVERLOAD |
| AI_ANOMALY_DETECTED | No | Restart container — behavioral anomaly | 503_DEADLOCK |

#### Cooldown Behaviour

| Scenario | Behaviour |
| --- | --- |
| Restart requested within cooldown period | Skip restart, log remaining cooldown time, return COOLDOWN_ACTIVE |
| Cooldown log throttle | Skip message is logged at most once per 10 seconds to avoid log spam |
| Inference engine response to COOLDOWN_ACTIVE | Set anomaly_counter to ANOMALY_CONFIRMATION_COUNT minus 1, keeping it primed to retry |

#### Post-Restart Sequence

| Step | Action |
| --- | --- |
| 1 | Execute container.restart() via Docker SDK |
| 2 | Record last_action_time to start cooldown period |
| 3 | Retry POST /inject/reset?target=all up to 8 times with 1 second between attempts |
| 4 | Log success or warning if all retries are exhausted |
| 5 | POST /ai/report with error_key and action=RESTART_SUCCESS |

#### CPU Telemetry Collection

The engine reads real CPU stats from the Docker daemon using container.stats(stream=False). It computes CPU percentage using the delta of total CPU usage divided by the delta of system CPU usage, scaled by the number of online CPUs.

| Value | How It Is Calculated |
| --- | --- |
| cpu_delta | cpu_stats.total_usage minus precpu_stats.total_usage |
| system_delta | cpu_stats.system_cpu_usage minus precpu_stats.system_cpu_usage |
| online_cpus | From cpu_stats.online_cpus or length of percpu_usage list |
| cpu_percent | (cpu_delta / system_delta) times online_cpus times 100 |

---

### 6.7 Webhook Server (webhook_server.py)

A separate FastAPI app running on port 5001. This is the legacy backup remediation path that receives Prometheus alerts via Alertmanager webhooks.

#### Handled Alerts

| Alert Name | Handler | Action |
| --- | --- | --- |
| HighErrorRate | remedy_high_error_rate() | Controlled restart with up to 3 retries plus health verification |
| APIServiceDown | remedy_service_down() | Controlled restart with up to 3 retries plus health verification |
| HighLatency | remedy_high_latency() | Log warning only — suggests horizontal scaling |
| HighActiveRequests | remedy_high_active_requests() | Log warning only — suggests horizontal scaling |

#### Additional Behaviours

| Feature | Detail |
| --- | --- |
| Cooldown protection | 60-second minimum gap between restarts |
| Retry logic | Up to 3 restart attempts per alert with health check between each |
| Health check | GET http://api_service:8000/health with 5-second timeout |
| Escalation | If 2 consecutive alert cycles fail, logs a CRITICAL escalation message |
| Resolved alerts | Resets retry counter for the alert when Alertmanager sends resolved status |

---

## 7. Service 3 — Prometheus

**Container name:** prometheus
**Port:** 9090
**Config file:** configs/prometheus.yml

Prometheus scrapes the api_service at http://api_service:8000/metrics every 5 seconds and stores all metrics in its internal time-series database. The remediation engine queries this database via the HTTP API to power both the rule-based detector and the LSTM input pipeline.

### Alert Rules (configs/alert.rules.yml)

| Alert Name | Trigger Expression | For Duration | Severity |
| --- | --- | --- | --- |
| APIServiceDown | up{job="api_service"} == 0 | 30 seconds | critical |
| CheckoutFailures | Checkout 5xx rate divided by total checkout rate greater than 5% | 15 seconds | warning |
| ServiceOverloaded | Sum of 503 rate over 2 minutes greater than 0.5 | Immediate | warning |
| HighLatency | p95 latency histogram quantile greater than 2 seconds | 20 seconds | warning |

---

## 8. Service 4 — Alertmanager

**Container name:** alertmanager
**Port:** 9093
**Config file:** configs/alertmanager.yml

Alertmanager receives firing alerts from Prometheus, groups them, and routes them to the remediation engine's webhook server.

### Routing Configuration

| Setting | Value | Purpose |
| --- | --- | --- |
| resolve_timeout | 1 minute | How long to wait before marking an alert as resolved |
| group_by | alertname | Group alerts with the same name into a single notification |
| group_wait | 5 seconds | Wait time before sending the first notification batch |
| group_interval | 10 seconds | Minimum gap between notifications for the same group |
| repeat_interval | 1 minute | Re-send if alert is still firing after this duration |
| send_resolved | true | Send notification when an alert resolves |
| Webhook target | http://remediation_engine:5001/webhook | Where to deliver all alert payloads |

---

## 9. LSTM Model and Training Pipeline

### Model Specifications

| Property | Value |
| --- | --- |
| Model type | Multi-step LSTM forecaster |
| Architecture | 2-layer LSTM with fully connected output head |
| Input features | 3 — request_rate, error_rate, p95_latency |
| Sequence length | 30 timesteps |
| Hidden size | 64 units |
| Output | Next-timestep prediction of all 3 features |
| File size | 208 KB |
| Loss function | MSELoss (Mean Squared Error) |
| Optimizer | Adam with learning rate 0.001 |
| Training epochs | 20 |
| Batch size | 32 |

### Training Data Pipeline

| Step | Description |
| --- | --- |
| Data collection | Fetch 20 minutes of metrics from Prometheus at 15-second resolution |
| Normalization | Fit StandardScaler — zero mean and unit variance per feature |
| Sequence building | SequenceBuilder creates overlapping windows of 30 timesteps |
| Tensor conversion | Convert NumPy arrays to PyTorch tensors for training |
| Training | Adam optimizer minimizes MSELoss over 20 epochs |
| Threshold derivation | Run training data through model, compute mean + 3 sigma of MSE values |
| Artifact saving | Save lstm_model.pt, scaler.pkl, and threshold.json to /models/ |

### Model Artifacts

| File | Contents | Used By |
| --- | --- | --- |
| lstm_model.pt | Trained LSTM weights in PyTorch state_dict format | InferenceEngine at startup |
| scaler.pkl | Fitted StandardScaler with learned mean and variance | InferenceEngine — normalizes live data |
| threshold.json | Single float value — the 3-sigma MSE upper bound from training | InferenceEngine — static threshold baseline |

---

## 10. Fault Injection System

### Injection API Reference

| Endpoint | Method | Parameters | Description |
| --- | --- | --- | --- |
| /inject/{fault_type} | POST | duration_s (5 to 3600), intensity (0.1 to 2.0) | Inject a named fault scenario |
| /inject/reset | POST | target (all or fault key name) | Clear one or all active faults |

### All Supported Fault Types

| Fault Type | Category | Pending | Immediate CPU Effect |
| --- | --- | --- | --- |
| 500_checkout | Legacy demo | Yes | No |
| 503_deadlock | Legacy demo | Yes | No |
| 503_overload | Legacy demo | No | Yes — burns real CPU in /health handler |
| 504_timeout | Legacy demo | Yes | No |
| 429_bot | Legacy demo | No | No |
| db_latency | Realistic | No | No — adds async sleep |
| lock_contention | Realistic | No | No — probabilistic 503 |
| dependency_timeout | Realistic | No | No — async sleep then 504 |
| dependency_reset | Realistic | No | No — probabilistic 503 |

### Intensity Parameter Effects

| Fault | Effect of Increasing Intensity |
| --- | --- |
| db_latency | Sleep duration scales linearly from 0.25 seconds to 1.5 seconds times intensity |
| lock_contention | Failure probability increases from 0.25 toward 0.95 and wait time increases |
| dependency_reset | Failure probability increases from 0.20 toward 0.95 |
| dependency_timeout | Sleep duration scales from 1.8 seconds upward to a maximum of 7.0 seconds |
| overload | CPU burn loop iteration count scales from 4 million to 12 million iterations |

### Pending vs Immediate Mode

| Mode | Activation Trigger | Typical Use Case |
| --- | --- | --- |
| Pending | Activates when the first real request hits the affected endpoint | Crash and deadlock faults — mirrors how real bugs surface under user activity |
| Immediate | Activates as soon as the inject API call is made | Ambient conditions like overload, security throttling, and database faults |

---

## 11. AI Detection Strategy

The system uses two independent detection layers that operate simultaneously on every polling cycle.

### Layer 1 — Rule-Based Spike Detector

The rule layer detects well-known failure signatures with deterministic logic.

#### Rule Layer Parameters

| Parameter | Default | Description |
| --- | --- | --- |
| RULE_LOOKBACK_SECONDS | 60 | Time range queried for spike detection |
| RULE_QUERY_WINDOW | 30s | PromQL rate window within each spike query |
| RULE_QUERY_STEP | 5s | Resolution of the Prometheus range query |
| RULE_CONFIRMATION_COUNT | 1 | Number of consecutive detections required before acting |

#### Spike Rate Thresholds

| Status Code | Threshold | Rationale |
| --- | --- | --- |
| 500 | 0.05 requests per second | Any sustained crash rate is critical |
| 503 | 0.05 requests per second | Service unavailability needs immediate attention |
| 504 | 0.03 requests per second | Timeout cascade starts at lower rates |
| 429 | 0.10 requests per second | Higher tolerance — brief 429 spikes are more acceptable |

#### Rule Precedence

When the rule layer fires, the LSTM AI layer is silenced for 30 seconds (RULE_PRECEDENCE_SECONDS). This prevents both layers from acting on the same incident and causing double restarts.

---

### Layer 2 — LSTM Anomaly Detector

The LSTM layer detects behavioral drift and novel anomalies that do not produce obvious HTTP error spikes.

#### AI Layer Safety Guards

| Guard | Mechanism | Purpose |
| --- | --- | --- |
| Warmup period | 90-second silence after engine startup | Suppresses cold-start noise during initial metric accumulation |
| Corroboration | Requires traffic present AND failure signal visible | Prevents false positives during idle or zero-traffic periods |
| Static threshold | threshold.json value multiplied by 2.0 | Baseline from training data with double sensitivity multiplier |
| Dynamic threshold | 98th percentile of recent clean baseline scores | Auto-calibrates to real traffic patterns over time |
| Effective threshold | Higher of static threshold or dynamic threshold | Always uses the more conservative of the two bounds |
| Clean baseline | Score history updated only when corroboration fails | Baseline never learns from anomaly periods |
| Cooldown guard | 60 seconds minimum between restarts | Prevents restart storms from rapid successive alerts |
| Rule precedence | 30-second silence after rule layer fires | Prevents duplicate actions on the same incident |

---

## 12. Decision Engine and Remediation Logic

### Complete Remediation Decision Table

| Alert Type | CPU Check Required | CPU Condition | Action | Dashboard Key | Return Value |
| --- | --- | --- | --- | --- | --- |
| HTTP_500_SPIKE | No | Any | Restart container | 500_CRASH | RESTART_SUCCESS |
| HTTP_503_SPIKE | Yes | CPU above 70% | Suppress restart | 503_OVERLOAD | SUPPRESS_RESTART_FOR_SCALING |
| HTTP_503_SPIKE | Yes | CPU at or below 70% | Restart container | 503_DEADLOCK | RESTART_SUCCESS |
| HTTP_504_SPIKE | No | Any | Restart container | 504_TIMEOUT | RESTART_SUCCESS |
| HTTP_429_SPIKE | No | Any | Log only, no restart | 429_SECURITY | LOG_ONLY |
| AI_ANOMALY_DETECTED | Yes | CPU above 70% | Suppress restart | 503_OVERLOAD | SUPPRESS_RESTART_FOR_SCALING |
| AI_ANOMALY_DETECTED | Yes | CPU at or below 70% | Restart container | 503_DEADLOCK | RESTART_SUCCESS |

### Return Value Meanings

| Return Value | Meaning | Dashboard Effect |
| --- | --- | --- |
| RESTART_SUCCESS | Container was restarted successfully | Increments remediations_fixed |
| SUPPRESS_RESTART_FOR_SCALING | Restart suppressed due to high CPU overload | Increments remediations_suppressed |
| LOG_ONLY | Alert noted but no infrastructure action taken | Increments remediations_suppressed |
| COOLDOWN_ACTIVE | Another restart is already within the cooldown window | No dashboard change |
| RESTART_FAILED | Docker restart call threw an exception | No dashboard increment |
| NO_ACTION_MAPPED | Alert type not recognized by the decision engine | No dashboard change |

---

## 13. Dashboard and Performance Tracking

### AI Insights Page (/performance)

The dashboard page is served by the FastAPI main.py and auto-refreshes data every 3 seconds via JavaScript fetch calls.

#### KPI Cards

| KPI Card | Data Source | Formula |
| --- | --- | --- |
| Model Accuracy | Display value | 94.2% when total detections exceed 2, otherwise 91.5% |
| Total Detections | performance_data.total_detections | Incremented on every POST to /ai/report |
| Self-Healing Effectiveness | Computed from stats | (remediations_fixed + remediations_suppressed) divided by total_detections times 100 |

#### Anomaly Distribution Doughnut Chart

| Property | Value |
| --- | --- |
| Chart type | Doughnut with 80% cutout |
| Library | Chart.js (loaded from CDN) |
| Segments | 500 Crash, 503 Deadlock, 503 Overload, 504 Timeout, 429 Security |
| Data source | performance_data.error_counts dictionary |
| Colors | Red for 500, Gold for 503 Deadlock, Orange for 503 Overload, Purple for 504, Green for 429 |

#### Action Log Stream

| Property | Value |
| --- | --- |
| Data source | GET /ai/logs — reads last 15 lines of logs/remediation.log |
| Refresh interval | Every 3 seconds via JavaScript setInterval |
| Line colors | Gold for ACTION lines, Green for DIAGNOSIS lines, Red for ERROR lines |
| Scroll behavior | Auto-scrolls to bottom when new entries arrive |

#### Persistence

Dashboard statistics are written to logs/dashboard_stats.json after every /ai/report call. Because the logs directory is a shared Docker volume, this file survives container restarts. Historical stats are never lost even when the api_service container is restarted as part of remediation.

---

## 14. Docker Deployment

### Service Configuration Summary

| Service | Build Context | Image | Ports | Depends On |
| --- | --- | --- | --- | --- |
| api_service | ./api_service | Custom build | 8000:8000 | None |
| prometheus | prom/prometheus:latest | Official | 9090:9090 | None |
| alertmanager | prom/alertmanager:latest | Official | 9093:9093 | None |
| remediation_engine | . (root) | Custom build | 5001:5001 | api_service, prometheus |

### Shared Volumes

| Host Path | Container | Mount Path | Purpose |
| --- | --- | --- | --- |
| ./logs | api_service | /app/logs | API service writes remediation.log and dashboard_stats.json |
| ./logs | remediation_engine | /app/logs | Remediation engine reads and writes to same log files |
| ./models | remediation_engine | /models | LSTM model artifacts read at startup |
| /var/run/docker.sock | remediation_engine | /var/run/docker.sock | Docker API access for container restarts |
| ./configs/prometheus.yml | prometheus | /etc/prometheus/prometheus.yml | Scrape configuration |
| ./configs/alert.rules.yml | prometheus | /etc/prometheus/alert.rules.yml | Alert rule definitions |
| ./configs/alertmanager.yml | alertmanager | /etc/alertmanager/alertmanager.yml | Routing configuration |

### Commands

| Command | Purpose |
| --- | --- |
| docker-compose up --build | Build images and start all services |
| docker-compose up -d --build | Build and start all services in detached mode |
| docker-compose down | Stop and remove all containers |
| docker-compose down -v | Stop, remove containers, and delete volumes |
| docker logs remediation_engine -f | Tail AI engine logs in real time |
| docker logs api_service -f | Tail API service logs in real time |

### Service URLs

| Service | URL |
| --- | --- |
| Boutique Home | http://localhost:8000 |
| AI Insights Dashboard | http://localhost:8000/performance |
| Raw Prometheus Metrics | http://localhost:8000/metrics |
| Prometheus Web UI | http://localhost:9090 |
| Alertmanager Web UI | http://localhost:9093 |
| Remediation Webhook | http://localhost:5001/webhook |

---

## 15. Configuration Reference

### AI Inference Engine Variables

| Environment Variable | Default | Description |
| --- | --- | --- |
| SEQUENCE_LENGTH | 30 | Number of timesteps in each LSTM input window |
| WINDOW_MINUTES | 20 | Lookback window fetched from Prometheus per inference cycle |
| STEP_SECONDS | 5 | Resolution of Prometheus range queries in seconds |
| POLL_INTERVAL | 5 | Seconds between each iteration of the monitoring loop |
| AI_WARMUP_SECONDS | 90 | Silence period after engine starts to avoid cold-start noise |
| ANOMALY_CONFIRMATION_COUNT | 1 | Consecutive anomalous cycles required before triggering remediation |
| AI_ENABLE_REMEDIATION | true | Master switch to enable or disable all remediation actions |
| AI_REQUIRE_CORROBORATION | true | Require traffic and failure signal before LSTM triggers |
| AI_THRESHOLD_MULTIPLIER | 1.5 | Multiplier applied to the static threshold from threshold.json |
| AI_DYNAMIC_WINDOW_SAMPLES | 240 | Maximum clean scores stored for dynamic threshold computation |
| AI_DYNAMIC_MIN_SAMPLES | 40 | Minimum scores before dynamic threshold is trusted |
| AI_DYNAMIC_PERCENTILE | 99.0 | Percentile of baseline scores used for dynamic threshold |
| AI_MIN_REQUEST_RATE_FOR_SIGNAL | 0.05 | Minimum request rate per second for corroboration to pass |
| AI_MIN_ERROR_RATE_FOR_SIGNAL | 0.02 | Minimum error rate for corroboration to pass |
| AI_MIN_P95_FOR_SIGNAL | 1.5 | Minimum p95 latency in seconds for corroboration to pass |

### Rule-Based Layer Variables

| Environment Variable | Default | Description |
| --- | --- | --- |
| RULE_LOOKBACK_SECONDS | 60 | Number of seconds of data checked for spike conditions |
| RULE_QUERY_WINDOW | 30s | PromQL rate window used within each spike query |
| RULE_QUERY_STEP | 5s | Step resolution for Prometheus range queries |
| RULE_CONFIRMATION_COUNT | 1 | Consecutive confirmations before rule fires |
| RULE_PRECEDENCE_SECONDS | 30 | Seconds LSTM is silenced after a rule detects a spike |
| SPIKE_THRESHOLD_500 | 0.05 | 500 error rate in requests per second to confirm spike |
| SPIKE_THRESHOLD_503 | 0.05 | 503 error rate in requests per second to confirm spike |
| SPIKE_THRESHOLD_504 | 0.03 | 504 error rate in requests per second to confirm spike |
| SPIKE_THRESHOLD_429 | 0.10 | 429 error rate in requests per second to confirm spike |

### Decision Engine Variables

| Environment Variable | Default | Description |
| --- | --- | --- |
| REMEDIATION_COOLDOWN_SECONDS | 60 | Minimum seconds between consecutive container restarts |
| HIGH_CPU_THRESHOLD | 70 | CPU percentage above which the fault is treated as overload |
| COOLDOWN_LOG_INTERVAL_SECONDS | 10 | Minimum seconds between cooldown skip log messages |
| TARGET_CONTAINER_NAME | api_service | Name of the Docker container to restart on remediation |
| DOCKER_SOCKET_URL | unix:///var/run/docker.sock | URL for the Docker daemon connection |
| API_REPORT_URL | http://api_service:8000/ai/report | Endpoint to send action reports to the dashboard |
| API_RESET_URL | http://api_service:8000/inject/reset?target=all | Endpoint to auto-clear faults after restart |
| AUTO_RESET_RETRIES | 8 | Number of fault reset attempts after a successful restart |
| AUTO_RESET_RETRY_DELAY_SECONDS | 1.0 | Seconds to wait between each reset retry |
| PROMETHEUS_URL | http://prometheus:9090 | Base URL for all Prometheus HTTP API queries |
| PROMETHEUS_TIMEOUT_SECONDS | 10 | Timeout for Prometheus HTTP requests |

---

## 16. End-to-End Workflow

### Normal Operation

| Step | Component | Action |
| --- | --- | --- |
| 1 | User | Browses the LUXE AI boutique and triggers product, cart, and checkout requests |
| 2 | MetricsMiddleware | Records each request — duration, status code, active count |
| 3 | Prometheus | Scrapes /metrics every 5 seconds and stores time-series data |
| 4 | InferenceEngine | Fetches 20 minutes of metric history from Prometheus |
| 5 | LSTM | Predicts next timestep — actual closely matches, MSE score is low |
| 6 | InferenceEngine | Logs active status and score below threshold — no action taken |
| 7 | System | Remains in HEALTHY state |

### Fault Detection and Remediation — Deadlock Scenario

| Step | Component | Action |
| --- | --- | --- |
| 1 | Demo operator | POST /inject/503_deadlock — cart fault enters pending state |
| 2 | User | POST /cart/add — pending fault promotes to active, returns 503 |
| 3 | MetricsMiddleware | Records 503 status code — http_requests_total{status="503"} increases |
| 4 | Prometheus | Scrapes metrics, 503 rate rises in time-series database |
| 5 | InferenceEngine | Rule layer queries 503 spike rate, peak exceeds 0.05 threshold |
| 6 | InferenceEngine | Calls DecisionEngine.determine_remediation("HTTP_503_SPIKE") |
| 7 | DecisionEngine | Reads CPU stats from Docker daemon |
| 8a | DecisionEngine | CPU is below 70% — classifies as deadlock, calls _execute_restart() |
| 9 | DecisionEngine | container.restart() executes — api_service stops and reboots |
| 10 | DecisionEngine | Retries POST /inject/reset?target=all up to 8 times until api_service responds |
| 11 | DecisionEngine | POST /ai/report with error_key=503_DEADLOCK and action=RESTART_SUCCESS |
| 12 | System | api_service is healthy again, status badge returns to HEALTHY |

### Fault Detection and Remediation — Overload Scenario

| Step | Component | Action |
| --- | --- | --- |
| 1 | Demo operator | POST /inject/503_overload — overload fault activates immediately |
| 2 | User | GET /health — handler executes CPU burn loop for millions of iterations |
| 3 | MetricsMiddleware | Records 503 status code — error rate rises |
| 4 | DecisionEngine | CPU check reads above 70% due to burn loop |
| 5 | DecisionEngine | Classifies as overload, suppresses restart |
| 6 | DecisionEngine | POST /ai/report with error_key=503_OVERLOAD and action=SUPPRESS_RESTART_FOR_SCALING |
| 7 | System | No restart performed — correct inference for overload-class fault |

---

## 17. Demo Scenarios

### Scenario 1 — Application Crash (500)

| Field | Value |
| --- | --- |
| Inject command | POST /inject/500_checkout |
| Expected detection | HTTP_500_SPIKE via rule layer |
| Expected diagnosis log | DIAGNOSIS: Localized application crash |
| Expected action log | ACTION: Restarting api_service. REASON: State Corruption |
| Dashboard key | 500_CRASH |

### Scenario 2 — Deadlock (503 with Low CPU)

| Field | Value |
| --- | --- |
| Inject command | POST /inject/503_deadlock |
| Expected detection | HTTP_503_SPIKE via rule layer |
| Expected diagnosis log | DIAGNOSIS: Deadlock recognized. Restarting |
| Expected action log | ACTION: Restarting api_service. REASON: App Deadlock |
| Dashboard key | 503_DEADLOCK |

### Scenario 3 — Overload (503 with High CPU)

| Field | Value |
| --- | --- |
| Inject command | POST /inject/503_overload |
| Trigger command | Hammer GET /health multiple times |
| Expected detection | HTTP_503_SPIKE via rule layer |
| Expected diagnosis log | DIAGNOSIS: Overload condition. Suppressing restart |
| Expected action | No restart — SUPPRESS_RESTART_FOR_SCALING |
| Dashboard key | 503_OVERLOAD |

### Scenario 4 — Bot Attack (429)

| Field | Value |
| --- | --- |
| Inject command | POST /inject/429_bot |
| Expected detection | HTTP_429_SPIKE via rule layer |
| Expected diagnosis log | DIAGNOSIS: Bot Attack. Logging only |
| Expected action | LOG_ONLY — no restart |
| Dashboard key | 429_SECURITY |

### Scenario 5 — Gateway Timeout (504)

| Field | Value |
| --- | --- |
| Inject command | POST /inject/504_timeout |
| Expected detection | HTTP_504_SPIKE via rule layer |
| Expected diagnosis log | DIAGNOSIS: Gateway Timeout. Clearing connections |
| Expected action log | ACTION: Restarting api_service. REASON: 504 Timeout Cleanup |
| Dashboard key | 504_TIMEOUT |

### Scenario 6 — AI-Only Behavioral Anomaly

| Field | Value |
| --- | --- |
| Inject command | POST /inject/db_latency?intensity=1.5 |
| Notes | No HTTP errors initially — only latency degradation |
| Expected detection | LSTM MSE score rises as p95 latency increases |
| Expected diagnosis log | DIAGNOSIS: AI Detected Behavioral Anomaly (Low CPU). Restarting |
| Time to detection | Approximately 30 to 60 seconds after injection |
| Dashboard key | 503_DEADLOCK |

---

## 18. Key Design Decisions

### Decision 1 — Dual-Layer Detection

The rule layer handles confirmed, well-understood fault signatures instantly with no ambiguity. The LSTM layer handles behavioral drift and novel anomalies that have no defined HTTP signature. Neither layer alone is sufficient — the rule layer misses subtle slowdowns and the LSTM layer can produce false positives without confirmation. Running both in parallel provides complementary coverage. Rule precedence ensures they never conflict on the same incident.

### Decision 2 — CPU-Aware Remediation

A 503 error can come from two completely different root causes — a deadlocked process (low CPU) or an overloaded system (high CPU). These require opposite responses. Restarting an overloaded service while it is under peak load worsens the overload because the cold-started container immediately receives the full traffic backlog. Reading real Docker CPU stats before acting eliminates this class of wrong remediation.

### Decision 3 — Pending Fault Mode

Crash and deadlock faults are held in pending state until the first real request activates them. This mirrors how real application bugs surface — they appear when specific code paths are hit under user load, not at startup. This makes fault injection scenarios more realistic to demonstrate.

### Decision 4 — Auto-Reset After Restart

Test faults are automatically cleared via the reset API after each successful restart. Without this, the restarted service would immediately re-enter fault mode because the injected fault was still in the state dictionary. This auto-reset makes the healing loop completely self-contained and prevents demos from needing manual cleanup between scenarios.

### Decision 5 — Persistent Dashboard Stats

Writing stats to a JSON file on a shared Docker volume ensures the AI Insights dashboard retains historical remediation counts across container restarts. This is essential because the api_service container itself is what gets restarted during remediation. Without a shared persistent store, every heal event would wipe the dashboard history.

### Decision 6 — Dynamic Anomaly Threshold

A threshold derived from training data alone may not hold in different environments or as traffic patterns evolve. The dynamic threshold re-computes itself from the 98th percentile of recent clean MSE scores collected during live operation. This makes the system self-adapting and reduces false positives during sustained but legitimate traffic changes.

### Decision 7 — Non-Blocking Reporting

The report POST call to /ai/report uses a 1-second timeout and is wrapped in try/except with a silent pass. During a container restart, the API is offline for several seconds. Blocking the decision engine on this call would stall the remediation loop. Missed stats updates during the restart window are acceptable — the healing action is the priority.

---

## 19. Limitations and Future Work

### Current Limitations

| Area | Limitation |
| --- | --- |
| Model training data | LSTM trained on synthetic low-traffic data — may need retraining for production patterns |
| CPU telemetry latency | Docker stats API call takes approximately 1 second — can bottleneck the decision engine under rapid alerts |
| Single container scope | Remediation only targets api_service — no multi-service or distributed system support |
| Static model weights | LSTM does not update online — weights have no mechanism for adapting to drift over long deployments |
| Escalation | The webhook server logs a CRITICAL escalation message but sends no external notification |
| Accuracy display | The 94.2 percent model accuracy on the dashboard is a display constant — real precision and recall are not computed at runtime |
| No horizontal scaling | The system restarts containers but cannot scale them out — no Kubernetes or Docker Swarm integration |

### Planned Future Improvements

| Improvement | Expected Benefit |
| --- | --- |
| Online LSTM fine-tuning | Continuously retrain on recent clean samples to prevent model drift over time |
| Multi-service support | Extend Docker control to restart any container based on alert labels and container name maps |
| Kubernetes integration | Replace Docker restart with Kubernetes pod deletion and HPA scaling triggers |
| Attention-based explanability | Log which Golden Signal caused the LSTM score spike using attention weight output |
| External escalation | Integrate PagerDuty, Slack, or email for alerts that exceed retry thresholds |
| Grafana dashboard | Replace custom HTML dashboard with a full Grafana and PromQL visualization layer |
| Feedback loop for thresholds | Track false positive and negative rates over time and auto-tune thresholds accordingly |
| Extended feature set | Add memory usage, disk I/O, network rate, and active session count as LSTM input features |

---

*This document is the complete and authoritative reference for the Self-Healing AI Agent project as of February 2026. All information is derived directly from the implemented source code in this repository.*
