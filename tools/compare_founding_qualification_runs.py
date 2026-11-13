"""Compare the old and candidate application timings without dropping any matched row."""

import argparse
from collections import defaultdict
from pathlib import Path
from statistics import median

from analyze_founding_qualification_performance import collect, key
from analyze_s6_4_wp6b import check
from founding_qualification_witnesses import table


PHASES=("advance_ms","cut_ms","checkpoint_ms","midpoint_save_ms","midpoint_restore_ms","total_ms","process_ms")


def compare(before, after):
    fields=("case","model","session","block","slot","treatment")
    def by_position(raw):
        rows=collect(raw)
        index={tuple(r[k] for k in fields):r for r in rows}
        check(len(index)==len(rows),"duplicate application schedule position")
        return index
    originals, candidate=by_position(before),by_position(after)
    check(candidate.keys()<=originals.keys(),"new performance run changed its workload schedule")
    groups=defaultdict(list)
    for position,row in candidate.items():
        original=originals[position]
        check(key(row)==key(original) and row["state_hash"]==original["state_hash"] and row["trace_hash"]==original["trace_hash"],
              "changed application timing workload authority")
        groups[row["case"],row["model"],row["treatment"]].append((original,row))
    for (case,model,treatment),group in sorted(groups.items()):
        for phase in PHASES:
            a,b=([float(pair[i][phase]) for pair in group] for i in (0,1))
            yield dict(case=case,model=model,treatment=treatment,phase=phase,n=len(group),
                original_median_ms=median(a),candidate_median_ms=median(b),
                ratio=median(b)/median(a) if median(a) else None,
                original_max_ms=max(a),candidate_max_ms=max(b))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("baseline","candidate","output"):
        parser.add_argument(name,type=Path)
    args=parser.parse_args()
    rows=list(compare(args.baseline,args.candidate))
    args.output.write_bytes(table(rows))
    print(f"{sum(row['n'] for row in rows if row['phase']=='process_ms')} same-authority application rows compared")
