"""Reproduce the observed motility-assay queen death at adjacent native state cuts."""

from argparse import ArgumentParser
from contextlib import closing
import gzip
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from op0 import DAY
from op0.archive import file_hash, json_bytes
from op0.codec import checkpoint, require
from op0.live import NativeCore
from tools.run_r0_diagnostics import journal, mass_columns
from tools.run_r0_r1 import HOUR, Witness


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path, help="Completed R0-r1 candidate long-run diagnostic")
    parser.add_argument("core", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    with gzip.open(args.original, "rt", encoding="utf-8") as f:
        original = json.load(f)
    receipt = original["receipt"]
    death = next(row for row in original["deaths"] if row["role"] == "queen")
    queen, when = death["ant"], death["time_ms"]
    before = when // DAY * DAY
    cuts = (before, when-HOUR, when-1, when, before+DAY)
    packets, snapshots = [], []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with (TemporaryDirectory(dir=args.output.parent) as scratch,
          closing(NativeCore(args.core.resolve(strict=True), scratch)) as core):
        state = checkpoint(core.call(receipt["command"]))
        for day in range(1,before//DAY):
            core.call(f"ADVANCE_STEP {day*DAY}")
        cursor = state["cursor"]
        witness = Witness(None)
        for index, at in enumerate(cuts):
            raw = core.call(f"ADVANCE {at}")
            state = checkpoint(raw)
            for event in journal(core,cursor,state["cursor"],witness):
                if index and (event.actor == queen or event.related == queen or event.kind in (5,12,37)):
                    packets.append(event.packet())
            snapshots.append(dict(time_ms=at,cursor=state["cursor"],queen=state["ants"][queen],
                                  state_sha256=sha256(raw).hexdigest(),
                                  **mass_columns("depot",state["stored"]),**mass_columns("external",state["available"])))
            cursor = state["cursor"]
            core.call("CHECK_LEDGERS")
    require(any(e["kind"]=="AntDied" and int(e["id"])==death["event_id"] and e["time_ms"]==when for e in packets),
            "Native run did not reproduce the archived death")
    require(cursor==original["census"][before//DAY+1]["facts"], "Final daily cursor changed")
    with gzip.open(args.output,"xb",compresslevel=4) as f:
        f.write(json_bytes(dict(command=receipt["command"],original_sha256=file_hash(args.original),
                               binary_sha256=file_hash(args.core),death=death,cuts=snapshots,facts=packets)))
    print(f"Verified death {death['event_id']} at {when} ms and following cut {cursor}")


if __name__=="__main__":
    main()
