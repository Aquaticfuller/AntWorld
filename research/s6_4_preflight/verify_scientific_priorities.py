#!/usr/bin/env python3
"""Verify Phase 2 classifications and their links to the accepted scientific audit."""

import argparse
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from graphlib import TopologicalSorter

from verify_batch1 import REVIEW, ROOT, index, list_field, require, rows
from verify_scientific_integration import check_table, compact, fields, unique


APPROVED = "2fb9da7a602235a33ed11cc96ee54ab64b2f0f2b"
MECHANISM_FILE = "S6_4_PHASE2_MECHANISM_PRIORITY.csv"
BLOCKER_FILE = "S6_4_PHASE2_BLOCKER_REGISTER.csv"
PARAMETER_FILE = "S6_4_PHASE2_PARAMETER_PRIORITY.csv"
SCOPE_FILE = "S6_4_PHASE2_READINESS_SCOPE.md"
BLOCKING = "BLOCKING_FOR_BIOLOGICAL_READINESS"
CLASSES = {
    BLOCKING, "HIGH_PRIORITY_MODEL_REMEDIATION", "CALIBRATION_REQUIRED", "VALIDATION_REQUIRED",
    "OPTIONAL_BIOLOGICAL_EXTENSION", "ENGINEERING_ONLY",
}

MEASURE = "EMPIRICAL_CALIBRATION_REQUIRED"
RANGE = "SENSITIVITY_RANGE_REQUIRED"
INPUT = "EXPERIMENTAL_CONDITION_INPUT"
SOFTWARE = "ENGINEERING_OR_NUMERICAL"
UNIDENTIFIED = "CURRENTLY_NOT_IDENTIFIABLE"


def members(owner, *names):
    return tuple(f"{owner}.{name}" for name in names)


