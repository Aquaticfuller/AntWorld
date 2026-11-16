"""Verify the live clock, native continuation and local save controls."""

from contextlib import closing
from hashlib import sha256
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from op0 import DAY
from op0.archive import prefixed
from op0.codec import CASTES, checkpoint, decode_fact
from op0.index import Catalog
from op0.live import ROOT, LiveSession, NativeCore, core_path, read_live_events
from op0.query import HOUR, ReadAPI
from op0.server import bind


BINARY = Path(os.environ.get("M0_LIVE_CORE", core_path())).resolve()
WITNESS = ROOT / "experiments/m0/portable-demo/borisovka-shaft-1-slots.zip"
MINUTE = HOUR // 60


@unittest.skipUnless(BINARY.is_file(), "Build antworld_m0_live or set M0_LIVE_CORE")
class LiveTests(unittest.TestCase):
    def setUp(self):
        root = Path(os.environ.get("M0_LIVE_TEST_ROOT", "out")).resolve()
        root.mkdir(parents=True, exist_ok=True)
        self.folder = Path(self.enterContext(TemporaryDirectory(dir=root, prefix="m0-live-test-")))
        self.now = 1_000_000_000
        self.live = self.enterContext(LiveSession(BINARY, self.folder / "saves", clock=lambda: self.now))

    def advance(self, delta_ms):
        with self.live.lock:
            self.now += delta_ms * 1_000_000
            self.live.advance()
            return self.live.status()

    def test_new_colony_matches_reviewed_day_90_checkpoint(self):
        with ZipFile(WITNESS) as witness, closing(NativeCore(BINARY, self.folder)) as core:
            core.call("NEW 270001 1")
            self.assertEqual(sha256(core.call(f"ADVANCE {90 * DAY}")).digest(),
                             sha256(witness.read("final.frame")).digest())
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_nest_dynamics_is_opt_in_and_survives_sqlite(self):
        self.live.write("new", {"nest_dynamics": True})
        self.live.write("clock", {"running": False})
        frame = self.live.worker.call(f"ADVANCE {48 * DAY}")
        self.live.publish(frame)
        view = self.live.read("view", {})
        self.assertEqual((view["schema_version"], view["physics"]), (26, 33))
        self.assertEqual(view["nest_dynamics"], {"worker_motor": True, "excavation": 3})
        self.live.write("save", {"name": "Nest dynamics"})
        expected = self.live.worker.call(f"ADVANCE {49 * DAY}")
        self.live.write("load", {"name": "Nest dynamics"})
        self.assertEqual(self.live.worker.call("FRAME"), frame)
        self.assertEqual(self.live.worker.call(f"ADVANCE {49 * DAY}"), expected)
        self.assertEqual(self.live.worker.call("CHECK_LEDGERS"), b"")
        self.live.write("new", {})
        self.assertEqual(self.live.read("view", {})["physics"], 29)

    def test_nursery_view_reports_native_motion_and_preserves_it_through_sqlite(self):
        with patch("op0.live.randbits", return_value=91):
            self.live.write("nursery", {"traffic": False})
            control = self.live.read("view", {})
            self.live.write("nursery", {"traffic": True})
        initial = self.live.read("view", {})
        self.assertEqual((control["physics"], initial["physics"], initial["schema_version"]), (33, 34, 27))
        self.assertEqual((initial["seed"], initial["rate"], initial["time_ms"]), ("17", 1, 0))
        self.assertTrue(initial["seeded_nursery"])
        self.assertEqual([(a["id"], a["position_m"]) for a in control["ants"]],
                         [(a["id"], a["position_m"]) for a in initial["ants"]])
        self.advance(4_050)
        self.live.write("clock", {"running": False})
        frame = self.live.worker.call("FRAME")
        moving = self.live.read("view", {})
        ant = next(a for a in moving["ants"] if 0 < (a["motion_plan"] or {}).get("progress", 0) < 1)
        self.assertEqual(ant["position_m"], ant["motion_plan"]["from_m"])
        self.assertNotEqual(ant["motion_plan"]["to_m"], ant["position_m"])
        self.assertEqual(self.live.worker.call("FRAME"), frame)
        self.live.write("save", {"name": "In motion"})
        expected = self.live.worker.call("ADVANCE 16000")
        self.live.write("load", {"name": "In motion"})
        self.assertEqual(self.live.worker.call("FRAME"), frame)
        self.assertEqual(self.live.read("view", {})["ants"], moving["ants"])
        self.assertEqual(self.live.worker.call("ADVANCE 16000"), expected)
        self.assertEqual(self.live.worker.call("CHECK_LEDGERS"), b"")

    def test_nursery_runs_past_the_former_lifetime_event_limit_without_writing(self):
        with closing(NativeCore(BINARY, self.folder)) as core:
            if not core.local_ecology:
                self.skipTest("Build the native live Core with compact history")
            core.call("NEW_NURSERY 91 17 2")
            frame = checkpoint(core.call(f"ADVANCE {54 * HOUR}"))
            total, hot, packed, budget = map(int, core.call("HISTORY_STORAGE").split())
            self.assertEqual((frame["time_ms"], total), (54 * HOUR, frame["cursor"]))
            self.assertGreater(total, 4_000_000)
            self.assertLess(hot, 65_536)
            self.assertLess(0, packed)
            self.assertLess(packed, budget)
            page = read_live_events(core.call("FACTS_AFTER 4000000"), frame)
            self.assertEqual([int(fact["id"]) for fact in page], list(range(4_000_001, 4_000_513)))
            self.assertEqual(core.call("CHECK_LEDGERS"), b"")
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_compressed_history_continues_across_a_saved_prefix(self):
        with closing(NativeCore(BINARY, self.folder)) as core:
            if not core.local_ecology:
                self.skipTest("Build the native live Core with compact history")
            core.call("NEW_NURSERY 91 17 2")
            saved = core.call(f"ADVANCE {25 * MINUTE}")
            saved_cut = checkpoint(saved)
            save_id = "0" * 32
            core.call(f"SAVE {save_id}")

            def history_hash(cut):
                digest = sha256()
                for after in range(0, cut["cursor"], 512):
                    page = core.call(f"FACTS_AFTER {after}")
                    self.assertTrue(page)
                    digest.update(page)
                return digest.hexdigest()

            final = core.call(f"ADVANCE {60 * MINUTE}")
            expected_history = history_hash(checkpoint(final))
            self.assertEqual(core.call(f"LOAD {save_id} {saved_cut['world']}"), saved)
            self.assertEqual(int(core.call("HISTORY_STORAGE").split()[2]), 0)
            # The resumed runtime packs its new suffix while leaving the
            # verified SQLite prefix accessible through the same history API.
            core.call(f"ADVANCE {45 * MINUTE}")
            self.assertEqual(core.call(f"ADVANCE {60 * MINUTE}"), final)
            self.assertGreater(int(core.call("HISTORY_STORAGE").split()[2]), 0)
            self.assertEqual(history_hash(checkpoint(final)), expected_history)
            self.assertEqual(core.call("CHECK_LEDGERS"), b"")

    def test_local_ecology_observes_physical_supply_and_uptake(self):
        if not self.live.core().local_ecology:
            self.skipTest("Build the native live Core with local ecology")
        for treatment, water, scenario in (("ecology", 4000, "water-fed"), ("ecology-dry", 0, "no-external-water")):
            with self.subTest(treatment=treatment), patch("op0.live.randbits", return_value=91):
                self.live.write("nursery", {"treatment": treatment})
                initial = self.live.read("view", {})
                self.assertEqual((initial["ecology"], initial["physics"], initial["rate"]), (scenario, 35, 1))
                self.assertEqual(initial["sources"][0]["stock_ug"], (4000, 500, water, 0))
                self.assertEqual(initial["feeder_reserve_ug"], (7000, 875, 7 * water // 4, 0))
                self.advance(10 * MINUTE)
                self.live.write("clock", {"running": False})
                with self.live.lock:
                    core, frame = self.live.worker, self.live.frame
                    facts = [fact for after in range(0, frame["cursor"], 512)
                             for fact in read_live_events(core.call(f"FACTS_AFTER {after}"), frame)]
                    delivery = next(f for f in facts if f["kind"] == "FoodDelivered")
                    self.assertEqual(delivery["mass_ug"][2] > 0, bool(water))
                    self.assertTrue(any(f["kind"] == "NutritionTransferred" and sum(f["mass_ug"]) for f in facts))
                    absorbed = [f for f in facts if f["kind"] == "PhysiologyUpdated" and f["actor"] == delivery["actor"]
                                and f["time_ms"] >= delivery["time_ms"]]
                    self.assertTrue(any(f["mass_ug"][0] > 0 for f in absorbed))
                    self.assertEqual(any(f["mass_ug"][2] > 0 for f in absorbed), bool(water))
                    self.assertEqual(core.call("CHECK_LEDGERS"), b"")

        self.live.write("nursery", {"treatment": "ecology"})
        self.live.write("clock", {"running": False})
        self.live.publish(self.live.worker.call(f"ADVANCE {DAY}"))
        view = self.live.read("view", {"group": "food"})
        self.assertEqual(view["feeder_reserve_ug"], (6000, 750, 6000, 0))
        self.assertTrue(any(fact["kind"] == "ResourceReleased" for fact in view["events"]))
        self.live.publish(self.live.worker.call(f"ADVANCE {2 * DAY}"))
        view = self.live.read("view", {"group": "birth"})
        egg, = (ant for ant in view["ants"] if ant["stage"] == "Egg")
        self.assertEqual((egg["mother"], egg["born_ms"]), ("2", 2 * DAY))
        self.assertTrue(any(fact["kind"] == "AntBorn" and fact["actor"] == egg["id"] for fact in view["events"]))
        self.assertEqual(self.live.worker.call("CHECK_LEDGERS"), b"")

    def test_fast_forward_stops_at_each_committed_milestone(self):
        expected, positions = {}, {}
        with ZipFile(WITNESS) as witness, witness.open("facts.bin") as stream:
            final = checkpoint(witness.read("final.frame"))
            ants = final["ants"]
            surface_y = final["surface"]["origin_m"][1]
            for _, raw in prefixed(stream):
                _, fact = decode_fact(raw)
                event = fact.packet()
                kind, stage = event["kind"], event["stage"]
                if (kind, stage) == ("AntBorn", "Egg"):
                    expected.setdefault("egg", event)
                elif (kind, stage) == ("StageChanged", "Larva"):
                    expected.setdefault("hatch", event)
                if stage == "Adult" and fact.actor in ants and CASTES[ants[fact.actor]["caste"]] == "Worker":
                    if kind == "StageChanged":
                        expected.setdefault("worker", event)
                    if kind == "FoodDelivered" and sum(fact.mass) > 0:
                        expected.setdefault("delivery", event)
                    if kind == "SoilExcavated":
                        edit = next(e for e in final["edits"] if e["event"] == fact.id)
                        self.assertGreater(edit["volume_q3"], 0)
                        event["geometry_edits"] = [edit | {"actor": event["actor"]}]
                        expected.setdefault("excavation", event)
                    if kind in ("AntSeeded", "StageChanged", "Moved"):
                        previous = positions.get(fact.actor)
                        if kind == "Moved" and previous and previous[1] < surface_y <= fact.position[1]:
                            expected.setdefault("exit", event)
                        positions[fact.actor] = fact.position
                if len(expected) == 6:
                    break
        targets = ("egg", "hatch", "worker", "exit", "delivery", "excavation")
        self.assertEqual(set(expected), set(targets))

        with patch("op0.live.randbits", return_value=270001):
            self.live.write("new", {})
        with self.assertRaisesRegex(ValueError, "Unknown live milestone"):
            self.live.write("seek", {"target": "unknown"})

        self.live.write("seek", {"target": "egg"})
        self.advance(100)
        cancelled = self.live.write("clock", {"running": False})
        self.assertEqual((cancelled["fast_forward"]["state"], cancelled["running"], cancelled["rate"]),
                         ("cancelled", False, 1))

        with closing(NativeCore(BINARY, self.folder)) as reference:
            reference.call("NEW 270001 1")
            for target in targets:
                with self.subTest(target=target):
                    started = self.live.write("seek", {"target": target})
                    self.assertTrue(started["running"])
                    for _ in range(180):
                        stopped = self.advance(1000)
                        if not stopped["running"]:
                            break
                    self.assertEqual(stopped["fast_forward"], dict(target=target, state="reached", event=expected[target]))
                    stamp = expected[target]["time_ms"]
                    self.assertEqual((stopped["time_ms"], stopped["running"], stopped["rate"]), (stamp, False, 1))
                    self.assertEqual(self.advance(2000)["time_ms"], stamp)
                    with self.live.lock:
                        self.assertEqual(self.live.worker.call("FRAME"), reference.call(f"ADVANCE {stamp}"))
                    self.live.write("clock", {"running": True})
                    self.assertEqual(self.advance(1250)["time_ms"], stamp + 1250)
                    self.live.write("clock", {"running": False})

        past = self.live.write("seek", {"target": "egg"})
        self.assertEqual(past["fast_forward"], dict(target="egg", state="already", event=expected["egg"]))
        self.assertEqual(past["time_ms"], expected["excavation"]["time_ms"] + 1250)
        self.assertEqual(list(self.live.saves.rglob("*.sqlite")), [])

    def test_native_clock_save_metadata_and_exact_resume(self):
        started = self.live.write("new", {})
        self.assertTrue(started["running"])
        self.assertEqual((started["rate"], started["time_ms"]), (1, 0))
        first = self.live.read("view", {})
        self.assertEqual([(ant["caste"], ant["stage"]) for ant in first["ants"]], [("Queen", "Adult")])
        self.assertEqual(self.advance(750)["time_ms"], 750)
        self.live.write("clock", {"running": False})
        self.assertEqual(self.advance(2000)["time_ms"], 750)
        self.assertEqual(list(self.live.saves.rglob("*.sqlite")), [])

        self.live.write("clock", {"running": True, "rate": 86400})
        for _ in range(16):
            self.advance(250)
        halted = self.live.write("clock", {"running": False})
        self.assertEqual(halted["time_ms"], 4 * DAY + 750)
        view = self.live.read("view", {"group": "birth"})
        self.assertEqual(view["events"][0]["kind"], "AntBorn")
        self.assertEqual(view["events"][0]["time_ms"], 4 * DAY)
        self.assertTrue(view["terrain"]["openings"])

        name = "First nest \u4e00"
        self.live.write("save", {"name": name})
        path = self.live.saves / (name + ".sqlite")
        saved = self.live.read("saves", {})["entries"][0]
        self.assertEqual((saved["world_id"], saved["time_ms"], saved["size_bytes"], saved["facts"]),
                         (started["world_id"], halted["time_ms"], path.stat().st_size, int(view["cursor"])))
        original = sha256(path.read_bytes()).digest()
        for invalid in ("../escape", "CON", "nested/path"):
            with self.assertRaises(ValueError):
                self.live.write("save", {"name": invalid})
        with self.assertRaises(ValueError):
            self.live.write("save", {"name": name})
        target = 5 * DAY
        with self.live.lock:
            expected = self.live.worker.call(f"ADVANCE {target}")
        restored = self.live.write("load", {"name": name})
        self.assertEqual((restored["world_id"], restored["time_ms"], restored["rate"], restored["running"]),
                         (started["world_id"], halted["time_ms"], 1, False))
        self.assertEqual(sha256(path.read_bytes()).digest(), original)

        # Moving the exported save in Explorer must not break the loaded world.
        path.rename(path.with_name("Moved in Explorer.sqlite"))
        with self.live.lock:
            continued = self.live.worker.call(f"ADVANCE {target}")
            self.assertEqual(continued, expected)
            self.live.publish(continued)
        self.live.write("save", {"name": "Moved in Explorer", "overwrite": True})
        [updated] = self.live.read("saves", {})["entries"]
        self.assertEqual(updated["time_ms"], target)
        with LiveSession(BINARY, self.live.saves, clock=lambda: self.now) as restarted:
            self.assertIsNone(restarted.read("status", {})["world_id"])
            self.assertEqual(restarted.write("load", {"name": "Moved in Explorer"})["time_ms"], target)
            self.assertEqual(restarted.worker.call("FRAME"), continued)
        catalogue = Catalog(self.folder / "replay")
        worlds, _, _ = catalogue.browse(catalogue.register(path.with_name("Moved in Explorer.sqlite")))
        self.assertEqual((worlds[0]["world_id"], worlds[0]["end_ms"], worlds[0]["facts"]),
                         (updated["world_id"], target, updated["facts"]))
        broken = self.live.saves / "Broken.sqlite"
        broken.write_bytes(b"not SQLite")
        with self.assertRaises((sqlite3.DatabaseError, ValueError)):
            self.live.write("load", {"name": "Broken"})
        self.assertEqual(self.live.read("status", {})["time_ms"], target)

    def test_shorter_worker_timing_and_completed_actions_persist(self):
        with self.assertRaisesRegex(ValueError, "Unknown worker timing"):
            self.live.write("new", {"timing": "invalid"})
        self.live.write("new", {"timing": "shorter"})
        self.live.write("clock", {"running": False})
        with self.live.lock:
            saved_frame = self.live.worker.call(f"ADVANCE {46 * DAY}")
            self.live.publish(saved_frame)
        view = self.live.read("view", {})
        self.assertEqual((view["schema_version"], view["physics"]), (24, 31))
        self.assertEqual(view["worker_activity_timing"], {"check_ms": 900000, "minimum_program_ms": 3600000})
        self.assertTrue({"NestIngested", "NutritionTransferred", "BiologicalObservation"} <=
                        {event["kind"] for event in view["actions"]})
        cursor = min(int(event["id"]) for event in view["actions"]) - 1
        native = read_live_events(self.live.worker.call(f"FACTS_AFTER {cursor}"), self.live.frame)
        first_page = {event["id"]: event for event in native}
        for event in view["actions"]:
            self.assertEqual(event, first_page[event["id"]])
            self.assertIn(event["outcome"], ("Success", "Partial"))
            if event.get("action"):
                self.assertEqual(event["action"]["phase"], "Completed")
            else:
                self.assertGreater(sum(event["mass_ug"]), 0)
        self.assertEqual(self.live.worker.call("FRAME"), saved_frame)

        self.assertEqual(self.live.worker.call("CHECK_LEDGERS"), b"")
        self.live.write("save", {"name": "Shorter timing"})
        expected = self.live.worker.call(f"ADVANCE {47 * DAY}")
        self.live.write("load", {"name": "Shorter timing"})
        self.assertEqual(self.live.worker.call("FRAME"), saved_frame)
        self.assertEqual(self.live.read("view", {})["actions"], view["actions"])
        self.assertEqual(self.live.worker.call(f"ADVANCE {47 * DAY}"), expected)
        self.assertEqual(self.live.worker.call("CHECK_LEDGERS"), b"")

        catalogue = Catalog(self.folder / "replay")
        archive = catalogue.register(self.live.saves / "Shorter timing.sqlite")
        worlds, _, _ = catalogue.browse(archive)
        self.assertEqual(worlds[0]["settings"]["physics"], 31)

    def test_local_nest_activity_is_opt_in_and_restorable(self):
        with self.assertRaisesRegex(ValueError, "Unknown local nest activity"):
            self.live.write("new", {"local_nest_activity": "yes"})
        self.live.write("new", {"local_nest_activity": True})
        self.live.write("clock", {"running": False})
        with self.live.lock:
            recorded = self.live.worker.call(f"ADVANCE {60 * DAY}")
            self.live.publish(recorded)
        view = self.live.read("view", {})
        self.assertTrue(view["local_nest_activity"])
        self.assertEqual((view["schema_version"], view["physics"]), (25, 32))
        self.live.write("save", {"name": "Resting sites"})
        expected = self.live.worker.call(f"ADVANCE {61 * DAY}")
        self.live.write("load", {"name": "Resting sites"})
        self.assertEqual(self.live.worker.call("FRAME"), recorded)
        self.assertEqual(self.live.worker.call(f"ADVANCE {61 * DAY}"), expected)
        self.assertEqual(self.live.worker.call("CHECK_LEDGERS"), b"")

    def test_loopback_origin_and_folder_control(self):
        api = ReadAPI(Catalog(self.folder / "cache"))
        server = self.enterContext(bind(api, 0, self.live))
        server_thread = Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        self.addCleanup(server_thread.join)
        self.addCleanup(server.shutdown)
        port = server.server_port
        origin = f"http://127.0.0.1:{port}"

        def request(method, route, *, from_origin=origin, host=None):
            client = HTTPConnection("127.0.0.1", port, timeout=10)
            try:
                headers = {"Content-Type": "application/json"}
                if from_origin:
                    headers["Origin"] = from_origin
                if host:
                    headers["Host"] = host
                client.request(method, "/api/v1/" + route, b"{}" if method == "POST" else None, headers)
                response = client.getresponse()
                return response.status, json.loads(response.read())
            finally:
                client.close()

        self.assertEqual(request("GET", "live/status")[1]["data"]["world_id"], None)
        self.assertEqual(request("POST", "live/new", from_origin=None)[0], 403)
        self.assertEqual(request("POST", "live/new", from_origin="https://example.test")[0], 403)
        self.assertEqual(request("POST", "live/new", host="example.test")[0], 403)
        self.assertEqual(request("GET", "live/status")[1]["data"]["world_id"], None)
        self.assertEqual(request("POST", "live/new")[0], 200)
        self.assertEqual(request("GET", "catalog"), (200, {"schema": "antworld.observation.v1", "data": []}))
        with patch("op0.live.open_folder") as opener:
            self.assertEqual(request("POST", "live/folder")[0], 200)
            opener.assert_called_once_with(self.live.saves)
