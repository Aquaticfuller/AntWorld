"""Run and verify every R2 arm on a single Release executable."""

import argparse
from pathlib import Path
import subprocess
import sys

from run_s6_4_wp6b_r2 import MASKS, REFERENCES, ROOT
from run_s6_4_wp6b import write_json


def run_tool(name, *args):
    return subprocess.run([sys.executable, ROOT / "tools" / (name + ".py"), *args], cwd=ROOT).returncode


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("binary", "compiler", "out", "scratch"):
        parser.add_argument("--" + name, type=lambda p: Path(p).resolve(), required=True)
    args = parser.parse_args()
    exits = {}
    for model in (*MASKS, *REFERENCES):
        exits[f"collect/{model}"] = run_tool("run_s6_4_wp6b_r2", "--model", model, "--binary", args.binary,
                                             "--compiler", args.compiler, "--out", args.out / model, "--scratch", args.scratch)
    for model in (*MASKS, *REFERENCES):
        exits[f"verify/{model}"] = run_tool("verify_s6_4_wp6b_r2", args.out / model, "--out", args.out / f"{model}-analysis")
        if model in MASKS:
            exits[f"trace/{model}"] = run_tool("trace_s6_4_wp6b_r2", args.out / model, args.out / f"{model}-tracks")
    exits["recovery"] = run_tool("check_s6_4_wp6b_r2_recovery", "--archive", args.out, "--binary", args.binary,
                                "--scratch", args.scratch, "--out", args.out / "recovery.json")
    if not any(exits.values()):
        exits["comparison"] = run_tool("summarize_s6_4_wp6b_r2", args.out, args.out / "comparison")
    write_json(args.out / "suite_receipt.json", dict(exit_codes=exits))
    raise SystemExit(int(any(exits.values())))
