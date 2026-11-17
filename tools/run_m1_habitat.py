"""Run the frozen M1 habitat matrix and stream representative native witnesses."""

import argparse
from collections import Counter
from contextlib import closing, nullcontext
from ctypes import byref
from hashlib import sha256
from itertools import combinations, product
import json
from math import dist
import os
from pathlib import Path
import platform
from tempfile import TemporaryDirectory
from time import perf_counter
from zipfile import ZIP_DEFLATED, ZipFile

from op0 import DAY
from op0.archive import file_hash, json_bytes
from op0.codec import KINDS, STAGES, U32, checkpoint, decode_fact
from op0.live import NativeCore, ROOT, core_path


MIB = 1 << 20
WALL_BUDGET = 120
WITNESS_BUDGET = 24 * MIB
CUTS = {90, 150, 240}
PHYSICS36_BASE = "36bbf99bd0cd28c992a6fa830dccfb9ff9e419a8"


def cpu_seconds(pid):
    if os.name == "nt":
        from tools import s6_2_windows_telemetry as win
        handle = win.open_process(0x1000, False, pid)
        if not handle:
            return None
        try:
            ticks = [win.W.FILETIME() for _ in range(4)]
            if not win.get_process_times(handle, *(byref(t) for t in ticks)):
                return None
            return round(sum(map(win.filetime, ticks[2:])) / 10_000_000, 6)
        finally:
            win.close(handle)
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
    except OSError:
        return None
    return (int(fields[11]) + int(fields[12])) / os.sysconf("SC_CLK_TCK")


def cases(series):
    if series == "archive36":
        for seed, trail in product(range(1, 7), (60, 1955)):
            yield f"open-{seed}-{trail}", "NEW_HABITAT 201 %d 250 80 open %d" % (seed, trail), 90, False
        for temperature, humidity, entrance in ((250, 80, "plugged"), (250, 80, "blocked"),
                                                (225, 80, "open"), (270, 60, "open")):
            yield (f"control-{entrance}-{temperature}-{humidity}",
                   f"NEW_HABITAT 201 2 {temperature} {humidity} {entrance} 1955", 90, False)
    elif series == "paired":
        for serial, (seed, trail, entrance, policy) in enumerate(
                product((1, 2, 3, 6), (60, 1955), ("open", "blocked"), ("reference", "reachable")), 1001):
            yield (f"{seed}-{trail}-{entrance}-{policy}",
                   f"NEW_OBSERVATORY {serial} {seed} 250 80 {entrance} {trail} {policy} finite", 150, False)
    elif series == "extended":
        for serial, (seed, entrance, supply, publish) in enumerate(((1, "open", "finite", False),
                (2, "open", "finite", False), (2, "plugged", "finite", True), (2, "open", "absent", True)), 2001):
            yield (f"{seed}-{entrance}-{supply}",
                   f"NEW_OBSERVATORY {serial} {seed} 250 80 {entrance} 1955 reference {supply}", 240, publish)
    else:
        yield "2-plugged-finite-day90", "NEW_OBSERVATORY 2003 2 250 80 plugged 1955 reference finite", 90, True


