#!/usr/bin/env python3
"""
Improved LSTM Training for Anomaly Detection
Optimized for small datasets with clear error_rate signals
"""
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import json
import os
from sklearn.preprocessing import StandardScaler
import pickle

# Paths
DATA_FILE = "real_training_data.npy"
LABELS_FILE = "real_training_data_labels.npy"
MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "lstm_model.pt")
SCALER_PATH = os.path.join(MODEL_DIR, "scaler.pkl")
THRESHOLD_PATH = os.path.join(MODEL_DIR, "threshold.json")

# Hyperparameters - OPTIMIZED for small dataset
SEQUENCE_LENGTH = 30
HIDDEN_SIZE = 32  # Reduced from 64 to prevent overfitting
NUM_LAYERS = 1    # Reduced from 2 - simpler is better for small data
BATCH_SIZE = 16   # Smaller batches
EPOCHS = 100      # More epochs with early stopping
LEARNING_RATE = 0.001

class SimpleLSTMAutoencoder(nn.Module):
    """Simplified LSTM autoencoder optimized for small datasets"""
    def __init__(self, input_size, hidden_size):
        super().__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        
        # Encoder: input -> hidden
        self.encoder = nn.LSTM(input_size, hidden_size, batch_first=True)
        
        # Decoder: hidden -> hidden
        self.decoder = nn.LSTM(hidden_size, hidden_size, batch_first=True)
        
        # Output projection: hidden -> input
        self.output_layer = nn.Linear(hidden_size, input_size)
        
    def forward(self, x):
        # Encode
        _, (hidden, cell) = self.encoder(x)
        
        # Prepare decoder input (repeat last hidden state)
        batch_size = x.size(0)
        seq_len = x.size(1)
        decoder_input = hidden[-1].unsqueeze(1).repeat(1, seq_len, 1)
        
        # Decode
        decoder_output, _ = self.decoder(decoder_input, (hidden, cell))
        
        # Project to output
        output = self.output_layer(decoder_output)
        
        return output

class TimeSeriesDataset(Dataset):
    def __init__(self, data, seq_length):
        self.data = data
        self.seq_length = seq_length
    
    def __len__(self):
        return max(0, len(self.data) - self.seq_length)
    
    def __getitem__(self, idx):
        sequence = self.data[idx:idx + self.seq_length]
        return torch.FloatTensor(sequence)

print("="*70)
print("IMPROVED LSTM TRAINING FOR ANOMALY DETECTION")
print("="*70)

# Load data
print(f"\n[1/7] Loading data from {DATA_FILE}...")
data = np.load(DATA_FILE)
labels = np.load(LABELS_FILE)

print(f"✅ Loaded {len(data)} samples")
print(f"   Shape: {data.shape}")
print(f"   Normal: {np.sum(labels == 0)}, Anomaly: {np.sum(labels == 1)}")

# Analyze data distribution
print(f"\n[2/7] Analyzing data distribution...")
normal_data = data[labels == 0]
anomaly_data = data[labels == 1]

feature_names = ["request_rate", "error_rate", "p95_latency", "memory_mb", "active_connections"]
print("\nNormal baseline:")
for i, name in enumerate(feature_names):
    print(f"  {name}: mean={np.mean(normal_data[:, i]):.3f}, std={np.std(normal_data[:, i]):.3f}")

print("\nAnomaly patterns:")
for i, name in enumerate(feature_names):
    print(f"  {name}: mean={np.mean(anomaly_data[:, i]):.3f}, std={np.std(anomaly_data[:, i]):.3f}")

# Split data - use 90% for training, 10% for validation
print(f"\n[3/7] Preparing training data (normal samples only)...")
split_idx = int(len(normal_data) * 0.9)
train_data = normal_data[:split_idx]
val_data = normal_data[split_idx:]

print(f"✅ Train: {len(train_data)}, Val: {len(val_data)}, Test (anomaly): {len(anomaly_data)}")

# Normalize
print(f"\n[4/7] Normalizing data...")
scaler = StandardScaler()
train_data_scaled = scaler.fit_transform(train_data)
val_data_scaled = scaler.transform(val_data)
anomaly_data_scaled = scaler.transform(anomaly_data)

print(f"✅ Scaler fitted on {len(train_data)} normal samples")

# Create datasets
train_dataset = TimeSeriesDataset(train_data_scaled, SEQUENCE_LENGTH)
val_dataset = TimeSeriesDataset(val_data_scaled, SEQUENCE_LENGTH)

if len(train_dataset) == 0 or len(val_dataset) == 0:
    print(f"❌ ERROR: Not enough data for sequences!")
    print(f"   Need at least {SEQUENCE_LENGTH} samples, have {len(train_data)}")
    exit(1)

train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE)

print(f"✅ Created {len(train_dataset)} training sequences, {len(val_dataset)} validation sequences")

# Initialize model
print(f"\n[5/7] Initializing LSTM model...")
input_size = data.shape[1]
model = SimpleLSTMAutoencoder(input_size, HIDDEN_SIZE)
criterion = nn.MSELoss()
optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)

print(f"✅ Model: {input_size} features, {HIDDEN_SIZE} hidden, {NUM_LAYERS} layer")
print(f"   Parameters: {sum(p.numel() for p in model.parameters())}")

# Training with early stopping
print(f"\n[6/7] Training for up to {EPOCHS} epochs (with early stopping)...")
best_val_loss = float('inf')
patience = 15
patience_counter = 0

