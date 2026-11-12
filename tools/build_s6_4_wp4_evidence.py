"""Project the accepted BR-01 and BR-04 evidence without changing its classification."""

import argparse
import csv
import io

import build_s6_4_wp2_evidence as projection


OUTPUT = projection.ROOT / "research/s6_4_wp4/MECHANISM_TRANSITION_PARAMETER_MAP.csv"
PACKAGES = {"BR-01": "RM-04", "BR-04": "RM-05"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    blockers = {row["BlockerId"]: row for row in projection.read("S6_4_PHASE2_BLOCKER_REGISTER")}
    tables = [(kind, projection.read(f"INTEGRATED_{kind.upper()}_EVIDENCE"))
              for kind in ("Mechanism", "Transition", "Parameter")]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, projection.FIELDS, lineterminator="\n")
    writer.writeheader()
    for blocker, package in PACKAGES.items():
        row = blockers[blocker]
        scope = set((row["PrimaryMechanismIds"] + ";" + row["SupportingMechanismIds"]).split(";"))
        counts = {}
        for kind, table in tables:
            # The projection function uses the label as metadata. Its scope and evidence
            # are supplied by the accepted blocker register and integrated source table.
            rows = list(projection.project("BR-03", scope, kind, table))
            identities = {entry["RecordId"] for entry in rows}
            if len(identities) != len(rows) or not rows or (kind == "Mechanism" and identities != scope):
                raise ValueError(f"incomplete {blocker} {kind} projection")
            writer.writerows(dict(entry, Blocker=blocker, Package=package) for entry in rows)
            counts[kind] = len(rows)
        print(blocker, counts)
    data = stream.getvalue().encode("utf-8")
    if args.check:
        if OUTPUT.read_bytes() != data:
            raise ValueError("WP-4 evidence map differs from accepted inputs")
    else:
        OUTPUT.write_bytes(data)


if __name__ == "__main__":
    main()
