"""Verify the live clock, native continuation and local save controls."""

from contextlib import closing
from hashlib import sha256
from http.client import HTTPConnection
import json
from math import dist
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
from op0.codec import CASTES, KINDS, checkpoint, decode_fact
from op0.index import Catalog
from op0.live import ROOT, LiveSession, NativeCore, core_path, read_live_events
from op0.query import HOUR, ReadAPI
from op0.server import bind
from tools.compare_m0_worker_rhythm import facts


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

    def test_observatory_presets_preserve_native_geometry_and_resources(self):
        if not self.live.core().observatory:
            self.skipTest("The native core predates the M1 observatory")
        for name in ("open", "plugged", "absent"):
            with self.subTest(name=name):
                self.live.write("observatory", {"preset": name})
                self.live.write("clock", {"running": False})
                view = self.live.read("view", {})
                volume = self.live.read("volume", {"epoch": str(view["epoch"])})
                self.assertEqual((view["physics"], view["schema_version"], view["seed"]), (36, 29, "2"))
                self.assertEqual(view["external_supply"], name != "absent")
                self.assertEqual(bool(view["terrain"]["openings"]), name != "plugged")
                self.assertEqual((volume["world_id"], volume["revision"]), (view["world_id"], view["terrain"]["revision"]))
                self.assertEqual(len(view["ants"]), 1)
                with self.assertRaises(ValueError):
                    self.live.read("volume", {"epoch": str(view["epoch"] - 1)})

    def test_reachable_berth_version_and_readonly_history_survive_restore(self):
        worker = self.live.core()
        if not worker.observatory:
            self.skipTest("The native core predates the M1 experiment")
        self.live.install(worker.call("NEW_OBSERVATORY 250 2 250 80 open 1955 reachable finite"), running=False)
        native = worker.call(f"ADVANCE {49 * DAY}")
        self.live.publish(native)
        frame = self.live.frame
        self.assertEqual((frame["schema"], frame["physics"]), (30, 37))
        self.assertTrue(frame["flags"]["founding_habitat"]["alternate_berth"])
        options = {"epoch": str(self.live.epoch)}
        while True:
            timeline = self.live.read("chronicle", options)
            if timeline["through"] == timeline["cursor"]:
                break
        milestones = timeline["landmarks"]
        egg = self.live.read("fact", dict(options, id=milestones["egg"]["id"]))
        self.assertEqual(egg, milestones["egg"])
        self.assertEqual(egg["kind"], "AntBorn")
        life = self.live.read("life", dict(options, id=egg["actor"]))
        self.assertEqual(life["lifecycle"][0], egg)
        self.assertEqual(worker.call("FRAME"), native)
        self.live.write("save", {"name": "M1 reachable"})
        expected = worker.call(f"ADVANCE {50 * DAY}")
        self.live.write("load", {"name": "M1 reachable"})
        self.assertEqual(worker.call("FRAME"), native)
        self.assertEqual(worker.call(f"ADVANCE {50 * DAY}"), expected)
        self.assertEqual(worker.call("CHECK_LEDGERS"), b"")

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

    def test_foundress_habitat_climate_changes_body_loss_and_hatching(self):
        core = self.live.core()
        if not core.founding_habitat:
            self.skipTest("Build the native live Core with founding habitat")
        results = {}
        for temperature, humidity in ((225, 80), (250, 80), (250, 60)):
            self.live.write("habitat", {"temperature": temperature, "humidity": humidity})
            view = self.live.read("view", {})
            self.assertEqual((view["physics"], view["schema_version"], view["rate"]), (36, 29, 1))
            [queen] = view["ants"]
            self.assertEqual(queen["caste"], "Queen")
            self.assertEqual(queen["position_m"], view["habitat"]["brood_site_m"])
            self.assertNotEqual(queen["position_m"], view["colonies"][0]["position_m"])
            cut = checkpoint(core.call(f"ADVANCE {2 * DAY}"))
            loss = cut["ants"][int(queen["id"])]["lost_water_ug"]
            core.call(f"ADVANCE {26 * DAY}")
            hatch = core.call("FIND_MILESTONE hatch")
            results[temperature, humidity] = (view["climate"], view["worker_activity_timing"], loss,
                                              decode_fact(hatch)[1].time if hatch else None)
            self.assertEqual(core.call("CHECK_LEDGERS"), b"")
        cool, warm, dry = (results[regime] for regime in ((225, 80), (250, 80), (250, 60)))
        self.assertGreater(cool[1]["check_ms"], warm[1]["check_ms"])
        self.assertEqual((cool[3], warm[3]), (247 * DAY // 10, 207 * DAY // 10))
        self.assertEqual(dry[0]["larva_loss_ug_day"], 2 * warm[0]["larva_loss_ug_day"])
        self.assertEqual(dry[2], 2 * warm[2])
        self.assertIsNone(dry[3])
        for invalid in ({"temperature": 17}, {"soil_plug": 1}, {"trail_half_life": 100}, {"seed": 0}):
            with self.assertRaises(ValueError):
                self.live.write("habitat", {"temperature": 250, "humidity": 80} | invalid)

    def test_founding_habitat_collects_and_restores_real_history(self):
        if not self.live.core().founding_habitat:
            self.skipTest("Build the native live Core with founding habitat")
        self.live.write("habitat", {"temperature": 250, "humidity": 80, "trail_half_life": 1955})
        self.live.write("clock", {"running": False})
        core = self.live.worker
        self.assertEqual(self.live.read("view", {})["surface"]["trail_half_life_s"], 1955)
        saved = core.call(f"ADVANCE {60 * DAY}")
        saved_cut = checkpoint(saved)
        self.live.publish(saved)
        witnessed = {"FoodCollected", "FoodDelivered", "Moved", "StageChanged", "BiologicalObservation",
                     "RecruitmentCue", "RecruitmentObserved", "RecruitmentActivated", "FoundressWaterIngested"}
        events = [event.packet() for event in facts(core, saved_cut["cursor"]) if KINDS[event.kind] in witnessed]
        food = decode_fact(core.call("FIND_MILESTONE delivery"))[1].packet()
        water = decode_fact(core.call("FIND_MILESTONE water"))[1].packet()
        self.assertGreater(food["mass_ug"][0], 0)
        self.assertEqual(water["mass_ug"][:2], (0, 0))
        self.assertGreater(water["mass_ug"][2], 0)
        self.assertTrue(any(e["kind"] == "FoundressWaterIngested" and e["mass_ug"][2] for e in events))
        for identifier in (food["actor"], water["actor"]):
            history = [e for e in events if e["actor"] == identifier]
            born = next(e for e in history if e["kind"] == "StageChanged" and e["stage"] == "Adult")
            out = next(e for e in history if e["kind"] == "Moved" and e["position_m"][1] >= 0)
            collect = next(e for e in history if e["kind"] == "FoodCollected")
            return_to_nest = next(e for e in history if e["kind"] == "FoodDelivered")
            self.assertLess(born["time_ms"], out["time_ms"])
            self.assertLess(out["time_ms"], collect["time_ms"])
            self.assertLess(collect["time_ms"], return_to_nest["time_ms"])
            self.assertLess(return_to_nest["position_m"][1], 0)
        self.assertTrue(any(e.get("trail_deposited_units", 0) > 0 for e in events))
        self.assertTrue(core.call("FIND_MILESTONE patrol"))
        self.live.write("save", {"name": "Founding habitat"})
        target = 61 * DAY
        expected = core.call(f"ADVANCE {target}")
        expected_facts = core.call(f"FACTS_AFTER {saved_cut['cursor'] - 16}")
        self.live.write("load", {"name": "Founding habitat"})
        self.assertEqual(core.call("FRAME"), saved)
        core.call(f"ADVANCE {60 * DAY + 15 * MINUTE}")
        self.assertEqual(core.call(f"ADVANCE {target}"), expected)
        self.assertEqual(core.call(f"FACTS_AFTER {saved_cut['cursor'] - 16}"), expected_facts)
        self.assertEqual(core.call("CHECK_LEDGERS"), b"")

    def test_recruited_worker_delivers_and_entrance_contact_is_linked_to_an_arrival(self):
        with closing(NativeCore(BINARY, self.folder)) as core:
            if not core.founding_habitat:
                self.skipTest("Build the native live Core with founding habitat")
            core.call("NEW_HABITAT 201 3 250 80 open 60")
            frame = core.call(f"ADVANCE {90 * DAY}")
            cut = checkpoint(frame)
            activation = decode_fact(core.call("FIND_MILESTONE recruitment"))[1]
            contact = decode_fact(core.call("FIND_MILESTONE entrance-contact"))[1]
            journal = {event.id: event for event in facts(core, cut["cursor"])}
            cue, observation = journal[activation.aux], journal[activation.id - 1]
            self.assertEqual((KINDS[cue.kind], KINDS[observation.kind]), ("RecruitmentCue", "RecruitmentObserved"))
            self.assertEqual((cue.actor, observation.actor), (activation.related, activation.actor))
            self.assertNotEqual(cue.actor, activation.actor)
            self.assertGreater(journal[cue.payload].mass[0], 0)
            self.assertTrue(any(e.actor == activation.actor and e.id > activation.id and e.mass[0] > 0 and
                                KINDS[e.kind] == "FoodDelivered" for e in journal.values()))
            arrival = journal[contact.id - 1]
            self.assertEqual((KINDS[arrival.kind], arrival.actor, arrival.source), ("Moved", contact.related, contact.source))
            self.assertLessEqual(dist(arrival.position, contact.position), cut["contact_m"] + 1e-12)
            self.assertNotEqual(contact.actor, contact.related)
            save_id = "1" * 32
            core.call(f"SAVE {save_id}")
            self.assertEqual(core.call(f"LOAD {save_id} {cut['world']}"), frame)
            self.assertEqual(decode_fact(core.call("FIND_MILESTONE entrance-contact"))[1], contact)
            self.assertEqual(core.call("CHECK_LEDGERS"), b"")

    def test_only_a_reachable_soil_plug_can_be_opened_in_the_comparison(self):
        with closing(NativeCore(BINARY, self.folder)) as core:
            if not core.founding_habitat:
                self.skipTest("Build the native live Core with founding habitat")
            for access in ("plugged", "blocked"):
                with self.subTest(access=access):
                    initial = checkpoint(core.call(f"NEW_HABITAT 201 2 250 80 {access} 1955"))
                    self.assertFalse(initial["edits"])
                    final = checkpoint(core.call(f"ADVANCE {75 * DAY}"))
                    worker = decode_fact(core.call("FIND_MILESTONE worker"))[1].packet()
                    self.assertGreater(worker["time_ms"], 0)
                    exit_fact = core.call("FIND_MILESTONE exit")
                    delivery = core.call("FIND_MILESTONE delivery")
                    if access == "blocked":
                        self.assertEqual((exit_fact, delivery), (b"", b""))
                    else:
                        exit_time = decode_fact(exit_fact)[1].time
                        cap = next(e for e in final["edits"] if e["box_q"][4] == initial["geometry"]["solid"][4])
                        self.assertLess(cap["time_ms"], exit_time)
                        self.assertLess(exit_time, decode_fact(delivery)[1].time)
                        self.assertTrue(any(e.payload == cap["parcel"] and KINDS[e.kind] == "SoilDropped"
                                            for e in facts(core, final["cursor"])))
                    self.assertEqual(core.call("CHECK_LEDGERS"), b"")

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

    def test_next_birth_skips_the_first_and_continues_after_restore(self):
        if not self.live.core().next_milestone:
            self.skipTest("Build the native Core with next-event seeking")
        with patch("op0.live.randbits", return_value=270001):
            self.live.write("new", {})

        def seek_birth(occurrence):
            started = self.live.write("seek", {"target": "egg", "occurrence": occurrence})
            self.assertEqual(started["fast_forward"]["state"], "seeking")
            for _ in range(180):
                stopped = self.advance(1000)
                if not stopped["running"]:
                    break
            hit = stopped["fast_forward"]
            self.assertEqual(hit["state"], "reached")
            self.assertEqual((stopped["time_ms"], stopped["rate"]), (hit["event"]["time_ms"], 1))
            return hit["event"]

        first = seek_birth("first")
        second = seek_birth("next")
        self.assertEqual((first["time_ms"], second["time_ms"]), (4 * DAY, 4 * DAY + 2 * HOUR))
        self.assertGreater(int(second["id"]), int(first["id"]))
        before = self.live.status()
        with self.assertRaisesRegex(ValueError, "Choose the first or next event"):
            self.live.write("seek", {"target": "egg", "occurrence": "previous"})
        self.assertEqual(self.live.status(), before)
        self.live.write("save", {"name": "After second birth"})
        third = seek_birth("next")
        self.assertGreater(int(third["id"]), int(second["id"]))
        frame = self.live.worker.call("FRAME")
        self.live.write("load", {"name": "After second birth"})
        self.assertEqual(seek_birth("next"), third)
        self.assertEqual(self.live.worker.call("FRAME"), frame)

    def test_next_exit_uses_current_positions_and_keeps_same_timestamp_matches(self):
        if not self.live.core().next_milestone:
            self.skipTest("Build the native Core with next-event seeking")
        # These two recorded exits were committed in the same atomic timestamp.
        events = []
        with ZipFile(WITNESS) as witness, witness.open("facts.bin") as stream:
            for _, raw in prefixed(stream):
                _, fact = decode_fact(raw)
                if fact.id in (52416, 52420):
                    events.append(fact.packet())
                if fact.id == 52420:
                    break
        self.assertEqual([event["kind"] for event in events], ["Moved", "Moved"])
        first, second = events
        self.assertEqual(first["time_ms"], second["time_ms"])
        stamp = first["time_ms"]
        with patch("op0.live.randbits", return_value=270001):
            self.live.write("new", {})
        self.live.write("clock", {"running": False})
        self.live.publish(self.live.worker.call(f"ADVANCE {stamp - 1}"))

        request = {"target": "exit", "occurrence": "next"}
        started = self.live.write("seek", request)
        self.assertEqual(started["fast_forward"]["state"], "seeking")
        stopped = self.advance(1000)
        self.assertEqual(stopped["fast_forward"]["event"], first)
        frame = self.live.worker.call("FRAME")
        next_stop = self.live.write("seek", request)
        self.assertEqual(next_stop["fast_forward"], dict(request, state="reached", event=second))
        self.assertEqual((next_stop["time_ms"], next_stop["running"], next_stop["rate"]), (stamp, False, 1))
        self.assertEqual(self.live.worker.call("FRAME"), frame)

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
