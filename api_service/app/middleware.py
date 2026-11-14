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

        # EXCLUDE ADMIN/MONITORING/AI TRAFFIC FROM AI KNOWLEDGE
        is_internal = any(endpoint.startswith(p) for p in ["/metrics", "/health", "/dashboard", "/favicon.ico", "/ai/", "/inject/"])
        if is_internal:
            return await call_next(request)

        ACTIVE_REQUESTS.inc()

        # --- Update system-level metrics on every real request ---
        # Memory: RSS in MB
        try:
            mem_mb = _PROCESS.memory_info().rss / (1024 * 1024)
            MEMORY_USAGE_MB.set(mem_mb)
        except PermissionError as e:
            # Docker permission issue - needs SYS_PTRACE capability or --privileged
            print(f"[METRICS WARNING] Memory collection failed (permission denied): {e}")
            print("[METRICS WARNING] Add 'cap_add: [SYS_PTRACE]' to api_service in docker-compose.yml")
            MEMORY_USAGE_MB.set(0.0)
        except Exception as e:
            print(f"[METRICS ERROR] Memory collection failed: {e}")
            MEMORY_USAGE_MB.set(0.0)

        # Active TCP connections held by this process
        try:
            conns = len(_PROCESS.net_connections(kind="tcp"))
            ACTIVE_CONNECTIONS.set(conns)
        except PermissionError as e:
            # Docker permission issue - needs SYS_PTRACE capability or --privileged
            print(f"[METRICS WARNING] Connection collection failed (permission denied): {e}")
            print("[METRICS WARNING] Add 'cap_add: [SYS_PTRACE]' to api_service in docker-compose.yml")
            ACTIVE_CONNECTIONS.set(0.0)
        except Exception as e:
            print(f"[METRICS ERROR] Connection collection failed: {e}")
            ACTIVE_CONNECTIONS.set(0.0)

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