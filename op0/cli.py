"""Launcher and dependency-free terminal interface for OP0."""

from argparse import ArgumentParser
import json
from math import isfinite
import os
from pathlib import Path
import sqlite3
import sys
from time import sleep
from urllib.parse import urlencode
from zipfile import BadZipFile

from . import DAY
from .archive import pack, zip_terminal_frame
from .codec import ArchiveError, require
from .index import Catalog
from .locale import LANGUAGES, translator
from .query import HOUR, ReadAPI


ROOT = Path(__file__).resolve().parent.parent
VERIFIED = ROOT / "experiments/s6_4_founding_cohort_release/correction"
PREVIOUS = ROOT / "experiments/s6_4_ecological_mechanism_closure/portable-physics/joint"
DEMOS = (
    (VERIFIED, "borisovka-1-shaft-joint-balanced-5500-corrected-c011n1-r1.zip", "Founding colony",
     "Borisovka · protected shaft · balanced supply. Follow the queen and her first foragers."),
    (VERIFIED, "borisovka-1-shaft-joint-absent-5500-corrected-c011n1-r1.zip", "No external supply",
     "Borisovka · same shaft and seed. Observe brood losses and colony decline without external resources."),
    (VERIFIED, "borisovka-1-shaft-joint-no-protein-5500-corrected-c011n1-r1.zip", "Protein-limited colony",
     "Borisovka · shaft · no external protein. A recorded nutritional control."),
    (VERIFIED, "st_petersburg-1-dogleg-joint-limited-5500-corrected-c011n1-r1.zip", "Limited supply · dogleg",
     "St. Petersburg · dogleg · limited supply. A large history with recorded decline."),
    (PREVIOUS, "borisovka-1-shaft-joint-balanced-5500.zip", "Before the feeding correction",
     "Borisovka · protected shaft · the reference run for inspecting the first-ration change."),
)
ERRORS = (ArchiveError, ValueError, KeyError, TypeError, OSError, sqlite3.Error, BadZipFile, RuntimeError)


def cache_path():
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "AntWorld/OP0"
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "antworld/op0"


def default_catalog(path, include_demos=True):
    catalog = Catalog(path)
    if include_demos:
        manifests = {}
        producers = {}
        for folder, filename, title, description in DEMOS:
            if not (folder / filename).is_file():
                continue
            if folder not in manifests:
                manifests[folder] = {r["archive"]: r["sha256"] for r in map(json.loads,
                                    (folder / "archives.jsonl").read_text(encoding="utf-8").splitlines())}
                run = json.loads((folder / "run.json").read_bytes())
                producers[folder] = {field: run[field] for field in ("source", "cpp_tree", "binary_sha256") if field in run}
            key = catalog.register(folder / filename, title, manifests[folder][filename], description, producers[folder])
            tip = zip_terminal_frame(folder / filename)
            require(tip["framed"], "Published catalogue lacks a terminal frame")
            catalog.entries[key]["preview"] = dict(world_id=tip["world"], physics=tip["physics"], seed=str(tip["seed"]),
                                                  start_ms=0, end_ms=tip["time_ms"], facts=tip["cursor"],
                                                  workers=sum(ant["stage"] == 3 and ant["caste"] == 0 for ant in tip["ants"].values()),
                                                  queens=sum(ant["stage"] == 3 and ant["caste"] == 1 for ant in tip["ants"].values()),
                                                  integrity="FRAME_MATCHED · HISTORY NOT INDEXED", readiness="ENGINEERING_ONLY")
    saved = catalog.root / "imports.json"
    if saved.is_file():
        for value in json.loads(saved.read_bytes()):
            try:
                catalog.register(Path(value))
            except (OSError, ArchiveError) as err:
                print(f"OP0 skipped registered import: {err}", file=sys.stderr)
    return catalog


def api_get(api, path, **options):
    return api.dispatch("/api/v1/" + path + ("?" + urlencode(options) if options else ""))["data"]


def register_import(catalog, path):
    key = catalog.register(path)
    worlds, _, elapsed = catalog.browse(key)
    saved = catalog.root / "imports.json"
    paths = set(json.loads(saved.read_bytes())) if saved.is_file() else set()
    paths.add(str(path.resolve()))
    # Update the local catalogue only, after the source was checked.
    temporary = saved.with_suffix(".tmp")
    temporary.write_text(json.dumps(sorted(paths), indent=2), encoding="utf-8")
    temporary.replace(saved)
    return worlds, elapsed


