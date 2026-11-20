"""Measure the Windows browser's wall-delivery workload without drawing or sleeping."""

from argparse import ArgumentParser
from collections import Counter
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from unittest.mock import patch

from op0 import DAY
from op0.codec import checkpoint
from op0.live import LiveSession, NativeCore


def measure(binary, scratch):
    request = "NEW_MOUTH_HANDOFF_NEST 9202 2 250 80 plugged 1955 reachable finite"
    calls, sizes, elapsed = Counter(), Counter(), Counter()
    with TemporaryDirectory(dir=scratch) as folder, closing(NativeCore(binary, Path(folder))) as core:
        session = LiveSession(binary, Path(folder))
        session.worker = core
        native_call = core.call

        def timed(command):
            name = command.split()[0]
            start = perf_counter()
            reply = native_call(command)
            elapsed[name] += perf_counter() - start
            calls[name] += 1
            sizes[name] += len(reply)
            return reply

        session.install(native_call(request), running=False)
        session.start_seek("wall-delivery", "next")
        with patch.object(core, "call", timed):
            start = perf_counter()
            while session.seeking() and session.frame["time_ms"] < 150 * DAY:
                session.advance()
            duration = perf_counter() - start
        if session.fast_forward["state"] != "reached":
            raise ValueError(f"The native search ended without a wall handoff: {session.fast_forward}")
        raw = native_call("FRAME")
        cut = checkpoint(raw)
        trace = sha256()
        for after in range(0, cut["cursor"], 512):
            trace.update(native_call(f"FACTS_AFTER {after} 512"))
        if native_call("CHECK_LEDGERS"):
            raise ValueError("Unexpected budget response")
        return dict(request=request, core_sha256=sha256(binary.read_bytes()).hexdigest(),
                    event=session.fast_forward["event"], cursor=cut["cursor"],
                    frame_sha256=sha256(raw).hexdigest(), canonical_sha256=trace.hexdigest(),
                    seconds=duration, calls=dict(calls), reply_bytes=dict(sizes), native_seconds=dict(elapsed))


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--scratch", type=Path, default=Path("out"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.scratch.mkdir(parents=True, exist_ok=True)
    rows = [measure(binary.resolve(), args.scratch) for binary in (args.reference, args.candidate)]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(dict(reference=rows[0], candidate=rows[1]), indent=2) + "\n", encoding="utf-8")
    if any(rows[0][key] != rows[1][key] for key in
           ("request", "event", "cursor", "frame_sha256", "canonical_sha256", "calls", "reply_bytes")):
        raise ValueError("The measurement changed the observed event, complete state, journal or read workload")
    print(f"Event {rows[0]['event']['id']}, {rows[0]['cursor']} facts. "
          f"Reference {rows[0]['seconds']:.2f} s, candidate {rows[1]['seconds']:.2f} s.")


if __name__ == "__main__":
    main()
