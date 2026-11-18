"""Projections of the reviewed Core's checkpoint and canonical fact codecs."""

from dataclasses import dataclass
from math import isfinite
from struct import Struct, unpack_from
from uuid import UUID


class ArchiveError(ValueError):
    """The input cannot be observed under the supported archive contract."""


def require(condition, message):
    if not condition:
        raise ArchiveError(message)


MASK = (1 << 64) - 1
SAFE_TIME = (1 << 53) - 1
U64 = Struct("<Q")
U32 = Struct("<I")
POSITION = Struct("<3d")
MASS = Struct("<4Q")
BOX = Struct("<6i")
FACT = Struct("<5QB3QB3Q3d4Q4BdB")
OBS = Struct("<2B3QB3d")
KINDS = tuple("""Diagnostic ColonySeeded AntSeeded FoodSeeded Moved FoodCollected ActionRejected StageChanged AntDied
SurfaceConfigured ForagingStarted ForagingDecision FoodDelivered Rested TrailMaintenance PhysiologyEnabled
PhysiologyUpdated BehaviorChanged NutritionDecision CargoIngested NestIngested NutritionTransferred GeometryConfigured
SoilExcavated SoilDropped SoilPickedUp SoilFilled ExcavationDecision FoodPlaced SocialConfigured AutonomyChanged
AutonomyDecision LongTermConfigured ReproductionEnabled ReproductionAttempt AntBorn ResourceCycleConfigured
ResourceReleased ProteinRecycled BiologyConfigured CareProgramChanged CareTick BiologicalObservation BroodMoved
FoundingConfigured FoundingReserveSeeded FoundingEggFunded FoundingLipidConverted FoundingRation FoundingLipidMobilized
FoundingHatchCue FoundressNestMeal FoundingDietaryEggFunded FoundingBoundaryUptake RecruitmentCue RecruitmentObserved
RecruitmentActivated ActivityChanged FoundressWaterIngested""".split())

STAGES = ("Egg", "Larva", "Pupa", "Adult", "Dead")
CASTES = ("Worker", "Queen", "Male")
PROGRAMS = ("Paused", "Rest", "Nurse", "Forage", "Excavate")
FORAGING_MODES = ("Explore", "Follow trail", "Follow memory", "Collect", "Return", "Deliver", "Rest")
FORAGING_REASONS = ("None", "Search", "Local food", "Trail", "Memory", "Home trace", "Nest contact", "No legal step")
DEATHS = ("Unknown", "Energy depleted", "Dehydration", "Fixture death")
OUTCOMES = ("Success", "Partial", "Missing entity", "Dead actor", "Invalid stage", "Out of bounds", "Too fast",
            "Stale position", "Out of reach", "Depleted", "Capacity", "Duplicate action", "Invalid transition",
            "Already dead", "Blocked", "Non-local move", "Away from nest", "Empty inventory", "Stale geometry",
            "Non-diggable", "Invalid geometry", "Insufficient energy")
ACTS = ("Inactive", "Walk", "Approach brood", "Inspect brood", "Arrange brood", "Clean brood", "Transport brood",
        "Feed brood", "Close worker contact", "Collect food", "Deliver food", "Ingest food", "Transfer nutrition",
        "Excavate", "Handle soil", "Revisit brood site", "Pick up brood", "Place brood", "Return to care shelter",
        "Move to a resting site", "Approach the depot", "Approach a nestmate", "Yield to a food carrier",
        "Entrance patrol", "Entrance antennal contact")
PHASES = ("Opportunity", "Selected", "Started", "Completed", "Interrupted")
RELATED = {21, 35, 43, 46, 48, 50, 52, 55, 56}
FACETS = {
    "birth": (35,), "stage": (7,), "death": (8,), "nutrition": (19, 20, 21, 38, 48, 51, 53, 58),
    "care": (40, 42, 43, 48, 50), "food": (3, 5, 12, 28, 37), "recruitment": (54, 55, 56),
    "soil": (23, 24, 25, 26), "movement": (4, 43), "rejected": (6,), "tasks": (17, 57),
}
HIGHLIGHTS = {5, 7, 8, 12, 21, 23, 24, 25, 26, 35, 43, 48, 56, 58}


