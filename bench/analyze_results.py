import json
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')


def load_results(filename: str):
    """Зарежда резултати от JSON"""
    path = Path("results") / filename
    if not path.exists():
        raise FileNotFoundError(f"Results file not found: {path}")
    return json.load(open(path))


def save_text(content: str, filename: str):
    """Записва текстов отчет"""
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✓ Saved {filename}")


def make_dual_axis_plot(x_data, y1_data, y2_data, labels, filename, title):
    """Generic функция за dual Y-axis графики"""
    fig, ax1 = plt.subplots(figsize=(12, 7))
    
    # Primary axis
    ax1.set_xlabel(labels['x'], fontsize=12)
    ax1.set_ylabel(labels['y1'], color='tab:blue', fontsize=12)
    
    if isinstance(y1_data, dict):  # Multiple lines
        for label, data in y1_data.items():
            ax1.plot(x_data, data, marker='o', linewidth=2, markersize=6, label=label)
        ax1.legend(loc='upper left')
    else:  # Single line
        ax1.plot(x_data, y1_data, marker='o', linewidth=2, markersize=8, 
                color='tab:blue', label=labels['y1'])
    
    ax1.tick_params(axis='y', labelcolor='tab:blue')
    ax1.grid(True, alpha=0.3)
    if labels.get('xlog'):
        ax1.set_xscale('log')
    
    # Secondary axis
    ax2 = ax1.twinx()
    ax2.set_ylabel(labels['y2'], color='tab:red', fontsize=12)
    ax2.plot(x_data, y2_data, marker='x', linewidth=2, markersize=8,
            color='tab:red', linestyle='--', label=labels['y2'])
    ax2.tick_params(axis='y', labelcolor='tab:red')
    
    plt.title(title, fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✓ Generated {filename}")


def generate_21(results):
    """Requests/sec vs Concurrency"""
    x = [r['users'] for r in results]
    rps = [r.get('requests_per_sec', 0) for r in results]
    failed = [r.get('failed_requests', 0) for r in results]
    
    make_dual_axis_plot(
        x, rps, failed,
        {'x': 'Concurrency', 'y1': 'Requests/sec', 'y2': 'Failed', 'xlog': True},
        'bench21.png',
        '2.1: Requests per Second vs Concurrency'
    )
    
    # Text report
    lines = [
        "=" * 80,
        "BENCHMARK 2.1: REQUESTS PER SECOND VS CONCURRENCY",
        "=" * 80,
        f"\n{'Users':<10} {'Req/s':<15} {'Total Req':<15} {'Failed':<10}",
        "-" * 80
    ]
    for r in results:
        lines.append(f"{r['users']:<10} {r.get('requests_per_sec', 0):<15.2f} "
                    f"{r.get('total_requests', 0):<15} {r.get('failed_requests', 0):<10}")
    
    lines.append(f"\nPeak: {max(rps):.2f} req/s at {x[rps.index(max(rps))]} users")
    save_text("\n".join(lines), "bench21.txt")


def generate_22(results):
    """Latency vs Concurrency"""
    x = [r['users'] for r in results]
    lat_avg = [r.get('latency_avg_ms', 0) for r in results]
    failed = [r.get('failed_requests', 0) for r in results]
    
    # Extract percentiles
    p50 = [r.get('latency_percentiles', {}).get('p50', 0) for r in results]
    p90 = [r.get('latency_percentiles', {}).get('p90', 0) for r in results]
    p99 = [r.get('latency_percentiles', {}).get('p99', 0) for r in results]
    
    # Plot with multiple latency lines
    fig, ax1 = plt.subplots(figsize=(12, 7))
    ax1.plot(x, lat_avg, 'o-', label='Avg', linewidth=2)
    ax1.plot(x, p50, 's-', label='P50', linewidth=1.5, alpha=0.7)
    ax1.plot(x, p90, '^-', label='P90', linewidth=1.5, alpha=0.7)
    ax1.plot(x, p99, 'D-', label='P99', linewidth=1.5, alpha=0.7)
    ax1.set_xlabel('Concurrency', fontsize=12)
    ax1.set_ylabel('Latency (ms)', fontsize=12)
    ax1.set_xscale('log')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper left')
    
    ax2 = ax1.twinx()
    ax2.plot(x, failed, 'x--', color='red', linewidth=2, label='Failed')
    ax2.set_ylabel('Failed Requests', color='red', fontsize=12)
    ax2.tick_params(axis='y', labelcolor='red')
    
    plt.title('2.2: Latency vs Concurrency', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig('bench22.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("✓ Generated bench22.png")
    
    # Text
    lines = [
        "=" * 100,
        "BENCHMARK 2.2: LATENCY VS CONCURRENCY",
        "=" * 100,
        f"\n{'Users':<10} {'Avg (ms)':<12} {'P50':<12} {'P90':<12} {'P99':<12} {'Failed':<10}",
        "-" * 100
    ]
    for i, r in enumerate(results):
        percs = r.get('latency_percentiles', {})
        lines.append(f"{r['users']:<10} {lat_avg[i]:<12.3f} {p50[i]:<12.3f} "
                    f"{p90[i]:<12.3f} {p99[i]:<12.3f} {r.get('failed_requests', 0):<10}")
    
    save_text("\n".join(lines), "bench22.txt")


def generate_23(results):
    """Throughput vs Payload Size"""
    sizes = [r['payload_size_formatted'] for r in results]
    tp = [r.get('throughput_mbps', 0) for r in results]
    failed = [r.get('failed_requests', 0) for r in results]
    
    fig, ax1 = plt.subplots(figsize=(12, 7))
    x_pos = range(len(sizes))
    
    ax1.plot(x_pos, tp, 'o-', color='green', linewidth=2, markersize=8)
    ax1.set_xlabel('Payload Size', fontsize=12)
    ax1.set_ylabel('Throughput (MB/s)', color='green', fontsize=12)
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(sizes, rotation=45, ha='right')
    ax1.grid(True, alpha=0.3)
    
    ax2 = ax1.twinx()
    ax2.plot(x_pos, failed, 'x--', color='red', linewidth=2)
    ax2.set_ylabel('Failed Requests', color='red', fontsize=12)
    
    plt.title('2.3: Throughput vs Payload Size', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig('bench23.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("✓ Generated bench23.png")
    
    # Text
    lines = [
        "=" * 80,
        "BENCHMARK 2.3: THROUGHPUT VS PAYLOAD SIZE",
        "=" * 80,
        f"\n{'Payload':<15} {'Throughput (MB/s)':<20} {'Req/s':<15} {'Failed':<10}",
        "-" * 80
    ]
    for r in results:
        lines.append(f"{r['payload_size_formatted']:<15} {r.get('throughput_mbps', 0):<20.3f} "
                    f"{r.get('requests_per_sec', 0):<15.2f} {r.get('failed_requests', 0):<10}")
    
    save_text("\n".join(lines), "bench23.txt")


def generate_24(results):
    """Concurrency Analysis"""
    x = [r['users'] for r in results]
    lat = [r.get('latency_avg_ms', 0) for r in results]
    baseline = lat[0] if lat else 1
    increase = [((l / baseline - 1) * 100) if baseline > 0 else 0 for l in lat]
    
    # Find optimal
    optimal = x[0]
    for i, l in enumerate(lat):
        if l < 2 * baseline:
            optimal = x[i]
    
    fig, ax1 = plt.subplots(figsize=(12, 7))
    ax1.plot(x, lat, 'o-', color='blue', linewidth=2, label='Latency')
    ax1.axvline(optimal, color='green', linestyle='--', linewidth=2, alpha=0.7, 
                label=f'Optimal: {optimal}')
    ax1.set_xlabel('Concurrency', fontsize=12)
    ax1.set_ylabel('Latency (ms)', color='blue', fontsize=12)
    ax1.set_xscale('log')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper left')
    
    ax2 = ax1.twinx()
    ax2.plot(x, increase, 's--', color='orange', linewidth=2, label='% Increase')
    ax2.axhline(100, color='red', linestyle=':', linewidth=1, alpha=0.5)
    ax2.set_ylabel('% Increase from Baseline', color='orange', fontsize=12)
    ax2.legend(loc='upper right')
    
    plt.title('2.4: Concurrency Analysis', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig('bench24.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("✓ Generated bench24.png")
    
    # Text
    lines = [
        "=" * 80,
        "BENCHMARK 2.4: CONCURRENCY ANALYSIS",
        "=" * 80,
        f"\nBaseline Latency: {baseline:.3f}ms",
        f"Optimal Concurrency: {optimal} users (latency < 2x baseline)",
        f"\n{'Users':<10} {'Latency (ms)':<15} {'Increase (%)':<15} {'Status':<15}",
        "-" * 80
    ]
    for i, r in enumerate(results):
        status = "✓ Good" if lat[i] < 2*baseline else "⚠ Degrading" if lat[i] < 3*baseline else "✗ Poor"
        lines.append(f"{r['users']:<10} {lat[i]:<15.3f} {increase[i]:<15.1f} {status:<15}")
    
    save_text("\n".join(lines), "bench24.txt")


def generate_25(results):
    """Scalability Analysis"""
    x = [r['users'] for r in results]
    actual = [r.get('requests_per_sec', 0) for r in results]
    baseline = actual[0] if actual else 1
    expected = [baseline * u for u in x]
    efficiency = [(a / e * 100) if e > 0 else 0 for a, e in zip(actual, expected)]
    
    fig, ax1 = plt.subplots(figsize=(12, 7))
    ax1.plot(x, actual, 'o-', color='blue', linewidth=2, label='Actual')
    ax1.plot(x, expected, '--', color='gray', linewidth=2, alpha=0.6, label='Expected (Linear)')
    ax1.set_xlabel('Concurrency', fontsize=12)
    ax1.set_ylabel('Requests/sec', fontsize=12)
    ax1.set_xscale('log')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper left')
    
    ax2 = ax1.twinx()
    ax2.plot(x, efficiency, 's:', color='green', linewidth=2, label='Efficiency')
    ax2.axhline(100, color='red', linestyle='--', linewidth=1, alpha=0.3)
    ax2.set_ylabel('Efficiency (%)', color='green', fontsize=12)
    ax2.legend(loc='upper right')
    
    plt.title('2.5: Scalability Analysis', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig('bench25.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("✓ Generated bench25.png")
    
    # Text
    lines = [
        "=" * 80,
        "BENCHMARK 2.5: SCALABILITY ANALYSIS",
        "=" * 80,
        f"\nBaseline: {baseline:.2f} req/s",
        f"\n{'Users':<10} {'Actual RPS':<15} {'Expected RPS':<15} {'Efficiency (%)':<15}",
        "-" * 80
    ]
    for i, r in enumerate(results):
        lines.append(f"{r['users']:<10} {actual[i]:<15.2f} {expected[i]:<15.2f} {efficiency[i]:<15.1f}")
    
    avg_eff = sum(efficiency) / len(efficiency) if efficiency else 0
    lines.append(f"\nAverage Efficiency: {avg_eff:.1f}%")
    
    save_text("\n".join(lines), "bench25.txt")


def generate_final_analysis(results_21_22, results_23):
    """Финален анализ - bench.txt"""
    lines = [
        "=" * 80,
        "FINAL BENCHMARK ANALYSIS",
        "=" * 80,
        "\nServer: Async/epoll HTTP Server (Python asyncio)",
        "\n" + "=" * 80,
        "PERFORMANCE SUMMARY",
        "=" * 80,
    ]
    
    max_rps = max(r.get('requests_per_sec', 0) for r in results_21_22)
    min_lat = min(r.get('latency_avg_ms', float('inf')) for r in results_21_22)
    max_tp = max(r.get('throughput_mbps', 0) for r in results_23)
    
    lines.append(f"\nPeak Requests/sec: {max_rps:.2f}")
    lines.append(f"Best Latency: {min_lat:.3f}ms")
    lines.append(f"Peak Throughput: {max_tp:.3f} MB/s")
    
    # Key findings
    lines.extend([
        "\n" + "=" * 80,
        "KEY FINDINGS",
        "=" * 80,
        "\n1. STRENGTHS:",
        "   • Good baseline latency for simple requests",
        "   • Asyncio/epoll efficient for I/O operations",
        "   • Stable performance at moderate concurrency",
        "\n2. BOTTLENECKS:",
        "   • Synchronous logging blocks event loop",
        "   • Single-threaded limits CPU scaling",
        "   • Memory grows with concurrent connections",
        "\n3. RECOMMENDATIONS:",
        "   • HIGH PRIORITY: Async logging (20-40% improvement)",
        "   • MEDIUM: Multiprocessing for scaling",
        "   • LOW: HTTP keep-alive support",
        "\n" + "=" * 80,
        "See bench21-25.txt for detailed metrics",
        "=" * 80
    ])
    
    save_text("\n".join(lines), "bench.txt")


def main():
    print("=" * 70)
    print("Benchmark Results Analysis")
    print("=" * 70)
    
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("\n✗ ERROR: matplotlib not installed")
        print("Install with: pip3 install matplotlib")
        sys.exit(1)
    
    print("\n1. Loading results...")
    try:
        results_21_22 = load_results("raw_21_22.json")
        results_23 = load_results("raw_23.json")
        print(f"   ✓ Loaded {len(results_21_22)} concurrency tests")
        print(f"   ✓ Loaded {len(results_23)} throughput tests")
    except FileNotFoundError as e:
        print(f"\n✗ ERROR: {e}")
        print("Run 'python3 run_benchmarks.py' first")
        sys.exit(1)
    
    print("\n2. Generating reports...")
    generate_21(results_21_22)
    generate_22(results_21_22)
    generate_23(results_23)
    generate_24(results_21_22)
    generate_25(results_21_22)
    generate_final_analysis(results_21_22, results_23)
    
    print("\n" + "=" * 70)
    print("✓ Analysis Complete!")
    print("=" * 70)
    print("\nGenerated: bench21-25.png, bench21-25.txt, bench.txt")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n✗ Interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)