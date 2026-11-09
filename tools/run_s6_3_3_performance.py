"""Use the unchanged qualified runner/admission/schedule with pre-frozen S6.3.3 binaries."""
import json
from pathlib import Path
import run_s6_3_2_performance as runner
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    runner.HASHES=json.loads((ROOT/'experiments/s6_3_3/performance_manifest.json').read_text())['binary_sha256']
    runner.main()
