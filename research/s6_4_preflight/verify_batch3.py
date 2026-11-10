#!/usr/bin/env python3
"""Verify Batch 3 scope, earlier evidence links, and frozen source references."""

import re
import subprocess
import sys

from reproduce_batch3_sources import INPUTS
from verify_batch1 import CLASSES, REVIEW, ROOT, index, list_field, require, rows
from verify_batch2 import (
    ANCHORS, CROSS, DIRECT, FIXTURE, INVENTORY, PARAMETERS, TRANSITIONS, measured,
    verify_citations, verify_location,
)


APPROVED = "1652d092446fff2377b988e6f1326a9cc58f77af"
SCOPE = {
    *(f"TSK-{i:02}" for i in range(1, 6)), *(f"NST-{i:02}" for i in range(1, 9)),
    "POP-01", "POP-03", "POP-05", "POP-06",
}
SOURCE_FILE = "BATCH3_SOURCE_FULLTEXT_REGISTER.csv"
ACCESS_FILE = "BATCH3_SOURCE_ACCESS_LOG.csv"
RULE_FILE = "BATCH3_MECHANISM_EVIDENCE_REVIEW.csv"
PARAMETER_FILE = "BATCH3_PARAMETER_EVIDENCE_REVIEW.csv"
PRIOR_RULES = ("MECHANISM_EVIDENCE_REVIEW.csv", "BATCH2_MECHANISM_EVIDENCE_REVIEW.csv")
PRIOR_PARAMETERS = ("PARAMETER_EVIDENCE_REVIEW.csv", "BATCH2_PARAMETER_EVIDENCE_REVIEW.csv")
PRIOR_SOURCES = ("SOURCE_FULLTEXT_REGISTER.csv", "BATCH2_SOURCE_FULLTEXT_REGISTER.csv")
SOURCES = {
    *(f"B3-T{i:02}" for i in range(1, 10)),
    *(f"B3-N{i:02}" for i in (1, 2, 3, 4, 5, 7, 8)),
    *(f"B3-P{i:02}" for i in range(1, 13)),
}
ASSUMPTION = "MODELING_ASSUMPTION"
TARGET = "Lasius niger"
WEB_ONLY = {"B3-N05", "B3-P06"}
ACCESS_READS = {
    "READ_FULL_ARTICLE_SECTIONS": "ORIGINAL_ARTICLE",
    "READ_PUBLISHER_HTML_SECTIONS": "ORIGINAL_ARTICLE",
    "READ_AND_RECALCULATED": "PRIMARY_DATA",
}
ACCESS_LIMITS = {"CATALOGUE_SHELL_ONLY", "NON_PDF_RESPONSE", "METADATA_READ_ONLY", "HTTP_403", "RESTRICTED_DATASET"}
TABLES = (SOURCE_FILE, ACCESS_FILE, RULE_FILE, PARAMETER_FILE, INVENTORY, TRANSITIONS, PARAMETERS, ANCHORS,
          *PRIOR_RULES, *PRIOR_PARAMETERS, *PRIOR_SOURCES)


def verify_sources(tables):
    sources = index(tables[SOURCE_FILE], "SourceId")
    require(sources.keys() == SOURCES, "Batch 3 source coverage drift")
    dois = set()
    for sid, record in sources.items():
        doi = record["DOI"]
        require(re.fullmatch(r"10\.\d{4,9}/[^\s;]+", doi) and record["PrimaryURL"] == f"https://doi.org/{doi}"
                and doi.casefold() not in dois, f"{sid}: invalid or duplicate DOI")
        dois.add(doi.casefold())
        expected = {
            "B3-N07": ("Solenopsis invicta", CROSS, "D"),
            "B3-P07": ("Mixed field ants, Lasius niger was 57 of 58 identified post-flood individuals", DIRECT, "B"),
            "B3-T01": (TARGET, DIRECT, "B"),
            "B3-T08": ("Lasius niger (focal); Temnothorax nylanderi (separate Fig. 4b excluded)", DIRECT, "A"),
            "B3-P04": ("Lasius niger (this row); Lasius neoniger (other arms)", DIRECT, "A"),
        }.get(sid, (TARGET, DIRECT, "A"))
        actual = tuple(record[field] for field in ("ActualExperimentalSpecies", "EvidenceClassification", "AtlasGrade"))
        require(actual == expected, f"{sid}: evidence class, study species or grade mismatch")
        require(record["TargetSpecies"] == TARGET and record["Batch"] == "3" and record["PaperId"] == sid,
                f"{sid}: invalid target or paper identity")
        require(record["FullTextAccessStatus"] == "FULL_ARTICLE_AVAILABLE"
                and record["FullTextActuallyRead"] == "YES_SELECTED_SECTIONS"
                and all(value.strip() for value in record.values()), f"{sid}: incomplete reading metadata")
        require(all(measured(record[field]) for field in ("ActualMeasuredEndpoint", "OriginalMeasurement", "Unit")),
                f"{sid}: missing biological endpoint")
    return sources


