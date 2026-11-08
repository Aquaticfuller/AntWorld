#!/usr/bin/env python3
"""Summarize measured latency without interpreting host timings as ecological calibration."""
import csv
import io
import math
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/'experiments/s4/performance'
with (DATA/'samples.csv').open(encoding='utf-8',newline='') as stream:
    rows = list(csv.DictReader(stream))
assert len(rows) == 810
groups = defaultdict(list)
for row in rows:
    assert row['scope'] == 'ENGINEERING_FIXTURE'
    edits = int(row['lifetime_edits'])
    if row['case'] == 'local_repeated_patch':
        edits -= 2*int(row['iteration']) + (row['operation']=='fill_commit')
    groups[(row['case'],row['population'],edits,row['operation'])].append(row)
summary = []
for key, samples in sorted(groups.items()):
    assert len(samples) == 30
    times = sorted(float(row['elapsed_us']) for row in samples)
    summary.append(dict(case=key[0],population=key[1],remote_edits=key[2],operation=key[3],samples=30,
                        p50_us=statistics.median(times),p95_us=times[math.ceil(.95*len(times))-1],
                        p99_us=times[-1],maximum_us=times[-1],candidates=samples[0]['candidates'],
                        nodes=samples[0]['nodes'],checkpoint_bytes=samples[0]['checkpoint_bytes']))
stream = io.StringIO(newline='')
writer = csv.DictWriter(stream,fieldnames=list(summary[0]),lineterminator='\n')
writer.writeheader(); writer.writerows(summary)
(DATA/'summary.csv').write_text(stream.getvalue(),encoding='utf-8',newline='\n')
print(stream.getvalue())
