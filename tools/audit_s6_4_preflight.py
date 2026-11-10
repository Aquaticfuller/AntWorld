"""Generate and verify the source-only AntWorld S6.4 Preflight inventory."""

import argparse
import ast
import bisect
from collections import Counter, defaultdict
import csv
from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "research/s6_4_preflight"
BASELINE = "b35b988ecf1b92f7bac3c00af393b88ab8330d67"
CORE_TREE = "277cc8e78cc1acd1cf4a74bf39d08dfdb6a99c69"
ATLAS_COMMIT = "2e1a5fa129821176954f26a88f56791635bc8cda"
HEADER = "cpp/include/antworld/core/"
PENDING = "PENDING_FULL_TEXT_REVIEW"
STEP_1 = "e16ccabaf7ad458dd77f35f3f4f1f247e19bd2f5"
NUMERIC_CLASSES = {
    "BIOLOGICAL_PARAMETER", "ENGINEERING_CONSTANT", "FIXTURE_OR_TEST_VALUE",
    "STRUCTURAL_OR_ALGORITHMIC_CONSTANT", "UNIT_CONVERSION", "UNRESOLVED",
}

OWNERS = {
    "PositionM": "SEN-01;FOR-08;CAR-07;NST-02",
    "FoodMass": "NUT-01;NUT-02;NUT-05;NUT-06;PHY-03;POP-06",
    "AntSeed": "POP-01;FOR-06;NST-03",
    "WorldConfig": "SEN-01;SEN-04;SEN-05;FOR-08;CAR-07;NST-02",
    "RuntimeLimits": "SYS-01;SYS-02;SYS-03;PHE-02;NST-01;NST-02;POP-01",
    "SurfaceConfig": "SEN-01;FOR-08;FOR-09",
    "BehaviorConfig": "SEN-02;FOR-02;FOR-03;FOR-04;FOR-05;FOR-08;FOR-10;PHE-01;PHE-02;PHE-03",
    "PhysiologyConfig": "PHY-01;PHY-02;PHY-03;PHY-04;DEV-01;DEV-03;DEV-04;NUT-03;NUT-04;NUT-06;TSK-04;POP-04",
    "PhysiologySeed": "PHY-01;PHY-02;PHY-03;PHY-04;DEV-03;NUT-02",
    "SocialConfig": "SEN-04;NUT-03;NUT-04;NUT-06;TSK-01;TSK-02;TSK-03",
    "LongTermConfig": "TSK-03;TSK-04;NUT-07;NST-06",
    "ReproductionConfig": "DEV-03;DEV-04;POP-03",
    "ResourceCycleConfig": "POP-06",
    "CareMotionProfile": "CAR-02;CAR-05;CAR-06;CAR-07;CAR-08",
    "SpeciesCareProfile": "SEN-05;CAR-01;CAR-03;CAR-04;CAR-05;CAR-07;CAR-08",
    "IndividualCareProfile": "CAR-01;CAR-02;CAR-03",
    "EnvironmentCareProfile": "CAR-01;CAR-10;NST-08",
    "GeometryConfig": "NST-01;NST-02;NST-03;NST-04;NST-05;NST-06;NST-07",
    "PointQ": "NST-01;NST-02;NST-03",
    "BoxQ": "NST-01;NST-02;NST-03;NST-04",
    "ActionProposal": "SYS-02;FOR-06;FOR-07;FOR-08",
    "NutritionProposal": "NUT-05;NUT-06;NUT-07",
    "SoilProposal": "NST-03;NST-04",
    "PlaceFoodCommand": "NUT-01;SYS-03",
    "Controls": "PHY-01;DEV-03;NUT-06;TSK-03",
    "IntegratedOptions": "NUT-01;NUT-04;TSK-02;TSK-03",
}

API_TYPES = {
    "WorldRuntime": ("", "", "WorldConfig", "RuntimeLimits"),
    "seed_colony": ("PositionM",),
    "seed_ant": ("", "AntSeed"),
    "seed_food": ("PositionM", "FoodMass"),
    "configure_surface": ("SurfaceConfig", "", "BehaviorConfig"),
    "configure_social": ("SocialConfig",),
    "configure_geometry": ("GeometryConfig", "", ""),
    "configure_long_term": ("LongTermConfig",),
    "enable_physiology": ("", "PhysiologySeed", "PhysiologyConfig"),
    "configure_resource_cycle": ("", "ResourceCycleConfig"),
    "enable_reproduction": ("", "ReproductionConfig"),
    "configure_biology": ("SpeciesCareProfile", "EnvironmentCareProfile"),
    "enable_brood_care": ("", "IndividualCareProfile"),
    "place_food": ("PlaceFoodCommand",),
    "submit": ("ActionProposal",),
    "submit_nutrition": ("NutritionProposal",),
    "submit_soil": ("SoilProposal",),
    "schedule_lifecycle": (),
    "start_foraging": (),
    "set_autonomy": (),
    "set_behavior": (),
    "pause_brood_care": (),
}