def verify_access(tables, sources):
    access = index(tables[ACCESS_FILE], "AccessId")
    require(access.keys() == {f"B3-ACC-{i:03}" for i in range(1, 46)}, "Batch 3 access record coverage drift")
    article_reads = {}
    raw_digests = {}
    for aid, row in access.items():
        sid, outcome, digest = row["SourceId"], row["AccessOutcome"], row["SourceSha256"]
        require(sid in sources and all(row[key] for key in ("Date", "AccessRoute", "Location", "Limitations")),
                f"{aid}: incomplete or unknown access record")
        require(outcome in ACCESS_READS or outcome in ACCESS_LIMITS, f"{aid}: invalid access outcome")
        if outcome in ACCESS_READS:
            require(row["ActuallyRead"] == "YES_SELECTED_SECTIONS" and row["ReadingScope"]
                    and row["MaterialKind"] == ACCESS_READS[outcome], f"{aid}: invalid reading claim")
            if outcome == "READ_PUBLISHER_HTML_SECTIONS":
                require(sid in WEB_ONLY and not digest and row["Location"].startswith("https://"),
                        f"{aid}: web-only article read lacks provenance or falsely pins a file")
            else:
                require(re.fullmatch(r"[0-9a-f]{64}", digest), f"{aid}: missing or invalid source hash")
            if outcome == "READ_AND_RECALCULATED":
                raw_digests[digest] = (sid, row["Location"])
            else:
                require(sid not in article_reads, f"{aid}: duplicate article receipt")
                article_reads[sid] = outcome
        else:
            require(row["ActuallyRead"] == "NO" and not digest, f"{aid}: access limitation marked as verified")
    require(article_reads.keys() == sources.keys(), "Unverified full-text scope")
    require({sid for sid, outcome in article_reads.items() if outcome == "READ_PUBLISHER_HTML_SECTIONS"} == WEB_ONLY,
            "Unexpected reading-route coverage")
    require(raw_digests.keys() == {digest for _, digest in INPUTS.values()}, "Raw input hashes differ from the reproducer")
    for name, (doi, digest) in INPUTS.items():
        sid, location = raw_digests[digest]
        require(doi.casefold() in location.casefold() and sid == ("B3-P07" if name.endswith(".tsv") else "B3-P06"),
                f"{name}: mismatched raw source record")


def rule_sets(records):
    require(all(row["RecordKind"] in {"MECHANISM", "TRANSITION"} for row in records), "Unexpected evidence record type")
    return (
        index((row for row in records if row["RecordKind"] == "MECHANISM"), "MechanismId"),
        index((row for row in records if row["RecordKind"] == "TRANSITION"), "TransitionId"),
    )


def verify_rules(records, inventory, state, anchors, sources, conflicts):
    mechanisms, transitions = rule_sets(records)
    require(len(mechanisms) == 17 and mechanisms.keys() == SCOPE, "Batch 3 mechanism coverage drift")
    expected = {tid for tid, row in state.items() if row["MechanismId"] in SCOPE}
    require(len(transitions) == 27 and transitions.keys() == expected, "Batch 3 transition coverage drift")
    linked = set()
    for row in records:
        tid, mid, kind = row["TransitionId"], row["MechanismId"], row["RecordKind"]
        require(bool(tid) == (kind == "TRANSITION") and mid in SCOPE, f"{tid or mid}: wrong rule identity")
        key, frozen = (tid, state[tid]) if tid else (mid, inventory[mid])
        require(mid == frozen["MechanismId"] and row["Domain"] == inventory[mid]["Domain"], f"{key}: wrong rule owner")
        if tid:
            element = f"{frozen['FromState']} → {frozen['ToState']}"
            rule = " | ".join(frozen[field] for field in ("Trigger", "GuardOrAlternate", "ActionAndNextWake"))
        else:
            element, rule = frozen["Mechanism"], frozen["SourceRule"]
        require((row["CodeElement"], row["CurrentRuleOrGuard"], row["Function"]) == (element, rule, frozen["Function"]),
                f"{key}: source rule description changed")
        verify_location(row, frozen, key, kind, anchors)
        linked.update(verify_citations(row, key, sources, conflicts))
        category = row["EvidenceClassification"]
        require(category in CLASSES and row["CoreRuleClassification"] in {FIXTURE, ASSUMPTION},
                f"{key}: evidence classification invalid")
        ids = list_field(row["SourceIds"])
        if category == FIXTURE:
            require(row["RuleAssessment"] == "ENGINEERING_ONLY" and not ids, f"{key}: fixture presented as biology")
        else:
            require(ids and measured(row["MeasuredEndpointAndUnit"]), f"{key}: biological comparison has no endpoint")
            if category in {DIRECT, CROSS}:
                require(any(sources[sid]["EvidenceClassification"] == category for sid in ids),
                        f"{key}: species classification is unsupported")
        require(all(row[field].strip() for field in ("InformationChannel", "SupportedBiologicalClaim", "UnsupportedImplementationOrGap")),
                f"{key}: incomplete independent rule assessment")
    return mechanisms, transitions, linked


