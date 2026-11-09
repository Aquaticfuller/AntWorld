"""Admit unchanged ABBA workloads only after a recorded low-load qualification.

Run one session at a time. A failed admission never starts the benchmark. Retry
after at least five minutes, at most three times; retain every attempt.
"""
import argparse
import csv
import ctypes as C
from datetime import datetime
import hashlib
import io
import json
import statistics as st
import subprocess
import time
from pathlib import Path
from run_s6_3_performance import schedule
from run_s6_2_performance import ROOT, digest, host, write_rows
from extract_s6_2_hwinfo import MAPPING, header
import s6_2_windows_telemetry as win

HASHES = {'contacts': '7e79d7aab6d27128e9c5bd58c834b320ba830997f3bef0a733ee2b9ed4edd582',
          'births': 'c3cdbb06bfdf998568843917c5e2fbc42db2235a3911db001de3d86ba1d5894a'}


def quantile(x, p):
    x = sorted(x); i = (len(x)-1)*p; lo = int(i)
    return x[lo] + (x[min(lo+1, len(x)-1)]-x[lo])*(i-lo)


def sensor_tail(path, fields):
    # Read only a short suffix; the independent logger retains the complete file.
    with path.open('rb') as stream:
        stream.seek(0, 2); size = stream.tell(); stream.seek(max(0, size-65536))
        tail = stream.read().decode('utf-8', errors='replace').splitlines()
    candidates = list(csv.reader(tail[1:-1]))
    for row in reversed(candidates):
        if len(row) != len(fields) or row[0] == 'Date':
            continue
        try:
            at = datetime.strptime(row[0]+' '+row[1], '%d.%m.%Y %H:%M:%S.%f').timestamp()
            result = dict(sensor_utc_ns=int(at*1e9), sensor_age_s=time.time()-at, source_prefix_bytes=size)
            for index, label in MAPPING.items():
                value = row[index]
                result[label] = 1 if value in ('Yes', chr(0x662f)) else 0 if value in ('No', chr(0x5426)) else float(value) if value else ''
            return result
        except ValueError:
            continue
    return dict(sensor_utc_ns='', sensor_age_s='', source_prefix_bytes=size)


