"""Run the matched live habitat preview cases without writing raw histories."""

from argparse import ArgumentParser
from collections import Counter
from contextlib import closing
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from op0 import DAY
from op0.codec import ACTS, KINDS, PHASES, checkpoint
from op0.live import ROOT, NativeCore, core_path
from tools.compare_m0_worker_rhythm import facts


def describe(core, cut):
    counts, first = Counter(), {}
    responses, responders_delivering, foragers = set(), set(), set()
    ports = {edit["event"] for edit in cut["edits"] if edit["box_q"][4] == cut["geometry"]["solid"][4]}
    for event in facts(core, cut["cursor"]):
        name = KINDS[event.kind]
        if name == "StageChanged" and event.stage == 3:
            name = "Eclosed"
        elif name == "Moved":
            if event.position[1] < cut["surface"]["origin_m"][1]:
                continue
            name = "Surface move"
        elif name == "FoodDelivered":
            foragers.add(event.actor)
            if not (event.mass[0] or event.mass[1]) and event.mass[2]:
                name = "Water delivered"
            elif event.actor in responses:
                responders_delivering.add(event.actor)
        elif name == "RecruitmentActivated":
            responses.add(event.actor)
        elif name == "BiologicalObservation" and event.observation and PHASES[event.observation[0]] == "Completed":
            name = ACTS[event.observation[1]]
        elif name == "SoilExcavated" and event.id in ports:
            name = "Surface soil excavated"
        if name not in {"Eclosed", "Surface move", "FoodDelivered", "Water delivered", "RecruitmentCue", "RecruitmentObserved",
                        "RecruitmentActivated", "SoilExcavated", "SoilDropped", "Surface soil excavated",
                        "Entrance patrol", "Entrance antennal contact", "AntDied", "Clean brood"}:
            continue
        counts[name] += 1
        first.setdefault(name, [event.id, event.time, event.actor])
    return dict(facts=cut["cursor"], counts=dict(counts), first=first, carrying_workers=len(foragers),
                recruited_workers_delivering=len(responders_delivering),
                live_workers=sum(a["stage"] == 3 and a["caste"] == 0 for a in cut["ants"].values()),
                history_storage=list(map(int, core.call("HISTORY_STORAGE").split())))


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, default=core_path())
    args = parser.parse_args()
    out = ROOT / "out"
    out.mkdir(exist_ok=True)
    cases = [(seed, 250, 80, "open", half_life) for seed in range(1, 7) for half_life in (60, 1955)]
    cases += [(2, 250, 80, "plugged", 1955), (2, 250, 80, "blocked", 1955),
              (2, 225, 80, "open", 1955), (2, 270, 60, "open", 1955)]
    with TemporaryDirectory(dir=out, prefix="m0-habitat-probe-") as work, closing(NativeCore(args.core.resolve(), work)) as core:
        for seed, temperature, humidity, access, half_life in cases:
            core.call(f"NEW_HABITAT 201 {seed} {temperature} {humidity} {access} {half_life}")
            cut = checkpoint(core.call(f"ADVANCE {90 * DAY}"))
            core.call("CHECK_LEDGERS")
            print(json.dumps(dict(seed=seed, temperature_c=temperature / 10, humidity_percent=humidity, entrance=access,
                                  trail_half_life_seconds=half_life, **describe(core, cut))), flush=True)


if __name__ == "__main__":
    main()