def verify_parameters(tables, matrix, anchors, sources, conflicts):
    parameters = index(tables[PARAMETER_FILE], "ParameterKey")
    expected = {key for key, row in matrix.items() if SCOPE.intersection(list_field(row["MechanismIds"]))}
    require(len(parameters) == 139 and parameters.keys() == expected, "Batch 3 parameter coverage drift")
    earlier = [index(tables[name], "ParameterKey") for name in PRIOR_PARAMETERS]
    old_sources = [index(tables[name], "SourceId") for name in PRIOR_SOURCES]
    linked = set()
    shared = 0
    for key, row in parameters.items():
        frozen = matrix[key]
        verify_location(row, frozen, key, "CORE_RULE", anchors)
        for field in ("RecordKind", "MechanismIds", "SourceExpression", "CurrentSourceValue", "Unit",
                      "Role", "Scope", "ValueRoleClass", "ParameterEvidenceClass"):
            require(row[field] == frozen[field], f"{key}: frozen {field} differs")
        require(row["ParameterEvidenceClass"] == FIXTURE and row["AtlasParameterGrade"] == frozen["AtlasGrade"] == "F",
                f"{key}: fixture provenance changed")
        require(list_field(row["Batch3MechanismIds"]) == [mid for mid in list_field(frozen["MechanismIds"]) if mid in SCOPE],
                f"{key}: wrong Batch 3 mechanism links")
        prior_batches, prior_mids, prior_ids, prior_dois = [], [], [], set()
        for batch, previous in enumerate(earlier, 1):
            if key in previous:
                old = previous[key]
                prior_batches.append(str(batch))
                prior_mids.extend(list_field(old[f"Batch{batch}MechanismIds"]))
                for sid in list_field(old["SourceIds"]):
                    prior_ids.append(f"B{batch}/{sid}")
                    prior_dois.add(old_sources[batch - 1][sid]["DOI"].casefold())
        shared += bool(prior_batches)
        require(list_field(row["PriorReviewBatches"]) == prior_batches and
                list_field(row["PriorMechanismIds"]) == list(dict.fromkeys(prior_mids)) and
                list_field(row["PriorSourceRefs"]) == prior_ids and bool(row["PriorUses"]) == bool(prior_batches),
                f"{key}: earlier domain or source link mismatch")
        require(all(mid in row["PriorUses"] for mid in prior_mids), f"{key}: missing earlier mechanism context")
        expected_dois = sorted(prior_dois.intersection(doi.casefold() for doi in list_field(row["DOIs"])))
        require(list_field(row["OverlappingPrimaryDOIs"]) == expected_dois, f"{key}: invalid prior DOI overlap")
        require(row["Batch3UseType"] in {"DIRECT", "INDIRECT", "METADATA_ONLY", "ENGINEERING_ONLY", "DIRECT_INPUT", "FIXTURE_CONTEXT"}
                and all(row[field].strip() for field in ("Batch3Use", "CrossDomainCoupling", "EvidenceApplicability")),
                f"{key}: no independent applicability assessment")
        ids = list_field(row["SourceIds"])
        expected_status = ("NO", "UNCALIBRATED_COMPARATOR_ONLY") if ids else ("NOT_APPLICABLE", "ENGINEERING_OR_CONTEXT_FIELD")
        require((row["CanCalibrateCurrentValue"], row["CalibrationAssessment"]) == expected_status,
                f"{key}: unauthorized calibration or incorrect status")
        require(row["Batch3UseType"] != "ENGINEERING_ONLY" or not ids, f"{key}: engineering rule assigned biological evidence")
        if ids:
            require(all(measured(row[field]) for field in ("ActualMeasuredEndpoint", "OriginalMeasurement", "OriginalUnit")),
                    f"{key}: biological comparator lacks endpoint or unit")
        linked.update(verify_citations(row, key, sources, conflicts))
    require(shared == 92 and len(parameters) - shared == 47, "Shared/first-review split changed")
    return parameters, linked


