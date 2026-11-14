"""
Inference Engine — V4
======================
Upgrades over V3:
  - Integrates OnlineLearner: clean production samples fed into fine-tuning buffer
  - Live threshold persistence: writes calibrated threshold back to threshold.json every N iterations
  - 5-feature support: memory_mb + active_connections now included in analysis
  - fetch_latest() used for corroboration check (faster than re-reading full window)
"""

import os
import json
import time
import math
import torch
import joblib
import requests
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from remediation_engine.ai.data_collector import PrometheusDataCollector
from remediation_engine.ai.feature_builder import SequenceBuilder
from remediation_engine.ai.lstm_model import LSTMForecastModel
from remediation_engine.ai.decision_engine import DecisionEngine
from remediation_engine.ai.online_learner import OnlineLearner


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# ── Global Configs ──────────────────────────────────────────────────
SEQUENCE_LENGTH             = _env_int("SEQUENCE_LENGTH", 30)
WINDOW_MINUTES              = _env_int("WINDOW_MINUTES", 20)
STEP_SECONDS                = _env_int("STEP_SECONDS", 5)
POLL_INTERVAL               = _env_int("POLL_INTERVAL", 5)
AI_WARMUP_SECONDS           = _env_int("AI_WARMUP_SECONDS", 30)
ANOMALY_CONFIRMATION_COUNT  = _env_int("ANOMALY_CONFIRMATION_COUNT", 1)
AI_ENABLE_REMEDIATION       = _env_bool("AI_ENABLE_REMEDIATION", True)
AI_REQUIRE_CORROBORATION    = _env_bool("AI_REQUIRE_CORROBORATION", True)
AI_THRESHOLD_MULTIPLIER     = _env_float("AI_THRESHOLD_MULTIPLIER", 1.5)
AI_DYNAMIC_WINDOW_SAMPLES   = _env_int("AI_DYNAMIC_WINDOW_SAMPLES", 240)

# Local-friendly defaults for terminal execution
PROMETHEUS_URL         = os.getenv("PROMETHEUS_URL",         "http://localhost:9090")
API_REPORT_URL         = os.getenv("API_REPORT_URL",         "http://localhost:8000/ai/report")
API_RESET_URL          = os.getenv("API_RESET_URL",          "http://localhost:8000/inject/reset?target=all")
TARGET_CONTAINER_NAME  = os.getenv("TARGET_CONTAINER_NAME",  "api_service")
DOCKER_SOCKET_URL      = os.getenv("DOCKER_SOCKET_URL",      "npipe:////./pipe/docker_engine")
INJECT_TOKEN           = os.getenv("INJECT_TOKEN",           "changeme-local-dev")
AI_DYNAMIC_MIN_SAMPLES      = _env_int("AI_DYNAMIC_MIN_SAMPLES", 100)
AI_DYNAMIC_PERCENTILE       = _env_float("AI_DYNAMIC_PERCENTILE", 99.9)
AI_MIN_REQUEST_RATE_FOR_SIGNAL = _env_float("AI_MIN_REQUEST_RATE_FOR_SIGNAL", 0.05)
AI_MIN_ERROR_RATE_FOR_SIGNAL   = _env_float("AI_MIN_ERROR_RATE_FOR_SIGNAL", 0.02)
AI_MIN_P95_FOR_SIGNAL          = _env_float("AI_MIN_P95_FOR_SIGNAL", 1.5)
AI_CRITICAL_ERROR_THRESHOLD    = _env_float("AI_CRITICAL_ERROR_THRESHOLD", 0.5) # 50%+ errors is always critical
RULE_PRECEDENCE_SECONDS     = _env_int("RULE_PRECEDENCE_SECONDS", 30)

# Feature Significance Weights: [request_rate, error_rate, p95_latency, memory_mb, active_connections]
# We weight error_rate (index 1) and latency (index 2) much higher.
FEATURE_WEIGHTS = torch.tensor([1.0, 10.0, 3.0, 1.0, 1.0], dtype=torch.float32)

