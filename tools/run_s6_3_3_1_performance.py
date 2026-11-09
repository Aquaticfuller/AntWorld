"""Freeze both Release executables and run the admitted version-2 Windows batch."""
import argparse
import ctypes as C
import gzip
import hashlib
import json
import math
from pathlib import Path
import shutil
import statistics as st
import subprocess
import time

from extract_s6_2_hwinfo import extract, header
from run_s6_2_performance import ROOT, digest, host, write_rows
from run_s6_3_2_performance import quantile, sensor_tail
from run_s6_3_performance import schedule
from s6_3_3_1_processor_times import Sampler, selected_core
import s6_2_windows_telemetry as win

BINARIES = {'contacts': 'antworld_s6_2_benchmark.exe', 'births': 'antworld_s6_3_1_birth_benchmark.exe'}
MAPPING = ROOT/'experiments/s6_2/hwinfo_columns_v2.json'
CONFIRMATION = 'instrument_v2_confirmation/receipt.json'
PROTOCOL = ROOT/'docs/55_S6_3_3_1_Performance_Instrument_Protocol.md'
CORRECTION = ROOT/'docs/57_S6_3_3_1_Reserve_Birth_Benchmark_Correction.md'
SENSOR_FIELDS = ('package_temperature_c', 'package_power_w', 'p0_t0_effective_clock_mhz')


def save(path, data):
    path.write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8', newline='\n')


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def dependencies():
    return {name: digest(ROOT/'tools'/name) for name in (
        Path(__file__).name, 's6_3_3_1_processor_times.py', 's6_2_windows_telemetry.py',
        'diagnose_s6_3_2_counters.py', 'run_s6_3_2_performance.py',
        'run_s6_3_performance.py', 'run_s6_2_performance.py', 'extract_s6_2_hwinfo.py',
        'verify_s6_3_3_1_reserve_workload.py')}


def prepare(args):
    assert not (args.out/'freeze.json').exists()
    assert not git('status', '--porcelain', '--', 'cpp'), 'commit the measured core before freezing'
    revision = git('rev-parse', 'HEAD')
    confirmation_path = args.confirmation or args.out/CONFIRMATION
    confirmation = load(confirmation_path)
    sources = dependencies()
    assert confirmation['status'] == 'PASS' and confirmation['instrument_version'] == 2
    assert confirmation['probe_sha256'] == sources['s6_3_3_1_processor_times.py']
    compiler = subprocess.check_output([str(args.compiler), '--version'], text=True).splitlines()
    cache = (args.build/'CMakeCache.txt').read_text(encoding='utf-8')
    assert 'CMAKE_BUILD_TYPE:STRING=Release' in cache and 'ANTWORLD_SANITIZERS:BOOL=OFF' in cache
    kinds = (args.kind,) if args.kind else tuple(BINARIES)
    for kind in kinds:
        for number in (1, 2, 3):
            assert not (args.out/kind/f'session{number}').exists()
    records = {}
    for kind in kinds:
        name = BINARIES[kind]
        schedules = {}
        for number in (1, 2, 3):
            directory = args.out/kind/f'session{number}'
            directory.mkdir(parents=True)
            path = directory/'schedule.csv'
            write_rows(path, schedule(number, kind))
            schedules[directory.name] = digest(path)
        records[kind] = dict(name=name, sha256=digest(args.build/name), schedule_sha256=schedules)
    save(args.out/'freeze.json', dict(
        source_commit=revision, configuration='Release', compiler=compiler, created_utc_ns=time.time_ns(),
        instrument_version=2, confirmation=str(confirmation_path.relative_to(ROOT).as_posix()),
        confirmation_sha256=digest(confirmation_path), correction_sha256=digest(CORRECTION),
        protocol_sha256=digest(PROTOCOL), sensor_mapping_sha256=digest(MAPPING), script_sha256=sources,
        order=[f'{kind}/session{number}' for kind in kinds for number in (1, 2, 3)], executables=records))
    print(f'Frozen {len(kinds)*3} schedules and {len(kinds)} Release executable hashes from {revision}', flush=True)