# These groups describe the scientific use of a field, separately from its frozen software role and provenance.
PARAMETER_GROUPS = (
    (MEASURE, "Measure individual stage durations with matched landmarks, nutrition and temperature. Preserve within-queen nesting",
     members("PhysiologyConfig", "egg_duration", "larva_duration", "pupa_duration")),
    (MEASURE, "Measure matched caste, age, mass and actual activity budgets with respiration or other usable energy observations",
     members("PhysiologyConfig", "active_nj_per_ms", "basal_nj_per_ms")),
    (MEASURE, "Measure water flux under matched humidity and temperature. Only the loss rate is biological after fixing the numerical period",
     ("PhysiologyConfig.water_loss_ug_per_period",)),
    (MEASURE, "Measure time-resolved intake, crop contents, uptake and body state under known component doses before setting an effective rate",
     members("PhysiologyConfig", "carb_absorption_ug_per_s", "water_absorption_ug_per_s", "protein_absorption_ug_per_s")),
    (MEASURE, "Measure compartment capacity in the target caste and condition. An observed meal or a survival time alone cannot set the cap",
     members("PhysiologyConfig", "crop_capacity_ug", "hydration_capacity_ug")),
    (MEASURE, "Measure component export or usable offspring energy for viable first-worker eggs separately from maternal dissipation",
     members("ReproductionConfig", "egg_protein_ug", "egg_water_ug", "egg_energy_nj")),
    (MEASURE, "Measure actual loaded and unloaded travel by caste, stage, posture and load. The trained-worker returns do not cover all these states",
     members("CareMotionProfile", "queen_unloaded_m_per_s", "worker_unloaded_m_per_s", "queen_loaded_m_per_s", "worker_loaded_m_per_s")),
    (MEASURE, "Measure matched act durations with distinct onset and completion events. Record censored or interrupted bouts",
     (*members("CareMotionProfile", "manipulation_duration", "pickup_duration", "placement_duration"),
      "SpeciesCareProfile.worker_contact_duration")),
    (MEASURE, "Measure carrying and work costs under the specific load and material. Scale the motion or work representation with measured exposure",
     ("AntSeed.carrying_capacity_ug", "ReproductionConfig.offspring_carrying_capacity_ug",
      "GeometryConfig.dig_energy_nj_per_q3", "GeometryConfig.work_duration")),
    (UNIDENTIFIED, "Final survival and output confound effective yield, usable storage and cost. Require independent flux and reserve data",
     (*members("PhysiologyConfig", "carbohydrate_yield_nj_per_ug", "energy_capacity_nj"), "ReproductionConfig.dissipated_energy_nj")),
    (UNIDENTIFIED, "Observed transfers, uptake and juvenile growth do not identify exact-ingredient signal, requested dose, hard cap or threshold independently",
     (*members("PhysiologyConfig", "larval_protein_requirement_ug", "adult_protein_target_ug", "transfer_limit_ug"),
      "NutritionProposal.requested_ug", "offspring_adult_protein_target", "depot_local_demand_max",
      "nutrition_fraction_guards", "nutrient_signal_quarter")),
    (UNIDENTIFIED, "The attempt clock and reserve guard are unobserved policy components. Birth counts combine opportunities, successful allocation and censoring",
     (*members("ReproductionConfig", "interval", "maintenance_horizon"), "maternal_reserve_inequalities")),
    (UNIDENTIFIED, "Mark counts, effective behavioral aging and cue choice cannot independently set an unscaled field, cutoff, decay and response",
     (*members("BehaviorConfig", "deposit_units", "trail_cap_units", "trail_cutoff_units", "trail_half_life_s", "trail_weight"),
      "trail_exponential_decay")),
    (UNIDENTIFIED, "Private route recall and search paths confound weights, exposure and memory. A hard expiry or exact effective coefficient has no matched estimate",
     (*members("BehaviorConfig", "memory_lifetime", "explore_weight", "persistence_weight"),
      "visited_step_weight", "initial_heading_rule")),
    (UNIDENTIFIED, "Different combinations of access, detection, timing and contact gating reproduce the same observed care scans",
     (*members("SpeciesCareProfile", "care_probability", "maximum_inhibition", "worker_contact_probability", "social_memory_horizon"),
      "Queen social recency function", "Sheltered manipulation weights")),
    (UNIDENTIFIED, "Relative weights and overlapping eligibility are confounded with dwell and real act execution. Marginal task occupation cannot identify the lottery",
     members("SocialConfig", "forage_weight", "nurse_weight", "rest_weight", "excavate_weight")),
    (UNIDENTIFIED, "Local crowding, substrate and permission to excavate are confounded in removed volume. No matched evidence identifies the vacancy and contact thresholds",
     ("LongTermConfig.empty_sites_per_contact", "space_demand_contact_minimum", "excavation_contact_minimum")),
    (RANGE, "Bound the discrete movement and local cue approximation against matched trajectories and exposure. Examine numerical resolution and failed trips",
     (*members("BehaviorConfig", "max_trip_moves", "route_capacity", "sensing_radius_cells", "step_duration"),
      "sole_predecessor_cue", "WorldConfig.max_speed_m_per_s", "ExcavatorState.path")),
    (RANGE, "Treat the reach and movement rule as a local approximation. Check actual proximity, handling, search and unsuccessful events across defensible ranges",
     (*members("SpeciesCareProfile", "bout_duration", "decision_interval", "perception_radius_m", "step_m", "arrangement_m"),
      *members("CareMotionProfile", "search_pause", "search_steps"), "Planar empty-view search", "WorldConfig.contact_distance_m")),
    (RANGE, "Quantized clearance, reach and work geometry affect access and transport. Test spatial resolution with fixed physical inputs",
     (*members("GeometryConfig", "reach_q", "body_half_q", "loaded_half_q", "max_patch_extent_q", "decision_delay", "move_duration"),
      "Frontier slab thickness and loaded span")),
    (RANGE, "Scheduled decisions and hard gates affect encounter or expenditure dynamics. Check sensitivity and alignment with observed time and flux",
     (*members("PhysiologyConfig", "behavior_interval", "absorption_period"),
      *members("SocialConfig", "encounter_budget", "decision_interval", "minimum_program_time"),
      "Care capacity cutoff", "task_urgent_reserve_fraction", "zero_reserve_death", "active_metabolic_gate")),
    (RANGE, "Use explicit policy or ablation settings and compare resulting behaviors. A switch does not represent a measured species probability",
     (*members("BehaviorConfig", "memory_enabled", "trails_enabled"), "CareMotionProfile.integrate_autonomy",
      *members("SpeciesCareProfile", "local_retrieval", "motion"),
      *members("LongTermConfig", "demand_feedback", "protein_recycling", "complete_depot_visits", "post_intake_contact"),
      *members("SocialConfig", "bounded_contacts", "demand_sensitive", "exchange_enabled", "gift_first", "local_work_continuation"))),
    (INPUT, "Match the starting cohort, assay or supplied ration. An externally selected condition is not a fitted response or a natural default",
     (*members("AntSeed", "position", "stage", "caste"),
      *members("FoodMass", "carbs_ug", "protein_ug", "water_ug", "other_ug"),
      *members("PlaceFoodCommand", "position", "mass"),
      *members("EnvironmentCareProfile", "arena_radius_m", "neutral_displacement_assay", "relative_humidity", "temperature_c"),
      *members("IndividualCareProfile", "context", "age_at_enrollment"))),
    (INPUT, "Match or document the distribution of observed starting reserves. Fixture defaults do not estimate real founding reserves",
     members("PhysiologySeed", "crop", "body_energy_nj", "hydration_ug", "tissue_protein_ug")),
    (INPUT, "Declare arena and substrate conditions from measurements. Converting physical density to quantized units does not fit a digging response",
     (*members("SurfaceConfig", "origin_m", "width", "height"), *members("WorldConfig", "min_m", "max_m"),
      *members("GeometryConfig", "origin_m", "initial_solid", "dry_ug_per_q3", "water_ug_per_q3"))),
    (INPUT, "Supply the actual experimental ration and timing as exogenous inputs. Natural productivity needs evidence beyond the proposed scope",
     (*members("ResourceCycleConfig", "release_limit", "reserve", "interval", "productive_span", "low_productivity_permille", "cyclic"),
      "resource_cycle_productivity_scaling")),
    (SOFTWARE, "Preserve dimensional arithmetic and numerical fidelity. Compare the biological rate separately from the time step or accumulator",
     ("PhysiologyConfig.water_loss_period", "water_loss_integrator", "absorption_pulse_conversion")),
)