def os_sample(counters, last):
    now = win.system_ticks(); idle, kernel, user = [a-b for a,b in zip(now,last)]
    power = win.PowerStatus(); assert win.get_power(C.byref(power))
    return dict(utc_ns=time.time_ns(), monotonic_ns=time.perf_counter_ns(),
                system_busy_pct=100*(1-idle/(kernel+user)) if kernel+user else '',
                ac=power.ac, battery_saver=power.saver, battery_percent=power.battery_percent,
                **counters.sample()), now


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--kind', choices=HASHES, required=True)
    p.add_argument('--session', type=int, choices=(1,2,3), required=True)
    p.add_argument('--hwinfo-csv', type=Path, required=True)
    args = p.parse_args(); binary = args.binary.resolve()
    assert digest(binary) == HASHES[args.kind], 'acceptance binary changed'
    args.out.mkdir(parents=True, exist_ok=True)
    cores = win.topology()
    chosen = next(c for c in cores if c['efficiency_class'] == max(x['efficiency_class'] for x in cores))
    logical = min(chosen['logical']); mask = 1 << logical
    observer_mask = sum(c['mask'] for c in cores) & ~chosen['mask']
    assert win.affinity(win.current_process(), observer_mask)
    config_path = args.out/'configuration.json'
    if not config_path.exists():
        meta = dict(protocol_commit='55e6871646f863d027f150911fa6c6f8a3db60c5',
                    source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                    binary_sha256=digest(binary), binary_name=binary.name, kind=args.kind,
                    topology=cores, selected_logical=logical, affinity_mask=mask, observer_affinity_mask=observer_mask,
                    before=host(), started_utc_ns=time.time_ns(), target_interval_ms=100,
                    runner_sha256=digest(Path(__file__)), schedule_policy='Unchanged S6.3 ABBA/BAAB; all three plans frozen before admission')
        config_path.write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
        for number in range(1,4):
            directory = args.out/f'session{number}'; directory.mkdir(exist_ok=True)
            write_rows(directory/'schedule.csv', schedule(number,args.kind))
    meta = json.loads(config_path.read_text(encoding='utf-8'))
    assert meta['binary_sha256'] == digest(binary) and meta['selected_logical'] == logical
    directory = args.out/f'session{args.session}'
    assert not (directory/'receipt.json').exists() and not (directory/'native.log').exists(), 'never repeat started sessions'
    attempts = sorted(directory.glob('admission*_receipt.json'))
    assert len(attempts) < 3, 'three failed admissions: request a quiet interval'
    if attempts:
        previous = json.loads(attempts[-1].read_text(encoding='utf-8'))
        assert time.time_ns()-previous['ended_utc_ns'] >= 300*10**9, 'five-minute retry interval has not elapsed'
    fields = header(args.hwinfo_csv)
    # Check against the reviewed localized layout, not merely its column count.
    mapping_path = ROOT/'experiments/s6_2/hwinfo_columns_v2.json'
    mapping = json.loads(mapping_path.read_text(encoding='utf-8'))
    assert hashlib.sha256(json.dumps(fields,ensure_ascii=True).encode()).hexdigest() == mapping['source_header_sha256']
    before = host(); records=[]; counters=win.Counters(logical); last=win.system_ticks()
    started = time.time_ns(); deadline=time.perf_counter()
    for _ in range(60):
        deadline += 1; time.sleep(max(0,deadline-time.perf_counter()))
        row,last=os_sample(counters,last); row.update(sensor_tail(args.hwinfo_csv,fields)); records.append(row)
    counters.finish()
    checks = {}
    for field in ('system_busy_pct','processor_busy_pct'):
        values=[r[field] for r in records if isinstance(r[field],(int,float))]
        checks[field+'_complete'] = len(values)==60
        checks[field+'_p50'] = st.median(values) if values else None
        checks[field+'_p95'] = quantile(values,.95) if values else None
    checks['power_valid'] = all(r['ac']==1 and r['battery_saver']==0 for r in records)
    checks['sensors_valid'] = all(isinstance(r['sensor_age_s'],(int,float)) and -2<=r['sensor_age_s']<=10 and
                                isinstance(r.get('package_temperature_c'),(int,float)) and
                                isinstance(r.get('package_power_w'),(int,float)) for r in records)
    admitted = checks['power_valid'] and checks['sensors_valid'] and all(checks[f+'_complete'] and checks[f+'_p50']<=10 and checks[f+'_p95']<=20 for f in ('system_busy_pct','processor_busy_pct'))
    attempt=len(attempts)+1
    write_rows(directory/f'admission{attempt}.csv',records)
    receipt=dict(attempt=attempt,started_utc_ns=started,ended_utc_ns=time.time_ns(),admitted=admitted,
                 checks=checks,host_before=before,source_header_sha256=mapping['source_header_sha256'])
    (directory/f'admission{attempt}_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(kind=args.kind,session=args.session,admission=receipt['checks'],admitted=admitted)),flush=True)
    if not admitted:
        return
    # Freeze no new biological data here: only run the verified historical binary.
    (directory/'hwinfo_before.raw').write_bytes(args.hwinfo_csv.read_bytes())
    counters=win.Counters(logical); last=win.system_ticks(); records=[]; started=time.time_ns()
    with (directory/'native.log').open('w',encoding='utf-8') as log:
        process=subprocess.Popen([str(binary),str(directory),str(directory/'schedule.csv'),str(mask)],stdout=log,stderr=subprocess.STDOUT)
        handle=win.open_process(0x1000,False,process.pid); deadline=time.perf_counter()
        while process.poll() is None:
            begin=time.perf_counter_ns(); row,last=os_sample(counters,last)
            times=[win.W.FILETIME() for _ in range(4)]
            valid=bool(handle and win.get_process_times(handle,*(C.byref(t) for t in times)))
            row.update(pid=process.pid,benchmark_cpu_ns=100*(win.filetime(times[2])+win.filetime(times[3])) if valid else '',collector_ns=time.perf_counter_ns()-begin)
            records.append(row); deadline+=.1; time.sleep(max(0,deadline-time.perf_counter()))
        code=process.wait()
        if handle:win.close(handle)
    counters.finish(); ended=time.time_ns(); write_rows(directory/'telemetry.csv',records)
    time.sleep(3); (directory/'hwinfo_after.raw').write_bytes(args.hwinfo_csv.read_bytes())
    receipt=dict(pid=process.pid,exit_code=code,started_utc_ns=started,ended_utc_ns=ended,
                 rows=len(schedule(args.session,args.kind)),telemetry_rows=len(records),binary_sha256=digest(binary),admission_attempt=attempt)
    assert receipt['binary_sha256']==meta['binary_sha256']
    (directory/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    meta['after']=host(); meta['ended_utc_ns']=time.time_ns()
    config_path.write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    print(f'{args.kind} session {args.session}: exit={code}; every sample retained',flush=True)
    assert code==0,'failure retained; stop measurement'


if __name__=='__main__':main()
