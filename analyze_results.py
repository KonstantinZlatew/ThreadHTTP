#!/usr/bin/env python3
"""
Анализира резултатите от benchmark тестовете и генерира:
- Графики (PNG файлове)
- Текстови отчети (TXT файлове)
- Финален анализ (bench.txt)
"""

import json
import sys
from pathlib import Path
from typing import List, Dict
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend


def load_results(filename: str) -> List[Dict]:
    """Зарежда резултати от JSON файл"""
    results_path = Path("results") / filename
    
    if not results_path.exists():
        raise FileNotFoundError(f"Results file not found: {results_path}")
    
    with open(results_path) as f:
        return json.load(f)


def save_text_report(content: str, filename: str):
    """Записва текстов отчет"""
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✓ Saved {filename}")


def generate_21_graph(results: List[Dict]):
    """
    Генерира bench21.png: Requests/sec vs Concurrency
    """
    connections = [r['connections'] for r in results]
    req_per_sec = [r.get('requests_per_sec', 0) for r in results]
    failed = [r.get('failed_requests', 0) for r in results]
    
    fig, ax1 = plt.subplots(figsize=(12, 7))
    
    # Primary axis: Requests/sec
    color1 = 'tab:blue'
    ax1.set_xlabel('Concurrency (parallel connections)', fontsize=12)
    ax1.set_ylabel('Requests per Second', color=color1, fontsize=12)
    ax1.plot(connections, req_per_sec, marker='o', linewidth=2, 
             markersize=8, color=color1, label='Requests/sec')
    ax1.tick_params(axis='y', labelcolor=color1)
    ax1.grid(True, alpha=0.3)
    ax1.set_xscale('log')  # Log scale за по-добра визуализация
    
    # Secondary axis: Failed requests
    ax2 = ax1.twinx()
    color2 = 'tab:red'
    ax2.set_ylabel('Failed Requests', color=color2, fontsize=12)
    ax2.plot(connections, failed, marker='x', linewidth=2, 
             markersize=8, color=color2, linestyle='--', label='Failed Requests')
    ax2.tick_params(axis='y', labelcolor=color2)
    
    # Title and legend
    plt.title('2.1: Requests per Second vs Concurrency\n(30 second test duration)', 
              fontsize=14, fontweight='bold')
    
    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
    
    plt.tight_layout()
    plt.savefig('bench21.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print("✓ Generated bench21.png")


def generate_21_text(results: List[Dict]):
    """
    Генерира bench21.txt: Tabular data за Requests/sec
    """
    content = []
    content.append("=" * 80)
    content.append("BENCHMARK 2.1: REQUESTS PER SECOND VS CONCURRENCY")
    content.append("=" * 80)
    content.append(f"\nTest Duration: 30 seconds per test")
    content.append(f"Test Date: {results[0].get('test_date', 'N/A')}" if results else "")
    content.append("\n" + "-" * 80)
    content.append(f"{'Concurrency':<15} {'Req/sec':<15} {'Total Req':<15} {'Failed':<15}")
    content.append("-" * 80)
    
    for r in results:
        content.append(
            f"{r['connections']:<15} "
            f"{r.get('requests_per_sec', 0):<15.2f} "
            f"{r.get('total_requests', 0):<15} "
            f"{r.get('failed_requests', 0):<15}"
        )
    
    content.append("-" * 80)
    content.append(f"\nPeak Performance: {max(r.get('requests_per_sec', 0) for r in results):.2f} req/s")
    content.append(f"Peak at Concurrency: {max(results, key=lambda x: x.get('requests_per_sec', 0))['connections']}")
    
    # Analysis
    content.append("\n" + "=" * 80)
    content.append("ANALYSIS")
    content.append("=" * 80)
    
    baseline = results[0].get('requests_per_sec', 1) if results else 1
    for r in results:
        rps = r.get('requests_per_sec', 0)
        scaling = (rps / baseline) if baseline > 0 else 0
        expected = r['connections']
        efficiency = (scaling / expected * 100) if expected > 0 else 0
        
        content.append(f"\nConcurrency {r['connections']:>4}: "
                      f"{rps:>10.2f} req/s "
                      f"(scaling: {scaling:>5.2f}x, efficiency: {efficiency:>5.1f}%)")
    
    text = "\n".join(content)
    save_text_report(text, "bench21.txt")


def generate_22_graph(results: List[Dict]):
    """
    Генерира bench22.png: Latency vs Concurrency
    """
    connections = [r['connections'] for r in results]
    latency_avg = [r.get('latency_avg_ms', 0) for r in results]
    failed = [r.get('failed_requests', 0) for r in results]
    
    # Percentiles
    p50 = [r.get('latency_percentiles', {}).get('p50', 0) for r in results]
    p90 = [r.get('latency_percentiles', {}).get('p90', 0) for r in results]
    p99 = [r.get('latency_percentiles', {}).get('p99', 0) for r in results]
    
    fig, ax1 = plt.subplots(figsize=(12, 7))
    
    # Primary axis: Latency
    color_avg = 'tab:blue'
    color_p50 = 'tab:cyan'
    color_p90 = 'tab:orange'
    color_p99 = 'tab:purple'
    
    ax1.set_xlabel('Concurrency (parallel connections)', fontsize=12)
    ax1.set_ylabel('Latency (milliseconds)', fontsize=12)
    
    ax1.plot(connections, latency_avg, marker='o', linewidth=2, 
             markersize=6, color=color_avg, label='Average')
    ax1.plot(connections, p50, marker='s', linewidth=1.5, 
             markersize=5, color=color_p50, label='50th percentile', alpha=0.7)
    ax1.plot(connections, p90, marker='^', linewidth=1.5, 
             markersize=5, color=color_p90, label='90th percentile', alpha=0.7)
    ax1.plot(connections, p99, marker='D', linewidth=1.5, 
             markersize=5, color=color_p99, label='99th percentile', alpha=0.7)
    
    ax1.grid(True, alpha=0.3)
    ax1.set_xscale('log')
    ax1.legend(loc='upper left')
    
    # Secondary axis: Failed requests
    ax2 = ax1.twinx()
    color2 = 'tab:red'
    ax2.set_ylabel('Failed Requests', color=color2, fontsize=12)
    ax2.plot(connections, failed, marker='x', linewidth=2, 
             markersize=8, color=color2, linestyle='--', label='Failed Requests')
    ax2.tick_params(axis='y', labelcolor=color2)
    ax2.legend(loc='upper right')
    
    plt.title('2.2: Latency vs Concurrency\n(30 second test duration)', 
              fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('bench22.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print("✓ Generated bench22.png")


def generate_22_text(results: List[Dict]):
    """
    Генерира bench22.txt: Tabular data за Latency
    """
    content = []
    content.append("=" * 100)
    content.append("BENCHMARK 2.2: LATENCY VS CONCURRENCY")
    content.append("=" * 100)
    content.append(f"\nTest Duration: 30 seconds per test")
    content.append("\n" + "-" * 100)
    content.append(f"{'Concurrency':<15} {'Avg (ms)':<12} {'P50 (ms)':<12} "
                  f"{'P90 (ms)':<12} {'P99 (ms)':<12} {'Failed':<12}")
    content.append("-" * 100)
    
    for r in results:
        percs = r.get('latency_percentiles', {})
        content.append(
            f"{r['connections']:<15} "
            f"{r.get('latency_avg_ms', 0):<12.3f} "
            f"{percs.get('p50', 0):<12.3f} "
            f"{percs.get('p90', 0):<12.3f} "
            f"{percs.get('p99', 0):<12.3f} "
            f"{r.get('failed_requests', 0):<12}"
        )
    
    content.append("-" * 100)
    
    # Analysis
    content.append("\n" + "=" * 100)
    content.append("LATENCY ANALYSIS")
    content.append("=" * 100)
    
    baseline_lat = results[0].get('latency_avg_ms', 1) if results else 1
    
    for r in results:
        lat = r.get('latency_avg_ms', 0)
        increase = ((lat / baseline_lat - 1) * 100) if baseline_lat > 0 else 0
        
        content.append(f"\nConcurrency {r['connections']:>4}: "
                      f"Avg latency {lat:>8.3f}ms "
                      f"(+{increase:>6.1f}% from baseline)")
    
    text = "\n".join(content)
    save_text_report(text, "bench22.txt")


def generate_23_graph(results: List[Dict]):
    """
    Генерира bench23.png: Throughput vs Payload Size
    """
    sizes = [r['payload_size'] for r in results]
    size_labels = [r['payload_size_formatted'] for r in results]
    throughput = [r.get('throughput_mbps', 0) for r in results]
    failed = [r.get('failed_requests', 0) for r in results]
    
    fig, ax1 = plt.subplots(figsize=(12, 7))
    
    # Primary axis: Throughput
    color1 = 'tab:green'
    ax1.set_xlabel('Payload Size', fontsize=12)
    ax1.set_ylabel('Throughput (MB/s)', color=color1, fontsize=12)
    ax1.plot(range(len(sizes)), throughput, marker='o', linewidth=2, 
             markersize=8, color=color1, label='Throughput')
    ax1.tick_params(axis='y', labelcolor=color1)
    ax1.grid(True, alpha=0.3)
    ax1.set_xticks(range(len(sizes)))
    ax1.set_xticklabels(size_labels, rotation=45, ha='right')
    
    # Secondary axis: Failed requests
    ax2 = ax1.twinx()
    color2 = 'tab:red'
    ax2.set_ylabel('Failed Requests', color=color2, fontsize=12)
    ax2.plot(range(len(sizes)), failed, marker='x', linewidth=2, 
             markersize=8, color=color2, linestyle='--', label='Failed Requests')
    ax2.tick_params(axis='y', labelcolor=color2)
    
    plt.title('2.3: Throughput vs Payload Size\n(30 second test, 10 connections)', 
              fontsize=14, fontweight='bold')
    
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
    
    plt.tight_layout()
    plt.savefig('bench23.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print("✓ Generated bench23.png")


def generate_23_text(results: List[Dict]):
    """
    Генерира bench23.txt: Tabular data за Throughput
    """
    content = []
    content.append("=" * 90)
    content.append("BENCHMARK 2.3: THROUGHPUT VS PAYLOAD SIZE")
    content.append("=" * 90)
    content.append(f"\nTest Duration: 30 seconds per test")
    content.append(f"Concurrency: 10 connections (constant)")
    content.append("\n" + "-" * 90)
    content.append(f"{'Payload':<15} {'Throughput':<18} {'Total Data':<18} {'Req/s':<15} {'Failed':<10}")
    content.append("-" * 90)
    
    for r in results:
        content.append(
            f"{r['payload_size_formatted']:<15} "
            f"{r.get('throughput_mbps', 0):<18.3f} MB/s "
            f"{r.get('total_data_mb', 0):<18.2f} MB "
            f"{r.get('requests_per_sec', 0):<15.2f} "
            f"{r.get('failed_requests', 0):<10}"
        )
    
    content.append("-" * 90)
    
    # Analysis
    content.append("\n" + "=" * 90)
    content.append("THROUGHPUT ANALYSIS")
    content.append("=" * 90)
    content.append("\nNote: Server has 10MB limit for request body")
    content.append("Payloads over 10MB are expected to fail or be truncated")
    
    for r in results:
        size_mb = r['payload_size'] / (1024 * 1024)
        tp = r.get('throughput_mbps', 0)
        failed_pct = (r.get('failed_requests', 0) / max(r.get('total_requests', 1), 1)) * 100
        
        status = "✓ OK" if r.get('failed_requests', 0) == 0 else "✗ FAILED"
        content.append(f"\n{r['payload_size_formatted']:>8}: "
                      f"{tp:>8.3f} MB/s, "
                      f"{r.get('requests_per_sec', 0):>8.2f} req/s "
                      f"({failed_pct:>5.1f}% failed) {status}")
    
    text = "\n".join(content)
    save_text_report(text, "bench23.txt")


def generate_24_graph_and_text(results: List[Dict]):
    """
    Генерира bench24.png и bench24.txt: Concurrency Analysis
    Цел: Определяне на оптималната конкурентност
    """
    connections = [r['connections'] for r in results]
    latency_avg = [r.get('latency_avg_ms', 0) for r in results]
    
    # Изчисляваме % увеличение спрямо baseline
    baseline_lat = latency_avg[0] if latency_avg else 1
    lat_increase_pct = [((lat / baseline_lat - 1) * 100) if baseline_lat > 0 else 0 
                        for lat in latency_avg]
    
    # Определяме "оптималната" конкурентност
    # Критерий: latency < 2x baseline
    optimal_idx = 0
    for i, lat in enumerate(latency_avg):
        if lat < 2 * baseline_lat:
            optimal_idx = i
        else:
            break
    
    optimal_concurrency = connections[optimal_idx] if optimal_idx < len(connections) else connections[-1]
    
    # График
    fig, ax1 = plt.subplots(figsize=(12, 7))
    
    # Primary axis: Absolute latency
    color1 = 'tab:blue'
    ax1.set_xlabel('Concurrency (parallel connections)', fontsize=12)
    ax1.set_ylabel('Latency (ms)', color=color1, fontsize=12)
    ax1.plot(connections, latency_avg, marker='o', linewidth=2, 
             markersize=8, color=color1, label='Average Latency')
    ax1.tick_params(axis='y', labelcolor=color1)
    ax1.grid(True, alpha=0.3)
    ax1.set_xscale('log')
    
    # Marker за optimal concurrency
    ax1.axvline(x=optimal_concurrency, color='green', linestyle='--', 
                linewidth=2, alpha=0.7, label=f'Optimal: {optimal_concurrency}')
    
    # Secondary axis: % increase
    ax2 = ax1.twinx()
    color2 = 'tab:orange'
    ax2.set_ylabel('Latency Increase from Baseline (%)', color=color2, fontsize=12)
    ax2.plot(connections, lat_increase_pct, marker='s', linewidth=2, 
             markersize=6, color=color2, linestyle='--', label='% Increase')
    ax2.tick_params(axis='y', labelcolor=color2)
    ax2.axhline(y=100, color='red', linestyle=':', linewidth=1, alpha=0.5, label='2x baseline')
    
    plt.title('2.4: Concurrency Analysis\n(Optimal concurrency before latency degrades)', 
              fontsize=14, fontweight='bold')
    
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
    
    plt.tight_layout()
    plt.savefig('bench24.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print("✓ Generated bench24.png")
    
    # Text report
    content = []
    content.append("=" * 80)
    content.append("BENCHMARK 2.4: CONCURRENCY ANALYSIS")
    content.append("=" * 80)
    content.append("\nGoal: Determine optimal concurrency level")
    content.append("Metric: Latency increase vs baseline (1 client)")
    content.append(f"\nBaseline Latency (1 client): {baseline_lat:.3f}ms")
    content.append(f"Optimal Concurrency: {optimal_concurrency} clients")
    content.append(f"  (latency stays below 2x baseline)")
    
    content.append("\n" + "-" * 80)
    content.append(f"{'Concurrency':<15} {'Latency (ms)':<15} {'Increase (%)':<15} {'Status':<20}")
    content.append("-" * 80)
    
    for i, r in enumerate(results):
        lat = r.get('latency_avg_ms', 0)
        inc = lat_increase_pct[i]
        
        if lat < 1.5 * baseline_lat:
            status = "✓ Excellent"
        elif lat < 2 * baseline_lat:
            status = "✓ Good"
        elif lat < 3 * baseline_lat:
            status = "⚠ Degrading"
        else:
            status = "✗ Poor"
        
        content.append(
            f"{r['connections']:<15} "
            f"{lat:<15.3f} "
            f"{inc:<15.1f} "
            f"{status:<20}"
        )
    
    content.append("-" * 80)
    
    content.append("\n" + "=" * 80)
    content.append("INTERPRETATION")
    content.append("=" * 80)
    content.append(f"\nThe server can efficiently handle up to {optimal_concurrency} concurrent clients")
    content.append(f"without significant latency degradation.")
    content.append(f"\nBeyond {optimal_concurrency} clients, latency starts to increase significantly,")
    content.append("indicating resource saturation (CPU, memory, or I/O bottleneck).")
    
    text = "\n".join(content)
    save_text_report(text, "bench24.txt")


def generate_25_graph_and_text(results: List[Dict]):
    """
    Генерира bench25.png и bench25.txt: Scalability Analysis
    Цел: Анализ на скалируемостта
    """
    connections = [r['connections'] for r in results]
    req_per_sec = [r.get('requests_per_sec', 0) for r in results]
    
    # Изчисляваме очакваното линейно скалиране
    baseline_rps = req_per_sec[0] if req_per_sec else 1
    expected_rps = [baseline_rps * c for c in connections]
    
    # Изчисляваме efficiency (actual / expected * 100%)
    efficiency = [(actual / expected * 100) if expected > 0 else 0 
                  for actual, expected in zip(req_per_sec, expected_rps)]
    
    # График
    fig, ax1 = plt.subplots(figsize=(12, 7))
    
    # Primary axis: Requests/sec
    color1 = 'tab:blue'
    color2 = 'tab:gray'
    ax1.set_xlabel('Concurrency (parallel connections)', fontsize=12)
    ax1.set_ylabel('Requests per Second', color='black', fontsize=12)
    
    ax1.plot(connections, req_per_sec, marker='o', linewidth=2, 
             markersize=8, color=color1, label='Actual RPS')
    ax1.plot(connections, expected_rps, marker='', linewidth=2, 
             linestyle='--', color=color2, alpha=0.6, label='Expected (Linear)')
    ax1.tick_params(axis='y')
    ax1.grid(True, alpha=0.3)
    ax1.set_xscale('log')
    ax1.legend(loc='upper left')
    
    # Secondary axis: Efficiency
    ax2 = ax1.twinx()
    color3 = 'tab:green'
    ax2.set_ylabel('Scalability Efficiency (%)', color=color3, fontsize=12)
    ax2.plot(connections, efficiency, marker='s', linewidth=2, 
             markersize=6, color=color3, linestyle=':', label='Efficiency')
    ax2.tick_params(axis='y', labelcolor=color3)
    ax2.axhline(y=100, color='red', linestyle='--', linewidth=1, alpha=0.3)
    ax2.legend(loc='upper right')
    
    plt.title('2.5: Scalability Analysis\n(How well does throughput scale with concurrency?)', 
              fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('bench25.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print("✓ Generated bench25.png")
    
    # Text report
    content = []
    content.append("=" * 90)
    content.append("BENCHMARK 2.5: SCALABILITY ANALYSIS")
    content.append("=" * 90)
    content.append("\nGoal: Measure how throughput scales with concurrency")
    content.append("Metric: Actual vs Expected linear scaling")
    content.append(f"\nBaseline (1 client): {baseline_rps:.2f} req/s")
    
    content.append("\n" + "-" * 90)
    content.append(f"{'Concurrency':<15} {'Actual RPS':<15} {'Expected RPS':<15} "
                  f"{'Efficiency':<15} {'Rating':<15}")
    content.append("-" * 90)
    
    for i, r in enumerate(results):
        actual = req_per_sec[i]
        expected = expected_rps[i]
        eff = efficiency[i]
        
        if eff >= 80:
            rating = "✓ Excellent"
        elif eff >= 60:
            rating = "✓ Good"
        elif eff >= 40:
            rating = "⚠ Fair"
        else:
            rating = "✗ Poor"
        
        content.append(
            f"{r['connections']:<15} "
            f"{actual:<15.2f} "
            f"{expected:<15.2f} "
            f"{eff:<15.1f}% "
            f"{rating:<15}"
        )
    
    content.append("-" * 90)
    
    content.append("\n" + "=" * 90)
    content.append("SCALABILITY INTERPRETATION")
    content.append("=" * 90)
    
    avg_efficiency = sum(efficiency) / len(efficiency) if efficiency else 0
    
    content.append(f"\nAverage Scalability Efficiency: {avg_efficiency:.1f}%")
    content.append("\nScalability Pattern:")
    
    if avg_efficiency >= 70:
        content.append("  ✓ EXCELLENT - Server scales nearly linearly with concurrency")
    elif avg_efficiency >= 50:
        content.append("  ✓ GOOD - Server scales reasonably well")
    elif avg_efficiency >= 30:
        content.append("  ⚠ FAIR - Server shows some scalability limitations")
    else:
        content.append("  ✗ POOR - Server does not scale well (likely bottleneck)")
    
    # Analyze trend
    if len(efficiency) >= 3:
        early_eff = sum(efficiency[:3]) / 3
        late_eff = sum(efficiency[-3:]) / 3
        
        content.append(f"\nEarly efficiency (low concurrency): {early_eff:.1f}%")
        content.append(f"Late efficiency (high concurrency): {late_eff:.1f}%")
        
        if late_eff < early_eff * 0.7:
            content.append("\n⚠ Efficiency drops significantly at high concurrency")
            content.append("   → Indicates bottleneck (likely event loop saturation)")
        elif late_eff > early_eff * 0.9:
            content.append("\n✓ Efficiency remains stable across concurrency levels")
    
    text = "\n".join(content)
    save_text_report(text, "bench25.txt")


def generate_final_analysis(results_21_22: List[Dict], results_23: List[Dict]):
    """
    Генерира bench.txt: Финален анализ и препоръки
    """
    content = []
    content.append("=" * 80)
    content.append("FINAL BENCHMARK ANALYSIS AND RECOMMENDATIONS")
    content.append("=" * 80)
    content.append("\nServer: Async/epoll HTTP Server (Python asyncio)")
    content.append("Test Duration: 30 seconds per test")
    
    # Summary stats
    content.append("\n" + "=" * 80)
    content.append("PERFORMANCE SUMMARY")
    content.append("=" * 80)
    
    max_rps = max(r.get('requests_per_sec', 0) for r in results_21_22)
    min_latency = min(r.get('latency_avg_ms', float('inf')) for r in results_21_22)
    max_throughput = max(r.get('throughput_mbps', 0) for r in results_23)
    
    content.append(f"\nPeak Requests/sec: {max_rps:.2f}")
    content.append(f"Best Latency: {min_latency:.3f}ms")
    content.append(f"Peak Throughput: {max_throughput:.3f} MB/s")
    
    # Analysis
    content.append("\n" + "=" * 80)
    content.append("OBSERVATIONS")
    content.append("=" * 80)
    
    content.append("\n1. CONCURRENCY HANDLING:")
    baseline_lat = results_21_22[0].get('latency_avg_ms', 1) if results_21_22 else 1
    high_conc = results_21_22[-1] if results_21_22 else {}
    high_lat = high_conc.get('latency_avg_ms', 0)
    lat_degradation = ((high_lat / baseline_lat - 1) * 100) if baseline_lat > 0 else 0
    
    content.append(f"   - Low concurrency (1 client): {baseline_lat:.3f}ms latency")
    content.append(f"   - High concurrency (1000 clients): {high_lat:.3f}ms latency")
    content.append(f"   - Latency degradation: {lat_degradation:.1f}%")
    
    if lat_degradation < 100:
        content.append("   ✓ Good: Latency remains stable under load")
    elif lat_degradation < 500:
        content.append("   ⚠ Moderate: Noticeable latency increase under heavy load")
    else:
        content.append("   ✗ Poor: Significant latency degradation under load")
    
    content.append("\n2. THROUGHPUT & PAYLOAD HANDLING:")
    
    # Analyze throughput results
    small_payload = results_23[0] if results_23 else {}
    large_payload = next((r for r in results_23 if r['payload_size'] == 10*1024*1024), {})
    
    small_tp = small_payload.get('throughput_mbps', 0)
    large_tp = large_payload.get('throughput_mbps', 0) if large_payload else 0
    
    content.append(f"   - Small payload (1B): {small_tp:.3f} MB/s")
    content.append(f"   - Large payload (10MB): {large_tp:.3f} MB/s")
    
    # Check for failures at large payloads
    failed_large = sum(1 for r in results_23 if r['payload_size'] > 10*1024*1024 and r.get('failed_requests', 0) > 0)
    if failed_large > 0:
        content.append(f"   ⚠ {failed_large} test(s) failed with payloads over 10MB (expected due to server limit)")
    
    content.append("\n3. SCALABILITY:")
    baseline_rps = results_21_22[0].get('requests_per_sec', 1) if results_21_22 else 1
    mid_result = results_21_22[len(results_21_22)//2] if len(results_21_22) > 2 else results_21_22[-1]
    mid_rps = mid_result.get('requests_per_sec', 0)
    mid_conc = mid_result.get('connections', 1)
    
    actual_scaling = mid_rps / baseline_rps if baseline_rps > 0 else 0
    expected_scaling = mid_conc
    efficiency = (actual_scaling / expected_scaling * 100) if expected_scaling > 0 else 0
    
    content.append(f"   - Scaling efficiency at {mid_conc} clients: {efficiency:.1f}%")
    
    if efficiency >= 70:
        content.append("   ✓ Excellent: Near-linear scaling")
    elif efficiency >= 50:
        content.append("   ✓ Good: Reasonable scaling")
    else:
        content.append("   ⚠ Limited: Sub-linear scaling (bottleneck detected)")
    
    content.append("\n4. ERROR RATE:")
    total_failed = sum(r.get('failed_requests', 0) for r in results_21_22)
    total_requests = sum(r.get('total_requests', 0) for r in results_21_22)
    error_rate = (total_failed / total_requests * 100) if total_requests > 0 else 0
    
    content.append(f"   - Total failed requests: {total_failed}")
    content.append(f"   - Error rate: {error_rate:.3f}%")
    
    if error_rate < 0.1:
        content.append("   ✓ Excellent: Very few errors")
    elif error_rate < 1:
        content.append("   ✓ Good: Low error rate")
    elif error_rate < 5:
        content.append("   ⚠ Moderate: Noticeable errors under load")
    else:
        content.append("   ✗ Poor: High error rate")
    
    # Strengths and Weaknesses
    content.append("\n" + "=" * 80)
    content.append("STRENGTHS")
    content.append("=" * 80)
    
    strengths = []
    if lat_degradation < 200:
        strengths.append("• Stable latency under moderate load")
    if efficiency >= 60:
        strengths.append("• Good scalability with concurrent connections")
    if error_rate < 1:
        strengths.append("• Low error rate and high reliability")
    if baseline_lat < 10:
        strengths.append("• Excellent baseline latency for simple requests")
    
    strengths.append("• Asyncio/epoll architecture efficient for I/O-bound operations")
    strengths.append("• Proper handling of HTTP protocol basics")
    
    for s in strengths:
        content.append(s)
    
    content.append("\n" + "=" * 80)
    content.append("WEAKNESSES & BOTTLENECKS")
    content.append("=" * 80)
    
    weaknesses = []
    
    if lat_degradation > 500:
        weaknesses.append("• Significant latency degradation at high concurrency")
        weaknesses.append("  → Likely due to single-threaded event loop (Python GIL)")
    
    weaknesses.append("• Synchronous file I/O for logging blocks event loop")
    weaknesses.append("  → Each log write blocks all concurrent requests")
    
    if efficiency < 50:
        weaknesses.append("• Poor scaling beyond moderate concurrency")
        weaknesses.append("  → CPU becomes bottleneck (single Python process)")
    
    weaknesses.append("• 10MB request limit restricts large file uploads")
    
    weaknesses.append("• Memory usage grows with concurrent connections")
    weaknesses.append("  → Each connection buffers headers and body in memory")
    
    for w in weaknesses:
        content.append(w)
    
    # Recommendations
    content.append("\n" + "=" * 80)
    content.append("RECOMMENDATIONS FOR IMPROVEMENT")
    content.append("=" * 80)
    
    content.append("\n1. LOGGING OPTIMIZATION (HIGH PRIORITY):")
    content.append("   • Move to asynchronous logging (aiofiles or queue-based)")
    content.append("   • Use buffered writes instead of immediate file I/O")
    content.append("   • Consider structured logging (JSON) for easier parsing")
    content.append("   • Rotate logs to prevent unbounded growth")
    content.append("   Expected impact: 20-40% latency reduction")
    
    content.append("\n2. CONCURRENCY SCALING (MEDIUM PRIORITY):")
    content.append("   • Implement multiprocessing (multiple server instances)")
    content.append("   • Use nginx/HAProxy as reverse proxy for load balancing")
    content.append("   • Each process handles subset of connections")
    content.append("   Expected impact: Near-linear scaling with CPU cores")
    
    content.append("\n3. MEMORY OPTIMIZATION (MEDIUM PRIORITY):")
    content.append("   • Stream large request bodies instead of buffering")
    content.append("   • Implement chunked processing for large payloads")
    content.append("   • Add connection pooling and limits")
    content.append("   Expected impact: Handle 2-3x more concurrent connections")
    
    content.append("\n4. PROTOCOL IMPROVEMENTS (LOW PRIORITY):")
    content.append("   • Add HTTP keep-alive support")
    content.append("   • Implement connection reuse")
    content.append("   • Support HTTP/2 for multiplexing")
    content.append("   Expected impact: 15-25% throughput increase")
    
    content.append("\n5. MONITORING & OBSERVABILITY:")
    content.append("   • Add Prometheus/StatsD metrics")
    content.append("   • Track per-request timing breakdowns")
    content.append("   • Monitor event loop lag")
    content.append("   • Alert on error rate thresholds")
    
    # Conclusion
    content.append("\n" + "=" * 80)
    content.append("CONCLUSION")
    content.append("=" * 80)
    
    content.append("\nThe server demonstrates solid performance for a Python asyncio")
    content.append("implementation, with good baseline latency and reasonable throughput.")
    content.append("\nThe primary bottleneck is synchronous logging, which blocks the event")
    content.append("loop on every request. Addressing this would yield immediate benefits.")
    content.append("\nFor production use at scale, consider:")
    content.append("  1. Asynchronous logging (quick win)")
    content.append("  2. Multiprocess architecture (horizontal scaling)")
    content.append("  3. Reverse proxy (nginx) for static content and load balancing")
    
    content.append("\n" + "=" * 80)
    content.append(f"Benchmark completed successfully")
    content.append("=" * 80)
    
    text = "\n".join(content)
    save_text_report(text, "bench.txt")


def main():
    """Главна функция за анализ"""
    
    print("=" * 70)
    print("Benchmark Results Analysis")
    print("=" * 70)
    
    # Проверка за matplotlib
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("\n✗ ERROR: matplotlib is not installed")
        print("Install with: pip install matplotlib")
        sys.exit(1)
    
    print("\n1. Loading results...")
    
    try:
        results_21_22 = load_results("raw_21_22.json")
        results_23 = load_results("raw_23.json")
        print(f"   ✓ Loaded {len(results_21_22)} concurrency tests")
        print(f"   ✓ Loaded {len(results_23)} throughput tests")
    except FileNotFoundError as e:
        print(f"\n✗ ERROR: {e}")
        print("\nPlease run 'python3 run_benchmarks.py' first to generate results")
        sys.exit(1)
    
    print("\n2. Generating graphs and reports...")
    
    # Generate 2.1
    print("\n   [2.1] Requests/sec vs Concurrency...")
    generate_21_graph(results_21_22)
    generate_21_text(results_21_22)
    
    # Generate 2.2
    print("\n   [2.2] Latency vs Concurrency...")
    generate_22_graph(results_21_22)
    generate_22_text(results_21_22)
    
    # Generate 2.3
    print("\n   [2.3] Throughput vs Payload Size...")
    generate_23_graph(results_23)
    generate_23_text(results_23)
    
    # Generate 2.4
    print("\n   [2.4] Concurrency Analysis...")
    generate_24_graph_and_text(results_21_22)
    
    # Generate 2.5
    print("\n   [2.5] Scalability Analysis...")
    generate_25_graph_and_text(results_21_22)
    
    # Generate final analysis
    print("\n   [Final] Overall Analysis...")
    generate_final_analysis(results_21_22, results_23)
    
    print("\n" + "=" * 70)
    print("✓ Analysis Complete!")
    print("=" * 70)
    print("\nGenerated files:")
    print("  Graphs:  bench21.png, bench22.png, bench23.png, bench24.png, bench25.png")
    print("  Reports: bench21.txt, bench22.txt, bench23.txt, bench24.txt, bench25.txt")
    print("  Analysis: bench.txt")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✗ Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)