def parameter_actions():
    result = {}
    for classification, reason, keys in PARAMETER_GROUPS:
        for key in keys:
            require(key not in result, f"Duplicate parameter disposition {key}")
            result[key] = (classification, reason)
    return result


def verify_frozen_phase1():
    # New Phase 2 artifacts are additions. An earlier accepted file can only change in the Evidence CI workflow.
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
    require(not unexpected, f"Accepted Phase 1 paths changed: {', '.join(sorted(unexpected))}")


def table(filename, key):
    return index(rows(REVIEW / filename), key)


def heading_ids(filename, prefix):
    body = (REVIEW / filename).read_text(encoding="utf-8")
    matches = re.findall(rf"^## ({re.escape(prefix)}\d\d)\b", body, re.MULTILINE)
    require(len(matches) == len(set(matches)), f"{filename}: duplicate section identity")
    return set(matches)


def references(record, column, allowed):
    refs = list_field(record[column])
    require(len(refs) == len(set(refs)) and set(refs) <= set(allowed),
            f"{next(iter(record.values()))}: bad or repeated {column}")
    return refs


def verify_classification(record):
    category = record["PrimaryClassification"]
    require(category in CLASSES, f"{next(iter(record.values()))}: invalid classification")
    references(record, "SecondaryClassifications", CLASSES - {category})


def source_basis(accepted):
    grades = {cite["AtlasGrade"] for cite in json.loads(accepted["CitationsJson"])}
    if "A" in grades:
        return "DIRECT_QUANTITATIVE_COMPARATOR"
    if "B" in grades:
        return "DIRECT_OBSERVATIONAL_COMPARATOR"
    if grades & {"C", "D", "E"}:
        return "CROSS_SPECIES_COMPARATOR"
    return "NO_EMPIRICAL_COMPARATOR"


