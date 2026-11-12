"""Event-to-lineage reconciliation for the unchanged WP-4 physiology."""

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from read_s6_4_rm02_sidecar import DEATHS, STAGES, require


PARTS = ("carbs", "protein", "water", "other")
ZERO = (0, 0, 0, 0)
ENTRY = {"AntSeeded", "AntBorn"}
DEBITS = {"gift_out", "uptake", "egg_export", "recycled"}


def components(values, prefix):
    return {f"{prefix}_{name}_ug": value for name, value in zip(PARTS, values, strict=True)}


def crop(row):
    return tuple(row[f"crop_{part}_ug"] for part in PARTS)


def death_code(fact):
    # Lifecycle fixture deaths carry a zero payload in the frozen fact schema.
    return (fact.payload or 3) if fact else 0


@dataclass
class Individual:
    spec: dict
    entry: object
    stage: int = field(init=False)
    at: int = field(init=False)
    program: int = 0
    basal: int = 0
    active: int = 0
    heat: int = 0
    export: int = 0
    birth_count: int = 0
    transitions: list = field(default_factory=list)
    flows: dict = field(default_factory=lambda: defaultdict(lambda: ZERO))
    death: object = None
    seen_enable: bool = False

    def __post_init__(self):
        self.stage = self.entry.stage
        self.at = self.entry.time
        require(self.at == self.spec["born_ms"], "lineage entry has wrong origin")
        self.initial_crop = tuple(self.spec[k] for k in ("initial_carbs_ug", "initial_protein_ug",
                                                        "initial_crop_water_ug", "initial_other_ug"))
        self.remaining = self.initial_crop

    def advance(self, at):
        require(at >= self.at, "lineage event reverses observation time")
        if self.stage == 4:
            return
        delta = at - self.at
        self.basal += delta * self.spec["basal_nj_per_ms"]
        if self.stage == 3 and self.program in (2, 3, 4):
            self.active += delta * self.spec["active_nj_per_ms"]
        self.at = at

    def apply(self, name, values):
        self.flows[name] = tuple(a + b for a, b in zip(self.flows[name], values, strict=True))
        sign = -1 if name in DEBITS else 1
        # The birth fact contains both crop protein and water exported from the body.
        crop_values = (0, values[1], 0, 0) if name == "egg_export" else values
        self.remaining = tuple(a + sign * b for a, b in zip(self.remaining, crop_values, strict=True))
        require(min(self.remaining) >= 0, "committed facts overdraw reconstructed crop")

    def evaluate(self, row, at):
        self.advance(at)
        q = self.spec
        require((self.stage, self.program, self.at) == (row["stage"], row["program"], row["settled_at_ms"]),
                "stage, program or settlement identity differs at the cut")
        require(death_code(self.death) == row["death_cause"], "death cause differs")
        require(self.seen_enable or self.entry.kind == "AntBorn", "missing initial physiology fact")
        require(self.remaining == crop(row), "crop ledger differs")
        carbs, protein, water, _ = self.flows["uptake"]
        output_water = self.flows["egg_export"][2]
        energy_in = q["initial_energy_nj"] + carbs * q["yield_nj_per_ug"]
        require((carbs, self.export, q["initial_tissue_ug"] + protein) ==
                (row["oxidized_carbs_ug"], row["exported_nj"], row["tissue_ug"]), "assimilation or birth debit differs")
        require(energy_in == row["energy_nj"] + row["dissipated_nj"] + self.export, "individual energy balance")
        require(q["initial_water_ug"] + water == row["hydration_ug"] + row["lost_water_ug"] + output_water,
                "individual water balance")
        return dict(body_energy_input_nj=energy_in, program_basal_integral_nj=self.basal,
                    program_active_integral_nj=self.active, reconstructed_egg_heat_nj=self.heat,
                    dissipated_outside_nominal_nj=row["dissipated_nj"] - self.heat - self.basal - self.active,
                    **components(self.flows["egg_export"], "export"))

    def disposition(self, stage, horizon):
        origin = next((e for e in (self.entry, *self.transitions) if e.stage == stage), None)
        if origin is None:
            return None
        terminal = next((e for e in self.transitions if e.stage == stage + 1), None)
        if stage == 3:
            terminal = None
        terminal = terminal or self.death
        stop = terminal.time if terminal else horizon
        return dict(stage=STAGES[stage], entry_ms=origin.time, entry_event_id=origin.event, stop_ms=stop,
                    endpoint=("death" if terminal.kind == "AntDied" else "transition") if terminal else "right_censored",
                    event_id=terminal.event if terminal else None, duration_ms=stop - origin.time,
                    death_cause=DEATHS[death_code(terminal)] if terminal and terminal.kind == "AntDied" else None)


