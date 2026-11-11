#!/usr/bin/env python3
"""Verify Phase 3 planning coverage, frozen provenance and holdout boundaries."""

import argparse
import json
import subprocess
import sys
from collections import Counter, defaultdict

from verify_batch1 import REVIEW, ROOT, index, list_field, require, rows
from verify_scientific_integration import check_table, compact, fields, unique
from verify_scientific_priorities import BLOCKER_FILE, PARAMETER_FILE, heading_ids, references


APPROVED = "c3cb3d0c02940420fd9e0bb4028628c7a9b19a9b"
PROTOCOLS = "S6_4_PHASE3_VALIDATION_PROTOCOLS.csv"
RULES = "S6_4_PHASE3_PARAMETER_EVALUATION_RULES.csv"
PARAMETERS = "S6_4_PHASE3_PARAMETER_IDENTIFIABILITY.csv"
DATA = "S6_4_PHASE3_DATA_AVAILABILITY.csv"
INDEPENDENT_PLAN = "INDEPENDENT_BIOLOGICAL_VALIDATION_PLAN.md"
SOURCES = "UNIFIED_SOURCE_CONTEXT_REGISTER.csv"

DIRECT = "DIRECTLY_ESTIMABLE_NOW"
DERIVED = "DERIVABLE_WITH_DECLARED_ASSUMPTIONS"
NEED_DATA = "REQUIRES_ADDITIONAL_DATA"
UNIDENTIFIED = "CURRENTLY_UNIDENTIFIABLE"
INPUT = "ENGINEERING_OR_EXPERIMENTAL_INPUT"
STATUSES = {DIRECT, DERIVED, NEED_DATA, UNIDENTIFIED, INPUT}
DETAILED_PRIORITIES = {"EMPIRICAL_CALIBRATION_REQUIRED", "SENSITIVITY_RANGE_REQUIRED", "CURRENTLY_NOT_IDENTIFIABLE"}
HOLDOUT_MISSING = "MATCHED_HOLDOUT_NOT_REGISTERED"
EXPOSED_DEVELOPMENT = {"B01", "B02", "B2-F01", "B2-F03"}
ROW_LEVEL_RECEIPTS = {"B01", "B02", "B03", "B07", "B07-X", "B08", "B2-F01", "B2-P03", "B2-P04", "B2-P06", "B3-P06", "B3-P07"}
ACCESS_LOGS = ("SOURCE_ACCESS_AND_READING_LOG.csv", "BATCH2_SOURCE_ACCESS_LOG.csv", "BATCH3_SOURCE_ACCESS_LOG.csv")
ASSESSMENT_FIELDS = (
    "IdentifiabilityStatus", "TargetEndpoint", "QuantitativeEvidenceStatus", "ComparatorSourceContextIds",
    "ExistingQuantitativeEvidence", "MappingToCurrentParameter", "UnitConversionOrStatisticalModel",
    "CouplingAndIdentifiability", "ProposedTreatment", "RangeBasis", "ValidationBlockerIds",
)
PROTOCOL_FIELDS = (
    "ProposedBiologicalUnit", "InputInitialization", "ObservableOutputs", "StatisticalComparison",
    "FailuresDeathsAndCensoring", "CalibrationPartition", "IndependentValidationRequirement",
    "UncertaintyAndAcceptanceMargins", "MismatchDiagnosis", "PlannedObservationInterface", "PerformanceAndPersistence",
)


def read_index(filename, key):
    return index(rows(REVIEW / filename), key)


def verify_frozen_inputs():
    changed = subprocess.check_output(
        ["git", "-C", str(ROOT), "diff", "--no-renames", "--name-status", APPROVED, "--"],
        encoding="utf-8",
    ).splitlines()
    unexpected = []
    for entry in changed:
        status, path = entry.split("\t", 1)
        if path == ".github/workflows/s6_4_preflight.yml":
            continue
        if status != "A" or path.startswith(("cpp/", "scenarios/", "experiments/")):
            unexpected.append(path)
    require(not unexpected, f"Accepted Phase 2 paths changed: {', '.join(sorted(unexpected))}")


