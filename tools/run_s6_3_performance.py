"""Frozen S6.3 ABBA/BAAB measurement using the unchanged S6.2 read-only telemetry provider."""
import argparse
import ctypes as C
import json
import subprocess
import time
from pathlib import Path
from run_s6_2_performance import ROOT, digest, host, write_rows
import s6_2_windows_telemetry as win


def schedule(session, kind):
    rows = []
    layouts = ('dense', 'dispersed') if kind == 'contacts' else ('dense',)
    def block(number, layout, warmup=False):
        order = (512, 2048, 2048, 512) if number % 2 else (2048, 512, 512, 2048)
        for slot, population in enumerate(order):
            rows.append(dict(sample=len(rows), session=session, block=number, slot=slot,
                             warmup=int(warmup), population=population, layout=layout, policy='bounded'))
    for layout in layouts:
        block(-1, layout, True)
    for number in range(1, 13):
        for layout in layouts if (number + session) % 2 else tuple(reversed(layouts)):
            block(number, layout)
            if number % 3 == 0:
                rows.append(dict(sample=len(rows), session=session, block=number, slot=4,
                                 warmup=0, population=128, layout=layout, policy='bounded'))
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--kind', choices=('contacts', 'births'), required=True)
    p.add_argument('--hwinfo-csv', type=Path)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    binary = args.binary.resolve()
    cores = win.topology()
    chosen = next(c for c in cores if c['efficiency_class'] == max(x['efficiency_class'] for x in cores))
    logical = min(chosen['logical'])
    mask, observer_mask = 1 << logical, sum(c['mask'] for c in cores) & ~chosen['mask']
    assert win.affinity(win.current_process(), observer_mask)
    meta = dict(protocol_commit='5607139', correction_protocol_commit='0c26f42',
                source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                binary_sha256=digest(binary), binary_name=binary.name, kind=args.kind,
                topology=cores, selected_logical=logical, affinity_mask=mask, observer_affinity_mask=observer_mask,
                before=host(), started_utc_ns=time.time_ns(), target_interval_ms=100,
                sensor_source='User HWiNFO CSV, native sampling interval and any gaps retained',
                note='Birth benchmark uses many queens only to stress endogenous registration; not a colony model.')
    (args.out/'configuration.json').write_text(json.dumps(meta, indent=2)+'\n', encoding='utf-8')
    for session in range(1, 4):
        directory = args.out/f'session{session}'
        directory.mkdir()
        plan = schedule(session, args.kind)
        write_rows(directory/'schedule.csv', plan)
        if args.hwinfo_csv:
            (directory/'hwinfo_before.raw').write_bytes(args.hwinfo_csv.read_bytes())
        counters, last = win.Counters(logical), win.system_ticks()
        records, started = [], time.time_ns()
        with (directory/'native.log').open('w', encoding='utf-8') as log:
            process = subprocess.Popen([str(binary), str(directory), str(directory/'schedule.csv'), str(mask)], stdout=log, stderr=subprocess.STDOUT)
            handle = win.open_process(0x1000, False, process.pid)
            deadline = time.perf_counter()
            while process.poll() is None:
                begin, now = time.perf_counter_ns(), win.system_ticks()
                idle, kernel, user = [a-b for a, b in zip(now, last)]
                last = now
                power = win.PowerStatus()
                assert win.get_power(C.byref(power))
                times = [win.W.FILETIME() for _ in range(4)]
                valid_cpu = bool(handle and win.get_process_times(handle, *(C.byref(t) for t in times)))
                row = dict(utc_ns=time.time_ns(), monotonic_ns=begin, pid=process.pid,
                           system_busy_pct=100*(1-idle/(kernel+user)) if kernel+user else '',
                           benchmark_cpu_ns=100*(win.filetime(times[2])+win.filetime(times[3])) if valid_cpu else '',
                           ac=power.ac, battery_saver=power.saver, battery_percent=power.battery_percent,
                           **counters.sample())
                row['collector_ns'] = time.perf_counter_ns()-begin
                records.append(row)
                deadline += .1
                time.sleep(max(0, deadline-time.perf_counter()))
            code = process.wait()
            if handle:
                win.close(handle)
        counters.finish()
        write_rows(directory/'telemetry.csv', records)
        ended = time.time_ns()
        if args.hwinfo_csv:
            time.sleep(3)
            (directory/'hwinfo_after.raw').write_bytes(args.hwinfo_csv.read_bytes())
        receipt = dict(pid=process.pid, exit_code=code, started_utc_ns=started, ended_utc_ns=ended,
                       rows=len(plan), telemetry_rows=len(records), binary_sha256=digest(binary))
        assert receipt['binary_sha256'] == meta['binary_sha256']
        (directory/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
        print(f'{args.kind} session {session}: exit={code}, rows={len(plan)}', flush=True)
        assert code == 0, 'Failure retained; stop measurement'
        time.sleep(5)
    meta['after'], meta['ended_utc_ns'] = host(), time.time_ns()
    (args.out/'configuration.json').write_text(json.dumps(meta, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