def verify_mechanisms(priorities, accepted, transitions, parameters, blockers, scope):
    require(len(priorities) == 75 and priorities.keys() == accepted.keys(), "Mechanism coverage differs from Phase 1")
    by_mid = defaultdict(list)
    for tid, row in transitions.items():
        by_mid[row["MechanismId"]].append(tid)
    referenced_transitions = set()
    referenced_parameters = set()
    projection = {
        "Domain": "Domain", "SourceContextIds": "SourceContextIds", "CitedAtlasGrades": "CitedAtlasGrades",
        "AcceptedMechanismEvidenceClass": "MechanismEvidenceClassification",
        "Phase1ScientificBlockerStatus": "ScientificBlockerStatus", "Phase1ConflictIds": "CrossDomainConflictIds",
        "AssociatedParameterKeys": "OwnerAssociatedParameterKeys",
    }
    for mid, row in priorities.items():
        verify_classification(row)
        original = accepted[mid]
        require(all(row[field] == original[source] for field, source in projection.items()), f"{mid}: changed accepted evidence")
        require(row["SourceBasis"] == source_basis(original), f"{mid}: source strength differs from accepted grades")
        require(row["ScopeId"] in scope and row["AssessmentBasis"].strip() and row["EndpointOrBoundary"].strip(),
                f"{mid}: missing scope, rationale or endpoint")
        primary = row["PrimaryBlockerId"]
        require(bool(primary) == (row["PrimaryClassification"] == BLOCKING) and (not primary or primary in blockers),
                f"{mid}: missing or inconsistent primary blocker")
        references(row, "RelatedBlockerIds", set(blockers) - {primary})
        tids = references(row, "TransitionIds", transitions)
        require(tids == by_mid[mid], f"{mid}: transition associations changed")
        referenced_transitions.update(tids)
        referenced_parameters.update(references(row, "AssociatedParameterKeys", parameters))
    require(referenced_transitions == transitions.keys() and referenced_parameters == parameters.keys(),
            "Integrated transition or parameter identities lack a mechanism decision")


def verify_source_links(blocker, scope_mechanisms, mechanisms, sources):
    block = blocker["BlockerId"]
    links = json.loads(blocker["PrimaryEvidenceLinksJson"])
    evidence_identities = set()
    direct = False
    for link in links:
        mid, context = link["MechanismId"], link["SourceContextId"]
        identity = (mid, context, link["OriginalSourceId"])
        require(mid in scope_mechanisms and identity not in evidence_identities, f"{block}: repeated or unrelated source link")
        evidence_identities.add(identity)
        source = sources[context]
        require(link["BiologicalSampleUnit"] == source["BiologicalSampleUnit"] and source["ActualMeasuredEndpoint"].strip(),
                f"{block}: missing or changed source endpoint or sample unit")
        cite = {key: value for key, value in link.items() if key not in {"MechanismId", "BiologicalSampleUnit"}}
        require(cite in json.loads(mechanisms[mid]["CitationsJson"]) and cite["Locators"], f"{block}: source or locator changed")
        direct |= cite["EvidenceClassification"] == "DIRECT_SPECIES_DATA" and cite["AtlasGrade"] in {"A", "B"}
    require(links and direct, f"{block}: no accepted direct species source")