def finite(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


def os_row(probe, logical):
    row = probe.sample()
    row['processor_busy_pct'] = row[f'cpu{logical}_nonidle_wall_pct']
    row['processor_busy_pct_status'] = 'VALID' if row['processor_busy_pct'] != '' else 'INVALID_NATIVE_INTERVAL'
    return row


def admission(probe, logical, directory, sensor, fields, number):
    before = host()
    probe.sample()
    started = time.time_ns()
    deadline = time.perf_counter()
    records = []
    for _ in range(60):
        deadline += 1
        time.sleep(max(0, deadline-time.perf_counter()))
        row = os_row(probe, logical)
        try:
            sensors = sensor_tail(sensor, fields)
            row['sensor_read_status'] = 'READ'
        except OSError as exc:
            sensors = dict(sensor_utc_ns='', sensor_age_s='', source_prefix_bytes='')
            row['sensor_read_status'] = f'OS_ERROR_{exc.errno}'
        row.update(sensors)
        for label in SENSOR_FIELDS:
            row.setdefault(label, '')
        records.append(row)
    # A lost sensor sample can add or omit mapped columns, never omit the row.
    keys = dict.fromkeys(key for row in records for key in row)
    for row in records:
        for key in keys:
            row.setdefault(key, '')
    checks = {}
    for field in ('system_busy_pct', 'processor_busy_pct'):
        values = [r[field] for r in records if finite(r[field])]
        checks[field+'_complete'] = len(values) == 60
        checks[field+'_p50'] = st.median(values) if values else None
        checks[field+'_p95'] = quantile(values, .95) if values else None
    checks['native_intervals_valid'] = all(r['nonidle_wall_all_valid'] and
                                           800000000 <= r['wall_delta_ns'] <= 1200000000 for r in records)
    checks['power_valid'] = all(r['ac'] == 1 and r['battery_saver'] == 0 for r in records)
    checks['sensors_valid'] = all(finite(r['sensor_age_s']) and -2 <= r['sensor_age_s'] <= 10
                                  and all(finite(r[field]) for field in SENSOR_FIELDS) for r in records)
    admitted = all(checks[k] for k in ('native_intervals_valid', 'power_valid', 'sensors_valid')) and all(
        checks[k+'_complete'] and checks[k+'_p50'] <= 10 and checks[k+'_p95'] <= 20
        for k in ('system_busy_pct', 'processor_busy_pct'))
    write_rows(directory/f'admission{number}.csv', records)
    receipt = dict(attempt=number, started_utc_ns=started, ended_utc_ns=time.time_ns(), admitted=admitted,
                   checks=checks, host_before=before, source_header_sha256=load(MAPPING)['source_header_sha256'])
    save(directory/f'admission{number}_receipt.json', receipt)
    print(json.dumps(dict(kind=directory.parent.name, session=directory.name,
                          attempt=number, admitted=admitted, **checks)), flush=True)
    return receipt


def telemetry_file(directory, records):
    path = directory/'telemetry.csv'
    if not records:
        return ''
    write_rows(path, records)
    compressed = path.with_suffix('.csv.gz')
    with path.open('rb') as source, compressed.open('xb') as out, gzip.GzipFile(
            fileobj=out, filename='', mode='wb', mtime=0) as stream:
        shutil.copyfileobj(source, stream)
    sha256 = digest(path)
    path.unlink()
    return sha256


def timed_run(directory, archive, binary, probe, logical, sensor, admitted):
    archive.mkdir(parents=True)
    before = archive/'hwinfo_before.raw'
    shutil.copyfile(sensor, before)
    rows, handle, code, error = [], None, None, ''
    probe.sample()
    started = time.time_ns()
    with (directory/'native.log').open('x', encoding='utf-8') as log:
        process = subprocess.Popen([str(binary), str(directory), str(directory/'schedule.csv'), str(1 << logical)],
                                   stdout=log, stderr=subprocess.STDOUT)
        try:
            handle = win.open_process(0x1000, False, process.pid)
            deadline = time.perf_counter()
            while process.poll() is None:
                begin = time.perf_counter_ns()
                row = os_row(probe, logical)
                times = [win.W.FILETIME() for _ in range(4)]
                valid = bool(handle and win.get_process_times(handle, *(C.byref(t) for t in times)))
                row.update(pid=process.pid, benchmark_cpu_ns=100*(win.filetime(times[2])+win.filetime(times[3])) if valid else '',
                           collector_ns=time.perf_counter_ns()-begin)
                rows.append(row)
                deadline += .1
                time.sleep(max(0, deadline-time.perf_counter()))
        except Exception as exc:
            error = repr(exc)
        finally:
            code = process.wait()
            ended = time.time_ns()
            if handle:
                win.close(handle)
    receipt = dict(pid=process.pid, exit_code=code, started_utc_ns=started, ended_utc_ns=ended,
                   rows=len(schedule(int(directory.name[-1]), directory.parent.name)), telemetry_rows=len(rows),
                   binary_sha256=digest(binary), admission_attempt=admitted['attempt'], collector_error=error,
                   telemetry_uncompressed_sha256=telemetry_file(directory, rows), hwinfo_before_sha256=digest(before))
    save(directory/'receipt.json', receipt)
    # Wait for the logger to flush the end bracket. Extraction runs after timing.
    time.sleep(5)
    after = archive/'hwinfo_after.raw'
    try:
        shutil.copyfile(sensor, after)
        save(archive/'receipt.json', receipt)
        extract(archive.parent, MAPPING)
        for name in ('hwinfo.csv', 'hwinfo_provenance.json'):
            shutil.copyfile(archive/name, directory/name)
        receipt['hwinfo_after_sha256'] = digest(after)
    except (OSError, ValueError, AssertionError, UnicodeError) as exc:
        receipt['sensor_error'] = repr(exc)
    receipt['host_after'] = host()
    save(directory/'receipt.json', receipt)
    print(f'{directory.parent.name}/{directory.name}: exit={code}; all measured rows retained', flush=True)
    return code == 0 and not error and not receipt.get('sensor_error')


def run(args):
    freeze = load(args.out/'freeze.json')
    assert freeze['script_sha256'] == dependencies() and freeze['protocol_sha256'] == digest(PROTOCOL)
    assert freeze['sensor_mapping_sha256'] == digest(MAPPING)
    confirmation_path = ROOT/freeze['confirmation']
    assert freeze['correction_sha256'] == digest(CORRECTION)
    assert freeze['confirmation_sha256'] == digest(confirmation_path)
    if 'births' in freeze['executables']:
        identity = load(args.out/'reserve_identity_receipt.json')
        assert identity['match'] and identity['rows'] == 3
        assert identity['executable_sha256'] == freeze['executables']['births']['sha256']
    assert not git('status', '--porcelain', '--', 'cpp')
    assert not git('diff', '--name-only', freeze['source_commit'], 'HEAD', '--', 'cpp')
    assert not (args.out/'batch_result.json').exists(), 'the frozen batch already ended'
    for kind, item in freeze['executables'].items():
        assert item['sha256'] == digest(args.build/item['name'])
        for session, value in item['schedule_sha256'].items():
            assert value == digest(args.out/kind/session/'schedule.csv')
    fields = header(args.hwinfo_csv)
    assert hashlib.sha256(json.dumps(fields, ensure_ascii=True).encode()).hexdigest() == load(MAPPING)['source_header_sha256']
    cores = win.topology()
    chosen = selected_core(cores)
    logical = min(chosen['logical'])
    observer = sum(c['mask'] for c in cores) & ~chosen['mask']
    confirmation = load(confirmation_path)
    assert cores == confirmation['topology'] and logical == confirmation['selected_logical']
    assert win.affinity(win.current_process(), observer), 'collector affinity failed'
    started = time.time_ns()
    with (args.out/'batch_start.json').open('x', encoding='utf-8') as stream:
        json.dump(dict(started_utc_ns=started, freeze_sha256=digest(args.out/'freeze.json')), stream, indent=2)
        stream.write('\n')
    outcome, finished = 'INTERRUPTED', []
    try:
        for key in freeze['order']:
            kind, session = key.split('/')
            directory = args.out/kind/session
            archive = args.archive/kind
            archive.mkdir(parents=True, exist_ok=True)
            config = dict(kind=kind, source_commit=freeze['source_commit'], before=host(), topology=cores,
                          binary_sha256=freeze['executables'][kind]['sha256'], selected_logical=logical,
                          affinity_mask=1 << logical, observer_affinity_mask=observer, target_interval_ms=100)
            if not (directory.parent/'configuration.json').exists():
                save(directory.parent/'configuration.json', config)
                save(archive/'configuration.json', config)
            assert not any(directory.glob('admission*.csv')) and not (directory/'native.log').exists()
            probe = Sampler(cores, (logical,))
            try:
                for attempt in (1, 2, 3):
                    receipt = admission(probe, logical, directory, args.hwinfo_csv, fields, attempt)
                    if receipt['admitted']:
                        break
                    if attempt < 3:
                        time.sleep(300)
                if not receipt['admitted']:
                    outcome = 'ADMISSION_EXHAUSTED'
                    return
                binary = args.build/freeze['executables'][kind]['name']
                if not timed_run(directory, archive/session, binary, probe, logical, args.hwinfo_csv, receipt):
                    outcome = 'STARTED_SESSION_INCOMPLETE'
                    return
                finished.append(key)
            finally:
                probe.close()
        outcome = 'COLLECTION_FINISHED'
    finally:
        save(args.out/'batch_result.json', dict(outcome=outcome, completed=finished, started_utc_ns=started,
                                               ended_utc_ns=time.time_ns()))
        print(outcome, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--compiler', type=Path)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--kind', choices=tuple(BINARIES))
    parser.add_argument('--confirmation', type=Path)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--hwinfo-csv', type=Path)
    args = parser.parse_args()
    for name in ('out', 'build', 'compiler', 'confirmation', 'archive', 'hwinfo_csv'):
        path = getattr(args, name)
        if path is not None:
            setattr(args, name, path.resolve())
    if args.prepare:
        if not args.compiler:
            parser.error('--compiler is required to freeze the build')
        prepare(args)
    else:
        if not args.archive or not args.hwinfo_csv:
            parser.error('--archive and --hwinfo-csv are required to collect samples')
        run(args)


if __name__ == '__main__':
    main()
