import urllib.request
import json
import os

mermaid_code = """
stateDiagram-v2
    [*] --> Monitor : Start Inference Loop (Every 5s)
    
    state Monitor {
        [*] --> FetchWindow
        FetchWindow --> NormalizeData
    }
    
    Monitor --> LSTMInference
    
    state LSTMInference {
        [*] --> ForecastNextTimestep
        ForecastNextTimestep --> ComputeMSE : Compare with actual
        ComputeMSE --> CheckThreshold
    }
    
    LSTMInference --> DecisionEngine : MSE > Threshold
    LSTMInference --> UpdateBaseline : MSE <= Threshold
    UpdateBaseline --> [*]
    
    state DecisionEngine {
        [*] --> CorroborateTraffic
        CorroborateTraffic --> CheckActiveErrors
        
        state Corroboration_Pass {
            CheckActiveErrors --> FetchDockerStats : Confirm CPU
            FetchDockerStats --> EvaluateAction
        }
        
        state Corroboration_Fail {
            CheckActiveErrors --> IgnoreAnomaly : False Positive
            IgnoreAnomaly --> [*]
        }
    }
    
    DecisionEngine --> Suppress : High CPU (> 70%)
    DecisionEngine --> Restart : Low CPU (Deadlock/Crash)
    
    Suppress --> [*]
    
    state Restart {
        [*] --> DockerRestart
        DockerRestart --> ClearFaults
        ClearFaults --> UpdateDashboard
    }
    
    Restart --> [*]
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
file_path = os.path.join(uml_dir, "activity_diagram.png")
with open(file_path, "wb") as f:
    f.write(response.read())

print(f"Success. Saved to {file_path}")