def fnv(data, value=14695981039346656037):
    for byte in data:
        value = ((value ^ byte) * 1099511628211) & MASK
    return value


def world_id(hi, lo):
    return str(UUID(int=(hi << 64) | lo))


def sql_id(value):
    return value if value < (1 << 63) else value - (1 << 64)


def label(values, index):
    return values[index] if index is not None and 0 <= index < len(values) else "Not recorded"


@dataclass(slots=True)
class Fact:
    id: int
    time: int
    source: int
    revision: int
    payload: int
    aux: int
    kind: int
    actor: int
    colony: int
    resource: int
    position: tuple
    mass: tuple
    stage: int
    outcome: int
    mode: int
    reason: int
    deposited_units: float
    forgot_memory: bool
    observation: tuple | None

    @property
    def related(self):
        if self.observation:
            return self.observation[2]
        return self.payload if self.kind in RELATED else 0

    def packet(self):
        result = dict(id=str(self.id), time_ms=self.time, kind=KINDS[self.kind], actor=str(self.actor) if self.actor else None,
                      related=str(self.related) if self.related else None, source=str(self.source) if self.source else None,
                      colony=str(self.colony) if self.colony else None, resource=str(self.resource) if self.resource else None,
                      position_m=self.position, stage=label(STAGES, self.stage) if self.actor else None,
                      outcome=label(OUTCOMES, self.outcome), mass_ug=self.mass, payload=str(self.payload), auxiliary=str(self.aux),
                      evidence="COMMITTED_FACT")
        if self.kind == 8:
            result["death_cause"] = label(DEATHS, self.payload)
        if self.kind == 17:
            result["program"] = label(PROGRAMS, self.payload)
        if self.kind == 4 and self.aux:
            duration, turn = self.aux >> 32, self.aux & 0xffffffff
            result["motion"] = dict(begins_ms=self.time-duration, translates_ms=self.time-duration+turn,
                                    duration_ms=duration, turn_ms=turn, ends_ms=self.time)
        if self.kind in (23, 24, 25, 26):
            result["parcel"] = str(self.payload)
        if self.kind == 11:
            result.update(mode=label(FORAGING_MODES, self.mode), reason=label(FORAGING_REASONS, self.reason),
                          forgot_memory=self.forgot_memory)
        if self.deposited_units:
            result["trail_deposited_units"] = self.deposited_units
        if self.observation:
            phase, act, _, bout, began, known, *destination = self.observation
            result["action"] = dict(phase=label(PHASES, phase), act=label(ACTS, act), bout=str(bout) if bout else None,
                                    began_ms=began if known else None, destination_m=destination)
        return result


def decode_fact(data, offset=0):
    (identifier, hi, lo, time, source, action, revision, payload, aux, kind, actor, colony, resource, x, y, z,
     c, p, w, o, stage, outcome, mode, reason, deposit, forgot) = FACT.unpack_from(data, offset)
    require(kind < len(KINDS) and time <= SAFE_TIME and action <= 2 and stage < len(STAGES) and outcome < len(OUTCOMES)
            and mode <= 6 and reason <= 7 and forgot <= 1 and isfinite(x) and isfinite(y) and isfinite(z)
            and isfinite(deposit) and deposit >= 0, "Invalid or unsupported canonical event fields")
    observation = OBS.unpack_from(data, offset + FACT.size) if kind == 42 else None
    if observation:
        phase, act, _, _, began, known, *position = observation
        require(phase < len(PHASES) and act < len(ACTS) and known <= 1 and (not known or began <= time)
                and all(map(isfinite, position)), "Invalid canonical action observation")
    return (hi, lo), Fact(identifier, time, source, revision, payload, aux, kind, actor, colony, resource,
                          (x, y, z), (c, p, w, o), stage, outcome, mode, reason, deposit, bool(forgot), observation)


