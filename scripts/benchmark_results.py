"""Aggregate benchmark runs by mode (standalone / distributed) and generate comparison charts.

Produces:
- docs/reports/benchmark_aggregate.csv
- docs/reports/throughput_comparison.png
- docs/reports/latency_comparison.png

Reads JSON files named `*_run*.json` in the `scripts/` folder.
"""
import glob
import json
import os
import statistics
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(__file__)
json_paths = sorted(glob.glob(os.path.join(HERE, '*_run*.json')))
if not json_paths:
    print('No run JSON files found in scripts/');
    raise SystemExit(1)

# Group by mode
groups = {}
for p in json_paths:
    with open(p, 'r', encoding='utf-8') as f:
        data = json.load(f)
    mode = data.get('context', {}).get('mode', 'unknown')
    perf = data.get('performance', {})
    latency = data.get('latency_ms', {})
    entry = {
        'file': os.path.basename(p),
        'throughput_mib_s': perf.get('average_throughput_mib_s', 0.0),
        'total_duration_sec': perf.get('total_duration_sec', 0.0),
        'total_uploaded_mib': perf.get('total_uploaded_mib', 0.0),
        'success_rate_percent': perf.get('success_rate_percent', 0.0),
        'latency_avg_ms': latency.get('average', 0.0),
        'latency_p95_ms': latency.get('p95', 0.0),
        'latency_p99_ms': latency.get('p99', 0.0),
    }
    groups.setdefault(mode, []).append(entry)

# Compute aggregates
out_dir = os.path.join(HERE, '..', 'docs', 'reports')
os.makedirs(out_dir, exist_ok=True)
aggregate_path = os.path.join(out_dir, 'benchmark_aggregate.csv')

agg_rows = []
for mode, entries in groups.items():
    throughputs = [e['throughput_mib_s'] for e in entries]
    lat_avg = [e['latency_avg_ms'] for e in entries]
    lat_p95 = [e['latency_p95_ms'] for e in entries]
    lat_p99 = [e['latency_p99_ms'] for e in entries]
    row = {
        'mode': mode,
        'runs': len(entries),
        'throughput_mean_mib_s': round(statistics.mean(throughputs), 4) if throughputs else 0.0,
        'throughput_stdev_mib_s': round(statistics.pstdev(throughputs), 4) if len(throughputs) > 1 else 0.0,
        'latency_avg_mean_ms': round(statistics.mean(lat_avg), 4) if lat_avg else 0.0,
        'latency_avg_stdev_ms': round(statistics.pstdev(lat_avg), 4) if len(lat_avg) > 1 else 0.0,
        'latency_p95_mean_ms': round(statistics.mean(lat_p95), 4) if lat_p95 else 0.0,
        'latency_p99_mean_ms': round(statistics.mean(lat_p99), 4) if lat_p99 else 0.0,
    }
    agg_rows.append(row)

# Save CSV
with open(aggregate_path, 'w', newline='', encoding='utf-8') as cf:
    fieldnames = ['mode', 'runs', 'throughput_mean_mib_s', 'throughput_stdev_mib_s',
                  'latency_avg_mean_ms', 'latency_avg_stdev_ms', 'latency_p95_mean_ms', 'latency_p99_mean_ms']
    writer = csv.DictWriter(cf, fieldnames=fieldnames)
    writer.writeheader()
    for r in agg_rows:
        writer.writerow(r)
print('Wrote', aggregate_path)

# Create comparison charts
modes = [r['mode'] for r in agg_rows]
throughput_means = [r['throughput_mean_mib_s'] for r in agg_rows]
throughput_stds = [r['throughput_stdev_mib_s'] for r in agg_rows]

# Throughput comparison
plt.figure(figsize=(7,5))
bars = plt.bar(modes, throughput_means, yerr=throughput_stds, capsize=8, color=['#1f77b4','#ff7f0e'])
plt.xlabel('Mode')
plt.ylabel('Mean Throughput (MiB/s)')
plt.title('Mean Throughput by Mode')
# Annotate bar values (show mean throughput on each bar)
for bar in bars:
    h = bar.get_height()
    plt.annotate(f"{h:.1f}",
                 xy=(bar.get_x() + bar.get_width() / 2, h),
                 xytext=(0, 6),
                 textcoords="offset points",
                 ha='center', va='bottom', fontsize=9, fontweight='bold')
plt.tight_layout()
throughput_png = os.path.join(out_dir, 'throughput_comparison.png')
plt.savefig(throughput_png)
plt.close()
print('Saved', throughput_png)

# Latency comparison (avg, p95, p99)
lat_avg_means = [r['latency_avg_mean_ms'] for r in agg_rows]
lat_p95_means = [r['latency_p95_mean_ms'] for r in agg_rows]
lat_p99_means = [r['latency_p99_mean_ms'] for r in agg_rows]

x = range(len(modes))
plt.figure(figsize=(8,5))
plt.plot(x, lat_avg_means, marker='o', label='avg')
plt.plot(x, lat_p95_means, marker='o', label='p95')
plt.plot(x, lat_p99_means, marker='o', label='p99')
plt.xticks(x, modes)
plt.xlabel('Mode')
plt.ylabel('Latency (ms)')
plt.title('Latency Percentiles by Mode')
plt.legend()
plt.grid(axis='y', linestyle=':', alpha=0.6)
# Annotate latency points with values
for xi, y in enumerate(lat_avg_means):
    plt.annotate(f"{y:.1f}ms", xy=(xi, y), xytext=(0, 8), textcoords='offset points', ha='center', fontsize=9, fontweight='bold')
for xi, y in enumerate(lat_p95_means):
    plt.annotate(f"{y:.1f}ms", xy=(xi, y), xytext=(0, 18), textcoords='offset points', ha='center', fontsize=9)
for xi, y in enumerate(lat_p99_means):
    plt.annotate(f"{y:.1f}ms", xy=(xi, y), xytext=(0, 28), textcoords='offset points', ha='center', fontsize=9)
plt.tight_layout()
latency_png = os.path.join(out_dir, 'latency_comparison.png')
plt.savefig(latency_png)
plt.close()
print('Saved', latency_png)

print('Done')
