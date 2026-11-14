#!/usr/bin/env python3
"""
Real Training Data Collection
Collects actual metrics from your running system to train the LSTM
"""
import requests
import time
import json
import numpy as np
from datetime import datetime
import os

PROMETHEUS_URL = "http://localhost:9090"
API_URL = "http://localhost:8000"
TOKEN = "changeme-local-dev"
OUTPUT_FILE = "real_training_data.npy"

def query_prometheus(query):
    """Query Prometheus for a metric"""
    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query},
            timeout=5
        )
        result = response.json()
        if result["status"] == "success" and result["data"]["result"]:
            return float(result["data"]["result"][0]["value"][1])
        return 0.0
    except:
        return 0.0

def collect_metrics():
    """Collect current metrics snapshot"""
    metrics = {
        "request_rate": query_prometheus(
            'sum(rate(http_requests_total[10s])) or vector(0)'
        ),
        "error_rate": query_prometheus(
            'sum(rate(http_requests_total{status=~"5.."}[10s])) / '
            'sum(rate(http_requests_total[10s])) or vector(0)'
        ),
        "p95_latency": query_prometheus(
            'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[10s])) by (le)) or vector(0)'
        ),
        "memory_mb": query_prometheus(
            'sum(process_memory_mb) or vector(0)'
        ),
        "active_connections": query_prometheus(
            'sum(process_active_connections) or vector(0)'
        ),
    }
    return [
        metrics["request_rate"],
        metrics["error_rate"],
        metrics["p95_latency"],
        metrics["memory_mb"],
        metrics["active_connections"]
    ]

def inject_fault(fault_type):
    """Inject a fault via API"""
    try:
        response = requests.post(
            f"{API_URL}/inject/{fault_type}",
            headers={"Authorization": f"Bearer {TOKEN}"},
            timeout=5
        )
        return response.status_code == 200
    except:
        return False

def reset_faults():
    """Clear all faults"""
    try:
        requests.post(
            f"{API_URL}/inject/reset?target=all",
            headers={"Authorization": f"Bearer {TOKEN}"},
            timeout=5
        )
    except:
        pass

def generate_traffic(duration_seconds, rate_per_second=2):
    """Generate traffic for a duration"""
    endpoints = ["/health", "/products", "/cart/add"]
    end_time = time.time() + duration_seconds
    
    while time.time() < end_time:
        for endpoint in endpoints:
            try:
                if endpoint == "/cart/add":
                    requests.post(f"{API_URL}{endpoint}", timeout=2)
                else:
                    requests.get(f"{API_URL}{endpoint}", timeout=2)
            except:
                pass
            time.sleep(1.0 / rate_per_second)

print("="*70)
print("REAL TRAINING DATA COLLECTION")
print("="*70)
print("\nThis will collect actual metrics from your system:")
print("1. Normal operation (clean samples)")
print("2. Each error type (fault samples)")
print("3. Save to", OUTPUT_FILE)
print("\nEstimated time: 10-15 minutes")
print("="*70)

input("\nPress ENTER to start data collection...")

all_data = []
labels = []

# Phase 1: Collect NORMAL samples
print("\n[PHASE 1] Collecting NORMAL operation samples (5 minutes)...")
print("Generating baseline traffic...")

for i in range(150):  # 150 samples = 5 minutes at 2 samples/sec
    generate_traffic(duration_seconds=2, rate_per_second=2)
    metrics = collect_metrics()
    all_data.append(metrics)
    labels.append(0)  # 0 = normal
    
    if i % 30 == 0:
        print(f"  Collected {i}/150 normal samples... "
              f"[req/s: {metrics[0]:.2f}, err: {metrics[1]:.2%}]")

print(f"✅ Collected {len([l for l in labels if l == 0])} normal samples")

# Phase 2: Collect ERROR samples for each fault type
fault_types = [
    ("503_deadlock", "503 Deadlock"),
    ("503_overload", "503 Overload"),
    ("504_timeout", "504 Timeout"),
    ("500_checkout", "500 Crash"),
]

for fault_key, fault_name in fault_types:
    print(f"\n[PHASE 2] Collecting {fault_name} samples...")
    
    # Inject fault
    print(f"  Injecting {fault_name}...")
    if not inject_fault(fault_key):
        print(f"  ⚠️  Failed to inject {fault_name}, skipping...")
        continue
    
    time.sleep(5)  # Wait for fault to activate
    
    # Collect fault samples
    print(f"  Collecting fault samples (30 seconds)...")
    for i in range(15):  # 15 samples during fault
        generate_traffic(duration_seconds=2, rate_per_second=2)
        metrics = collect_metrics()
        all_data.append(metrics)
        labels.append(1)  # 1 = anomaly
        
        if i % 5 == 0:
            print(f"    Sample {i}/15: "
                  f"[req/s: {metrics[0]:.2f}, err: {metrics[1]:.2%}]")
    
    # Clear fault and wait for recovery
    print(f"  Clearing {fault_name}...")
    reset_faults()
    time.sleep(10)  # Wait for recovery
    
    # Collect recovery samples
    print(f"  Collecting recovery samples...")
    for i in range(10):
        generate_traffic(duration_seconds=2, rate_per_second=2)
        metrics = collect_metrics()
        all_data.append(metrics)
        labels.append(0)  # Back to normal
    
    print(f"✅ Collected {fault_name} samples")

# Save data
print(f"\n[SAVING] Writing data to {OUTPUT_FILE}...")
data_array = np.array(all_data, dtype=np.float32)
labels_array = np.array(labels, dtype=np.int32)

# Save both data and labels
np.save(OUTPUT_FILE, data_array)
np.save(OUTPUT_FILE.replace('.npy', '_labels.npy'), labels_array)

print(f"✅ Saved {len(data_array)} samples")
print(f"   Normal samples: {np.sum(labels_array == 0)}")
print(f"   Anomaly samples: {np.sum(labels_array == 1)}")
print(f"\nData shape: {data_array.shape}")
print(f"Features: request_rate, error_rate, p95_latency, memory_mb, active_connections")

print("\n" + "="*70)
print("DATA COLLECTION COMPLETE!")
print("="*70)
print(f"\nNext step: Train the LSTM model on this data")
print(f"Run: python train_on_real_data.py")
print("="*70)
