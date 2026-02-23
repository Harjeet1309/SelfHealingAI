"""
Prometheus Data Collector — V2 (5 features)
=============================================
Queries all 5 Golden Signal features from Prometheus:
    1. request_rate      — HTTP request throughput (req/s)
    2. error_rate        — Fraction of requests returning errors
    3. p95_latency       — 95th percentile response time (seconds)
    4. memory_mb         — RSS memory of the API process (MB)
    5. active_connections — Open TCP connections held by the process
"""

import os
from datetime import datetime, timedelta
from typing import List

import numpy as np
import requests


# Number of features this collector returns — must match model input_size
FEATURE_COUNT = 5
FEATURE_NAMES = ["request_rate", "error_rate", "p95_latency", "memory_mb", "active_connections"]


class PrometheusDataCollector:
    def __init__(self, base_url: str = "http://prometheus:9090"):
        self.base_url       = os.getenv("PROMETHEUS_URL", base_url)
        self.request_timeout = int(os.getenv("PROMETHEUS_TIMEOUT_SECONDS", "10"))

        # PromQL expressions — 5 features
        self.queries = {
            # 1. Request throughput
            "request_rate": (
                'sum(rate(http_requests_total[30s])) or vector(0)'
            ),

            # 2. Error rate — fraction of requests that returned a non-200 status
            "error_rate": (
                '('
                '  sum(rate(http_requests_total{status!="200"}[30s])) or vector(0)'
                ') / ('
                '  (sum(rate(http_requests_total[30s])) > 0) or vector(1)'
                ')'
            ),

            # 3. p95 latency in seconds
            "p95_latency": (
                'histogram_quantile(0.95,'
                '  sum(rate(http_request_duration_seconds_bucket[30s])) by (le)'
                ') or vector(0)'
            ),

            # 4. RSS memory in MB — exposed by MetricsMiddleware via psutil
            "memory_mb": (
                'process_memory_mb or vector(0)'
            ),

            # 5. Active TCP connections — exposed by MetricsMiddleware via psutil
            "active_connections": (
                'process_active_connections or vector(0)'
            ),
        }

    # ──────────────────────────────────────────────────────────────────
    # PUBLIC
    # ──────────────────────────────────────────────────────────────────

    def fetch_window(
        self,
        minutes: int = 20,
        step_seconds: int = 5,
    ) -> np.ndarray:
        """
        Fetch a time-window of all 5 features from Prometheus.

        Returns:
            np.ndarray of shape (timesteps, 5) — clipped to shortest series.
            Returns zeros of shape (1, 5) if Prometheus is unreachable.
        """
        end   = datetime.utcnow()
        start = end - timedelta(minutes=minutes)
        step  = f"{step_seconds}s"

        results = {}
        for name, query in self.queries.items():
            values = self._query_range(query, start, end, step)
            results[name] = values

        # Align all series to the same length
        min_len = min(len(v) for v in results.values())
        if min_len == 0:
            return np.zeros((1, FEATURE_COUNT), dtype=np.float32)

        aligned = np.stack(
            [results[name][-min_len:] for name in FEATURE_NAMES],
            axis=1,
        ).astype(np.float32)

        return aligned

    def fetch_latest(self) -> np.ndarray:
        """
        Fetch only the most recent single data point for all 5 features.
        Returns np.ndarray of shape (1, 5).
        Used for real-time logging and quick spot checks.
        """
        results = {}
        for name, query in self.queries.items():
            try:
                url    = f"{self.base_url}/api/v1/query"
                params = {"query": query}
                resp   = requests.get(url, params=params, timeout=self.request_timeout)
                data   = resp.json()
                res    = data.get("data", {}).get("result", [])
                value  = float(res[0]["value"][1]) if res else 0.0
                results[name] = value
            except Exception:
                results[name] = 0.0

        row = np.array([[results[name] for name in FEATURE_NAMES]], dtype=np.float32)
        return row

    # ──────────────────────────────────────────────────────────────────
    # PRIVATE
    # ──────────────────────────────────────────────────────────────────

    def _query_range(
        self,
        query: str,
        start: datetime,
        end: datetime,
        step: str,
    ) -> List[float]:
        """Execute a single Prometheus range query. Returns list of float values."""
        try:
            url    = f"{self.base_url}/api/v1/query_range"
            params = {
                "query": query,
                "start": start.isoformat() + "Z",
                "end":   end.isoformat()   + "Z",
                "step":  step,
            }
            resp = requests.get(url, params=params, timeout=self.request_timeout)
            data = resp.json()
            result = data.get("data", {}).get("result", [])
            if not result:
                return []
            return [float(v[1]) for v in result[0]["values"]]
        except Exception:
            return []