class Reader:
    def __init__(self, raw):
        self.raw = raw
        self.pos = 0

    def take(self, count):
        require(0 <= count <= len(self.raw) - self.pos, "Truncated checkpoint projection")
        before = self.pos
        self.pos += count
        return self.raw[before:self.pos]

    def unpack(self, form):
        return form.unpack(self.take(form.size))

    def uint(self):
        return self.unpack(U64)[0]

    def flag(self):
        value = self.take(1)[0]
        require(value <= 1, "Invalid checkpoint flag")
        return bool(value)

    def position(self):
        value = self.unpack(POSITION)
        require(all(map(isfinite, value)), "Invalid checkpoint position")
        return value

    def mass(self):
        return self.unpack(MASS)

    def skip_rows(self, size):
        self.take(self.uint() * size)


VERSIONS = {f"AWCKPT{suffix}".encode() + b"\0": pair for suffix, pair in {
    "8": (8, 9), "9": (9, 11), "A": (10, 12), "B": (11, 13), "C": (12, 14), "D": (13, 15),
    "E": (14, 16), "F": (15, 17), "G": (16, 18), "H": (17, 19), "I": (18, 20), "J": (19, 21),
    "K": (20, 22), "L": (21, 23),
}.items()}
ECOLOGICAL = b"AWCKPTM\0"
MICROWORLD_VERSIONS = {(31, 38), (23, 27), (23, 28), (23, 29), (23, 30), (24, 31), (25, 32), (26, 33), (27, 34), (28, 35),
                       (29, 36), (30, 37)}
INNER = {key for key, (schema, _) in VERSIONS.items() if schema <= 13}


def checkpoint_header(r):
    magic = bytes(r.take(8))
    resume = magic == b"AWRESUM1"
    first = tip = 0
    if resume:
        first, tip, _ = r.unpack(Struct("<3Q"))
        require(first <= tip and (not tip or first < tip) and tip - first <= 4096, "Invalid continuation history window")
        magic = bytes(r.take(8))
    framed = magic == b"AWSTATE1"
    if framed:
        magic = bytes(r.take(8))
    ecological = magic == ECOLOGICAL
    if ecological:
        outer = r.unpack(Struct("<2I"))
        require(outer in MICROWORLD_VERSIONS or outer in {(22, 24), (22, 25), (22, 26)},
                "Unsupported ecological checkpoint version")
        magic = bytes(r.take(8))
    version = r.unpack(Struct("<2I"))
    require(VERSIONS.get(magic) == version and r.unpack(U32)[0] == 1, "Unsupported checkpoint or RNG version")
    founding = version[0] >= 15
    if founding:
        magic = bytes(r.take(8))
    continuous = magic == b"AWCKPTE\0"
    if continuous:
        magic = bytes(r.take(8))
    require(magic in INNER and (not founding or magic == b"AWCKPTD\0") and (not ecological or continuous),
            "Unsupported inner checkpoint layout")
    hi, lo, seed, time, revision = r.unpack(Struct("<5Q"))
    require(hi or lo, "Missing checkpoint WorldId")
    require(time <= SAFE_TIME, "Checkpoint time exceeds the browser integer range")
    return framed, resume, first, tip, outer if ecological else None, version, magic, continuous, hi, lo, seed, time, revision


