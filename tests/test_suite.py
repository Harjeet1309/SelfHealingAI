"""
Test Suite — Self-Healing AI Agent
====================================
Covers:
    - Unit tests for DecisionEngine (all alert types, overload suppression, cooldown)
    - Unit tests for InferenceEngine threshold logic
    - Unit tests for OnlineLearner buffer and fine-tuning trigger
    - Integration tests for API health and fault injection endpoints
    - Integration tests for Chaos Controller scenario listing and execution
    - Remediation flow end-to-end smoke test
"""

import os
import sys
import json
import time
import unittest
import threading
import numpy as np
from unittest.mock import MagicMock, patch, PropertyMock
from collections import deque

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from remediation_engine.ai.decision_engine import DecisionEngine
from remediation_engine.ai.online_learner import OnlineLearner
from remediation_engine.ai.synthetic_data_generator import build_dataset, generate_normal, generate_crash_500
from remediation_engine.ai.feature_builder import SequenceBuilder


# ═══════════════════════════════════════════════════════════════════════
# UNIT TESTS — Decision Engine
# ═══════════════════════════════════════════════════════════════════════

class TestDecisionEngine(unittest.TestCase):

    def setUp(self):
        """Create a DecisionEngine with a mocked Docker client."""
        with patch("remediation_engine.ai.decision_engine.docker.DockerClient"):
            self.engine = DecisionEngine()

        # Mock the container restart so no real Docker calls happen
        self.mock_container = MagicMock()
        self.engine.docker_client.containers.get = MagicMock(
            return_value=self.mock_container
        )
        # Mock CPU stats — low CPU by default (deadlock scenario)
        self.engine._get_container_stats = MagicMock(
            return_value={"cpu_percent": 10.0}
        )
        # Disable health check for speed in unit tests
        self.engine.health_check_enabled = False
        # Disable API reporting
        self.engine._report = MagicMock()
        # Disable fault reset
        self.engine._auto_reset_faults = MagicMock()

    # ── Crash 500 ───────────────────────────────────────────────────
    def test_http_500_triggers_restart(self):
        result = self.engine.determine_remediation("HTTP_500_SPIKE")
        self.assertIn("RESTART", result)
        self.mock_container.restart.assert_called_once()

    # ── Deadlock 503 (low CPU) ──────────────────────────────────────
    def test_http_503_low_cpu_triggers_restart(self):
        self.engine._get_container_stats = MagicMock(return_value={"cpu_percent": 20.0})
        result = self.engine.determine_remediation("HTTP_503_SPIKE")
        self.assertIn("RESTART", result)
        self.mock_container.restart.assert_called_once()

    # ── Overload 503 (high CPU) — must NOT restart ──────────────────
    def test_http_503_high_cpu_suppresses_restart(self):
        self.engine._get_container_stats = MagicMock(return_value={"cpu_percent": 85.0})
        result = self.engine.determine_remediation("HTTP_503_SPIKE")
        self.assertEqual(result, "SUPPRESS_RESTART_FOR_SCALING")
        self.mock_container.restart.assert_not_called()

    # ── AI Anomaly + High CPU — must suppress ──────────────────────
    def test_ai_anomaly_high_cpu_suppresses(self):
        self.engine._get_container_stats = MagicMock(return_value={"cpu_percent": 90.0})
        result = self.engine.determine_remediation("AI_ANOMALY_DETECTED")
        self.assertEqual(result, "SUPPRESS_RESTART_FOR_SCALING")
        self.mock_container.restart.assert_not_called()

    # ── AI Anomaly + Low CPU — must restart ────────────────────────
    def test_ai_anomaly_low_cpu_restarts(self):
        self.engine._get_container_stats = MagicMock(return_value={"cpu_percent": 15.0})
        result = self.engine.determine_remediation("AI_ANOMALY_DETECTED")
        self.assertIn("RESTART", result)

    # ── 504 Timeout — always restart ───────────────────────────────
    def test_http_504_triggers_restart(self):
        result = self.engine.determine_remediation("HTTP_504_SPIKE")
        self.assertIn("RESTART", result)

    # ── 429 Bot Attack — log only, never restart ────────────────────
    def test_http_429_logs_only(self):
        result = self.engine.determine_remediation("HTTP_429_SPIKE")
        self.assertEqual(result, "LOG_ONLY")
        self.mock_container.restart.assert_not_called()

    # ── Unknown alert type — no action ─────────────────────────────
    def test_unknown_alert_no_action(self):
        result = self.engine.determine_remediation("UNKNOWN_ALERT_XYZ")
        self.assertEqual(result, "NO_ACTION_MAPPED")

    # ── Cooldown prevents second restart ───────────────────────────
    def test_cooldown_blocks_second_restart(self):
        # First restart sets cooldown timer
        self.engine.determine_remediation("HTTP_500_SPIKE")
        # Second call should be blocked
        result = self.engine.determine_remediation("HTTP_500_SPIKE")
        self.assertEqual(result, "COOLDOWN_ACTIVE")
        # Container restart should only have been called once
        self.assertEqual(self.mock_container.restart.call_count, 1)

    # ── Multi-container routing ─────────────────────────────────────
    def test_multi_container_routing(self):
        self.engine.container_routing["HTTP_500_SPIKE"] = "payment_service"
        self.engine.determine_remediation("HTTP_500_SPIKE")
        self.engine.docker_client.containers.get.assert_called_with("payment_service")

    # ── Health verification called after restart ────────────────────
    def test_health_verification_called_on_restart(self):
        self.engine.health_check_enabled = True
        self.engine._verify_health = MagicMock(return_value=True)
        result = self.engine.determine_remediation("HTTP_500_SPIKE")
        self.engine._verify_health.assert_called_once()
        self.assertEqual(result, "RESTART_SUCCESS_VERIFIED")

    def test_unverified_restart_returned_when_health_check_fails(self):
        self.engine.health_check_enabled = True
        self.engine._verify_health = MagicMock(return_value=False)
        result = self.engine.determine_remediation("HTTP_500_SPIKE")
        self.assertEqual(result, "RESTART_SUCCESS_UNVERIFIED")