RULE_LOOKBACK_SECONDS       = _env_int("RULE_LOOKBACK_SECONDS", 60)
RULE_QUERY_WINDOW           = os.getenv("RULE_QUERY_WINDOW", "10s")
RULE_QUERY_STEP             = os.getenv("RULE_QUERY_STEP", "5s")
RULE_CONFIRMATION_COUNT     = _env_int("RULE_CONFIRMATION_COUNT", 1)
RULE_SPIKE_THRESHOLDS: Dict[str, float] = {
    "500": _env_float("SPIKE_THRESHOLD_500", 0.05),
    "503": _env_float("SPIKE_THRESHOLD_503", 0.05),
    "504": _env_float("SPIKE_THRESHOLD_504", 0.03),
    "429": _env_float("SPIKE_THRESHOLD_429", 0.1),
}

# Online learning & threshold persistence config
ONLINE_FINE_TUNE_TRIGGER    = _env_int("ONLINE_FINE_TUNE_TRIGGER", 500)
THRESHOLD_PERSIST_INTERVAL  = _env_int("THRESHOLD_PERSIST_INTERVAL_ITERATIONS", 100)

# Paths should be cross-platform. We check for /models (Docker) or models/ (Local)
def _find_path(env_name: str, filename: str) -> str:
    # 1. Check if ENV is set
    env_val = os.getenv(env_name)
    if env_val:
        return env_val
    
    # 2. Check Docker root path
    docker_path = os.path.join("/", "models", filename)
    if os.path.exists(docker_path):
        return docker_path
        
    # 3. Fallback to local project path (relative to CWD)
    local_path = os.path.join("models", filename)
    return local_path

MODEL_PATH      = _find_path("MODEL_PATH",     "lstm_model.pt")
SCALER_PATH     = _find_path("SCALER_PATH",    "scaler.pkl")
THRESHOLD_PATH  = _find_path("THRESHOLD_PATH", "threshold.json")