def verify_protocols(protocols, blockers, sources):
    require(protocols.keys() == blockers.keys() == {f"BR-{number:02}" for number in range(1, 10)},
            "Expected exactly one protocol for each of the nine blockers")
    for bid, record in protocols.items():
        frozen = blockers[bid]
        require(record["Title"] == frozen["Title"] and record["ScopeIds"] == frozen["ProposedScopeIds"]
                and record["AcceptedCrossDomainConflictIds"] == frozen["AcceptedCrossDomainConflictIds"], f"{bid}: accepted scope or conflict drift")
        require(record["AcceptedSourceLinksJson"] == frozen["PrimaryEvidenceLinksJson"], f"{bid}: changed accepted source link")
        citations = json.loads(record["AcceptedSourceLinksJson"])
        contexts = references(record, "SourceContextIds", sources)
        require(contexts == unique(cite["SourceContextId"] for cite in citations), f"{bid}: source context list differs from accepted links")
        for cite in citations:
            source = sources[cite["SourceContextId"]]
            require(cite["DOI"].casefold() == source["DOI"].casefold()
                    and cite["BiologicalSampleUnit"] == source["BiologicalSampleUnit"] and cite["Locators"],
                    f"{bid}: inconsistent source locator, DOI or biological unit")
        require(record["HeldOutDatasetId"] == f"VAL-{bid}" and record["IndependentEvidenceStatus"] == HOLDOUT_MISSING
                and record["ExecutionStatus"] == "NOT_RUN", f"{bid}: holdout or execution status overstated")
        require(all(record[field].strip() for field in PROTOCOL_FIELDS), f"{bid}: missing protocol element")


def data_material(context):
    if context in ROW_LEVEL_RECEIPTS:
        return "ROW_LEVEL_MATERIAL_IN_ACCEPTED_RECEIPT"
    specific = {
        "B06": "PUBLISHED_STAGE_SUMMARIES",
        "R1C": "TABLE_TRANSCRIPTION_IN_ACCEPTED_RECEIPT",
        "B2-F03": "PARTIALLY_REUSED_TRACKS_AND_PUBLISHED_COMPARISONS",
        "B3-N05": "RESTRICTED_RAW_DATA_PUBLISHED_SUMMARIES",
    }
    return specific.get(context, "REVIEWED_PUBLICATION_CONTEXT")


def accepted_access(source, logs):
    result = []
    for view in json.loads(source["SourceViewsJson"]):
        log = view["AccessLog"]
        for aid in view["AccessIds"]:
            item = logs[log][aid]
            require(item["SourceId"] == view["SourceId"], f"{aid}: incorrect source access link")
            result.append(dict(AccessLog=log, **fields(item, ("AccessId", "SourceId", "MaterialKind", "AccessOutcome", "SourceSha256"))))
    return result


def availability(sources, protocols):
    by_source = defaultdict(list)
    logs = {name: read_index(name, "AccessId") for name in ACCESS_LOGS}
    for bid, protocol in protocols.items():
        for context in list_field(protocol["SourceContextIds"]):
            by_source[context].append(bid)
    result = []
    for context, source in sources.items():
        related = by_source[context]
        group = "B2-F01" if context in {"B2-F01", "B2-F03"} else source["GlobalPaperId"]
        role = "EXPOSED_DEVELOPMENT" if context in EXPOSED_DEVELOPMENT else "REVIEWED_COMPARATOR"
        if context == "B06":
            role = "EXPOSED_CONDITIONAL_CALIBRATION_CANDIDATE"
        detail = {
            "B01": "Previously used for model development. Keep original denominators and time origins.",
            "B02": "Previously used for model development. Keep paired origins and nonaligned retrieval versus placement markers.",
            "B06": "Both population summaries were exposed. The source has no verified individual warm-egg time and reserve series in this plan.",
            "B2-F01": "The 69 archived horizontal tracks overlap B2-F03. Group them before any split.",
            "B2-F03": "The reused B2-F01 subset shares its split group. This plan conservatively groups the entire source.",
            "B3-N05": "Accepted reading recorded restricted DataSuds raw data. Keep reported dry-mass and depth comparisons unresolved.",
        }.get(context, "Use only within the accepted sample, endpoint, species and conditions. Verify access and grouping before future analysis.")
        result.append(dict(
            DatasetId=context, SourceContextId=context, SplitGroupId=group, EvidenceRole=role,
            Availability=data_material(context), IndependentValidationEligible="NO_EXPOSED_REFERENCE",
            RelatedProtocolIds=";".join(related), DOI=source["DOI"], OriginalSourceIds=source["OriginalSourceIds"],
            **fields(source, ("PrimaryURL", "ActualExperimentalSpecies", "BiologicalSampleUnit", "SampleSize",
                              "ExperimentalConditions", "Temperature", "RelativeHumidity", "FoodCondition",
                              "MethodsSection", "ResultsSection", "Figure", "Table", "SupplementaryMaterial",
                              "ActualMeasuredEndpoint", "OriginalMeasurement", "Unit", "StatisticalUncertainty")),
            AcceptedAccessReceiptsJson=compact(accepted_access(source, logs)), LimitationOrAcquisition=detail,
        ))
    for bid, protocol in protocols.items():
        key = protocol["HeldOutDatasetId"]
        record = dict.fromkeys(result[0], "")
        record.update(
            DatasetId=key, SplitGroupId=key, EvidenceRole="PROSPECTIVE_HOLDOUT",
            Availability=HOLDOUT_MISSING, IndependentValidationEligible="PENDING_ACQUISITION_AND_SPLIT_FREEZE",
            RelatedProtocolIds=bid, ActualExperimentalSpecies="Lasius niger (planned)",
            BiologicalSampleUnit=protocol["ProposedBiologicalUnit"], ExperimentalConditions=protocol["InputInitialization"],
            ActualMeasuredEndpoint=protocol["ObservableOutputs"], StatisticalUncertainty=protocol["UncertaintyAndAcceptanceMargins"],
            AcceptedAccessReceiptsJson="[]", LimitationOrAcquisition=protocol["IndependentValidationRequirement"],
        )
        result.append(record)
    verified = index(result, "DatasetId")
    require(len(result) == 70 and len(logs) == 3 and sum(len(log) for log in logs.values()) == 133, "Unexpected dataset or access coverage")
    require(verified["B2-F01"]["SplitGroupId"] == verified["B2-F03"]["SplitGroupId"], "Shared track dependency lost")
    return result


