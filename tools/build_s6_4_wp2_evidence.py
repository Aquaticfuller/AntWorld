"""Project the accepted BR-03 and BR-05 source and parameter evidence."""

import argparse
import csv
import io
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACCEPTED = ROOT / "research/s6_4_preflight"
OUTPUT = ROOT / "research/s6_4_wp2/MECHANISM_TRANSITION_PARAMETER_MAP.csv"
BLOCKERS = {"BR-03": "RM-06", "BR-05": "RM-03"}
COMMON = ("SourceFile", "StartLine", "EndLine", "SourceSpanSha256", "SourceAnchorIds",
          "SourceContextIds", "DOIs", "CitedAtlasGrades", "ScientificBlockerStatus")
FIELDS = ("Package", "Blocker", "RecordKind", "RecordId", "MechanismIds", *COMMON,
          "Symbol", "RuleOrValue", "Unit", "EvidenceClass", "AtlasGrade", "Calibration", "Gap")


def read(name):
    with (ACCEPTED / (name + ".csv")).open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def project(block, scope, kind, rows):
    for row in rows:
        if kind == "Parameter":
            owners = scope.intersection(row["MechanismIds"].split(";"))
            if not owners:
                continue
            identity, symbol = row["ParameterKey"], row["Declaration"]
            rule, unit = row["CurrentSourceValue"], row["Unit"]
            evidence, grade, calibration = (row["ParameterEvidenceClass"], row["AtlasGrade"],
                                            row["CalibrationApplicability"])
            gap = row["CanCalibrateCurrentValue"]
        else:
            owners = scope.intersection((row["MechanismId"],))
            if not owners:
                continue
            identity = row["TransitionId"] if kind == "Transition" else row["MechanismId"]
            symbol, rule, unit = row["Function"], row["CurrentRuleOrGuard"], ""
            evidence, grade = row["MechanismEvidenceClassification"], row["CitedAtlasGrades"]
            calibration = row["CanCalibrateCurrentRule"]
            gap = row["ImplementationDifferenceAndUncertainty"]
        yield dict(Package=BLOCKERS[block], Blocker=block, RecordKind=kind, RecordId=identity,
                   MechanismIds=";".join(sorted(owners)), **{key: row[key] for key in COMMON},
                   Symbol=symbol, RuleOrValue=rule, Unit=unit, EvidenceClass=evidence,
                   AtlasGrade=grade, Calibration=calibration, Gap=gap)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    accepted = {r["BlockerId"]: r for r in read("S6_4_PHASE2_BLOCKER_REGISTER")}
    tables = [(kind, read(f"INTEGRATED_{kind.upper()}_EVIDENCE"))
              for kind in ("Mechanism", "Transition", "Parameter")]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, FIELDS, lineterminator="\n")
    writer.writeheader()
    for block in BLOCKERS:
        row = accepted[block]
        scope = set((row["PrimaryMechanismIds"] + ";" + row["SupportingMechanismIds"]).split(";"))
        counts = {}
        for kind, table in tables:
            records = list(project(block, scope, kind, table))
            identities = {r["RecordId"] for r in records}
            if len(identities) != len(records) or not records or (kind == "Mechanism" and identities != scope):
                raise ValueError(f"invalid {block} {kind} projection")
            counts[kind] = len(records)
            writer.writerows(records)
        print(block, counts)
    data = stream.getvalue().encode("utf-8")
    if args.check:
        if OUTPUT.read_bytes() != data:
            raise ValueError("WP-2 evidence projection differs from its accepted inputs")
    else:
        OUTPUT.write_bytes(data)


if __name__ == "__main__":
    main()
