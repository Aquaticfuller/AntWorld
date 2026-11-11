#!/usr/bin/env python3
"""Rebuild and verify the Phase 1 evidence tables from the accepted audit."""

import argparse
import csv
import io
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from functools import cache
from hashlib import sha256
from itertools import combinations

from verify_batch1 import CLASSES, REVIEW, ROOT, index, list_field, require, rows


APPROVED = "4dbafd087592b45d1b29101d67d35b400e388516"
DIRECT = "DIRECT_SPECIES_DATA"
CROSS = "CROSS_SPECIES_EXTRAPOLATION"
FIXTURE = "ENGINEERING_FIXTURE"
INVENTORY = "CURRENT_CORE_MECHANISM_INVENTORY.csv"
TRANSITIONS = "STATE_MACHINE_TRANSITION_EVIDENCE.csv"
PARAMETERS = "PARAMETER_EVIDENCE_MATRIX.csv"
FIXTURE_INDEX = "FIXTURE_CONFIGURATION_INDEX.csv"
BATCHES = (
    ("1", "", "SOURCE_ACCESS_AND_READING_LOG.csv"),
    ("2", "BATCH2_", "BATCH2_SOURCE_ACCESS_LOG.csv"),
    ("3", "BATCH3_", "BATCH3_SOURCE_ACCESS_LOG.csv"),
)

# Same focal study context, with the distinct endpoints and readings retained in SourceViewsJson.
CONTEXT_ALIASES = {
    "B3-T08": ("B01", "Same focal queen care, worker access and brood experiments"),
    "B3-P03": ("B03", "Same founding-diet design, 240 endpoints and regression sample"),
    "B3-P05": ("B06", "Same founder populations and temperature regimes"),
    "B3-P04": ("B07", "Same focal diet study and growth outcomes. The congener tracer has a separate context"),
    "B2-F02": ("R1C", "Same trained loaded-worker navigation study. The timed subset has a narrower sample"),
    "B3-T07": ("B2-F08", "Same scout observations under food type and brood manipulation"),
    "B3-N08": ("B2-F09", "Same planar sand-walking, texture-choice and conditioning assays"),
    "B3-T04": ("B2-P09", "Same scout and nestmate trials under 1, 4 and 8 days of deprivation"),
}

