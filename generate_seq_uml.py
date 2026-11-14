import urllib.request
import json
import os

mermaid_code = """
sequenceDiagram
    participant P as Prometheus
    participant A as API Service (Luxe AI)
    participant R as Remediation Engine
    participant D as Docker Daemon

    rect rgb(30, 30, 30)
    Note over P, A: Monitoring Phase
    loop Every 5 Seconds
        P->>A: Scrape /metrics
        A-->>P: Respond with Telemetry (CPU, Latency, Errors)
    end
    end

    rect rgb(40, 20, 20)
    Note over P, D: Analysis & Remediation Phase
    loop Every 5 Seconds
        R->>P: Fetch Metric Window (/api/v1/query_range)
        P-->>R: Return Time-Series Data
        Note over R: LSTM Inference & Rule Check
        
        alt Anomaly Detected
            Note over R: Decision Engine Analysis
            alt High CPU (Overload)
                R->>R: Suppress Restart
            else Normal CPU (Deadlock/Crash)
                R->>D: container.restart()
                Note over D: Kills & Restarts API Container
                D-->>R: Restart Confirmed
                R->>A: Reset Active Faults
                R->>A: Update AI Dashboard Stats
            end
        end
    end
    end
"""

uml_dir = r"c:\Users\gudde\Desktop\SelfHealingAI\uml"
os.makedirs(uml_dir, exist_ok=True)

data = json.dumps({"diagram_source": mermaid_code}).encode("utf-8")
req = urllib.request.Request(
    "https://kroki.io/mermaid/png", 
    data=data, 
    headers={
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
)

response = urllib.request.urlopen(req)
file_path = os.path.join(uml_dir, "sequence_diagram.png")
with open(file_path, "wb") as f:
    f.write(response.read())

print(f"Success. Saved to {file_path}")
