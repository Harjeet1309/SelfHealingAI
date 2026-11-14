#!/usr/bin/env python3
"""
Simple Anomaly Detection Model
Uses statistical approach instead of complex LSTM
"""
import numpy as np
import json
import os
from sklearn.preprocessing import StandardScaler
import pickle

# Paths
DATA_FILE = "real_training_data.npy"
LABELS_FILE = "real_training_data_labels.npy"
MODEL_DIR = "models"
SCALER_PATH = os.path.join(MODEL_DIR, "scaler.pkl")
THRESHOLD_PATH = os.path.join(MODEL_DIR, "threshold.json")
STATS_PATH = os.path.join(MODEL_DIR, "baseline_stats.json")

print("="*70)
print("SIMPLE STATISTICAL ANOMALY DETECTION")
print("="*70)

# Load data
print(f"\n[1/4] Loading data from {DATA_FILE}...")
data = np.load(DATA_FILE)
labels = np.load(LABELS_FILE)

print(f"✅ Loaded {len(data)} samples")
print(f"   Shape: {data.shape}")
print(f"   Normal: {np.sum(labels == 0)}, Anomaly: {np.sum(labels == 1)}")

# Split into train/test
print(f"\n[2/4] Analyzing normal vs anomaly patterns...")
normal_data = data[labels == 0]
anomaly_data = data[labels == 1]

# Compute statistics for each feature
feature_names = ["request_rate", "error_rate", "p95_latency", "memory_mb", "active_connections"]

print("\nNormal baseline statistics:")
for i, name in enumerate(feature_names):
    mean = np.mean(normal_data[:, i])
    std = np.std(normal_data[:, i])
    print(f"  {name}: mean={mean:.3f}, std={std:.3f}")

print("\nAnomaly statistics:")
for i, name in enumerate(feature_names):
    mean = np.mean(anomaly_data[:, i])
    std = np.std(anomaly_data[:, i])
    print(f"  {name}: mean={mean:.3f}, std={std:.3f}")

# Normalize data
print(f"\n[3/4] Computing normalization and thresholds...")
scaler = StandardScaler()
normal_scaled = scaler.fit_transform(normal_data)
anomaly_scaled = scaler.transform(anomaly_data)

# Compute baseline statistics (mean and std of normal data)
baseline_mean = np.mean(normal_scaled, axis=0)
baseline_std = np.std(normal_scaled, axis=0)

# Compute anomaly scores using Mahalanobis-like distance
def compute_anomaly_score(sample):
    """Compute how far sample deviates from baseline"""
    # Weighted distance from baseline
    # Error rate gets highest weight (most important signal)
    weights = np.array([1.0, 3.0, 1.0, 0.5, 0.5])  # error_rate has weight 3
    deviation = np.abs(sample - baseline_mean)
    weighted_deviation = deviation * weights
    return np.sum(weighted_deviation)

# Compute scores for normal data
normal_scores = [compute_anomaly_score(sample) for sample in normal_scaled]
anomaly_scores = [compute_anomaly_score(sample) for sample in anomaly_scaled]

# Set threshold at 95th percentile of normal scores
threshold = float(np.percentile(normal_scores, 95))

print(f"✅ Threshold (95th percentile): {threshold:.3f}")
print(f"   Normal score range: {np.min(normal_scores):.3f} - {np.max(normal_scores):.3f}")
print(f"   Anomaly score range: {np.min(anomaly_scores):.3f} - {np.max(anomaly_scores):.3f}")

# Test detection rate
detected = np.sum(np.array(anomaly_scores) > threshold)
total = len(anomaly_scores)
detection_rate = detected / total if total > 0 else 0

print(f"\n[4/4] Testing detection performance...")
print(f"✅ Anomaly detection rate: {detection_rate:.1%} ({detected}/{total})")

# Compute false positive rate
false_positives = np.sum(np.array(normal_scores) > threshold)
fp_rate = false_positives / len(normal_scores)
print(f"✅ False positive rate: {fp_rate:.1%} ({false_positives}/{len(normal_scores)})")

# Save artifacts
print(f"\n[SAVING] Saving model artifacts...")
os.makedirs(MODEL_DIR, exist_ok=True)

with open(SCALER_PATH, 'wb') as f:
    pickle.dump(scaler, f)

with open(STATS_PATH, 'w') as f:
    json.dump({
        "baseline_mean": baseline_mean.tolist(),
        "baseline_std": baseline_std.tolist(),
        "weights": [1.0, 3.0, 1.0, 0.5, 0.5],
        "feature_names": feature_names
    }, f, indent=2)

with open(THRESHOLD_PATH, 'w') as f:
    json.dump({
        "threshold": threshold,
        "static_threshold": threshold,
        "training_samples": len(normal_data),
        "detection_rate": detection_rate,
        "false_positive_rate": fp_rate,
        "trained_on": "real_data_statistical"
    }, f, indent=2)

print(f"✅ Saved:")
print(f"   Scaler: {SCALER_PATH}")
print(f"   Baseline Stats: {STATS_PATH}")
print(f"   Threshold: {THRESHOLD_PATH}")

print("\n" + "="*70)
print("TRAINING COMPLETE!")
print("="*70)
print(f"\nDetection Rate: {detection_rate:.1%}")
print(f"False Positive Rate: {fp_rate:.1%}")
print("\nThis simple statistical model focuses on error_rate (the clearest signal)")
print("and should provide more reliable detection than complex LSTM.")
print("\nRestart the remediation engine to use the new model:")
print("  docker-compose restart remediation_engine")
print("="*70)
