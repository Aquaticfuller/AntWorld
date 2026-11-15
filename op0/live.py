"""Host the native MicroWorld clock and its manually saved SQLite snapshots."""

from collections import OrderedDict
from contextlib import closing
import os
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
from .codec import CASTES, DEATHS, FACETS, HIGHLIGHTS, KINDS, PROGRAMS, STAGES, U32, checkpoint, decode_fact, label, require
from .geometry import AXES, focused_window, terrain_view
from .query import HOUR, integer


ROOT = Path(__file__).resolve().parent.parent
RATES = (1, 10, 60, 600, 3600, 86400)
FRAME_LIMIT = 128 * 1024 * 1024
LIVE_GROUPS = {name: {KINDS[kind] for kind in kinds} for name, kinds in FACETS.items()}
LIVE_GROUPS["highlights"] = {KINDS[kind] for kind in HIGHLIGHTS}


def core_path():
    name = "antworld_m0_live.exe" if os.name == "nt" else "antworld_m0_live"
    paths = (ROOT / "out/m0-live-bin" / name, ROOT / "build/m0-live" / name,
             ROOT / "build/m0-live/Release" / name)
    return next((path for path in paths if path.is_file()), paths[0])


class NativeCore:
    def __init__(self, binary, workdir):
        self.process = subprocess.Popen([str(binary)], cwd=workdir, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            require(self.call("HELLO") == b"antworld.m0.live.v1", "Unsupported live Core protocol")
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


def read_recent(data, frame):
    offset, previous = 0, None
    events = []
    expected = UUID(frame["world"]).int
    while offset < len(data):
        size = U32.unpack_from(data, offset)[0]
        start = offset + U32.size
        end = start + size
        require(end <= len(data), "Truncated live event")
        identity, fact = decode_fact(data[start:end])
        require(expected == ((identity[0] << 64) | identity[1]) and fact.time <= frame["time_ms"] and
                (previous is None or fact.id == previous + 1), "Live event does not belong to the published cut")
        events.append(fact.packet())
        previous, offset = fact.id, end
    require(previous == (frame["cursor"] or None), "Live events do not reach the published cut")
    return events


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
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        require(db.execute("PRAGMA application_id").fetchone() == (SQLITE_ID,) and
                db.execute("PRAGMA user_version").fetchone() == (2,), "Expected an AntWorld SQLite save")
        rows = db.execute("SELECT w.world,w.time_ms,w.cursor,substr(g.checkpoint,1,24) FROM worlds w "
                          "JOIN generations g ON g.world=w.world AND g.generation=w.generation LIMIT 2").fetchall()
    require(len(rows) == 1, "Expected a single MicroWorld colony")
    world, stamp, cursor, header = rows[0]
    require(type(stamp) is int and 0 <= stamp < 1 << 53 and isinstance(header, bytes) and len(header) == 24 and
            header[:16] == b"AWSTATE1AWCKPTM\0" and
            header[16:20] == U32.pack(23) and U32.unpack_from(header, 20)[0] in (27, 28, 29, 30),
            "Expected a MicroWorld checkpoint")
    require(isinstance(world, str) and str(UUID(world)) == world and isinstance(cursor, str) and key(cursor) < 1 << 53,
            "Invalid save identity")
    return dict(name=path.stem, world_id=world, time_ms=stamp, facts=key(cursor), size_bytes=info.st_size,
                modified_ms=info.st_mtime_ns // 1_000_000, loadable=True)


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
        self.sections = OrderedDict()
        self.epoch = 0
        self.running = False
        self.rate = 1
        self.anchor_ns = self.anchor_ms = 0
        self.saved = None
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
            self.recent = read_recent(self.worker.call("RECENT"), frame)
        self.frame = frame

    def reanchor(self):
        self.anchor_ns, self.anchor_ms = self.clock(), self.frame["time_ms"]

    def install(self, raw, *, running, saved=None, copy=None):
        if self.loaded_copy:
            discard_stage(self.loaded_copy)
        self.loaded_copy = copy
        self.publish(raw, reset=True)
        self.epoch += 1
        self.sections.clear()
        self.running, self.rate, self.saved, self.error = running, 1, saved, None
        self.reanchor()

    def advance(self):
        if self.running:
            stamp = self.frame["time_ms"]
            target = self.anchor_ms + (self.clock() - self.anchor_ns) * self.rate // 1_000_000
            # A slow frame may fall behind the desired rate. Bound one Core call
            # so the next pause or save can still take the controller lock.
            if target > stamp:
                self.publish(self.worker.call(f"ADVANCE {min(target, stamp + 12 * HOUR)}"))

    def run_clock(self):
        while not self.stopping.wait(.10):
            with self.lock:
                try:
                    self.advance()
                except Exception as err:
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
                    world_id=frame["world"] if frame else None, epoch=self.epoch, running=self.running, rate=self.rate,
                    saved_name=self.saved["name"] if self.saved else None, dirty=dirty, error=self.error)

    def read(self, resource, options):
        with self.lock:
            if resource == "status":
                return self.status()
            if resource == "saves":
                return self.list_saves()
            require(resource == "view", "Unknown live view")
            data = self.status()
            if self.frame is None:
                return data
            frame = self.frame
            geometry, surface = frame["geometry"], frame["surface"]
            colonies = list(frame["colonies"].values())
            focus = colonies[0]["position_m"]
            axis = options.get("axis", "y")
            require(axis in AXES, "Unknown slice axis")
            u, v, n = AXES[axis]
            solid = geometry["solid"]
            default = round((focus[n] - geometry["origin_m"][n]) / geometry["quantum_m"])
            layer = integer(options, "layer_q", default, solid[n], solid[n + 3] - 1)
            clearance = options.get("clearance") == "1"
            key = len(frame["edits"]), axis, layer, clearance
            if key not in self.sections:
                window = focused_window(geometry, focus, (u, v), 22)
                self.sections[key] = terrain_view(geometry, frame["edits"], axis, layer, window,
                                                   roof_focus=focus, clearance=clearance)
                if len(self.sections) > 8:
                    self.sections.popitem(last=False)
            group = options.get("group", "highlights")
            require(group == "all" or group in LIVE_GROUPS, "Unknown event category")
            data.update(physics=frame["physics"], schema_version=frame["schema"], seed=str(frame["seed"]),
                        cursor=str(frame["cursor"]), colonies=colonies, geometry=geometry, terrain=self.sections[key],
                        surface={k: v for k, v in surface.items() if k != "walkable"} |
                        {"blocked": [i for i, value in enumerate(surface["walkable"]) if not value]},
                        bounds_m=(frame["world_min_m"], frame["world_max_m"]), sources=list(frame["sources"].values()),
                        ants=[dict(ant, stage=label(STAGES, ant["stage"]), caste=label(CASTES, ant["caste"]),
                                   program=label(PROGRAMS, ant.get("program")), death_cause=label(DEATHS, ant.get("death_code")))
                              for ant in frame["ants"].values()],
                        events=[e for e in reversed(self.recent) if group == "all" or e["kind"] in LIVE_GROUPS[group]][:16],
                        motion=[e for e in self.recent if e["kind"] in ("Moved", "BroodMoved")])
            return data

    def name_path(self, name):
        require(isinstance(name, str) and 1 <= len(name) <= 64 and name == name.strip() and
                not name.startswith(".") and not name.endswith(".") and
                all(ord(c) >= 32 and c not in '<>:"/\\|?*' for c in name) and
                not re.fullmatch(r"CON|PRN|AUX|NUL|(?:COM|LPT)[1-9¹²³]", name.split(".")[0].strip(), re.IGNORECASE),
                "Use a save name with 1–64 characters and no path separators or reserved names.")
        return self.saves / (name + ".sqlite")

    def list_saves(self):
        entries = []
        for path in self.saves.glob("*.sqlite"):
            info = regular_file(path)
            if info is None:
                continue
            try:
                self.name_path(path.stem)
                entries.append(save_details(path))
            except (OSError, ValueError, sqlite3.Error):
                entries.append(dict(name=path.stem, size_bytes=info.st_size, modified_ms=info.st_mtime_ns // 1_000_000,
                                    time_ms=None, loadable=False))
        return dict(folder=str(self.saves), entries=sorted(entries, key=lambda row: row["modified_ms"], reverse=True))

    def save(self, name, overwrite):
        path = self.name_path(name)
        exists = os.path.lexists(path)
        if exists:
            require(regular_file(path) and stable_save(path), "The destination is not a finished save slot")
            require(overwrite, "A save with this name already exists.")
            save_details(path)
        self.advance()
        token = uuid4().hex
        stage = Path(self.workdir.name) / (token + ".sqlite")
        try:
            self.worker.call("SAVE " + token)
            info = save_details(stage)
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

    def load(self, name):
        path = self.name_path(name)
        save_details(path)
        worker = self.core()
        token = uuid4().hex
        stage = Path(self.workdir.name) / (token + ".sqlite")
        try:
            # A loaded Core has a read handle to its history prefix. Keep it
            # independent of the file that the player manages in Explorer.
            copyfile(path, stage)
            details = save_details(stage) | {"name": name}
            raw = worker.call(f"LOAD {token} {details['world_id']}")
            self.install(raw, running=False, saved=details, copy=stage)
        finally:
            if self.loaded_copy != stage:
                discard_stage(stage)

    def write(self, resource, data):
        with self.lock:
            if resource == "new":
                self.install(self.core().call(f"NEW {randbits(63) or 1} 1"), running=True)
            elif resource == "load":
                self.load(data.get("name"))
            elif resource == "folder":
                self.saves.mkdir(parents=True, exist_ok=True)
                open_folder(self.saves)
            else:
                require(self.frame is not None, "Create or load a colony first")
                if resource == "save":
                    self.save(data.get("name"), data.get("overwrite") is True)
                elif resource == "clock":
                    rate, running = data.get("rate", self.rate), data.get("running", self.running)
                    require(type(rate) is int and rate in RATES and type(running) is bool, "Invalid live clock settings")
                    self.advance()
                    self.running, self.rate, self.error = running, rate, None
                    self.reanchor()
                else:
                    raise ValueError("Unknown live command")
            return self.status()
