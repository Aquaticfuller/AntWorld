#!/usr/bin/env python3
"""Check the reviewed Batch 2 evidence and its frozen source references."""

import re
import subprocess
import sys

from verify_batch1 import CLASSES, REVIEW, ROOT, index, list_field, require, rows


REVIEWED = "f2994f4059c244258fe5dc7250f985bf8c399c6d"
SOURCE_REGISTER = "BATCH2_SOURCE_FULLTEXT_REGISTER.csv"
ACCESS_LOG = "BATCH2_SOURCE_ACCESS_LOG.csv"
RULE_REVIEW = "BATCH2_MECHANISM_EVIDENCE_REVIEW.csv"
PARAMETER_REVIEW = "BATCH2_PARAMETER_EVIDENCE_REVIEW.csv"
CONFLICTS = "BATCH2_EVIDENCE_CONFLICTS.md"
INVENTORY = "CURRENT_CORE_MECHANISM_INVENTORY.csv"
TRANSITIONS = "STATE_MACHINE_TRANSITION_EVIDENCE.csv"
PARAMETERS = "PARAMETER_EVIDENCE_MATRIX.csv"
ANCHORS = "SOURCE_ANCHORS.csv"
TABLES = (SOURCE_REGISTER, ACCESS_LOG, RULE_REVIEW, PARAMETER_REVIEW, INVENTORY, TRANSITIONS, PARAMETERS, ANCHORS)
SCOPE = {
    "SEN-01", "SEN-02", "SEN-03", "SEN-06",
    *(f"{domain}-{i:02}" for domain, count in (("FOR", 10), ("PHE", 5)) for i in range(1, count + 1)),
}
PAPERS = {
    *(f"B2-F{i:02}" for i in range(1, 11)),
    *(f"B2-P{i:02}" for i in (*range(1, 14), 15, 16)),
}
TARGET = "Lasius niger"
DIRECT = "DIRECT_SPECIES_DATA"
CROSS = "CROSS_SPECIES_EXTRAPOLATION"
FIXTURE = "ENGINEERING_FIXTURE"
FOCAL_CONTEXTS = {
    "B2-F02": "Acanthomyops (Lasius) niger (historical name)",
    "B2-P10": "Lasius niger focal. Formica rufa, F. fusca and F. sanguinea separately analysed in the paper.",
    "B2-P16": "Lasius niger focal. Euprenolepis procera and Linepithema humile separate groups.",
}
LOCATIONS = ("SourceFile", "StartLine", "EndLine", "SourceSpanSha256", "SourceAnchorIds")
READ_OUTCOMES = {
    "READ_FULL_ARTICLE_SECTIONS": "ORIGINAL_ARTICLE",
    "READ_SUPPLEMENT_SECTIONS": "SUPPLEMENT",
    "READ_AND_RECALCULATED": "PRIMARY_DATA",
}
OTHER_OUTCOMES = {
    "CATALOGUE_SHELL_ONLY", "HTTP_403", "METADATA_READ_ONLY", "NON_PDF_RESPONSE", "RESTRICTED_REPOSITORY_PDF",
}


def measured(text):
    return text.strip().upper() not in {"", "NOT_APPLICABLE", "NOT APPLICABLE", "NOT MEASURED", "N/A", "UNKNOWN"}


