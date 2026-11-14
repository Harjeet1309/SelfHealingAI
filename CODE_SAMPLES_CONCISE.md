# Code Samples - Essential Snippets

## 1. AI Anomaly Detection (Core)

```python
# LSTM Model
class LSTMForecastModel(nn.Module):
    def __init__(self, input_size=5, hidden_size=32):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, batch_first=True)
        self.fc = nn.Linear(hidden_size, input_size)
    
    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        return self.fc(lstm_out)

# Anomaly Detection
def detect_anomaly(metrics_sequence):
    X = torch.FloatTensor(scaler.transform(metrics_sequence)).unsqueeze(0)
    with torch.no_grad():
        reconstruction = model(X)
        mse = torch.mean((reconstruction - X) ** 2).item()
    return mse > threshold  # True if anomaly
```

## 2. Error Injection

```python
# Inject Fault
@router.post("/inject/{fault_type}")
def inject_fault(fault_type: str):
    system_state[fault_type]["active"] = True
    return {"message": f"Fault {fault_type} injected"}

# Application Endpoint with Fault
@router.post("/checkout")
async def checkout():
    if system_state["checkout"]["active"]:
        raise HTTPException(status_code=500, detail="Checkout crash")
    return {"message": "Success"}
```

## 3. Decision Engine

```python
def determine_remediation(error_rate, cpu_usage):
    if error_rate > 0.5:
        if cpu_usage > 70:
            return "SUPPRESS_RESTART"  # Overload - don't restart
        else:
            return restart_service()   # Deadlock - restart
    return "NO_ACTION"

def restart_service():
    docker_client.containers.get('api_service').restart()
    return verify_recovery()
```

## 4. Metrics Collection

```python
# Prometheus Query
def query_prometheus(promql):
    response = requests.get(f"{PROMETHEUS_URL}/api/v1/query",
                          params={"query": promql})
    return float(response.json()["data"]["result"][0]["value"][1])

# Collect Metrics
metrics = {
    "error_rate": query_prometheus(
        'sum(rate(http_requests_total{status=~"5.."}[30s])) / '
        'sum(rate(http_requests_total[30s]))'
    ),
    "cpu_usage": query_prometheus('rate(process_cpu_seconds_total[30s]) * 100')
}
```

## 5. Docker Configuration

```yaml
# docker-compose.yml
services:
  api_service:
    build: ./api_service
    ports: ["8000:8000"]
  
  prometheus:
    image: prom/prometheus:latest
    ports: ["9090:9090"]
  
  remediation_engine:
    build: ./remediation_engine
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
```

## 6. Training

```python
# Train LSTM
for epoch in range(50):
    X = torch.FloatTensor(normal_data_sequences)
    reconstruction = model(X)
    loss = criterion(reconstruction, X)
    loss.backward()
    optimizer.step()

# Compute Threshold
threshold = np.percentile(reconstruction_errors, 95)
```

## 7. Testing

```powershell
# Test Error Injection
Invoke-WebRequest -Uri "http://localhost:8000/inject/500_checkout?token=changeme-local-dev" -Method POST

# Verify Error Occurs
Invoke-WebRequest -Uri "http://localhost:8000/checkout" -Method POST
# Expected: 500 error

# Watch AI Heal
docker-compose logs -f remediation_engine
```

---

**That's it!** These 7 code snippets cover all major functionality in ~100 lines.