class Observation:
    def __init__(self, initial):
        self.cursor = 0
        self.hash = sha256()
        self.counts = Counter()
        self.deaths = Counter()
        self.stages = {}
        self.worker_ids = set()
        self.positions = {}
        self.queen = next(int(a["id"]) for a in initial["ants"].values() if a["caste"] == 1)
        self.queen_death = None
        self.eclosed_ms = None
        self.deliveries = [0] * 4
        self.last_delivery = None
        self.responders, self.returning_responders = set(), set()
        self.pantry = [0] * 4
        self.empty_ms = Counter()
        self.pantry_at = 0
        self.move_seconds = Counter()
        self.distance = Counter()
        self.max_close_pairs = 0
        self.supply_days_without_delivery = 0

    def move_clock(self, time):
        if self.eclosed_ms is not None:
            elapsed = time - max(self.pantry_at, self.eclosed_ms)
            for index, name in ((0, "carbohydrate"), (2, "water")):
                if not self.pantry[index]:
                    self.empty_ms[name] += elapsed
        self.pantry_at = time

    def consume(self, event):
        kind = KINDS[event.kind]
        if kind in {"AntSeeded", "AntBorn", "StageChanged"}:
            self.stages[event.actor] = event.stage
            self.positions[event.actor] = event.position
            if kind == "AntBorn":
                self.counts["births"] += 1
            elif kind == "StageChanged":
                self.counts[STAGES[event.stage]] += 1
                if event.stage == 3:
                    if self.eclosed_ms is None:
                        self.eclosed_ms = event.time
                        self.pantry_at = event.time
                    self.worker_ids.add(event.actor)
        elif kind == "AntDied":
            self.deaths[f"{STAGES[self.stages[event.actor]]}/{event.payload}"] += 1
            self.stages[event.actor] = event.stage
            if event.actor == self.queen:
                self.queen_death = dict(event=str(event.id), time_ms=event.time, cause_code=event.payload)
        elif kind in {"Moved", "BroodMoved"}:
            before = self.positions.get(event.actor)
            if kind == "Moved" and before is not None and event.actor in self.worker_ids:
                self.distance[event.actor] += dist(before, event.position)
                if event.aux:
                    self.move_seconds[event.actor] += (event.aux >> 32) / 1000
                self.counts["worker_moves"] += 1
                self.counts["worker_surface_entries"] += before[1] < 0 <= event.position[1]
            self.positions[event.actor] = event.position
        elif kind in {"FoodCollected", "FoodDelivered", "NestIngested", "ProteinRecycled", "FoundressNestMeal"}:
            self.counts[kind] += 1
            if kind == "FoodDelivered":
                self.last_delivery = event.time
                if event.mass[2] and event.mass[2] == sum(event.mass):
                    self.counts["water_only_deliveries"] += 1
                if event.actor in self.responders and event.mass[0]:
                    self.returning_responders.add(event.actor)
                for index, amount in enumerate(event.mass):
                    self.deliveries[index] += amount
            if kind != "FoodCollected":
                self.move_clock(event.time)
                change = 1 if kind in {"FoodDelivered", "ProteinRecycled"} else -1
                self.pantry = [value + change * amount for value, amount in zip(self.pantry, event.mass)]
        elif kind in {"RecruitmentCue", "RecruitmentObserved", "RecruitmentActivated", "SoilExcavated", "SoilDropped",
                      "FoundressWaterIngested", "NutritionTransferred", "FoundingRation"}:
            self.counts[kind] += 1
            if kind == "RecruitmentActivated":
                self.responders.add(event.actor)

    def read_to(self, core, cursor, stream):
        # Canonical records arrive in exact native order and are hashed before projection.
        while self.cursor < cursor:
            page = core.call(f"FACTS_AFTER {self.cursor}")
            if not page:
                raise ValueError("Missing native history page")
            self.hash.update(page)
            if stream is not None:
                stream.write(page)
            at = 0
            while at < len(page):
                size, = U32.unpack_from(page, at)
                at += U32.size
                _, event = decode_fact(page, at)
                self.cursor += 1
                if event.id != self.cursor or self.cursor > cursor:
                    raise ValueError("Unexpected native journal cursor")
                self.consume(event)
                at += size

    def sample(self, cut):
        self.move_clock(cut["time_ms"])
        stock = tuple(sum(c["stock_ug"][i] for c in cut["colonies"].values()) for i in range(4))
        if tuple(self.pantry) != stock:
            raise ValueError("Committed pantry ledger disagrees with native cut")
        workers = [a["position_m"] for a in cut["ants"].values() if a["stage"] == 3 and a["caste"] == 0]
        width = 2 * cut["geometry"]["body_half_q"] * cut["geometry"]["quantum_m"]
        self.max_close_pairs = max(self.max_close_pairs, sum(dist(a, b) < width for a, b in combinations(workers, 2)))
        if (workers and cut["time_ms"] >= DAY and
            any(sum(s["stock_ug"]) and s["position_m"][1] >= 0 for s in cut["sources"].values()) and
                (self.last_delivery is None or self.last_delivery <= cut["time_ms"] - DAY)):
            self.supply_days_without_delivery += 1

    def summary(self, core, cut, raw, day, now):
        live = Counter("Worker" if ant["stage"] == 3 and ant["caste"] == 0 else STAGES[ant["stage"]]
                       for ant in cut["ants"].values() if ant["stage"] != 4)
        geometry = cut["geometry"]
        return dict(day=day, time_ms=cut["time_ms"], frame_sha256=sha256(raw).hexdigest(), canonical_sha256=self.hash.hexdigest(),
                    cursor=self.cursor, queen_alive=cut["ants"][self.queen]["stage"] != 4, queen_death=self.queen_death,
                    first_eclosed_ms=self.eclosed_ms, live=dict(live), counts=dict(self.counts), deaths_by_stage_and_code=dict(self.deaths),
                    delivered_ug=self.deliveries.copy(), recruited_workers_delivering=len(self.returning_responders),
                    pantry_ug=self.pantry.copy(), empty_pantry_after_first_worker_ms=dict(self.empty_ms),
                    last_delivery_ms=self.last_delivery, outside_supply_days_without_delivery=self.supply_days_without_delivery,
                    worker_recorded_motion_s=round(sum(self.move_seconds.values()), 3),
                    worker_distance_m=round(sum(self.distance.values()), 6),
                    maximum_close_worker_pairs_at_daily_cuts=self.max_close_pairs,
                    soil_edits=len(cut["edits"]), excavation_mm3=round(sum(e["volume_q3"] for e in cut["edits"] if e["kind"] == 0)
                        * (1000 * geometry["quantum_m"]) ** 3, 9),
                    history_storage=list(map(int, core.call("HISTORY_STORAGE").split())),
                    memory_bytes=list(map(int, core.call("MEMORY").split())), wall_seconds=round(now, 6),
                    native_process_cpu_seconds=cpu_seconds(core.process.pid))


