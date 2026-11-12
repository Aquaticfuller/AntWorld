"""Independently replay committed geometry edits and material custody."""

from collections import Counter, deque
from dataclasses import dataclass
from itertools import product
import math

from read_s6_4_rm02_sidecar import require
from verify_s6_4_wp3 import row, rows, sequence


AXES = "xyz"
NEIGHBORS = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
SOIL_FACTS = {"SoilExcavated", "SoilFilled", "SoilDropped", "SoilPickedUp"}
PHASES = ("Opportunity", "Selected", "Started", "Completed", "Interrupted")


def cells(record):
    return product(*(range(int(record[f"min_{a}_q"]), int(record[f"max_{a}_q"])) for a in AXES))


def within(a, b, epsilon=1e-12):
    return all(abs(x - y) <= epsilon for x, y in zip(a, b, strict=True))


class Grid:
    def __init__(self, layout):
        self.solid = set(cells(layout[0]))
        require(layout[0]["kind"] == "solid", "initial solid row absent")
        self.rock, self.void = set(), set()
        for r in layout[1:]:
            area = set(cells(r))
            require(area <= self.solid, "initial geometry outside solid")
            if r["kind"] == "void":
                self.void |= area
            else:
                require(r["kind"] == "rock" and not (area & self.void), "invalid rock layout")
                self.rock |= area
        self.soil = self.solid - self.rock - self.void

    def edit(self, entry, excavation):
        region = set(cells(entry))
        require(region <= self.solid and not region & self.rock, "authoritative edit touches non-editable material")
        source, destination = (self.soil, self.void) if excavation else (self.void, self.soil)
        changed = source & region
        require(len(changed) == int(entry["volume_q3"]) > 0, "edit amount differs from initial-solid replay")
        source.difference_update(changed)
        destination.update(changed)
        return len(changed)

    def connected(self, origin):
        if origin not in self.void:
            return 0
        seen = {origin}
        pending = deque([origin])
        while pending:
            a, b, c = pending.popleft()
            for x, y, z in NEIGHBORS:
                point = a + x, b + y, c + z
                if point in self.void and point not in seen:
                    seen.add(point)
                    pending.append(point)
        return len(seen)

    def swept(self, a, b, half):
        swept = product(*(range(min(x, y) - half, max(x, y) + half) for x, y in zip(a, b, strict=True)))
        return all(point not in self.solid or point in self.void for point in swept)


@dataclass
class Parcel:
    origin_edit: int
    initial: int
    remaining: int
    carrier: int
    position: tuple
    state: int = 0


