"""Read one fixed raw-counter diagnostic; never admit or time a benchmark."""
import argparse
import ctypes as C
import hashlib
import json
import time
from pathlib import Path
from run_s6_2_performance import host, write_rows
from run_s6_3_2_performance import sensor_tail, os_sample
from extract_s6_2_hwinfo import header
import s6_2_windows_telemetry as win


class Raw(C.Structure):
    _fields_ = [('status', win.W.DWORD), ('timestamp', win.W.FILETIME),
                ('first', C.c_longlong), ('second', C.c_longlong),
                ('multi', win.W.DWORD)]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--hwinfo-csv', type=Path, required=True)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    cores = win.topology()
    chosen = next(c for c in cores if c['efficiency_class'] == max(x['efficiency_class'] for x in cores))
    logical = min(chosen['logical'])
    assert win.affinity(win.current_process(), sum(c['mask'] for c in cores) & ~chosen['mask'])
    counters = win.Counters(logical)
    pdh = C.WinDLL('pdh')
    raw = win.bind(pdh, 'PdhGetRawCounterValue', [win.W.HANDLE, C.POINTER(win.W.DWORD), C.POINTER(Raw)], win.W.LONG)
    base = win.bind(pdh, 'PdhGetCounterTimeBase', [win.W.HANDLE, C.POINTER(C.c_longlong)], win.W.LONG)
    legacy = win.W.HANDLE()
    status = counters.add(counters.query, f'\\Processor({logical})\\% Processor Time', 0, C.byref(legacy))
    assert status == 0, f'legacy counter unavailable: {status & 0xffffffff}'
    counters.items['legacy_busy_pct'] = legacy
    counters.collect(counters.query)
    fields = header(args.hwinfo_csv)
    metadata = dict(host=host(), selected_logical=logical, topology=cores,
                    diagnostic_only=True, source_header_sha256=hashlib.sha256(json.dumps(fields, ensure_ascii=True).encode()).hexdigest())
    previous = {}
    def values():
        result = {}
        for name in ('processor_busy_pct', 'legacy_busy_pct'):
            handle = counters.items[name]
            value, kind, rate = Raw(), win.W.DWORD(), C.c_longlong()
            error = raw(handle, C.byref(kind), C.byref(value)) & 0xffffffff
            rate_error = base(handle, C.byref(rate)) & 0xffffffff
            item = dict(raw_api_status=error, raw_status=value.status, counter_type=kind.value,
                        timestamp=win.filetime(value.timestamp), first=value.first, second=value.second,
                        multi=value.multi, timebase_status=rate_error, timebase=rate.value)
            old = previous.get(name)
            item.update(first_delta=value.first-old[0] if old else '', second_delta=value.second-old[1] if old else '')
            previous[name] = (value.first, value.second)
            result.update({name+'_'+key: value for key, value in item.items()})
        return result
    metadata['initial_raw'] = values()
    (args.out/'configuration.json').write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8')
    records, last, deadline = [], win.system_ticks(), time.perf_counter()
    for _ in range(60):
        deadline += 1
        time.sleep(max(0, deadline-time.perf_counter()))
        row, last = os_sample(counters, last)
        row.update(values())
        row.update(sensor_tail(args.hwinfo_csv, fields))
        records.append(row)
    counters.finish()
    write_rows(args.out/'raw_counters.csv', records)
    print(json.dumps(dict(samples=len(records), primary_invalid=sum(r['processor_busy_pct']=='' for r in records),
                          legacy_invalid=sum(r['legacy_busy_pct']=='' for r in records),
                          primary_nonpositive_second_deltas=sum(r['processor_busy_pct_second_delta']<=0 for r in records))))


if __name__ == '__main__':
    main()
