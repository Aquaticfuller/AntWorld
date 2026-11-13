"""Separate the founding mother's contact, hatch cue, repeat and paid feed endpoints."""

import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
from statistics import median

from analyze_s6_4_wp6b import check, facts
from run_s6_4_wp6b import write_json
from verify_ecological_closure import WATER, fixed_witnesses, read_archives


def diagnose(raw, queen, horizon):
    larvae, cues, repeats = {}, {}, set()
    for event,time,source,kind,actor,target,aux,stage,_,mass,obs in facts(raw,WATER):
        if kind==7 and stage==1:
            larvae[actor] = dict(hatch_event=event,hatch_ms=time)
        elif kind==50 and actor==queen:
            check(target in larvae and time==larvae[target]["hatch_ms"],"founder cue lacks its actual hatch")
            larvae[target].update(hatch_cue_event=event,hatch_cue_ms=time)
            cues[aux]=target
        elif kind==41 and actor==queen and aux==3:
            repeats.add(source)
        elif kind==42 and actor==queen and obs[2] in larvae:
            phase,act,child,bout,*_ = obs
            larva=larvae[child]
            if phase==0:
                larva.setdefault("first_opportunity_ms",time)
            if phase==1 and act==7:
                larva.setdefault("first_selected_feed_ms",time)
                larva["repeat_selections"]=larva.get("repeat_selections",0)+(source in repeats)
                if source in cues:
                    check(cues[source]==child,"hatch wake did not respect its local target")
                    larva["hatch_cue_feed_selected"]=1
                    larva["hatch_cue_feed_bout"]=bout
            if phase==2 and act==7:
                larva.setdefault("first_started_feed_ms",time)
            if phase==3 and act==7 and larva.get("hatch_cue_feed_bout")==bout and mass[1]:
                larva["hatch_cue_feed_paid"]=1
        elif kind==48 and actor==queen and mass[1]:
            larva=larvae[target]
            larva.setdefault("first_maternal_protein_ms",time)
            larva.setdefault("first_maternal_protein_event",event)
            larva["positive_maternal_protein_rations"]=larva.get("positive_maternal_protein_rations",0)+1
        elif kind==16 and actor in larvae and stage==1 and mass[1]:
            larvae[actor].setdefault("first_larval_assimilation_ms",time)
        elif kind==7 and stage==2:
            larvae[actor].update(larval_end_ms=time,larval_outcome="PUPATED")
        elif kind==8 and actor in larvae and "larval_outcome" not in larvae[actor]:
            larvae[actor].update(larval_end_ms=time,larval_outcome=f"DEATH_{target}")
    for row in larvae.values():
        if "larval_outcome" not in row:
            row.update(larval_end_ms=horizon,larval_outcome="RIGHT_CENSORED")
    return larvae


def run(directory, output, witnesses_only=False):
    output.mkdir(parents=True)
    individuals, groups = [], defaultdict(Counter)
    for archive, files in read_archives(directory,witnesses_only,"care"):
        case=json.loads(files["case.json"])
        receipt=archive["receipt"]
        check(receipt["status"]=="COMPLETE","care panel has an unaccounted host failure")
        queen=int(receipt["summary"]["queen"])
        for identity,row in diagnose(files["facts.bin"],queen,case["horizon_ms"]).items():
            individuals.append(dict(case=archive["case"],population=case["population"],treatment=case["treatment"],
                                    seed=case["software_seed"],ant=identity,**row))
            total=groups[case["population"],case["treatment"]]
            total["larvae"]+=1
            for k in ("hatch_cue_event","first_opportunity_ms","first_selected_feed_ms","first_started_feed_ms",
                      "first_maternal_protein_ms","first_larval_assimilation_ms","hatch_cue_feed_selected","hatch_cue_feed_paid"):
                total[k]+=k in row
            total["repeat_selections"]+=row.get("repeat_selections",0)
            if "first_maternal_protein_ms" not in row:
                total["unfed_"+row["larval_outcome"]]+=1
    with (output/"founder_feeding_by_larva.csv").open("x",newline="",encoding="utf-8") as stream:
        headers=tuple(dict.fromkeys(k for r in individuals for k in r if k!="hatch_cue_feed_bout"))
        writer=csv.DictWriter(stream,headers,extrasaction="ignore",lineterminator="\n")
        writer.writeheader()
        writer.writerows(individuals)
    results=[]
    for (population,treatment),value in sorted(groups.items()):
        delays=[(r["first_maternal_protein_ms"]-r["hatch_ms"])/3600000 for r in individuals
                if (r["population"],r["treatment"])==(population,treatment) and "first_maternal_protein_ms" in r]
        results.append(dict(population=population,treatment=treatment,**value,
                            median_observed_first_meal_delay_hours=median(delays) if delays else None))
    write_json(output/"founder_feeding_summary.json",results)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("care_archives",type=Path)
    parser.add_argument("output",type=Path)
    parser.add_argument("--witnesses-only",action="store_true",help=f"Use the {len(fixed_witnesses('care'))} fixed public archives.")
    arguments=parser.parse_args()
    run(arguments.care_archives,arguments.output,arguments.witnesses_only)
