"""Record actual host/source provenance and retain interrupted serial-prefix evidence."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    target = ROOT/'experiments/s6_1'
    hardware = json.loads((ROOT/'out/s6_1-hardware.json').read_text(encoding='utf-8-sig'))
    hardware['os'][0]['Caption'] = 'Microsoft Windows 11 Home'
    hardware['power_plan'] = 'Balanced'
    chronology = dict(protocol='03ae833', diagnosis_profile='f6a46b9addbc8ccc5f3f28cf8302068fa51406e0',
                      optimized_profile='4591160cca2c7b9504e859e2cc5e9545d7441da2',
                      final_contact_executable='d60c8ff1e9d8eaa331b708439d149721325d9679',
                      observer_export_and_core_verification='c8dd6d0329497a13b5d59e01fdfbf16a2f63edc4',
                      interval_execution='fbe8852fe7eac77709394310262f138216902ef0')
    timing = {}
    for name, prefix in [('baseline', 's6_1-baseline'), ('final', 's6_1-final-performance')]:
        timing[name] = {phase+'_utc': (ROOT/f'out/{prefix}-{phase}.txt').read_text(encoding='utf-8-sig').strip()
                        for phase in ('start', 'end')}
    interrupted = json.loads((ROOT/'out/s6_1-interrupted-prefixes.json').read_text(encoding='utf-8-sig'))
    prefix_dir = target/'execution_prefixes'
    prefix_dir.mkdir(exist_ok=True)
    facts = []
    prefix_counts = {}
    for suite, directory in [('matrix', 's6_1-matrix'), ('observer_integrated', 's6_1-observer-integrated'),
                             ('integrated', 's6_1-integrated')]:
        path = ROOT/'out'/directory/'summary.csv'
        text = path.read_text(encoding='utf-8')
        (prefix_dir/f'{suite}.csv').write_text(text, encoding='utf-8', newline='\n')
        with path.open(encoding='utf-8', newline='') as stream:
            summaries = list(csv.DictReader(stream))
        assert all(None not in r and None not in r.values() for r in summaries)
        prefix_counts[suite] = len(summaries)
        if suite != 'integrated':
            for r in summaries:
                fields = ('suite', 'seed', 'policy', 'workers', 'source_protein_ug', 'budget', 'minimum_ms', 'condition', 'mirror')
                filename = '-'.join(r[f] for f in fields)+'-facts.bin'
                data = (path.parent/filename).read_bytes()
                assert len(data) == 159*int(r['events'])
                facts.append(dict(suite=suite, filename=filename, facts=int(r['events']), sha256=hashlib.sha256(data).hexdigest()))
    with (prefix_dir/'canonical_facts.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, list(facts[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(facts)
    report = dict(scope='ENGINEERING_FIXTURE', hardware=hardware, source_chronology=chronology,
                  isolated_contact_timing=timing, interrupted_serial_attempt=interrupted,
                  retained_complete_prefix_summary_rows=prefix_counts,
                  prefix_policy='All completed serial-prefix cases retained and compared with interval reruns. Incomplete in-progress cases remain local, are not passed results, and are rerun in the complete frozen grid. Each final case contributes once.',
                  core_unchanged_after_c8dd6d0=True,
                  limitations='No CPU frequency, thermal or scheduler telemetry was sampled during the acceptance timing matrix. Host metadata collected afterward cannot identify the timing-variation cause. Ecology timings overlap independent executions and are not isolated latency benchmarks.')
    (target/'provenance.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(prefix_counts))


if __name__ == '__main__':
    main()