SAMPLE_UNITS = {
    "B01": "Founding or established queen per intervention. Scans, windows and time points repeat within queen",
    "B02": "One queen or worker trio. Brood-origin trials are paired within the same unit",
    "B03": "Individual founding queen per feeding arm. Offspring counts are nested outcomes",
    "B04": "Individual queen or pooled worker respirometry sample. Pool members are not independent runs",
    "B05": "Individual sampled at a reported stage. The comparison concerns sexual females and immature stages",
    "B06": "Foundress and first brood in a population and temperature regime. Stage observations are nested",
    "B07": "Colony for growth, with repeated censuses. Field preference is a separate colony assay",
    "B07-X": "Congener colony. Tissue type and sampling time are repeated pooled observations",
    "B08": "One run per source colony. Individual and dyadic contacts repeat within the five groups",
    "N01": "Source colony and experimental group. Oral bouts repeat within groups. Intake uses measured foragers",
    "N27": "Individual queen or worker measurement within device and species. Natal-colony independence is unestablished",
    "R1L": "Colony or experimental group, depending on assay. Retrieval ranks and repeated tests are nested",
    "R1C": "Trained worker, with repeated runs. Timed normal-light comparison uses trips from only two workers",
    "FT01": "Individual foundress per destructive sampling time. Sections and images are nested within individuals",
    "FT01-X": "Pictured Pachycondyla queen specimens. Independent replication is unreported",
    "B2-F01": "Worker trajectory within source colony. Time windows are repeated segments of a track",
    "B2-F03": "Worker within colony. The 69 archived horizontal tracks reuse B2-F01. New light trials repeat within worker",
    "B2-F04": "Scout group for intake or acceptance, with workers nested in groups and source colonies",
    "B2-F05": "Single-tested scout within source colony. Measurements of both drops repeat within scout",
    "B2-F06": "Naive ant or repeated decisions of a trained ant, nested within colony for each experiment",
    "B2-F07": "Individual worker within colony. Visits and choices repeat within worker",
    "B2-F08": "One scout per trial, nested in experimental nests and mother colonies",
    "B2-F09": "Experimental worker group for locomotion. Tracks and repeated choices are nested within groups and workers",
    "B2-F10": "Group trial for branch flows and choices. Separate individual encounters with marked paper",
    "B2-P01": "Naive worker choice nested in tested groups and four source colonies",
    "B2-P02": "Individually observed worker with repeated trajectory segments. Independent group count not established in the review",
    "B2-P03": "Worker within colony, with repeated trip and fork decisions. Route side is assigned within treatment and colony",
    "B2-P04": "Individual track or first branch choice within colony, in separate experiments",
    "B2-P05": "Source colony for width trials. Worker and repeated journeys within colony for bead manipulation",
    "B2-P06": "Worker trial within colony. Segment counts repeat within routes and workers",
    "B2-P07": "Colony trial. Choices and 20 min windows repeat within a trial",
    "B2-P08": "Colony and marked worker. Passage and mark counts repeat within workers",
    "B2-P09": "Single-scout assay within three stock colonies. Nestmates and contact events repeat within the scout window",
    "B2-P10": "Pooled gland extraction for chemistry. Independent behavioral and electrode replication is not reported",
    "B2-P11": "Colony for collective outcomes, with mirrored trials or first choices within colony",
    "B2-P12": "Naive individual choice with source-colony nesting in the focal-species assay",
    "B2-P12-C": "Naive individual choice in the congener assay. No pooling with focal choices",
    "B2-P13": "Individual worker nested within colony. Retest pairs share the same worker",
    "B2-P15": "Aged-bridge trial with recipient colony distinct from donor. Passage observations are repeated within trials",
    "B2-P16": "Ten-decision measurement group within colony material. Individual decisions are not independent groups",
    "B3-T01": "Five source colonies, with tagged individuals, scans and observation series nested within them",
    "B3-T02": "Paired forager and intranidal samples per colony. Head-width measurements are nested",
    "B3-T03": "Group for efficiency, with worker head widths nested in each group",
    "B3-T05": "Group of 20 per trial within two source colonies. Aggregation scans repeat",
    "B3-T06": "Group of 20 per tube-choice trial. Counts repeat every five minutes within trial",
    "B3-T09": "Pooled sample of 16 workers. Pools combine natal colonies and do not provide individual trajectories",
    "B3-N01": "Experimental excavation group within source colony. Time observations repeat within group",
    "B3-N02": "Excavation group per trial. Area and shape images repeat within trial",
    "B3-N03": "Experimental group of 50 within source colony. Repeated images within each 90 h assay",
    "B3-N04": "Construction arena replicate, separate field mound specimen and separate pellet encounters within pile or arena",
    "B3-N05": "Colony per thermal regime. CT scans repeat within colony. Ant-free controls are separate",
    "B3-N07": "Fire-ant excavation trial. Image frames and worker trajectories repeat within trial",
    "B3-P01": "Worker with repeated survival follow-up. Cohorts pool natal colonies and do not identify colony hazards",
    "B3-P02": "Queenless fragment within source colony. Daily counts repeat within fragment",
    "B3-P06": "One focal colony. Worker CTmin samples and pooled SMR batches are within-colony observations",
    "B3-P07": "Matched field plot and bait census across years. No individually tracked colonies",
    "B3-P08": "Treatment fragment within source colony. Ovary outcomes are nested within fragments",
    "B3-P09": "Worker survival within source colony and acclimation group. Focal and other species remain separate",
    "B3-P10": "Founding queen per treatment. The second brood is conditional on survival",
    "B3-P11": "Colony lineage. The second-year rearrangement does not provide a new independent lineage",
    "B3-P12": "Individual foundress in solitary assays or colony in the worker assay, with repeated within-colony outcomes",
}

# Prior conflict IDs also attach the related parameter reviews, including shared uses.
# Mechanisms listed here lack support for the named claim in the current model.
CLAIM_BLOCKS = {
    "INT-C01": (("B1-C01", "B1-C02", "B1-C09", "B3-C05"), ("CAR-03", "CAR-06", "CAR-08", "CAR-10"),
                "Quantitatively faithful active brood care and retrieval"),
    "INT-C02": (("B1-C03", "B1-C04", "B1-C06", "B1-C10", "B3-C05", "B3-C16"),
                ("NUT-08", "DEV-03", "DEV-04", "PHY-01"), "A measured maternal care, reserve and provisioning loop"),
    "INT-C03": (("B1-C05", "B1-C10", "B1-C11", "B3-C11", "B3-C13", "B3-C14", "B3-C15", "B3-C16"),
                ("DEV-01", "DEV-02", "PHY-05", "POP-04", "POP-05"), "Stage-, age- and season-specific life history"),
    "INT-C04": (("B2-C01", "B2-C02", "B2-C03", "B2-C04", "B2-C05", "B2-C06", "B2-C08", "B2-C09", "B2-C10", "B2-C11", "B3-C04"),
                ("SEN-02", "SEN-03", "SEN-06", "FOR-04", "FOR-05", "PHE-03", "PHE-04", "PHE-05"),
                "A causal, species-faithful recruitment and route-learning loop"),
    "INT-C05": (("B2-C07", "B3-C08"), ("PHE-01", "PHE-02"), "Measured chemical deposition and spatial persistence"),
    "INT-C06": (("B1-C07", "B3-C01", "B3-C02", "B3-C03", "B3-C04", "B3-C05"),
                ("PHY-02", "TSK-02", "TSK-03", "TSK-04", "TSK-05"), "Observed activity, rest and state-dependent energy use"),
    "INT-C07": (("B3-C06", "B3-C07", "B3-C08", "B3-C09", "B3-C10"),
                ("NST-03", "NST-04", "NST-05", "NST-06", "NST-08"), "Species-validated nest growth and morphology"),
    "INT-C08": (("B1-C05", "B1-C10", "B3-C09", "B3-C13", "B3-C14", "B3-C17"),
                ("PHY-04", "POP-06", "NST-08"), "Natural seasonal conditions and ecological resource inputs"),
    "INT-C09": (("B1-C06", "B1-C08", "B3-C12", "B3-C17"), (), "Diet, delivered nutrition and colony growth estimates"),
    "INT-C10": (("B1-C01", "B1-C02", "B1-C06", "B1-C07", "B1-C08", "B1-C09", "B2-C05", "B2-C07", "B3-C09", "B3-C10", "B3-C13"),
                (), "Unresolved primary-source metadata and numerical comparisons"),
    "INT-C12": (("B1-C04", "B1-C07", "B1-C08", "B2-C07", "B2-C11", "B3-C18"), (),
                "Mechanism identification from aggregate population or traffic outcomes"),
}