def verify_sources(tables):
    sources = index(tables[SOURCE_REGISTER], "SourceId")
    require(len(PAPERS) == 25 and sources.keys() == PAPERS | {"B2-P12-C"}, "Batch 2 source coverage drift")
    doi_owners = {}
    for sid, row in sources.items():
        paper = row["PaperId"]
        require(paper == ("B2-P12" if sid == "B2-P12-C" else sid), f"{sid}: wrong parent paper")
        doi = row["DOI"]
        require(re.fullmatch(r"10\.\d{4,9}/[^\s;]+", doi) and row["PrimaryURL"] == f"https://doi.org/{doi}",
                f"{sid}: invalid DOI or primary URL")
        require(doi_owners.setdefault(doi.casefold(), paper) == paper, f"{sid}: DOI belongs to multiple papers")
        require(all(row[field] == sources[paper][field] for field in ("DOI", "Title", "Authors", "Year", "Journal")),
                f"{sid}: bibliography differs from parent paper")
        require(row["TargetSpecies"] == TARGET and row["Batch"] == "2", f"{sid}: wrong target or batch")
        species = row["ActualExperimentalSpecies"]
        classification, grade = row["EvidenceClassification"], row["AtlasGrade"]
        if sid == "B2-P12-C":
            valid_context = (species, classification, grade) == ("Lasius neglectus", CROSS, "C")
        else:
            valid_context = species == FOCAL_CONTEXTS.get(sid, TARGET) and classification == DIRECT and grade in {"A", "B"}
        require(valid_context, f"{sid}: species, evidence class and Atlas grade disagree")
        require(all(measured(row[field]) for field in ("ActualMeasuredEndpoint", "OriginalMeasurement", "Unit")),
                f"{sid}: missing measured source endpoint, observation or unit")
        require(row["FullTextAccessStatus"] == "FULL_ARTICLE_AVAILABLE" and row["FullTextActuallyRead"] == "YES_SELECTED_SECTIONS"
                and all(row[field].strip() for field in ("MethodsSection", "ResultsSection", "SampleSize", "ReadingScope")),
                f"{sid}: incomplete source reading scope")

    access = index(tables[ACCESS_LOG], "AccessId")
    p15_pdf = access.get("B2-ACC-046", {})
    require((p15_pdf.get("SourceId"), p15_pdf.get("AccessOutcome")) == ("B2-P15", "READ_FULL_ARTICLE_SECTIONS"),
            "B2-P15: missing stable PDF reading record")
    full_reads = set()
    for aid, row in access.items():
        sid, outcome = row["SourceId"], row["AccessOutcome"]
        require(sid in sources and row["AccessRoute"] and row["Location"], f"{aid}: invalid source access record")
        require(outcome in READ_OUTCOMES or outcome in OTHER_OUTCOMES, f"{aid}: invalid access outcome")
        digest = row["SourceSha256"]
        require(not digest or re.fullmatch(r"[0-9a-f]{64}", digest), f"{aid}: invalid source file SHA-256")
        if outcome in READ_OUTCOMES:
            require(row["ActuallyRead"] == "YES_SELECTED_SECTIONS" and row["ReadingScope"]
                    and row["MaterialKind"] == READ_OUTCOMES[outcome], f"{aid}: inconsistent reading claim")
            require(digest or (aid, sid) == ("B2-ACC-029", "B2-P15"), f"{aid}: missing source file SHA-256")
            if outcome == "READ_FULL_ARTICLE_SECTIONS":
                full_reads.add(sid)
        else:
            require(row["ActuallyRead"] == "NO", f"{aid}: unsuccessful access marked as a reading")
    require(full_reads == sources.keys(), "At least one source lacks a full article reading record")
    return sources, len(access)


def verify_citations(row, key, sources, conflicts):
    ids = list_field(row["SourceIds"])
    require(len(ids) == len(set(ids)) and set(ids) <= sources.keys(), f"{key}: unknown or duplicate source ID")
    require(list_field(row["DOIs"]) == [sources[sid]["DOI"] for sid in ids], f"{key}: source DOI drift")
    require(list_field(row["AtlasSourceGrades"]) == [f"{sid}={sources[sid]['AtlasGrade']}" for sid in ids],
            f"{key}: cited Atlas grade drift")
    locators = row["EvidenceLocators"].split(" | ") if row["EvidenceLocators"] else []
    require([entry.split(" ", 1)[0] for entry in locators] == ids
            and all(entry.partition(" ")[2].strip() for entry in locators), f"{key}: missing source locator")
    refs = list_field(row["ConflictIds"])
    require(len(refs) == len(set(refs)) and set(refs) <= conflicts, f"{key}: unknown or duplicate conflict ID")
    return set(refs)


def verify_location(row, frozen, key, kind, anchors):
    for field in LOCATIONS:
        require(row[field] == frozen[field], f"{key}: changed frozen {field}")
    for aid in list_field(row["SourceAnchorIds"]):
        require(aid in anchors and (anchors[aid]["RecordKind"], anchors[aid]["RecordId"]) == (kind, key),
                f"{key}: wrong owner for source anchor {aid}")


