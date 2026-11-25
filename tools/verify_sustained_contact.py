"""Replay the six-hour seed-2 intervention on a disposable, content-addressed cut."""

import argparse
from contextlib import closing
import gzip
from hashlib import sha256
import json
from math import dist
from pathlib import Path
from tempfile import TemporaryDirectory

from op0.codec import ACTS, KINDS, PHASES, checkpoint, require
from op0.live import NativeCore, ROOT, core_path, live_bodies
from tools.compare_m0_worker_rhythm import facts


EVIDENCE = ROOT / "research/single_nest"
WORLD = "00000000-0000-028d-0000-00d30000264a"
START = 7_845_622_429
END = 7_867_222_430
CUT_HASH = "23bae7f931aa605e0b81b215d3757c876b9c481f0fa1b2fa2b9699ce497418dc"
LAST_ALIVE_HASH = "dfade043e7169f4f43b6ce5386c6a09fb0be6db201f33af961c8cf31b1b37b2d"


def fnv64(data):
    value = 14695981039346656037
    for byte in data:
        value = ((value ^ byte) * 1099511628211) & ((1 << 64) - 1)
    return value.to_bytes(8, "little")


def experimental_fork(core, folder, original):
    """Change only three declared config bytes in this one research fixture."""
    require(sha256(original).hexdigest() == CUT_HASH, "Unexpected research fixture")
    command = next(row["command"] for line in (EVIDENCE / "WORKED_EXIT_TRIALS.jsonl").read_text().splitlines()
                   if (row := json.loads(line))["physics"] == 63 and row["seed"] == 2 and row["supply"] == "nearby")
    initial = []
    slot = "a" * 32
    for model in ("worked-exit", "sustained-contact"):
        core.call(command.replace("worked-exit", model))
        core.call(f"SAVE_SNAPSHOT {slot}")
        file = folder / (slot + ".awstate")
        initial.append(file.read_bytes()[:-8])
        file.unlink()
    old, candidate = initial
    changes = [(i, a, b) for i, (a, b) in enumerate(zip(old, candidate, strict=True)) if a != b]
    require([(a,b) for _,a,b in changes] == [(56,57), (63,64), (19,20)], "Unexpected layout difference")
    modified = bytearray(original)
    for offset, before, after in changes:
        if before == 19:
            config_suffix = old[offset-48:offset+1]
            require(modified.count(config_suffix) == 1, "Ambiguous immutable configuration")
            offset = modified.index(config_suffix) + 48
        require(modified[offset] == before, "Unexpected source field")
        modified[offset] = after
    modified[-8:] = fnv64(modified[:-8])
    return modified


def replay(core, folder, raw, physics):
    slot = str(physics) * 16
    (folder / (slot + ".awstate")).write_bytes(raw)
    def load():
        return checkpoint(core.call(f"LOAD_SNAPSHOT {slot} {WORLD}"))
    start = load()
    require(start["physics"] == physics and start["time_ms"] == START, "Wrong starting conditions")
    before_death = core.call(f"ADVANCE {END-1}")
    if physics == 63:
        require(sha256(before_death).hexdigest() == LAST_ALIVE_HASH, "Original history diverged")
    last_raw = core.call(f"ADVANCE {END}")
    end = checkpoint(last_raw)
    stream = list(facts(core, end["cursor"], start["cursor"]))
    payments = [f for f in stream if KINDS[f.kind] == "NutritionTransferred" and f.payload == 2 and f.mass[0]]
    deaths = [f.id for f in stream if KINDS[f.kind] == "AntDied" and f.actor == 2]
    if physics == 63:
        require(deaths == [469357] and not payments, "Old failure changed")
    else:
        require(not deaths and any(f.actor in (8,9) for f in payments), "Real founder meal missing")
    approaches = [[f.id, f.time, f.actor, f.observation[2], f.outcome, list(f.position)]
                  for f in stream if f.observation and ACTS[f.observation[1]] == "Approach a nestmate"
                  and PHASES[f.observation[0]] == "Completed" and f.actor in (8,9) and f.observation[2] == 2]
    load()
    witnessed = []
    for meal in payments:
        prior = checkpoint(core.call(f"ADVANCE {meal.time-1}"))
        bodies = live_bodies(core.call("BODY_STATES"), prior)
        pair, = [line.split() for line in core.call("ORAL_ACCESS").splitlines() if int(line.split()[0]) == meal.actor]
        require(pair[1:3] == [b"1", b"1"], "Missing visible contact before payment")
        after = checkpoint(core.call(f"ADVANCE {meal.time}"))
        def crop_change(actor):
            return [b-a for a,b in zip(prior["ants"][actor]["crop_ug"], after["ants"][actor]["crop_ug"], strict=True)]
        require(crop_change(2) == list(meal.mass) == [-v for v in crop_change(meal.actor)], "Unequal crop payment")
        gap = 1000 * dist(bodies[str(meal.actor)]["mouth_m"], bodies["2"]["mouth_m"])
        witnessed.append(dict(event=meal.id, time_ms=meal.time, donor=meal.actor, receiver=2,
                              mass_ug=meal.mass, mouth_gap_mm=gap))
    require(core.call(f"ADVANCE {END}") == last_raw and core.call("CHECK_LEDGERS") == b"",
            "Partitioned replay or ledger mismatch")
    uptake = [[f.id,f.time,f.mass[0]] for f in stream if f.actor == 2 and f.mass[0]
              and KINDS[f.kind] in ("PhysiologyUpdated","FoundingBoundaryUptake")]
    return dict(physics=physics, start_cursor=start["cursor"], end_cursor=end["cursor"], deaths=deaths,
                payments=witnessed, founder_uptake=uptake, approaches=approaches, final_sha256=sha256(last_raw).hexdigest())


def verify(binary, scratch):
    original = gzip.decompress((EVIDENCE / "SEED2_SIX_HOUR_CUT.awstate.gz").read_bytes())
    with TemporaryDirectory(dir=scratch) as temp, closing(NativeCore(binary, temp)) as core:
        folder = Path(temp)
        branch = experimental_fork(core, folder, original)
        return [replay(core, folder, data, version) for data, version in ((original,63),(branch,64))]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, default=core_path())
    args = parser.parse_args()
    print(json.dumps(verify(args.core.resolve(), ROOT/"out"), indent=2))
