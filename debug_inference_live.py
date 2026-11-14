
import os
import sys
import time
import json
import torch
import joblib
import numpy as np
import requests
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from remediation_engine.ai.data_collector import PrometheusDataCollector, FEATURE_NAMES
from remediation_engine.ai.feature_builder import SequenceBuilder
from remediation_engine.ai.lstm_model import LSTMForecastModel


# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
MODEL_PATH = os.getenv("MODEL_PATH", "./models/lstm_model.pt")
SCALER_PATH = os.getenv("SCALER_PATH", "./models/scaler.pkl")
THRESHOLD_PATH = os.getenv("THRESHOLD_PATH", "./models/threshold.json")
SEQUENCE_LENGTH = 30
WINDOW_MINUTES = 20
STEP_SECONDS = 5
POLL_INTERVAL = 5

# Threshold config
THRESHOLD_MULTIPLIER = 4.0
MIN_REQUEST_RATE = 0.05
MIN_ERROR_RATE = 0.02
MIN_P95_LATENCY = 1.5


# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def query_prometheus(query: str, minutes: int = 20, step: str = "5s"):
    """Execute a Prometheus range query."""
    try:
        end = datetime.utcnow()
        start = end - timedelta(minutes=minutes)
        
        url = f"{PROMETHEUS_URL}/api/v1/query_range"
        params = {
            "query": query,
            "start": start.isoformat() + "Z",
            "end": end.isoformat() + "Z",
            "step": step,
        }
        
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        result = data.get("data", {}).get("result", [])
        
        if not result:
            return []
        
        return [float(v[1]) for v in result[0]["values"]]
    
    except Exception as e:
        print(f"❌ Prometheus query failed: {e}")
        return []


def check_corroboration(features):
    """Check if error signals are corroborated by traffic and failures."""
    has_traffic = features.get("request_rate", 0.0) >= MIN_REQUEST_RATE
    has_failure = (
        features.get("error_rate", 0.0) >= MIN_ERROR_RATE
        or features.get("p95_latency", 0.0) >= MIN_P95_LATENCY
    )
    
    return has_traffic and has_failure


def print_separator():
    print("\n" + "=" * 80 + "\n")


# ═══════════════════════════════════════════════════════════════
# MAIN MONITORING LOOP
# ═══════════════════════════════════════════════════════════════

