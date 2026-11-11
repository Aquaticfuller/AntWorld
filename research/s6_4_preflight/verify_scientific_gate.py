#!/usr/bin/env python3
"""Verify the scientific gate against the approved Phase 3 identities and Core."""

import json
import re
import subprocess
import sys
from collections import Counter
from graphlib import TopologicalSorter
from hashlib import sha256

from verify_batch1 import REVIEW, ROOT, list_field, require
from verify_scientific_priorities import BLOCKER_FILE, heading_ids, references
from verify_scientific_validation_plan import (
    DATA, DERIVED, HOLDOUT_MISSING, INPUT, NEED_DATA, PARAMETERS, PROTOCOLS, SOURCES, UNIDENTIFIED, read_index,
)


APPROVED = "80fa974689fc15b6deef404e64bf7721c28fe57f"
CORE_TREE = "277cc8e78cc1acd1cf4a74bf39d08dfdb6a99c69"
BACKLOG = "S6_4_PHASE4_REMEDIATION_BACKLOG.csv"
MATRIX = "S6_4_PHASE4_IMPLEMENTATION_AUTHORIZATION_MATRIX.csv"
ACQUISITION = "S6_4_PHASE4_DATA_ACQUISITION_REGISTER.csv"
ROADMAP = "MODEL_REMEDIATION_ROADMAP.md"
GATE = "S6_4_PHASE4_FIRST_IMPLEMENTATION_GATE.md"
BLOCKERS = {f"BR-{number:02}" for number in range(1, 10)}
PACKAGE_BLOCKERS = dict(zip(
    (f"RM-{number:02}" for number in range(1, 11)),
    ("BR-04", "BR-02", "BR-05", "BR-01", "BR-04", "BR-03", "BR-06", "BR-07", "BR-08", "BR-09"),
))
REQUIRED_CHANGES = {"BR-01", "BR-02", "BR-04", "BR-05", "BR-07"}
PREREQUISITES = {
    "RM-04": {"RM-02", "RM-03", "RM-06"},
    "RM-05": {"RM-01", "RM-02", "RM-03", "RM-04"},
    "RM-08": {"RM-02", "RM-03", "RM-07"},
    "RM-09": {"RM-02", "RM-03", "RM-04", "RM-05"},
    "RM-10": {"RM-03"},
}
CANDIDATE_BLOCKERS = {
    "CAND-01": {"BR-01", "BR-08"}, "CAND-02": {"BR-05"}, "CAND-03": {"BR-06", "BR-07"},
    "CAND-04": {"BR-06", "BR-07"}, "CAND-05": {"BR-09"}, "CAND-06": {"BR-01"},
}
SOURCE_AVAILABILITY = {
    "REF-B06-SUMMARY": ("BR-04", "VERIFIED", "INELIGIBLE_AS_INDEPENDENT"),
    "REF-B06-ROWS": ("BR-04", "NOT_FOUND", "INELIGIBLE_AS_INDEPENDENT"),
    "REF-ZJTSDI": ("BR-09", "RESTRICTED", "INELIGIBLE_AS_INDEPENDENT"),
    "REF-LECKIE-CT": ("BR-09", "NOT_FOUND", "UNSCREENED_PARTIAL_CANDIDATE"),
}
SOURCE_PATHS = {
    "cpp/apps/s6_3_1_fixture.hpp",
    "cpp/include/antworld/core/physiology.hpp",
    "cpp/include/antworld/core/long_term.hpp",
    "cpp/include/antworld/core/world_runtime.hpp",
    "cpp/src/physiology.cpp",
    "cpp/src/physiology_internal.hpp",
    "cpp/src/long_term.cpp",
    "cpp/src/checkpoint_s3.hpp",
    "cpp/CMakeLists.txt",
}
FROZEN_BLOCKER_FIELDS = (
    "Title", "ProposedScopeIds", "PrimaryMechanismIds", "PrimaryMechanismTransitionIds",
    "KeyParameterReferences", "AcceptedCrossDomainConflictIds",
)


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def verify_frozen_inputs():
    changed = git("diff", "--no-renames", "--name-status", APPROVED, "--").decode("utf-8").splitlines()
    for entry in changed:
        status, path = entry.split("\t", 1)
        allowed = path == ".github/workflows/s6_4_preflight.yml" and status == "M"
        allowed |= status == "A" and path.startswith("research/s6_4_preflight/")
        require(allowed, f"Phase 4 changed an accepted path or added an out-of-scope path: {path}")
    require(git("rev-parse", f"{APPROVED}:cpp", "HEAD:cpp").decode().splitlines() == [CORE_TREE, CORE_TREE],
            "Frozen C++ tree identity changed")
    gate = (REVIEW / GATE).read_text(encoding="utf-8")
    matches = re.findall(r"^\| `(cpp/[^`]+)` \| `([0-9a-f]{64})` \|$", gate, re.MULTILINE)
    require(len(matches) == len(SOURCE_PATHS) and {path for path, _ in matches} == SOURCE_PATHS,
            "The first gate must pin all nine source blobs")
    for path, digest in matches:
        require(sha256(git("show", f"{APPROVED}:{path}")).hexdigest() == digest, f"{path}: frozen SHA-256 mismatch")