STATE_GROUPS = {
    "LifeStage": ("Persisted life stage", "DEV-01;POP-01;POP-02;POP-04"),
    "Caste": ("Persisted caste label", "DEV-02;POP-01;CAR-01"),
    "Species": ("Fixture species label", "POP-01;PHY-05"),
    "Direction": ("Surface direction or unset marker", "SEN-01;FOR-04"),
    "BehaviorMode": ("Foraging program state or decision label", "FOR-02;FOR-05;FOR-07;PHE-03"),
    "DecisionReason": ("Foraging decision annotation", "FOR-02;FOR-05;PHE-03"),
    "IndividualBehavior": ("Ordinary task program", "TSK-02;TSK-03;TSK-04;PHY-02"),
    "DeathCause": ("Physiology terminal cause or unset marker", "POP-02;POP-04"),
    "NutritionAction": ("Requested nutrition action", "NUT-05;NUT-06;NUT-07"),
    "CareContext": ("Individual enrollment metadata", "CAR-01;CAR-02"),
    "CareAct": ("Care motor state or observation label", "CAR-03;CAR-04;CAR-05;CAR-06;CAR-08;CAR-11"),
    "ObservationPhase": ("Committed observation label", "SYS-04;CAR-11"),
    "ActionKind": ("Ordinary requested action", "SYS-02;FOR-06;FOR-07;FOR-08;TSK-04"),
    "SoilAction": ("Requested soil action", "NST-03;NST-04;NST-05"),
    "ParcelState": ("Persisted soil custody", "NST-03;NST-04"),
    "Material": ("Material authority result", "NST-01;NST-02"),
    "Kind": ("ScheduledEvent::Kind, queued dispatch", "SYS-01;SYS-02"),
    "Phase": ("Event-order phase", "SYS-01;SYS-02"),
    "Outcome": ("Resolution outcome, not a behavior state", "SYS-02;CAR-11"),
    "FactKind": ("Canonical fact label, not a behavior state", "SYS-03;SYS-04"),
}
OBSERVER_ONLY_CARE = {
    "CollectFood", "DeliverFood", "IngestFood", "TransferNutrition", "Excavate", "HandleSoil"
}
LITERAL_FILES = {
    "behavior.cpp", "behavior_rng.hpp", "care.cpp", "care_internal.hpp",
    "contact_index.hpp", "ecology.cpp", "excavation.cpp", "foraging.cpp",
    "geometry.cpp", "geometry_internal.hpp", "geometry_kernel.cpp", "long_term.cpp",
    "long_term_internal.hpp", "motion_numeric.hpp", "physiology.cpp",
    "physiology_internal.hpp", "social.cpp", "social_internal.hpp",
    "spatial_navigation.cpp", "spatial_navigation.hpp", "surface_internal.hpp",
    "world_runtime.cpp",
}
CPP_MASK = re.compile(
    r'//[^\n]*|/\*.*?\*/|R"(?P<delimiter>[^()\s\\]{0,16})\(.*?\)(?P=delimiter)"'
    r'|"(?:\\.|[^"\\])*"|(?<![\w.])\'(?:\\.|[^\'\\])*\'', re.S
)
NUMBER = re.compile(
    r"(?<![\w.])(?:0[xX][0-9a-fA-F']+(?:\.[0-9a-fA-F']*)?(?:[pP][+-]?[0-9]+)?"
    r"|0[bB][01']+|(?:[0-9][0-9']*(?:\.[0-9']*)?|\.[0-9][0-9']*)(?:[eE][+-]?[0-9]+)?)"
    r"(?:[uUlLfF]{1,3})?(?![\w.])"
)
PAIRS = {"(": ")", "[": "]", "{": "}"}
PAPER_FIELDS = dict(OriginalStudy="", DOI="", FullTextStatus="NOT_REVIEWED_IN_STEP_1",
                    PageOrSection="", FigureOrTable="", ExperimentalConditions="",
                    SampleSizeAndUnit="", OriginalMeasurement="", StatisticalUncertainty="",
                    ModelMeasurementDifference="", ValueSupport=PENDING, RecalibrationAssessment=PENDING)


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], encoding="utf-8").strip()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def mask(text):
    return CPP_MASK.sub(lambda match: re.sub(r"[^\n]", " ", match[0]), text)


def compact(text):
    return " ".join(text.strip().split())


class Source:
    def __init__(self, path, text=None):
        self.path = path
        self.raw = (ROOT / path).read_text(encoding="utf-8") if text is None else text
        self.code = mask(self.raw)
        self.lines = self.raw.splitlines()
        self.breaks = [m.start() for m in re.finditer("\n", self.raw)]
        self.sha256 = digest(self.raw)

    def line(self, offset):
        return bisect.bisect_left(self.breaks, offset) + 1

    def location(self, start, stop):
        return dict(SourceFile=self.path, StartLine=self.line(start), EndLine=self.line(max(start, stop - 1)))


def group_end(text, opening):
    stack = [PAIRS[text[opening]]]
    for i in range(opening + 1, len(text)):
        ch = text[i]
        if ch in PAIRS:
            stack.append(PAIRS[ch])
        elif ch == stack[-1]:
            stack.pop()
            if not stack:
                return i + 1
    raise ValueError(f"Unclosed C++ group at character {opening}")


def parts(text, start, stop, separators=","):
    """Split at top-level separators while preserving absolute source offsets."""
    offset = start
    while offset < stop:
        ch = text[offset]
        if ch in PAIRS:
            offset = group_end(text, offset)
            continue
        if ch in separators:
            yield start, offset
            start = offset + 1
        offset += 1
    if start < stop:
        yield start, stop


def trim(text, start, stop):
    while start < stop and text[start].isspace():
        start += 1
    while stop > start and text[stop - 1].isspace():
        stop -= 1
    return start, stop


@dataclass(frozen=True)
class Region:
    kind: str
    symbol: str
    first: int
    last: int


def symbol_regions(source):
    """Index explicit lexical definitions in the frozen sources.

    This checks declaration containment. It does not resolve overloads, virtual
    calls, preprocessing branches or call graphs.
    """
    code = source.code
    types = []
    type_pattern = r"^[ \t]*(?:template[^\n]*>\s+)?(?P<kind>enum\s+class|struct|class)\s+(?P<name>[\w:]+)[^;{}\n]*\{"
    for match in re.finditer(type_pattern, code, re.M):
        types.append(Region("ENUM" if match["kind"].startswith("enum") else "TYPE",
                            match["name"], source.line(match.start()), source.line(group_end(code, match.end() - 1) - 1)))
    functions = []
    fn_pattern = (
        r"^[ \t]*(?:template[^\n]*>\s+)?(?:\[\[[^\n]*?\]\]\s*)?"
        r"(?:(?:[\w:<>,*&]+[ \t]+)+)?(?P<name>(?:\w+::)*~?\w+)\s*\("
    )
    suffix = r"\s*(?:(?:const|noexcept|override|final)\s*)*(?:->\s*[\w:<>,*& \t]+\s*)?\{"
    for match in re.finditer(fn_pattern, code, re.M):
        name = match["name"]
        if name in {"if", "for", "while", "switch", "catch", "requires", "return", "static_assert"}:
            continue
        first = source.line(match.start())
        if "::" not in name and not code[match.start():match.start("name")].strip():
            continue
        end = group_end(code, match.end() - 1)
        body = re.match(suffix, code[end:])
        if body is None:
            continue
        last = source.line(group_end(code, end + body.end() - 1) - 1)
        parents = [region for region in types if region.kind == "TYPE" and region.first < first and last <= region.last]
        if "::" not in name and parents:
            name = max(parents, key=lambda region: region.first).symbol + "::" + name
        functions.append(Region("FUNCTION", name, first, last))
    constants = []
    variable = r"^[ \t]*(?:(?:inline|static)\s+)*constexpr\s+[\w:<>,*& \t]+?\s+(\w+)\s*([={])"
    for match in re.finditer(variable, code, re.M):
        first = source.line(match.start())
        statement_end = next((last for _, last in parts(code, match.end() - 1, len(code), ";")), match.end())
        last = source.line(statement_end)
        constants.append(Region("CONSTANT", match[1], first, last))
    return types + functions + constants


