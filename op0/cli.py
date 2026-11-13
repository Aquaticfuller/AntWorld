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
from .query import ReadAPI


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


def stamp(ms):
    return f"day {ms / DAY:,.3f}"


def event_text(event):
    who = (" #" + event["actor"]) if event["actor"] else ""
    target = (" → #" + event["related"]) if event["related"] else ""
    detail = event.get("death_cause") or event.get("outcome")
    if event.get("action"):
        detail = event["action"]["act"] + " / " + event["action"]["phase"]
    return f'{event["id"]:>8}  {stamp(event["time_ms"]):>14}  {event["kind"]}{who}{target}  {detail}'


class Terminal:
    def __init__(self, api, plain=False):
        self.api = api
        self.plain = plain or not sys.stdout.isatty()
        self.meta = self.follow = self.event = None
        self.t, self.after, self.next_after, self.group = 0, 0, None, "highlights"

    def request(self, operation, **options):
        return api_get(self.api, f"world/{self.meta['key']}/{operation}", **options)

    def seek(self, position):
        self.t = max(0, min(position, self.meta["end_ms"]))
        self.event = None
        self.after = 0

    def view(self):
        if not self.plain:
            print("\x1b[2J\x1b[H", end="")
        print("\n ANT WORLD  /  OP0  /  OBSERVATION PREVIEW")
        print(" ────────────────────────────────────────────────────────────────────")
        if not self.meta:
            for index, entry in enumerate(api_get(self.api, "catalog"), 1):
                print(f" {index:>2}  {entry['title']}")
                print(f"     {entry['description'] or 'Imported source'}")
                if not entry["worlds"] and (preview := entry["preview"]):
                    print(f"     {preview['world_id']} · physics {preview['physics']} · seed {preview['seed']} · "
                          f"{stamp(preview['start_ms'])} to {stamp(preview['end_ms'])} · {preview['integrity']} · {preview['readiness']}")
                    print(f"     Frame records {preview['workers']} worker(s) and {preview['queens']} live queen(s) at the end")
                for world in entry["worlds"]:
                    p = world["final_population"]
                    print(f"     {world['world_id']} · physics {world['physics']} · seed {world['seed']} · "
                          f"{stamp(world['end_ms'])} · {world['integrity']} · {world['readiness']}")
                    print(f"     End: {p['workers']} worker(s), {len(p['queens_alive'])} queen(s), "
                          f"{p['eggs'] + p['larvae'] + p['pupae']} brood")
            print("\n Enter a world number, import <path>, or q. The source is verified when opened.")
            return
        meta = self.meta
        cut = {"event": self.event} if self.event else {"time_ms": self.t}
        state = self.request("state", **cut)
        pop, actions = state["population"], state["cumulative"]
        print(f" {meta['title']}  ·  {stamp(self.t)} / {stamp(meta['end_ms'])}  ·  committed through #{state['cursor']}")
        print(f" {meta['world_id']}  ·  {meta['population'] or 'Population not recorded'}  ·  seed {meta['settings']['seed']} "
              f" ·  physics {meta['settings']['physics']}  ·  {meta['integrity']}  ·  {meta['readiness']}")
        print(" Queen " + ("alive #" + ", #".join(pop["queens_alive"]) if pop["queens_alive"] else "not present at this cut") +
              f"  |  {pop['workers']} workers  |  {pop['eggs']} eggs  |  {pop['larvae']} larvae  |  {pop['pupae']} pupae")
        print(f" External {state['external_ug']} µg  |  Nest {state['nest_ug']} µg  (carbs, protein, water, other)")
        print(f" Collections {actions.get('collections', 0)}  ·  Deliveries {actions.get('deliveries', 0)}  ·  "
              f"Trophallaxis {actions.get('trophallaxis', 0)}  ·  Excavations {actions.get('excavations', 0)}  ·  "
              f"Activations {actions.get('activations', 0)}")
        if self.event:
            print("\n Selected: " + event_text(self.request("event", id=self.event)))
        if self.follow:
            ant = self.request("ant", id=self.follow, **cut)
            s = ant["sample"] or {}
            print(f"\n Tracking #{ant['id']}  ·  {ant['caste']}  ·  {ant['stage']}  ·  {ant['program']}")
            print(f" Mother {ant['mother'] or 'Not recorded'}  ·  born "
                  f"{stamp(ant['born_ms']) if ant['born_ms'] is not None else 'Not recorded'}  ·  "
                  f"{ant['death_cause'] or ant['status']}")
            if s:
                print(f" Sample {stamp(s['time_ms'])}: {s.get('energy_nj')} nJ · {s.get('hydration_ug')} µg water · "
                      f"crop {s.get('crop_ug')} µg")
            if ant["died_ms"] is not None:
                print(f" Died {stamp(ant['died_ms'])}; {ant['death_cause'] or 'cause not recorded'}")
            print(" Life: " + " | ".join(f"{e['stage']} #{e['id']} ({stamp(e['time_ms'])})" for e in ant["life_events"]))
        lo = (self.t // DAY) * DAY
        events = self.request("events", since_ms=lo, until_ms=min(lo+DAY-1, meta["end_ms"]),
                              after=self.after, group=self.group, limit=7, **({"ant": self.follow} if self.follow else {}))
        self.next_after = events["next_after"]
        print(f"\n Committed events in day {lo // DAY}  [{self.group}]")
        for item in events["events"]:
            print(" " + event_text(item))
        if not events["events"]:
            print(" No matching events in this window.")
        print("\n Milestones: " + " · ".join(f"{m['label']} #{m['id']}" for m in meta["milestones"] if m["label"] in
              ("First hatch", "First worker eclosed", "First food delivered", "First excavation", "First recruitment activation", "Queen died")))
        print(" d <day>  +/-  play [days/s]  pause (Ctrl-C)  e <event>  f <category>  more  a <ant>  untrack  w  q")

    def command(self, line):
        word, _, arg = line.strip().partition(" ")
        arg = arg.strip()
        if word == "q":
            return False
        if word == "w":
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
                    print(f" {i}  {world['title']}  {world['world_id']}")
                choice = int(input("World in this store > "))
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
                print(event_text(detail))
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
                    print("\n Playback paused.")
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
                print(f"\n {err}", file=sys.stderr)
                if not self.plain:
                    input(" Press Enter to continue ")


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
            Terminal(api, args.plain).run()
        else:
            from .server import serve
            serve(api, args.port, not args.no_browser)
    except ERRORS as err:
        print(f"OP0: {err}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nOP0 closed.")
    return 0
