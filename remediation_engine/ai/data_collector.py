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

        # PromQL expressions — 5 features (Aggregated with sum)
        self.queries = {
            "request_rate": 'sum(rate(http_requests_total[10s])) or vector(0)',
            "error_rate": (
                '(sum(rate(http_requests_total{status!="200"}[10s])) or vector(0)) / '
                '(sum(rate(http_requests_total[10s])) > 0 or vector(1))'
            ),
            "p95_latency": (
                'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[10s])) by (le)) or vector(0)'
            ),
            "memory_mb": 'sum(process_memory_mb) or vector(0)',
            "active_connections": 'sum(process_active_connections) or vector(0)',
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
        """
        import time
        end_epoch   = time.time()
        start_epoch = end_epoch - (minutes * 60)
        step        = f"{step_seconds}s"

        results = {}
        for name, query in self.queries.items():
            values = self._query_range(query, start_epoch, end_epoch, step)
            results[name] = values

        # Find the target length (max length returned by any query)
        max_len = max((len(v) for v in results.values()), default=0)
        if max_len == 0:
            # Fallback to fetch_latest to at least get current pulse
            latest = self.fetch_latest()
            return latest

        # Pad shorter series with their last value or zeros to match max_len
        final_series = []
        for name in FEATURE_NAMES:
            series = results.get(name, [])
            if len(series) < max_len:
                last_val = series[-1] if series else 0.0
                padding = [last_val] * (max_len - len(series))
                series = padding + series
            final_series.append(series[-max_len:])

        aligned = np.stack(final_series, axis=1).astype(np.float32)
        return aligned

    def fetch_latest(self) -> np.ndarray:
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

    def _query_range(
        self,
        query: str,
        start: float,
        end: float,
        step: str,
    ) -> List[float]:
        """Execute a single Prometheus range query using float timestamps."""
        try:
            url    = f"{self.base_url}/api/v1/query_range"
            params = {
                "query": query,
                "start": str(start),
                "end":   str(end),
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