TRANSITION_BLOCKS = {
    "INT-C01": ("CAR-03-T03", "CAR-06-T03", "CAR-08-T03", "CAR-10-T01"),
    "INT-C02": ("PHY-01-T01", "DEV-03-T02", "DEV-04-T01"),
    "INT-C03": ("DEV-01-T01", "DEV-01-T02", "DEV-01-T03", "DEV-01-T04", "POP-04-T01"),
    "INT-C04": ("SEN-02-T01", "SEN-03-T01", "FOR-04-T01", "FOR-05-T01", "FOR-05-T02", "PHE-03-T01"),
    "INT-C05": ("PHE-01-T01", "PHE-02-T01"),
    "INT-C06": ("PHY-02-T01", "TSK-02-T01", "TSK-03-T02"),
    "INT-C07": ("NST-05-T02", "NST-06-T01"),
    "INT-C08": ("PHY-04-T01", "POP-06-T01"),
}

LOCATION_FIELDS = ("SourceFile", "StartLine", "EndLine", "SourceSpanSha256", "SourceAnchorIds")
SOURCE_FIELDS = ("Title", "Authors", "Year", "Journal", "DOI", "PrimaryURL", "TargetSpecies", "ActualExperimentalSpecies",
                 "Population", "Caste", "LifeStage", "ColonySize", "SampleSize", "ExperimentalConditions", "Temperature",
                 "RelativeHumidity", "FoodCondition", "MethodsSection", "ResultsSection", "Figure", "Table", "SupplementaryMaterial",
                 "ActualMeasuredEndpoint", "OriginalMeasurement", "Unit", "StatisticalUncertainty", "FullTextAccessStatus",
                 "FullTextActuallyRead", "ReadingScope", "Limitations", "EvidenceClassification", "AtlasGrade")


def frozen_inputs():
    def git(*args):
        return subprocess.check_output(["git", "-C", str(ROOT), *args], encoding="utf-8")

    old_paths = set(git("ls-tree", "-r", "--name-only", APPROVED, "--", REVIEW.relative_to(ROOT).as_posix()).splitlines())
    require(f"{REVIEW.relative_to(ROOT).as_posix()}/{INVENTORY}" in old_paths, "Accepted evidence baseline unavailable")
    changed = set(git("diff", "--name-only", APPROVED, "--").splitlines())
    protected = old_paths | {".github/workflows/ci.yml", "tools/audit_s6_4_preflight.py", "tools/test_s6_4_preflight.py"}
    changed = sorted(path for path in changed if path in protected or path.startswith(("cpp/", "scenarios/", "experiments/", "docs/")))
    require(not changed, f"Accepted inputs changed: {', '.join(changed)}")


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def unique(values):
    return list(dict.fromkeys(values))


def fields(row, names):
    return {name: row[name] for name in names}


def read_batch(number, prefix, access_file):
    register = f"{prefix}SOURCE_FULLTEXT_REGISTER.csv"
    rules = f"{prefix}MECHANISM_EVIDENCE_REVIEW.csv"
    parameters = f"{prefix}PARAMETER_EVIDENCE_REVIEW.csv"
    conflicts = f"{prefix}EVIDENCE_CONFLICTS.md"
    sources = index(rows(REVIEW / register), "SourceId")
    accesses = defaultdict(list)
    for aid, row in index(rows(REVIEW / access_file), "AccessId").items():
        require(row["SourceId"] in sources, f"{aid}: unknown source in access log")
        accesses[row["SourceId"]].append(aid)
    require(accesses.keys() == sources.keys(), f"Batch {number}: source without an access record")
    conflict_ids = re.findall(r"^## (B\d-C\d\d)\b", (REVIEW / conflicts).read_text(encoding="utf-8"), re.MULTILINE)
    require(len(conflict_ids) == len(set(conflict_ids)), f"Batch {number}: duplicate conflict ID")
    return dict(number=number, register=register, rule_file=rules, parameter_file=parameters, access_file=access_file,
                sources=sources, accesses=accesses, rules=list(rows(REVIEW / rules)),
                parameters=index(rows(REVIEW / parameters), "ParameterKey"), conflicts=set(conflict_ids))


