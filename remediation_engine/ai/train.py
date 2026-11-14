"""
Upgraded LSTM Training Pipeline — V2
======================================
Improvements over V1:
  - Trains on large synthetic dataset (10 000+ timesteps) instead of 20 min live data
  - Proper 80/20 train / validation split
  - Early stopping on validation loss (patience=15)
  - ReduceLROnPlateau learning rate scheduler
  - Gradient clipping to prevent exploding gradients
  - Threshold computed from VALIDATION set MSE (not training set) — more realistic
  - Threshold uses 99th percentile of val MSE (not mean+3std) — cleaner bound
  - Saves best checkpoint only (lowest val loss)
  - Full training report printed at end
"""

import os
import json
import joblib
import torch
import torch.nn as nn
import numpy as np

from torch.utils.data import DataLoader, TensorDataset, random_split
from sklearn.preprocessing import StandardScaler

from remediation_engine.ai.synthetic_data_generator import build_dataset
from remediation_engine.ai.feature_builder import SequenceBuilder
from remediation_engine.ai.lstm_model import LSTMForecastModel


# ─────────────────────────────────────────────
# TRAINING CONFIGURATION
# ─────────────────────────────────────────────

SEQUENCE_LENGTH     = 30
EPOCHS              = 120          # high ceiling — early stopping will cut this short
BATCH_SIZE          = 64
LEARNING_RATE       = 5e-4
WEIGHT_DECAY        = 1e-5         # L2 regularization
GRAD_CLIP           = 1.0          # max gradient norm
VAL_SPLIT           = 0.20         # 20% held out for validation
PATIENCE            = 15           # early stopping patience (epochs)
LR_PATIENCE         = 7            # ReduceLROnPlateau patience
LR_FACTOR           = 0.5          # LR reduced by this factor on plateau
MIN_LR              = 1e-6
THRESHOLD_PERCENTILE = 99.0        # percentile of val MSE used as threshold

MODEL_DIR           = os.path.join(os.path.dirname(__file__), "..", "..", "models")
DEVICE              = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Feature Significance Weights: [request_rate, error_rate, p95_latency, memory_mb, active_connections]
# Matches InferenceEngine V4 priorities
FEATURE_WEIGHTS = torch.tensor([1.0, 10.0, 3.0, 1.0, 1.0], dtype=torch.float32).to(DEVICE)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _print_header(title):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")


def _evaluate(model, loader, criterion, device):
    """Run one full pass over a dataloader and return average loss."""
    model.eval()
    total_loss = 0.0
    with torch.no_grad():
        for batch_X, batch_y in loader:
            batch_X, batch_y = batch_X.to(device), batch_y.to(device)
            pred = model(batch_X)
            sq_diff = (pred - batch_y) ** 2
            loss = torch.mean(sq_diff * FEATURE_WEIGHTS)
            total_loss += loss.item()
    return total_loss / len(loader)


# ─────────────────────────────────────────────
# MAIN TRAINING FUNCTION
# ─────────────────────────────────────────────

