"""Report paired hierarchical uncertainty, terminal causes and measured phase costs."""

import argparse
from collections import Counter, defaultdict
import csv
from itertools import groupby
from pathlib import Path
from random import Random
from statistics import median

from analyze_integrated_founding import check, dump
from run_integrated_founding import DAY
from run_s6_4_wp6b import write_json


ENDPOINTS = ("complete", "g_eclosion", "g_sustained_worker", "g_queen_uptake", "g_larval_uptake", "g_late_eclosion",
             "g_joint_survival", "valid_loaded_trips", "dietary_eggs", "queen_absorbed_c", "queen_absorbed_w", "queen_150_death_days")


def number(row, key):
    return float(row.get(key) or 0)


def quantiles(items):
    values = sorted(items)
    return {} if not values else {"p50":median(values),**{label:values[int((len(values)-1)*p)] for label,p in
                                   (("p95",.95),("p99",.99),("maximum",1))}}


def curves(observations):
    at_risk = len(observations)
    survival = 1.0
    incidence = defaultdict(float)
    for when, group in groupby(sorted(observations),key=lambda row:row[0]):
        exits=Counter(status for _,status in group)
        for cause,count in exits.items():
            if cause!="censored":
                incidence[cause] += survival*count/at_risk
        yield dict(time_ms=when,at_risk=at_risk,**exits,**{f"incidence_{cause}":v for cause,v in incidence.items()})
        survival *= 1-(sum(exits.values())-exits["censored"])/at_risk
        at_risk -= sum(exits.values())


def read(path):
    with path.open(encoding="utf-8",newline="") as stream:
        return list(csv.DictReader(stream))


