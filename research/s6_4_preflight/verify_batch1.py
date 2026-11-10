#!/usr/bin/env python3
"""Verify the first full-text review and reproduce its archived reference summaries."""

import csv
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import fmean, stdev
from urllib.parse import unquote, urlsplit


REVIEW = Path(__file__).resolve().parent
ROOT = REVIEW.parents[1]
LITERATURE = ROOT / "experiments/s6_3_3/literature"
CLASSES = {
    "DIRECT_SPECIES_DATA", "CROSS_SPECIES_EXTRAPOLATION", "MODELING_ASSUMPTION", "ENGINEERING_FIXTURE",
}
BATCH_MECHANISMS = {
    "SEN-04", "SEN-05", "POP-02", "POP-04",
    *(f"{domain}-{index:02}" for domain, size in
      (("CAR", 12), ("NUT", 8), ("DEV", 4), ("PHY", 5), ("SYS", 6))
      for index in range(1, size + 1)),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        for line, row in enumerate(reader, 2):
            require(None not in row and None not in row.values(), f"{path.name}:{line} has mismatched columns")
            yield {key.strip(): value for key, value in row.items()}


def index(records, key):
    result = {}
    for row in records:
        identity = row[key]
        require(identity and identity not in result, f"Blank or duplicate {key} {identity}")
        result[identity] = row
    return result


def list_field(value):
    return value.split(";") if value else []


def verify_sources():
    sources = index(rows(REVIEW / "SOURCE_FULLTEXT_REGISTER.csv"), "SourceId")
    log = index(rows(REVIEW / "SOURCE_ACCESS_AND_READING_LOG.csv"), "AccessId")
    body_reads = set()
    for rid, entry in log.items():
        require(entry["SourceId"] in sources and entry["AccessRoute"] and entry["ReadingScope"], f"{rid}: incomplete access record")
        outcome = entry["AccessOutcome"]
        read = entry["ActuallyRead"] == "YES_SELECTED_SECTIONS"
        require(read == (outcome in {"READ_FULL_ARTICLE_SECTIONS", "READ_SUPPLEMENT_SECTIONS"}),
                f"{rid}: reading claim conflicts with access outcome")
        digest = entry["SourceSha256"]
        require(not digest or re.fullmatch(r"[0-9a-f]{64}", digest), f"{rid}: malformed source hash")
        if outcome == "READ_FULL_ARTICLE_SECTIONS":
            require(entry["MaterialKind"] == "ORIGINAL_ARTICLE", f"{rid}: invalid primary article record")
            body_reads.add(entry["SourceId"])

    require(body_reads == sources.keys(), "Source register has an article without a current body-reading entry")
    paper_ids = {source["PaperId"] for source in sources.values()}
    require(len(sources) == 14 and len(paper_ids) == 13, "First-batch source count changed")
    doi_to_paper = {}
    for sid, source in sources.items():
        require(all(source.values()), f"{sid}: required source metadata is blank")
        paper, doi = source["PaperId"], source["DOI"]
        require(paper in sources and doi == sources[paper]["DOI"], f"{sid}: assay context lost its parent paper")
        require(re.fullmatch(r"10\.\d{4,9}/\S+", doi) or (sid == "R1L" and doi == "NOT_FOUND"), f"{sid}: invalid DOI")
        require(doi_to_paper.setdefault(doi.casefold(), paper) == paper, f"{sid}: duplicate paper identity")
        require(source["EvidenceClassification"] in CLASSES and source["AtlasGrade"] in set("ABCDEF"),
                f"{sid}: invalid evidence tags")
        require(source["FullTextActuallyRead"] == "YES_SELECTED_SECTIONS", f"{sid}: reading scope drift")
    congener = sources["B07-X"]
    require(congener["ActualExperimentalSpecies"] == "Lasius neoniger" and congener["AtlasGrade"] == "C"
            and congener["EvidenceClassification"] == "CROSS_SPECIES_EXTRAPOLATION", "Congener tracer evidence conflated with L. niger")
    return sources, len(log)


def verify_citations(record, identity, sources, conflicts):
    source_ids = list_field(record["SourceIds"])
    require(set(source_ids) <= sources.keys(), f"{identity}: unknown source ID")
    expected_grades = [f"{sid}={sources[sid]['AtlasGrade']}" for sid in source_ids]
    require(list_field(record["AtlasSourceGrades"]) == expected_grades, f"{identity}: source grade drift")
    cited = set(re.findall(r"(?:^| \| )([\w-]+): \S", record["EvidenceLocators"]))
    require(cited == set(source_ids), f"{identity}: missing source or locator")
    require(set(list_field(record["ConflictIds"])) <= conflicts, f"{identity}: unknown conflict ID")
    return [sources[sid]["EvidenceClassification"] for sid in source_ids]


def verify_review(sources, conflicts):
    inventory = index(rows(REVIEW / "CURRENT_CORE_MECHANISM_INVENTORY.csv"), "MechanismId")
    state_machine = index(rows(REVIEW / "STATE_MACHINE_TRANSITION_EVIDENCE.csv"), "TransitionId")
    matrix = index(rows(REVIEW / "PARAMETER_EVIDENCE_MATRIX.csv"), "ParameterKey")
    anchors = index(rows(REVIEW / "SOURCE_ANCHORS.csv"), "AnchorId")
    require(BATCH_MECHANISMS <= inventory.keys(), "Batch 1 scope contains unknown mechanisms")
    review = list(rows(REVIEW / "MECHANISM_EVIDENCE_REVIEW.csv"))
    require(all(row["RecordKind"] in {"MECHANISM", "TRANSITION"} for row in review), "Unexpected review record kind")
    mechanisms = index((row for row in review if row["RecordKind"] == "MECHANISM"), "MechanismId")
    transitions = index((row for row in review if row["RecordKind"] == "TRANSITION"), "TransitionId")
    require(mechanisms.keys() == BATCH_MECHANISMS, "Batch 1 mechanism coverage drift")
    require(transitions.keys() == {key for key, row in state_machine.items() if row["MechanismId"] in BATCH_MECHANISMS},
            "Batch 1 transition coverage drift")

    for row in review:
        mid, tid = row["MechanismId"], row["TransitionId"]
        identity = tid or mid
        require(bool(tid) == (row["RecordKind"] == "TRANSITION"), f"{identity}: wrong transition identity")
        frozen = state_machine[tid] if tid else inventory[mid]
        require(frozen["MechanismId"] == mid and row["Domain"] == inventory[mid]["Domain"], f"{identity}: wrong owning mechanism")
        if tid:
            element = f"{frozen['FromState']} -> {frozen['ToState']}"
            rule = ". ".join(frozen[field] for field in ("Trigger", "GuardOrAlternate", "ActionAndNextWake"))
        else:
            element, rule = frozen["Mechanism"], frozen["SourceRule"]
        require(row["CodeElement"] == element and row["CurrentRuleOrGuard"] == rule, f"{identity}: frozen rule description drift")
        ids = list_field(row["SourceAnchorIds"])
        require(ids and row["SourceAnchorIds"] == frozen["SourceAnchorIds"], f"{identity}: changed frozen anchors")
        require(all(anchors[aid]["RecordId"] == identity for aid in ids), f"{identity}: anchor belongs to another rule")
        source_classes = verify_citations(row, identity, sources, conflicts)
        classification = row["EvidenceClassification"]
        require(classification in CLASSES, f"{identity}: invalid claim classification")
        if classification in {"DIRECT_SPECIES_DATA", "CROSS_SPECIES_EXTRAPOLATION"}:
            require(classification in source_classes, f"{identity}: claim has no matching kind of biological source")
        require(all(row[field] for field in ("MeasuredEndpointAndUnit", "RuleAssessment", "UnsupportedImplementationOrGap")),
                f"{identity}: missing endpoint or assessment")

    parameters = index(rows(REVIEW / "PARAMETER_EVIDENCE_REVIEW.csv"), "ParameterKey")
    expected = {key for key, row in matrix.items() if BATCH_MECHANISMS.intersection(list_field(row["MechanismIds"]))}
    require(parameters.keys() == expected, "Batch 1 parameter coverage drift")
    for key, row in parameters.items():
        frozen = matrix[key]
        for field in ("MechanismIds", "SourceFile", "StartLine", "EndLine", "SourceSpanSha256", "SourceAnchorIds",
                      "SourceExpression", "CurrentSourceValue", "Unit", "ValueRoleClass", "ParameterEvidenceClass"):
            require(row[field] == frozen[field], f"{key}: changed {field} from frozen matrix")
        require(set(list_field(row["Batch1MechanismIds"])) == BATCH_MECHANISMS.intersection(list_field(row["MechanismIds"])),
                f"{key}: changed batch mechanism links")
        require(set(list_field(row["SourceAnchorIds"])) <= anchors.keys(), f"{key}: missing source anchor")
        require(row["AtlasParameterGrade"] == frozen["AtlasGrade"] == "F" and row["ParameterEvidenceClass"] == "ENGINEERING_FIXTURE",
                f"{key}: provenance changed without calibration")
        require(row["CanCalibrateCurrentValue"] in {"NO", "NOT_APPLICABLE"}, f"{key}: unexpected calibration claim")
        if row["CanCalibrateCurrentValue"] == "NOT_APPLICABLE":
            # The frozen inventory includes scene geometry in MODEL_SETTING.
            require(row["ValueRoleClass"] != "MODEL_SETTING" or key in {"WorldConfig.min_m", "WorldConfig.max_m"},
                    f"{key}: model setting excluded from biological review")
        require(all(row[field] for field in ("EndpointMatch", "UnitConversionAndSourceDifference", "CalibrationAssessment")),
                f"{key}: missing parameter assessment")
        verify_citations(row, key, sources, conflicts)
    return len(mechanisms), len(transitions), len(parameters)


def verify_b01():
    values = defaultdict(dict)
    for row in rows(LITERATURE / "Reversibility_of_worker_effect_3_days.csv"):
        key = row["Treatment"], int(row["Time"])
        require(int(row["Scans"]) == 50, f"B01 raw scan denominator changed for {key}")
        label = row["Box_label"]
        require(label not in values[key], f"B01 duplicated queen {label} in {key}")
        values[key][label] = 100 * int(row["Nursing"]) / int(row["Scans"])
    focal = (("Without_workers", 24), ("With_workers", 24), ("Workers_removed", 48))
    summaries = []
    for key, mean, sd in zip(focal, (6.500, 0.125, 6.250), (7.248, 0.500, 9.849)):
        group = values[key].values()
        require(len(group) == 16, f"B01 raw unit count changed for {key}")
        require(round(fmean(group), 3) == mean and round(stdev(group), 3) == sd, f"B01 reference drift for {key}")
        summaries.append(f"{mean:.3f}% (SD {sd:.3f} pp)")
    return ", ".join(summaries)


def verify_b02():
    pairings = defaultdict(dict)
    fields = ("brood items after 10min", "first contact", "first retrieving")
    for row in rows(LITERATURE / "B02_retrieval.csv"):
        unit = row["qw"], row["queen"]
        origin = row["same"]
        require(origin in {"0", "1"} and origin not in pairings[unit], f"B02 invalid origin pair {unit}")
        pairings[unit][origin] = tuple(float(row[field]) for field in fields)
    counts = Counter(group for group, _ in pairings)
    require(counts == {"q": 79, "w": 70, "w2": 50}, "B02 raw cohort sizes changed")
    require(all(origins.keys() == {"0", "1"} for origins in pairings.values()), "B02 missing origin pairing")
    matched = {colony for group, colony in pairings if group == "q" and ("w", colony) in pairings}
    require(len(matched) == 67, "B02 queen/first-worker matched count changed")
    results = []
    for group, expected_mean, expected_sd in (
        ("q", (3.772, 94.374, 212.788), (2.069, 114.962, 188.778)),
        ("w", (4.850, 40.512, 128.370), (1.768, 58.102, 142.557)),
    ):
        samples = [tuple(map(fmean, zip(origins["0"], origins["1"])))
                   for (category, _), origins in pairings.items() if category == group]
        # The archived raw 600 s markers are included, not treated as observed event times.
        means = tuple(round(fmean(values), 3) for values in zip(*samples))
        sds = tuple(round(stdev(values), 3) for values in zip(*samples))
        require((means, sds) == (expected_mean, expected_sd), f"B02 summary drift for {group}")
        results.append(str(means))
    return " / ".join(results)


def verify_carthy():
    path = ROOT / "experiments/s6_3_3_2/literature/carthy_loaded_returns.csv"
    records = [row for row in rows(path) if row["condition"] == "normal" and row["status"] == "TIMED"]
    require(len(records) == 12 and {row["individual"] for row in records} == {"17", "27"}, "Carthy retained runs changed")
    rates = [float(row["distance_in"]) * 25.4 / float(row["time_s"]) for row in records]
    limits = round(min(rates), 2), round(max(rates), 2)
    require(limits == (11.75, 29.89), "Carthy derived loaded path rates drifted")
    require(math.isclose(6.15 * 20.1 / 3.6, 34.3375) and math.isclose(0.99 * 20.1 / 3.6, 5.5275),
            "Conditional oxygen-to-power arithmetic drifted")
    require(round(5643.4 / 342.2965, 2) == 16.49, "Sucrose combustion arithmetic drifted")
    return f"{limits[0]:.2f}–{limits[1]:.2f} mm/s"


def verify_links():
    for name in ("README.md", "FULLTEXT_REVIEW_PROGRESS.md", "EVIDENCE_CONFLICTS.md"):
        document = REVIEW / name
        for link in re.findall(r"\]\(([^)\s]+)\)", document.read_text(encoding="utf-8")):
            parsed = urlsplit(link)
            if parsed.scheme:
                require(parsed.scheme == "https", f"{name}: unexpected link scheme for {link}")
                continue
            target = (document.parent / unquote(parsed.path)) if parsed.path else document
            require(target.exists(), f"{name}: broken relative link to {link}")
            if parsed.fragment and target.suffix == ".md":
                headings = re.findall(r"^#+ (.+)$", target.read_text(encoding="utf-8"), re.MULTILINE)
                slugs = {re.sub(r"[^\w -]", "", heading.lower()).replace(" ", "-") for heading in headings}
                require(parsed.fragment in slugs, f"{name}: missing heading at {link}")


def main():
    sources, access_count = verify_sources()
    conflicts = set(re.findall(r"^## (B1-C\d{2})\b", (REVIEW / "EVIDENCE_CONFLICTS.md").read_text(encoding="utf-8"), re.MULTILINE))
    require(len(conflicts) == 11, "First-batch conflict register changed")
    mechanisms, transitions, parameters = verify_review(sources, conflicts)
    verify_links()
    print(f"PASS: {len(sources)} source contexts, {access_count} access records, {len(conflicts)} conflicts and document links")
    print(f"PASS: {mechanisms} mechanisms, {transitions} transitions, {parameters} parameters linked to the frozen inventory")
    print(f"PASS: B01 per-queen focal means: {verify_b01()}")
    print(f"PASS: B02 unit means (count, contact s, marker s), queen / first-worker trio: {verify_b02()}")
    print(f"PASS: Carthy retained path range {verify_carthy()}; oxygen and combustion conversions")


if __name__ == "__main__":
    main()
