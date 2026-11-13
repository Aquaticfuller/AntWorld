"""Compare original and portable ecological archives without discarding byte differences."""

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
from struct import unpack_from
from zipfile import ZipFile

from analyze_s6_4_wp6b import check
from run_s6_4_wp6b import write_json
from verify_ecological_publication import csv_rows, manifest


def raw_difference(before, after):
    a=b=0
    changes=Counter()
    while a<len(before) and b<len(after):
        length, = unpack_from("<I",before,a)
        other, = unpack_from("<I",after,b)
        stop,next_stop = a+4+length,b+4+other
        if length!=other:
            return {"aligned":False}
        if before[a:stop]!=after[b:next_stop]:
            if (before[a+69]==4 and before[a:a+154]==after[b:b+154] and
                    before[a+162:stop]==after[b+162:next_stop]):
                changes["trail_concentration_facts"]+=1
            else:
                changes["other_different_facts"]+=1
        a,b=stop,next_stop
    return {"aligned":a==len(before) and b==len(after)} | dict(changes)


def compare_panel(old, new, previous, current, dest):
    left,right = manifest(old),manifest(new)
    check([r["case"] for r in left]==[r["case"] for r in right],"policy matrix denominator changed")
    earlier,later = ({r["case"]:r for r in csv_rows(folder/"worlds.csv")} for folder in (previous,current))
    matched, histogram = [], Counter()
    for a,b in zip(left,right,strict=True):
        case = a["case"]
        x,y = a["receipt"],b["receipt"]
        row = {"case":case,"before_status":x["status"],"after_status":y["status"]}
        if x["status"]==y["status"]=="COMPLETE":
            row["raw_facts_sha_equal"]=int(x["artifacts"]["facts.bin"]==y["artifacts"]["facts.bin"])
            row["final_frame_sha_equal"]=int(x["artifacts"]["final.frame"]==y["artifacts"]["final.frame"])
            if x["artifacts"]["facts.bin"]!=y["artifacts"]["facts.bin"]:
                with ZipFile(old/a["archive"]) as first, ZipFile(new/b["archive"]) as second:
                    delta=raw_difference(first.read("facts.bin"),second.read("facts.bin"))
                row |= delta
            if case in earlier and case in later:
                checked = set(earlier[case]) | set(later[case])
                changed = [k for k in sorted(checked) if (earlier[case].get(k) or "")!=(later[case].get(k) or "")]
                row["changed_observed_endpoints"]=";".join(changed)
                histogram.update(changed)
        matched.append(row)
    dest.mkdir(parents=True)
    with (dest/"policy_comparison.csv").open("x",encoding="utf-8",newline="") as stream:
        fields=tuple(dict.fromkeys(k for row in matched for k in row))
        writer=csv.DictWriter(stream,fields,lineterminator="\n")
        writer.writeheader()
        writer.writerows(matched)
    result = dict(attempts=len(matched), old_failures=sum(r["before_status"]!="COMPLETE" for r in matched),
                  new_failures=sum(r["after_status"]!="COMPLETE" for r in matched),
                  raw_facts_equal=sum(r.get("raw_facts_sha_equal",0) for r in matched),
                  frame_equal=sum(r.get("final_frame_sha_equal",0) for r in matched),
                  aligned_only_trail=sum(bool(r.get("aligned")) and not r.get("other_different_facts") for r in matched),
                  non_trail_fact_difference=sum(bool(r.get("other_different_facts")) or r.get("aligned") is False for r in matched),
                  changed_observed_endpoints=dict(histogram))
    write_json(dest/"policy_summary.json",result)
    print(json.dumps(result,sort_keys=True))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("old","new","previous","current","dest"):
        parser.add_argument(name,type=Path)
    args=parser.parse_args()
    compare_panel(args.old,args.new,args.previous,args.current,args.dest)
