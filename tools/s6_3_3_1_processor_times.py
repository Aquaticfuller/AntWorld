"""Cross-check PDH with Windows per-logical-CPU cumulative kernel times."""
import argparse
import ctypes as C
import hashlib
import json
import platform
import statistics as st
import subprocess
import sys
import time
from pathlib import Path

import s6_2_windows_telemetry as win
from diagnose_s6_3_2_counters import Raw
from run_s6_2_performance import write_rows


class ProcessorTimes(C.Structure):
    _fields_ = [(name, C.c_int64) for name in ('idle', 'kernel', 'user', 'reserved1', 'reserved2')]
    _fields_.append(('reserved3', C.c_uint32))


def busy(ticks):
    idle, kernel, user = ticks
    if 0 <= idle <= kernel and user >= 0 and kernel + user > 0:
        return 100 * (kernel + user - idle) / (kernel + user)
    return ''


class Sampler:
    """Sample independent CPU accounting and retain PDH data without substitution."""
    def __init__(self, cores, logicals):
        logicals_all = sorted(i for core in cores for i in core['logical'])
        if C.sizeof(ProcessorTimes) != 48 or logicals_all != list(range(len(logicals_all))):
            raise RuntimeError('Unsupported Windows CPU topology or native record layout')
        self.array = (ProcessorTimes * len(logicals_all))()
        self.ntquery = win.bind(C.WinDLL('ntdll'), 'NtQuerySystemInformation',
                                [C.c_uint32, C.c_void_p, C.c_uint32, C.POINTER(C.c_uint32)], C.c_int32)
        self.raw = win.bind(C.WinDLL('pdh'), 'PdhGetRawCounterValue',
                            [win.W.HANDLE, C.POINTER(win.W.DWORD), C.POINTER(Raw)], win.W.LONG)
        self.timebase = win.bind(C.WinDLL('pdh'), 'PdhGetCounterTimeBase',
                                 [win.W.HANDLE, C.POINTER(C.c_longlong)], win.W.LONG)
        self.pdh = {i: win.Counters(i) for i in logicals}
        self.old_native = None
        self.old_system = None
        self.old_monotonic = None
        self.old_pdh = {}
        self.sample()

    def sample(self):
        begin = time.perf_counter_ns()
        length = C.c_uint32()
        status = self.ntquery(8, self.array, C.sizeof(self.array), C.byref(length)) & 0xffffffff
        native = ([(p.idle, p.kernel, p.user) for p in self.array]
                  if status == 0 and length.value == C.sizeof(self.array) else None)
        system = win.system_ticks()
        power = win.PowerStatus()
        if not win.get_power(C.byref(power)):
            raise C.WinError(C.get_last_error())
        delta = None if native is None or self.old_native is None else [
            tuple(a-b for a, b in zip(now, old)) for now, old in zip(native, self.old_native)]
        row = dict(utc_ns=time.time_ns(), monotonic_ns=begin, native_status=status, native_bytes=length.value,
                   native_all_valid=delta is not None and all(busy(t) != '' for t in delta),
                   system_busy_pct=busy(tuple(a-b for a, b in zip(system, self.old_system))) if self.old_system else '',
                   native_system_busy_pct=busy(tuple(map(sum, zip(*delta)))) if delta is not None else '',
                   system_idle_100ns=system[0], system_kernel_100ns=system[1], system_user_100ns=system[2],
                   ac=power.ac, battery_saver=power.saver, battery_percent=power.battery_percent)
        wall = (begin-self.old_monotonic)/100 if self.old_monotonic is not None else 0
        row['wall_delta_ns'] = begin-self.old_monotonic if self.old_monotonic is not None else ''
        valid_clock = delta is not None and wall > 0
        clock_busy = 0
        for index in range(len(self.array)):
            now = native[index] if native is not None else ('', '', '')
            inc = delta[index] if delta is not None else ('', '', '')
            for field, value, change in zip(('idle', 'kernel', 'user'), now, inc):
                row[f'cpu{index}_{field}_100ns'] = value
                row[f'cpu{index}_delta_{field}_100ns'] = change
            row[f'cpu{index}_busy_pct'] = busy(inc) if delta is not None else ''
            nonidle_kernel = inc[1]-inc[0] if delta is not None else ''
            used = nonidle_kernel+inc[2] if delta is not None else ''
            valid = delta is not None and wall > 0 and nonidle_kernel >= 0 and inc[2] >= 0 and used <= wall+312500
            row[f'cpu{index}_nonidle_kernel_delta_100ns'] = nonidle_kernel
            row[f'cpu{index}_nonidle_wall_pct'] = 100*used/wall if valid else ''
            valid_clock = valid_clock and valid
            if valid:
                clock_busy += used
        row['nonidle_wall_all_valid'] = valid_clock
        row['nonidle_wall_system_pct'] = 100*clock_busy/(wall*len(self.array)) if valid_clock else ''
        self.old_native, self.old_system, self.old_monotonic = native, system, begin
        for index, counter in self.pdh.items():
            values = counter.sample()
            item = counter.items.get('processor_busy_pct')
            raw, kind, rate = Raw(), win.W.DWORD(), C.c_longlong()
            raw_status = self.raw(item, C.byref(kind), C.byref(raw)) & 0xffffffff if item else counter.errors.get('processor_busy_pct', -1)
            rate_status = self.timebase(item, C.byref(rate)) & 0xffffffff if item else raw_status
            previous = self.old_pdh.get(index)
            valid_raw = raw_status == 0 and raw.status in (0, 1)
            values.update(raw_api_status=raw_status, raw_counter_status=raw.status, raw_type=kind.value,
                          raw_first=raw.first, raw_second=raw.second, raw_multi=raw.multi,
                          raw_timestamp_100ns=win.filetime(raw.timestamp), rate_status=rate_status, rate=rate.value,
                          raw_first_delta=raw.first-previous[0] if valid_raw and previous else '',
                          raw_second_delta=raw.second-previous[1] if valid_raw and previous else '')
            self.old_pdh[index] = (raw.first, raw.second) if valid_raw else None
            row.update({f'pdh{index}_{key}': value for key, value in values.items()})
        row['collector_ns'] = time.perf_counter_ns() - begin
        return row

    def close(self):
        for counter in self.pdh.values():
            counter.finish()