def paper_key(source):
    doi = source["DOI"]
    if doi == "NOT_FOUND":
        require(source["SourceId"] == "R1L" and source["PrimaryURL"].startswith("https://"), "Unknown DOI-less paper")
        return (source["Title"], source["PrimaryURL"])
    require(re.fullmatch(r"10\.\d{4,9}/[^\s;]+", doi), f"Invalid DOI {doi}")
    return doi.casefold()


def unify_sources(batches):
    source_ids = set()
    paper_ids = {}
    contexts = defaultdict(list)
    aliases = {}
    for batch in batches:
        for sid, source in batch["sources"].items():
            require(sid not in source_ids and source["Batch"] == batch["number"], f"Duplicate or misplaced source {sid}")
            source_ids.add(sid)
            require(paper_key(source) == paper_key(batch["sources"][source["PaperId"]]), f"{sid}: parent paper DOI differs")
            paper_id = paper_ids.setdefault(paper_key(source), source["PaperId"])
            species = source["ActualExperimentalSpecies"]
            focal = "Lasius niger" in species or sid == "B2-F02" and species == "Acanthomyops (Lasius) niger (historical name)"
            valid_class = source["EvidenceClassification"] == (DIRECT if focal else CROSS)
            require(valid_class and source["AtlasGrade"] in ("AB" if focal else "CDE"), f"{sid}: species evidence class or grade drift")
            require(source["FullTextActuallyRead"] == "YES_SELECTED_SECTIONS" and source["ReadingScope"], f"{sid}: missing reading scope")
            context, reason = CONTEXT_ALIASES.get(sid, (sid, "Canonical source context"))
            aliases[sid] = (context, paper_id)
            contexts[context].append((source, batch, reason))

    require(set(CONTEXT_ALIASES) <= source_ids and set(SAMPLE_UNITS) == contexts.keys(), "Unreviewed source or biological sample unit")
    require(len(source_ids) == 69 and len(paper_ids) == 58 and len(contexts) == 61, "Source coverage drift")
    registry = []
    for context, views in contexts.items():
        canonical = views[0][0]
        require(canonical["SourceId"] == context, f"{context}: missing canonical view")
        context_views = []
        for source, batch, reason in views:
            sid = source["SourceId"]
            require(paper_key(source) == paper_key(canonical), f"{sid}: merged unrelated publications")
            require(source["ActualExperimentalSpecies"] == canonical["ActualExperimentalSpecies"] or sid == "B2-F02",
                    f"{sid}: merged unlike experimental taxa")
            require((source["EvidenceClassification"], source["AtlasGrade"]) == (canonical["EvidenceClassification"], canonical["AtlasGrade"]),
                    f"{sid}: merged incompatible source grades")
            overrides = {name: source[name] for name in SOURCE_FIELDS if source[name] != canonical[name]}
            if source.get("EvidenceRelation"):
                overrides["EvidenceRelation"] = source["EvidenceRelation"]
            context_views.append(dict(Batch=batch["number"], SourceId=sid, PaperId=source["PaperId"],
                                      SourceRegister=batch["register"], AccessLog=batch["access_file"],
                                      AccessIds=batch["accesses"][sid], MergeReason=reason, SourceFieldOverrides=overrides))
        same_paper = [sid for sid, (_, paper_id) in aliases.items()
                      if paper_id == aliases[context][1] and aliases[sid][0] == sid and sid != context]
        shared_data = {"B2-F01": "B2-F03", "B2-F03": "B2-F01"}.get(context, "")
        registry.append(dict(SourceContextId=context, GlobalPaperId=aliases[context][1],
                             OriginalSourceIds=";".join(view["SourceId"] for view in context_views),
                             SamePublicationOtherContexts=";".join(same_paper), SharedDataWithContexts=shared_data,
                             **fields(canonical, SOURCE_FIELDS), BiologicalSampleUnit=SAMPLE_UNITS[context],
                             SourceViewsJson=compact(context_views)))
    return aliases, registry