def verify_records(tables, conflicts):
    sources, access_count = verify_sources(tables)
    inventory = index(tables[INVENTORY], "MechanismId")
    state = index(tables[TRANSITIONS], "TransitionId")
    matrix = index(tables[PARAMETERS], "ParameterKey")
    anchors = index(tables[ANCHORS], "AnchorId")
    review = tables[RULE_REVIEW]
    require(all(row["RecordKind"] in {"MECHANISM", "TRANSITION"} for row in review), "Unexpected review record kind")
    mechanisms = index((row for row in review if row["RecordKind"] == "MECHANISM"), "MechanismId")
    transitions = index((row for row in review if row["RecordKind"] == "TRANSITION"), "TransitionId")
    expected_transitions = {tid for tid, row in state.items() if row["MechanismId"] in SCOPE}
    require(len(mechanisms) == 19 and mechanisms.keys() == SCOPE and SCOPE <= inventory.keys(),
            "Batch 2 mechanism coverage drift")
    require(len(transitions) == 19 and transitions.keys() == expected_transitions, "Batch 2 transition coverage drift")
    referenced_conflicts = set()
    for row in review:
        mid, tid, kind = row["MechanismId"], row["TransitionId"], row["RecordKind"]
        require(bool(tid) == (kind == "TRANSITION") and mid in SCOPE, f"{tid or mid}: wrong review identity")
        key, frozen = (tid, state[tid]) if tid else (mid, inventory[mid])
        require(frozen["MechanismId"] == mid and row["Domain"] == inventory[mid]["Domain"], f"{key}: wrong mechanism owner")
        if tid:
            element = f"{frozen['FromState']} → {frozen['ToState']}"
            rule = " | ".join(frozen[field] for field in ("Trigger", "GuardOrAlternate", "ActionAndNextWake"))
        else:
            element, rule = frozen["Mechanism"], frozen["SourceRule"]
        require(row["CodeElement"] == element and row["CurrentRuleOrGuard"] == rule
                and row["Function"] == frozen["Function"], f"{key}: changed frozen rule description")
        verify_location(row, frozen, key, kind, anchors)
        referenced_conflicts.update(verify_citations(row, key, sources, conflicts))
        classification = row["EvidenceClassification"]
        require(classification in CLASSES and row["CoreRuleClassification"] in {"MODELING_ASSUMPTION", FIXTURE},
                f"{key}: invalid evidence or implementation class")
        if classification in {DIRECT, CROSS}:
            require(any(sources[sid]["EvidenceClassification"] == classification for sid in list_field(row["SourceIds"])),
                    f"{key}: no source of the asserted biological class")
            require(measured(row["MeasuredEndpointAndUnit"]), f"{key}: no biological measurement endpoint")
        require(all(row[field].strip() for field in ("RuleAssessment", "SupportedBiologicalClaim", "UnsupportedImplementationOrGap")),
                f"{key}: incomplete rule assessment")

    parameters = index(tables[PARAMETER_REVIEW], "ParameterKey")
    expected_parameters = {key for key, row in matrix.items() if SCOPE.intersection(list_field(row["MechanismIds"]))}
    require(len(parameters) == 67 and parameters.keys() == expected_parameters, "Batch 2 parameter coverage drift")
    for key, row in parameters.items():
        frozen = matrix[key]
        verify_location(row, frozen, key, "CORE_RULE", anchors)
        for field in ("RecordKind", "MechanismIds", "SourceExpression", "CurrentSourceValue",
                      "Unit", "Role", "Scope", "ValueRoleClass", "ParameterEvidenceClass"):
            require(row[field] == frozen[field], f"{key}: changed frozen {field}")
        links = [mid for mid in list_field(frozen["MechanismIds"]) if mid in SCOPE]
        require(list_field(row["Batch2MechanismIds"]) == links, f"{key}: changed Batch 2 parameter links")
        require(row["ParameterEvidenceClass"] == FIXTURE and row["AtlasParameterGrade"] == frozen["AtlasGrade"] == "F",
                f"{key}: parameter evidence class or grade changed")
        require((row["CanCalibrateCurrentValue"], row["CalibrationAssessment"]) in {
            ("NO", "UNCALIBRATED_COMPARATOR_ONLY"), ("NOT_APPLICABLE", "NOT_A_BIOLOGICAL_COEFFICIENT"),
        }, f"{key}: unauthorized calibration")
        if row["CanCalibrateCurrentValue"] == "NO":
            require(row["SourceIds"] and measured(row["ActualMeasuredEndpoint"]), f"{key}: missing biological comparator")
        referenced_conflicts.update(verify_citations(row, key, sources, conflicts))
    require(referenced_conflicts == conflicts, "At least one conflict lost its evidence links")
    return access_count