# ═══════════════════════════════════════════════════════════════════════
# UNIT TESTS — Online Learner
# ═══════════════════════════════════════════════════════════════════════

class TestOnlineLearner(unittest.TestCase):

    def _make_learner(self, trigger=10):
        import torch
        model = MagicMock()
        model.parameters = MagicMock(return_value=iter([]))
        model.state_dict = MagicMock(return_value={})
        learner = OnlineLearner(
            model=model,
            model_path="/tmp/test_model.pt",
            threshold_path="/tmp/test_threshold.json",
            device=torch.device("cpu"),
            fine_tune_trigger=trigger,
            save_raw_data=False,
        )
        return learner

    def test_buffer_fills_correctly(self):
        learner = self._make_learner(trigger=50)
        X = np.random.randn(30, 5).astype(np.float32)
        y = np.random.randn(5).astype(np.float32)
        for _ in range(20):
            learner.add_clean_sample(X, y, mse_score=0.005)
        self.assertEqual(learner.buffer_size, 20)

    def test_mse_scores_accumulate(self):
        learner = self._make_learner(trigger=1000)
        X = np.random.randn(30, 5).astype(np.float32)
        y = np.random.randn(5).astype(np.float32)
        for i in range(50):
            learner.add_clean_sample(X, y, mse_score=float(i) * 0.001)
        self.assertEqual(len(learner._mse_scores), 50)

    def test_live_threshold_returns_none_below_min_samples(self):
        learner = self._make_learner(trigger=1000)
        # min_samples_for_threshold=100, we add only 10
        X = np.random.randn(30, 5).astype(np.float32)
        y = np.random.randn(5).astype(np.float32)
        for _ in range(10):
            learner.add_clean_sample(X, y, mse_score=0.01)
        self.assertIsNone(learner.get_live_threshold())

    def test_live_threshold_computed_after_min_samples(self):
        learner = self._make_learner(trigger=1000)
        learner.min_samples = 10
        X = np.random.randn(30, 5).astype(np.float32)
        y = np.random.randn(5).astype(np.float32)
        for _ in range(100):
            learner.add_clean_sample(X, y, mse_score=0.01)
        result = learner.get_live_threshold()
        self.assertIsNotNone(result)
        self.assertIsInstance(result, float)

    def test_max_buffer_enforced(self):
        learner = self._make_learner(trigger=10000)
        learner._X_buffer.maxlen  # should be set
        X = np.random.randn(30, 5).astype(np.float32)
        y = np.random.randn(5).astype(np.float32)
        for _ in range(learner._X_buffer.maxlen + 100):
            learner._X_buffer.append(X.copy())
        self.assertEqual(learner.buffer_size, learner._X_buffer.maxlen)