class InferenceEngine:
    def __init__(self):
        self.collector       = PrometheusDataCollector(base_url=PROMETHEUS_URL)
        self.builder         = SequenceBuilder(sequence_length=SEQUENCE_LENGTH)
        
        # Pass local-friendly URLs to the Decision Engine
        self.decision_engine = DecisionEngine(
            api_url=API_REPORT_URL,
            api_reset_url=API_RESET_URL,
            health_url_template=None,  # Use default from DecisionEngine (reads from env var)
            token=INJECT_TOKEN
        )

        self.model     = None
        self.scaler    = None
        self.threshold = None

        self.anomaly_counter        = 0
        self.rule_spike_counters    = {code: 0 for code in RULE_SPIKE_THRESHOLDS}
        self.score_history          = deque(maxlen=AI_DYNAMIC_WINDOW_SAMPLES)
        self.last_rule_detection_time = 0.0
        self._iteration_count       = 0
        self._model_mtime           = 0.0   # tracks last-known model file mtime
        self._current_sample_count  = 0

        self._load_artifacts()

        # Online learner — wired up after model is loaded
        self.online_learner = OnlineLearner(
            model=self.model,
            model_path=MODEL_PATH,
            threshold_path=THRESHOLD_PATH,
            device=torch.device("cpu"),
            fine_tune_trigger=ONLINE_FINE_TUNE_TRIGGER,
        )

        # Seed mtime so we don’t false-trigger on startup
        try:
            self._model_mtime = os.path.getmtime(MODEL_PATH)
        except OSError:
            self._model_mtime = 0.0

    # ──────────────────────────────────────────────────────────────────
    # STARTUP
    # ──────────────────────────────────────────────────────────────────

    def _load_artifacts(self):
        self.scaler     = joblib.load(SCALER_PATH)
        input_size      = self.scaler.mean_.shape[0]

        # Use simple autoencoder architecture matching training
        self.model = LSTMForecastModel(
            input_size=input_size,
            hidden_size=32,  # Match training script
            num_layers=1,    # Match training script
            dropout=0.0,
            num_attention_heads=4,
            attention_dropout=0.1,
        )
        self.model.load_state_dict(torch.load(MODEL_PATH, map_location="cpu"))
        self.model.eval()

        # Load threshold with fallback if file doesn't exist
        try:
            with open(THRESHOLD_PATH, "r") as f:
                self.threshold = json.load(f)["threshold"]
        except FileNotFoundError:
            # Use default threshold from training if file doesn't exist
            self.threshold = 2.45  # Default from improved training
            print(f"[V4] Threshold file not found, using default: {self.threshold:.6f}")

        print(
            f"[V4] AI Engine initialized. "
            f"input_size={input_size}, threshold={self.threshold:.6f}"
        )

    # ──────────────────────────────────────────────────────────────────
    # HOT-RELOAD (after online fine-tuning)
    # ──────────────────────────────────────────────────────────────────

    def _maybe_hot_reload_model(self):
        """
        Check if OnlineLearner has written new weights to MODEL_PATH since
        the last time we loaded. If so, reload state_dict in-place so the
        live inference loop immediately benefits from the updated weights
        without requiring a Docker restart.

        The reload is intentionally lightweight — only the state_dict is
        swapped; the model architecture and scaler are unchanged.
        """
        try:
            current_mtime = os.path.getmtime(MODEL_PATH)
        except OSError:
            return  # File temporarily missing — skip

        if current_mtime <= self._model_mtime:
            return  # Nothing has changed

        try:
            new_state = torch.load(MODEL_PATH, map_location="cpu")
            self.model.load_state_dict(new_state)
            self.model.eval()
            self._model_mtime = current_mtime
            print(
                f"[V4-HOT-RELOAD] Model weights reloaded from disk after fine-tune "
                f"(pass #{self.online_learner.fine_tune_count}). "
                f"Inference now uses updated weights."
            )
        except Exception as e:
            print(f"[V4-HOT-RELOAD] WARNING: Could not reload model weights: {e}")

    # ──────────────────────────────────────────────────────────────────
    # AI SCORE
    # ──────────────────────────────────────────────────────────────────

    def _compute_ai_score(self) -> Optional[Tuple[float, Dict, object, object]]:
        """
        Returns (mse_score, latest_features, last_X, last_y) or None.
        last_X and last_y are returned so the online learner can consume them.
        """
        data = self.collector.fetch_window(minutes=WINDOW_MINUTES, step_seconds=STEP_SECONDS)
        self._current_sample_count = data.shape[0]
        if data.shape[0] <= SEQUENCE_LENGTH:
            return None

        scaled = self.scaler.transform(data)
        X, y   = self.builder.build_sequences(scaled)
        if len(X) == 0:
            return None

        last_X  = X[-1]              # shape (seq_len, features)
        last_y  = y[-1]              # shape (features,)

        X_tensor    = torch.tensor(X[-1:], dtype=torch.float32)
        y_tensor    = torch.tensor(y[-1:], dtype=torch.float32)

        with torch.no_grad():
            # Autoencoder reconstructs the input sequence
            reconstruction = self.model(X_tensor)
            
            # MSE between input and reconstruction
            sq_diff = (reconstruction - X_tensor) ** 2
            mse = torch.mean(sq_diff).item()
            
            if math.isnan(mse):
                mse = 0.0

        # ── IDLE STATE SANITIZATION ──────────────────────────────────
        # The LSTM will output arbitrary errors for all-zeros inputs
        # since it was trained on active traffic. If there is virtually
        # no traffic and no errors, the system is nominal — force MSE=0.
        if (features_from_data := {
            "request_rate": float(data[-1, 0]) if data.shape[1] > 0 else 0.0,
            "error_rate":   float(data[-1, 1]) if data.shape[1] > 1 else 0.0,
        }):
            recent_reqs = float(data[-min(10, data.shape[0]):, 0].mean())
            recent_errs = float(data[-min(10, data.shape[0]):, 1].mean())
            if recent_reqs < 0.5 and recent_errs < 0.01:
                mse = 0.0

        # Extract named features from the last raw (un-scaled) timestep
        latest_features = {
            "request_rate"      : float(data[-1, 0]) if data.shape[1] > 0 else 0.0,
            "error_rate"        : float(data[-1, 1]) if data.shape[1] > 1 else 0.0,
            "p95_latency"       : float(data[-1, 2]) if data.shape[1] > 2 else 0.0,
            "memory_mb"         : float(data[-1, 3]) if data.shape[1] > 3 else 0.0,
            "active_connections": float(data[-1, 4]) if data.shape[1] > 4 else 0.0,
        }

        return mse, latest_features, last_X, last_y

    # ──────────────────────────────────────────────────────────────────
    # THRESHOLD
    # ──────────────────────────────────────────────────────────────────

    def _get_effective_ai_threshold(self) -> Tuple[float, Optional[float]]:
        static_threshold  = self.threshold * AI_THRESHOLD_MULTIPLIER
        dynamic_threshold = None

        # CRITICAL FIX: Only use CLEAN samples (below static threshold) for dynamic threshold
        # This prevents the feedback loop where high scores during faults raise the threshold
        # making the AI blind to the anomaly
        if len(self.score_history) >= 20:
            clean_scores = [s for s in self.score_history if s < static_threshold]
            
            if len(clean_scores) >= 20:
                dynamic_threshold = float(
                    torch.tensor(clean_scores, dtype=torch.float32)
                    .quantile(0.98).item()
                )

        if dynamic_threshold is None:
            return static_threshold, None

        return max(static_threshold, dynamic_threshold), dynamic_threshold

    # ──────────────────────────────────────────────────────────────────
    # CORROBORATION
    # ──────────────────────────────────────────────────────────────────

    def _is_corroborated(self, features: Dict[str, float]) -> bool:
        has_traffic = features.get("request_rate", 0.0) >= AI_MIN_REQUEST_RATE_FOR_SIGNAL
        has_failure = (
            features.get("error_rate", 0.0)   >= AI_MIN_ERROR_RATE_FOR_SIGNAL
            or features.get("p95_latency", 0.0) >= AI_MIN_P95_FOR_SIGNAL
        )
        return has_traffic and has_failure

    # ──────────────────────────────────────────────────────────────────
    # RULE-BASED LAYER
    # ──────────────────────────────────────────────────────────────────

    def _perform_health_checks(self) -> bool:
        detected_any_rule = False
        end_epoch   = time.time()
        start_epoch = end_epoch - RULE_LOOKBACK_SECONDS

        alert_mapping = {
            "500": "HTTP_500_SPIKE",
            "503": "HTTP_503_SPIKE",
            "504": "HTTP_504_SPIKE",
            "429": "HTTP_429_SPIKE",
        }

        def check_spike(status_code: str):
            query  = (
                f'sum(rate(http_requests_total{{status="{status_code}"}}[{RULE_QUERY_WINDOW}]))'
            )
            values = self.collector._query_range(query, start_epoch, end_epoch, RULE_QUERY_STEP)
            peak   = max(values) if values else 0.0
            thr    = RULE_SPIKE_THRESHOLDS[status_code]
            return peak >= thr, peak, thr

        for status_code, alert_type in alert_mapping.items():
            try:
                is_spiking, peak_rate, threshold = check_spike(status_code)
            except Exception as e:
                print(f"[V4 RULES] Failed {status_code} spike query: {e}")
                continue

            if is_spiking:
                self.rule_spike_counters[status_code] += 1
                if self.rule_spike_counters[status_code] == RULE_CONFIRMATION_COUNT:
                    detected_any_rule = True
                    self.last_rule_detection_time = time.time()
                    self.last_rule_type = alert_type # Store for AI layer to reference
                    print(
                        f"[V4 RULES] {status_code} spike detected "
                        f"(peak={peak_rate:.4f}, threshold={threshold:.4f})."
                    )
                    result = self.decision_engine.determine_remediation(alert_type)
                    if result == "COOLDOWN_ACTIVE":
                        self.rule_spike_counters[status_code] = max(
                            RULE_CONFIRMATION_COUNT - 1, 0
                        )
            else:
                self.rule_spike_counters[status_code] = 0

        return detected_any_rule

    # ──────────────────────────────────────────────────────────────────
    # MAIN LOOP
    # ──────────────────────────────────────────────────────────────────


    def _push_telemetry(self, mse, thr, features):
        """Send live telemetry to the dashboard central hub."""
        url = API_REPORT_URL.replace("/ai/report", "/ai/telemetry/push")
        token = INJECT_TOKEN
        payload = {
            "mse_score": mse,
            "threshold": thr,
            "request_rate": features.get("request_rate", 0),
            "error_rate": features.get("error_rate", 0),
            "p95_latency": features.get("p95_latency", 0),
            "memory_mb": features.get("memory_mb", 0),
            "active_conns": features.get("active_connections", 0),
            "online_buffer": self.online_learner.buffer_size,
        }
        try:
            requests.post(url, json=payload, headers={"Authorization": f"Bearer {token}"}, timeout=2)
        except Exception:
            pass  # Fail silent — dashboard is secondary to monitoring

    def run(self):
        self.engine_start_time = time.time()
        print("[V4] Autonomous Monitoring Loop Active.")
        print(f"[V4] Features: request_rate, error_rate, p95_latency, memory_mb, active_connections")
        print(f"[V4] Online learning trigger: {ONLINE_FINE_TUNE_TRIGGER} clean samples")

        while True:
            try:
                self._iteration_count += 1

                # 1. Rule-Based Layer
                self._perform_health_checks()

                # 2. AI Layer
                ai_signal = self._compute_ai_score()

                now              = time.time()
                # Use samples instead of time for warmup — allows instant start if window has data
                is_warming_up    = (self._current_sample_count < SEQUENCE_LENGTH)
                is_in_cooldown   = (
                    now - self.decision_engine.last_action_time
                    < self.decision_engine.cooldown_period
                )

                if ai_signal is not None:
                    score, features, last_X, last_y = ai_signal
                    effective_threshold, dynamic_threshold = self._get_effective_ai_threshold()
                    corroborated         = self._is_corroborated(features)
                    rule_precedence      = (now - self.last_rule_detection_time < RULE_PRECEDENCE_SECONDS)

                    # Push telemetry to dashboard API
                    self._push_telemetry(score, effective_threshold, features)

                    # ── PROFESSIONAL NOC OUTPUT (TERMINAL) ───────────────────
                    header = f"\n{'═'*70}\n[ MONITORING PULSE ] - {datetime.now().strftime('%H:%M:%S')}\n{'═'*70}"
                    
                    # Metrics Row
                    metrics_row = (
                        f"📊 REQUESTS: {features['request_rate']:.2f}/s | "
                        f"ERRORS: {features['error_rate']*100:>5.1f}% | "
                        f"LATENCY: {features['p95_latency']*1000:>6.1f}ms"
                    )
                    
                    # Infrastructure Row
                    infra_row = (
                        f"⚙️  MEMORY: {features['memory_mb']:>6.1f}MB | "
                        f"CONNS: {features['active_connections']:>3.0f} | "
                        f"CPU: {features.get('cpu_percent', 0):>4.1f}%"
                    )

                    # AI Identification Row
                    # Identification Logic (V4)
                    is_ai_anomaly    = (score > effective_threshold)
                    is_state_anomaly = (features['error_rate'] >= AI_CRITICAL_ERROR_THRESHOLD)
                    
                    ai_status = "HEALTHY"
                    indicator = "🟢"
                    
                    if is_state_anomaly:
                        ai_status = "STATE CRITICAL"
                        indicator = "🔴"
                    elif is_ai_anomaly:
                        ai_status = "BEHAVIOR ANOMALY"
                        indicator = "🟡"
                    
                    ai_row = (
                        f"{indicator} AI STATUS: {ai_status:<16} | "
                        f"AI SCORE: {score:.6f} | "
                        f"THRESHOLD: {effective_threshold:.6f}"
                    )

                    print(header)
                    print(metrics_row)
                    print(infra_row)
                    print(ai_row)
                    
                    if is_warming_up:
                        print(f"⏳ WARMING UP: {self._current_sample_count}/{SEQUENCE_LENGTH} samples")
                    
                    # ── Anomaly trigger logic ──────────────────────────────
                    should_trigger = is_state_anomaly or (is_ai_anomaly and corroborated)

                    # FIXED: Removed rule_precedence blocking - let AI always evaluate
                    if (
                        AI_ENABLE_REMEDIATION
                        and should_trigger
                        and not is_warming_up
                    ):
                        if is_state_anomaly:
                            self.anomaly_counter = ANOMALY_CONFIRMATION_COUNT
                            # 1. Determine Logical Source (For the Healer's brain)
                            logical_source = "STATE_CRITICAL"
                            # Check if the rule engine saw a specific status code spike in the last 20 seconds
                            if hasattr(self, 'last_rule_type') and (now - self.last_rule_detection_time < 20):
                                logical_source = self.last_rule_type
                            
                            # 2. Determine Display Label (For the User's eyes)
                            if features['error_rate'] > 0:
                                if "503" in logical_source:
                                    diag_label = "DEADLOCK (503)"
                                elif "504" in logical_source:
                                    diag_label = "TIMEOUT (504)"
                                elif "500" in logical_source:
                                    diag_label = "CRASH (500)"
                                else:
                                    # Fallback to behavior-based guessing if rule engine missed it
                                    diag_label = "DEADLOCK (503)" if features.get('p95_latency', 0) > 0.5 else "CRASH (500/504)"
                                
                                final_display = f"STATE_CRITICAL_{diag_label}"
                            else:
                                final_display = "STATE_CRITICAL"
                        else:
                            self.anomaly_counter += 1
                            logical_source = "NOT_ANOMALY"
                            final_display  = "NOT_ANOMALY"

                        progress = "█" * self.anomaly_counter + "░" * (ANOMALY_CONFIRMATION_COUNT - self.anomaly_counter)
                        print(f"🔎 CONFIRMING: [{progress}] ({self.anomaly_counter}/{ANOMALY_CONFIRMATION_COUNT})")
                        
                        if self.anomaly_counter >= ANOMALY_CONFIRMATION_COUNT:
                            if not is_state_anomaly:
                                logical_source = "AI_ANOMALY_DETECTED"
                                final_display  = "AI_ANOMALY_DETECTED"

                            print(f"\n{'🔥'*20}\n⚡ [REMEDIATION] TRIGGERING ACTION via {final_display}\n{'🔥'*20}\n")
                            print(f"🔎 [DIAGNOSIS] Identified {final_display.replace('_', ' ')} signature. Executing Recovery.")
                            result = self.decision_engine.determine_remediation(logical_source)
                            
                            if result == "COOLDOWN_ACTIVE":
                                self.anomaly_counter = max(ANOMALY_CONFIRMATION_COUNT - 1, 0)
                            else:
                                self.anomaly_counter = 0
                    else:
                        if not is_warming_up:
                            self.anomaly_counter = 0
                    
                    print(f"{'─'*70}")

                    # ── Clean sample handling (no fault detected) ──────────
                    is_clean = not corroborated and not is_warming_up
                    if is_clean:
                        # Update dynamic baseline
                        self.score_history.append(score)

                        # Feed into online learner for future fine-tuning
                        self.online_learner.add_clean_sample(
                            X=last_X, y=last_y, mse_score=score
                        )

                    # ── Periodic threshold persistence ─────────────────────
                    # Writes live-calibrated threshold back to threshold.json
                    if self._iteration_count % THRESHOLD_PERSIST_INTERVAL == 0:
                        if dynamic_threshold is not None:
                            self.online_learner.persist_threshold(
                                dynamic_threshold=dynamic_threshold,
                                static_threshold=self.threshold,
                            )

                # ── Hot-reload check ────────────────────────────────────────
                # After online learner may have written new weights, reload
                # them into self.model in-place (no container restart needed).
                self._maybe_hot_reload_model()

            except Exception as e:
                print(f"[V4 ERROR] Inference Loop Exception: {e}")

            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")

    # validate() call removed to allow local terminal execution with defaults.
    
    engine = InferenceEngine()
    engine.run()
