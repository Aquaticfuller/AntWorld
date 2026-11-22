"""Read worker body, crop and source stocks on actual emergence and death cuts."""

from argparse import ArgumentParser
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path

from op0 import DAY
from op0.codec import CASTES, DEATHS, KINDS, STAGES, checkpoint, decode_fact, require
from op0.live import ROOT, NativeCore, core_path, founding_balance


def trace(core, receipt):
    initial = core.call(receipt["command"])
    require(sha256(initial).hexdigest() == receipt["initial_sha256"], "Different initial world")
    frame = checkpoint(initial)
    end = receipt["census"][-1]["day"] * DAY
    targets = "worker worker-death"
    source, = (s for s in frame["sources"].values() if s["position_m"][1] < frame["surface"]["origin_m"][1]
               and s["initial_ug"][2] and sum(s["initial_ug"]) == s["initial_ug"][2])
    wick = int(source["id"])
    lives = {}
    reply = core.call(f"FIND_NEXT_MILESTONES 0 {targets}")
    while reply or frame["time_ms"] < end:
        if not reply:
            reply = core.call(f"ADVANCE_UNTIL_ANY {end} {targets}")
        if reply == b"exhausted":
            break
        frame = checkpoint(core.call("FRAME"))
        if not reply:
            continue
        death = reply[0] == 1
        require(reply[0] <= 1 and (not death or STAGES[reply[1]] == "Adult"), "Invalid milestone")
        _, event = decode_fact(reply, 2 if death else 1)
        ant = frame["ants"][event.actor]
        require(event.time == frame["time_ms"] and event.id <= frame["cursor"] and CASTES[ant["caste"]] == "Worker"
                and KINDS[event.kind] == ("AntDied" if death else "StageChanged"), "Milestone does not match cut")
        life = lives.setdefault(event.actor, {})
        kind = "death" if death else "emergence"
        require(kind not in life, "Repeated milestone")
        balance = founding_balance(core, frame, event.actor)
        life[kind] = dict(fact=event.id, time_ms=event.time, position_m=event.position, body_water_ug=balance["water_ug"],
                          body_energy_nj=balance["energy_nj"], lipid_ug=balance["lipid_ug"], crop_ug=balance["crop_ug"],
                          water_lost_ug=ant["lost_water_ug"], wick_water_ug=frame["sources"][wick]["stock_ug"][2],
                          depot_cpw_ug=frame["colonies"][int(ant["colony"])]["stock_ug"][:3])
        if death:
            life[kind]["cause"] = DEATHS[event.payload]
        reply = core.call(f"FIND_NEXT_MILESTONES {event.id} {targets}")
    raw = core.call(f"ADVANCE {end}")
    require(sha256(raw).hexdigest() == receipt["final_sha256"], "Final frame differs from the two-year assay")
    require(core.call("CHECK_LEDGERS") == b"", "Native ledger failure")
    deaths = Counter(life["death"]["cause"] for life in lives.values() if "death" in life)
    expected = {key.removeprefix("Adult: "): value for key, value in receipt["offspring_deaths"].items()
                if key.startswith("Adult: ")}
    require(len(lives) == receipt["transitions"]["eclosed_workers"] and deaths == expected
            and all("emergence" in life for life in lives.values()), "Individual fates disagree with the census")
    return dict(run=receipt["run"], seed=receipt["seed"], command=receipt["command"],
                initial_sha256=receipt["initial_sha256"], final_sha256=receipt["final_sha256"],
                end_ms=end, wick_position_m=source["position_m"], lives=lives)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, default=core_path())
    parser.add_argument("--run", default="nearby")
    parser.add_argument("--seed", type=int, default=3)
    args = parser.parse_args()
    path = ROOT / "research/single_nest/PROTECTED_HABITAT_RECEIPTS.jsonl"
    receipt, = (r for line in path.read_text(encoding="utf-8").splitlines() if
                (r := json.loads(line))["run"] == args.run and r["seed"] == args.seed)
    with closing(NativeCore(args.core.resolve(), ROOT / "out")) as core:
        print(json.dumps(trace(core, receipt), separators=(",", ":")))


if __name__ == "__main__":
    main()
