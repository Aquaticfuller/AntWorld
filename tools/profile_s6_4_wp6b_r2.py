"""Run the frozen F1 application protocol with the added H1+H2 model."""

from pathlib import Path
import shutil
import time

import profile_s6_4_wp6b_r1 as assay
from run_s6_4_wp6b import ROOT, sha


PROTOCOL = Path(__file__).resolve().parents[1] / "research/s6_4_wp6b_r2/FROZEN_R2_PROTOCOL.md"
PREVIOUS = ROOT / "experiments/s6_4_wp6b_r2/performance/application"


def carry_prior_admission(args):
    native = assay.native
    session = PREVIOUS / "session1"
    source = session / "admission1_receipt.json"
    previous = native.load(source)
    frozen = native.load(PREVIOUS / "freeze.json")
    stop = native.load(PREVIOUS / "batch_result.json")
    assert previous["attempt"] == 1 and not previous["admitted"]
    assert not any(PREVIOUS.glob("session*/samples.csv")) and not stop["completed"]
    attempt = {"receipt_sha256": sha(source), "samples_sha256": sha(session / "admission1.csv")}
    destination = args.out / "session1"
    if args.prepare:
        assay.prepare(args)
        filename = args.out / "freeze.json"
        freeze = native.load(filename)
        assert all(freeze[k] == frozen[k] for k in ("cpp_tree", "binary_sha256", "schedules", "protocol_sha256"))
        for name in ("admission1_receipt.json", "admission1.csv"):
            shutil.copyfile(session / name, destination / name)
        native.save(filename, freeze | {"prior_first_admission": attempt})
    else:
        freeze = native.load(args.out / "freeze.json")
        assert freeze["prior_first_admission"] == attempt
        assert sha(destination / source.name) == attempt["receipt_sha256"]
        assert sha(destination / "admission1.csv") == attempt["samples_sha256"]
        assert time.time_ns() - previous["ended_utc_ns"] >= 300_000_000_000
        assay.run(args, first_attempt=2)


def main():
    assay.PROTOCOL = PROTOCOL
    assay.MODEL_ARGUMENTS["both"] = (*assay.NOMINAL, 3)
    assay.MODEL_VERSIONS["both"] = 3
    assay.ADDITIONAL_SOURCES = (Path(__file__).name, "run_s6_4_wp6b_r2_performance.py")
    if "s6_4_wp6b_r2_append_log.py" in assay.native.dependencies():
        assay.main(on_prepare=carry_prior_admission, on_run=carry_prior_admission)
    else:
        assay.main()


if __name__ == "__main__":
    main()