def attest(raw):
    return {"sha256": sha256(raw).hexdigest(), "bytes": len(raw)}


def run_case(core, name, command, horizon, archive_path, identity):
    started = perf_counter()
    current = core.call(command)
    initial_raw = core.call("INITIAL")
    initial = checkpoint(initial_raw)
    inputs = dict(case=name, command=command, horizon_days=horizon, world_id=initial["world"], seed=initial["seed"],
                  schema=initial["schema"], physics=initial["physics"], initial=attest(initial_raw),
                  parameters=list(core.call("HABITAT_PARAMETERS").decode().split()))
    observation = Observation(initial)
    sections = []
    status, reason, day = "COMPLETE", None, 0
    stage_path = None if archive_path is None else archive_path.with_suffix(".partial")
    with ZipFile(stage_path, "x", compression=ZIP_DEFLATED, compresslevel=6) if stage_path else nullcontext() as archive:
        with archive.open("facts.bin", "w", force_zip64=True) if archive else nullcontext() as stream:
            cut = checkpoint(current, verify_hash=False)
            observation.read_to(core, cut["cursor"], stream)
            for target in range(1, horizon + 1):
                if perf_counter() - started >= WALL_BUDGET:
                    status, reason = "STOPPED", "Daily cut reached after wall budget"
                    break
                try:
                    raw = core.call(f"ADVANCE {target * DAY}")
                except ValueError as error:
                    status, reason = "STOPPED", str(error)
                    break
                day, current = target, raw
                cut = checkpoint(current, verify_hash=False)
                observation.read_to(core, cut["cursor"], stream)
                observation.sample(cut)
                if target in CUTS:
                    core.call("CHECK_LEDGERS")
                    sections.append(observation.summary(core, cut, current, day, perf_counter() - started))
                if stage_path and stage_path.stat().st_size > WITNESS_BUDGET:
                    status, reason = "STOPPED", "Witness disk budget exceeded"
                    break
        if not sections or sections[-1]["day"] != day:
            sections.append(observation.summary(core, cut, current, day, perf_counter() - started))
        result = dict(identity=identity, inputs=inputs, status=status, stop_reason=reason, last_confirmed_day=day, cuts=sections)
        if archive and status == "COMPLETE":
            native_input = command.split()
            case = json_bytes(dict(case=name, arm="micro-m0-founding-habitat", population="Borisovka", layout="shaft",
                                   source=native_input[-1], parameters=inputs, physics=inputs["physics"],
                                   externally_seeded_workers=0, status="ENGINEERING_ONLY"))
            artifacts = {"facts.bin": {"bytes": archive.getinfo("facts.bin").file_size,
                                         "sha256": observation.hash.hexdigest()}}
            for member, data in (("initial.chk", initial_raw), ("final.frame", current), ("case.json", case)):
                archive.writestr(member, data)
                artifacts[member] = attest(data)
            archive.writestr("receipt.json", json_bytes(dict(status=status, identity=identity | inputs, artifacts=artifacts)))
    if archive_path:
        if status == "COMPLETE" and stage_path.stat().st_size <= WITNESS_BUDGET:
            stage_path.rename(archive_path)
            result["witness"] = dict(name=archive_path.name, sha256=file_hash(archive_path), bytes=archive_path.stat().st_size)
        else:
            result.update(status="STOPPED", stop_reason=reason or "Witness disk budget exceeded")
            stage_path.unlink()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("series", choices=("archive36", "paired", "extended", "witness90"))
    parser.add_argument("--core", type=Path, default=core_path())
    parser.add_argument("--output", type=Path)
    parser.add_argument("--case", action="append", default=[])
    args = parser.parse_args()
    out = ROOT / "out"
    out.mkdir(exist_ok=True)
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
    binary = args.core.resolve()
    identity = dict(system=platform.system(), machine=platform.machine(), reviewed_reference=PHYSICS36_BASE,
                    binary_sha256=file_hash(binary), native_protocol=None)
    with TemporaryDirectory(prefix="m1-run-", dir=out) as work:
        for name, command, horizon, witness in cases(args.series):
            if args.case and name not in args.case:
                continue
            with closing(NativeCore(binary, work)) as core:
                protocol = core.call("HELLO").decode()
                path = args.output / f"m1-{name}.zip" if witness and args.output else None
                result = run_case(core, name, command, horizon, path, identity | {"native_protocol": protocol})
                print(json.dumps(result, allow_nan=False, separators=(",", ":")), flush=True)


if __name__ == "__main__":
    main()