def compare(analysis, output, pairs):
    tables, grouped = {}, defaultdict(list)
    folders=sorted({folder.name:folder for root in analysis for folder in root.glob("analysis-*")}.values())
    for folder in folders:
        if not (folder/"worlds.csv").is_file() or folder.name.endswith("-closed"):
            continue
        records = read(folder/"worlds.csv")
        key = (records[0]["model"],records[0]["matrix"])
        tables[key]={row["case"]:row for row in records}
        for row in records:
            if row["status"]=="COMPLETE":
                row["queen_150_death_days"] = min(number(row,"queen_death_ms") or 150*DAY,150*DAY)/DAY
            grouped[(*key,row["population"],row["arm"])].append(row)
    levels, contrasts, phase_costs, competition = [], [], [], []
    for (model,matrix,pop,arm), records in sorted(grouped.items()):
        common = dict(model=model,matrix=matrix,population=pop,arm=arm)
        completed = [row for row in records if row["status"]=="COMPLETE"]
        levels.append(common | dict(n=len(records),observed=len(completed),
            energy_deaths=sum(row["queen_death_cause"]=="1" for row in completed),
            water_deaths=sum(row["queen_death_cause"]=="2" for row in completed),
            queen_120=sum(number(row,"queen_alive_120") for row in completed),
            queen_150=sum(number(row,"queen_alive_150") for row in completed),
            eclosed=sum(number(row,"eclosed") for row in completed),
            adult_survived_7d=sum(number(row,"workers_alive_7d") for row in completed),
            adult_with_cw=sum(number(row,"workers_with_adult_cw") for row in completed),
            queen_death_median_d=median([number(row,"queen_death_ms")/DAY for row in completed if row.get("queen_death_ms")])
                                 if any(row.get("queen_death_ms") for row in completed) else None,
            **{field:sum(number(row,field) for row in completed) for field in ENDPOINTS if field!="queen_150_death_days"},
            **{field:sum(number(row,field) for row in completed) for field in ("source_facts","delivered_c","delivered_p","delivered_w",
               "queen_boundary_uptakes","worker_protein_assimilated_lower_bound_ug","workers_censored","late_adults_from_dietary_eggs")}))
        for field in ("process_wall_ms","advance_ms","peak_rss_bytes","midpoint_save_ms","midpoint_restore_ms","facts_bytes","frame_bytes"):
            values = [number(row,field) for row in completed if number(row,field)>0]
            phase_costs.append(common | dict(field=field,n=len(values),**quantiles(values)))
        for endpoint, terminal in (("first_worker", "first_worker_ms"),("first_delivery", "first_delivery_ms"),
                                   ("queen_joint_uptake", "first_queen_water_ms"),("queen_survival", "queen_death_ms")):
            outcomes = []
            for row in completed:
                when = number(row,terminal)
                if endpoint=="queen_joint_uptake":
                    c=number(row,"first_queen_carb_ms")
                    when=max(c,when) if c and when else 0
                death = number(row,"queen_death_ms")
                if when and (endpoint not in ("first_worker","first_delivery") or not death or when<death):
                    outcomes.append((int(when),f"death_{row['queen_death_cause']}" if endpoint=="queen_survival" else "observed_endpoint"))
                elif death:
                    outcomes.append((int(death),f"death_{row['queen_death_cause']}"))
                else:
                    outcomes.append((150*DAY,"censored"))
            competition.extend(common | dict(endpoint=endpoint,**values) for values in curves(outcomes))
    rng=Random(640602)
    for earlier,later in pairs:
        for matrix in ("nominal","factorial"):
            if (earlier,matrix) not in tables or (later,matrix) not in tables:
                continue
            left,right=tables[earlier,matrix],tables[later,matrix]
            check(left.keys()==right.keys(), f"paired world inventory changed: {earlier}/{later}/{matrix}")
            for pop,arm in sorted({(row["population"],row["arm"]) for row in right.values()}):
                groups=defaultdict(list)
                for case,after in right.items():
                    if (after["population"],after["arm"])!=(pop,arm):
                        continue
                    before=left[case]
                    check((before["profile"],before["seed"])==(after["profile"],after["seed"]), "unmatched software profile or seed")
                    groups[after["profile"]].append((before,after))
                complete=sum(a["status"]==b["status"]=="COMPLETE" for group in groups.values() for a,b in group)
                for endpoint in ENDPOINTS:
                    samples = [[number(b,endpoint)-number(a,endpoint) for a,b in group] for group in groups.values()]
                    n=sum(map(len,samples))
                    if complete==n or endpoint=="complete":
                        distribution=sorted(sum(x for g in rng.choices(samples,k=len(samples)) for x in rng.choices(g,k=len(g)))/n
                                            for _ in range(4096))
                        effect=sum(sum(g) for g in samples)/n
                        lo,hi=(distribution[int((len(distribution)-1)*p)] for p in (.025,.975))
                    else:
                        effect=lo=hi=None
                    contrasts.append(dict(control=earlier,candidate=later,matrix=matrix,population=pop,arm=arm,endpoint=endpoint,
                                          worlds=n,complete_pairs=complete,effect=effect,lo95=lo,hi95=hi))
    output.mkdir(parents=True)
    for filename,records in (("groups",levels),("paired_effects",contrasts),("phase_costs",phase_costs),("competing_events",competition)):
        dump(output/f"{filename}.csv",records)
    gates={}
    for (model,matrix),cases in tables.items():
        if matrix=="factorial":
            by_profile=defaultdict(list)
            for row in cases.values():
                if row["arm"]=="balanced":
                    by_profile[row["population"],row["profile"]].append(number(row,"complete"))
            gates[model]={pop:{profile:int(sum(values)) for (p,profile),values in sorted(by_profile.items()) if p==pop}
                          for pop in sorted({p for p,_ in by_profile})}
    write_json(output/"factorial_gate.json", gates)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("analysis",type=Path)
    parser.add_argument("out",type=Path)
    parser.add_argument("--additional-analysis",type=Path,action="append",default=[])
    parser.add_argument("--pair",action="append",default=[])
    args=parser.parse_args()
    compare([args.analysis,*args.additional_analysis],args.out,[pair.split(":") for pair in args.pair])
