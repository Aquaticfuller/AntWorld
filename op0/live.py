"""Host the native MicroWorld clock and its explicit continuation and archive saves."""

from collections import OrderedDict
from contextlib import closing
import os
from math import isfinite
from pathlib import Path
import re
from secrets import randbits
from shutil import copyfile
import sqlite3
import stat
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Event, RLock, Thread
from time import monotonic_ns
from uuid import UUID, uuid4

from .archive import SQLITE_ID, key
from .chronicle import Chronicle, LANDMARKS
from .codec import (ACTS, CASTES, DEATHS, FACETS, HIGHLIGHTS, KINDS, MICROWORLD_VERSIONS, PROGRAMS, STAGES, U32, Reader,
                    checkpoint, checkpoint_header, decode_fact, label, require, world_id)
from .geometry import AXES, focused_window, nest_volume, terrain_view
from .query import HOUR, integer


ROOT = Path(__file__).resolve().parent.parent
RATES = (1, 10, 60, 600, 3600, 86400)
HABITAT_MILESTONES = {"water", "recruitment", "patrol", "entrance-contact"}
BROOD_MILESTONES = {"brood-moved", "brood-cleaned"}
FOUNDER_MILESTONES = {"queen-meal", "queen-uptake"}
MILESTONES = {"egg", "hatch", "worker", "exit", "delivery", "wall-delivery", "excavation", "queen-gift", *HABITAT_MILESTONES,
              *BROOD_MILESTONES, *FOUNDER_MILESTONES}
NEW_COLONY_TIMINGS = {"standard": "", "shorter": " 900000 3600000"}
HABITAT_TEMPERATURES = (225, 250, 270)
HABITAT_HUMIDITIES = (60, 80, 90)
OBSERVATORY_PRESETS = {"open": ("open", "finite"), "plugged": ("plugged", "finite"), "absent": ("open", "absent")}
SAVE_SUFFIXES = {"snapshot": ".awstate", "archive": ".sqlite"}
FRAME_LIMIT = 128 * 1024 * 1024
ECOLOGY_WORLD_TAGS = {651: "water-fed", 652: "no-external-water"}
NURSERY_WORLD_TAGS = {649, 650, *ECOLOGY_WORLD_TAGS}  # Matches the native nursery fixtures.
NURSERY_TREATMENTS = {"reference": 0, "traffic": 1, "provisioned": 2, "ecology": 5, "ecology-dry": 6}
LIVE_GROUPS = {name: {KINDS[kind] for kind in kinds} for name, kinds in FACETS.items()}
LIVE_GROUPS["highlights"] = {KINDS[kind] for kind in HIGHLIGHTS}


def core_path():
    name = "antworld_m0_live.exe" if os.name == "nt" else "antworld_m0_live"
    installed = ROOT / "out/m0-live-bin" / name
    paths = (installed.with_stem("antworld_m0_live_v21"), installed.with_stem("antworld_m0_live_v20"), installed.with_stem("antworld_m0_live_v19"),
             installed.with_stem("antworld_m0_live_v18"), installed.with_stem("antworld_m0_live_v17"),
             installed.with_stem("antworld_m0_live_v16"), installed.with_stem("antworld_m0_live_v15"),
             installed.with_stem("antworld_m0_live_v14"), installed.with_stem("antworld_m0_live_v13"),
             installed.with_stem("antworld_m0_live_v12"),
             installed.with_stem("antworld_m0_live_v11"),
             installed.with_stem("antworld_m0_live_v10"),
             installed.with_stem("antworld_m0_live_v9"),
             installed.with_stem("antworld_m0_live_v8"), installed.with_stem("antworld_m0_live_v7"),
             installed.with_stem("antworld_m0_live_v6"), ROOT / "build/m0-live" / name,
             ROOT / "build/m0-live/Release" / name, installed.with_stem("antworld_m0_live_v5"))
    return next((path for path in paths if path.is_file()), paths[0])


def is_nursery(frame):
    return frame is not None and UUID(frame["world"]).int >> 64 in NURSERY_WORLD_TAGS


