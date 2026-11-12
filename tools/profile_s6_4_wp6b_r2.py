"""Run the frozen F1 application protocol with the added H1+H2 model."""

from pathlib import Path

import profile_s6_4_wp6b_r1 as assay


PROTOCOL = Path(__file__).resolve().parents[1] / "research/s6_4_wp6b_r2/FROZEN_R2_PROTOCOL.md"


if __name__ == "__main__":
    assay.PROTOCOL = PROTOCOL
    assay.MODEL_ARGUMENTS["both"] = (*assay.NOMINAL, 3)
    assay.MODEL_VERSIONS["both"] = 3
    assay.ADDITIONAL_SOURCES = (Path(__file__).name,)
    assay.main()