def citations(review, batch, aliases, identity):
    ids = list_field(review["SourceIds"])
    require(len(ids) == len(set(ids)) and set(ids) <= batch["sources"].keys(), f"{identity}: unknown or repeated source")
    grades = [f"{sid}={batch['sources'][sid]['AtlasGrade']}" for sid in ids]
    require(list_field(review["AtlasSourceGrades"]) == grades, f"{identity}: source grade changed")
    if "DOIs" in review:
        require(list_field(review["DOIs"]) == [batch["sources"][sid]["DOI"] for sid in ids], f"{identity}: DOI mismatch")
    locators = defaultdict(list)
    delimiter = ": " if batch["number"] == "1" else " "
    for entry in review["EvidenceLocators"].split(" | ") if review["EvidenceLocators"] else ():
        sid, _, locator = entry.partition(delimiter)
        require(sid in ids and locator.strip(), f"{identity}: invalid source locator {entry}")
        locators[sid].append(locator)
    require(list(locators) == ids, f"{identity}: missing or misordered citation locators")
    result = []
    for sid in ids:
        source = batch["sources"][sid]
        context, paper = aliases[sid]
        result.append(dict(SourceContextId=context, GlobalPaperId=paper, OriginalSourceId=sid,
                           Locators=locators[sid], **fields(source, ("DOI", "AtlasGrade", "EvidenceClassification"))))
    conflicts = list_field(review["ConflictIds"])
    require(len(conflicts) == len(set(conflicts)) and set(conflicts) <= batch["conflicts"], f"{identity}: invalid conflict reference")
    return result, conflicts


def citation_summary(refs):
    return dict(SourceContextIds=";".join(unique(ref["SourceContextId"] for ref in refs)),
                DOIs=";".join(unique(ref["DOI"] for ref in refs if ref["DOI"] != "NOT_FOUND")),
                CitedAtlasGrades=";".join(unique(f"{ref['SourceContextId']}={ref['AtlasGrade']}" for ref in refs)))


def claim_status(conflicts, subject=None, calibration_contexts_differ=False):
    related = []
    blocked = []
    for issue, (previous, direct_mechanisms, claim) in CLAIM_BLOCKS.items():
        if subject in direct_mechanisms or subject in TRANSITION_BLOCKS.get(issue, ()):
            blocked.append(claim)
            related.append(issue)
        elif set(previous).intersection(conflicts):
            related.append(issue)
    if calibration_contexts_differ:
        related.append("INT-C11")
    if blocked:
        status = "YES_FOR_SPECIFIED_CLAIMS"
        rationale = "The current evidence or implementation leaves the following claims unsupported. " + ". ".join(blocked)
    elif related:
        status = "RELATED_OR_SUPPORTING_RECORD"
        rationale = "See the cited issue for scope. This record alone does not establish a scientific block"
    else:
        status = "NO_BLOCK_IDENTIFIED_IN_PHASE_1"
        rationale = "No cross-domain block assigned in this integration. The accepted evidence limits still apply"
    return dict(CrossDomainConflictIds=";".join(sorted(related)), ScientificBlockerStatus=status, ScientificBlockerBasis=rationale)


@cache
def source_text(path):
    require(path.startswith("cpp/"), f"Unexpected frozen source file {path}")
    source = (ROOT / path).read_text(encoding="utf-8")
    return sha256(source.encode("utf-8")).hexdigest(), source.splitlines()


def check_span(record, key):
    digest, lines = source_text(record["SourceFile"])
    first, last = int(record["StartLine"]), int(record["EndLine"])
    require(1 <= first <= last <= len(lines), f"{key}: invalid source span")
    span = "\n".join(lines[first - 1:last])
    require(sha256(span.encode("utf-8")).hexdigest() == record["SourceSpanSha256"], f"{key}: source span hash differs")
    require(record.get("SourceFileSha256", digest) == digest, f"{key}: source file hash differs")


def check_location(review, frozen, anchors, kind, key):
    require(all(field not in review or review[field] == frozen[field] for field in LOCATION_FIELDS), f"{key}: frozen location drift")
    ids = list_field(frozen["SourceAnchorIds"])
    if frozen.get("RecordKind") == "DECLARED_SOURCE":
        require(not ids and kind == "CORE_RULE", f"{key}: declared parameter unexpectedly has an anchor ID")
        check_span(frozen, key)
        return {"Symbol": frozen["Declaration"], "SymbolKind": "DECLARATION_OWNER"}
    require(ids and all(aid in anchors and (anchors[aid]["RecordKind"], anchors[aid]["RecordId"]) == (kind, key)
                        for aid in ids), f"{key}: unknown or misassigned anchor")
    primary = anchors[ids[0]]
    require(primary["Role"] == "PRIMARY" and all(primary[field] == frozen[field] for field in LOCATION_FIELDS[:-1]),
            f"{key}: primary source span mismatch")
    require(all(anchors[aid]["Role"] == "SUPPORTING" for aid in ids[1:]), f"{key}: misclassified supporting anchor")
    for aid in ids:
        check_span(anchors[aid], aid)
    return primary


