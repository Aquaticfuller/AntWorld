"""Run the accepted WP-5 founding controls and check their original evidence bytes."""

import argparse
import json
from pathlib import Path
import subprocess
import tarfile
from tempfile import TemporaryDirectory

from run_s6_4_wp6b import ROOT, git, sha, write_json
from wp6a_budget_screen import PRIMARY_SEEDS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    controls = ROOT / "experiments/s6_4_wp5/baseline/raw"
    binary = args.binary.resolve(strict=True)
    matches = []
    for arm in ("on", "off"):
        for seed in PRIMARY_SEEDS:
            source = controls / f"founding-{arm}-0-{seed}"
            receipt = json.loads((source / "receipt.json").read_text())
            archive = source / "raw.tar.gz"
            if sha(archive) != receipt["archive_sha256"]:
                raise ValueError("the accepted historical archive changed")
            with TemporaryDirectory() as folder, tarfile.open(archive) as tar:
                output = Path(folder) / "control"
                result = subprocess.run([binary, output, "founding", arm, "0", str(seed)], capture_output=True, text=True)
                checked = {}
                for name in ("initial.chk", "final.chk", "canonical.bin"):
                    generated = output / name
                    checked[name] = dict(match=result.returncode == 0 and generated.read_bytes() == tar.extractfile(name).read(),
                                         sha256=sha(generated) if generated.exists() else None)
                matches.append(dict(arm=arm, seed=seed, exit_code=result.returncode, stdout=result.stdout,
                                    stderr=result.stderr, control_sha256=receipt["archive_sha256"], files=checked))
    success = all(all(file["match"] for file in row["files"].values()) for row in matches)
    write_json(args.out, dict(source=git("rev-parse", "HEAD"), binary_sha256=sha(binary), passed=success, cases=matches))
    print(f"{sum(all(v['match'] for v in r['files'].values()) for r in matches)}/12 exact WP-5 founding controls")
    return int(not success)


if __name__ == "__main__":
    raise SystemExit(main())