def stamp(ms, tr):
    hh, within = divmod(ms % DAY, HOUR)
    mm, within = divmod(within, 60_000)
    ss, milli = divmod(within, 1000)
    return tr("Day {number}", number=ms // DAY) + f" {hh:02d}:{mm:02d}:{ss:02d}.{milli:03d}"


def event_text(event, tr):
    who = (" #" + event["actor"]) if event["actor"] else ""
    target = (" → #" + event["related"]) if event["related"] else ""
    detail = tr(event.get("death_cause") or event.get("outcome"))
    if event.get("action"):
        detail = tr(event["action"]["act"]) + " / " + tr(event["action"]["phase"])
    name = tr(event["kind"])
    if name != event["kind"]:
        name += f' ({event["kind"]})'
    return f'{event["id"]:>8}  {stamp(event["time_ms"], tr):>14}  {name}{who}{target}  {detail}'


class Terminal:
    def __init__(self, api, plain=False, language=None):
        self.api = api
        self.plain = plain or not sys.stdout.isatty()
        self.meta = self.follow = self.event = None
        self.t, self.after, self.next_after, self.group = 0, 0, None, "highlights"
        self.preference = api.catalog.root / "terminal-language.txt"
        saved = self.preference.read_text(encoding="utf-8").strip() if self.preference.is_file() else "en"
        self.language = language or (saved if saved in LANGUAGES else "en")
        self.tr = translator(self.language)

    def request(self, operation, **options):
        return api_get(self.api, f"world/{self.meta['key']}/{operation}", **options)

    def seek(self, position):
        self.t = max(0, min(position, self.meta["end_ms"]))
        self.event = None
        self.after = 0

    def view(self):
        tr = self.tr
        if not self.plain:
            print("\x1b[2J\x1b[H", end="")
        print("\n " + tr("ANT WORLD  /  OP0  /  OBSERVATION PREVIEW"))
        print(" ────────────────────────────────────────────────────────────────────")
        if not self.meta:
            for index, entry in enumerate(api_get(self.api, "catalog"), 1):
                print(f" {index:>2}  {tr(entry['title'])}")
                print(f"     {tr(entry['description'] or 'Imported source')}")
                if not entry["worlds"] and (preview := entry["preview"]):
                    interval = tr("{start} to {end}", start=stamp(preview["start_ms"], tr), end=stamp(preview["end_ms"], tr))
                    print("     " + " · ".join((preview["world_id"], tr("Physics {version}", version=preview["physics"]),
                                               tr("Seed {seed}", seed=preview["seed"]), interval,
                                               tr(preview["integrity"]), preview["readiness"])))
                    print("     " + tr("Frame records {workers} worker(s) and {queens} live queen(s) at the end",
                                       workers=preview["workers"], queens=preview["queens"]))
                for world in entry["worlds"]:
                    p = world["final_population"]
                    print("     " + " · ".join((world["world_id"], tr("Physics {version}", version=world["physics"]),
                                               tr("Seed {seed}", seed=world["seed"]), stamp(world["end_ms"], tr),
                                               world["integrity"], world["readiness"])))
                    print("     " + tr("End: {workers} worker(s), {queens} queen(s), {brood} brood", workers=p["workers"],
                                       queens=len(p["queens_alive"]), brood=p["eggs"] + p["larvae"] + p["pupae"]))
            print("\n " + tr("Enter a world number, import <path>, or q. The source is verified when opened."))
            print(" lang en | lang zh-CN")
            return
        meta = self.meta
        cut = {"event": self.event} if self.event else {"time_ms": self.t}
        state = self.request("state", **cut)
        pop, actions = state["population"], state["cumulative"]
        print(f" {tr(meta['title'])}  ·  {stamp(self.t, tr)} / {stamp(meta['end_ms'], tr)}  ·  "
              + tr("committed through #{id}", id=state["cursor"]))
        print(" " + " · ".join((meta["world_id"], tr(meta["population"] or "Population not recorded"),
                               tr("Seed {seed}", seed=meta["settings"]["seed"]), tr("Physics {version}", version=meta["settings"]["physics"]),
                               meta["integrity"], meta["readiness"])))
        queen = tr("alive #{ids}", ids=", #".join(pop["queens_alive"])) if pop["queens_alive"] else tr("not present at this cut")
        print(f" {tr('Queen')} {queen}  |  " + tr("{workers} workers  |  {eggs} eggs  |  {larvae} larvae  |  {pupae} pupae", **pop))
        print(" " + tr("External {external} µg  |  Nest {nest} µg  (carbs, protein, water, other)",
                       external=state["external_ug"], nest=state["nest_ug"]))
        print(" " + "  ·  ".join(f"{tr(label)} {actions.get(key, 0)}" for key, label in (
            ("collections", "Collections"), ("deliveries", "Deliveries"), ("trophallaxis", "Trophallaxis"),
            ("excavations", "Excavations"), ("activations", "Activations"))))
        if self.event:
            print("\n " + tr("Selected") + " · " + event_text(self.request("event", id=self.event), tr))
        if self.follow:
            ant = self.request("ant", id=self.follow, **cut)
            s = ant["sample"] or {}
            identity = "  ·  ".join(tr(ant[k]) for k in ("caste", "stage", "program"))
            print("\n " + tr("Tracking #{id}", id=ant["id"]) + "  ·  " + identity)
            born = stamp(ant["born_ms"], tr) if ant["born_ms"] is not None else tr("Not recorded")
            print(f" {tr('Mother')} {ant['mother'] or tr('Not recorded')}  ·  {tr('Born')} {born}  ·  "
                  f"{tr(ant['death_cause'] or ant['status'])}")
            if s:
                print(" " + tr("Sample {day}", day=stamp(s["time_ms"], tr)) +
                      f" · {s.get('energy_nj')} nJ · {s.get('hydration_ug')} {tr('µg water')} · {tr('crop')} {s.get('crop_ug')} µg")
            if ant["died_ms"] is not None:
                print(f" {tr('Died')} {stamp(ant['died_ms'], tr)} · {tr(ant['death_cause'])}")
            print(" " + tr("Life") + " · " + " | ".join(
                f"{tr(e['stage'])} #{e['id']} ({stamp(e['time_ms'], tr)})" for e in ant["life_events"]))
        lo = (self.t // DAY) * DAY
        daily = self.request("activity", day=lo // DAY)["totals"]
        print("\n " + tr("{facts} committed records · {moves} movements · {collections} collections · {deliveries} deliveries", **daily))
        events = self.request("events", since_ms=lo, until_ms=min(lo+DAY-1, meta["end_ms"]),
                              after=self.after, group=self.group, limit=7, **({"ant": self.follow} if self.follow else {}))
        self.next_after = events["next_after"]
        print("\n " + tr("Committed events in day {day}", day=lo // DAY) + f"  [{tr(self.group)}]")
        for item in events["events"]:
            print(" " + event_text(item, tr))
        if not events["events"]:
            print(" " + tr("No matching events in this window."))
        print("\n " + tr("Milestones") + " · " + " · ".join(f"{tr(m['label'])} #{m['id']}" for m in meta["milestones"] if m["label"] in
              ("First hatch", "First worker eclosed", "First food delivered", "First excavation", "First recruitment activation", "Queen died")))
        print(" " + tr("d <day>  h <HH:MM[:SS]>  +/-  n/p event  play [days/s]  e <id>  f <category>  more  a <ant>  w  q  lang en|zh-CN"))

    def seek_clock(self, arg):
        parts = arg.split(":")
        require(len(parts) in (2, 3) and all(p.isdecimal() for p in parts), "Use an hour as HH:MM or HH:MM:SS")
        hh, mm = map(int, parts[:2])
        ss = int(parts[2]) if len(parts) == 3 else 0
        requested = self.t // DAY * DAY + hh * HOUR + mm * 60_000 + ss * 1000
        require(hh < 24 and mm < 60 and ss < 60 and requested <= self.meta["end_ms"], "Time is outside the archived day")
        self.seek(requested)

    def command(self, line):
        word, _, arg = line.strip().partition(" ")
        arg = arg.strip()
        if word == "q":
            return False
        if word == "lang":
            if not arg or arg == "toggle":
                arg = "en" if self.language == "zh-CN" else "zh-CN"
            require(arg in LANGUAGES, "Choose en, zh-CN, or toggle")
            self.preference.write_text(arg + "\n", encoding="utf-8")
            self.language, self.tr = arg, translator(arg)
        elif word == "w":
            self.meta = self.follow = None
        elif not self.meta and word == "import":
            register_import(self.api.catalog, Path(arg.strip('"')))
        elif not self.meta and word.isdecimal():
            catalog = api_get(self.api, "catalog")
            if not 1 <= int(word) <= len(catalog):
                raise ValueError("Choose a world number from the list")
            worlds = api_get(self.api, f"archive/{catalog[int(word)-1]['key']}")["worlds"]
            if len(worlds) > 1:
                for i, world in enumerate(worlds, 1):
                    print(f" {i}  {self.tr(world['title'])}  {world['world_id']}")
                choice = int(input(self.tr("World in this store > ")))
                if not 1 <= choice <= len(worlds):
                    raise ValueError("Choose a published world from the list")
                world = worlds[choice-1]
            else:
                world = worlds[0]
            self.meta = api_get(self.api, f"world/{world['key']}/meta")
            self.group = "highlights"
            self.seek(0)
        elif self.meta and word:
            if word in ("+", "-"):
                self.seek(self.t + (DAY if word == "+" else -DAY))
            elif word == "d":
                days = float(arg)
                if not isfinite(days) or not 0 <= days <= self.meta["end_ms"] / DAY:
                    raise ValueError("Choose a day inside the archived time interval")
                self.seek(round(days * DAY))
            elif word == "e":
                detail = self.request("event", id=int(arg))
                self.seek(detail["time_ms"])
                self.event = detail["id"]
            elif word in ("n", "p"):
                anchor = {"event": self.event} if self.event else {"time_ms": self.t}
                detail = self.request("adjacent", direction="next" if word == "n" else "previous",
                                      **anchor, **({"ant": self.follow} if self.follow else {}))
                require(detail is not None, "No matching event in that direction.")
                self.seek(detail["time_ms"])
                self.event = detail["id"]
            elif word == "h":
                self.seek_clock(arg)
            elif word == "a":
                cut = {"event": self.event} if self.event else {"time_ms": self.t}
                self.follow = self.request("ant", id=int(arg), **cut)["id"]
                self.after = 0
            elif word == "untrack":
                self.follow = None
                self.after = 0
            elif word == "f":
                self.request("events", limit=1, group=arg)
                self.group, self.after = arg, 0
            elif word == "more":
                self.after = self.next_after or self.after
            elif word == "play":
                speed = float(arg or "6")
                if not 0.01 <= speed <= 120:
                    raise ValueError("Playback speed must be 0.01–120 days per second")
                try:
                    while self.t < self.meta["end_ms"]:
                        sleep(.25)
                        self.seek(self.t + round(speed*DAY/4))
                        self.view()
                except KeyboardInterrupt:
                    print("\n " + self.tr("Playback paused."))
            else:
                raise ValueError("Unknown command")
        return True

    def run(self):
        while True:
            self.view()
            try:
                if not self.command(input("\n op0 > ")):
                    return
            except (EOFError, KeyboardInterrupt):
                return
            except ERRORS as err:
                print(f"\n {self.tr(str(err))}", file=sys.stderr)
                if not self.plain:
                    input(" " + self.tr("Press Enter to continue "))


def main(argv=None):
    parser = ArgumentParser(prog="python -m op0", description="Replay committed AntWorld history.")
    parser.add_argument("--cache", type=Path, default=cache_path())
    parser.add_argument("--no-demos", action="store_true")
    modes = parser.add_subparsers(dest="mode", required=True)
    server = modes.add_parser("serve", help="Open the local web viewer")
    server.add_argument("--port", type=int, default=8765)
    server.add_argument("--no-browser", action="store_true")
    server.add_argument("--import-path", action="append", type=Path, default=[])
    terminal = modes.add_parser("tui", help="Open the terminal viewer")
    terminal.add_argument("--plain", action="store_true")
    terminal.add_argument("--language", choices=LANGUAGES)
    terminal.add_argument("--import-path", action="append", type=Path, default=[])
    modes.add_parser("import", help="Verify and add a ZIP or stable SQLite store").add_argument("source", type=Path)
    package = modes.add_parser("pack", help="Package an existing native export")
    package.add_argument("directory", type=Path)
    package.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.mode == "pack":
            pack(args.directory, args.output)
            return 0
        catalog = default_catalog(args.cache, not args.no_demos)
        if args.mode == "import":
            worlds, elapsed = register_import(catalog, args.source)
            for meta in worlds:
                print(f"{meta['title']} | {meta['world_id']} | {meta['facts']:,} facts | "
                      f"{meta['integrity']} | {elapsed/1000:.3f} s")
            return 0
        for path in args.import_path:
            register_import(catalog, path)
        api = ReadAPI(catalog)
        if args.mode == "tui":
            Terminal(api, args.plain, args.language).run()
        else:
            from .server import serve
            serve(api, args.port, not args.no_browser)
    except ERRORS as err:
        print(f"OP0: {err}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nOP0 closed.")
    return 0