class MaterialReplay:
    def __init__(self, dest, run, tables):
        g = row(dest / "geometry_config.csv")
        self.quantum = float(g["quantum_m"])
        self.origin = tuple(float(g[f"origin_{a}_m"]) for a in AXES)
        self.dry, self.water = int(g["dry_ug_per_q3"]), int(g["water_ug_per_q3"])
        self.dig_energy = int(g["energy_nj_per_q3"])
        self.grid = Grid(list(rows(dest / "layout.csv")))
        self.base_soil = len(self.grid.soil)
        self.edit_rows = sequence(rows(dest / "edits.csv"), lambda r: int(r["event"]))
        self.edits = self.excavated = self.filled = self.loaded_moves = 0
        self.distance_m = 0.0
        self.positions, self.parcels, self.carriers = {}, {}, {}
        self.dead = set()
        self.excavating = set()
        self.totals = Counter()
        self.run, self.tables = run, tables
        self.schedules = sequence(rows(dest / "inputs.csv"), lambda r: int(r["scheduled_id"]))
        self.selected, self.resolutions = {}, {}

    def quantize(self, position):
        point = tuple(round((a - b) / self.quantum) for a, b in zip(position, self.origin, strict=True))
        require(within(position, tuple(a + b * self.quantum for a, b in zip(self.origin, point, strict=True))),
                "unaligned diagnostic position")
        return point

    def read(self, fact):
        actor, kind = fact.actor, fact.kind
        if kind in {"AntSeeded", "AntBorn"}:
            self.positions[actor] = fact.position
        if kind == "AntDied":
            self.dead.add(actor)
        if kind in {"BehaviorChanged", "AntDied"}:
            entered = kind == "BehaviorChanged" and fact.payload == 4
            if entered != (actor in self.excavating):
                if entered:
                    self.excavating.add(actor)
                else:
                    self.excavating.remove(actor)
                self.tables.add("excavation_program_boundaries", self.run, event=fact.event, actor=actor,
                                sim_ms=fact.time, source=fact.source, boundary="enter" if entered else "exit",
                                event_kind=kind, provenance="COMMITTED_FACT", physical_work_duration="UNOBSERVED")
        if kind == "BiologicalObservation" and fact.care[1] in (13, 14):
            phase, act, _, bout, began, known, *_ = fact.care
            if phase == 1:
                self.selected[bout] = fact.event
            self.tables.add("soil_action_observations", self.run, event=fact.event, actor=actor, sim_ms=fact.time,
                            source=fact.source, bout=bout, phase=PHASES[phase], act="dig" if act == 13 else "handle_soil",
                            started_ms=began if known else "UNOBSERVED", outcome=fact.outcome, provenance="COMMITTED_FACT")
        if fact.source in self.schedules and kind in SOIL_FACTS | {"Moved", "ActionRejected"}:
            require(fact.source not in self.resolutions, "host request has duplicate resolution")
            self.resolutions[fact.source] = fact
        if kind in {"Moved", "BroodMoved"}:
            if actor in self.carriers:
                previous = self.positions[actor]
                parcel = self.parcels[self.carriers[actor]]
                distance = math.dist(previous, fact.position)
                self.loaded_moves += 1
                self.distance_m += distance
                parcel.position = fact.position
                self.tables.add("loaded_soil_motion", self.run, event=fact.event, actor=actor, sim_ms=fact.time,
                                source=fact.source, parcel=self.carriers[actor], distance_m=round(distance, 12),
                                carried_q3=parcel.remaining, dry_ug=parcel.remaining * self.dry,
                                water_ug=parcel.remaining * self.water,
                                **{f"from_{a}_m": p for a, p in zip(AXES, previous, strict=True)},
                                **{f"to_{a}_m": p for a, p in zip(AXES, fact.position, strict=True)}, provenance="RECONSTRUCTED")
            self.positions[actor] = fact.position
        if kind == "ExcavationDecision":
            self.totals["decisions"] += 1
        if kind == "ActionRejected" and fact.source in self.selected:
            self.totals[f"rejected_{fact.outcome}"] += 1
            self.tables.add("soil_rejections", self.run, event=fact.event, selection=self.selected[fact.source],
                            actor=actor, sim_ms=fact.time, source=fact.source, outcome=fact.outcome)
        if kind not in SOIL_FACTS:
            return
        parcel_id = fact.payload
        edit_id = ""
        if kind in {"SoilExcavated", "SoilFilled"}:
            excavation = kind == "SoilExcavated"
            entry = self.edit_rows.pop(fact.event)
            self.edits += 1
            edit_id = self.edits
            require(tuple(int(entry[key]) for key in ("edit", "actor", "source", "parcel", "sim_ms")) ==
                    (self.edits, actor, fact.source, parcel_id, fact.time), "edit lacks matching committed event")
            require(entry["kind"] == ("excavate" if excavation else "fill"), "edit opcode differs")
            moved = self.grid.edit(entry, excavation)
            if excavation:
                require(actor not in self.carriers and parcel_id not in self.parcels, "invalid excavation custody")
                self.excavated += moved
                self.carriers[actor] = parcel_id
                self.parcels[parcel_id] = Parcel(self.edits, moved, moved, actor, fact.position)
            else:
                require(self.carriers.get(actor) == parcel_id, "fill without custody")
                self.filled += moved
                parcel = self.parcels[parcel_id]
                parcel.remaining -= moved
                require(parcel.remaining >= 0, "filled more than stored parcel")
                if not parcel.remaining:
                    parcel.state, parcel.carrier = 2, 0
                    del self.carriers[actor]
        else:
            parcel = self.parcels[parcel_id]
            moved = parcel.remaining
            parcel.position = fact.position
            if kind == "SoilDropped":
                require(self.carriers.pop(actor) == parcel_id, "drop without custody")
                parcel.state, parcel.carrier = 1, 0
            else:
                require(actor not in self.carriers and parcel.state == 1, "pickup without available parcel")
                parcel.state, parcel.carrier = 0, actor
                self.carriers[actor] = parcel_id
        self.totals[kind] += 1
        self.totals[f"{kind}_q3"] += moved
        self.tables.add("soil_actions", self.run, event=fact.event, actor=actor, sim_ms=fact.time, source=fact.source,
                        action=kind, parcel=parcel_id, edit=edit_id, moved_q3=moved, dry_ug=moved * self.dry,
                        water_ug=moved * self.water, source_class="host" if fact.source in self.schedules else "autonomous",
                        fixture_dig_cost_nj=moved * self.dig_energy if kind == "SoilExcavated" else 0,
                        selection=self.selected.get(fact.source, "UNOBSERVED"), **{f"{a}_m": p for a, p in zip(AXES, fact.position, strict=True)})

    def check_cut(self, current, route, world_ledger, nest):
        carry = sum(p.remaining for p in self.parcels.values() if p.state == 0)
        deposits = sum(p.remaining for p in self.parcels.values() if p.state == 1)
        values = (self.base_soil, len(self.grid.soil), carry, deposits, self.edits, self.excavated, self.filled)
        names = ("soil_initial_q3", "soil_remaining_q3", "soil_carried_q3", "soil_deposited_q3", "geometry_revision",
                 "excavated_q3", "filled_q3")
        require(tuple(current[k] for k in names) == values and values[0] == sum(values[1:4]), "soil ledger differs at cut")
        require(all(route[key] == str(current[key]) for key in ("cursor", "sim_ms", "geometry_revision")), "unbound route cut")
        actor = int(route["actor"])
        require(within(tuple(float(route[f"actor_{a}_m"]) for a in AXES), self.positions[actor]), "route actor differs")
        points = [tuple(map(int, point.split(":"))) for point in route["points_q"].split(";") if point]
        if route["found"] == "1":
            require(points[0] == self.quantize(self.positions[actor]) and
                    points[-1] == self.quantize(tuple(float(route[f"target_{a}_m"]) for a in AXES)), "wrong route endpoints")
            half = int(route["half_extent_q"])
            for a, b in zip(points, points[1:]):
                require(sum(abs(x - y) for x, y in zip(a, b, strict=True)) == 1 and self.grid.swept(a, b, half),
                        "public route crosses independently reconstructed soil")
        else:
            require(not points, "absent route retains points")
        self.tables.add("geometry_timeline", self.run, cut=current["cut"], cursor=current["cursor"], sim_ms=current["sim_ms"],
                        **dict(zip(names, values, strict=True)), connected_void_q3=self.grid.connected(nest),
                        all_void_q3=len(self.grid.void), carried_by_dead_q3=sum(p.remaining for p in self.parcels.values()
                                                                              if p.carrier in self.dead),
                        route_found=route["found"] or "UNOBSERVED", route_budget_exhausted=route["budget_exhausted"] or "UNOBSERVED",
                        route_steps=max(0, len(points) - 1), focal=actor, food_in_crops_ug=sum(world_ledger[f"colony_crop_{x}_ug"]
                                                                          for x in ("carb", "protein", "water", "other")))

    def finish(self, dest):
        require(not self.edit_rows, "geometry edit did not have a canonical fact")
        actual = sequence(rows(dest / "parcels.csv"), lambda p: int(p["parcel"]))
        require(set(actual) == set(self.parcels), "parcel set differs")
        for key, parcel in self.parcels.items():
            entry = actual[key]
            fields = ("origin_edit", "initial_q3", "remaining_q3", "carrier", "state")
            require(tuple(int(entry[k]) for k in fields) == (parcel.origin_edit, parcel.initial, parcel.remaining, parcel.carrier, parcel.state)
                    and within(tuple(float(entry[f"{a}_m"]) for a in AXES), parcel.position), "parcel authority differs")
        require(set(self.schedules) == set(self.resolutions), "unresolved host intervention")
        return dict(digs=self.totals["SoilExcavated"], fills=self.totals["SoilFilled"], drops=self.totals["SoilDropped"],
                    pickups=self.totals["SoilPickedUp"], decisions=self.totals["decisions"], excavated_q3=self.excavated,
                    filled_q3=self.filled, excavated_dry_ug=self.excavated * self.dry,
                    excavated_water_ug=self.excavated * self.water, dropped_q3=self.totals["SoilDropped_q3"],
                    fixture_dig_cost_nj=self.excavated * self.dig_energy,
                    loaded_moves=self.loaded_moves, loaded_distance_m=round(self.distance_m, 12),
                    soil_rejections=sum(n for key, n in self.totals.items() if key.startswith("rejected_")),
                    final_carried_q3=sum(p.remaining for p in self.parcels.values() if p.state == 0))
