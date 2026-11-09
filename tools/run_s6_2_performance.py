"""Run the frozen balanced Windows timing protocol with retained hardware evidence."""
import argparse
import csv
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

import s6_2_windows_telemetry as win

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ps_json(script):
    value = subprocess.check_output(['powershell', '-NoProfile', '-Command', script], encoding='utf-8-sig')
    return json.loads(value)


def host():
    return ps_json("$ErrorActionPreference='Stop'; [ordered]@{cpu=@(Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed);os=@(Get-CimInstance Win32_OperatingSystem | Select-Object Version,BuildNumber,TotalVisibleMemorySize);power_plan=(Get-ItemProperty 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Power\\User\\PowerSchemes').ActivePowerScheme;timezone_minutes=[TimeZoneInfo]::Local.GetUtcOffset([DateTime]::Now).TotalMinutes;processes=@(Get-Process | Select-Object Id,ProcessName,CPU,WorkingSet)} | ConvertTo-Json -Depth 5")


def schedule(session, mode):
    rows = []
    def block(number, layout, warmup=False, policies=False):
        abba = (0, 1, 1, 0) if number % 2 else (1, 0, 0, 1)
        for slot, choice in enumerate(abba):
            rows.append(dict(sample=len(rows), session=session, block=number, slot=slot,
                             warmup=int(warmup), population=2048 if policies else (512, 2048)[choice],
                             layout=layout, policy=('exhaustive', 'bounded')[choice] if policies else 'bounded'))
    if mode == 'smoke':
        return [dict(sample=i, session=0, block=i, slot=0, warmup=0, population=128,
                     layout=layout, policy=policy) for i, (layout, policy) in
                enumerate((('dense', 'bounded'), ('dispersed', 'bounded'), ('dense', 'exhaustive'), ('dispersed', 'exhaustive')))]
    if mode == 'primary':
        for layout in ('dense', 'dispersed'):
            block(-1, layout, True)
    for number in range(1, (12 if mode == 'primary' else 4)+1):
        layouts = ('dense',) if mode == 'exhaustive' else ('dense', 'dispersed')
        if (number + session) % 2:
            layouts = tuple(reversed(layouts))
        for layout in layouts:
            block(number, layout, policies=mode == 'exhaustive')
    return rows


def write_rows(path, rows):
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--mode', choices=('primary', 'attribution', 'overhead', 'exhaustive', 'smoke'), required=True)
    parser.add_argument('--hwinfo-csv', type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    binary = args.binary.resolve()
    cores = win.topology()
    fastest = max(c['efficiency_class'] for c in cores)
    chosen = next(c for c in cores if c['efficiency_class'] == fastest)
    logical = min(chosen['logical'])
    mask = 1 << logical
    observer_mask = sum(c['mask'] for c in cores) & ~chosen['mask']
    assert win.affinity(win.current_process(), observer_mask), 'observer affinity failed'
    meta = dict(protocol_commit='3f6d1a9', source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                binary_sha256=digest(binary), binary_name=binary.name, mode=args.mode,
                topology=cores, selected_logical=logical, affinity_mask=mask, observer_affinity_mask=observer_mask,
                target_interval_ms=100, before=host(), started_utc_ns=time.time_ns(),
                sensor_source='user-provided HWiNFO CSV; native provider interval retained',
                overhead_scope='Only this Python/PDH collector is disabled in overhead controls. HWiNFO remains running unchanged.')
    (args.out/'configuration.json').write_text(json.dumps(meta, indent=2)+'\n', encoding='utf-8')
    for session in range(1, (3 if args.mode == 'primary' else 1)+1):
        directory = args.out/f'session{session}'
        directory.mkdir()
        plan = schedule(session, args.mode)
        write_rows(directory/'schedule.csv', plan)
        if args.hwinfo_csv:
            data = args.hwinfo_csv.read_bytes()
            (directory/'hwinfo_before.raw').write_bytes(data)
        counters = win.Counters(logical) if args.mode != 'overhead' else None
        records, last = [], win.system_ticks()
        started = time.time_ns()
        with (directory/'native.log').open('w', encoding='utf-8') as log:
            process = subprocess.Popen([str(binary), str(directory), str(directory/'schedule.csv'), str(mask)], stdout=log, stderr=subprocess.STDOUT)
            handle = win.open_process(0x1000, False, process.pid)
            deadline = time.perf_counter()
            while process.poll() is None:
                if counters:
                    begin = time.perf_counter_ns()
                    now = win.system_ticks()
                    idle, kernel, user = [a-b for a,b in zip(now, last)]
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
        if counters:
            counters.finish()
            assert records
            write_rows(directory/'telemetry.csv', records)
        ended = time.time_ns()
        if args.hwinfo_csv:
            time.sleep(3)  # Allow the independent sensor logger to flush a bracketing sample.
            data = args.hwinfo_csv.read_bytes()
            (directory/'hwinfo_after.raw').write_bytes(data)
        receipt = dict(pid=process.pid, exit_code=code, started_utc_ns=started, ended_utc_ns=ended,
                       rows=len(plan), telemetry_rows=len(records), binary_sha256=digest(binary))
        assert receipt['binary_sha256'] == meta['binary_sha256'], 'binary changed during experiment'
        (directory/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
        print(f'{args.mode} session {session}: exit={code}, scheduled={len(plan)}, telemetry={len(records)}', flush=True)
        assert code == 0, 'native failure retained; do not continue acceptance'
        time.sleep(5)
    meta['after'], meta['ended_utc_ns'] = host(), time.time_ns()
    (args.out/'configuration.json').write_text(json.dumps(meta, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