def merge_rules(batches, mechanisms, transitions, parameters, anchors, aliases):
    by_kind = {"MECHANISM": {}, "TRANSITION": {}}
    by_mechanism = defaultdict(list)
    for key, record in parameters.items():
        for mid in list_field(record["MechanismIds"]):
            by_mechanism[mid].append(key)
    for batch in batches:
        for review in batch["rules"]:
            kind, mid, tid = (review[field] for field in ("RecordKind", "MechanismId", "TransitionId"))
            require(kind in by_kind and bool(tid) == (kind == "TRANSITION"), f"{mid}/{tid}: invalid record kind")
            key = tid or mid
            target = by_kind[kind]
            require(key not in target, f"{key}: rule appears in more than one accepted batch")
            frozen = transitions[tid] if tid else mechanisms[mid]
            require(frozen["MechanismId"] == mid and review["Domain"] == mechanisms[mid]["Domain"], f"{key}: wrong mechanism owner or domain")
            primary = check_location(review, frozen, anchors, kind, key)
            require(primary["Symbol"] == frozen["Function"] and review.get("Function", frozen["Function"]) == frozen["Function"],
                    f"{key}: wrong code symbol")
            refs, conflicts = citations(review, batch, aliases, key)
            category = review["EvidenceClassification"]
            require(category in CLASSES and (category not in {DIRECT, CROSS} or (
                any(ref["EvidenceClassification"] == category for ref in refs) and review["MeasuredEndpointAndUnit"].strip()
            )), f"{key}: comparison lacks measured evidence of its declared type")
            if tid:
                specifics = fields(frozen, ("TransitionId", "StateSystem", "FromState", "ToState", "Trigger", "GuardOrAlternate",
                                            "ActionAndNextWake", "ParameterKeys"))
                exact_keys = [name for name in list_field(frozen["ParameterKeys"]) if name in parameters]
                specifics["ExactTransitionParameterKeys"] = ";".join(exact_keys)
                specifics["UnexpandedParameterReferences"] = ";".join(name for name in list_field(frozen["ParameterKeys"]) if name not in parameters)
            else:
                specifics = fields(frozen, ("Mechanism", "CallerOrEntry", "ImplementationStatus", "AvailableInputsAndLocality",
                                            "SourceRule", "OutcomeOrTermination", "SourceBoundaryOrGap", "ParameterFamilies"))
            target[key] = dict(MechanismId=mid, **specifics, Domain=review["Domain"],
                               **fields(frozen, (*LOCATION_FIELDS, "Function", "RuntimeScope", "ImplementationBasis")),
                               AcceptedBatch=batch["number"], AcceptedReviewFile=batch["rule_file"],
                               CurrentRuleOrGuard=review["CurrentRuleOrGuard"], InformationChannel=review.get("InformationChannel", ""),
                               CoreRuleClassification=review.get("CoreRuleClassification", frozen["ImplementationBasis"]),
                               MechanismEvidenceClassification=category, OwnerAssociatedParameterKeys=";".join(by_mechanism[mid]),
                               OwnerParameterEvidenceClassification=FIXTURE if by_mechanism[mid] else "NOT_APPLICABLE",
                               OwnerParameterAtlasGrade="F" if by_mechanism[mid] else "NOT_APPLICABLE",
                               **citation_summary(refs), CitationsJson=compact(refs), MeasuredEndpointAndUnit=review["MeasuredEndpointAndUnit"],
                               SupportedBiologicalClaim=review.get("SupportedBiologicalClaim", ""), RuleAssessment=review["RuleAssessment"],
                               ImplementationDifferenceAndUncertainty=review["UnsupportedImplementationOrGap"],
                               CanCalibrateCurrentRule="NO_CALIBRATION_ESTABLISHED" if refs else "NOT_APPLICABLE",
                               AcceptedConflictIds=";".join(conflicts),
                               **claim_status(conflicts, key if category != FIXTURE else None))
    require(by_kind["MECHANISM"].keys() == mechanisms.keys() and by_kind["TRANSITION"].keys() == transitions.keys(),
            "Integrated rule IDs differ from frozen inventory")
    require(Counter(row["AcceptedBatch"] for row in by_kind["MECHANISM"].values()) == {"1": 39, "2": 19, "3": 17}
            and Counter(row["AcceptedBatch"] for row in by_kind["TRANSITION"].values()) == {"1": 53, "2": 19, "3": 27},
            "Accepted rule coverage by batch changed")
    return ([by_kind["MECHANISM"][key] for key in mechanisms], [by_kind["TRANSITION"][key] for key in transitions])


def compare_uses(left, right):
    left_contexts = {ref["SourceContextId"] for ref in left["Citations"]}
    right_contexts = {ref["SourceContextId"] for ref in right["Citations"]}
    same_contexts = sorted(left_contexts & right_contexts)
    same_papers = {ref["GlobalPaperId"] for ref in left["Citations"]} & {ref["GlobalPaperId"] for ref in right["Citations"]}
    return dict(Batches=[left["Batch"], right["Batch"]], SharedSourceContexts=same_contexts, SharedPapers=sorted(same_papers),
                DifferentCalibrationApplicability=left["CanCalibrateCurrentValue"] != right["CanCalibrateCurrentValue"],
                InferenceTransfer="NOT_ESTABLISHED")