def verify_blockers(blockers, priorities, mechanisms, sources, scopes, conflicts, parameters):
    require(set(blockers) == {f"BR-{number:02}" for number in range(1, 10)}, "Blocker identity coverage changed")
    dependency_graph = {}
    all_conflicts = set()
    required_fields = (
        "Title", "Problem", "MagnitudeAndComparisonLimit", "ExistingEvidenceUse", "AdditionalEvidenceNeeded",
        "MinimumClearanceEvidence", "PermittedSimplification", "RemainsOpenIf",
    )
    for bid, row in blockers.items():
        verify_classification(row)
        require(row["PrimaryClassification"] == BLOCKING and row["Status"].startswith("OPEN_"), f"{bid}: premature blocker closure")
        require(all(row[field].strip() for field in required_fields), f"{bid}: incomplete clearance criteria")
        scope = references(row, "ProposedScopeIds", scopes - {"SC-10", "SC-11"})
        primary = [mid for mid, review in priorities.items() if review["PrimaryBlockerId"] == bid]
        support = [mid for mid, review in priorities.items() if bid in list_field(review["RelatedBlockerIds"])]
        require(primary and list_field(row["PrimaryMechanismIds"]) == primary and list_field(row["SupportingMechanismIds"]) == support,
                f"{bid}: blocker and mechanism membership disagree")
        require(scope and {priorities[mid]["ScopeId"] for mid in primary} <= set(scope), f"{bid}: direct mechanisms outside scope")
        expected_transitions = [tid for mid in primary for tid in list_field(priorities[mid]["TransitionIds"])]
        require(list_field(row["PrimaryMechanismTransitionIds"]) == expected_transitions, f"{bid}: wrong transition scope")
        linked_mids = set(primary + support)
        linked_parameters = {key for mid in linked_mids for key in list_field(priorities[mid]["AssociatedParameterKeys"])}
        require(references(row, "KeyParameterReferences", linked_parameters & parameters.keys()), f"{bid}: no linked parameters")
        linked_conflicts = {cid for mid in linked_mids for cid in list_field(mechanisms[mid]["CrossDomainConflictIds"])}
        issue_conflicts = references(row, "AcceptedCrossDomainConflictIds", linked_conflicts & conflicts)
        require(issue_conflicts, f"{bid}: no link to an accepted cross-domain finding")
        all_conflicts.update(issue_conflicts)
        verify_source_links(row, linked_mids, mechanisms, sources)
        archive = list_field(row["ArchivedSimulationOrAuditRefs"])
        require(archive and all((ROOT / name).is_file() for name in archive), f"{bid}: missing historical reference")
        dependency_graph[bid] = references(row, "PriorBlockerEvidence", set(blockers) - {bid})
    TopologicalSorter(dependency_graph).prepare()
    require(all_conflicts == conflicts - {"INT-C11"}, "Expected cross-domain finding coverage changed")


def priority_for(record, actions):
    key = record["ParameterKey"]
    if key in actions:
        return actions[key]
    if key.startswith(("Controls.", "IntegratedOptions.")):
        return INPUT, "This selects a fixture arm or input. Observe the corresponding condition or test the selected policy, without fitting the fixture control"
    require(record["CalibrationApplicability"] == "NON_CALIBRATION_CONTEXT", f"{key}: no decision for a biological-use candidate")
    return SOFTWARE, "Treat the representation, limit or scheduling convention as engineering. Check numerical fidelity for the associated behavior"


def priority_use(use, classification):
    status = use["CanCalibrateCurrentValue"]
    require(status in {"NO", "NOT_APPLICABLE"}, "Phase 1 parameter calibration status changed")
    if status == "NOT_APPLICABLE":
        action = "KEEP_AS_RECORDED_CONTEXT"
    else:
        action = {
            MEASURE: "NEEDS_MATCHED_MEASUREMENT",
            RANGE: "NEEDS_BEHAVIORAL_RANGE_OR_CONTRAST",
            INPUT: "MATCH_CONDITION_OR_TEST_SELECTED_POLICY",
            SOFTWARE: "SEPARATE_SOFTWARE_CONVENTION_FROM_MEASURED_RATE",
            UNIDENTIFIED: "NO_IDENTIFIED_ESTIMAND_FOR_CURRENT_RULE",
        }[classification]
    return dict(
        Batch=use["Batch"], AcceptedReviewFile=use["AcceptedReviewFile"],
        MechanismIds=[entry["MechanismId"] for entry in use["MechanismUses"]],
        Domains=unique(entry["Domain"] for entry in use["MechanismUses"]),
        AcceptedApplicability=status, AcceptedAssessment=use["CalibrationAssessment"],
        AcceptedUseExplanation=use.get("EvidenceApplicability", use.get("UnitConversionAndSourceDifference", "")),
        Phase2Action=action,
    )


