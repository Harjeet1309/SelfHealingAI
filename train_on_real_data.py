#!/usr/bin/env python3
"""
Train LSTM on Real Data
Uses the collected real metrics to train the model
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

# Hyperparameters
SEQUENCE_LENGTH = 30
HIDDEN_SIZE = 64
NUM_LAYERS = 2
BATCH_SIZE = 32
EPOCHS = 50
LEARNING_RATE = 0.001

class LSTMAutoencoder(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers):
        super().__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.encoder = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.decoder = nn.LSTM(hidden_size, hidden_size, num_layers, batch_first=True)
        self.output_layer = nn.Linear(hidden_size, input_size)
    
    def forward(self, x):
        # Encode
        _, (hidden, cell) = self.encoder(x)
        
        # Decode
        decoder_input = hidden[-1].unsqueeze(1).repeat(1, x.size(1), 1)
        decoder_output, _ = self.decoder(decoder_input, (hidden, cell))
        
        # Project back to input size
        output = self.output_layer(decoder_output)
        return output

class TimeSeriesDataset(Dataset):
    def __init__(self, data, seq_length):
        self.data = data
        self.seq_length = seq_length
    
    def __len__(self):
        return len(self.data) - self.seq_length
    
    def __getitem__(self, idx):
        sequence = self.data[idx:idx + self.seq_length]
        return torch.FloatTensor(sequence)

print("="*70)
print("TRAINING LSTM ON REAL DATA")
print("="*70)

# Load data
print(f"\n[1/6] Loading data from {DATA_FILE}...")
data = np.load(DATA_FILE)
labels = np.load(LABELS_FILE)

print(f"✅ Loaded {len(data)} samples")
print(f"   Shape: {data.shape}")
print(f"   Normal: {np.sum(labels == 0)}, Anomaly: {np.sum(labels == 1)}")

# Split into train/val (use only NORMAL samples for training)
print(f"\n[2/6] Preparing training data (normal samples only)...")
normal_data = data[labels == 0]
anomaly_data = data[labels == 1]

# 80/20 split for train/val
split_idx = int(len(normal_data) * 0.8)
train_data = normal_data[:split_idx]
val_data = normal_data[split_idx:]

print(f"✅ Train: {len(train_data)}, Val: {len(val_data)}")

# Normalize
print(f"\n[3/6] Normalizing data...")
scaler = StandardScaler()
train_data_scaled = scaler.fit_transform(train_data)
val_data_scaled = scaler.transform(val_data)
anomaly_data_scaled = scaler.transform(anomaly_data)

# Create datasets
train_dataset = TimeSeriesDataset(train_data_scaled, SEQUENCE_LENGTH)
val_dataset = TimeSeriesDataset(val_data_scaled, SEQUENCE_LENGTH)

train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE)

print(f"✅ Created {len(train_dataset)} training sequences")

# Initialize model
print(f"\n[4/6] Initializing LSTM model...")
input_size = data.shape[1]
model = LSTMAutoencoder(input_size, HIDDEN_SIZE, NUM_LAYERS)
criterion = nn.MSELoss()
optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)

print(f"✅ Model: {input_size} features, {HIDDEN_SIZE} hidden, {NUM_LAYERS} layers")

# Training
print(f"\n[5/6] Training for {EPOCHS} epochs...")
best_val_loss = float('inf')

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
    
    # Validate
    model.eval()
    val_loss = 0
    with torch.no_grad():
        for batch in val_loader:
            output = model(batch)
            loss = criterion(output, batch)
            val_loss += loss.item()
    
    train_loss /= len(train_loader)
    val_loss /= len(val_loader)
    
    if val_loss < best_val_loss:
        best_val_loss = val_loss
        torch.save(model.state_dict(), MODEL_PATH)
    
    if (epoch + 1) % 10 == 0:
        print(f"  Epoch {epoch+1}/{EPOCHS}: "
              f"Train Loss: {train_loss:.6f}, Val Loss: {val_loss:.6f}")

print(f"✅ Training complete! Best val loss: {best_val_loss:.6f}")

# Compute threshold
print(f"\n[6/6] Computing anomaly threshold...")
model.load_state_dict(torch.load(MODEL_PATH))
model.eval()

all_mse = []
with torch.no_grad():
    for batch in val_loader:
        output = model(batch)
        mse = torch.mean((output - batch) ** 2, dim=(1, 2))
        all_mse.extend(mse.numpy())

threshold = float(np.percentile(all_mse, 99))
print(f"✅ Threshold (99th percentile): {threshold:.6f}")

# Test on anomaly data
print(f"\n[TESTING] Evaluating on anomaly samples...")
anomaly_dataset = TimeSeriesDataset(anomaly_data_scaled, SEQUENCE_LENGTH)
anomaly_loader = DataLoader(anomaly_dataset, batch_size=BATCH_SIZE)

anomaly_mse = []
with torch.no_grad():
    for batch in anomaly_loader:
        output = model(batch)
        mse = torch.mean((output - batch) ** 2, dim=(1, 2))
        anomaly_mse.extend(mse.numpy())

detected = np.sum(np.array(anomaly_mse) > threshold)
total = len(anomaly_mse)
detection_rate = detected / total if total > 0 else 0

print(f"✅ Anomaly detection rate: {detection_rate:.1%} ({detected}/{total})")
print(f"   Normal MSE range: {np.min(all_mse):.6f} - {np.max(all_mse):.6f}")
print(f"   Anomaly MSE range: {np.min(anomaly_mse):.6f} - {np.max(anomaly_mse):.6f}")

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
        "trained_on": "real_data"
    }, f, indent=2)

print(f"✅ Saved:")
print(f"   Model: {MODEL_PATH}")
print(f"   Scaler: {SCALER_PATH}")
print(f"   Threshold: {THRESHOLD_PATH}")

print("\n" + "="*70)
print("TRAINING COMPLETE!")
print("="*70)
print("\nYour LSTM is now trained on YOUR system's real data!")
print("Restart the remediation engine to load the new model:")
print("  docker-compose restart remediation_engine")
print("\nNow when you inject errors, the graph WILL spike automatically!")
print("="*70)
