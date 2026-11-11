"""Independently decode and reconcile a closed RM-02 assay directory."""

import argparse
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory

from analyze_s6_4_rm02 import Output, Trace, get_row
from read_s6_4_rm02_sidecar import open_sidecar, require
from run_s6_4_rm02 import sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("assay", type=Path)
    args = parser.parse_args()
    root = args.assay
    config = get_row(root / "configuration.csv")
    summary = get_row(root / "summary.csv")
    case = dict(case=config["lineage"], mode=config["mode"], arm=config["arm"],
                workers=int(config["workers"]), seed=int(config["seed"]))
    require(summary["status"] == "ENGINEERING_PASS" and summary["observer_complete"] == summary["rejoined"]
            == summary["exact_off"] == "1", "assay receipt was not exact")
    require(sha256(root / "initial.chk") == config["initial_sha256"], "initial checkpoint digest mismatch")
    with (open_sidecar(root / "observer.sqlite") as (manifest, cuts),
          TemporaryDirectory() as scratch, ExitStack() as stack):
        require(manifest["world_id"] == config["world_id"] and manifest["seed"] == case["seed"]
                and manifest["lineage"] == case["case"] and not manifest["origin"], "manifest mismatch")
        trace = Trace(case, config, manifest, Output(Path(scratch), stack))
        tail = None
        for tail in cuts:
            trace.cut(tail)
        require(tail is not None and tail["cursor"] == int(summary["events"])
                and tail["time"] == int(config["horizon_ms"]) and not trace.coverage["lost"]
                and trace.coverage["examined"] == tail["cursor"], "incomplete closed sidecar")
        require(manifest["anchors"].get(tail["seq"]) == summary["checkpoint_sha256"] == sha256(root / "final.chk"),
                "sidecar anchor does not match the authoritative checkpoint")
        trace.finish(tail["time"])
        print(f"{tail['seq']} cuts, {tail['cursor']} examined, {trace.coverage['crop_checks']} reconciled crop states, "
              f"{trace.net['NutritionTransferred']} scoped actual gifts")


if __name__ == "__main__":
    main()