@dataclass(frozen=True)
class Field:
    owner: str
    name: str
    type: str
    initializer: str
    source: str
    first: int
    last: int

    @property
    def key(self):
        return f"{self.owner}.{self.name}"


def fields(sources):
    definitions = {}
    for src in sources:
        for match in re.finditer(r"\bstruct\s+(\w+)\s*\{", src.code):
            owner = match[1]
            if owner not in OWNERS:
                continue
            opening = match.end() - 1
            declarations = []
            for first, last in parts(src.code, opening + 1, group_end(src.code, opening) - 1, ";"):
                declaration = src.code[first:last]
                if not declaration.strip() or "operator" in declaration or "[[" in declaration:
                    continue
                dtype = ""
                for i, (start, stop) in enumerate(parts(src.code, first, last)):
                    fragment = src.code[start:stop]
                    if i == 0:
                        prefix = re.match(r"\s*((?:\w+::)*\w+(?:<[\w:]+>)?)\s+", fragment)
                        require(prefix is not None, f"Unparsed declaration {owner}: {fragment}")
                        dtype = prefix[1]
                        start += prefix.end()
                    member = re.fullmatch(r"\s*(\w+)\s*([\s\S]*)", src.code[start:stop])
                    require(member is not None, f"Unparsed member {owner}: {src.raw[start:stop]}")
                    name = member[1]
                    init_start, init_stop = trim(src.code, start + member.start(2), stop)
                    pos = start + member.start(1)
                    declarations.append(Field(owner, name, dtype, src.raw[init_start:init_stop],
                                              src.path, src.line(pos), src.line(max(pos, init_stop - 1))))
            require(owner not in definitions, f"Duplicate schema {owner}")
            definitions[owner] = declarations
    require(set(definitions) == set(OWNERS), f"Missing source schemas: {set(OWNERS) - set(definitions)}")
    return definitions


EXTRA_METADATA = {
    "WorldConfig": """continuous_spatial_motion|boolean|Select subgrid swept motion for newly configured worlds""",
    "RuntimeLimits": """entities|entities|Runtime identity budget
pending_events|scheduled events|Queue capacity
committed_events|facts or journal entries|Runtime history and associated edit/request budget
events_per_timestamp|events/timestamp|Same-time scheduler execution budget
checkpoint_bytes|bytes|Host checkpoint budget
surface_cells|cells|Surface definition size limit
trail_cells|cells|Sparse field slot budget
geometry_edits|edits|Authoritative geometry edit budget
geometry_index_entries|entries|Geometry edit index budget
geometry_partition_cells|partitions|Exact local geometry partition budget
sdf_bricks|bricks|Derived signed distance cache budget
navigation_nodes|nodes|Read-only route query search budget
neighborhood_buckets|buckets|Geometric neighborhood query budget""",
    "CareMotionProfile": """worker_unloaded_m_per_s|m/s|Preferred unloaded worker travel before world cap
queen_unloaded_m_per_s|m/s|Preferred unloaded queen travel before world cap
worker_loaded_m_per_s|m/s|Preferred brood-loaded worker travel before world cap
queen_loaded_m_per_s|m/s|Preferred brood-loaded queen travel before world cap
pickup_duration|ms|Explicit pickup handling time
placement_duration|ms|Explicit placement handling time
manipulation_duration|ms|Stationary handling duration or minimum arrangement duration
search_pause|ms|Dedicated pause after successful placement
search_steps|moves|Dedicated empty-view search cadence counter
integrate_autonomy|boolean|Enable finite care leases in the normal autonomy program""",
    "SpeciesCareProfile": """decision_interval|ms|Dedicated inactive or idle decision cadence
bout_duration|ms|Legacy common duration without timed motion
worker_contact_duration|ms|Dedicated successful worker contact duration
social_memory_horizon|ms|Time for successful contact inhibition to reach zero
care_probability|dimensionless probability|Per-decision new brood choice before queen inhibition
worker_contact_probability|dimensionless probability|Per-decision queen worker-contact choice
maximum_inhibition|dimensionless fraction|Maximum depression of new queen brood-choice probability
perception_radius_m|m|Indexed care observation radius before material filters
step_m|m|Nominal care travel segment limit
arrangement_m|m|Maximum local brood arrangement shift
local_retrieval|boolean|Enable displaced target persistence and pickup-site revisit
motion|optional profile|Select timed movement and separate manipulation clocks""",
    "IndividualCareProfile": """context|category|Declared enrollment caste context
age_at_enrollment|ms|Age metadata, no rate multiplier""",
    "EnvironmentCareProfile": """temperature_c|deg C|Assay temperature metadata
relative_humidity|dimensionless fraction|Assay relative humidity metadata
neutral_displacement_assay|boolean|Allow constrained foreign-brood retrieval assay
arena_radius_m|m|Care-only test disc radius or zero for no disc""",
    "PointQ": """x|q|Quantized X coordinate
y|q|Quantized Y coordinate
z|q|Quantized Z coordinate""",
    "ActionProposal": """actor|AntRef|Actor identity
execute_at|ms|Scheduled simulation time
kind|category|Requested ordinary action
food|FoodRef|Target food identity
destination|m vector|Requested physical endpoint
requested_ug|ug/action|Requested mass before capacity and supply checks""",
    "NutritionProposal": """actor|AntRef|Donor or self intake actor
execute_at|ms|Scheduled simulation time
kind|category|Requested nutrition action
recipient|AntRef|Requested recipient identity
requested_ug|ug/action|Requested mass before room and supply checks""",
    "SoilProposal": """actor|AntRef|Soil worker identity
execute_at|ms|Scheduled simulation time
kind|category|Requested soil action
box|q^3 box|Requested local excavation or fill bounds
parcel|SoilParcelRef|Soil parcel to pick up, drop or spend
observed_geometry_revision|revision|Most recent geometry revision seen by caller""",
    "PlaceFoodCommand": """world|WorldId|Target world
id|CommandId|Idempotency key for explicit input
position|m vector|Physical position of the introduced source
mass|ug component vector|Explicit introduced ingredient mass""",
}
FIELD_SCOPE = {
    "BehaviorConfig": ("Worker", "Adult"),
    "CareMotionProfile": ("Queen;Worker", "Adult"),
    "SpeciesCareProfile": ("Queen;Worker", "Adult caregivers and brood targets"),
    "IndividualCareProfile": ("Queen;Worker", "Adult"),
    "SocialConfig": ("Worker;Queen", "Adult actors and applicable contact targets"),
    "ReproductionConfig": ("Queen;Worker offspring", "Adult mother and Egg offspring"),
    "Controls": ("Queen;Worker", "Adult mother and developing offspring"),
    "IntegratedOptions": ("Worker;Queen", "Context-dependent"),
    "RuntimeLimits": ("Not applicable", "Not applicable"),
    "ResourceCycleConfig": ("Not applicable", "Not applicable"),
    "PlaceFoodCommand": ("Not applicable", "Not applicable"),
}
SPECIAL_SCOPE = {
    "PhysiologyConfig.egg_duration": ("Configured individual", "Egg"),
    "PhysiologyConfig.larva_duration": ("Configured individual", "Larva"),
    "PhysiologyConfig.pupa_duration": ("Configured individual", "Pupa"),
    "PhysiologyConfig.larval_protein_requirement_ug": ("Configured individual", "Larva"),
    "PhysiologyConfig.protein_absorption_ug_per_s": ("Configured individual", "Larva"),
    "PhysiologyConfig.active_nj_per_ms": ("Worker", "Adult in active ordinary program"),
    "PhysiologyConfig.adult_protein_target_ug": ("Configured adult, normally Queen", "Adult"),
    "CareMotionProfile.worker_unloaded_m_per_s": ("Worker", "Adult"),
    "CareMotionProfile.worker_loaded_m_per_s": ("Worker", "Adult"),
    "CareMotionProfile.queen_unloaded_m_per_s": ("Queen", "Adult"),
    "CareMotionProfile.queen_loaded_m_per_s": ("Queen", "Adult"),
    "SpeciesCareProfile.worker_contact_probability": ("Queen", "Adult"),
    "SpeciesCareProfile.maximum_inhibition": ("Queen", "Adult"),
    "SpeciesCareProfile.social_memory_horizon": ("Queen", "Adult"),
}
INPUT_SCHEMAS = {
    "PositionM", "FoodMass", "AntSeed", "PhysiologySeed", "PointQ", "BoxQ",
    "ActionProposal", "NutritionProposal", "SoilProposal", "PlaceFoodCommand",
    "Controls", "IntegratedOptions",
}
UNIT_CONVERSIONS = {"milliseconds_per_second", "nanojoules_per_joule"}