def verify_backlog(backlog, frozen, protocols, sources):
    require(backlog.keys() == frozen.keys() == protocols.keys() == BLOCKERS, "Expected all nine root blockers")
    for bid, row in backlog.items():
        require(all(row[field] == frozen[bid][field] for field in FROZEN_BLOCKER_FIELDS),
                f"{bid}: changed accepted identity or conflict references")
        protocol = protocols[bid]
        require(row["AcceptedSourceLinksJson"] == protocol["AcceptedSourceLinksJson"]
                and row["AcceptedSourceContextIds"] == protocol["SourceContextIds"]
                and row["RequiredIndependentDatasetId"] == protocol["HeldOutDatasetId"],
                f"{bid}: changed source or independent-validation reference")
        references(row, "AcceptedSourceContextIds", sources)
        require(row["BiologicalStatus"] == "BLOCKED" and row["ValidatedOutcome"] == "NOT_RUN"
                and row["CurrentDefaultAdoption"] == "NOT_AUTHORIZED", f"{bid}: premature biological clearance")
        expected = "REQUIRED" if bid in REQUIRED_CHANGES else "CONDITIONAL_ON_MATCHED_RESIDUAL_ERROR"
        require(row["MechanismChangeDecision"] == expected, f"{bid}: remediation decision drift")
        require(all(row[field].strip() for field in (
            "CalibrationDisposition", "AdmissibleSimplification", "NewDataBeforeBiologicalImplementation",
            "AllowedTechnicalPrecursor", "BiologicalClearance",
        )), f"{bid}: missing remediation boundary")


def verify_packages(packages, backlog, protocols):
    require(packages.keys() == PACKAGE_BLOCKERS.keys() == heading_ids(ROADMAP, "RM-"), "Package coverage changed")
    dependencies = {}
    for pid, row in packages.items():
        bid = PACKAGE_BLOCKERS[pid]
        first = pid == "RM-01"
        require(row["PrimaryBlockerId"] == bid, f"{pid}: wrong root blocker")
        require(row["FrozenComparatorCommit"] == APPROVED and row["CoreTree"] == CORE_TREE,
                f"{pid}: frozen comparator changed")
        require(row["EngineeringGateRecommendation"] == (
            "GO_FOR_ISOLATED_ENGINEERING_EXPERIMENT" if first else "HOLD_FOR_EVIDENCE_AND_APPROVAL"),
            f"{pid}: premature engineering go")
        require(row["ActivationState"] == (
            "PENDING_INDEPENDENT_PHASE4_APPROVAL" if first else "REQUIRES_SEPARATE_REVIEW"),
            f"{pid}: missing independent approval boundary")
        require(row["BiologicalGateDecision"] == "BLOCKED" and row["DefaultChangeDecision"] == "NOT_AUTHORIZED",
                f"{pid}: biological or default adoption was authorized")
        expected_data = "" if first else protocols[bid]["HeldOutDatasetId"]
        require(row["RequiredIndependentDatasetIds"] == expected_data, f"{pid}: wrong independent dataset")
        dependencies[pid] = set(references(row, "PrerequisitePackageEvidenceIds", packages))
        require(dependencies[pid] == PREREQUISITES.get(pid, set()), f"{pid}: causal prerequisite drift")
        require(all(row[field].strip() for field in (
            "AllowedScope", "IndependentEngineeringAcceptance", "IndependentBiologicalAcceptance", "FailureAndRollback",
        )), f"{pid}: missing approval or rollback criteria")
    tuple(TopologicalSorter(dependencies).static_order())
    for bid, row in backlog.items():
        assigned = {pid for pid, blocker in PACKAGE_BLOCKERS.items() if blocker == bid}
        require(set(references(row, "PackageIds", packages)) == assigned, f"{bid}: inconsistent package assignment")