def train():
    os.makedirs(MODEL_DIR, exist_ok=True)

    _print_header("STEP 1 — Generating Synthetic Dataset")
    data = build_dataset(repeat_normal=10, smooth_window=3, verbose=True)

    _print_header("STEP 2 — Normalizing Features")
    scaler = StandardScaler()
    scaled = scaler.fit_transform(data)
    print(f"  Scaler fitted on {data.shape[0]} timesteps.")
    print(f"  Feature means  : {scaler.mean_}")
    print(f"  Feature scales : {scaler.scale_}")

    _print_header("STEP 3 — Building Sequences")
    builder = SequenceBuilder(sequence_length=SEQUENCE_LENGTH)
    X, y = builder.build_sequences(scaled)

    if len(X) == 0:
        raise RuntimeError(
            f"No sequences built. data has {scaled.shape[0]} rows "
            f"but SEQUENCE_LENGTH={SEQUENCE_LENGTH}. Increase dataset size."
        )

    print(f"  X shape: {X.shape}   (samples, seq_len, features)")
    print(f"  y shape: {y.shape}   (samples, features)")

    X_t = torch.tensor(X, dtype=torch.float32)
    y_t = torch.tensor(y, dtype=torch.float32)

    dataset   = TensorDataset(X_t, y_t)
    val_size  = int(len(dataset) * VAL_SPLIT)
    train_size = len(dataset) - val_size
    train_ds, val_ds = random_split(dataset, [train_size, val_size],
                                    generator=torch.Generator().manual_seed(42))

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,  num_workers=0)
    val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    print(f"  Train samples : {train_size}")
    print(f"  Val   samples : {val_size}")

    _print_header("STEP 4 — Model Initialisation")
    input_size = data.shape[1]
    model = LSTMForecastModel(
        input_size=input_size,
        hidden_size=128,
        num_layers=2,
        dropout=0.25,
        num_attention_heads=4,
        attention_dropout=0.1,
        bidirectional=False,
    ).to(DEVICE)

    total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  Device       : {DEVICE}")
    print(f"  Parameters   : {total_params:,}")
    print(f"  Architecture :")
    print(model)

    criterion  = nn.MSELoss()
    optimizer  = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    scheduler  = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=LR_FACTOR, patience=LR_PATIENCE, min_lr=MIN_LR
    )

    _print_header("STEP 5 — Training Loop")
    best_val_loss   = float("inf")
    best_epoch      = 0
    patience_counter = 0
    best_state      = None
    history         = {"train": [], "val": []}

    for epoch in range(1, EPOCHS + 1):
        # ── Train ──
        model.train()
        train_loss = 0.0
        for batch_X, batch_y in train_loader:
            batch_X, batch_y = batch_X.to(DEVICE), batch_y.to(DEVICE)
            optimizer.zero_grad()
            pred = model(batch_X)
            # ── Weighted MSE Training ──
            sq_diff = (pred - batch_y) ** 2
            loss = torch.mean(sq_diff * FEATURE_WEIGHTS)
            
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), GRAD_CLIP)
            optimizer.step()
            train_loss += loss.item()
        train_loss /= len(train_loader)

        # ── Validate ──
        val_loss = _evaluate(model, val_loader, criterion, DEVICE)
        scheduler.step(val_loss)

        history["train"].append(train_loss)
        history["val"].append(val_loss)

        # ── Checkpoint ──
        improved = val_loss < best_val_loss
        if improved:
            best_val_loss    = val_loss
            best_epoch       = epoch
            patience_counter = 0
            best_state       = {k: v.clone() for k, v in model.state_dict().items()}
        else:
            patience_counter += 1

        current_lr = optimizer.param_groups[0]["lr"]
        marker = "✓" if improved else " "
        print(
            f"  [{marker}] Epoch {epoch:4d}/{EPOCHS} "
            f"| Train: {train_loss:.6f} "
            f"| Val: {val_loss:.6f} "
            f"| LR: {current_lr:.2e} "
            f"| Patience: {patience_counter}/{PATIENCE}"
        )

        # ── Early stopping ──
        if patience_counter >= PATIENCE:
            print(f"\n  Early stopping triggered at epoch {epoch}.")
            print(f"  Best epoch was {best_epoch} with val_loss={best_val_loss:.6f}")
            break

    _print_header("STEP 6 — Computing Anomaly Threshold")
    # Restore best weights
    model.load_state_dict(best_state)
    model.eval()

    # Compute per-sample MSE on the VALIDATION set (unseen during training)
    all_mse = []
    with torch.no_grad():
        for batch_X, batch_y in val_loader:
            batch_X, batch_y = batch_X.to(DEVICE), batch_y.to(DEVICE)
            pred = model(batch_X)
            
            # --- Aligned Hybrid Identification Logic (Matches Inference V4) ---
            # 1. Prediction Error
            sq_diff_pred = (pred - batch_y) ** 2
            pred_err = torch.mean(sq_diff_pred * FEATURE_WEIGHTS, dim=1)
            
            # 2. State Deviation (how far is truth from healthy zero)
            sq_diff_dev = (batch_y ** 2)
            state_dev = torch.mean(sq_diff_dev * FEATURE_WEIGHTS, dim=1)
            
            # Hybrid Score
            hybrid_score = (0.7 * pred_err) + (0.3 * state_dev)
            
            all_mse.extend(hybrid_score.cpu().numpy().tolist())

    all_mse = np.array(all_mse)
    threshold = float(np.percentile(all_mse, THRESHOLD_PERCENTILE))
    mean_mse  = float(np.mean(all_mse))
    std_mse   = float(np.std(all_mse))
    p95_mse   = float(np.percentile(all_mse, 95))
    p99_mse   = float(np.percentile(all_mse, 99))

    print(f"  Val MSE stats:")
    print(f"    Mean    : {mean_mse:.6f}")
    print(f"    Std     : {std_mse:.6f}")
    print(f"    P95     : {p95_mse:.6f}")
    print(f"    P99     : {p99_mse:.6f}   ← used as threshold")
    print(f"  Threshold set to: {threshold:.6f}")

    _print_header("STEP 7 — Saving Artifacts")
    model_path     = os.path.join(MODEL_DIR, "lstm_model.pt")
    scaler_path    = os.path.join(MODEL_DIR, "scaler.pkl")
    threshold_path = os.path.join(MODEL_DIR, "threshold.json")
    history_path   = os.path.join(MODEL_DIR, "training_history.json")

    torch.save(best_state, model_path)
    joblib.dump(scaler, scaler_path)

    with open(threshold_path, "w") as f:
        json.dump({
            "threshold"    : threshold,
            "method"       : f"val_mse_p{THRESHOLD_PERCENTILE}",
            "mean_val_mse" : mean_mse,
            "std_val_mse"  : std_mse,
            "p95_val_mse"  : p95_mse,
            "p99_val_mse"  : p99_mse,
            "best_epoch"   : best_epoch,
            "best_val_loss": best_val_loss,
            "total_samples": len(dataset),
            "train_samples": train_size,
            "val_samples"  : val_size,
        }, f, indent=2)

    with open(history_path, "w") as f:
        json.dump(history, f)

    print(f"  Model     → {model_path}")
    print(f"  Scaler    → {scaler_path}")
    print(f"  Threshold → {threshold_path}")
    print(f"  History   → {history_path}")

    _print_header("TRAINING COMPLETE")
    print(f"  Best epoch       : {best_epoch}")
    print(f"  Best val loss    : {best_val_loss:.6f}")
    print(f"  Anomaly threshold: {threshold:.6f}")
    print(f"  Total samples    : {len(dataset):,}")
    print(f"  Training samples : {train_size:,}")
    print(f"  Validation samp  : {val_size:,}")
    print()


if __name__ == "__main__":
    train()