def verify_rejections(tables, conflicts):
    cases = (
        (RULE_REVIEW, "MechanismId", "SEN-02", "SourceIds", "B2-UNKNOWN", "unknown or duplicate source ID"),
        (RULE_REVIEW, "MechanismId", "SEN-02", "DOIs", "10.1007/BF01201674", "source DOI drift"),
        (RULE_REVIEW, "MechanismId", "SEN-02", "AtlasSourceGrades", "B2-F04=D", "cited Atlas grade drift"),
        (RULE_REVIEW, "MechanismId", "SEN-02", "SourceAnchorIds", "M-011-A01", "changed frozen SourceAnchorIds"),
        (RULE_REVIEW, "MechanismId", "SEN-02", "MeasuredEndpointAndUnit", "NOT_APPLICABLE", "no biological measurement endpoint"),
        (RULE_REVIEW, "MechanismId", "SEN-02", "ConflictIds", "B2-C99", "unknown or duplicate conflict ID"),
        (PARAMETER_REVIEW, "ParameterKey", "route_storage_capacity", "Batch2MechanismIds", "SEN-01", "changed Batch 2 parameter links"),
        (PARAMETER_REVIEW, "ParameterKey", "route_storage_capacity", "CanCalibrateCurrentValue", "YES", "unauthorized calibration"),
        (SOURCE_REGISTER, "SourceId", "B2-P12-C", "EvidenceClassification", DIRECT, "species, evidence class and Atlas grade disagree"),
    )
    for name, id_field, identity, field, replacement, diagnostic in cases:
        changed = list(tables[name])
        position = next(i for i, row in enumerate(changed) if row[id_field] == identity)
        changed[position] = {**changed[position], field: replacement}
        try:
            verify_records({**tables, name: changed}, conflicts)
        except ValueError as error:
            require(diagnostic in str(error), f"{field} corruption was rejected for the wrong reason: {error}")
        else:
            raise ValueError(f"Corruption accepted in {identity}.{field}")
    print(f"PASS: {len(cases)} injected evidence errors rejected with their expected diagnostics")


def verify_reviewed_evidence():
    # Compare the reviewed contents with universal newlines on both platforms.
    # The access history is append-only so that a new successful read preserves earlier access limits.
    files = (SOURCE_REGISTER, ACCESS_LOG, RULE_REVIEW, PARAMETER_REVIEW, CONFLICTS,
             "BATCH2_FULLTEXT_REVIEW_PROGRESS.md", "BATCH2_VALIDATION_GAPS.md")
    for name in files:
        path = REVIEW / name
        original = subprocess.check_output(
            ["git", "show", f"{REVIEWED}:{path.relative_to(ROOT).as_posix()}"], cwd=ROOT, encoding="utf-8",
        )
        current = path.read_text(encoding="utf-8")
        unchanged = current.startswith(original) if name == ACCESS_LOG else current == original
        require(unchanged, f"{name}: reviewed scientific evidence or original access history changed")


def main():
    tables = {name: list(rows(REVIEW / name)) for name in TABLES}
    headings = re.findall(r"^## (B2-C\d{2}) \|", (REVIEW / CONFLICTS).read_text(encoding="utf-8"), re.MULTILINE)
    conflicts = set(headings)
    require(len(headings) == 11 and conflicts == {f"B2-C{i:02}" for i in range(1, 12)}, "Batch 2 conflict register drift")
    access_count = verify_records(tables, conflicts)
    verify_rejections(tables, conflicts)
    verify_reviewed_evidence()
    # Reuse the Step 1-R1 check for actual C++ spans, declarations and generated matrix contents.
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(ROOT / "tools/audit_s6_4_preflight.py"), "--check"],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8",
    )
    require(result.returncode == 0, f"Step 1-R1 source verification failed:\n{result.stdout}")
    print("PASS: 19 mechanisms, 19 transitions and 67 uncalibrated parameter records match the frozen source and anchors")
    print(f"PASS: 25 papers, 26 assay contexts, {access_count} access records and 11 conflicts")
    print("PASS: reviewed scientific evidence and original negative results preserved")


if __name__ == "__main__":
    try:
        main()
    except (KeyError, OSError, ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"FAIL: {error}") from error
