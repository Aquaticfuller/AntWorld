"""Compare oral planners on an unchanged reference cut and replay two old excavators."""

import argparse
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from op0 import DAY
from op0.codec import require
from op0.live import NativeCore, ROOT, core_path
from tools.inspect_first_meal_window import inspect


def terminal_probe(core, trial, expected):
    raw = core.call(trial["command"])
    require(sha256(raw).hexdigest() == trial["initial_sha256"], "Reference input changed")
    time = trial["queen_death"][1] - 1
    for t in range(4 * DAY, time, 4 * DAY):
        core.call(f"ADVANCE {t}")
        core.call("COMPACT_HISTORY")
    cut = core.call(f"ADVANCE {time}")
    require(sha256(cut).hexdigest() == expected["predeath_sha256"], "Terminal cut changed")
    def pairs(command):
        return [list(map(int, line.split())) for line in core.call(command).splitlines()]
    original = pairs("ORAL_ACCESS")
    candidate = pairs("ORAL_ALIGNMENT_PROBE")
    require(cut == core.call("FRAME"), "Reading a counterfactual changed the world")
    require([r[:3]+r[5:] for r in original] == [r[:3]+r[5:] for r in candidate],
            "A geometry probe changed visibility, contact or payable carbohydrate")
    return dict(sha256=expected["predeath_sha256"], time_ms=time, fields=[
        "donor", "visible", "in_contact", "founder_has_step", "donor_has_step",
        "offered_carbs_ug", "requested_carbs_ug"], original=original, candidate=candidate)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, default=core_path())
    args = parser.parse_args()
    repo = ROOT / "research/single_nest"
    cuts = {r["purpose"]:r["record"] for r in map(json.loads, (repo/"FIRST_MEAL_LOCAL_CUTS.jsonl").read_text().splitlines())}
    trials = map(json.loads, (repo/"FIRST_MEAL_TRIALS.jsonl").read_text().splitlines())
    trial = next(r for r in trials if r["physics"] == 62 and r["seed"] == 2 and r["supply"] == "nearby")
    with TemporaryDirectory(dir=ROOT/"out") as temp, closing(NativeCore(args.core.resolve(), temp)) as core:
        print(json.dumps(terminal_probe(core,trial,cuts["candidate-founder-last-ms"])),flush=True)
        for seed in (17,29):
            result = inspect(core,"local-crop-return",seed,46,48,False)
            old = cuts[f"post-dig-pre-forage-{seed}"]
            require(json.loads(json.dumps(result)) == old,
                    "Old post-dig world no longer reproduces")
            print(json.dumps(dict(seed=seed, cuts=[c["frame_sha256"] for c in result["cuts"]])),flush=True)


if __name__ == "__main__":
    main()
