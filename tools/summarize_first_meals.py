"""Compare registered worlds and recompute survival from individual life facts."""

import argparse
import json
from pathlib import Path

from op0 import DAY
from op0.codec import require

MODELS = {56:"checked-offer", 57:"local-departure", 58:"meal-rendezvous", 59:"first-meal",
          60:"responsive-meal", 61:"work-face", 62:"local-crop-return"}


def outcome(row):
    lives = row["lives"].values()
    census = {c["day"]:c for c in row["census"]}
    for day,c in census.items():
        now = day*DAY
        alive = [a for a in lives if "Adult" in a and a["Adult"][1]<=now and
                 ("death" not in a or a["death"][1]>now)]
        require(c["workers"]==len(alive), "Worker census disagrees with life histories")
        death = row.get("queen_death")
        require(c["queen_alive"]==(death is None or death[1]>now), "Founder census disagrees with death")
    doses = {}
    for key, flow in row["mouths"].items():
        role = key.split("/")[-1]
        doses[role] = doses.get(role,0) + flow["mass_ug"][0]
    year_two = sum("Adult" in a and a["Adult"][1]>365*DAY for a in lives)
    first = row["first"]
    sugar = first.get("FoodCollected")
    last_day = max(census)
    return dict(seed=row["seed"], physics=row["physics"], supply=row["supply"], days=last_day,
                first_exit_day=first["surface"][1]/DAY if "surface" in first else None,
                first_sugar_day=sugar[1]/DAY if sugar else None,
                emergence_to_sugar_hours=(sugar[1]-first["Adult"][1])*24/DAY if sugar else None,
                sugar_before_founder_death=bool(sugar and (not death or sugar[1]<death[1])),
                sugar_gifts_ug=doses,
                founder_approaches=row["encounters"].get("queen_to_worker/moved",0),
                worker_approaches=row["encounters"].get("worker_to_queen/moved",0),
                founder_death_day=death[1]/DAY if death else None,
                workers={d:c["workers"] for d,c in census.items() if d in (73,365,730)},
                later_emerged_alive=row["cohorts_emerged_alive"]["later"],
                year_two_eclosions=year_two,
                sustained=(census[730]["queen_alive"] and year_two>0 and
                           census[730]["workers"]>max(census[365]["workers"],census[73]["workers"]))
                          if last_day==730 else None)


def paired(rows):
    output = [outcome(r) for r in rows]
    seeds = (1,2,3,17,29)
    require({r["physics"] for r in rows}==set(MODELS), "Missing treatment")
    for physics, model in MODELS.items():
        cases = [r for r in rows if r["physics"]==physics]
        require(len({(r["seed"],r["supply"]) for r in cases})==len(cases), "Duplicate world")
        long = physics not in (57,58)
        expected = {(s,"nearby") for s in (seeds if long else (1,2))}
        if long:
            expected.add((2,"absent"))
        require({(r["seed"],r["supply"]) for r in cases}==expected, "Incomplete treatment panel")
        for r in cases:
            kind,_,seed,temp,rh,door,trail,access,supply,air,ground,arm,wick = r["command"].split()
            require((kind,int(seed),temp,rh,door,trail,access,supply,air,ground,arm,wick)==
                    ("NEW_PROVISIONED_NEST",r["seed"],"250","80","plugged","1955","reachable",r["supply"],
                     "sheltered","mineral",model,"wet-wick"),
                    "Mismatched environment")
            require(r["census"][-1]["day"]==(730 if long else 90), "Truncated simulation")
    return output


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipts",type=Path)
    args=parser.parse_args()
    rows=[json.loads(line) for line in args.receipts.read_text(encoding="utf-8-sig").splitlines()]
    for result in paired(rows):
        print(json.dumps(result,separators=(",",":")))