def parameter_priorities(accepted, priorities):
    actions = parameter_actions()
    require(actions.keys() <= accepted.keys(), "Unknown parameter in priority groups")
    result = []
    use_count = 0
    for key, record in accepted.items():
        require(record["ParameterEvidenceClass"] == "ENGINEERING_FIXTURE" and record["AtlasGrade"] == "F",
                f"{key}: Phase 1 fixture evidence changed")
        classification, reason = priority_for(record, actions)
        mids = list_field(record["MechanismIds"])
        blockers = unique(bid for mid in mids
                          for bid in list_field(priorities[mid]["PrimaryBlockerId"]) + list_field(priorities[mid]["RelatedBlockerIds"]))
        uses = [priority_use(use, classification) for use in json.loads(record["UseAssessmentsJson"])]
        use_count += len(uses)
        require(uses and set(mid for use in uses for mid in use["MechanismIds"]) == set(mids), f"{key}: incomplete use contexts")
        result.append(dict(
            **fields(record, ("ParameterKey", "ValueRoleClass", "SourceFile", "StartLine", "EndLine", "SourceAnchorIds",
                              "SourceSymbol", "CurrentSourceValue", "Unit", "Scope", "Role", "MechanismIds",
                              "Domains", "ParameterEvidenceClass", "AtlasGrade")),
            PriorityClass=classification, PriorityBasis=reason, AssociatedBlockerIds=";".join(blockers),
            Phase1CalibrationApplicability=record["CalibrationApplicability"], UseDispositionsJson=compact(uses),
        ))
    contexts = [row for row in result if row["Phase1CalibrationApplicability"] == "CONTEXT_DEPENDENT"]
    require((len(result), use_count, len(contexts)) == (249, 369, 25), "Parameter or shared-context coverage changed")
    for row in contexts:
        uses = json.loads(row["UseDispositionsJson"])
        require({use["AcceptedApplicability"] for use in uses} == {"NO", "NOT_APPLICABLE"}
                and all(use["AcceptedUseExplanation"] for use in uses), f"{row['ParameterKey']}: lost context-specific calibration judgment")
    return result


def run(write_parameters):
    verify_frozen_phase1()
    mechanisms = table("INTEGRATED_MECHANISM_EVIDENCE.csv", "MechanismId")
    transitions = table("INTEGRATED_TRANSITION_EVIDENCE.csv", "TransitionId")
    parameters = table("INTEGRATED_PARAMETER_EVIDENCE.csv", "ParameterKey")
    sources = table("UNIFIED_SOURCE_CONTEXT_REGISTER.csv", "SourceContextId")
    priorities = table(MECHANISM_FILE, "MechanismId")
    blockers = table(BLOCKER_FILE, "BlockerId")
    scopes = heading_ids(SCOPE_FILE, "SC-")
    conflicts = heading_ids("CROSS_DOMAIN_CONFLICTS.md", "INT-C")
    require(len(scopes) == 12 and len(conflicts) == 12 and (len(transitions), len(sources)) == (99, 61),
            "Proposed scope or accepted evidence coverage changed")
    require(heading_ids("UNRESOLVED_GAPS.md", "BR-") == blockers.keys(), "An open blocker is absent from the gap report")
    verify_mechanisms(priorities, mechanisms, transitions, parameters, blockers, scopes)
    verify_blockers(blockers, priorities, mechanisms, sources, scopes, conflicts, parameters)
    result = parameter_priorities(parameters, priorities)
    check_table(REVIEW / PARAMETER_FILE, result, write_parameters)
    flags = "YES_FOR_SPECIFIED_CLAIMS"
    require(sum(row["ScientificBlockerStatus"] == flags for row in mechanisms.values()) == 34
            and sum(row["ScientificBlockerStatus"] == flags for row in transitions.values()) == 26,
            "Accepted Phase 1 claim-marker counts changed")
    print("Verified 75 mechanism decisions, 99 transition references, 249 parameters and 25 context-dependent parameters.")
    direct = sum(bool(row["PrimaryBlockerId"]) for row in priorities.values())
    print(f"Verified {len(blockers)} open root blockers, {direct} direct mechanism links and original evidence references.")
    print("Mechanism priorities:", dict(sorted(Counter(row["PrimaryClassification"] for row in priorities.values()).items())))
    print("Parameter dispositions:", dict(sorted(Counter(row["PriorityClass"] for row in result).items())))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-parameters", action="store_true", help="Regenerate the derived parameter priority table")
    try:
        run(parser.parse_args().write_parameters)
    except (OSError, KeyError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Scientific priorities check failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
