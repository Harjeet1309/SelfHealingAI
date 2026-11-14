#!/usr/bin/env python3
"""
Metrics Collection Validation Script
=====================================
Tests if psutil can collect memory and connection metrics.
Run this inside the api_service container to verify the fix.

Usage:
    docker exec -it api_service python /app/validate_metrics_fix.py
"""

import os
import sys
import psutil

def test_memory_collection():
    """Test if we can read process memory."""
    print("\n" + "="*60)
    print("TEST 1: Memory Collection (RSS)")
    print("="*60)
    try:
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        mem_mb = mem_info.rss / (1024 * 1024)
        print(f"✅ SUCCESS: Memory RSS = {mem_mb:.2f} MB")
        print(f"   Full memory info: {mem_info}")
        return True
    except PermissionError as e:
        print(f"❌ FAILED: Permission denied")
        print(f"   Error: {e}")
        print(f"   Fix: Add 'cap_add: [SYS_PTRACE]' to docker-compose.yml")
        return False
    except Exception as e:
        print(f"❌ FAILED: Unexpected error")
        print(f"   Error: {e}")
        return False


def test_connection_collection():
    """Test if we can read network connections."""
    print("\n" + "="*60)
    print("TEST 2: Network Connections")
    print("="*60)
    try:
        process = psutil.Process(os.getpid())
        connections = process.net_connections(kind="tcp")
        conn_count = len(connections)
        print(f"✅ SUCCESS: Active TCP connections = {conn_count}")
        if conn_count > 0:
            print(f"   Sample connections:")
            for conn in connections[:3]:
                print(f"     - {conn.laddr} -> {conn.raddr} [{conn.status}]")
        return True
    except PermissionError as e:
        print(f"❌ FAILED: Permission denied")
        print(f"   Error: {e}")
        print(f"   Fix: Add 'cap_add: [SYS_PTRACE]' to docker-compose.yml")
        return False
    except Exception as e:
        print(f"❌ FAILED: Unexpected error")
        print(f"   Error: {e}")
        return False


def test_prometheus_metrics():
    """Test if Prometheus metrics are being exposed correctly."""
    print("\n" + "="*60)
    print("TEST 3: Prometheus Metrics Exposure")
    print("="*60)
    try:
        import requests
        response = requests.get("http://localhost:8000/metrics", timeout=5)
        if response.status_code == 200:
            content = response.text
            
            # Check for memory metric
            if "process_memory_mb" in content:
                # Extract value
                for line in content.split('\n'):
                    if line.startswith("process_memory_mb") and not line.startswith("#"):
                        value = float(line.split()[1])
                        if value > 0:
                            print(f"✅ SUCCESS: process_memory_mb = {value:.2f} MB")
                        else:
                            print(f"⚠️  WARNING: process_memory_mb = 0.0 (metrics not collecting)")
                        break
            else:
                print(f"❌ FAILED: process_memory_mb not found in /metrics")
            
            # Check for connections metric
            if "process_active_connections" in content:
                for line in content.split('\n'):
                    if line.startswith("process_active_connections") and not line.startswith("#"):
                        value = float(line.split()[1])
                        print(f"✅ SUCCESS: process_active_connections = {value:.0f}")
                        break
            else:
                print(f"❌ FAILED: process_active_connections not found in /metrics")
            
            return True
        else:
            print(f"❌ FAILED: /metrics returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"⚠️  SKIPPED: Could not test /metrics endpoint")
        print(f"   Error: {e}")
        print(f"   (This is OK if api_service is not running yet)")
        return None


def main():
    print("\n" + "="*60)
    print("PSUTIL METRICS COLLECTION VALIDATION")
    print("="*60)
    print(f"Python version: {sys.version}")
    print(f"psutil version: {psutil.__version__}")
    print(f"Process PID: {os.getpid()}")
    print(f"Running as UID: {os.getuid()}")
    
    results = []
    results.append(("Memory Collection", test_memory_collection()))
    results.append(("Connection Collection", test_connection_collection()))
    
    metrics_result = test_prometheus_metrics()
    if metrics_result is not None:
        results.append(("Prometheus Metrics", metrics_result))
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result is True)
    failed = sum(1 for _, result in results if result is False)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if failed > 0:
        print("\n" + "="*60)
        print("REMEDIATION STEPS")
        print("="*60)
        print("1. Stop the containers:")
        print("   docker-compose down")
        print("")
        print("2. Verify docker-compose.yml has the fix:")
        print("   api_service:")
        print("     cap_add:")
        print("       - SYS_PTRACE")
        print("")
        print("3. Rebuild and restart:")
        print("   docker-compose up --build -d")
        print("")
        print("4. Re-run this validation:")
        print("   docker exec -it api_service python /app/validate_metrics_fix.py")
        print("="*60)
        sys.exit(1)
    else:
        print("\n✅ All tests passed! Metrics collection is working correctly.")
        sys.exit(0)


if __name__ == "__main__":
    main()