def main():
    print_separator()
    print("🔍 LIVE SELF-HEALING AI DEBUGGER")
    print_separator()
    print(f"Prometheus: {PROMETHEUS_URL}")
    print(f"Model: {MODEL_PATH}")
    print(f"Poll Interval: {POLL_INTERVAL}s")
    print_separator()
    
    # Load model and scaler
    print("Loading ML artifacts...")
    try:
        scaler = joblib.load(SCALER_PATH)
        print(f"✅ Scaler loaded: {scaler.mean_.shape[0]} features")
        
        input_size = scaler.mean_.shape[0]
        model = LSTMForecastModel(
            input_size=input_size,
            hidden_size=128,
            num_layers=2,
            dropout=0.25,
            num_attention_heads=4,
            attention_dropout=0.1,
        )
        model.load_state_dict(torch.load(MODEL_PATH, map_location="cpu"))
        model.eval()
        print(f"✅ Model loaded: input_size={input_size}")
        
        with open(THRESHOLD_PATH, "r") as f:
            threshold_data = json.load(f)
            static_threshold = threshold_data["threshold"] * THRESHOLD_MULTIPLIER
        print(f"✅ Threshold loaded: {static_threshold:.6f}")
        
    except Exception as e:
        print(f"❌ Failed to load ML artifacts: {e}")
        print("Make sure Docker containers are running!")
        return
    
    print_separator()
    print("Starting live monitoring... Press Ctrl+C to stop.")
    print_separator()
    
    iteration = 0
    score_history = []
    
    while True:
        try:
            iteration += 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # ── STEP 1: FETCH RAW METRICS FROM PROMETHEUS ────────────────
            print(f"\n[{timestamp}] Iteration #{iteration}")
            print("-" * 80)
            
            queries = {
                "request_rate": 'sum(rate(http_requests_total[30s])) or vector(0)',
                "error_rate": (
                    '('
                    '  sum(rate(http_requests_total{status!="200"}[30s])) or vector(0)'
                    ') / ('
                    '  (sum(rate(http_requests_total[30s])) > 0) or vector(1)'
                    ')'
                ),
                "p95_latency": (
                    'histogram_quantile(0.95,'
                    '  sum(rate(http_request_duration_seconds_bucket[30s])) by (le)'
                    ') or vector(0)'
                ),
                "memory_mb": 'process_memory_mb or vector(0)',
                "active_connections": 'process_active_connections or vector(0)',
            }
            
            results = {}
            for name, query in queries.items():
                values = query_prometheus(query, minutes=WINDOW_MINUTES, step=f"{STEP_SECONDS}s")
                results[name] = values
            
            # Check if we have enough data
            min_len = min(len(v) for v in results.values()) if results else 0
            if min_len == 0:
                print("⚠️  No data from Prometheus yet. Waiting for more samples...")
                time.sleep(POLL_INTERVAL)
                continue
            
            print(f"📊 Data points collected: {min_len} (need >{SEQUENCE_LENGTH} for AI)")
            
            # Show latest values
            print("\n📈 LATEST METRICS FROM PROMETHEUS:")
            features = {}
            for name in FEATURE_NAMES:
                value = results[name][-1] if results[name] else 0.0
                features[name] = value
                
                # Color-code based on severity
                if name == "error_rate" and value > 0.1:
                    print(f"  🔴 {name:20s}: {value:.4f}")
                elif name == "p95_latency" and value > 2.0:
                    print(f"  🟠 {name:20s}: {value:.2f}s")
                else:
                    print(f"  ⚪ {name:20s}: {value:.4f}")
            
            # ── STEP 2: COMPUTE AI SCORE ─────────────────────────────────
            if min_len <= SEQUENCE_LENGTH:
                print(f"\n⏳ Need {SEQUENCE_LENGTH - min_len + 1} more data points for AI analysis...")
                time.sleep(POLL_INTERVAL)
                continue
            
            # Build feature array
            data = np.stack([results[name][-min_len:] for name in FEATURE_NAMES], axis=1).astype(np.float32)
            scaled = scaler.transform(data)
            
            builder = SequenceBuilder(sequence_length=SEQUENCE_LENGTH)
            X, y = builder.build_sequences(scaled)
            
            if len(X) == 0:
                print("⚠️  No sequences built. Check data quality.")
                time.sleep(POLL_INTERVAL)
                continue
            
            # Run inference
            last_X = X[-1]
            last_y = y[-1]
            
            X_tensor = torch.tensor(X[-1:], dtype=torch.float32)
            y_tensor = torch.tensor(y[-1:], dtype=torch.float32)
            
            with torch.no_grad():
                prediction = model(X_tensor)
                mse_score = torch.mean((prediction - y_tensor) ** 2).item()
                if np.isnan(mse_score):
                    mse_score = 0.0
            
            score_history.append(mse_score)
            
            # Compute dynamic threshold
            effective_threshold = static_threshold
            dynamic_threshold = None
            if len(score_history) >= 20:
                dynamic_threshold = float(
                    torch.tensor(score_history, dtype=torch.float32).quantile(0.98).item()
                )
                effective_threshold = max(static_threshold, dynamic_threshold)
            
            # ── STEP 3: DISPLAY ANALYSIS ─────────────────────────────────
            print(f"\n🧠 AI ANOMALY DETECTION:")
            print(f"  MSE Score:           {mse_score:.6f}")
            print(f"  Static Threshold:    {static_threshold:.6f}")
            if dynamic_threshold:
                print(f"  Dynamic Threshold:   {dynamic_threshold:.6f}")
            print(f"  Effective Threshold: {effective_threshold:.6f}")
            
            # Check if anomaly detected
            is_anomaly = mse_score > effective_threshold
            print(f"\n  {'🔴 ANOMALY DETECTED!' if is_anomaly else '🟢 Normal operation'}")
            print(f"     Score ({mse_score:.4f}) {'>' if is_anomaly else '<='} Threshold ({effective_threshold:.4f})")
            
            # ── STEP 4: CORROBORATION CHECK ──────────────────────────────
            corroborated = check_corroboration(features)
            print(f"\n🔍 CORROBORATION CHECK:")
            print(f"  Has Traffic:      {'✅' if features['request_rate'] >= MIN_REQUEST_RATE else '❌'} (rate={features['request_rate']:.3f})")
            print(f"  Has Errors:       {'✅' if features['error_rate'] >= MIN_ERROR_RATE else '❌'} (rate={features['error_rate']:.3f})")
            print(f"  High Latency:     {'✅' if features['p95_latency'] >= MIN_P95_LATENCY else '❌'} (latency={features['p95_latency']:.2f}s)")
            print(f"  Corroborated:     {'✅ YES' if corroborated else '❌ NO'}")
            
            # ── STEP 5: REMEDIATION DECISION ─────────────────────────────
            print(f"\n🛠️  REMEDIATION STATUS:")
            if is_anomaly and corroborated:
                print(f"  ⚡ TRIGGER REMEDIATION!")
                print(f"     → Action: Restart api_service container")
                print(f"     → Reason: AI detected behavioral anomaly")
            elif is_anomaly and not corroborated:
                print(f"  ⚠️  Anomaly detected but NOT corroborated")
                print(f"     → No action taken (likely false positive)")
            else:
                print(f"  ✅ No action needed - system healthy")
            
            # ── STEP 6: QUICK DIAGNOSTICS ────────────────────────────────
            print(f"\n📋 QUICK DIAGNOSTICS:")
            print(f"  Total samples:     {min_len}")
            print(f"  Sequences built:   {len(X)}")
            print(f"  Score history:     {len(score_history)} samples")
            print(f"  Avg MSE (recent):  {np.mean(score_history[-10:]):.6f}")
            print(f"  Max MSE (recent):  {np.max(score_history[-10:]):.6f}")
            
            print_separator()
            
        except KeyboardInterrupt:
            print("\n\n👋 Debugger stopped by user.")
            break
        except Exception as e:
            print(f"\n❌ Error in monitoring loop: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(POLL_INTERVAL)
        
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()