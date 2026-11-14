FROM python:3.11-slim

WORKDIR /app

# Install curl for the HEALTHCHECK command
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY watchdog.py .

RUN pip install --no-cache-dir docker==7.0.0 requests==2.31.0

EXPOSE 5003

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5003/ || exit 1

CMD ["python", "watchdog.py"]