def fixture_candidates(parameters):
    counts = Counter()
    for row in rows(REVIEW / FIXTURE_INDEX):
        candidates = set(list_field(row["ParameterCandidates"]))
        require(candidates <= parameters.keys(), "Unknown parameter in fixture configuration index")
        counts.update(candidates)
    return counts


def merge_parameters(batches, mechanisms, parameters, anchors, aliases):
    result = []
    coverage = Counter()
    fixture_counts = fixture_candidates(parameters)
    batch_mechanisms = {batch["number"]: {row["MechanismId"] for row in batch["rules"] if row["RecordKind"] == "MECHANISM"}
                        for batch in batches}
    for key, frozen in parameters.items():
        mids = list_field(frozen["MechanismIds"])
        require(set(mids) <= mechanisms.keys(), f"{key}: unknown mechanism association")
        primary = check_location({}, frozen, anchors, "CORE_RULE", key)
        uses = []
        all_refs = []
        all_conflicts = []
        for batch in batches:
            number = batch["number"]
            if key not in batch["parameters"]:
                continue
            review = batch["parameters"][key]
            check_location(review, frozen, anchors, "CORE_RULE", key)
            frozen_fields = ("MechanismIds", "SourceExpression", "CurrentSourceValue", "Unit", "Scope", "Role", "ValueRoleClass",
                             "ParameterEvidenceClass")
            require(fields(review, frozen_fields) == fields(frozen, frozen_fields), f"{key}: inconsistent value, units or scope")
            require(review["ParameterEvidenceClass"] == FIXTURE and review["AtlasParameterGrade"] == frozen["AtlasGrade"] == "F",
                    f"{key}: current parameter evidence upgraded without calibration")
            require(review["CanCalibrateCurrentValue"] in {"NO", "NOT_APPLICABLE"}, f"{key}: unsupported calibration claim")
            expected = batch_mechanisms[number] & set(mids)
            linked = list_field(review[f"Batch{number}MechanismIds"])
            require(linked and len(linked) == len(expected) and set(linked) == expected, f"{key}: wrong context in Batch {number}")
            refs, conflicts = citations(review, batch, aliases, key)
            all_refs.extend(refs)
            all_conflicts.extend(conflicts)
            metadata = ("ActualMeasuredEndpoint", "OriginalMeasurement", "OriginalUnit", "StatisticalUncertainty", "EndpointMatch",
                        "UnitConversionAndSourceDifference", "ConversionReferenceURL", "CanCalibrateCurrentValue", "CalibrationAssessment",
                        "Batch3UseType", "Batch3Use", "CrossDomainCoupling", "EvidenceApplicability", "PriorReviewBatches", "PriorMechanismIds",
                        "PriorUses", "PriorSourceRefs", "OverlappingPrimaryDOIs")
            uses.append(dict(Batch=number, AcceptedReviewFile=batch["parameter_file"],
                             MechanismUses=[fields(mechanisms[mid], ("MechanismId", "Domain", "Mechanism", "Function")) for mid in linked],
                             Citations=refs, AcceptedConflictIds=conflicts, **{field: review[field] for field in metadata if field in review}))
        reviewed_mids = [item["MechanismId"] for use in uses for item in use["MechanismUses"]]
        require(uses and len(reviewed_mids) == len(mids) and set(reviewed_mids) == set(mids), f"{key}: incomplete cross-domain uses")
        coverage[tuple(use["Batch"] for use in uses)] += 1
        statuses = {use["CanCalibrateCurrentValue"] for use in uses}
        mixed = len(statuses) > 1
        applicability = "CONTEXT_DEPENDENT" if mixed else "EVIDENCE_INSUFFICIENT" if "NO" in statuses else "NON_CALIBRATION_CONTEXT"
        result.append(dict(**fields(frozen, ("ParameterKey", "RecordKind", "ValueRoleClass", "MechanismIds", *LOCATION_FIELDS,
                                              "Declaration", "SourceExpression", "CurrentSourceValue", "Unit", "Role", "Scope", "Caste",
                                              "LifeStage", "Species", "ParameterEvidenceClass", "AtlasGrade")),
                           SourceSymbol=primary["Symbol"], SourceSymbolKind=primary["SymbolKind"],
                           Domains=";".join(unique(mechanisms[mid]["Domain"] for mid in mids)),
                           FixtureCandidateIndex=FIXTURE_INDEX if fixture_counts[key] else "",
                           FixtureCandidateRows=str(fixture_counts[key]),
                           MechanismEvidenceClassesJson=compact({mid: mechanisms[mid]["MechanismEvidenceClassification"] for mid in mids}),
                           ReviewBatches=";".join(use["Batch"] for use in uses), **citation_summary(all_refs),
                           CanCalibrateCurrentValue="NO" if "NO" in statuses else "NOT_APPLICABLE", CalibrationApplicability=applicability,
                           UseAssessmentsJson=compact(uses), CrossReviewComparisonsJson=compact([compare_uses(*pair) for pair in combinations(uses, 2)]),
                           AcceptedConflictIds=";".join(unique(all_conflicts)), **claim_status(all_conflicts, calibration_contexts_differ=mixed)))
    require(coverage == {("1",): 68, ("2",): 35, ("3",): 47, ("1", "2"): 7, ("1", "3"): 67, ("2", "3"): 4,
                         ("1", "2", "3"): 21}, "Cross-batch parameter overlap changed")
    require(sum(row["CalibrationApplicability"] == "CONTEXT_DEPENDENT" for row in result) == 25, "Calibration-applicability comparison drift")
    return result


