"""Replay a founder's terminal encounter and compare a matched two-year panel."""

import argparse
from contextlib import closing
import gzip
from hashlib import sha256
import json
from math import dist
from pathlib import Path
from tempfile import TemporaryDirectory

from op0.codec import KINDS, checkpoint, require
from op0.live import NativeCore, ROOT, core_path, live_bodies
from tools.compare_m0_worker_rhythm import facts
from tools.verify_sustained_contact import EVIDENCE, experimental_fork, feeding_summary
from tools.verify_first_meal import verify_inputs


def terminal(binary, version):
    raw = gzip.decompress((EVIDENCE / "SEED2_STALLED_PAIR_CUT.awstate.gz").read_bytes())
    world = "00000000-0000-028d-0000-00e30000264a"
    slot = "e" * 32
    stop = 7_088_150_452
    with TemporaryDirectory(dir=ROOT/"out") as temp, closing(NativeCore(binary, temp)) as core:
        folder = Path(temp)
        if version != 67:
            raw = experimental_fork(core, folder, raw, 67, version)
        (folder/(slot+".awstate")).write_bytes(raw)
        def load():
            return checkpoint(core.call(f"LOAD_SNAPSHOT {slot} {world}"))
        start = load()
        final = core.call(f"ADVANCE {stop}")
        end = checkpoint(final)
        stream = list(facts(core, end["cursor"], start["cursor"]))
        gifts = [f for f in stream if KINDS[f.kind]=="NutritionTransferred" and f.payload==2 and f.mass[0]]
        deaths = [[f.id,f.time] for f in stream if KINDS[f.kind]=="AntDied" and f.actor==2]
        if version==67:
            require(not gifts and deaths==[[131278, stop]], "Published failure changed")
        else:
            require(gifts and not deaths, "Local encounter did not deliver sugar before starvation")
        load()
        witnessed = []
        for gift in gifts:
            before = checkpoint(core.call(f"ADVANCE {gift.time-1}"))
            poses = live_bodies(core.call("BODY_STATES"), before)
            oral = next(r.split() for r in core.call("ORAL_ACCESS").splitlines() if int(r.split()[0])==gift.actor)
            require(oral[1:3]==[b"1",b"1"], "Gift lacks previous mouth contact")
            after = checkpoint(core.call(f"ADVANCE {gift.time}"))
            for who, sign in ((gift.actor,-1), (2,1)):
                a,b = before["ants"][who]["crop_ug"],after["ants"][who]["crop_ug"]
                require([sign*(y-x) for x,y in zip(a,b)]==list(gift.mass), "Unbalanced oral transfer")
            witnessed.append(dict(id=gift.id, time_ms=gift.time, donor=gift.actor, dose_ug=gift.mass,
                                  mouth_mm=1000*dist(poses["2"]["mouth_m"],poses[str(gift.actor)]["mouth_m"])))
        require(core.call(f"ADVANCE {stop}")==final and core.call("CHECK_LEDGERS")==b"", "Continuation or ledger differs")
        uptake = sum(f.mass[0] for f in stream if f.actor==2 and KINDS[f.kind] in
                     ("FoundingBoundaryUptake","PhysiologyUpdated"))
        if gifts:
            require(uptake>0, "Sugar stayed in the founder crop")
            load()
            cut_time = gifts[0].time-1
            pending = core.call(f"ADVANCE {cut_time}")
            saved = "f"*32
            core.call(f"SAVE_SNAPSHOT {saved}")
            require(core.call(f"LOAD_SNAPSHOT {saved} {world}")==pending, "Pending meal lost in snapshot")
            require(core.call(f"ADVANCE {stop}")==final, "Resume changed outcome")
        return dict(version=version, cut_sha256=sha256(raw).hexdigest(), final_sha256=sha256(final).hexdigest(),
                    deaths=deaths, payments=witnessed, sugar_uptake_ug=uptake, final_energy_nj=end["ants"][2]["energy_nj"],
                    final_body_water_ug=end["ants"][2]["hydration_ug"])


def panel(binary, path):
    with gzip.open(EVIDENCE/"SUSTAINED_CONTACT_TRIALS.jsonl.gz", "rt") as source:
        old = [row for line in source if (row:=json.loads(line))["physics"]==67]
    with gzip.open(path, "rt") as source:
        new = [json.loads(line) for line in source]
    pairs = {(r["seed"],r["supply"]) for r in old}
    versions = {68:"local-solicitation", 69:"source-refill"}
    require(len(pairs)==6 and len(new)==12 and
            {(r["physics"],r["seed"],r["supply"]) for r in new}==
            {(v,seed,supply) for v in versions for seed,supply in pairs}, "Missing paired worlds")
    for row in new:
        baseline = next(r for r in old if (r["seed"],r["supply"])==(row["seed"],row["supply"]))
        args = row["command"].split()
        expected = baseline["command"].split()
        require(args[:1]+args[2:-2]+args[-1:]==expected[:1]+expected[2:-2]+expected[-1:] and
                args[-2]==versions[row["physics"]] and row["census"][-1]["day"]==730,
                "Changed environment, treatment or observation window")
        if row["supply"]=="absent":
            require(not row["founder_feeding_by_day"], "Unfunded sugar in absent-food control")
        paid = sum(v["sugar_ug"] for k,v in row["sugar_flux"].items()
                   if k.startswith("NutritionTransferred/") and k.endswith("/2"))
        require(paid==sum(day["sugar_ug"] for day in row["founder_feeding_by_day"].values()),
                "Actor flux disagrees with the founder meal ledger")
        for entry in row["sugar_flux"].values():
            require(0<=entry["before_founder_death_ug"]<=entry["sugar_ug"] and entry["count"]>0 and
                    entry["first"]<=entry["last"], "Invalid sugar flux interval")
    return dict(inputs=verify_inputs(binary, old+new), worlds=[feeding_summary(r) for r in old+new])


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core",type=Path,default=core_path())
    parser.add_argument("--panel",type=Path)
    args=parser.parse_args()
    binary=args.core.resolve()
    (ROOT/"out").mkdir(exist_ok=True)
    result=panel(binary,args.panel) if args.panel else [terminal(binary,v) for v in (67,68,69,70)]
    print(json.dumps(result,indent=2))