for epoch in range(EPOCHS):
    # Train
    model.train()
    train_loss = 0
    for batch in train_loader:
        optimizer.zero_grad()
        output = model(batch)
        loss = criterion(output, batch)
        loss.backward()
        optimizer.step()
        train_loss += loss.item()
    
    train_loss /= len(train_loader)
    
    # Validate
    model.eval()
    val_loss = 0
    with torch.no_grad():
        for batch in val_loader:
            output = model(batch)
            loss = criterion(output, batch)
            val_loss += loss.item()
    
    val_loss /= len(val_loader)
    
    # Early stopping check
    if val_loss < best_val_loss:
        best_val_loss = val_loss
        torch.save(model.state_dict(), MODEL_PATH)
        patience_counter = 0
    else:
        patience_counter += 1
    
    if (epoch + 1) % 10 == 0:
        print(f"  Epoch {epoch+1}/{EPOCHS}: "
              f"Train Loss: {train_loss:.6f}, Val Loss: {val_loss:.6f} "
              f"{'✓ BEST' if patience_counter == 0 else f'(patience: {patience_counter}/{patience})'}")
    
    # Early stopping
    if patience_counter >= patience:
        print(f"✅ Early stopping at epoch {epoch+1} (no improvement for {patience} epochs)")
        break

print(f"✅ Training complete! Best val loss: {best_val_loss:.6f}")

# Load best model
model.load_state_dict(torch.load(MODEL_PATH))
model.eval()

# Compute threshold from validation data
print(f"\n[7/7] Computing anomaly threshold...")
all_mse = []
with torch.no_grad():
    for batch in val_loader:
        output = model(batch)
        mse = torch.mean((output - batch) ** 2, dim=(1, 2))
        all_mse.extend(mse.numpy())

# Use 95th percentile (less aggressive than 99th)
threshold = float(np.percentile(all_mse, 95))
print(f"✅ Threshold (95th percentile): {threshold:.6f}")
print(f"   Normal MSE range: {np.min(all_mse):.6f} - {np.max(all_mse):.6f}")

# Test on anomaly data
print(f"\n[TESTING] Evaluating on {len(anomaly_data)} anomaly samples...")
anomaly_dataset = TimeSeriesDataset(anomaly_data_scaled, SEQUENCE_LENGTH)

if len(anomaly_dataset) == 0:
    print("⚠️  Not enough anomaly samples for sequence testing")
    anomaly_mse = []
else:
    anomaly_loader = DataLoader(anomaly_dataset, batch_size=BATCH_SIZE)
    anomaly_mse = []
    with torch.no_grad():
        for batch in anomaly_loader:
            output = model(batch)
            mse = torch.mean((output - batch) ** 2, dim=(1, 2))
            anomaly_mse.extend(mse.numpy())

if len(anomaly_mse) > 0:
    detected = np.sum(np.array(anomaly_mse) > threshold)
    total = len(anomaly_mse)
    detection_rate = detected / total if total > 0 else 0
    
    print(f"✅ Anomaly detection rate: {detection_rate:.1%} ({detected}/{total})")
    print(f"   Anomaly MSE range: {np.min(anomaly_mse):.6f} - {np.max(anomaly_mse):.6f}")
    
    # Show some examples
    print(f"\n   Sample anomaly scores:")
    for i in range(min(5, len(anomaly_mse))):
        status = "✓ DETECTED" if anomaly_mse[i] > threshold else "✗ MISSED"
        print(f"     Sample {i+1}: MSE={anomaly_mse[i]:.6f} {status}")
else:
    detection_rate = 0.0
    print("⚠️  No anomaly sequences available for testing")

# Compute false positive rate
false_positives = np.sum(np.array(all_mse) > threshold)
fp_rate = false_positives / len(all_mse) if len(all_mse) > 0 else 0
print(f"✅ False positive rate: {fp_rate:.1%} ({false_positives}/{len(all_mse)})")

# Save artifacts
print(f"\n[SAVING] Saving model artifacts...")
os.makedirs(MODEL_DIR, exist_ok=True)

with open(SCALER_PATH, 'wb') as f:
    pickle.dump(scaler, f)

with open(THRESHOLD_PATH, 'w') as f:
    json.dump({
        "threshold": threshold,
        "static_threshold": threshold,
        "training_samples": len(train_data),
        "detection_rate": detection_rate,
        "false_positive_rate": fp_rate,
        "trained_on": "real_data_lstm_improved",
        "model_params": {
            "hidden_size": HIDDEN_SIZE,
            "num_layers": NUM_LAYERS,
            "sequence_length": SEQUENCE_LENGTH
        }
    }, f, indent=2)

print(f"✅ Saved:")
print(f"   Model: {MODEL_PATH}")
print(f"   Scaler: {SCALER_PATH}")
print(f"   Threshold: {THRESHOLD_PATH}")

print("\n" + "="*70)
print("LSTM TRAINING COMPLETE!")
print("="*70)
print(f"\nResults:")
print(f"  Detection Rate: {detection_rate:.1%}")
print(f"  False Positive Rate: {fp_rate:.1%}")
print(f"  Model Size: {sum(p.numel() for p in model.parameters())} parameters")
print(f"\nThe LSTM autoencoder learns normal patterns and detects deviations.")
print(f"Threshold: {threshold:.6f}")
print("\nRestart the remediation engine to use the new model:")
print("  docker-compose restart remediation_engine")
print("="*70)
