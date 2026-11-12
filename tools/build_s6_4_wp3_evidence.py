"""Project the accepted foraging and recruitment source and parameter evidence."""

import argparse
import csv
import io

from build_s6_4_wp2_evidence import COMMON, FIELDS, ROOT, read


OUTPUT = ROOT / "research/s6_4_wp3/MECHANISM_TRANSITION_PARAMETER_MAP.csv"
SCOPES = {
    "BR-06": {"SEN-01", "SEN-02", "SEN-06", *(f"FOR-{i:02}" for i in range(1, 11))},
    "BR-07": {"SEN-03", "FOR-01", "FOR-02", "FOR-04", "FOR-05", *(f"PHE-{i:02}" for i in range(1, 6))},
}


def project(blocker, scope, kind, row):
    common = {key: row[key] for key in COMMON}
    if kind == "Parameter":
        owners = scope.intersection(row["MechanismIds"].split(";"))
        if not owners:
            return None
        identity, symbol, rule, unit = (row[key] for key in
            ("ParameterKey", "Declaration", "CurrentSourceValue", "Unit"))
        evidence, grade = row["ParameterEvidenceClass"], row["AtlasGrade"]
        calibration, gap = row["CalibrationApplicability"], row["CanCalibrateCurrentValue"]
    else:
        owners = scope.intersection((row["MechanismId"],))
        if not owners:
            return None
        identity, symbol, rule, unit = row[kind + "Id"], row["Function"], row["CurrentRuleOrGuard"], ""
        evidence, grade = row["MechanismEvidenceClassification"], row["CitedAtlasGrades"]
        calibration, gap = row["CanCalibrateCurrentRule"], row["ImplementationDifferenceAndUncertainty"]
    return dict(Package="RM-07" if blocker == "BR-06" else "RM-08", Blocker=blocker,
                RecordKind=kind, RecordId=identity, MechanismIds=";".join(sorted(owners)), **common,
                Symbol=symbol, RuleOrValue=rule, Unit=unit, EvidenceClass=evidence,
                AtlasGrade=grade, Calibration=calibration, Gap=gap)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, FIELDS, lineterminator="\n")
    writer.writeheader()
    covered = {kind: set() for kind in ("Mechanism", "Transition", "Parameter")}
    for kind in covered:
        table = read(f"INTEGRATED_{kind.upper()}_EVIDENCE")
        for blocker, scope in SCOPES.items():
            rows = [entry for row in table if (entry := project(blocker, scope, kind, row)) is not None]
            identities = {row["RecordId"] for row in rows}
            if len(identities) != len(rows) or (kind == "Mechanism" and identities != scope):
                raise ValueError(f"invalid projection for {blocker} {kind}")
            covered[kind].update(identities)
            writer.writerows(rows)
    totals = {kind: len(ids) for kind, ids in covered.items()}
    if totals != {"Mechanism": 19, "Transition": 19, "Parameter": 67}:
        raise ValueError(f"incomplete Batch 2 scope: {totals}")
    print(totals)
    data = stream.getvalue().encode("utf-8")
    if args.check:
        if OUTPUT.read_bytes() != data:
            raise ValueError("WP-3 evidence map differs from accepted inputs")
    else:
        OUTPUT.write_bytes(data)


if __name__ == "__main__":
    main()
