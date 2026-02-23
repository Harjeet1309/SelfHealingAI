from prometheus_client import Counter, Histogram, Gauge

# Total HTTP Requests
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status"]
)

# Total Error Requests
ERROR_COUNT = Counter(
    "http_errors_total",
    "Total number of HTTP error responses",
    ["method", "endpoint", "status"]
)

# Request Latency Histogram
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"]
)

# Active Requests Gauge
ACTIVE_REQUESTS = Gauge(
    "http_active_requests",
    "Number of active HTTP requests"
)

# --- NEW: Feature 4 — Process Memory Usage ---
MEMORY_USAGE_MB = Gauge(
    "process_memory_mb",
    "RSS memory of the API service process in megabytes"
)

# --- NEW: Feature 5 — Active TCP Connections ---
ACTIVE_CONNECTIONS = Gauge(
    "process_active_connections",
    "Number of open TCP connections held by the API process"
)