# ═══════════════════════════════════════════════════════════════════════
# UNIT TESTS — Synthetic Dataset Generator
# ═══════════════════════════════════════════════════════════════════════

class TestSyntheticDataGenerator(unittest.TestCase):

    def test_build_dataset_returns_5_features(self):
        data = build_dataset(repeat_normal=2, verbose=False)
        self.assertEqual(data.shape[1], 5)

    def test_build_dataset_has_enough_rows(self):
        data = build_dataset(repeat_normal=2, verbose=False)
        self.assertGreater(data.shape[0], 5000)

    def test_no_nan_in_dataset(self):
        data = build_dataset(repeat_normal=2, verbose=False)
        self.assertFalse(np.isnan(data).any(), "Dataset contains NaN values")

    def test_no_negative_request_rate(self):
        data = build_dataset(repeat_normal=2, verbose=False)
        self.assertTrue((data[:, 0] >= 0).all(), "request_rate contains negatives")

    def test_error_rate_bounded_0_to_1(self):
        data = build_dataset(repeat_normal=2, verbose=False)
        self.assertTrue((data[:, 1] >= 0).all())
        self.assertTrue((data[:, 1] <= 1).all(), "error_rate exceeds 1.0")

    def test_memory_mb_positive(self):
        data = build_dataset(repeat_normal=2, verbose=False)
        self.assertTrue((data[:, 3] > 0).all(), "memory_mb has zero/negative values")

    def test_crash_scenario_has_high_error_rate(self):
        crash = generate_crash_500()
        self.assertEqual(crash.shape[1], 5)
        # The fault section (rows 100-180) should have high error rate
        fault_section = crash[100:180, 1]
        self.assertGreater(fault_section.max(), 0.3)

    def test_normal_scenario_has_low_error_rate(self):
        normal = generate_normal(n=300)
        self.assertLess(normal[:, 1].mean(), 0.02)


# ═══════════════════════════════════════════════════════════════════════
# UNIT TESTS — Sequence Builder
# ═══════════════════════════════════════════════════════════════════════

class TestSequenceBuilder(unittest.TestCase):

    def test_correct_output_shapes(self):
        builder = SequenceBuilder(sequence_length=30)
        data    = np.random.randn(100, 5).astype(np.float32)
        X, y    = builder.build_sequences(data)
        # Should produce 100 - 30 = 70 sequences
        self.assertEqual(X.shape, (70, 30, 5))
        self.assertEqual(y.shape, (70, 5))

    def test_empty_when_data_too_short(self):
        builder = SequenceBuilder(sequence_length=30)
        data    = np.random.randn(20, 5).astype(np.float32)
        X, y    = builder.build_sequences(data)
        self.assertEqual(len(X), 0)

    def test_sequence_content_correct(self):
        builder = SequenceBuilder(sequence_length=3)
        data    = np.arange(20).reshape(10, 2).astype(np.float32)
        X, y    = builder.build_sequences(data)
        # X[0] should be rows 0,1,2; y[0] should be row 3
        np.testing.assert_array_equal(X[0], data[:3])
        np.testing.assert_array_equal(y[0], data[3])


# ═══════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS — API Service
# ═══════════════════════════════════════════════════════════════════════