def checkpoint(raw, *, verify_hash=True):
    """Read a committed snapshot, without restoring or advancing a runtime."""
    require(len(raw) >= 124, "Checkpoint is too short")
    content = memoryview(raw)[:-8]
    if verify_hash:
        require(fnv(content) == U64.unpack_from(raw, len(raw) - 8)[0], "Checkpoint checksum mismatch")
    r = Reader(content)
    framed, resume, first, tip, outer, version, magic, continuous, hi, lo, seed, time, revision = checkpoint_header(r)
    ecological = outer is not None
    extended = magic != b"AWCKPT8\0"
    r.take(40)  # Allocators, scheduling sequence and private RNG state.
    r.skip_rows(115)
    cursor = r.uint()
    fact_offset = r.pos
    if not framed:
        require(not resume or tip == cursor, "Continuation cursor mismatch")
        for _ in range(first, cursor):
            require(r.pos + 65 < len(r.raw), "Truncated checkpoint fact prefix")
            length = 210 if r.raw[r.pos + 65] == 42 else 159
            r.take(length)
    fact_end = r.pos
    world_min, world_max = r.position(), r.position()
    max_speed, contact = r.unpack(Struct("<2d"))
    flags = None
    if ecological:
        flags = dict(zip(("distance_clock", "floor_space", "recruitment", "activity_cost"), (r.flag() for _ in range(4))))
        flags.update(zip(("unloaded_m_per_s", "loaded_m_per_s", "soil_handling_ms", "cue_lifetime_ms",
                          "cue_minimum_carbs_ug", "water_sip_ug", "cue_response_ppm", "first_ration_ppm"),
                         r.unpack(Struct("<2d4Q2I"))))
        flags["suppress_foundress_hatch_cue"] = outer[1] in (26, 28, 30)
        if outer[0] >= 23:
            flags["brood_space"] = True
            flags["portable_care_motion"] = outer[1] >= 29
        if outer[1] >= 32:
            flags["local_nest_activity"] = True
        if outer == (24, 31) or (outer[1] >= 32 and r.flag()):
            interval, dwell = r.unpack(Struct("<2q"))
            require(60000 <= interval <= dwell <= 21600000, "Invalid MicroWorld worker timing")
            flags["worker_activity_timing"] = dict(check_ms=interval, minimum_program_ms=dwell)
        if outer[1] >= 33:
            motor, score = r.flag(), r.take(1)[0]
            require(score <= 3 and (motor or score), "Invalid nest dynamics treatment")
            flags["nest_dynamics"] = dict(worker_motor=motor, excavation=score)
        if outer[1] >= 34:
            require(motor, "Body traffic requires the worker motor")
            flags["local_traffic"] = True
        if outer[1] >= 35:
            flags["yield_to_loaded"], flags["local_pantry_checks"] = r.flag(), r.flag()
            require(flags["yield_to_loaded"] or flags["local_pantry_checks"], "Invalid nursery work or traffic policy")
        if outer[1] >= 36:
            brood_site, buffer = r.position(), r.uint()
            require(flags["local_pantry_checks"] and flags["recruitment"] and 0 < buffer <= 1_000_000_000 and
                    all(low <= value <= high for value, low, high in zip(brood_site, world_min, world_max)),
                    "Invalid founding habitat")
            flags["founding_habitat"] = dict(brood_site_m=brood_site, pantry_buffer_ug=buffer)
            if outer[1] == 38:
                flags["founding_habitat"]["sealed_chamber"] = True
            if outer[1] == 37:
                flags["founding_habitat"]["alternate_berth"] = True
    if r.flag():
        r.take(32)
    r.take(8)  # Executed events on the boundary.
    living = r.uint()
    introduced, available, carried, stored = (r.mass() for _ in range(4))
    colonies = {}
    for _ in range(r.uint()):
        identifier, species, founded = r.unpack(Struct("<QBQ"))
        colonies[identifier] = dict(id=str(identifier), species=species, founded_ms=founded, position_m=r.position(), stock_ug=r.mass())
    ants = {}
    for _ in range(r.uint()):
        identifier, colony, born, stage, caste = r.unpack(Struct("<3Q2B"))
        position = r.position()
        position_revision, carrying_capacity = r.unpack(Struct("<2Q"))
        ants[identifier] = dict(id=str(identifier), colony=str(colony), born_ms=born, stage=stage, caste=caste,
                                position_m=position, position_revision=position_revision, carrying_capacity_ug=carrying_capacity,
                                carried_ug=r.mass())
    sources = {}
    for _ in range(r.uint()):
        identifier = r.uint()
        sources[identifier] = dict(id=str(identifier), position_m=r.position(), initial_ug=r.mass(), stock_ug=r.mass())
    surface = None
    if r.flag():
        origin = r.position()
        width, height, step = r.unpack(Struct("<2Id"))
        behavior = r.unpack(Struct("<2B3I4Q4d3I"))
        cells = r.uint()
        require(0 < cells == width * height and isfinite(step) and step > 0, "Invalid surface dimensions")
        walkable = bytes(r.take(cells))
        require(set(walkable) <= {0, 1}, "Invalid surface cell mask")
        surface = dict(origin_m=origin, width=width, height=height, cell_m=step, walkable=walkable,
                       trails_enabled=bool(behavior[0]), memory_enabled=bool(behavior[1]),
                       trail_weight=behavior[-1], trail_half_life_s=behavior[9])
        r.take(14 * 8 + 16)  # Foraging counters and maintenance handle.
        r.skip_rows(1099)
        for stride in (32, 16, 24, 24):
            r.skip_rows(stride)
    for _ in range(r.uint()):
        identifier = r.uint()
        r.take(17 * 8)
        mother = 0
        if extended:
            r.take(16)
            mother = r.uint()
            r.take(8)
        r.take(56)  # Initial physiology.
        crop = r.mass()
        energy, water, protein, oxidized, lost, dissipated, *_ = r.unpack(Struct("<11Q"))
        updated, absorption, progress, _, _ = r.unpack(Struct("<5Q"))
        program, death = r.unpack(Struct("<2B"))
        active_work = r.uint() if flags and flags["activity_cost"] else None
        require(identifier in ants, "Physiology snapshot references an unknown ant")
        ants[identifier].update(mother=str(mother) if mother else None, energy_nj=energy, hydration_ug=water,
                                 tissue_protein_ug=protein, crop_ug=crop, program=program, death_code=death,
                                 updated_ms=updated, next_absorption_ms=absorption, stage_progress_ms=progress,
                                 active_work=str(active_work) if active_work is not None else None,
                                 oxidized_carbs_ug=oxidized, lost_water_ug=lost, dissipated_nj=dissipated)
    geometry, edits, ledger, soil_carriers, soil_piles = None, [], None, set(), []
    if r.flag():
        origin = r.position()
        quantum = r.unpack(Struct("<d"))[0]
        require(isfinite(quantum) and quantum > 0, "Invalid geometry scale")
        solid = r.unpack(BOX)
        dry, water, body, loaded, *_ = r.unpack(Struct("<2Q7I4Q"))
        voids, rocks = ([r.unpack(BOX) for _ in range(r.uint())] for _ in range(2))
        geometry = dict(origin_m=origin, quantum_m=quantum, solid=solid, voids=voids, rocks=rocks,
                        body_half_q=body, loaded_half_q=loaded, dry_ug_per_q3=dry, water_ug_per_q3=water)
        geometry_revision, *ledger = r.unpack(Struct("<7Q"))
        for _ in range(r.uint()):
            edit, source, event, actor, parcel, kind, at = r.unpack(Struct("<5QBQ"))
            edits.append(dict(edit=edit, source=source, event=event, actor=actor, parcel=parcel, kind=kind, time_ms=at,
                              box_q=r.unpack(BOX), volume_q3=r.uint()))
        require(len(edits) == geometry_revision, "Geometry snapshot omits an edit")
        parcel = Struct("<5Q3dB")
        count = r.uint()
        require(count <= (len(r.raw) - r.pos) // parcel.size, "Invalid soil parcel count")
        for _ in range(count):
            identity, origin_edit, _, amount, carrier, x, y, z, state = r.unpack(parcel)
            if state == 0:
                require(carrier in ants and str(carrier) not in soil_carriers, "Invalid soil carrier in checkpoint")
                soil_carriers.add(str(carrier))
            elif state == 1 and amount:
                soil_piles.append(dict(id=str(identity), origin_edit=str(origin_edit), position_m=(x, y, z),
                                       volume_mm3=amount * (quantum * 1000)**3))
    schema, physics = outer if ecological else version
    return dict(world=world_id(hi, lo), seed=seed, time_ms=time, revision=revision, cursor=cursor, framed=framed,
                schema=schema, physics=physics, inner_schema=version[0], inner_physics=version[1], flags=flags,
                world_min_m=world_min, world_max_m=world_max, max_speed_m_per_s=max_speed, contact_m=contact,
                surface=surface, geometry=geometry, edits=edits, soil=ledger, soil_piles=soil_piles,
                soil_carriers=tuple(sorted(soil_carriers, key=int)), first_history_cursor=first,
                colonies=colonies, ants=ants,
                sources=sources, living=living, introduced= introduced, available=available, carried=carried, stored=stored,
                fact_offset=fact_offset, fact_end=fact_end)
