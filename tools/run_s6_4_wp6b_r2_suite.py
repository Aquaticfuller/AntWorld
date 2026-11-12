"""Run and verify every R2 arm on a single Release executable."""

import argparse
from pathlib import Path
import subprocess
import sys

from run_s6_4_wp6b_r2 import MASKS, REFERENCES, ROOT


def run_tool(name, *args):
    subprocess.run([sys.executable, ROOT / "tools" / (name + ".py"), *args], cwd=ROOT, check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("binary", "compiler", "out", "scratch"):
        parser.add_argument("--" + name, type=lambda p: Path(p).resolve(), required=True)
    args = parser.parse_args()
    for model in (*MASKS, *REFERENCES):
        run_tool("run_s6_4_wp6b_r2", "--model", model, "--binary", args.binary, "--compiler", args.compiler,
                 "--out", args.out / model, "--scratch", args.scratch)
    for model in (*MASKS, *REFERENCES):
        run_tool("verify_s6_4_wp6b_r2", args.out / model, "--out", args.out / f"{model}-analysis")
        if model in MASKS:
            run_tool("trace_s6_4_wp6b_r2", args.out / model, args.out / f"{model}-tracks")
    run_tool("check_s6_4_wp6b_r2_recovery", "--archive", args.out, "--binary", args.binary,
             "--scratch", args.scratch, "--out", args.out / "recovery.json")
    run_tool("summarize_s6_4_wp6b_r2", args.out, args.out / "comparison")
