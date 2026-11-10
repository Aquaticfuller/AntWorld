#!/usr/bin/env python3
"""Verify the first full-text review and reproduce its archived reference summaries."""

import argparse
import csv
import io
import math
import re
from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
from statistics import fmean, stdev
from urllib.parse import unquote, urlsplit
from zipfile import ZipFile


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
    require(len(sources) == 15 and len(paper_ids) == 13, "First-batch source count changed")
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
    for sid, species, grade in (("B07-X", "Lasius neoniger", "C"), ("FT01-X", "Pachycondyla crassinoda", "D")):
        source = sources[sid]
        require((source["ActualExperimentalSpecies"], source["AtlasGrade"], source["EvidenceClassification"])
                == (species, grade, "CROSS_SPECIES_EXTRAPOLATION"), f"{sid}: non-target evidence conflated with L. niger")
    return sources, log


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


def tab_rows(archive, name):
    return csv.DictReader(io.StringIO(archive.read(name).decode("utf-8-sig"), newline=""), delimiter="\t")


def verify_b01_supplement(path):
    with ZipFile(path) as archive:
        design = index(tab_rows(archive, "Effect_of_worker_cues_wire_mesh_design_info.txt"), "Box_label")
        observations = {(row["Observation"], row["Box_label"]) for row in
                        tab_rows(archive, "Effect_of_worker_cues_wire_mesh_BORIS_output.txt") if row["Behavior"] == "0"}
        first_worker = {}
        for row in tab_rows(archive, "Brood_production.txt"):
            if row["Brood_type"] == "Workers" and int(row["Quantity"]) > 0:
                queen, day = row["Queen"], int(row["Day"])
                first_worker[queen] = min(day, first_worker.get(queen, day))

    # Appendix S1 joins on windows with at least one non-care scan, then applies its exclusions.
    require((len(design), len(observations)) == (60, 175), "B01 raw mesh design drift")
    excluded_boxes = {f"E4-20-{number}" for number in ("41", "22", "08", "66", "23")}
    excluded_windows = {"36-24h", "39-6h", "39-24h", "09-6h", "09-24h", "59-24h"}
    remaining = {(window, queen) for window, queen in observations
                 if queen not in excluded_boxes and window not in excluded_windows}
    order = ("Callows_separated", "Callows_with_Q", "No_callows")

    def arm_counts(windows):
        counts = Counter(design[queen]["Treatment"] for queen in {queen for _, queen in windows})
        return tuple(counts[arm] for arm in order)

    require(arm_counts(remaining) == (21, 14, 20), "B01 mesh counts before tray exclusion drifted")
    retained = {(window, queen) for window, queen in remaining if design[queen]["Tray"] != "0"}
    require(arm_counts(retained) == (13, 14, 16) and len(retained) == 127, "B01 mesh analysis counts drifted")
    days = first_worker.values()
    require((len(days), round(fmean(days), 2), round(stdev(days), 2)) == (17, 62.88, 2.52),
            "B01 Fig. S4 first-worker days drifted")
    print("PASS: B01 mesh exclusions 60 -> 55 -> 43 queens and 127 windows; Fig. S4 onset 62.88 ± 2.52 d (17 queens)")


def verify_b03_supplement(path):
    from openpyxl import load_workbook

    workbook = load_workbook(path, data_only=True, read_only=True)
    try:
        data = {code: (pupae, workers, comment) for code, _, pupae, workers, comment in
                workbook["Supporting Information 1"].iter_rows(min_row=2, values_only=True)
                if isinstance(code, str) and re.fullmatch(r"[A-H]\d{2}", code)}
    finally:
        workbook.close()
    require(len(data) == 240 and sum(note == "queen died" for _, _, note in data.values()) == 4,
            "B03 queen endpoint or death annotation counts changed")
    for arm, mean, sd in (("A", 18.73, 4.74), ("B", 17.90, 5.20), ("D", 18.23, 3.95), ("F", 21.77, 5.04)):
        counts = [pupae + workers for code, (pupae, workers, _) in data.items() if code.startswith(arm)]
        require((len(counts), round(fmean(counts), 2), round(stdev(counts), 2)) == (30, mean, sd),
                f"B03 all-row day-49 summary changed for arm {arm}")
    print("PASS: B03 all 240 queen endpoints, four death annotations and four day-49 summaries")


