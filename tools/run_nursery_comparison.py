"""Measure matching seeded nurseries from committed moves and sampled motion plans."""

from argparse import ArgumentParser
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from math import dist
from pathlib import Path
from tempfile import TemporaryDirectory

from op0.archive import file_hash, json_bytes
from op0.codec import KINDS, OUTCOMES, checkpoint
from op0.live import NativeCore, core_path, live_motion
from tools.run_r0_diagnostics import journal
from tools.run_r0_r1 import Witness


def body_intersections(frame, plans):
    geometry = frame["geometry"]
    bodies = []
    for id_, ant in frame["ants"].items():
        if ant["stage"] != 3:
            continue
        pose = ant["position_m"]
        if plan := plans.get(id_):
            pose = tuple(a+(b-a)*plan["progress"] for a,b in zip(plan["from_m"], plan["to_m"], strict=True))
        loaded = any(ant["carried_ug"]) or ant["id"] in frame["soil_carriers"]
        half = geometry["quantum_m"] * geometry["loaded_half_q" if loaded else "body_half_q"]
        bodies.append((pose, half))
    return sum(all(abs(a-b) < half+other_half-1e-12 for a,b in zip(p,q,strict=True))
               for i,(p,half) in enumerate(bodies) for q,other_half in bodies[:i])


def assay(core, directory, traffic):
    command = f"NEW_NURSERY 91 17 {int(traffic)}"
    with closing(NativeCore(core, directory)) as native:
        initial_raw = native.call(command)
        initial = checkpoint(initial_raw)
        samples = overlap_samples = peak_pairs = 0
        for time in range(0,120_000+1,25):
            final_raw = native.call(f"ADVANCE {time}")
            final = checkpoint(final_raw,verify_hash=False)
            plans = live_motion(native.call("WORKER_MOTION"),final)
            pairs = body_intersections(final,plans)
            samples += 1
            overlap_samples += bool(pairs)
            peak_pairs = max(peak_pairs,pairs)
        digest = Witness(None)
        starts = {k:a["position_m"] for k,a in initial["ants"].items() if (a["stage"],a["caste"])==(3,0)}
        actions = Counter(worker_moves=0, brood_moves=0, nutrition_transfers=0, nestmate_approaches=0, blocked_care_bouts=0)
        distance_m, actors = 0.0, set()
        for fact in journal(native,0,final["cursor"],digest):
            kind, outcome = KINDS[fact.kind], OUTCOMES[fact.outcome]
            if kind == "Moved" and outcome == "Success" and fact.actor in starts:
                distance_m += dist(starts[fact.actor],fact.position)
                starts[fact.actor] = fact.position
                actors.add(fact.actor)
                actions["worker_moves"] += 1
            if kind == "BroodMoved" and outcome == "Success":
                actions["brood_moves"] += 1
            if kind == "NutritionTransferred" and sum(fact.mass) > 0 and outcome in {"Success", "Partial"}:
                actions["nutrition_transfers"] += 1
            if fact.observation:
                act=fact.packet()["action"]
                if outcome == "Success" and act["phase"] == "Completed" and act["act"] == "Approach a nestmate":
                    actions["nestmate_approaches"] += 1
                if act["phase"] == "Interrupted" and outcome == "Blocked":
                    actions["blocked_care_bouts"] += 1
        native.call("CHECK_LEDGERS")
        return dict(command=command, world_id=final["world"], physics=final["physics"], horizon_ms=final["time_ms"], samples=samples,
                    overlap_samples=overlap_samples, peak_pairs=peak_pairs, adults_displaced=len(actors),
                    worker_distance_m=distance_m, actions=dict(actions), facts=final["cursor"],
                    initial_frame_sha256=sha256(initial_raw).hexdigest(), final_frame_sha256=sha256(final_raw).hexdigest(),
                    canonical_sha256=digest.digest.hexdigest())


def main():
    p = ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path)
    p.add_argument("--core", type=Path, default=core_path())
    args = p.parse_args()
    core=args.core.resolve(strict=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=args.output.parent) as temp:
        control, candidate=(assay(core,temp,traffic) for traffic in (False,True))
    result=dict(binary_sha256=file_hash(core), control=control, candidate=candidate)
    args.output.write_bytes(json_bytes(result))
    print(json.dumps(result,indent=2))


if __name__ == "__main__":
    main()
