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
import torch
import joblib
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
AI_WARMUP_SECONDS           = _env_int("AI_WARMUP_SECONDS", 90)
ANOMALY_CONFIRMATION_COUNT  = _env_int("ANOMALY_CONFIRMATION_COUNT", 1)
AI_ENABLE_REMEDIATION       = _env_bool("AI_ENABLE_REMEDIATION", True)
AI_REQUIRE_CORROBORATION    = _env_bool("AI_REQUIRE_CORROBORATION", False)
AI_THRESHOLD_MULTIPLIER     = _env_float("AI_THRESHOLD_MULTIPLIER", 1.5)
AI_DYNAMIC_WINDOW_SAMPLES   = _env_int("AI_DYNAMIC_WINDOW_SAMPLES", 240)
AI_DYNAMIC_MIN_SAMPLES      = _env_int("AI_DYNAMIC_MIN_SAMPLES", 100)
AI_DYNAMIC_PERCENTILE       = _env_float("AI_DYNAMIC_PERCENTILE", 99.0)
AI_MIN_REQUEST_RATE_FOR_SIGNAL = _env_float("AI_MIN_REQUEST_RATE_FOR_SIGNAL", 0.05)
AI_MIN_ERROR_RATE_FOR_SIGNAL   = _env_float("AI_MIN_ERROR_RATE_FOR_SIGNAL", 0.02)
AI_MIN_P95_FOR_SIGNAL          = _env_float("AI_MIN_P95_FOR_SIGNAL", 1.5)
RULE_PRECEDENCE_SECONDS     = _env_int("RULE_PRECEDENCE_SECONDS", 30)

RULE_LOOKBACK_SECONDS       = _env_int("RULE_LOOKBACK_SECONDS", 60)
RULE_QUERY_WINDOW           = os.getenv("RULE_QUERY_WINDOW", "30s")
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

MODEL_PATH      = os.getenv("MODEL_PATH",     "/models/lstm_model.pt")
SCALER_PATH     = os.getenv("SCALER_PATH",    "/models/scaler.pkl")
THRESHOLD_PATH  = os.getenv("THRESHOLD_PATH", "/models/threshold.json")


class InferenceEngine:
    def __init__(self):
        self.collector       = PrometheusDataCollector()
        self.builder         = SequenceBuilder(sequence_length=SEQUENCE_LENGTH)
        self.decision_engine = DecisionEngine()

        self.model     = None
        self.scaler    = None
        self.threshold = None

        self.anomaly_counter        = 0
        self.rule_spike_counters    = {code: 0 for code in RULE_SPIKE_THRESHOLDS}
        self.score_history          = deque(maxlen=AI_DYNAMIC_WINDOW_SAMPLES)
        self.last_rule_detection_time = 0.0
        self._iteration_count       = 0

        self._load_artifacts()

        # Online learner — wired up after model is loaded
        self.online_learner = OnlineLearner(
            model=self.model,
            model_path=MODEL_PATH,
            threshold_path=THRESHOLD_PATH,
            device=torch.device("cpu"),
            fine_tune_trigger=ONLINE_FINE_TUNE_TRIGGER,
        )

    # ──────────────────────────────────────────────────────────────────
    # STARTUP
    # ──────────────────────────────────────────────────────────────────

    def _load_artifacts(self):
        self.scaler     = joblib.load(SCALER_PATH)
        input_size      = self.scaler.mean_.shape[0]

        self.model = LSTMForecastModel(
            input_size=input_size,
            hidden_size=128,
            num_layers=2,
            dropout=0.25,
            num_attention_heads=4,
            attention_dropout=0.1,
        )
        self.model.load_state_dict(torch.load(MODEL_PATH, map_location="cpu"))
        self.model.eval()

        with open(THRESHOLD_PATH, "r") as f:
            self.threshold = json.load(f)["threshold"]

        print(
            f"[V4] AI Engine initialized. "
            f"input_size={input_size}, threshold={self.threshold:.6f}"
        )

    # ──────────────────────────────────────────────────────────────────
    # AI SCORE
    # ──────────────────────────────────────────────────────────────────

    def _compute_ai_score(self) -> Optional[Tuple[float, Dict, object, object]]:
        """
        Returns (mse_score, latest_features, last_X, last_y) or None.
        last_X and last_y are returned so the online learner can consume them.
        """
        data = self.collector.fetch_window(minutes=WINDOW_MINUTES, step_seconds=STEP_SECONDS)
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
            prediction = self.model(X_tensor)
            mse = torch.mean((prediction - y_tensor) ** 2).item()

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

        if len(self.score_history) >= 20:
            dynamic_threshold = float(
                torch.tensor(list(self.score_history), dtype=torch.float32)
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
        end_time   = datetime.utcnow()
        start_time = end_time - timedelta(seconds=RULE_LOOKBACK_SECONDS)
        time_range = (start_time.isoformat() + "Z", end_time.isoformat() + "Z")

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
            values = self.collector._query_range(query, *time_range, RULE_QUERY_STEP)
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
                is_warming_up    = (now - self.engine_start_time < AI_WARMUP_SECONDS)
                is_in_cooldown   = (
                    now - self.decision_engine.last_action_time
                    < self.decision_engine.cooldown_period
                )

                if ai_signal is not None:
                    score, features, last_X, last_y = ai_signal
                    effective_threshold, dynamic_threshold = self._get_effective_ai_threshold()
                    corroborated         = self._is_corroborated(features)
                    rule_precedence      = (now - self.last_rule_detection_time < RULE_PRECEDENCE_SECONDS)

                    status = (
                        "[WARMING UP]" if is_warming_up else
                        "[COOLDOWN]"   if is_in_cooldown else
                        "[ACTIVE]"
                    )
                    dyn_text = f"{dynamic_threshold:.6f}" if dynamic_threshold else "n/a"

                    print(
                        f"[V4-AI] {status} score={score:.4f} thr={effective_threshold:.4f} "
                        f"dyn={dyn_text} "
                        f"rr={features['request_rate']:.2f} "
                        f"err={features['error_rate']:.3f} "
                        f"p95={features['p95_latency']:.2f}s "
                        f"mem={features['memory_mb']:.0f}MB "
                        f"conns={features['active_connections']:.0f} "
                        f"online_buf={self.online_learner.buffer_size}"
                    )

                    # ── Anomaly trigger ────────────────────────────────────
                    if (
                        AI_ENABLE_REMEDIATION
                        and score > effective_threshold
                        and not is_warming_up
                        and (corroborated or not AI_REQUIRE_CORROBORATION)
                        and not rule_precedence
                    ):
                        self.anomaly_counter += 1
                        if self.anomaly_counter == ANOMALY_CONFIRMATION_COUNT:
                            result = self.decision_engine.determine_remediation("AI_ANOMALY_DETECTED")
                            if result == "COOLDOWN_ACTIVE":
                                self.anomaly_counter = max(ANOMALY_CONFIRMATION_COUNT - 1, 0)
                            else:
                                self.anomaly_counter = 0
                    else:
                        if not is_warming_up:
                            self.anomaly_counter = 0

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

            except Exception as e:
                print(f"[V4 ERROR] Inference Loop Exception: {e}")

            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    engine = InferenceEngine()
    engine.run()