def parameter_rules(rules, priorities, sources, protocols):
    by_key = {}
    for rid, rule in rules.items():
        category = rule["Phase2PriorityClass"]
        require(category in DETAILED_PRIORITIES and rule["IdentifiabilityStatus"] in STATUSES, f"{rid}: invalid rule class")
        keys = references(rule, "ParameterKeys", priorities)
        contexts = references(rule, "ComparatorSourceContextIds", sources)
        holdouts = references(rule, "ValidationBlockerIds", protocols)
        require(keys and contexts and holdouts and all(rule[field].strip() for field in ASSESSMENT_FIELDS), f"{rid}: incomplete assessment")
        for key in keys:
            require(key not in by_key and priorities[key]["PriorityClass"] == category, f"{key}: duplicate or incompatible assessment")
            by_key[key] = rule
    expected = {key for key, row in priorities.items() if row["PriorityClass"] in DETAILED_PRIORITIES}
    require(by_key.keys() == expected and len(by_key) == 110, "A priority parameter lacks a specific Phase 3 assessment")
    return by_key


def input_assessment(priority):
    experimental = priority["PriorityClass"] == "EXPERIMENTAL_CONDITION_INPUT"
    require(experimental or priority["PriorityClass"] == "ENGINEERING_OR_NUMERICAL", "Missing scientific parameter assessment")
    if experimental:
        return dict(
            IdentifiabilityStatus=INPUT, TargetEndpoint="Document the matched exposure, initialization or control treatment",
            QuantitativeEvidenceStatus="ASSAY_OR_SOFTWARE_CONTROL", ComparatorSourceContextIds="",
            ExistingQuantitativeEvidence="Use actual assay input records and any accepted condition references",
            MappingToCurrentParameter="The supplied value specifies the treatment or initialization rather than a fitted response",
            UnitConversionOrStatisticalModel="Record original units, conversion and measurement uncertainty at the correct biological level",
            CouplingAndIdentifiability="An undocumented input can confound a behavioral contrast; shared policy selectors remain explicit",
            ProposedTreatment="Use matched declared measurements or freeze the control arm",
            RangeBasis="Use measured input variation and declared apparatus or fixture bounds",
            ValidationBlockerIds=priority["AssociatedBlockerIds"],
        )
    return dict(
        IdentifiabilityStatus=INPUT, TargetEndpoint="Verify numerical accuracy, deterministic observation and representation at matched conditions",
        QuantitativeEvidenceStatus="ASSAY_OR_SOFTWARE_CONTROL", ComparatorSourceContextIds="",
        ExistingQuantitativeEvidence="Use frozen code, configuration, workload and unit conventions for the current field",
        MappingToCurrentParameter="The representation, limit or scheduler convention remains an engineering control",
        UnitConversionOrStatisticalModel="Use declared dimensional arithmetic, resolution convergence and paired software runs",
        CouplingAndIdentifiability="An engineering bound may affect effective behavior and needs a sensitivity check before causal interpretation",
        ProposedTreatment="Freeze the software control and test invariants and observational effects",
        RangeBasis="Use supported bounds, checked precision and stable-workload engineering tests",
        ValidationBlockerIds="",
    )


