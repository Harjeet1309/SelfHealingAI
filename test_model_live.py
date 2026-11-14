
import os
import torch
import joblib
import numpy as np
import json
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from remediation_engine.ai.lstm_model import LSTMForecastModel
from remediation_engine.ai.feature_builder import SequenceBuilder

MODEL_PATH = "./models/lstm_model.pt"
SCALER_PATH = "./models/scaler.pkl"
THRESHOLD_PATH = "./models/threshold.json"

def test_inference():
    print("--- Testing Inference Artifacts ---")
    
    # Check if files exist
    for p in [MODEL_PATH, SCALER_PATH, THRESHOLD_PATH]:
        if not os.path.exists(p):
            print(f"❌ Missing file: {p}")
            return

    # Load artifacts
    scaler = joblib.load(SCALER_PATH)
    print(f"✅ Scaler: {scaler.mean_.shape[0]} features")
    print(f"   Means: {scaler.mean_}")
    print(f"   Scales: {scaler.scale_}")

    input_size = scaler.mean_.shape[0]
    model = LSTMForecastModel(input_size=input_size)
    model.load_state_dict(torch.load(MODEL_PATH, map_location="cpu"))
    model.eval()
    print(f"✅ Model loaded. Input size: {input_size}")

    with open(THRESHOLD_PATH, "r") as f:
        thr_data = json.load(f)
        print(f"✅ Threshold: {thr_data['threshold']}")

    # Exactly as seen in user's Iteration #46
    # rr        : 0.2009
    # er          : 1.0000
    # p95         : 0.0425
    # mem           : 0.0000
    # conns  : 0.0000
    user_crash_row = [0.2009, 1.0000, 0.0425, 0.0, 0.0]
    
    # Let's assume some typical normal values for the history
    user_normal_row = [1.4, 0.005, 0.15, 85.0, 8.0]

    # Test 4: Replicate user's state (all crash)
    data_user = np.array([user_crash_row] * 31, dtype=np.float32)
    scaled_user = scaler.transform(data_user)
    
    X_u = torch.tensor(scaled_user[:-1], dtype=torch.float32).unsqueeze(0)
    y_u = torch.tensor(scaled_user[-1:], dtype=torch.float32)
    
    with torch.no_grad():
        pred_u = model(X_u)
        mse_u = torch.mean((pred_u - y_u)**2).item()
    
    print(f"\nTest 4 (User Crash Row -> User Crash Row):")
    print(f"   X_scaled last step: {X_u[0, -1]}")
    print(f"   y_tensor          : {y_u}")
    print(f"   pred              : {pred_u}")
    print(f"   MSE               : {mse_u:.6f}")
    if np.isnan(mse_u): print("   (IS NAN!)")

    # Test 5: What if data is ALL identical?
    data_identical = np.zeros((31, 5), dtype=np.float32)
    scaled_id = scaler.transform(data_identical)
    X_id = torch.tensor(scaled_id[:-1], dtype=torch.float32).unsqueeze(0)
    y_id = torch.tensor(scaled_id[-1:], dtype=torch.float32)
    with torch.no_grad():
        pred_id = model(X_id)
        mse_id = torch.mean((pred_id - y_id)**2).item()
    print(f"\nTest 5 (All Zeros):")
    print(f"   MSE: {mse_id:.6f}")

if __name__ == "__main__":
    test_inference()
