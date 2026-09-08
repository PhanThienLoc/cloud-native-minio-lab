import json
import glob
import os
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Discover run JSON files
json_paths = sorted(glob.glob(os.path.join(os.path.dirname(__file__), '*_run*.json')))
if not json_paths:
    print('No run JSON files found in scripts/');
    raise SystemExit(1)

rows = []
for p in json_paths:
    with open(p, 'r', encoding='utf-8') as f:
        data = json.load(f)
    name = os.path.basename(p)
    mode = data.get('context', {}).get('mode', 'unknown')
    perf = data.get('performance', {})
    latency = data.get('latency_ms', {})
    row = {
        'file': name,
        'mode': mode,
        'throughput_mib_s': perf.get('average_throughput_mib_s', 0.0),
        'total_duration_sec': perf.get('total_duration_sec', 0.0),
        'total_uploaded_mib': perf.get('total_uploaded_mib', 0.0),
        'success_rate_percent': perf.get('success_rate_percent', 0.0),
        'latency_avg_ms': latency.get('average', 0.0),
        'latency_p95_ms': latency.get('p95', 0.0),
        'latency_p99_ms': latency.get('p99', 0.0),
    }
    rows.append(row)

# Ensure output dir
out_dir = os.path.join(os.path.dirname(__file__), '..', 'docs', 'reports')
os.makedirs(out_dir, exist_ok=True)
csv_path = os.path.join(out_dir, 'run_summary.csv')
with open(csv_path, 'w', newline='', encoding='utf-8') as cf:
    writer = csv.DictWriter(cf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
print('Wrote', csv_path)

# Prepare charts
# Throughput chart
labels = [r['file'].replace('.json','') for r in rows]
throughputs = [r['throughput_mib_s'] for r in rows]
modes = [r['mode'] for r in rows]

plt.figure(figsize=(10,6))
colors = ['#1f77b4' if m=='standalone' else '#ff7f0e' for m in modes]
plt.bar(labels, throughputs, color=colors)
plt.xticks(rotation=45, ha='right')
plt.xlabel('Run')
plt.ylabel('Throughput (MiB/s)')
plt.title('Throughput per Run')
plt.tight_layout()
throughput_png = os.path.join(out_dir, 'throughput.png')
plt.savefig(throughput_png)
plt.close()
print('Saved', throughput_png)

# Latency chart (avg, p95, p99)
lat_avg = [r['latency_avg_ms'] for r in rows]
lat_p95 = [r['latency_p95_ms'] for r in rows]
lat_p99 = [r['latency_p99_ms'] for r in rows]

x = range(len(labels))
plt.figure(figsize=(10,6))
plt.plot(x, lat_avg, marker='o', label='avg')
plt.plot(x, lat_p95, marker='o', label='p95')
plt.plot(x, lat_p99, marker='o', label='p99')
plt.xticks(x, labels, rotation=45, ha='right')
plt.xlabel('Run')
plt.ylabel('Latency (ms)')
plt.title('Latency percentiles per Run')
plt.legend()
plt.grid(axis='y', linestyle=':', alpha=0.6)
plt.tight_layout()
latency_png = os.path.join(out_dir, 'latency.png')
plt.savefig(latency_png)
plt.close()
print('Saved', latency_png)

print('Done.')