def selected_core(cores):
    return next(core for core in cores if core['efficiency_class'] == max(c['efficiency_class'] for c in cores))


def diagnose(rows, selected, reference, basis='nonidle_wall'):
    def median(values):
        return st.median(values) if values else None

    core_suffix = 'nonidle_wall_pct' if basis == 'nonidle_wall' else 'busy_pct'
    total_key = 'nonidle_wall_system_pct' if basis == 'nonidle_wall' else 'native_system_busy_pct'
    complete_key = 'nonidle_wall_all_valid' if basis == 'nonidle_wall' else 'native_all_valid'
    groups = []
    for label, own, other in [('selected_pulse', selected, reference), ('reference_pulse', reference, selected)]:
        inner = [r for r in rows if r['phase'] == label][2:10]
        groups.append(dict(phase=label, own_p50=median([r[f'cpu{own}_{core_suffix}'] for r in inner if r[f'cpu{own}_{core_suffix}'] != '']),
                           other_p50=median([r[f'cpu{other}_{core_suffix}'] for r in inner if r[f'cpu{other}_{core_suffix}'] != ''])))
    system_error = median([abs(r['system_busy_pct']-r[total_key]) for r in rows
                           if r['system_busy_pct'] != '' and r[total_key] != ''])
    error = {}
    invalid = {}
    for index in (selected, reference):
        native_key, pdh_key = f'cpu{index}_{core_suffix}', f'pdh{index}_processor_busy_pct'
        error[index] = median([abs(r[native_key]-r[pdh_key]) for r in rows if r['phase'] in ('background', 'recovery')
                               and r.get(pdh_key, '') != '' and r[native_key] != ''])
        missing = [r for r in rows if r.get(pdh_key, '') == '']
        invalid[index] = dict(samples=len(missing), statuses=sorted({r.get(pdh_key+'_status', '') for r in missing}, key=str),
                              idle_delta_exceeds_clock=sum(isinstance(r[f'pdh{index}_raw_first_delta'], int) and
                                r[f'pdh{index}_raw_first_delta'] > r[f'pdh{index}_raw_second_delta'] > 0 for r in missing))
    complete = len(rows) == 60 and all(r[complete_key] and r['system_busy_pct'] != '' and
                                       800000000 <= r['wall_delta_ns'] <= 1200000000 for r in rows)
    passed = (complete and system_error is not None and system_error <= 2 and
              all(g['own_p50'] is not None and g['own_p50'] >= 80 and g['other_p50'] is not None and g['other_p50'] < 35 for g in groups) and
              all(e is not None and e <= 10 for e in error.values()))
    return dict(status='PASS' if passed else 'INCONCLUSIVE', basis=basis, native_complete=complete, pulses=groups,
                native_vs_system_median_abs_pp=system_error, pdh_vs_native_median_abs_pp=error, invalid_pdh=invalid)


def main():
    if len(sys.argv) == 4 and sys.argv[1] == '--pulse':
        if not win.affinity(win.current_process(), 1 << int(sys.argv[2])):
            raise C.WinError(C.get_last_error())
        end = int(sys.argv[3])
        while time.perf_counter_ns() < end:
            pass
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    cores = win.topology()
    chosen = selected_core(cores)
    other = next(c for c in cores if c['mask'] != chosen['mask'])
    selected, reference = min(chosen['logical']), min(other['logical'])
    mask = sum(c['mask'] for c in cores) & ~(chosen['mask'] | other['mask'])
    if not win.affinity(win.current_process(), mask):
        raise C.WinError(C.get_last_error())
    probe = Sampler(cores, (selected, reference))
    rows = []
    deadline = time.perf_counter_ns()
    pulse = None
    try:
        for label, seconds, logical in [('background', 20, None), ('selected_pulse', 12, selected),
                                        ('reference_pulse', 12, reference), ('recovery', 16, None)]:
            if logical is not None:
                pulse = subprocess.Popen([sys.executable, __file__, '--pulse', str(logical), str(deadline+seconds*10**9)])
            for _ in range(seconds):
                deadline += 10**9
                time.sleep(max(0, (deadline-time.perf_counter_ns())/10**9))
                rows.append(dict(interval=len(rows)+1, phase=label, **probe.sample()))
            if pulse is not None:
                if pulse.wait(timeout=5) != 0:
                    raise RuntimeError('Pinned pulse failed')
                pulse = None
    finally:
        if pulse is not None and pulse.poll() is None:
            pulse.terminate()
            pulse.wait(timeout=5)
        probe.close()
        if rows:
            write_rows(args.out/'samples.csv', rows)
    result = diagnose(rows, selected, reference)
    result.update(instrument_version=2, selected_logical=selected, reference_logical=reference, observer_affinity_mask=mask, topology=cores,
                  windows=platform.version(), probe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (args.out/'receipt.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