def verify_b07_supplement(path):
    paired = defaultdict(dict)
    with ZipFile(path) as archive:
        for row in tab_rows(archive, "DATA_combined.txt"):
            paired[row["species"], row["colony"]][row["census_number"]] = row
        pulse = [row for row in tab_rows(archive, "Lasius_pulseisotopedata.txt") if row["Sample ID"]]

    def centered_sum_squares(values):
        center = fmean(values)
        return sum((value - center) ** 2 for value in values)

    for species, expected in (("niger", (89, 86, 80, 4.363743)), ("neoniger", (96, 96, 47, 0.596697))):
        colonies = [data for (identity, _), data in paired.items() if identity == species]
        first_census = sum(colony["1"]["num_workers"].isdecimal() for colony in colonies)
        diets, cells = defaultdict(list), defaultdict(list)
        for colony in colonies:
            before, after = colony["2"], colony["8"]
            if before["num_workers"].isdecimal() and after["num_workers"].isdecimal():
                change = int(after["num_workers"]) - int(before["num_workers"])
                diets[after["diet"]].append(change)
                cells[after["diet"], after["freq"]].append(change)
        values = [change for changes in diets.values() for change in changes]
        # The sequential ANOVA tests diet first and uses diet-by-frequency cell residuals.
        diet_ss = centered_sum_squares(values) - sum(map(centered_sum_squares, diets.values()))
        residual_mean_square = sum(map(centered_sum_squares, cells.values())) / (len(values) - len(cells))
        diet_f = diet_ss / (len(diets) - 1) / residual_mean_square
        require((len(colonies), first_census, len(values), round(diet_f, 6)) == expected,
                f"B07 Table S3 diet result or census coverage changed for {species}")
        if species == "niger":
            for diet, n, mean, sd in (("16", 21, 23.57, 6.82), ("8", 22, 34.68, 12.01)):
                changes = diets[diet]
                require((len(changes), round(fmean(changes), 2), round(stdev(changes), 2)) == (n, mean, sd),
                        f"B07 niger diet 1:{diet} complete-pair summary changed")

    require(len(pulse) == 32 and all(row["Sample ID"].startswith("Lneo-") for row in pulse),
            "B07 isotope samples lost the species boundary")
    groups = defaultdict(set)
    for row in pulse:
        groups[row["Enriched"], row["Time"], row["Caste"]].add(row["Colony"])
    require({key: len(ids) for key, ids in groups.items()} == {
        (label, time, caste): count for label, count in (("Yes", 5), ("No", 3))
        for time in ("24", "96") for caste in ("W", "L")}, "B07 isotope colony strata changed")
    for time, caste, expected in (("24", "W", (16.38, 194.29)), ("96", "L", (9.41, 25.40))):
        selected = [row for row in pulse if (row["Enriched"], row["Time"], row["Caste"]) == ("Yes", time, caste)]
        means = tuple(round(100 * fmean(float(row[key]) for row in selected), 2) for key in ("C_APE2", "N_APE2"))
        require(means == expected, f"B07 isotope enrichment changed for {time}/{caste}")
    print("PASS: B07 census coverage, diet F=4.363743/0.596697 and 32 congener isotope aliquots")


def verify_downloads(log, download_dir, b01_dryad):
    local_paths = {}
    for rid, row in log.items():
        if row["AccessRoute"] == "User-supplied source file":
            path = download_dir / Path(row["Location"]).name
            require(sha256(path.read_bytes()).hexdigest() == row["SourceSha256"], f"{rid}: supplied file hash changed")
            local_paths[rid] = path
    require(sha256(b01_dryad.read_bytes()).hexdigest() == log["ACC-016"]["SourceSha256"], "B01 Dryad hash changed")
    print(f"PASS: {len(set(local_paths.values()))} recovered files and the B01 Dryad archive match recorded SHA-256 hashes")
    verify_b01_supplement(b01_dryad)
    verify_b03_supplement(local_paths["ACC-034"])
    verify_b07_supplement(local_paths["ACC-038"])


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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download-dir", type=Path, help="directory containing the supplied supplements")
    parser.add_argument("--b01-dryad", type=Path, help="original B01 Dryad ZIP used by the recovered analysis script")
    args = parser.parse_args()
    if bool(args.download_dir) != bool(args.b01_dryad):
        parser.error("--download-dir and --b01-dryad must be supplied together")
    sources, log = verify_sources()
    conflicts = set(re.findall(r"^## (B1-C\d{2})\b", (REVIEW / "EVIDENCE_CONFLICTS.md").read_text(encoding="utf-8"), re.MULTILINE))
    require(len(conflicts) == 11, "First-batch conflict register changed")
    mechanisms, transitions, parameters = verify_review(sources, conflicts)
    verify_links()
    print(f"PASS: {len(sources)} source contexts, {len(log)} access records, {len(conflicts)} conflicts and document links")
    print(f"PASS: {mechanisms} mechanisms, {transitions} transitions, {parameters} parameters linked to the frozen inventory")
    print(f"PASS: B01 per-queen focal means: {verify_b01()}")
    print(f"PASS: B02 unit means (count, contact s, marker s), queen / first-worker trio: {verify_b02()}")
    print(f"PASS: Carthy retained path range {verify_carthy()}; oxygen and combustion conversions")
    if args.download_dir:
        verify_downloads(log, args.download_dir, args.b01_dryad)


if __name__ == "__main__":
    main()
