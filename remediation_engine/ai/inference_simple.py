"""
Simple LSTM Inference Engine
=============================
Clean, focused implementation that WORKS.

Core functionality:
1. Load trained LSTM model
2. Collect metrics from Prometheus
3. Build sequences (30 timesteps)
4. Compute MSE (reconstruction error)
5. Compare to threshold
6. Trigger remediation if anomaly detected
"""

import os
import json
import time
import torch
import joblib
import requests
import numpy as np
from datetime import datetime
from collections import deque

# Import existing components
from remediation_engine.ai.decision_engine import DecisionEngine


class SimpleLSTMInference:
    def __init__(self):
        # Configuration
        self.prometheus_url = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
        self.sequence_length = 30
        self.poll_interval = 5  # seconds
        self.threshold = 2.45  # From training
        
        # Paths
        model_dir = "/models" if os.path.exists("/models") else "models"
        self.model_path = os.path.join(model_dir, "lstm_model.pt")
        self.scaler_path = os.path.join(model_dir, "scaler.pkl")
        self.threshold_path = os.path.join(model_dir, "threshold.json")
        
        # Load artifacts
        self._load_model()
        
        # Decision engine for remediation
        self.decision_engine = DecisionEngine(
            api_url=os.getenv("API_REPORT_URL", "http://api_service:8000/ai/report"),
            api_reset_url=os.getenv("API_RESET_URL", "http://api_service:8000/inject/reset?target=all"),
            token=os.getenv("INJECT_TOKEN", "changeme-local-dev")
        )
        
        # Metrics buffer
        self.metrics_buffer = deque(maxlen=100)
        self.anomaly_counter = 0
        self.anomaly_confirmation_needed = 2
        
        print(f"[SIMPLE-LSTM] Initialized successfully")
        print(f"[SIMPLE-LSTM] Model: {self.model_path}")
        print(f"[SIMPLE-LSTM] Threshold: {self.threshold:.6f}")
        print(f"[SIMPLE-LSTM] Sequence length: {self.sequence_length}")
    
    def _load_model(self):
        """Load LSTM model and scaler"""
        # Load scaler
        self.scaler = joblib.load(self.scaler_path)
        input_size = self.scaler.mean_.shape[0]
        
        # Load threshold
        try:
            with open(self.threshold_path, 'r') as f:
                data = json.load(f)
                threshold_value = data.get("threshold", 2.45)
                # If threshold is 0 or corrupted, use static_threshold or default
                if threshold_value == 0.0 or threshold_value < 0.1:
                    threshold_value = data.get("static_threshold", 2.45)
                self.threshold = threshold_value
        except:
            self.threshold = 2.45  # Default from training
        
        # Load model
        from remediation_engine.ai.lstm_model import LSTMForecastModel
        self.model = LSTMForecastModel(
            input_size=input_size,
            hidden_size=32,
            num_layers=1
        )
        self.model.load_state_dict(torch.load(self.model_path, map_location="cpu"))
        self.model.eval()
        
        print(f"[SIMPLE-LSTM] Model loaded: {input_size} features, threshold={self.threshold:.6f}")
    
    def _query_prometheus(self, query):
        """Query Prometheus for a metric"""
        try:
            response = requests.get(
                f"{self.prometheus_url}/api/v1/query",
                params={"query": query},
                timeout=3
            )
            result = response.json()
            if result["status"] == "success" and result["data"]["result"]:
                val = float(result["data"]["result"][0]["value"][1])
                import math
                if math.isnan(val) or math.isinf(val):
                    return 0.0
                return val
            return 0.0
        except:
            return 0.0
    
    def _collect_current_metrics(self):
        """Collect current metrics snapshot"""
        metrics = {
            "request_rate": self._query_prometheus(
                'sum(rate(http_requests_total[30s])) or vector(0)'
            ),
            "error_rate": self._query_prometheus(
                'sum(rate(http_requests_total{status=~"5.."}[30s])) / '
                'sum(rate(http_requests_total[30s])) or vector(0)'
            ),
            "p95_latency": self._query_prometheus(
                'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[30s])) by (le)) or vector(0)'
            ),
            "memory_mb": self._query_prometheus(
                'sum(process_memory_mb) or vector(0)'
            ),
            "active_connections": self._query_prometheus(
                'sum(process_active_connections) or vector(0)'
            ),
        }
        
        # Return as array
        return np.array([
            metrics["request_rate"],
            metrics["error_rate"],
            metrics["p95_latency"],
            metrics["memory_mb"],
            metrics["active_connections"]
        ])
    
    def _compute_mse(self, sequence):
        """Compute MSE using LSTM autoencoder"""
        # Scale sequence
        sequence_scaled = self.scaler.transform(sequence)
        
        # Convert to tensor (batch_size=1, seq_len=30, features=5)
        X = torch.FloatTensor(sequence_scaled).unsqueeze(0)
        
        # Get reconstruction
        with torch.no_grad():
            reconstruction = self.model(X)
        
        # Compute MSE
        mse = torch.mean((reconstruction - X) ** 2).item()
        
        return mse
    
    def _push_telemetry(self, mse, metrics):
        """Send telemetry to dashboard"""
        url = os.getenv("API_REPORT_URL", "http://api_service:8000/ai/report").replace("/ai/report", "/ai/telemetry/push")
        token = os.getenv("INJECT_TOKEN", "changeme-local-dev")
        
        payload = {
            "mse_score": mse,
            "threshold": self.threshold,
            "request_rate": float(metrics[0]),
            "error_rate": float(metrics[1]),
            "p95_latency": float(metrics[2]),
            "memory_mb": float(metrics[3]),
            "active_conns": float(metrics[4]),
            "online_buffer": 0
        }
        
        try:
            requests.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
                timeout=2
            )
        except:
            pass
    
    def run(self):
        """Main monitoring loop"""
        print("[SIMPLE-LSTM] Starting monitoring loop...")
        print("[SIMPLE-LSTM] Collecting initial samples...")
        
        while True:
            try:
                # Collect current metrics
                current_metrics = self._collect_current_metrics()
                
                # --- ZERO WAIT-TIME STARTUP FIX ---
                # Pre-fill buffer with initial metrics so we don't wait 2.5 minutes to start
                if len(self.metrics_buffer) == 0:
                    print(f"[SIMPLE-LSTM] Fast-forwarding warmup sequence...")
                    for _ in range(self.sequence_length - 1):
                        self.metrics_buffer.append(current_metrics)
                
                self.metrics_buffer.append(current_metrics)
                
                # Build sequence from last N samples
                sequence = np.array(list(self.metrics_buffer)[-self.sequence_length:])
                
                # --- IDLE STATE SANITIZATION ---
                # A neural network will output huge errors for [0,0,0,0,0] inputs if it was only trained on active traffic.
                # If there are virtually no requests and no errors, the system is nominal. We force MSE to 0.0.
                recent_reqs = np.mean(sequence[:, 0])
                recent_errs = np.mean(sequence[:, 1])
                
                if recent_reqs < 0.5 and recent_errs < 0.01:
                    mse = 0.0
                else:
                    # Compute real MSE
                    mse = self._compute_mse(sequence)
                
                # Push telemetry to dashboard
                self._push_telemetry(mse, current_metrics)
                
                # Check for anomaly
                is_anomaly = mse > self.threshold
                
                # Print monitoring pulse
                timestamp = datetime.now().strftime("%H:%M:%S")
                status = "🔴 ANOMALY" if is_anomaly else "🟢 NORMAL"
                print(f"\n[{timestamp}] {status}")
                print(f"  MSE: {mse:.6f} | Threshold: {self.threshold:.6f}")
                print(f"  Req/s: {current_metrics[0]:.2f} | Err: {current_metrics[1]*100:.1f}% | Latency: {current_metrics[2]*1000:.1f}ms")
                
                # Anomaly confirmation logic
                if is_anomaly:
                    self.anomaly_counter += 1
                    print(f"  Anomaly confirmation: {self.anomaly_counter}/{self.anomaly_confirmation_needed}")
                    
                    if self.anomaly_counter >= self.anomaly_confirmation_needed:
                        print(f"\n{'='*60}")
                        print(f"🚨 ANOMALY CONFIRMED - Triggering remediation")
                        print(f"{'='*60}\n")
                        
                        # Trigger remediation
                        result = self.decision_engine.determine_remediation("AI_ANOMALY_DETECTED")
                        
                        if result != "COOLDOWN_ACTIVE":
                            self.anomaly_counter = 0
                            # --- POST-RECOVERY SANITIZATION ---
                            # Empty the old anomalous sequence data out of memory so we don't instantly re-trigger 
                            # the moment the container comes back online.
                            self.metrics_buffer.clear()
                        else:
                            # Keep counter high during cooldown
                            self.anomaly_counter = max(self.anomaly_confirmation_needed - 1, 0)
                else:
                    self.anomaly_counter = 0
                
            except Exception as e:
                print(f"[SIMPLE-LSTM] Error in monitoring loop: {e}")
                import traceback
                traceback.print_exc()
            
            time.sleep(self.poll_interval)


if __name__ == "__main__":
    engine = SimpleLSTMInference()
    engine.run()
