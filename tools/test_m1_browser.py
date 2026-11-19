"""Run the observatory's real Chromium test with a private loopback Core session."""

from argparse import ArgumentParser
import json
import os
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory
from threading import Thread
from time import process_time

from op0.cli import M1_DEMOS
from op0.index import Catalog
from op0.live import LiveSession, ROOT, core_path
from op0.query import ReadAPI
from op0.server import bind
from tools.run_m1_habitat import cpu_seconds


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, default=core_path())
    parser.add_argument("--browser", type=Path, required=True)
    parser.add_argument("--scratch", type=Path, default=ROOT / "out")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--node", default="node")
    parser.add_argument("--mode", default="m1", choices=("m1", "m2", "overhaul", "live", "habitat", "nursery",
                                                        "ecology", "m1-witnesses", "m1-soak"))
    args = parser.parse_args()
    args.scratch.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=args.scratch, prefix="m1-browser-") as scratch:
        work = Path(scratch).resolve()
        catalog = Catalog(work / "index")
        if args.mode == "m1-witnesses":
            from tools.verify_m1_habitat import read_jsonl
            manifest = {row["archive"]: row["sha256"] for row in read_jsonl(M1_DEMOS[0][0] / "archives.jsonl")}
            for folder, name, title, description in M1_DEMOS:
                catalog.register(folder / name, title, manifest[name], description)
        app = ReadAPI(catalog)
        environment = os.environ.copy()
        if os.name == "nt":
            environment.update(TMPDIR=str(work), TEMP=str(work), TMP=str(work))
        with LiveSession(args.core, work / "saves") as live, bind(app, 0, None if args.mode == "m1-witnesses" else live) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            started = process_time()
            try:
                run([args.node, str(ROOT / "op0/tests/browser_smoke.mjs"), str(args.browser.absolute()),
                     f"http://127.0.0.1:{server.server_port}", str(args.output.resolve()), args.mode],
                    cwd=ROOT, env=environment, check=True, timeout=360)
                if args.mode == "m1-soak":
                    core = live.worker
                    with live.lock:
                        sample = dict(history_storage=list(map(int, core.call("HISTORY_STORAGE").split())),
                                      memory_bytes=list(map(int, core.call("MEMORY").split())),
                                      native_process_cpu_seconds=cpu_seconds(core.process.pid),
                                      host_process_cpu_seconds=round(process_time() - started, 6),
                                      persisted_save_bytes=sum(p.stat().st_size for p in live.saves.glob("*.sqlite")))
                    path = args.output / "m1-soak-receipt.json"
                    report = json.loads(path.read_bytes()) | sample
                    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            finally:
                server.shutdown()
                thread.join()


if __name__ == "__main__":
    main()
