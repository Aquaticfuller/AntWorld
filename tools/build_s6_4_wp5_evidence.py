"""Produce the WP-5 projection of accepted mechanisms, transitions and parameters."""

import argparse
import csv
import io
from pathlib import Path

from read_s6_4_rm02_sidecar import require
from verify_s6_4_wp3 import rows, sequence


RESEARCH = Path(__file__).resolve().parents[1] / "research"
SOURCE = RESEARCH / "s6_4_preflight"
DEST = RESEARCH / "s6_4_wp5"
COHORT = {"NUT-02", "NUT-06", "NUT-08", "TSK-01", "TSK-05"} | {f"POP-{i:02}" for i in range(1, 7)} \
    | {f"PHY-{i:02}" for i in range(1, 6)} | {f"DEV-{i:02}" for i in range(1, 5)}
SOIL = {"SEN-01", "SEN-06", "TSK-03", "TSK-04"} | {f"NST-{i:02}" for i in range(1, 9)}


def projection():
    scopes = COHORT | SOIL
    mechanisms = sequence(rows(SOURCE / "INTEGRATED_MECHANISM_EVIDENCE.csv"), lambda r: r["MechanismId"])
    require(scopes <= mechanisms.keys(), "WP-5 references unknown mechanism")
    outputs = []

    def add(kind, identity, related, record):
        ids = ";".join(sorted(related))
        outputs.append(dict(kind=kind, identity=identity, mechanisms=ids,
                            scope="cohort_and_geometry" if related & COHORT and related & SOIL else
                            "cohort" if related & COHORT else "geometry",
                            source=record["SourceFile"], start=record["StartLine"], end=record["EndLine"],
                            source_anchors=record["SourceAnchorIds"], span_sha256=record["SourceSpanSha256"],
                            frozen_rule=record.get("CurrentRuleOrGuard", record.get("CurrentSourceValue", "")),
                            unit=record.get("Unit", ""), data_contexts=record["SourceContextIds"], doi=record["DOIs"],
                            classification=record.get("ParameterEvidenceClass", record.get("MechanismEvidenceClassification", "")),
                            atlas_grade=record.get("AtlasGrade", record.get("CitedAtlasGrades", "")),
                            measured_endpoint=record.get("MeasuredEndpointAndUnit", ""),
                            accepted_gap=record.get("ImplementationDifferenceAndUncertainty", record.get("ScientificBlockerBasis", ""))))

    for identity, r in sorted(mechanisms.items()):
        if identity in scopes:
            add("mechanism", identity, {identity}, r)
    for r in rows(SOURCE / "INTEGRATED_TRANSITION_EVIDENCE.csv"):
        if r["MechanismId"] in scopes:
            add("transition", r["TransitionId"], {r["MechanismId"]}, r)
    for r in rows(SOURCE / "INTEGRATED_PARAMETER_EVIDENCE.csv"):
        related = set(r["MechanismIds"].split(";")) & scopes
        if related:
            add("parameter", r["ParameterKey"], related, r)
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = projection()
    target = DEST / "SOURCE_MODEL_EVIDENCE.csv"
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, list(data[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(data)
    content = stream.getvalue().encode()
    if args.check:
        require(content == target.read_bytes(), "WP-5 evidence projection differs")
    else:
        target.write_bytes(content)
    closure = list(rows(DEST / "SCIENTIFIC_CLOSURE.csv"))
    require({r["BR"] for r in closure} == {f"BR-{i:02}" for i in range(1, 10)} and len(closure) == 9
            and all(r["BiologicalStatus"] == "BLOCKED" for r in closure), "WP-5 closure matrix altered an accepted gate")
    print(f"{len(data)} frozen source records and nine open scientific roots")


if __name__ == "__main__":
    main()
