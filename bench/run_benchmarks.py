#!/usr/bin/env python3
"""
Главен скрипт за изпълнение на всички benchmark тестове.

Изпълнява:
- 2.1: Requests/sec при различна паралелност
- 2.2: Latency при различна паралелност  
- 2.3: Throughput при различни payload размери
- Резултатите се записват в results/ директория
"""

import sys
import time
import subprocess
from pathlib import Path
from benchmark_lib_locust import LocustBenchmark, save_results


def check_server_running(url: str = "http://127.0.0.1:9090") -> bool:
    """Проверява дали сървърът работи"""
    import socket
    from urllib.parse import urlparse
    
    parsed = urlparse(url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 9090
    
    try:
        sock = socket.create_connection((host, port), timeout=2)
        sock.close()
        return True
    except (socket.error, socket.timeout):
        return False


def wait_for_server(max_wait: int = 30) -> bool:
    """Изчаква сървърът да стартира"""
    print("Checking if server is running...")
    
    for i in range(max_wait):
        if check_server_running():
            print("✓ Server is running")
            return True
        
        if i == 0:
            print("Server not responding, waiting...")
        
        time.sleep(1)
    
    return False


def main():
    """Главна функция"""
    
    print("=" * 70)
    print("HTTP Server Benchmark Suite")
    print("=" * 70)
    
    # Инициализация
    locust = LocustBenchmark()
    
    # Проверка за locust
    print("\n1. Checking prerequisites...")
    if not locust.check_locust_installed():
        print("✗ ERROR: locust is not installed or not in PATH")
        print("\nTo install locust:")
        print("  pip3 install locust")
        print("  or: pip install locust")
        sys.exit(1)
    print("✓ locust is installed")
    
    # Проверка за сървър
    print("\n2. Checking server...")
    if not wait_for_server():
        print("✗ ERROR: Server is not running on http://127.0.0.1:9090")
        print("\nPlease start the server first:")
        print("  python3 server.py")
        sys.exit(1)
    
    # Параметри на тестовете
    DURATION = 30  # 30 секунди за всеки тест
    CONCURRENCY_LEVELS = [1, 2, 5, 10, 50, 100, 1000]
    PAYLOAD_SIZES = [
        1,                      # 1B
        1024,                   # 1KB
        100 * 1024,             # 100KB
        1024 * 1024,            # 1MB
        10 * 1024 * 1024,       # 10MB
        100 * 1024 * 1024,      # 100MB (над лимита)
        1024 * 1024 * 1024,     # 1GB (над лимита)
    ]
    
    print(f"\nTest Configuration:")
    print(f"  Duration per test: {DURATION}s")
    print(f"  Concurrency levels: {CONCURRENCY_LEVELS}")
    print(f"  Payload sizes: {[locust._format_size(s) for s in PAYLOAD_SIZES]}")
    
    # Изчисляване на приблизително време
    total_tests = len(CONCURRENCY_LEVELS) * 2 + len(PAYLOAD_SIZES)  # 2.1, 2.2, 2.3
    estimated_time = (total_tests * DURATION + total_tests * 2) / 60  # +2s cooldown
    print(f"  Estimated total time: ~{estimated_time:.1f} minutes")
    
    input("\nPress Enter to start benchmarks (or Ctrl+C to cancel)...")
    
    # ========================================================================
    # TEST 2.1 & 2.2: Requests/sec и Latency при различна паралелност
    # ========================================================================
    # Забележка: Тези два теста се правят едновременно, защото wrk
    # връща и двете метрики в един run
    
    print("\n" + "=" * 70)
    print("TEST 2.1 & 2.2: Requests/sec and Latency vs Concurrency")
    print("=" * 70)
    
    results_21_22 = locust.run_concurrency_test(
        concurrency_levels=CONCURRENCY_LEVELS,
        duration=DURATION
    )
    
    # Записваме резултатите
    save_results(results_21_22, "raw_21_22.json")
    
    print("\n✓ Tests 2.1 and 2.2 completed")
    
    # ========================================================================
    # TEST 2.3: Throughput при различни payload размери
    # ========================================================================
    
    print("\n" + "=" * 70)
    print("TEST 2.3: Throughput vs Payload Size")
    print("=" * 70)
    print("\nNote: Testing with POST requests")
    print("Payloads over 10MB will likely fail (server limit)")
    
    results_23 = locust.run_throughput_test(
        payload_sizes=PAYLOAD_SIZES,
        users=10,  # Константна паралелност
        duration=DURATION
    )
    
    save_results(results_23, "raw_23.json")
    
    print("\n✓ Test 2.3 completed")
    
    # ========================================================================
    # Summary
    # ========================================================================
    
    print("\n" + "=" * 70)
    print("BENCHMARK SUMMARY")
    print("=" * 70)
    
    print("\n2.1 & 2.2 Results (Concurrency):")
    print(f"{'Users':<15} {'Req/s':<12} {'Latency (ms)':<15} {'Failed':<10}")
    print("-" * 52)
    for r in results_21_22:
        print(f"{r['users']:<15} "
              f"{r.get('requests_per_sec', 0):<12.2f} "
              f"{r.get('latency_avg_ms', 0):<15.2f} "
              f"{r.get('failed_requests', 0):<10}")
    
    print("\n2.3 Results (Throughput):")
    print(f"{'Payload':<15} {'Throughput':<15} {'Failed':<10}")
    print("-" * 40)
    for r in results_23:
        print(f"{r['payload_size_formatted']:<15} "
              f"{r.get('throughput_mbps', 0):<15.2f} MB/s "
              f"{r.get('failed_requests', 0):<10}")
    
    print("\n" + "=" * 70)
    print("Raw results saved in results/ directory")
    print("Next step: Run analyze_results.py to generate graphs and reports")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✗ Benchmark interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)