class NativeCore:
    def __init__(self, binary, workdir):
        self.process = subprocess.Popen([str(binary)], cwd=workdir, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            version = self.call("HELLO")
            protocols = tuple(f"antworld.m0.live.v{i}".encode("ascii") for i in range(4, 19))
            require(version in protocols,
                    "Rebuild the live Core for this viewer version.")
            generation = 4 + protocols.index(version)
            self.worker_motor = generation >= 5
            self.nursery = generation >= 6
            self.provisioned_nursery = generation >= 7
            self.local_ecology = generation >= 8
            self.founding_habitat = generation >= 9
            self.observatory = generation >= 10
            self.next_milestone = generation >= 11
            self.single_nest = generation >= 12
            self.anatomical = generation >= 13
            self.mouth_access = generation >= 14
            self.adult_offers = generation >= 15
            self.wall_handoff = generation >= 16
            self.anatomical_handoff = generation >= 17
            self.familiar_return = generation >= 18
        except Exception:
            self.close()
            raise

    def call(self, command):
        pipe = self.process
        pipe.stdin.write(command.encode("ascii") + b"\n")
        pipe.stdin.flush()
        header = pipe.stdout.readline(128).split()
        require(len(header) == 2 and header[0] in (b"OK", b"ERR") and header[1].isdigit(),
                "The live Core did not return a valid reply")
        size = int(header[1])
        require(size <= FRAME_LIMIT, "Live Core reply exceeds the observation limit")
        data = pipe.stdout.read(size)
        require(len(data) == size, "The live Core closed during its reply")
        if header[0] == b"ERR":
            raise ValueError(data.decode("utf-8", errors="replace"))
        return data

    def close(self):
        try:
            try:
                self.process.stdin.close()
            except BrokenPipeError:
                pass
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        finally:
            self.process.stdout.close()


def founding_balance(core, frame, identifier):
    raw = core.call(f"FOUNDING_BALANCE {identifier}")
    if not raw:
        return None
    values = list(map(int, raw.split()))
    require(len(values) == 9 and values[0] == frame["time_ms"] and min(values) >= 0,
            "Invalid founding physiology observation")
    time, energy, water, lipid, protein, *crop = values
    return dict(time_ms=time, energy_nj=energy, water_ug=water, lipid_ug=lipid, mobile_protein_ug=protein, crop_ug=crop)


def live_bodies(data, frame):
    bodies = {}
    for row in data.splitlines():
        ant, count, held, act, target, began, *columns = row.decode("ascii").split()
        count, ant_id = int(count), int(ant)
        act, began = int(act), int(began)
        values = list(map(float, columns))
        require(ant_id in frame["ants"] and ant not in bodies and count in (1, 3) and
                len(values) == 12 + 4 * count and all(map(isfinite, values)) and
                (held == "0" or int(held) in frame["ants"]) and (target == "0" or int(target) in frame["ants"]) and
                0 <= act < len(ACTS) and 0 <= began <= frame["time_ms"], "Invalid native body observation")
        bodies[ant] = dict(forward=values[:3], up=values[3:6], mouth_m=values[6:9], abdomen_tip_m=values[9:12],
                           segments=[values[i:i+4] for i in range(12, len(values), 4)],
                           held_id=None if held == "0" else held,
                           care=dict(act=ACTS[act], target=target, began_ms=began) if act else None)
    return bodies


def read_live_events(data, frame, *, contiguous=False, after=None):
    offset, previous = 0, after
    events = []
    expected = UUID(frame["world"]).int
    while offset < len(data):
        size = U32.unpack_from(data, offset)[0]
        start = offset + U32.size
        end = start + size
        require(end <= len(data), "Truncated live event")
        identity, fact = decode_fact(data[start:end])
        require(expected == ((identity[0] << 64) | identity[1]) and fact.time <= frame["time_ms"] and
                0 < fact.id <= frame["cursor"] and (previous is None or
                (fact.id == previous + 1 if contiguous or after is not None else fact.id > previous)),
                "Live event does not belong to the published cut")
        events.append(fact.packet())
        previous, offset = fact.id, end
    if contiguous:
        require(previous == (frame["cursor"] or None), "Live events do not reach the published cut")
    return events


def live_motion(data, frame):
    result = {}
    now = frame["time_ms"]
    for line in data.splitlines():
        fields = line.split()
        require(len(fields)==12, "Malformed native movement lease")
        actor,begin,travel,end,heading,direction = map(int,fields[:6])
        points=tuple(map(float,fields[6:]))
        require(actor in frame["ants"] and actor not in result and begin<=now<end and begin<=travel<end and
                0<=heading<=10 and 1<=direction<=10 and all(map(isfinite,points)) and
                points[:3]==frame["ants"][actor]["position_m"] and points[:3]!=points[3:],
                "Movement lease disagrees with the native frame")
        progress = min(1,max(0,(now-travel)/(end-travel)))
        result[actor] = dict(from_m=points[:3], to_m=points[3:], begins_ms=begin, translates_ms=travel, ends_ms=end,
                             heading=heading, target_heading=direction, progress=progress,
                             evidence="CORE_MOTION_LEASE")
    return result


def regular_file(path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if stat.S_ISREG(info.st_mode) and not getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
        return info
    return None


def stable_save(path):
    return all(not side.exists() or (regular_file(side) and side.stat().st_size == 0)
               for side in (path.with_name(path.name + "-wal"), path.with_name(path.name + "-journal")))


def discard_stage(path):
    for suffix in ("", "-wal", "-shm", "-journal"):
        path.with_name(path.name + suffix).unlink(missing_ok=True)


def save_details(path):
    info = regular_file(path)
    require(info is not None and stable_save(path), "Open a finished MicroWorld save file")
    if path.suffix.lower() == SAVE_SUFFIXES["snapshot"]:
        with path.open("rb") as source:
            header = Reader(source.read(140))
            framed, snapshot, floor, tip, outer, _, _, _, hi, lo, _, stamp, _ = checkpoint_header(header)
        require(snapshot and not framed and outer in MICROWORLD_VERSIONS and tip < 1 << 53,
                "Expected a MicroWorld continuation snapshot")
        return dict(name=path.stem, world_id=world_id(hi, lo), time_ms=stamp, facts=tip, history_floor=floor,
                    size_bytes=info.st_size, modified_ms=info.st_mtime_ns // 1_000_000, mode="snapshot", loadable=True)
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        require(db.execute("PRAGMA application_id").fetchone() == (SQLITE_ID,) and
                db.execute("PRAGMA user_version").fetchone() == (2,), "Expected an AntWorld SQLite save")
        rows = db.execute("SELECT w.world,w.time_ms,w.cursor,substr(g.checkpoint,1,24) FROM worlds w "
                          "JOIN generations g ON g.world=w.world AND g.generation=w.generation LIMIT 2").fetchall()
    require(len(rows) == 1, "Expected a single MicroWorld colony")
    world, stamp, cursor, header = rows[0]
    require(type(stamp) is int and 0 <= stamp < 1 << 53 and isinstance(header, bytes) and len(header) == 24 and
            header[:16] == b"AWSTATE1AWCKPTM\0" and
            (U32.unpack_from(header, 16)[0], U32.unpack_from(header, 20)[0]) in MICROWORLD_VERSIONS,
            "Expected a MicroWorld checkpoint")
    require(isinstance(world, str) and str(UUID(world)) == world and isinstance(cursor, str) and key(cursor) < 1 << 53,
            "Invalid save identity")
    return dict(name=path.stem, world_id=world, time_ms=stamp, facts=key(cursor), size_bytes=info.st_size,
                modified_ms=info.st_mtime_ns // 1_000_000, mode="archive", loadable=True)


def open_folder(path):
    if os.name == "nt":
        os.startfile(str(path), "explore")
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(path)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class LiveSession:
    def __init__(self, binary, saves, *, clock=monotonic_ns):
        self.binary = binary.resolve()
        self.saves = saves.resolve()
        self.clock = clock
        self.lock = RLock()
        self.stopping = Event()
        self.thread = None
        self.worker = None
        self.workdir = None
        self.loaded_copy = None
        self.frame = None
        self.recent = []
        self.actions = []
        self.sections = OrderedDict()
        self.volume = None
        self.chronicle = Chronicle()
        self.history_floor = 0
        self.epoch = 0
        self.running = False
        self.rate = 1
        self.fast_forward = None
        self.anchor_ns = self.anchor_ms = 0
        self.saved = None
        self.climate = None
        self.error = None

    def __enter__(self):
        self.thread = Thread(target=self.run_clock, name="m0-core-clock", daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.stopping.set()
        self.thread.join()
        try:
            if self.worker:
                self.worker.close()
        finally:
            if self.workdir:
                self.workdir.cleanup()

    def core(self):
        require(self.binary.is_file(), "Build the live Core before creating or loading a colony.")
        if self.worker is None:
            self.saves.mkdir(parents=True, exist_ok=True)
            self.workdir = TemporaryDirectory(prefix=".m0-session-", dir=self.saves)
            try:
                self.worker = NativeCore(self.binary, self.workdir.name)
            except Exception:
                self.workdir.cleanup()
                self.workdir = None
                raise
        return self.worker

    def publish(self, raw, reset=False):
        # The pipe is private to this process. On-disk stores are validated by Store::load.
        frame = checkpoint(raw, verify_hash=False)
        if reset or not self.frame or self.frame["cursor"] != frame["cursor"]:
            cursor = self.frame["cursor"] if self.frame and not reset else 0
            self.recent = read_live_events(self.worker.call("RECENT"), frame, contiguous=True)
            actions = read_live_events(self.worker.call(f"RECENT_ACTIONS {cursor}"), frame)
            self.actions = (([] if reset else self.actions) + actions)[-12:]
        self.frame = frame

    def reanchor(self):
        self.anchor_ns, self.anchor_ms = self.clock(), self.frame["time_ms"]

    def install(self, raw, *, running, saved=None, copy=None):
        if self.loaded_copy:
            discard_stage(self.loaded_copy)
        self.loaded_copy = copy
        self.publish(raw, reset=True)
        self.climate = None
        if self.frame["flags"].get("founding_habitat"):
            fields = self.worker.call("HABITAT_PARAMETERS").split()
            require(len(fields) == 8, "Invalid native climate parameters")
            temperature, humidity = map(float, fields[:2])
            egg, larva, pupa, larva_loss, queen_loss, worker_loss = map(int, fields[2:])
            require(isfinite(temperature) and 0 <= humidity <= 1 and
                    min(egg, larva, pupa, larva_loss, queen_loss) > 0 and worker_loss >= 0, "Invalid native climate parameters")
            self.climate = dict(temperature_c=temperature, humidity_percent=round(humidity * 100),
                                egg_ms=egg, larva_ms=larva, pupa_ms=pupa,
                                larva_loss_ug_day=larva_loss, queen_loss_ug_day=queen_loss,
                                worker_loss_ug_day=worker_loss)
        self.epoch += 1
        self.sections.clear()
        self.volume = None
        self.chronicle = Chronicle()
        self.history_floor = saved.get("history_floor", 0) if saved else 0
        self.chronicle.cursor = self.history_floor
        self.running, self.rate, self.saved, self.error = running, 1, saved, None
        self.fast_forward = None
        self.reanchor()

    def seeking(self):
        return self.fast_forward is not None and self.fast_forward["state"] == "seeking"

    def milestone_event(self, raw):
        identity, event = decode_fact(raw)
        require(UUID(self.frame["world"]).int == ((identity[0] << 64) | identity[1]) and
                event.id <= self.frame["cursor"] and event.time <= self.frame["time_ms"],
                "Live milestone does not belong to the published cut")
        packet = event.packet()
        if packet["kind"] == "SoilExcavated":
            packet["geometry_edits"] = [edit | {"actor": str(edit["actor"])}
                                        for edit in self.frame["edits"] if edit["event"] == event.id]
        return packet

    def start_seek(self, target, occurrence):
        require(isinstance(target, str) and target in MILESTONES, "Unknown live milestone")
        require(target not in BROOD_MILESTONES or self.worker.single_nest, "Build the updated Core to seek brood actions.")
        habitat = (self.frame["flags"] or {}).get("founding_habitat")
        require(target not in HABITAT_MILESTONES or habitat, "Unknown live milestone")
        require(target not in FOUNDER_MILESTONES or (self.worker.mouth_access and habitat),
                "Founder meal milestones need the updated Core and a founding habitat.")
        require(target != "queen-gift" or (self.worker.adult_offers and habitat),
                "Queen transfer milestones need the updated Core and a founding habitat.")
        require(target != "wall-delivery" or (self.worker.wall_handoff and habitat and habitat.get("wall_handoff")),
                "Wall deliveries require a wall-handoff nest.")
        require(not self.seeking(), "Cancel the current fast-forward first.")
        require(occurrence in ("first", "next"), "Choose the first or next event")
        next_event = occurrence == "next"
        if next_event:
            require(self.worker.next_milestone, "Build the updated Core to seek the next event.")
            previous = self.fast_forward or {}
            event = previous.get("event")
            after = 0
            if (event and previous["state"] == "reached" and previous["target"] == target and
                    event["time_ms"] == self.frame["time_ms"]):
                after = event["id"]
            raw = self.worker.call(f"FIND_NEXT_MILESTONE {target} {after}")
        else:
            require(not self.history_floor, "Earlier events are unavailable in this compact save. Search for the next event.")
            raw = self.worker.call(f"FIND_MILESTONE {target}")
        event = self.milestone_event(raw) if raw else None
        self.fast_forward = dict(target=target, state="seeking", event=None)
        if next_event:
            self.fast_forward["occurrence"] = occurrence
        if event is None:
            self.running, self.rate, self.error = True, RATES[-1], None
            self.reanchor()
        elif next_event:
            self.stop_seek("reached", event)
            self.error = None
        else:
            self.fast_forward.update(state="already", event=event)

    def stop_seek(self, state, event=None):
        self.fast_forward = self.fast_forward | dict(state=state, event=event)
        self.running, self.rate = False, 1

    def advance(self):
        if not self.running:
            return
        stamp = self.frame["time_ms"]
        desired = self.anchor_ms + (self.clock() - self.anchor_ns) * self.rate // 1_000_000
        # Bound one Core call so a pause or save can still take the controller lock.
        # Event search advances to the next committed event at the Core's pace.
        # The native request also caps work at 256 indivisible timestamps.
        target = stamp + 12 * HOUR if self.seeking() else min(desired, stamp + 12 * HOUR)
        if target <= stamp:
            return
        if not self.seeking():
            self.publish(self.worker.call(f"ADVANCE {target}"))
            return
        reply = self.worker.call(f"ADVANCE_UNTIL {target} {self.fast_forward['target']}")
        self.publish(self.worker.call("FRAME"))
        if reply == b"exhausted":
            self.stop_seek("exhausted")
        elif reply:
            event = self.milestone_event(reply)
            require(event["time_ms"] == self.frame["time_ms"], "The Core did not stop at the live milestone")
            self.stop_seek("reached", event)

    def run_clock(self):
        while not self.stopping.wait(.02 if self.seeking() else .05 if is_nursery(self.frame) and self.rate == 1 else .10):
            with self.lock:
                try:
                    self.advance()
                except Exception as err:
                    if self.seeking():
                        self.stop_seek("cancelled")
                    self.running, self.error = False, str(err)
                    # A Core exception can occur after earlier cuts have committed.
                    try:
                        self.publish(self.worker.call("FRAME"), reset=True)
                    except (OSError, ValueError):
                        pass

    def status(self):
        frame = self.frame
        dirty = bool(frame and (not self.saved or self.saved["time_ms"] != frame["time_ms"] or
                                self.saved["facts"] != frame["cursor"]))
        return dict(enabled=True, core_available=self.binary.is_file(), time_ms=frame["time_ms"] if frame else None,
                    nursery_available=self.binary.is_file() and (self.worker is None or self.worker.nursery),
                    ecology_available=self.binary.is_file() and (self.worker is None or self.worker.local_ecology),
                    habitat_available=self.binary.is_file() and (self.worker is None or self.worker.founding_habitat),
                    observatory_available=self.binary.is_file() and (self.worker is None or self.worker.observatory),
                    single_nest_available=self.binary.is_file() and (self.worker is None or self.worker.single_nest),
                    founder_meals_available=bool(self.worker and self.worker.mouth_access),
                    queen_gifts_available=bool(self.worker and self.worker.adult_offers),
                    history_floor=self.history_floor,
                    next_milestone_available=bool(self.worker and self.worker.next_milestone),
                    world_id=frame["world"] if frame else None, epoch=self.epoch, running=self.running, rate=self.rate,
                    fast_forward=self.fast_forward, saved_name=self.saved["name"] if self.saved else None,
                    dirty=dirty, error=self.error)

    def advance_chronicle(self, frame):
        for _ in range(2):
            after = self.chronicle.cursor
            if after >= frame["cursor"]:
                break
            events = read_live_events(self.worker.call(f"FACTS_AFTER {after}"), frame, after=after)
            require(events, "Missing canonical chronicle page")
            for event in events:
                self.chronicle.accept(event, frame)

    def exact_fact(self, frame, identifier):
        require(identifier > self.history_floor, "This event predates the saved history window")
        command = f"FACTS_AFTER {identifier-1}" + (" 1" if self.worker.observatory else "")
        events = read_live_events(self.worker.call(command), frame, after=identifier-1)
        require(events, "The selected fact is not present in the published cut")
        event = events[0]
        if event["kind"] in {"SoilExcavated", "SoilDropped"}:
            event["geometry_edits"] = [edit | {field: str(edit[field]) for field in ("event", "actor", "source", "parcel")}
                                       for edit in frame["edits"] if edit["event"] == identifier]
        return event

    def read(self, resource, options):
        with self.lock:
            if resource == "status":
                return self.status()
            if resource == "saves":
                return self.list_saves()
            if resource in {"volume", "chronicle", "life", "fact"}:
                frame = self.frame
                require(frame is not None and options.get("epoch", str(self.epoch)) == str(self.epoch),
                        "This observation belongs to a different live colony")
                if resource == "volume":
                    revision = len(frame["edits"])
                    if self.volume is None or self.volume["revision"] != revision:
                        focus = next(iter(frame["colonies"].values()))["position_m"]
                        self.volume = nest_volume(frame["geometry"], frame["edits"], focus,
                                                  radius=44 if frame["physics"] >= 39 else 32)
                    return self.volume | {"epoch": self.epoch, "world_id": frame["world"]}
                if resource == "fact":
                    identifier = integer(options, "id", 0, 1, frame["cursor"])
                    return self.exact_fact(frame, identifier)
                self.advance_chronicle(frame)
                progress = dict(through=str(self.chronicle.cursor), cursor=str(frame["cursor"]))
                if resource == "chronicle":
                    return progress | {"landmarks": {name: self.chronicle.first.get(name) for name in LANDMARKS}}
                identifier = integer(options, "id", 0, 1, (1 << 64) - 1)
                require(identifier in frame["ants"], "Unknown ant in the live colony")
                key = str(identifier)
                life = [self.exact_fact(frame, e) for e in self.chronicle.life.get(key, ())]
                balance = founding_balance(self.worker, frame, identifier) if (
                    self.worker.adult_offers and (frame["flags"] or {}).get("founding_habitat")) else None
                return progress | {"lifecycle": life, "recent_activity": list(self.chronicle.recent.get(key, ())),
                                   "balance": balance}
            require(resource == "view", "Unknown live view")
            data = self.status()
            if self.frame is None:
                return data
            frame = self.frame
            geometry, surface = frame["geometry"], frame["surface"]
            colonies = list(frame["colonies"].values())
            nursery = is_nursery(frame)
            tag = UUID(frame["world"]).int >> 64
            ecology = ECOLOGY_WORLD_TAGS.get(tag)
            habitat = frame["flags"].get("founding_habitat")
            reserve = None
            if (ecology or habitat) and self.worker.local_ecology:
                reserve = tuple(map(int, self.worker.call("RESOURCE_RESERVES").split()))
                require(len(reserve) == 4 and min(reserve) >= 0, "Invalid native resource reserve")
            trails = []
            if habitat and options.get("trails") == "1":
                for line in self.worker.call("SURFACE_TRAILS").splitlines():
                    x, z, units = line.split()
                    x, z, units = int(x), int(z), float(units)
                    require(0 <= x < surface["width"] and 0 <= z < surface["height"] and isfinite(units) and units > 0,
                            "Invalid native trail observation")
                    trails.append((x, z, units))
            focus = (0,colonies[0]["position_m"][1],0) if nursery else colonies[0]["position_m"]
            axis = options.get("axis", "y")
            require(axis in AXES, "Unknown slice axis")
            u, v, n = AXES[axis]
            solid = geometry["solid"]
            default = round((focus[n] - geometry["origin_m"][n]) / geometry["quantum_m"])
            layer = integer(options, "layer_q", default, solid[n], solid[n + 3] - 1)
            clearance = options.get("clearance") == "1"
            key = len(frame["edits"]), axis, layer, clearance
            if key not in self.sections:
                window = focused_window(geometry, focus, (u, v), 36 if nursery else 22)
                self.sections[key] = terrain_view(geometry, frame["edits"], axis, layer, window,
                                                   roof_focus=focus, clearance=clearance)
                if len(self.sections) > 8:
                    self.sections.popitem(last=False)
            group = options.get("group", "highlights")
            require(group == "all" or group in LIVE_GROUPS, "Unknown event category")
            dynamics=frame["flags"].get("nest_dynamics", {})
            plans = live_motion(self.worker.call("WORKER_MOTION"),frame) if dynamics.get("worker_motor") else {}
            bodies = live_bodies(self.worker.call("BODY_STATES"), frame) if habitat and habitat.get("anatomical") else {}
            traffic = frame["flags"].get("local_traffic",False)
            data.update(physics=frame["physics"], schema_version=frame["schema"], seed=str(frame["seed"]),
                        local_traffic=traffic, seeded_nursery=nursery,
                        provisioned_nursery=tag == 650 or ecology is not None,
                        ecology=ecology, habitat=habitat, climate=self.climate, feeder_reserve_ug=reserve, trails=trails,
                        soil_piles=frame["soil_piles"],
                        external_supply=any(s["position_m"][1] >= surface["origin_m"][1] for s in frame["sources"].values()),
                        worker_activity_timing=frame["flags"].get("worker_activity_timing"),
                        local_nest_activity=bool(frame["flags"].get("local_nest_activity")),
                        nest_dynamics=dynamics,
                        cursor=str(frame["cursor"]), recent_from_id=self.recent[0]["id"] if self.recent else str(frame["cursor"] + 1),
                        colonies=colonies, geometry=geometry, terrain=self.sections[key],
                        surface={k: v for k, v in surface.items() if k != "walkable"} |
                        {"blocked": [i for i, value in enumerate(surface["walkable"]) if not value]},
                        bounds_m=(frame["world_min_m"], frame["world_max_m"]), sources=list(frame["sources"].values()),
                        ants=[dict(ant, motion_plan=plans.get(int(ant["id"])), body=bodies.get(ant["id"]),
                                   soil_load=ant["id"] in frame["soil_carriers"],
                                   loaded=bool(any(ant["carried_ug"]) or ant["id"] in frame["soil_carriers"]),
                                   stage=label(STAGES, ant["stage"]), caste=label(CASTES, ant["caste"]),
                                   program=label(PROGRAMS, ant.get("program")), death_cause=label(DEATHS, ant.get("death_code")))
                              for ant in frame["ants"].values()],
                        events=[e for e in reversed(self.recent) if group == "all" or e["kind"] in LIVE_GROUPS[group]][:16],
                        motion=[e for e in self.recent if e["kind"] in ("Moved", "BroodMoved")],
                        actions=list(reversed(self.actions)))
            return data

    def name_path(self, name, mode="archive"):
        require(isinstance(name, str) and 1 <= len(name) <= 64 and name == name.strip() and
                not name.startswith(".") and not name.endswith(".") and
                all(ord(c) >= 32 and c not in '<>:"/\\|?*' for c in name) and
                not re.fullmatch(r"CON|PRN|AUX|NUL|(?:COM|LPT)[1-9¹²³]", name.split(".")[0].strip(), re.IGNORECASE),
                "Use a save name with 1–64 characters and no path separators or reserved names.")
        require(isinstance(mode, str) and mode in SAVE_SUFFIXES, "Unknown save format")
        return self.saves / (name + SAVE_SUFFIXES[mode])

    def list_saves(self):
        entries = []
        for path in self.saves.iterdir() if self.saves.is_dir() else ():
            mode = next((mode for mode, suffix in SAVE_SUFFIXES.items() if suffix == path.suffix.lower()), None)
            if mode is None:
                continue
            info = regular_file(path)
            if info is None:
                continue
            try:
                self.name_path(path.stem, mode)
                entries.append(save_details(path))
            except (OSError, ValueError, sqlite3.Error):
                entries.append(dict(name=path.stem, size_bytes=info.st_size, modified_ms=info.st_mtime_ns // 1_000_000,
                                    time_ms=None, mode=mode, loadable=False))
        return dict(folder=str(self.saves), entries=sorted(entries, key=lambda row: row["modified_ms"], reverse=True))

    def save(self, name, overwrite, mode):
        path = self.name_path(name, mode)
        snapshot = mode == "snapshot"
        require(not snapshot or self.worker.single_nest, "Build the updated Core to save a compact snapshot.")
        require(snapshot or not self.history_floor, "Full history is unavailable for this colony")
        exists = os.path.lexists(path)
        if exists:
            require(regular_file(path) and stable_save(path), "The destination is not a finished save slot")
            require(overwrite, "A save with this name already exists.")
            save_details(path)
        self.advance()
        token = uuid4().hex
        stage = Path(self.workdir.name) / (token + path.suffix)
        try:
            self.worker.call(("SAVE_SNAPSHOT " if snapshot else "SAVE ") + token)
            info = save_details(stage)
            if snapshot:
                with stage.open("r+b") as saved:
                    os.fsync(saved.fileno())
            if exists:
                os.replace(stage, path)
            elif os.name == "nt":
                stage.rename(path)
            else:
                os.link(stage, path)
            self.saved = info | {"name": name}
        finally:
            discard_stage(stage)
            self.reanchor()

    def load(self, name, mode="archive"):
        path = self.name_path(name, mode)
        save_details(path)
        worker = self.core()
        snapshot = mode == "snapshot"
        require(not snapshot or worker.single_nest, "Build the updated Core to load a compact snapshot.")
        token = uuid4().hex
        stage = Path(self.workdir.name) / (token + path.suffix)
        try:
            # A loaded Core has a read handle to its history prefix. Keep it
            # independent of the file that the player manages in Explorer.
            copyfile(path, stage)
            details = save_details(stage) | {"name": name}
            command = "LOAD_SNAPSHOT" if snapshot else "LOAD"
            raw = worker.call(f"{command} {token} {details['world_id']}")
            self.install(raw, running=False, saved=details, copy=None if snapshot else stage)
        finally:
            if self.loaded_copy != stage:
                discard_stage(stage)

    def write(self, resource, data):
        with self.lock:
            if resource == "single-nest":
                supply = data.get("supply", "finite")
                require(supply in ("finite", "absent"), "Unknown supply setting")
                seed = data.get("seed", 2)
                require(type(seed) is int and 1 <= seed <= 2147483647, "Enter a valid software seed")
                core = self.core()
                require(core.single_nest, "Build the updated Core to start a sealed founding chamber.")
                models = {"reference": "NEW_SINGLE_NEST"}
                if core.anatomical:
                    models["anatomical"] = "NEW_ANATOMICAL_NEST"
                if core.mouth_access:
                    models["oral"] = "NEW_ORAL_NEST"
                if core.adult_offers:
                    models["offers"] = "NEW_OFFER_NEST"
                if core.wall_handoff:
                    models["wall"] = "NEW_WALL_HANDOFF_NEST"
                if core.anatomical_handoff:
                    models["mouth-handoff"] = "NEW_MOUTH_HANDOFF_NEST"
                if core.familiar_return:
                    models["familiar"] = "NEW_FAMILIAR_RETURN_NEST"
                model = data.get("model", "anatomical" if core.anatomical else "reference")
                require(isinstance(model, str) and model in models, "Build the updated Core to start this nest model.")
                command = models[model]
                self.install(core.call(f"{command} {randbits(63) or 1} {seed} 250 80 plugged 1955 reachable {supply}"),
                             running=True)
            elif resource == "observatory":
                preset = data.get("preset")
                require(isinstance(preset, str) and preset in OBSERVATORY_PRESETS, "Unknown observatory preset")
                entrance, supply = OBSERVATORY_PRESETS[preset]
                core = self.core()
                require(core.observatory, "Build the updated Core to start a live observatory.")
                command = f"NEW_OBSERVATORY {randbits(63) or 1} 2 250 80 {entrance} 1955 reference {supply}"
                self.install(core.call(command), running=True)
            elif resource == "habitat":
                temperature, humidity = data.get("temperature"), data.get("humidity")
                require(type(temperature) is int and temperature in HABITAT_TEMPERATURES and
                        type(humidity) is int and humidity in HABITAT_HUMIDITIES,
                        "Choose a supported founding temperature and humidity")
                sealed, trail = data.get("soil_plug", False), data.get("trail_half_life", 1955)
                seed = data.get("seed", 2)
                require(type(sealed) is bool and type(trail) is int and trail in (60, 1955),
                        "Choose a supported entrance and trail setting")
                require(type(seed) is int and 1 <= seed <= 2**31 - 1, "Choose a whole number between 1 and 2147483647 for the world seed")
                core = self.core()
                require(core.founding_habitat, "Build the updated Core to start a founding habitat.")
                access = "plugged" if sealed else "open"
                self.install(core.call(f"NEW_HABITAT {randbits(63) or 1} {seed} {temperature} {humidity} {access} {trail}"), running=True)
            elif resource == "nursery":
                treatment = data.get("treatment")
                if treatment is None:
                    traffic = data.get("traffic", True)
                    require(type(traffic) is bool, "Unknown nursery traffic setting")
                    treatment = "traffic" if traffic else "reference"
                require(isinstance(treatment, str) and treatment in NURSERY_TREATMENTS, "Unknown nursery treatment")
                core = self.core()
                require(core.nursery and (treatment != "provisioned" or core.provisioned_nursery),
                        "Build the native Core to open the nursery experiment.")
                require(not treatment.startswith("ecology") or core.local_ecology,
                        "Build the updated native Core to open the ecology experiment.")
                self.install(core.call(f"NEW_NURSERY {randbits(63) or 1} 17 {NURSERY_TREATMENTS[treatment]}"), running=True)
            elif resource == "new":
                timing = data.get("timing", "standard")
                require(isinstance(timing, str) and timing in NEW_COLONY_TIMINGS, "Unknown worker timing")
                activity = data.get("local_nest_activity", False)
                require(type(activity) is bool, "Unknown local nest activity setting")
                dynamics=data.get("nest_dynamics",False)
                require(type(dynamics) is bool, "Unknown nest dynamics setting")
                require(not dynamics or self.core().worker_motor, "Build the R0-r1 Core to start this experiment.")
                command = "NEW_MOTOR" if dynamics else "NEW_NEST" if activity else "NEW"
                self.install(self.core().call(f"{command} {randbits(63) or 1} 1{NEW_COLONY_TIMINGS[timing]}"), running=True)
            elif resource == "load":
                self.load(data.get("name"), data.get("mode", "archive"))
            elif resource == "folder":
                self.saves.mkdir(parents=True, exist_ok=True)
                open_folder(self.saves)
            else:
                require(self.frame is not None, "Create or load a colony first")
                if resource == "save":
                    mode = data.get("mode", "archive")
                    self.save(data.get("name"), data.get("overwrite") is True, mode)
                elif resource == "seek":
                    self.start_seek(data.get("target"), data.get("occurrence", "first"))
                elif resource == "clock":
                    rate, running = data.get("rate", self.rate), data.get("running", self.running)
                    require(type(rate) is int and rate in RATES and type(running) is bool, "Invalid live clock settings")
                    if self.seeking():
                        self.stop_seek("cancelled")
                    else:
                        self.advance()
                    self.running = data.get("running", self.running)
                    self.rate = data.get("rate", self.rate)
                    if self.running:
                        self.fast_forward = None
                    self.error = None
                    self.reanchor()
                else:
                    raise ValueError("Unknown live command")
            return self.status()
