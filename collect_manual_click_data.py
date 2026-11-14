#!/usr/bin/env python3
"""
Manual Click Data Collection
Collects data from YOUR manual clicks on the shopping site
No automated traffic - pure real user behavior
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
OUTPUT_FILE = "manual_click_training_data.npy"

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
            value = float(result["data"]["result"][0]["value"][1])
            if np.isnan(value) or np.isinf(value):
                return 0.0
            return value
        return 0.0
    except:
        return 0.0

def collect_metrics():
    """Collect current metrics snapshot"""
    metrics = {
        "request_rate": query_prometheus(
            'sum(rate(http_requests_total[30s])) or vector(0)'
        ),
        "error_rate": query_prometheus(
            'sum(rate(http_requests_total{status=~"5.."}[30s])) / '
            'sum(rate(http_requests_total[30s])) or vector(0)'
        ),
        "p95_latency": query_prometheus(
            'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[30s])) by (le)) or vector(0)'
        ),
        "memory_mb": query_prometheus(
            'sum(process_memory_mb) or vector(0)'
        ),
        "active_connections": query_prometheus(
            'sum(process_active_connections) or vector(0)'
        ),
    }
    
    values = [
        metrics["request_rate"],
        metrics["error_rate"],
        metrics["p95_latency"],
        metrics["memory_mb"],
        metrics["active_connections"]
    ]
    
    values = [0.0 if (np.isnan(v) or np.isinf(v)) else v for v in values]
    return values

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
        time.sleep(3)
    except:
        pass

print("="*70)
print("MANUAL CLICK DATA COLLECTION")
print("="*70)
print("\nThis script collects data from YOUR manual interactions.")
print("No automated traffic - just you clicking on the shopping site.")
print("\nYou'll need to:")
print("1. Click around the site normally (5 minutes)")
print("2. Then inject each error type and click during errors")
print("\nEstimated time: 15-20 minutes")
print("="*70)

input("\nPress ENTER to start...")

all_data = []
labels = []

# Phase 1: Normal clicking
print("\n[PHASE 1] Collecting NORMAL samples (5 minutes)")
print("=" * 70)
print("ACTION REQUIRED:")
print("  1. Open http://localhost:8000 in your browser")
print("  2. Click around the shopping site:")
print("     - Click 'Urban Shirt' → Add to cart")
print("     - Browse products")
print("     - Add/remove items")
print("  3. Keep clicking for 5 minutes")
print("  4. This script will collect samples every 2 seconds")
print("=" * 70)

input("\nPress ENTER when you're ready to start clicking...")

start_time = time.time()
sample_count = 0

while time.time() - start_time < 300:  # 5 minutes
    metrics = collect_metrics()
    all_data.append(metrics)
    labels.append(0)
    sample_count += 1
    
    if sample_count % 15 == 0:
        elapsed = int(time.time() - start_time)
        remaining = 300 - elapsed
        print(f"  [{elapsed}s] Collected {sample_count} samples... "
              f"[req/s: {metrics[0]:.2f}, err: {metrics[1]:.2%}] "
              f"({remaining}s remaining)")
    
    time.sleep(2)

print(f"✅ Collected {len([l for l in labels if l == 0])} normal samples")

# Phase 2: Error samples
fault_types = [
    ("503_overload", "503 Overload"),
    ("504_timeout", "504 Timeout"),
    ("500_checkout", "500 Crash"),
]

for fault_key, fault_name in fault_types:
    print(f"\n[PHASE 2] Collecting {fault_name} samples")
    print("=" * 70)
    
    # Clear previous faults
    reset_faults()
    time.sleep(5)
    
    print(f"ACTION REQUIRED:")
    print(f"  1. I'll inject {fault_name} in 5 seconds")
    print(f"  2. Keep clicking on the site for 1 minute")
    print(f"  3. You'll see errors - that's expected!")
    print("=" * 70)
    
    input(f"\nPress ENTER to inject {fault_name}...")
    
    # Inject fault
    if not inject_fault(fault_key):
        print(f"  ⚠️  Failed to inject {fault_name}, skipping...")
        continue
    
    print(f"  ✅ {fault_name} injected! Start clicking now!")
    time.sleep(10)
    
    # Collect during fault
    start_time = time.time()
    sample_count = 0
    
    while time.time() - start_time < 60:  # 1 minute
        metrics = collect_metrics()
        all_data.append(metrics)
        labels.append(1)
        sample_count += 1
        
        if sample_count % 10 == 0:
            print(f"    Sample {sample_count}: "
                  f"[req/s: {metrics[0]:.2f}, err: {metrics[1]:.2%}]")
        
        time.sleep(2)
    
    # Clear fault
    print(f"  Clearing {fault_name}...")
    reset_faults()
    time.sleep(15)
    
    # Collect recovery samples
    print(f"  Collecting recovery samples (keep clicking)...")
    for i in range(15):
        metrics = collect_metrics()
        all_data.append(metrics)
        labels.append(0)
        time.sleep(2)
    
    print(f"✅ Collected {fault_name} samples")

# Save data
print(f"\n[SAVING] Writing data to {OUTPUT_FILE}...")
data_array = np.array(all_data, dtype=np.float32)
labels_array = np.array(labels, dtype=np.int32)

# Validate
nan_count = np.sum(np.isnan(data_array))
if nan_count > 0:
    print(f"⚠️  WARNING: Found {nan_count} NaN values, replacing with 0")
    data_array = np.nan_to_num(data_array, nan=0.0)

np.save(OUTPUT_FILE, data_array)
np.save(OUTPUT_FILE.replace('.npy', '_labels.npy'), labels_array)

print(f"✅ Saved {len(data_array)} samples")
print(f"   Normal samples: {np.sum(labels_array == 0)}")
print(f"   Anomaly samples: {np.sum(labels_array == 1)}")
print(f"\nData shape: {data_array.shape}")
print(f"Data range: min={np.min(data_array):.3f}, max={np.max(data_array):.3f}")

print("\n" + "="*70)
print("DATA COLLECTION COMPLETE!")
print("="*70)
print(f"\nNext step: Train the LSTM on this manual click data")
print(f"Run: python train_lstm_improved.py")
print(f"(Update DATA_FILE to '{OUTPUT_FILE}' in the script)")
print("="*70)