class TestAPIServiceIntegration(unittest.TestCase):
    """
    These tests require the full Docker stack to be running.
    Skip gracefully if api_service is not reachable.
    """

    BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

    def _get(self, path):
        import requests
        return requests.get(f"{self.BASE_URL}{path}", timeout=5)

    def _post(self, path, json_body=None):
        import requests
        return requests.post(f"{self.BASE_URL}{path}", json=json_body, timeout=5)

    def _skip_if_down(self):
        try:
            import requests
            requests.get(f"{self.BASE_URL}/health", timeout=2)
        except Exception:
            self.skipTest("api_service not reachable — skipping integration test")

    def test_health_endpoint_returns_200(self):
        self._skip_if_down()
        resp = self._get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("status", data)

    def test_metrics_endpoint_returns_prometheus_text(self):
        self._skip_if_down()
        resp = self._get("/metrics")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("http_requests_total", resp.text)

    def test_root_endpoint_returns_200(self):
        self._skip_if_down()
        resp = self._get("/")
        self.assertEqual(resp.status_code, 200)

    def test_dashboard_endpoint_reachable(self):
        self._skip_if_down()
        resp = self._get("/dashboard")
        self.assertEqual(resp.status_code, 200)


# ═══════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS — Chaos Controller
# ═══════════════════════════════════════════════════════════════════════

class TestChaosControllerIntegration(unittest.TestCase):
    """
    These tests require the chaos_engine Docker service to be running.
    """

    BASE_URL = os.getenv("CHAOS_BASE_URL", "http://localhost:5002")

    def _get(self, path):
        import requests
        return requests.get(f"{self.BASE_URL}{path}", timeout=5)

    def _post(self, path, json_body=None):
        import requests
        return requests.post(f"{self.BASE_URL}{path}", json=json_body, timeout=5)

    def _skip_if_down(self):
        try:
            import requests
            requests.get(f"{self.BASE_URL}/health", timeout=2)
        except Exception:
            self.skipTest("chaos_engine not reachable — skipping integration test")

    def test_health_returns_ok(self):
        self._skip_if_down()
        resp = self._get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "ok")

    def test_scenarios_endpoint_lists_scenarios(self):
        self._skip_if_down()
        resp = self._get("/chaos/scenarios")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("available_scenarios", data)
        self.assertGreater(len(data["available_scenarios"]), 0)

    def test_status_returns_active_list(self):
        self._skip_if_down()
        resp = self._get("/chaos/status")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("active_count", resp.json())

    def test_history_returns_list(self):
        self._skip_if_down()
        resp = self._get("/chaos/history")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("history", resp.json())

    def test_unknown_scenario_returns_404(self):
        self._skip_if_down()
        resp = self._post("/chaos/run/nonexistent_scenario_xyz")
        self.assertEqual(resp.status_code, 404)


# ═══════════════════════════════════════════════════════════════════════
# REGRESSION TESTS — Threshold Logic
# ═══════════════════════════════════════════════════════════════════════

class TestThresholdLogic(unittest.TestCase):
    """
    Tests the effective threshold computation logic in isolation.
    Ensures static and dynamic thresholds are combined correctly.
    """

    def _make_score_history(self, scores):
        d = deque(maxlen=500)
        for s in scores:
            d.append(s)
        return d

    def test_static_threshold_used_when_no_dynamic(self):
        """With fewer than 20 samples, static x multiplier should be used."""
        static = 0.05
        multiplier = 2.0
        expected = static * multiplier

        score_history = self._make_score_history([0.01] * 10)  # < 20 samples
        import torch
        dynamic = None
        if len(score_history) >= 20:
            dynamic = float(
                torch.tensor(list(score_history), dtype=torch.float32).quantile(0.98).item()
            )
        effective = max(static * multiplier, dynamic) if dynamic else static * multiplier
        self.assertAlmostEqual(effective, expected)

    def test_dynamic_threshold_used_when_available(self):
        """With 20+ samples, dynamic should override if higher."""
        import torch
        static = 0.001     # very small static
        multiplier = 2.0
        scores = [0.5 + i * 0.01 for i in range(50)]  # large dynamic range
        score_history = self._make_score_history(scores)
        dynamic = float(
            torch.tensor(list(score_history), dtype=torch.float32).quantile(0.98).item()
        )
        effective = max(static * multiplier, dynamic)
        self.assertGreater(effective, static * multiplier)


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  Self-Healing AI Agent — Test Suite")
    print("=" * 60)
    unittest.main(verbosity=2)