class Budgets:
    def __init__(self, specs, configuration):
        self.individuals = {}
        self.specs = specs
        self.config = configuration
        self.attempts = {}
        self.births = {}
        self.gifts = []
        self.uptake = defaultdict(list)
        self.resolutions = {}
        self.counts = Counter()

    def read(self, fact, declared):
        self.counts[fact.kind] += 1
        if fact.source in declared and fact.kind in {"ActionRejected", "NutritionTransferred", "AntDied"}:
            require(fact.source not in self.resolutions, "duplicate external input resolution")
            self.resolutions[fact.source] = fact
        if fact.kind in ENTRY:
            self.entry(fact)
            return
        if fact.actor not in self.individuals:
            return
        actor = self.individuals[fact.actor]
        kind = fact.kind
        if kind in {"BehaviorChanged", "StageChanged", "AntDied"}:
            actor.advance(fact.time)
        if kind == "PhysiologyEnabled":
            require(not actor.seen_enable and fact.mass == actor.initial_crop, "initial crop differs")
            actor.seen_enable = True
        elif kind == "BehaviorChanged":
            actor.program = fact.payload
        elif kind == "StageChanged":
            require(fact.stage == actor.stage + 1 and fact.stage <= 3, "unexpected lifecycle transition")
            actor.transitions.append(fact)
            actor.stage = fact.stage
        elif kind == "AntDied":
            require(actor.stage < 4 and fact.stage == 4, "duplicate or invalid death")
            actor.death, actor.stage, actor.program = fact, 4, 0
        elif kind == "ReproductionAttempt":
            require(fact.source and fact.source not in self.attempts, "duplicate reproductive attempt")
            self.attempts[fact.source] = fact
        elif kind == "NutritionTransferred":
            require(sum(fact.mass) > 0 and fact.outcome in {"Success", "Partial"}, "invalid positive gift")
            require(self.individuals[fact.payload].stage in {1, 3}, "invalid gift recipient stage")
            actor.apply("gift_out", fact.mass)
            self.individuals[fact.payload].apply("gift_in", fact.mass)
            self.gifts.append((fact, self.individuals[fact.payload].stage))
        elif kind == "PhysiologyUpdated":
            actor.apply("uptake", fact.mass)
            self.uptake[fact.actor].append(fact)
            require(not any(fact.mass) or actor.stage in (1, 3), "positive egg or pupal uptake")
        elif kind in {"NestIngested", "CargoIngested", "ProteinRecycled"}:
            actor.apply({"NestIngested": "withdrawn", "CargoIngested": "ingested", "ProteinRecycled": "recycled"}[kind],
                        fact.mass)

    def entry(self, fact):
        require(fact.actor not in self.individuals, "reused individual ID")
        individual = Individual(self.specs[fact.actor], fact)
        self.individuals[fact.actor] = individual
        q = individual.spec
        if fact.kind != "AntBorn":
            require(q["mother"] == 0, "external seed cannot have a maternal debit")
            return
        require(fact.stage == 0 and fact.payload == q["mother"] != 0 and fact.source not in self.births,
                "invalid child lineage")
        mother = self.individuals[fact.payload]
        attempt = self.attempts[fact.source]
        require((attempt.actor, attempt.payload, attempt.time) == (fact.payload, fact.actor, fact.time),
                "birth lacks the funded attempt")
        require(fact.mass == (0, q["initial_tissue_ug"], q["initial_water_ug"], 0) and individual.initial_crop == ZERO
                and fact.auxiliary == q["initial_energy_nj"], "birth credit disagrees with child stores")
        require(fact.auxiliary == int(self.config["egg_export_nj"])
                and fact.mass[1:3] == (int(self.config["egg_export_protein_ug"]), int(self.config["egg_export_water_ug"])),
                "birth credit disagrees with frozen debit")
        mother.apply("egg_export", fact.mass)
        mother.export += fact.auxiliary
        mother.heat += int(self.config["egg_heat_nj"])
        mother.birth_count += 1
        self.births[fact.source] = fact