def metadata():
    # Reuse the historical unit/meaning vocabulary without importing its old
    # source checkout logic or carrying over any literature grades.
    prior = ast.parse((ROOT / "tools/provenance_s6_3_2.py").read_text(encoding="utf-8"))
    legacy = next(node.value for node in prior.body if isinstance(node, ast.Assign)
                  and any(isinstance(target, ast.Name) and target.id == "FIELDS" for target in node.targets))
    result = {}
    for groups in (ast.literal_eval(legacy), EXTRA_METADATA):
        for owner, table in groups.items():
            for row in table.splitlines():
                field, unit, meaning = row.split("|", 2)
                result[f"{owner}.{field}"] = (unit, meaning)
    return result


def source_value(field, expression):
    if not expression:
        if field.type.startswith("std::optional"):
            return "DISENGAGED_OPTIONAL"
        if field.type in {"PositionM", "FoodMass", "SimTime", "PointQ", "BoxQ", "AntRef",
                          "FoodRef", "SoilParcelRef", "WorldId", "CommandId"}:
            return "MEMBER_DEFAULTS_OF_" + field.type
        return "NO_EXPLICIT_INITIALIZER"
    expression = expression.removeprefix("=").strip()
    if expression == "{}":
        if field.type == "bool":
            return "false"
        if field.type == "double" or field.type.startswith(("std::uint", "std::int")):
            return "0"
        if field.type == "SimTime":
            return "{0}"
        return "VALUE_INITIALIZED"
    return compact(expression)