def check_table(path, records, write):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=tuple(records[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    if write:
        path.write_text(stream.getvalue(), encoding="utf-8", newline="\n")
    else:
        actual = list(rows(path))
        require(len(actual) == len(records), f"{path.name}: expected {len(records)} rows, got {len(actual)}")
        for line, (got, expected) in enumerate(zip(actual, records), 2):
            different = [field for field, value in expected.items() if got.get(field) != value]
            require(tuple(got) == tuple(expected) and not different,
                    f"{path.name}:{line} ({next(iter(expected.values()))}): unexpected fields {', '.join(different)}")


def run(write):
    frozen_inputs()
    batches = [read_batch(*batch) for batch in BATCHES]
    require([(len(batch["sources"]), sum(map(len, batch["accesses"].values())), len(batch["parameters"]), len(batch["conflicts"]))
             for batch in batches] == [(15, 42, 163, 11), (26, 46, 67, 11), (28, 45, 139, 18)], "Accepted batch counts changed")
    anchors = index(rows(REVIEW / "SOURCE_ANCHORS.csv"), "AnchorId")
    mechanisms = index(rows(REVIEW / INVENTORY), "MechanismId")
    transitions = index(rows(REVIEW / TRANSITIONS), "TransitionId")
    parameters = index(rows(REVIEW / PARAMETERS), "ParameterKey")
    require((len(mechanisms), len(transitions), len(parameters), len(anchors)) == (75, 99, 249, 541), "Frozen inventory coverage changed")
    require(set().union(*(set(batch["parameters"]) for batch in batches)) == parameters.keys(), "Parameter IDs differ from frozen matrix")
    accepted_conflicts = set().union(*(batch["conflicts"] for batch in batches))
    for previous, mids, _ in CLAIM_BLOCKS.values():
        require(set(previous) <= accepted_conflicts and set(mids) <= mechanisms.keys(), "Unknown conflict or mechanism in an integration finding")
    for issue, tids in TRANSITION_BLOCKS.items():
        require(issue in CLAIM_BLOCKS and set(tids) <= transitions.keys()
                and all(transitions[tid]["MechanismId"] in CLAIM_BLOCKS[issue][1] for tid in tids),
                f"{issue}: unknown or unrelated transition in integration finding")
    conflict_text = (REVIEW / "CROSS_DOMAIN_CONFLICTS.md").read_text(encoding="utf-8")
    findings = re.findall(r"^## (INT-C\d\d)\b", conflict_text, re.MULTILINE)
    require(len(findings) == 12 and set(findings) == {*CLAIM_BLOCKS, "INT-C11"}, "Cross-domain findings changed or are missing")

    aliases, source_rows = unify_sources(batches)
    mechanism_rows, transition_rows = merge_rules(batches, mechanisms, transitions, parameters, anchors, aliases)
    integrated_mechanisms = index(mechanism_rows, "MechanismId")
    parameter_rows = merge_parameters(batches, integrated_mechanisms, parameters, anchors, aliases)
    tables = {"INTEGRATED_MECHANISM_EVIDENCE.csv": mechanism_rows, "INTEGRATED_TRANSITION_EVIDENCE.csv": transition_rows,
              "INTEGRATED_PARAMETER_EVIDENCE.csv": parameter_rows, "UNIFIED_SOURCE_CONTEXT_REGISTER.csv": source_rows}
    all_rows = mechanism_rows + transition_rows + parameter_rows
    require({cid for row in all_rows for cid in list_field(row["AcceptedConflictIds"])} == accepted_conflicts,
            "An accepted conflict lost all evidence links")
    require({aid for row in all_rows for aid in list_field(row["SourceAnchorIds"])} == anchors.keys(), "An accepted source anchor lost its link")
    for filename, records in tables.items():
        check_table(REVIEW / filename, records, write)
    print("Verified 75 mechanisms, 99 transitions, 249 parameters with 369 reviews, and 541 source anchors.")
    print("Verified 58 publications, 61 source contexts, 69 accepted source views, and 133 access links.")
    print("Preserved 40 accepted conflicts and 12 integration findings. No current parameter was calibrated.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Regenerate the four derived CSVs")
    try:
        run(parser.parse_args().write)
    except (OSError, KeyError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Scientific integration check failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
