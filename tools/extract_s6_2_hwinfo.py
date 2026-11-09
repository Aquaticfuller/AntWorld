"""Translate selected CPU columns without altering any HWiNFO sample value.

Localized original CSV snapshots remain local/untracked. Column hashes and
source-byte hashes preserve their provenance; exported labels are English.
"""
import argparse
import csv
from datetime import datetime, timezone, timedelta
import hashlib
import io
import json
from pathlib import Path

MAPPING = {24: 'core_clock_mean_mhz', 25: 'p0_clock_mhz', 36: 'core_effective_clock_mean_mhz',
           37: 'p0_t0_effective_clock_mhz', 38: 'p0_t1_effective_clock_mhz',
           55: 'core_usage_mean_pct', 56: 'p0_t0_usage_pct', 57: 'p0_t1_usage_pct',
           105: 'core_temperature_mean_c', 106: 'p0_temperature_c', 127: 'package_dts_temperature_c',
           128: 'core_temperature_max_c', 129: 'any_core_thermal_throttling',
           130: 'p0_thermal_throttling', 140: 'any_core_critical_temperature',
           151: 'any_core_power_limit', 152: 'p0_power_limit', 162: 'package_thermal_throttling',
           163: 'package_critical_temperature', 164: 'package_power_limit',
           165: 'package_temperature_c', 166: 'ia_temperature_c', 177: 'package_power_w',
           178: 'ia_power_w', 180: 'system_power_w', 184: 'pl1_static_w',
           185: 'pl1_dynamic_w', 186: 'pl2_static_w', 187: 'pl2_dynamic_w'}


def header(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return next(csv.reader(stream))


def capture_map(source, target):
    fields = header(source)
    assert len(fields) == 472, 'review the sensor mapping for a different HWiNFO layout'
    target.write_text(json.dumps(dict(source_header_sha256=hashlib.sha256(json.dumps(fields, ensure_ascii=True).encode()).hexdigest(),
                                      source_columns=len(fields), columns=[dict(index=i, label=label,
                                      original_label_sha256=hashlib.sha256(fields[i].encode()).hexdigest()) for i, label in MAPPING.items()],
                                      mapping='Human-checked CPU labels; retain original local source. No missing/invalid value is filled.'), indent=2)+'\n', encoding='utf-8')


def extract(root, mapping):
    mapping = json.loads(mapping.read_text(encoding='utf-8'))
    timezone_minutes = json.loads((root/'configuration.json').read_text(encoding='utf-8'))['before']['timezone_minutes']
    zone = timezone(timedelta(minutes=timezone_minutes))
    for session in sorted(root.glob('session*')):
        receipt = json.loads((session/'receipt.json').read_text(encoding='utf-8'))
        source = session/'hwinfo_after.raw'
        data = source.read_bytes()
        stream = csv.reader(io.StringIO(data.decode('utf-8-sig')))
        fields = next(stream)
        assert hashlib.sha256(json.dumps(fields, ensure_ascii=True).encode()).hexdigest() == mapping['source_header_sha256']
        rows, incomplete = [], 0
        for number, row in enumerate(stream, 2):
            if not row or row[0] == 'Date':
                continue
            if len(row) != len(fields):
                incomplete += 1
                continue
            at = datetime.strptime(row[0]+' '+row[1], '%d.%m.%Y %H:%M:%S.%f').replace(tzinfo=zone)
            ns = int(at.timestamp()*1000000000)
            if not receipt['started_utc_ns']-3000000000 <= ns <= receipt['ended_utc_ns']+3000000000:
                continue
            result = dict(utc_ns=ns, source_line=number)
            for item in mapping['columns']:
                value = row[item['index']]
                if value in ('Yes', chr(0x662f)):
                    result[item['label']] = 1
                elif value in ('No', chr(0x5426)):
                    result[item['label']] = 0
                else:
                    result[item['label']] = float(value) if value else ''
            rows.append(result)
        assert rows, 'no HWiNFO observations overlap this session'
        with (session/'hwinfo.csv').open('w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, list(rows[0]), lineterminator='\n')
            writer.writeheader(); writer.writerows(rows)
        report = dict(source_prefix_bytes=len(data), source_prefix_sha256=hashlib.sha256(data).hexdigest(),
                      retained_rows=len(rows), incomplete_rows=incomplete, first_utc_ns=rows[0]['utc_ns'], last_utc_ns=rows[-1]['utc_ns'],
                      timezone_offset_minutes=timezone_minutes,
                      selection='Every CPU sensor row inside the declared run interval plus 3 s bracketing; no value-based filtering.')
        (session/'hwinfo_provenance.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
        print(session.name, 'HWiNFO rows', len(rows))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('mapping', type=Path)
    parser.add_argument('--capture-map', action='store_true')
    args = parser.parse_args()
    capture_map(args.source, args.mapping) if args.capture_map else extract(args.source, args.mapping)
