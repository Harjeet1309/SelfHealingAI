#!/usr/bin/env python3
"""
Training Data Collection Script
Collects real metrics from your system while injecting faults
This data will be used to train the LSTM model
"""
import requests
import time
import json
import numpy as np
from datetime import datetime

PROMETHEUS_URL = "http://localhost:9090"
API_URL = "http://localhost:8000"
TOKEN = "changeme-local-dev"

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
    """Collect current metrics from Prometheus"""
    metrics = {
        "timestamp": time.time(),
        "request_rate": query_prometheus('sum(rate(http_requests_total[30s]))'),
        "error_rate": query_prometheus('sum(rate(http_requests_total{status=~"5.."}[30s])) / sum(rate(http_requests_total[30s]))'),
        "p95_latency": query_prometheus('histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[30s])) by (le))'),
        "memory_mb": query_prometheus('sum(process_memory_mb)'),
        "active_connections": query_prometheus('sum(process_active_connections)'),
    }
    return metrics

def inject_fault(fault_type):
    """Inject a specific fault type"""
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
        response = requests.post(
            f"{API_URL}/inject/reset?target=all",
            headers={"Authorization": f"Bearer {TOKEN}"},
            timeout=5
        )
        return response.status_code == 200
    except:
        return False

def collect_scenario(scenario_name, fault_type, duration=120):
    """
    Collect data for a specific scenario
    
    Args:
        scenario_name: Name of the scenario (e.g., "normal", "503_deadlock")
        fault_type: Fault to inject (None for normal operation)
        duration: How long to collect data (seconds)
    """
    print(f"\n{'='*60}")
    print(f"Collecting: {scenario_name}")
    print(f"{'='*60}")
    
    data = []
    
    # Reset any existing faults
    reset_faults()
    time.sleep(5)
    
    # Inject fault if specified
    if fault_type:
        print(f"Injecting fault: {fault_type}")
        inject_fault(fault_type)
        time.sleep(2)
    
    # Collect metrics
    start_time = time.time()
    sample_count = 0
    
    while (time.time() - start_time) < duration:
        metrics = collect_metrics()
        metrics["scenario"] = scenario_name
        metrics["label"] = 0 if fault_type is None else 1  # 0=normal, 1=fault
        
        data.append(metrics)
        sample_count += 1
        
        # Print progress
        elapsed = time.time() - start_time
        print(f"[{sample_count:3d}] {elapsed:5.1f}s | "
              f"Req: {metrics['request_rate']:5.2f}/s | "
              f"Err: {metrics['error_rate']*100:5.1f}% | "
              f"Lat: {metrics['p95_latency']*1000:6.1f}ms")
        
        time.sleep(2)  # Sample every 2 seconds
    
    # Reset faults after collection
    if fault_type:
        print("Resetting faults...")
        reset_faults()
        time.sleep(10)  # Wait for recovery
    
    return data

def main():
    """Main data collection workflow"""
    print("\n" + "="*60)
    print("LSTM Training Data Collection")
    print("="*60)
    print("\nThis will collect real metrics from your system")
    print("Make sure traffic generator is running!")
    print("\nPress Ctrl+C to stop\n")
    
    all_data = []
    
    try:
        # Scenario 1: Normal operation (baseline)
        print("\n[1/5] Collecting NORMAL operation data...")
        data = collect_scenario("normal", None, duration=60)
        all_data.extend(data)
        
        # Scenario 2: 503 Deadlock
        print("\n[2/5] Collecting 503 DEADLOCK data...")
        data = collect_scenario("503_deadlock", "503_deadlock", duration=60)
        all_data.extend(data)
        
        # Scenario 3: 504 Timeout
        print("\n[3/5] Collecting 504 TIMEOUT data...")
        data = collect_scenario("504_timeout", "504_timeout", duration=60)
        all_data.extend(data)
        
        # Scenario 4: 500 Crash
        print("\n[4/5] Collecting 500 CRASH data...")
        data = collect_scenario("500_crash", "500_checkout", duration=60)
        all_data.extend(data)
        
        # Scenario 5: 503 Overload
        print("\n[5/5] Collecting 503 OVERLOAD data...")
        data = collect_scenario("503_overload", "503_overload", duration=60)
        all_data.extend(data)
        
    except KeyboardInterrupt:
        print("\n\nCollection stopped by user")
    
    # Save collected data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"training_data_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(all_data, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"Data Collection Complete!")
    print(f"{'='*60}")
    print(f"Samples collected: {len(all_data)}")
    print(f"Saved to: {filename}")
    print(f"\nNext step: Run training script to train LSTM on this data")
    
    # Convert to numpy for analysis
    features = np.array([[
        d['request_rate'],
        d['error_rate'],
        d['p95_latency'],
        d['memory_mb'],
        d['active_connections']
    ] for d in all_data])
    
    print(f"\nData shape: {features.shape}")
    print(f"Feature ranges:")
    print(f"  Request rate: {features[:,0].min():.2f} - {features[:,0].max():.2f}")
    print(f"  Error rate: {features[:,1].min():.3f} - {features[:,1].max():.3f}")
    print(f"  P95 latency: {features[:,2].min():.3f} - {features[:,2].max():.3f}")
    print(f"  Memory: {features[:,3].min():.1f} - {features[:,3].max():.1f} MB")
    print(f"  Connections: {features[:,4].min():.0f} - {features[:,4].max():.0f}")

if __name__ == "__main__":
    main()