def read_csv(name):
    with (REPORT / name).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def csv_text(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def value_role(field):
    if field.owner == "RuntimeLimits":
        return "HOST_LIMIT"
    if field.owner == "IndividualCareProfile" or field.key in {
        "EnvironmentCareProfile.temperature_c", "EnvironmentCareProfile.relative_humidity"
    }:
        return "CONTEXT_METADATA"
    if field.owner in INPUT_SCHEMAS:
        return "INPUT_OR_FIXTURE"
    if field.type == "bool" or field.type.startswith("std::optional"):
        return "MODE_SWITCH"
    return "MODEL_SETTING"


def parameter_rows(definitions, constants, sources):
    info = metadata()
    result = []
    for owner, schema in definitions.items():
        for field in schema:
            unit, role = info[field.key]
            caste, stage = SPECIAL_SCOPE.get(field.key, FIELD_SCOPE.get(owner, ("Context-dependent", "Context-dependent")))
            result.append(dict(
                ParameterKey=field.key, RecordKind="DECLARED_SOURCE", ValueRoleClass=value_role(field),
                MechanismIds=OWNERS[owner],
                SourceFile=field.source, StartLine=field.first, EndLine=field.last, Declaration=owner,
                SourceExpression=compact(field.initializer), CurrentSourceValue=source_value(field, field.initializer),
                Unit=unit, Role=role, Scope="Explicit fixture controls" if field.source.startswith("cpp/apps/") else "Declared default when the owning object or policy is used",
                Caste=caste, LifeStage=stage, Species="Lasius niger target or engineering context",
                ParameterEvidenceClass="ENGINEERING_FIXTURE", AtlasGrade="F", SourceAnchorIds="", **PAPER_FIELDS,
            ))
    for row in constants:
        result.append(dict(
            ParameterKey=row["ParameterKey"], RecordKind="REVIEWED_CORE_RULE",
            ValueRoleClass="UNIT_CONVERSION" if row["ParameterKey"] in UNIT_CONVERSIONS else "EXECUTION_RULE",
            MechanismIds=row["MechanismIds"],
            SourceFile=row["SourceFile"], StartLine=int(row["StartLine"]), EndLine=int(row["EndLine"]),
            Declaration=row["Function"], SourceExpression=row["Expression"], CurrentSourceValue=row["Expression"],
            Unit=row["Unit"], Role=row["Role"], Scope=row["RuntimeScope"], Caste=row["Caste"],
            LifeStage=row["LifeStage"], Species="Lasius niger target or engineering context",
            ParameterEvidenceClass="ENGINEERING_FIXTURE", AtlasGrade="F", SourceAnchorIds=row["SourceAnchorIds"], **PAPER_FIELDS,
        ))
    for row in result:
        src = sources[row["SourceFile"]]
        row["SourceSpanSha256"] = digest("\n".join(src.lines[row["StartLine"] - 1:row["EndLine"]]))
    require(len({row["ParameterKey"] for row in result}) == len(result), "Duplicate parameter key")
    return sorted(result, key=lambda row: (row["SourceFile"], row["StartLine"], row["ParameterKey"]))


def fixture_rows(fixture_sources, definitions):
    owner_names = "|".join(OWNERS)
    field_owners = defaultdict(list)
    for owner, members in definitions.items():
        for field in members:
            field_owners[field.name].append(owner)
    type_by_field = {field.key: field.type for schema in definitions.values() for field in schema}
    declarations = re.compile(rf"\b({owner_names})\s*(?:[&*]\s*)?(\w+)\s*(?=[=;,{{)\[])")
    aggregates = re.compile(rf"\b({owner_names})(?:\s+(\w+)(?:\s*=)?)?\s*\{{")
    functions = re.compile(rf"\b({owner_names})\s+(\w+)\s*\(")
    methods = re.compile(rf"\b({'|'.join(API_TYPES)})\s*\(")
    constructors = re.compile(r"\bWorldRuntime\s+(\w+)\s*(?:=\s*WorldRuntime\s*)?([({])")
    assignment = re.compile(r"\b(\w+(?:(?:\.|->)\w+)+)\s*(?:[-+*/%]?=(?!=)|\+\+|--)")
    result = []

    for src in fixture_sources:
        if src.path.endswith(".json"):
            contract = ("Reference design fixture, not loaded by the headless parser" if "biology" in src.path
                        else "Diagnostic scenario input")
            for number, line in enumerate(src.lines, 1):
                if line.strip() in {"{", "}", "},", "[", "]", "],"}:
                    continue
                result.append(dict(SourceFile=src.path, StartLine=number, EndLine=number,
                                   Kind="JSON_SCENARIO_SOURCE", Context=contract, ParameterCandidates="",
                                   Resolution="EXACT_JSON_SOURCE_LINE", SourceExpression=line.strip()))
            continue
        known = list(declarations.finditer(src.code))
        typed_positions = set()

        def add(start, stop, kind, context, keys="", resolution="UNBOUND_SOURCE_EXPRESSION"):
            start, stop = trim(src.code, start, stop)
            result.append(dict(**src.location(start, stop), Kind=kind, Context=context, ParameterCandidates=keys,
                               Resolution=resolution, SourceExpression=compact(src.raw[start:stop])))

        def add_aggregate(opening, owner, context, origin):
            if (opening, owner) in typed_positions:
                return
            typed_positions.add((opening, owner))
            end = group_end(src.code, opening)
            segments = [trim(src.code, first, last)
                        for first, last in parts(src.code, opening + 1, end - 1)
                        if src.code[first:last].strip()]
            schema = definitions[owner]
            if len(segments) > len(schema):
                add(opening, end, origin, context, resolution="UNRESOLVED_AGGREGATE_ARITY")
                return
            for ordinal, (start, stop) in enumerate(segments):
                field = schema[ordinal]
                designated = re.match(r"\.(\w+)\s*=", src.code[start:stop])
                if designated:
                    field = next((member for member in schema if member.name == designated[1]), None)
                    if field is None:
                        add(start, stop, origin, context, resolution="UNRESOLVED_DESIGNATED_MEMBER")
                        continue
                add(start, stop, origin, context, field.key,
                    "DESIGNATED_MEMBER" if designated else "DECLARED_AGGREGATE_POSITION")
                child_type = type_by_field[field.key]
                if child_type in definitions and src.code[start] == "{":
                    add_aggregate(start, child_type, field.key, origin)

        for match in aggregates.finditer(src.code):
            opening = match.end() - 1
            if re.search(r"\bstruct\s*$", src.code[max(0, match.start() - 20):match.start()]):
                continue
            add_aggregate(opening, match[1], match[2] or match[1], "TYPED_AGGREGATE")
        for match in functions.finditer(src.code):
            end = group_end(src.code, match.end() - 1)
            body = re.match(r"\s*(?:noexcept\s*)?\{", src.code[end:])
            if body is None:
                continue
            opening = end + body.end() - 1
            closing = group_end(src.code, opening)
            for returned in re.finditer(r"\breturn\s*\{", src.code[opening:closing]):
                add_aggregate(opening + returned.end() - 1, match[1], match[2], "TYPED_HELPER_RETURN")
        for match in re.finditer(r"(?<![.\w])(\w+)\s*=\s*\{", src.code):
            owners = {declaration[1] for declaration in known
                      if declaration[2] == match[1] and declaration.start() < match.start()}
            if len(owners) == 1:
                add_aggregate(match.end() - 1, next(iter(owners)), match[1], "WHOLE_ASSIGNMENT_CANDIDATE")
        for match in assignment.finditer(src.code):
            expression = re.split(r"\.|->", match[1])
            name = expression[-1]
            if name not in field_owners:
                continue
            owners = {declaration[1] for declaration in known
                      if declaration[2] == expression[0] and declaration.start() < match.start()}
            for member in expression[1:-1]:
                owners = {type_by_field.get(f"{owner}.{member}", "") for owner in owners}
            candidates = sorted({owner for owner in owners if owner in field_owners[name]})
            if not candidates:
                candidates = sorted(field_owners[name])
            stop = next((last for _, last in parts(src.code, match.end(), len(src.code), ";")), match.end())
            add(match.start(), stop, "MEMBER_WRITE", match[1], ";".join(f"{o}.{name}" for o in candidates),
                "LEXICAL_OWNER_CANDIDATE" if len(candidates) == 1 else "AMBIGUOUS_OWNER_CANDIDATES")

        def add_call(start, opening, name, context):
            end = group_end(src.code, opening)
            add(start, end, "API_BINDING", context, resolution="SYMBOLIC_ARGUMENTS_AND_OMITTED_DEFAULTS")
            for ordinal, (begin, stop) in enumerate(parts(src.code, opening + 1, end - 1)):
                types = API_TYPES[name]
                if ordinal >= len(types) or not types[ordinal]:
                    continue
                first, last = trim(src.code, begin, stop)
                if first < last and src.code[first] == "{":
                    add_aggregate(first, types[ordinal], name, "API_AGGREGATE")

        for match in methods.finditer(src.code):
            add_call(match.start(), match.end() - 1, match[1], match[1])
        for match in constructors.finditer(src.code):
            add_call(match.start(), match.end() - 1, "WorldRuntime", match[1])

    unique = {tuple(row.values()): row for row in result}
    return sorted(unique.values(), key=lambda row: (row["SourceFile"], row["StartLine"], row["EndLine"],
                                                     row["Kind"], row["ParameterCandidates"], row["SourceExpression"]))


def state_symbols(sources):
    result = []
    for src in sources:
        for match in re.finditer(r"\benum\s+class\s+(\w+)\s*:\s*[\w:]+\s*\{", src.code):
            enum = match[1]
            if enum not in STATE_GROUPS:
                continue
            role, mechanisms = STATE_GROUPS[enum]
            opening = match.end() - 1
            for start, stop in parts(src.code, opening + 1, group_end(src.code, opening) - 1):
                start, stop = trim(src.code, start, stop)
                token = re.match(r"\w+", src.code[start:stop])
                require(token is not None, f"Unparsed enum member {enum}: {src.raw[start:stop]}")
                value = token[0]
                specific = role
                if enum == "CareAct":
                    if value in OBSERVER_ONLY_CARE:
                        specific = "Observer alias for a committed ordinary action, not a care motor state"
                    elif value == "Count":
                        specific = "Array extent sentinel, not a behavior"
                result.append(dict(Enum=enum, Symbol=value, **src.location(start, stop),
                                   SourceExpression=compact(src.raw[start:stop]), Role=specific, MechanismIds=mechanisms))
    require({row["Enum"] for row in result} == set(STATE_GROUPS), "Incomplete state enumeration scan")
    require(len({(row["Enum"], row["Symbol"]) for row in result}) == len(result), "Ambiguous state enumeration")
    return sorted(result, key=lambda row: (row["SourceFile"], row["StartLine"]))


def review_candidates(sources, covered, fixture_keys, reviews, keys):
    old = csv.DictReader(io.StringIO(git("show", f"{STEP_1}:research/s6_4_preflight/SOURCE_NUMERIC_CANDIDATES.csv")))
    previous = {(row["SourceFile"], int(row["StartLine"])): row for row in old}
    seen_reviews = set()
    for src in sources:
        is_fixture = src.path.startswith(("cpp/apps/", "cpp/tests/"))
        if src.path.endswith((".json", ".cmake")) or not (is_fixture or Path(src.path).name in LITERAL_FILES):
            continue
        for line, (code, raw) in enumerate(zip(src.code.split("\n"), src.raw.split("\n")), 1):
            literals = [match[0] for match in NUMBER.finditer(code)]
            if not literals:
                continue
            key = (src.path, line)
            prior = previous.pop(key, None)
            require(prior is not None and prior["SourceLine"] == raw.strip() and prior["NumericTokens"] == " ".join(literals),
                    f"Frozen numeric candidate drift at {src.path}:{line}")
            linked = sorted(covered.get(key, set()))
            if is_fixture:
                classification = "FIXTURE_OR_TEST_VALUE"
                basis = "Application or test literal in a scenario, assertion, experiment runner or measurement. Runtime settings require their fixture call context."
                params = ";".join(sorted(fixture_keys.get(key, set())))
            else:
                review = reviews.get(key)
                require(review is not None and review["SourceLineSha256"] == digest(raw),
                        f"Missing or stale numeric review at {src.path}:{line}")
                seen_reviews.add(key)
                classification, basis, params = (review[name] for name in ("Classification", "Basis", "ParameterMatrixKeys"))
                require(classification in NUMERIC_CLASSES and classification != "FIXTURE_OR_TEST_VALUE" and basis,
                        f"Invalid numeric review at {src.path}:{line}")
            parameter_keys = set(filter(None, params.split(";")))
            require(parameter_keys <= keys, f"Unknown numeric parameter at {src.path}:{line}")
            if classification == "BIOLOGICAL_PARAMETER":
                require(parameter_keys and parameter_keys <= set(linked),
                        f"Biological candidate lacks a verified parameter span at {src.path}:{line}")
            yield dict(SourceFile=src.path, StartLine=line, EndLine=line,
                       Scope="FIXTURE_OR_TEST" if is_fixture else "CORE_EXECUTION",
                       NumericTokens=" ".join(literals), ReviewedAnchorCandidates=";".join(linked),
                       Step1Status=prior["Status"], Classification=classification, ClassificationBasis=basis,
                       ParameterMatrixKeys=params,
                       SourceLine=raw.strip())
    require(not previous, f"Missing original numeric candidates: {len(previous)}")
    require(seen_reviews == set(reviews), f"Orphan core numeric reviews: {set(reviews) - seen_reviews}")


def verify_span(row, source, regions):
    anchor = row["AnchorId"]
    first, last = int(row["StartLine"]), int(row["EndLine"])
    require(1 <= first <= last <= len(source.lines), f"{anchor}: invalid range in {source.path}:{first}-{last}")
    require(row["SourceFileSha256"] == source.sha256, f"{anchor}: file hash drift in {source.path}")
    require(row["SourceSpanSha256"] == digest("\n".join(source.lines[first - 1:last])),
            f"{anchor}: span hash drift in {source.path}:{first}-{last}")
    matches = [region for region in regions if (region.kind, region.symbol) == (row["SymbolKind"], row["Symbol"])]
    require(len(matches) == 1, f"{anchor}: expected one {row['SymbolKind']} {row['Symbol']} in {source.path}, found {matches}")
    region = matches[0]
    require((int(row["DeclarationLine"]), int(row["DefinitionEndLine"])) == (region.first, region.last),
            f"{anchor}: stored declaration range does not match {region}")
    require(region.first <= first <= last <= region.last, f"{anchor}: {first}-{last} is outside {region}")
    require(any(line.strip() for line in source.code.splitlines()[first - 1:last]),
            f"{anchor}: range contains no source code")


def verify_record_anchors(tables, sources, anchors):
    by_id = {}
    regions = {}
    for row in anchors:
        aid, path = row["AnchorId"], row["SourceFile"]
        require(aid not in by_id, f"Duplicate source anchor {aid}")
        by_id[aid] = row
        if path not in regions:
            regions[path] = symbol_regions(sources[path])
        verify_span(row, sources[path], regions[path])
        require(row["Role"] in {"PRIMARY", "SUPPORTING"} and row["ScopeVerification"] == "LEXICAL_DECLARATION_CONTAINMENT"
                and row["RelationVerification"] == "MANUAL_REVIEW",
                f"{aid}: lexical membership cannot certify a behavioral or call relationship")
    used = set()
    for record_kind, id_key, rows in tables:
        for row in rows:
            rid = row[id_key]
            linked = [by_id[aid] for aid in row["SourceAnchorIds"].split(";")]
            require(linked and linked[0]["Role"] == "PRIMARY"
                    and all(anchor["Role"] == "SUPPORTING" for anchor in linked[1:]),
                    f"{rid}: expected one primary anchor followed by supporting anchors")
            for anchor in linked:
                aid = anchor["AnchorId"]
                require(aid not in used and (anchor["RecordKind"], anchor["RecordId"]) == (record_kind, rid),
                        f"{rid}: invalid or repeated anchor {aid}")
                used.add(aid)
            primary = linked[0]
            source_keys = ("SourceFile", "StartLine", "EndLine", "SourceSpanSha256")
            require(all(primary[key] == row[key] for key in source_keys) and primary["Symbol"] == row["Function"],
                    f"{rid}: primary anchor projection differs from the verified declaration")
            if "SupportingAnchors" in row:
                require(row["SupportingAnchors"] == ";".join(anchor["AnchorId"] for anchor in linked[1:]),
                        f"{rid}: supporting anchor references differ from the verified declarations")
    require(used == set(by_id), f"Unlinked source anchors: {set(by_id) - used}")


def verify_history(crosswalk, mechanism_ids):
    path = ROOT / "research/s6_3_2_1/RULES.csv"
    with path.open(encoding="utf-8", newline="") as stream:
        previous = {row["RuleId"]: row for row in csv.DictReader(stream)}
    current_ids = {row["HistoricalRuleId"] for row in crosswalk}
    require(len(crosswalk) == len(previous) == len(current_ids) == 70 and set(previous) == current_ids,
            "Historical rules must be accounted for individually")
    for row in crosswalk:
        old = previous[row["HistoricalRuleId"]]
        require(row["HistoricalSourceCommit"] == ATLAS_COMMIT and row["CurrentSourceCommit"] == BASELINE,
                f"Wrong baseline on {row['HistoricalRuleId']}")
        require(row["HistoricalCodeAnchors"] == old["CodeAnchors"] and row["HistoricalSourceIds"] == old["RelatedSourceIds"]
                and row["HistoricalAssessment"] == old["Assessment"], f"Historical drift on {row['HistoricalRuleId']}")
        require(row["CurrentSourceReview"] and set(row["CurrentMechanismIds"].split(";")) <= mechanism_ids,
                f"Missing current review for {row['HistoricalRuleId']}")


def declaration_lines(source, name):
    pattern = rf"^[ \t]*(?:template [^\n]+\s+)?(?:[\w:<>,*&]+\s+)+(?:\w+::)*{name}\s*\("
    result = []
    for match in re.finditer(pattern, source.code, re.M):
        end = group_end(source.code, match.end() - 1)
        body = re.match(r"\s*(?:(?:const|noexcept)\s*)*\{", source.code[end:])
        if body:
            result.append(source.line(match.start()))
    return result


def relocate_historical_anchors(crosswalk, sources):
    old_sources = {}
    for row in crosswalk:
        for anchor in row["HistoricalCodeAnchors"].split("; "):
            path, line, name = re.fullmatch(r"(.+):(\d+) \((\w+)\)", anchor).groups()
            previous_line = int(line)
            if path not in old_sources:
                old_sources[path] = Source(path, git("show", f"{ATLAS_COMMIT}:{path}"))
            old = old_sources[path]
            historical = declaration_lines(old, name)
            require(len(historical) == 1 and 1 <= previous_line <= len(old.lines),
                    f"Cannot locate a unique historical function for {anchor}")
            src = sources[path]
            current = [(src, found) for found in declaration_lines(src, name)]
            if not current:
                current = [(candidate, found) for candidate in sources.values() if candidate.path.startswith("cpp/src/")
                           for found in declaration_lines(candidate, name)]
            require(len(current) == 1, f"Cannot locate a unique current function for {anchor}")
            current_src, current_line = current[0]
            same_file = current_src.path == path
            equal_line = same_file and previous_line <= len(src.lines) and old.lines[previous_line - 1] == src.lines[previous_line - 1]
            yield dict(HistoricalRuleId=row["HistoricalRuleId"], HistoricalSourceFile=path, Function=name,
                       HistoricalAnchorLine=previous_line, HistoricalDeclarationLine=historical[0],
                       CurrentSourceFile=current_src.path, CurrentDeclarationLine=current_line,
                       DeclarationLineDelta=current_line - historical[0] if same_file else "",
                       HistoricalAnchorTextMatchesAtSameLine=equal_line,
                       CurrentMechanismIds=row["CurrentMechanismIds"])


def verify_scope():
    require(git("rev-parse", f"{BASELINE}:cpp") == CORE_TREE, "Frozen Core tree mismatch")
    changes = set(git("diff", "--name-only", BASELINE).splitlines())
    changes.update(git("ls-files", "--others", "--exclude-standard").splitlines())
    audit_files = {
        ".github/workflows/s6_4_preflight.yml",
        "tools/audit_s6_4_preflight.py",
        "tools/test_s6_4_preflight.py",
    }
    outside = sorted(path for path in changes if not path.startswith("research/s6_4_preflight/")
                     and path not in audit_files)
    require(not outside, f"Out-of-scope repository changes: {outside}")


def audit_tables():
    verify_scope()
    paths = git("ls-tree", "-r", "--name-only", BASELINE, "--", "cpp", "scenarios").splitlines()
    sources = {path: Source(path) for path in paths if path.endswith((".cpp", ".hpp", ".h", ".cmake", ".json", "CMakeLists.txt"))}
    mechanisms = read_csv("CURRENT_CORE_MECHANISM_INVENTORY.csv")
    transitions = read_csv("STATE_MACHINE_TRANSITION_EVIDENCE.csv")
    constants = read_csv("REVIEWED_CORE_CONSTANTS.csv")
    crosswalk = read_csv("HISTORICAL_RULE_CROSSWALK.csv")
    anchors = read_csv("SOURCE_ANCHORS.csv")
    ids = {row["MechanismId"] for row in mechanisms}
    require(len(ids) == len(mechanisms), "Duplicate mechanism")
    require(len({row["TransitionId"] for row in transitions}) == len(transitions), "Duplicate transition")
    verify_record_anchors((
        ("MECHANISM", "MechanismId", mechanisms), ("TRANSITION", "TransitionId", transitions),
        ("CORE_RULE", "ParameterKey", constants),
    ), sources, anchors)
    for row in mechanisms + transitions + constants:
        linked = (row.get("MechanismIds") or row["MechanismId"]).split(";")
        require(set(linked) <= ids, f"Unknown mechanisms: {linked}")
    for row in mechanisms + transitions:
        require(row["MechanismEvidenceClass"] == PENDING and row["AtlasGrade"] == PENDING, "Step 1 carries no new evidence grade")
    verify_history(crosswalk, ids)

    definition_sources = [s for s in sources.values() if s.path.startswith(HEADER) or s.path.startswith("cpp/apps/") and s.path.endswith(".hpp")]
    definitions = fields(definition_sources)
    parameters = parameter_rows(definitions, constants, sources)
    fixtures = fixture_rows((s for s in sources.values() if s.path.startswith(("cpp/apps/", "cpp/tests/", "scenarios/"))), definitions)
    states = state_symbols(s for s in sources.values() if s.path.startswith(HEADER))
    keys = {row["ParameterKey"] for row in parameters}
    references = keys | set(definitions) | set(STATE_GROUPS)
    for table, field in ((mechanisms, "ParameterFamilies"), (transitions, "ParameterKeys")):
        for row in table:
            unknown = set(filter(None, row[field].split(";"))) - references
            require(not unknown, f"Unknown parameter reference on {row['MechanismId']}: {unknown}")
    for row in fixtures:
        require(set(filter(None, row["ParameterCandidates"].split(";"))) <= keys,
                f"Unknown fixture parameter at {row['SourceFile']}:{row['StartLine']}")
    for row in parameters + states:
        require(set(row["MechanismIds"].split(";")) <= ids, f"Unknown mechanism at {row['SourceFile']}:{row['StartLine']}")
    covered = defaultdict(set)
    for row in parameters:
        if row["RecordKind"] == "DECLARED_SOURCE":
            for line in range(row["StartLine"], row["EndLine"] + 1):
                covered[row["SourceFile"], line].add(row["ParameterKey"])
    for anchor in anchors:
        if anchor["RecordKind"] == "CORE_RULE":
            for line in range(int(anchor["StartLine"]), int(anchor["EndLine"]) + 1):
                covered[anchor["SourceFile"], line].add(anchor["RecordId"])
    fixture_keys = defaultdict(set)
    for row in fixtures:
        for line in range(row["StartLine"], row["EndLine"] + 1):
            fixture_keys[row["SourceFile"], line].update(filter(None, row["ParameterCandidates"].split(";")))
    core_reviews = read_csv("CORE_NUMERIC_REVIEW.csv")
    reviews = {(row["SourceFile"], int(row["Line"])): row for row in core_reviews}
    require(len(core_reviews) == len(reviews), "Duplicate numeric review")
    candidates = list(review_candidates(sources.values(), covered, fixture_keys, reviews, keys))

    cmake = sources["cpp/CMakeLists.txt"].raw
    core = {"cpp/" + path for path in re.search(r"add_library\(antworld_core\s+([^)]*)\)", cmake)[1].split()}
    require(core <= set(sources), "A compiled Core translation unit is missing")
    counts = [Counter(row["SourceFile"] for row in table) for table in
              (mechanisms, transitions, parameters, fixtures, states, candidates)]
    coverage = []
    for src in sources.values():
        path = src.path
        if path in core:
            role = "CORE_TRANSLATION_UNIT"
        elif path.startswith(("cpp/src/", HEADER)):
            role = "CORE_SUPPORT"
        elif path.startswith(("cpp/apps/", "cpp/tests/", "scenarios/")):
            role = "FIXTURE_OR_TEST_SOURCE"
        else:
            role = "BUILD_OR_PERSISTENCE_BOUNDARY"
        coverage.append(dict(SourceFile=path, Role=role, LineCount=len(src.lines), SourceSha256=src.sha256,
                             Mechanisms=counts[0][path], Transitions=counts[1][path], ParameterRows=counts[2][path],
                             FixtureRows=counts[3][path], StateSymbols=counts[4][path], NumericCandidateLines=counts[5][path]))
    tables = {
        "PARAMETER_EVIDENCE_MATRIX.csv": parameters,
        "FIXTURE_CONFIGURATION_INDEX.csv": fixtures,
        "STATE_SYMBOL_INDEX.csv": states,
        "SOURCE_NUMERIC_CANDIDATES.csv": candidates,
        "SOURCE_FILE_COVERAGE.csv": coverage,
        "HISTORICAL_ANCHOR_RELOCATION.csv": list(relocate_historical_anchors(crosswalk, sources)),
    }
    summary = dict(compiled_core_units=len(core), source_files=len(sources), mechanisms=len(mechanisms),
                   implemented_mechanisms=sum(row["ImplementationStatus"] == "IMPLEMENTED" for row in mechanisms),
                   transitions=len(transitions), parameter_rows=len(parameters), declared_members=sum(map(len, definitions.values())),
                   parameter_owners=len(definitions), reviewed_core_rules=len(constants), history_rows=len(crosswalk),
                   historical_dispositions=dict(sorted(Counter(row["Disposition"] for row in crosswalk).items())),
                   state_symbols=len(states), state_groups=len(STATE_GROUPS),
                   fixture_rows=len(fixtures), fixture_kinds=dict(sorted(Counter(row["Kind"] for row in fixtures).items())),
                   fixture_ambiguous_owners=sum(row["Resolution"] == "AMBIGUOUS_OWNER_CANDIDATES" for row in fixtures),
                   historical_anchors=len(tables["HISTORICAL_ANCHOR_RELOCATION.csv"]),
                   historical_moved_declarations=sum(row["DeclarationLineDelta"] != 0 for row in tables["HISTORICAL_ANCHOR_RELOCATION.csv"]),
                   verified_source_anchors=len(anchors),
                   source_anchors_by_role=dict(sorted(Counter(row["Role"] for row in anchors).items())),
                   numeric_classifications=dict(sorted(Counter(row["Classification"] for row in candidates).items())),
                   formerly_linked_candidates=sum(row["Step1Status"] == "WITH_REVIEWED_SOURCE_SPAN" for row in candidates),
                   lexical_candidates=len(candidates), mechanism_domains=dict(sorted(Counter(row["Domain"] for row in mechanisms).items())))
    return tables, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify the generated CSVs without writing files")
    args = parser.parse_args()
    tables, summary = audit_tables()
    for name, rows in tables.items():
        expected = csv_text(rows)
        path = REPORT / name
        if args.check:
            require(path.read_text(encoding="utf-8") == expected, f"Generated table drift: {name}")
        else:
            path.write_text(expected, encoding="utf-8", newline="\n")
    print(json.dumps(summary, indent=2))
    print("PASS: frozen source scope and audit tables verified" if args.check else "Generated source indexes")


if __name__ == "__main__":
    main()