def use_plans(priority, status):
    uses = json.loads(priority["UseDispositionsJson"])
    for use in uses:
        require(use["AcceptedApplicability"] in {"NO", "NOT_APPLICABLE"}, f"{priority['ParameterKey']}: accepted calibration status changed")
        use["Phase3UseStatus"] = INPUT if use["AcceptedApplicability"] == "NOT_APPLICABLE" else status
    return uses


def identifiability(parameters, priorities, assessments, protocols):
    require(parameters.keys() == priorities.keys() and len(parameters) == 249, "Accepted parameter coverage changed")
    result = []
    use_count = 0
    for key, parameter in parameters.items():
        priority = priorities[key]
        rule = assessments.get(key)
        assessment = fields(rule, ASSESSMENT_FIELDS) if rule is not None else input_assessment(priority)
        use_status = assessment["IdentifiabilityStatus"]
        uses = use_plans(priority, use_status)
        use_count += len(uses)
        linked = references(assessment, "ValidationBlockerIds", protocols)
        require(parameter["ParameterEvidenceClass"] == "ENGINEERING_FIXTURE" and parameter["AtlasGrade"] == "F",
                f"{key}: accepted value provenance changed")
        result.append(dict(
            **fields(parameter, ("ParameterKey", "SourceFile", "StartLine", "EndLine", "SourceSymbol", "SourceAnchorIds",
                                 "SourceSpanSha256", "SourceExpression", "CurrentSourceValue", "Unit", "Scope", "Role",
                                 "MechanismIds", "Domains", "ParameterEvidenceClass", "AtlasGrade")),
            Phase2PriorityClass=priority["PriorityClass"], AcceptedAssociatedBlockerIds=priority["AssociatedBlockerIds"],
            Phase1CalibrationApplicability=priority["Phase1CalibrationApplicability"],
            AcceptedSourceContextIds=parameter["SourceContextIds"], EvaluationRuleId=rule["RuleId"] if rule else "",
            **assessment,
            PlanningOnlyBlockerIds=";".join(bid for bid in linked if bid not in list_field(priority["AssociatedBlockerIds"])),
            IndependentHoldoutIds=";".join(protocols[bid]["HeldOutDatasetId"] for bid in linked),
            UsePlansJson=compact(uses),
        ))
    require(use_count == 369 and sum(row["Phase1CalibrationApplicability"] == "CONTEXT_DEPENDENT" for row in result) == 25,
            "Accepted parameter-use context coverage changed")
    require([row["ParameterKey"] for row in result if row["IdentifiabilityStatus"] == DERIVED] == ["PhysiologyConfig.egg_duration"]
            and all(row["IdentifiabilityStatus"] != DIRECT for row in result), "An unreviewed direct or derived estimate was introduced")
    return result


def run(write_derived):
    verify_frozen_inputs()
    sources = read_index(SOURCES, "SourceContextId")
    blockers = read_index(BLOCKER_FILE, "BlockerId")
    protocols = read_index(PROTOCOLS, "BlockerId")
    priorities = read_index(PARAMETER_FILE, "ParameterKey")
    parameters = read_index("INTEGRATED_PARAMETER_EVIDENCE.csv", "ParameterKey")
    require(len(sources) == 61, "Accepted source context coverage changed")
    require(heading_ids(INDEPENDENT_PLAN, "BR-") == protocols.keys(), "A protocol is missing from the independent plan")
    verify_protocols(protocols, blockers, sources)
    data = availability(sources, protocols)
    assessments = parameter_rules(read_index(RULES, "RuleId"), priorities, sources, protocols)
    plans = identifiability(parameters, priorities, assessments, protocols)
    check_table(REVIEW / DATA, data, write_derived)
    check_table(REVIEW / PARAMETERS, plans, write_derived)
    print("Verified 249 parameter assessments, including 110 targeted assessments and all 369 use contexts.")
    print("Verified 9 planned protocols, 61 accepted source contexts and 9 prospective holdouts with no registered independent data.")
    print("Identifiability:", dict(sorted(Counter(row["IdentifiabilityStatus"] for row in plans).items())))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-derived", action="store_true", help="Regenerate the parameter and availability CSVs")
    try:
        run(parser.parse_args().write_derived)
    except (OSError, KeyError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Scientific validation planning check failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