def verify_tables(tables, conflicts):
    sources = verify_sources(tables)
    verify_access(tables, sources)
    inventory = index(tables[INVENTORY], "MechanismId")
    state = index(tables[TRANSITIONS], "TransitionId")
    matrix = index(tables[PARAMETERS], "ParameterKey")
    anchors = index(tables[ANCHORS], "AnchorId")
    mechanisms, transitions, rule_conflicts = verify_rules(tables[RULE_FILE], inventory, state, anchors, sources, conflicts)
    parameters, parameter_conflicts = verify_parameters(tables, matrix, anchors, sources, conflicts)
    require(rule_conflicts | parameter_conflicts == conflicts, "At least one conflict lost its evidence links")
    used = {sid for name in (RULE_FILE, PARAMETER_FILE) for row in tables[name] for sid in list_field(row["SourceIds"])}
    require(used == sources.keys(), "At least one registered comparator has no audited application")

    all_mechanisms, all_transitions, all_parameters = set(mechanisms), set(transitions), set(parameters)
    for rules_name, params_name in zip(PRIOR_RULES, PRIOR_PARAMETERS, strict=True):
        previous_m, previous_t = rule_sets(tables[rules_name])
        require(not all_mechanisms.intersection(previous_m) and not all_transitions.intersection(previous_t),
                "Mechanism or transition overlaps a frozen prior batch")
        all_mechanisms.update(previous_m)
        all_transitions.update(previous_t)
        all_parameters.update(index(tables[params_name], "ParameterKey"))
    require((len(all_mechanisms), len(all_transitions), len(all_parameters)) == (75, 99, 249)
            and all_mechanisms == inventory.keys() and all_transitions == state.keys() and all_parameters == matrix.keys(),
            "Union of evidence batches differs from the frozen inventory")


def verify_rejections(tables, conflicts):
    cases = (
        (SOURCE_FILE, "SourceId", "B3-N07", "EvidenceClassification", DIRECT, "study species or grade mismatch"),
        (RULE_FILE, "TransitionId", "NST-03-T02", "SourceAnchorIds", "", "changed frozen SourceAnchorIds"),
        (RULE_FILE, "TransitionId", "TSK-02-T02", "SourceIds", "B3-UNKNOWN", "unknown or duplicate source ID"),
        (PARAMETER_FILE, "ParameterKey", "SocialConfig.nurse_weight", "PriorMechanismIds", "NST-02", "earlier domain or source link mismatch"),
        (PARAMETER_FILE, "ParameterKey", "SocialConfig.nurse_weight", "CanCalibrateCurrentValue", "YES", "unauthorized calibration"),
    )
    for name, field, key, column, value, diagnostic in cases:
        records = list(tables[name])
        position = next(i for i, row in enumerate(records) if row[field] == key)
        records[position] = {**records[position], column: value}
        try:
            verify_tables({**tables, name: records}, conflicts)
        except ValueError as error:
            require(diagnostic in str(error), f"{column}: wrong rejection reason: {error}")
        else:
            raise ValueError(f"Invalid {key}.{column} accepted")
    print(f"PASS: {len(cases)} injected scope, provenance and calibration errors rejected")


def git_output(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, encoding="utf-8")


def verify_frozen_inputs():
    prior_paths = git_output("ls-tree", "-r", "--name-only", APPROVED, "--", REVIEW.relative_to(ROOT).as_posix()).splitlines()
    require(prior_paths, "Approved evidence tree unavailable")
    modified = git_output("diff", "--name-only", APPROVED, "--", "cpp", "experiments", ".github/workflows/ci.yml", *prior_paths)
    require(not modified, f"Frozen Core, experiments or earlier review changed:\n{modified}")
    result = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "tools/audit_s6_4_preflight.py"), "--check"],
                            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8")
    require(result.returncode == 0, f"Step 1-R1 source verification failed:\n{result.stdout}")


def main():
    tables = {name: list(rows(REVIEW / name)) for name in TABLES}
    headings = re.findall(r"^## (B3-C\d{2}) \|", (REVIEW / "BATCH3_EVIDENCE_CONFLICTS.md").read_text(encoding="utf-8"), re.MULTILINE)
    conflicts = set(headings)
    require(len(headings) == 18 and conflicts == {f"B3-C{i:02}" for i in range(1, 19)}, "Batch 3 conflict register drift")
    verify_tables(tables, conflicts)
    verify_rejections(tables, conflicts)
    verify_frozen_inputs()
    print("PASS: 17 mechanisms, 27 transitions, and 139 uncalibrated parameters match their frozen source anchors")
    print("PASS: 92 shared and 47 first-reviewed parameters, with a union of 75 mechanisms, 99 transitions, and 249 parameters")
    print("PASS: 28 primary sources, 45 access records, 18 conflict records, and frozen prior reviews")


if __name__ == "__main__":
    try:
        main()
    except (KeyError, OSError, ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"FAIL: {error}") from error
