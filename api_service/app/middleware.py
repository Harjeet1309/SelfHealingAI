import os
import time
import psutil

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request

from .metrics import (
    REQUEST_COUNT,
    ERROR_COUNT,
    REQUEST_LATENCY,
    ACTIVE_REQUESTS,
    MEMORY_USAGE_MB,
    ACTIVE_CONNECTIONS,
)

# Cache the process handle — cheaper than creating it per-request
_PROCESS = psutil.Process(os.getpid())


class MetricsMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        method   = request.method
        endpoint = request.url.path

        # EXCLUDE ADMIN/MONITORING TRAFFIC FROM AI KNOWLEDGE
        if endpoint in ["/metrics", "/health", "/dashboard", "/favicon.ico"]:
            return await call_next(request)

        ACTIVE_REQUESTS.inc()

        # --- Update system-level metrics on every real request ---
        # Memory: RSS in MB
        try:
            mem_mb = _PROCESS.memory_info().rss / (1024 * 1024)
            MEMORY_USAGE_MB.set(mem_mb)
        except Exception:
            pass

        # Active TCP connections held by this process
        try:
            conns = len(_PROCESS.net_connections(kind="tcp"))
            ACTIVE_CONNECTIONS.set(conns)
        except Exception:
            pass

        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        status = str(response.status_code)

        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()

        if response.status_code >= 400:
            ERROR_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()

        ACTIVE_REQUESTS.dec()
        return response