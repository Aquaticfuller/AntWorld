"""Summarize all flat worker traces reserved in the frozen protocol."""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import statistics as st
import zipfile

from analyze_s6_3_2_performance import describe
from analyze_s6_3_3_1_performance import emit

DOI = '10.1371/journal.pone.0076531.s005'
SHA256 = '9990d73ea6c08ffeedfef7e332b8f1623ab71936afc62e25d5cf9f4df3520b49'
FIXTURE_CEILING_MM_S = .001*1000/10


def path_length(points):
    return sum(math.dist(a[1:], b[1:]) for a,b in zip(points, points[1:]))


def subsample(points):
    chosen = [points[0]]
    threshold = points[0][0]+1
    for point in points[1:]:
        if point[0]+1e-9 >= threshold:
            chosen.append(point)
            threshold += 1
    if chosen[-1] != points[-1]:
        chosen.append(points[-1])
    return chosen


def records(path):
    header = None
    with zipfile.ZipFile(path) as archive:
        for name in sorted(archive.namelist()):
            if name.endswith('/') or Path(name).name.startswith('._') or name.startswith('__MACOSX/'):
                continue
            with archive.open(name) as source:
                reader = csv.reader(io.TextIOWrapper(source, encoding='utf-8-sig'), delimiter='\t')
                fields = next(reader)
                if header is None:
                    header = fields
                assert header == fields and len(fields) == 10, (name,fields)
                rows = [row for row in reader if any(row)]
            assert all(len(row) == 10 and row[:6] == rows[0][:6] for row in rows), name
            angle,colony,temp,humidity,date,ant = rows[0][:6]
            assert angle == '1', angle  # Dataset S1 uses inclination index 1 for the flat condition.
            points = [tuple(map(float,row[7:10])) for row in rows]
            assert all(math.isfinite(v) for point in points for v in point)
            assert all(a[0] < b[0] for a,b in zip(points,points[1:])), name
            duration = points[-1][0]-points[0][0]
            net = math.dist(points[0][1:],points[-1][1:])
            path_m = path_length(points)
            coarse = path_length(subsample(points))
            assert duration > 0 and net-1e-12 <= coarse <= path_m+1e-12
            yield dict(dataset_doi=DOI, archive_member=name, inclination_raw=angle, inclination_deg=0, colony=colony,
                       temperature_raw=temp, humidity_raw=humidity, date_raw=date, ant=ant,
                       recorded_points=len(points), duration_s=duration, net_m=net, path_m=path_m,
                       path_at_1s_m=coarse, net_mm_per_s=1000*net/duration, path_mm_per_s=1000*path_m/duration,
                       path_at_1s_mm_per_s=1000*coarse/duration, care_fixture_ceiling_mm_per_s=FIXTURE_CEILING_MM_S)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('zip', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    with args.zip.open('rb') as f:
        assert hashlib.file_digest(f,'sha256').hexdigest() == SHA256
    rows = list(records(args.zip))
    assert len(rows) == 69 and len({(r['colony'],r['date_raw'],r['ant']) for r in rows}) == 69
    colonies = sorted({r['colony'] for r in rows})
    args.out.mkdir(parents=True, exist_ok=True)
    emit(args.out/'flat_worker_tracks.csv',rows,False)
    summaries = []
    for group in ('all',*colonies):
        chosen = [r for r in rows if group == 'all' or r['colony'] == group]
        for metric in ('duration_s','net_mm_per_s','path_mm_per_s','path_at_1s_mm_per_s'):
            values = [r[metric] for r in chosen]
            summaries.append(dict(colony=group,metric=metric,mean=st.mean(values),**describe(values)))
    emit(args.out/'flat_worker_summary.csv',summaries,False)
    receipt = dict(dataset_doi=DOI,archive_sha256=SHA256,files=len(rows),colonies=colonies,
                   geometry='Flat exploratory canvas. No caregiver load or nest travel.',
                   subsampling='First recorded point at or after each elapsed integer second, plus the final point.',
                   comparisons='Separate locomotion component, with no parameter fit or independent brood assay.')
    (args.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps([r for r in summaries if r['colony']=='all']))


if __name__=='__main__':
    main()
