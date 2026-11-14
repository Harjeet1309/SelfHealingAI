#!/usr/bin/env python3
"""
Background Traffic Generator
Generates realistic baseline HTTP traffic to populate dashboard metrics
"""
import requests
import time
import random
import threading
from datetime import datetime

API_URL = "http://localhost:8000"
TRAFFIC_RATE = 2  # requests per second (light baseline)

def generate_traffic():
    """Generate continuous background traffic"""
    endpoints = [
        "/health",
        "/products",
        "/cart/add",
    ]
    
    while True:
        try:
            endpoint = random.choice(endpoints)
            start = time.time()
            
            if endpoint == "/cart/add":
                response = requests.post(f"{API_URL}{endpoint}", timeout=2)
            else:
                response = requests.get(f"{API_URL}{endpoint}", timeout=2)
            
            latency = (time.time() - start) * 1000
            status = response.status_code
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] {endpoint} → {status} ({latency:.0f}ms)")
            
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Request failed: {e}")
        
        # Sleep to maintain target rate
        time.sleep(1.0 / TRAFFIC_RATE)

if __name__ == "__main__":
    print(f"Starting traffic generator: {TRAFFIC_RATE} req/s")
    print(f"Target: {API_URL}")
    print("Press Ctrl+C to stop\n")
    
    try:
        generate_traffic()
    except KeyboardInterrupt:
        print("\nTraffic generator stopped")