def verify_acquisition(registry, accepted_data):
    holdouts = {f"VAL-{bid}" for bid in BLOCKERS}
    require(registry.keys() == holdouts | CANDIDATE_BLOCKERS.keys() | SOURCE_AVAILABILITY.keys(),
            "The required, candidate or reference data records changed")
    require(holdouts == {key for key, row in accepted_data.items() if row["EvidenceRole"] == "PROSPECTIVE_HOLDOUT"},
            "Phase 3 holdout identities changed")
    require(heading_ids("S6_4_PHASE4_DATA_ACQUISITION_PLAN.md", "VAL-BR-") == holdouts, "A data route is undocumented")
    for key, row in registry.items():
        blockers = set(list_field(row["BlockerIds"]))
        require(all(row[field].strip() for field in ("AssetOrRequirement", "AccessEvidence", "PriorUse", "Action")),
                f"{key}: missing data provenance or next action")
        if key in holdouts:
            require(row["RecordKind"] == "REQUIRED_INDEPENDENT_SET" and blockers == {key.removeprefix("VAL-")}
                    and row["AvailabilityStatus"] == "PROPOSED_COLLECTION" and row["SearchForCompleteMatch"] == "NOT_FOUND"
                    and not row["SourceUrl"] and row["IndependentEligibility"] == "PENDING_ACQUISITION_AND_REVIEW"
                    and accepted_data[key]["Availability"] == HOLDOUT_MISSING, f"{key}: premature holdout availability")
        elif key in CANDIDATE_BLOCKERS:
            require(row["RecordKind"] == "PUBLIC_PARTIAL_CANDIDATE" and blockers == CANDIDATE_BLOCKERS[key]
                    and row["AvailabilityStatus"] == "AVAILABLE_NOT_ACQUIRED"
                    and row["IndependentEligibility"] == "UNSCREENED_PARTIAL_CANDIDATE", f"{key}: overstated partial data")
        else:
            blocker, status, eligibility = SOURCE_AVAILABILITY[key]
            require(row["RecordKind"] == "SOURCE_COMPONENT" and blockers == {blocker}
                    and (row["AvailabilityStatus"], row["IndependentEligibility"]) == (status, eligibility),
                    f"{key}: incorrect original-source status")
        if key not in holdouts:
            require(row["SourceUrl"].startswith("https://doi.org/") and not row["SearchForCompleteMatch"],
                    f"{key}: expected an exact source rather than a complete-match claim")


def verify_parameter_status(parameters):
    require(len(parameters) == 249 and all(
        row["ParameterEvidenceClass"] == "ENGINEERING_FIXTURE" and row["AtlasGrade"] == "F"
        for row in parameters.values()
    ), "Accepted parameter provenance changed")
    counts = Counter(row["IdentifiabilityStatus"] for row in parameters.values())
    require(counts == {DERIVED: 1, NEED_DATA: 28, UNIDENTIFIED: 56, INPUT: 164},
            "Parameter planning classes changed")
    require(parameters["PhysiologyConfig.egg_duration"]["IdentifiabilityStatus"] == DERIVED,
            "The conditional egg reference was lost or promoted")


def run():
    verify_frozen_inputs()
    frozen = read_index(BLOCKER_FILE, "BlockerId")
    protocols = read_index(PROTOCOLS, "BlockerId")
    sources = read_index(SOURCES, "SourceContextId")
    backlog = read_index(BACKLOG, "BlockerId")
    verify_backlog(backlog, frozen, protocols, sources)
    verify_packages(read_index(MATRIX, "PackageId"), backlog, protocols)
    verify_acquisition(read_index(ACQUISITION, "RecordId"), read_index(DATA, "DatasetId"))
    verify_parameter_status(read_index(PARAMETERS, "ParameterKey"))
    print("Verified the frozen Core tree, nine source SHA-256 digests and accepted evidence references.")
    print("Verified nine blocked roots, ten remediation packages, one pending technical recommendation and no default adoption.")
    print("Verified nine unacquired matched holdouts, six partial data candidates and all 249 parameter statuses.")


def main():
    try:
        run()
    except (OSError, KeyError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Scientific gate check failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
