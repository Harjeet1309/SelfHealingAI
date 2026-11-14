
import torch
import os

MODEL_PATH = "./models/lstm_model.pt"

def check_weights():
    if not os.path.exists(MODEL_PATH):
        print("❌ Model not found")
        return
    
    state_dict = torch.load(MODEL_PATH, map_location="cpu")
    has_nan = False
    for name, param in state_dict.items():
        if torch.isnan(param).any():
            print(f"🔴 Found NaNs in {name}")
            has_nan = True
        if torch.isinf(param).any():
            print(f"🔴 Found Infs in {name}")
            has_nan = True
    
    if not has_nan:
        print("✅ No NaNs or Infs in model weights.")

if __name__ == "__main__":
    check_weights()
