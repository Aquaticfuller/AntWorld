"""Recompute the RM-02 R1 diagnostic tables from the published frozen cases."""

import gzip
import hashlib
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from read_s6_4_rm02_sidecar import require


TOOLS = Path(__file__).resolve().parent
ARCHIVE = TOOLS.parent / "experiments/s6_4_rm02_r1"


def payload_hash(path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    raw, original, diagnosis = (ARCHIVE / part for part in ("baseline", "analysis", "diagnosis"))
    with TemporaryDirectory() as temporary:
        regenerated = Path(temporary) / "analysis"
        subprocess.run([sys.executable, TOOLS / "analyze_s6_4_rm02.py", raw, regenerated], check=True)
        names = {file.name for file in regenerated.iterdir()}
        require(names == {file.name for file in original.iterdir()}, "analysis output set differs")
        for name in sorted(names):
            require(payload_hash(regenerated / name) == payload_hash(original / name), f"analysis differs: {name}")
        subprocess.run([sys.executable, TOOLS / "summarize_s6_4_rm02_r1.py",
                        raw, regenerated, diagnosis, "--check"], check=True)
    print(f"Reproduced {len(names)} analysis files and the R1 diagnostic summaries")


if __name__ == "__main__":
    main()
