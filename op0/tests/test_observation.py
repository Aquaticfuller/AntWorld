"""Cross-check projections against published canonical bytes and native stores."""

from contextlib import closing
from hashlib import sha256
import http.client
import json
import os
from pathlib import Path
import shutil
from struct import unpack_from
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from zipfile import ZipFile

from op0 import DAY, SCHEMA
from op0.archive import file_hash, pack
from op0.cli import DEMOS, ROOT, VERIFIED, api_get, default_catalog
from op0.codec import ArchiveError
from op0.geometry import clear_centers, slice_at
from op0.index import Catalog
from op0.locale import translator
from op0.query import ReadAPI
from op0.server import bind


def selected_facts(source, wanted):
    """Independent fixed-offset witness reader. No OP0 codec, SQLite index or UI."""
    result, total = {}, 0
    checksum = sha256()
    with ZipFile(source) as archive, archive.open("facts.bin") as data:
        while prefix := data.read(4):
            length, = unpack_from("<I", prefix)
            payload = data.read(length)
            if len(payload) != length:
                raise AssertionError("Truncated witness")
            eid, _, _, ms = unpack_from("<QQQQ", payload, 0)
            if eid in wanted:
                result[eid] = (ms, payload[65], *unpack_from("<QQQdddQQQQ", payload, 66))
            checksum.update(prefix)
            checksum.update(payload)
            total += 1
    return result, total, checksum.hexdigest()


class ObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = os.environ.get("OP0_TEST_CACHE")
        cls.temp = None if env else TemporaryDirectory(prefix="op0-tests-")
        cls.root = Path(env or cls.temp.name)
        cls.root.mkdir(parents=True, exist_ok=True)
        cls.catalog = default_catalog(cls.root / "indexes")
        cls.api = ReadAPI(cls.catalog)
        cls.entries = api_get(cls.api, "catalog")
        cls.demo = api_get(cls.api, f"archive/{cls.entries[0]['key']}")["worlds"][0]
        cls.path = DEMOS[0][0] / DEMOS[0][1]

    @classmethod
    def tearDownClass(cls):
        if cls.temp:
            cls.temp.cleanup()

    def get(self, operation, **params):
        return api_get(self.api, f"world/{self.demo['key']}/{operation}", **params)

    def test_catalogue_physics_identity_and_initial_snapshot(self):
        self.assertEqual(len(self.entries), 5)
        meta = self.get("meta")
        self.assertEqual((meta["world_id"], meta["settings"]["physics"], meta["settings"]["seed"]),
                         ("00000000-0000-0286-0000-000000018a61", 25, "1"))
        self.assertEqual(meta["archive_sha256"], file_hash(self.path))
        self.assertEqual(meta["integrity"], "VERIFIED_PUBLISHED")
        self.assertEqual((meta["end_ms"], meta["readiness"], meta["biological_status"], meta["b06"], meta["release"]),
                         (150 * DAY, "ENGINEERING_ONLY", "BIOLOGICAL_BLOCKED", "INSUFFICIENT", "FAIL"))
        start = self.get("state", time_ms=0)
        self.assertEqual(start["population"]["queens_alive"], ["2"])
        self.assertEqual(start["population"]["workers"], 0)
        self.assertEqual(start["ants"][0]["position_m"], [0, -.004, 0])
        tip = self.get("state", time_ms=150 * DAY)
        self.assertEqual((tip["population"]["workers"], tip["geometry_revision"]), (45, 66))
        before = self.get("state", time_ms=45 * DAY)
        self.assertEqual(before["population"]["workers"], 0)
        self.assertTrue(before["queens_last_sample"])
        series = self.get("series")
        self.assertEqual(len(series), 151)
        self.assertEqual(series[0]["time_ms"], 0)
        self.assertEqual(series[-1]["population"], tip["population"])

    def test_canonical_exact_facts_pagination_and_movement(self):
        picked = {5375, 9661, 9826, 9938, 10692, 10706, 17118, 668720}
        facts, total, digest = selected_facts(self.path, picked)
        self.assertEqual(total, self.demo["facts"])
        self.assertEqual(digest, self.get("meta")["member_sha256"]["facts.bin"])
        for eid, raw in facts.items():
            event = self.get("event", id=eid)
            self.assertEqual(event["time_ms"], raw[0])
            self.assertEqual(event["actor"], str(raw[2]) if raw[2] else None)
            self.assertEqual(event["resource"], str(raw[4]) if raw[4] else None)
            self.assertEqual(tuple(event["position_m"]), raw[5:8])
            self.assertEqual(tuple(event["mass_ug"]), raw[8:])
        for group in ("all", "care", "recruitment", "nutrition", "soil"):
            page = self.get("events", group=group, limit=2)
            second = self.get("events", group=group, after=page["next_after"], limit=3)
            ids = [int(f["id"]) for f in page["events"] + second["events"]]
            self.assertEqual(ids, sorted(set(ids)))
            self.assertEqual(len(ids), 5)
        self.assertEqual(self.get("event", id=9938)["kind"], "FoodDelivered")
        self.assertEqual(self.get("event", id=10706)["parcel"], self.get("event", id=10692)["parcel"])
        self.assertGreater(sum(self.get("event", id=9826)["mass_ug"]), 0)
        recruit = self.get("event", id=17118)
        cue = self.get("event", id=recruit["origin_fact"])
        self.assertEqual((cue["kind"], self.get("event", id=cue["origin_fact"])["kind"]),
                         ("RecruitmentCue", "FoodDelivered"))
        track = self.get("path", event=9938, id=4, limit=200)
        self.assertFalse(track["connected_segments"])
        self.assertGreater(len(track["points"]), 10)
        self.assertTrue(any(point["position_m"][1] < 0 for point in track["points"]))
        self.assertTrue(any(point["position_m"][1] == 0 for point in track["points"]))
        self.assertEqual([int(p["id"]) for p in track["points"]], sorted(int(p["id"]) for p in track["points"]))

    def test_life_history_nonobserved_states_and_early_cohort(self):
        at = self.get("ant", event=5375, id=5)
        self.assertEqual((at["mother"], at["status"], at["death_cause"]), ("2", "Dead", "Energy depleted"))
        self.assertGreater(at["sample"]["energy_nj"], 0)
        self.assertLess(at["sample"]["time_ms"], at["died_ms"])
        self.assertEqual(self.get("ant", time_ms=0, id=5)["stage"], "Not yet present")
        more = self.get("events", ant=4, group="care", limit=100)
        self.assertTrue(any(f["related"] == "4" for f in more["events"]))
        self.assertTrue(all("4" in (f["actor"], f["related"]) for f in more["events"]))
        cohort = self.get("cohort", time_ms=150 * DAY)
        self.assertIn("5", cohort["members"])
        self.assertIsNone(self.get("cohort", time_ms=DAY))
        self.assertEqual(cohort["size"], 4)

    def test_3d_geometry_uses_ordered_edits_and_event_boundaries(self):
        geometry = self.get("meta")["settings"]["geometry"]
        edit = self.get("event", id=10692)["geometry_edits"][0]
        x, y, z = edit["box_q"][:3]
        before = self.get("geometry", event=10691, layer_q=z, clearance=1)
        after = self.get("geometry", event=10692, layer_q=z, clearance=1)
        self.assertEqual((before["revision"], after["revision"]), (0, 1))
        left, bottom = geometry["solid"][:2]
        self.assertEqual(before["slice"]["rows"][y-bottom][x-left], "1")
        self.assertEqual(after["slice"]["rows"][y-bottom][x-left], "0")
        self.assertGreater(len(after["openings"]), 0)
        for axis in "xy":
            self.assertEqual(self.get("geometry", axis=axis, time_ms=46*DAY)["slice"]["axis"], axis)
        self.assertFalse(any("1" in row for row in after["slice"]["unloaded_body_clear"]))
        clearance = self.get("geometry", event=10692, layer_q=z+1, clearance=1)
        self.assertTrue(any("1" in row for row in clearance["slice"]["unloaded_body_clear"]))

    def test_negative_archive_and_repeated_access(self):
        item = self.entries[1]
        opened = api_get(self.api, f"archive/{item['key']}")
        world = opened["worlds"][0]
        state = api_get(self.api, f"world/{world['key']}/state", time_ms=150*DAY)
        self.assertEqual((state["ants"], state["population"]["workers"], state["population"]["queens_alive"]), ([], 0, []))
        self.assertTrue(api_get(self.api, f"archive/{item['key']}")["cached"])
        self.assertEqual(world["world_id"], self.demo["world_id"])  # Independently archived branches can share a world ID.
        self.assertNotEqual(world["key"], self.demo["key"])

    def test_default_physics25_comparison(self):
        opened = api_get(self.api, f"archive/{self.entries[4]['key']}")
        comparison = api_get(self.api, "compare", left=self.demo["key"], right=opened["worlds"][0]["key"], time_ms=150*DAY)
        left, right = comparison["worlds"]
        self.assertFalse(comparison["individual_alignment"])
        self.assertEqual((left["world"]["physics"], right["world"]["physics"]), (25, 25))
        self.assertEqual(comparison["settings"]["seed"]["status"], "same")
        self.assertEqual(comparison["settings"]["geometry"]["status"], "same")
        self.assertEqual(comparison["settings"]["initial_maternal"]["status"], "same")
        self.assertEqual(comparison["settings"]["initial_external_ug"]["status"], "same")
        left_rules, right_rules = (comparison["settings"]["ecological"][side] for side in ("left", "right"))
        self.assertNotEqual(left_rules["first_ration_ppm"], right_rules["first_ration_ppm"])
        self.assertNotEqual(left["cohort"], right["cohort"])

    def test_adjacent_physics_versions_use_their_original_settings(self):
        cases = (
            (ROOT / "experiments/s6_4_ecological_mechanism_closure/joint-repaired/borisovka-1-shaft-joint-balanced-5500.zip", 24),
            (ROOT / "experiments/s6_4_founding_cohort_release/hatch/borisovka-1-shaft-joint-balanced-5500-hatch-c111n0-r1.zip", 26),
        )
        for path, version in cases:
            with self.subTest(physics=version):
                index = self.catalog.register(path)
                meta = self.catalog.browse(index)[0][0]
                self.assertEqual(meta["settings"]["physics"], version)
                self.assertEqual(meta["settings"]["ecological"]["suppress_foundress_hatch_cue"], version == 26)
                self.assertEqual(meta["facts"], int(api_get(self.api, f"world/{meta['key']}/state", time_ms=meta["end_ms"])["cursor"]))

    def test_wrong_queries_and_http_is_local_and_read_only(self):
        for path in ("/api/v2/catalog", "/api/v1/world/../../meta",
                     f"/api/v1/world/{self.demo['key']}/state?time_ms=-5", f"/api/v1/world/{self.demo['key']}/events?limit=201",
                     f"/api/v1/world/{self.demo['key']}/events?group=madeup",
                     f"/api/v1/world/{self.demo['key']}/state?time_ms=1&time_ms=2"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.api.dispatch(path)
        with bind(self.api, 0) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with closing(http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=15)) as conn:
                    conn.request("GET", "/")
                    response = conn.getresponse()
                    self.assertEqual(response.status, 200)
                    self.assertIn(b"Simulation time", response.read())
                    conn.request("GET", "/api/v1/catalog")
                    self.assertEqual(json.loads(conn.getresponse().read())["schema"], SCHEMA)
                    conn.request("GET", "/", headers={"Host": "elsewhere.test"})
                    response = conn.getresponse()
                    self.assertEqual(response.status, 403)
                    response.read()
                    conn.request("POST", "/api/v1/catalog")
                    self.assertEqual(conn.getresponse().status, 501)
            finally:
                server.shutdown()
                thread.join()

    def test_source_tamper_missing_member_and_export_pack(self):
        with TemporaryDirectory(dir=self.root) as tmp:
            scratch = Path(tmp)
            bad = scratch / "bad.zip"
            with ZipFile(bad, "w") as z:
                z.writestr("case.json", "{}")
            with self.assertRaisesRegex(ArchiveError, "ZIP needs"):
                self.catalog.browse(self.catalog.register(bad))
            bad2 = scratch / "bad2.zip"
            with ZipFile(self.path) as z, ZipFile(bad2, "w") as out:
                for member in z.infolist():
                    if member.filename == "facts.bin":
                        out.writestr(member.filename, b"changed")
                    else:
                        out.writestr(member.filename, (z.read(member) if member.filename != "case.json" else b"{}"))
            with self.assertRaisesRegex(ArchiveError, "Member hash mismatch"):
                self.catalog.browse(self.catalog.register(bad2))
            absent = DEMOS[1][0] / DEMOS[1][1]
            with ZipFile(absent) as z:
                for filename in ("initial.chk", "final.frame", "facts.bin"):
                    with z.open(filename) as src, (scratch / filename).open("wb") as dest:
                        shutil.copyfileobj(src, dest)
            exported = scratch / "packed.zip"
            pack(scratch, exported)
            other, _, _ = self.catalog.browse(self.catalog.register(exported))
            self.assertIsNone(other[0]["scenario"])
            self.assertIsNone(other[0]["first_cohort"])
            self.assertEqual(other[0]["integrity"], "VERIFIED_RECEIPT")

    def test_sqlite_midpoint_with_wal_and_no_source_writes(self):
        filename = "borisovka-1-shaft-joint-balanced-5500-durable-split-corrected-c011n1-r1.zip"
        with TemporaryDirectory(dir=self.root) as tmp, ZipFile(VERIFIED / filename) as archive:
            directory = Path(tmp)
            names = ["midpoint.sqlite", "midpoint.sqlite-wal"]
            for name in names:
                with archive.open(name) as src, (directory / name).open("wb") as dest:
                    shutil.copyfileobj(src, dest)
            hashes = [(p, file_hash(p)) for p in map(directory.joinpath, names)]
            world = self.catalog.browse(self.catalog.register(hashes[0][0]))[0][0]
            self.assertEqual(world["archive_kind"], "SQLite v2")
            self.assertEqual(world["world_id"], self.demo["world_id"])
            self.assertGreater(world["end_ms"], 0)
            self.assertLess(world["end_ms"], 150*DAY)
            state = api_get(self.api, f"world/{world['key']}/state", time_ms=world["end_ms"])
            self.assertEqual(state["cursor"], str(world["facts"]))
            self.assertEqual(state["population"], self.get("state", time_ms=world["end_ms"])["population"])
            self.assertEqual(hashes, [(p, file_hash(p)) for p, _ in hashes])
            self.assertFalse((directory / "midpoint.sqlite-shm").exists())

    @unittest.skipUnless(os.environ.get("OP0_LEGACY_CLI"), "Set OP0_LEGACY_CLI to the native legacy fixture builder")
    def test_native_legacy_published_store(self):
        with TemporaryDirectory(dir=self.root) as tmp:
            source = Path(tmp) / "legacy.sqlite"
            result = subprocess.run([os.environ["OP0_LEGACY_CLI"], str(source)], capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            initial_hash = file_hash(source)
            meta = self.catalog.browse(self.catalog.register(source))[0][0]
            self.assertEqual((meta["archive_kind"], meta["settings"]["physics"], meta["end_ms"]), ("SQLite v1", 9, 1902))
            self.assertEqual(meta["facts"], 3)
            state = api_get(self.api, f"world/{meta['key']}/state", time_ms=1902)
            self.assertEqual(state["population"]["workers"], 1)
            self.assertEqual(initial_hash, file_hash(source))

    def test_terminal_with_real_world(self):
        result = subprocess.run([sys.executable, "-X", "utf8", "-m", "op0", "--cache", str(self.catalog.root), "tui", "--plain", "--language", "en"],
                                input="1\nd 150\ne 5375\na 5\nf care\nw\n2\nd 150\nq\n", capture_output=True,
                                text=True, encoding="utf-8", cwd=ROOT, timeout=100)
        self.assertEqual(result.returncode, 0, result.stderr)
        for pattern in ("Founding colony", "45 workers", "Energy depleted", "Tracking #5", "No external supply",
                        "0 workers", "VERIFIED_PUBLISHED"):
            self.assertIn(pattern, result.stdout)
        self.assertEqual(result.stderr, "")

    def test_terminal_switches_language_without_resetting_cursor(self):
        with TemporaryDirectory(dir=self.root) as tmp:
            cmd = [sys.executable, "-X", "utf8", "-m", "op0", "--cache", tmp, "tui", "--plain"]
            switched = subprocess.run(cmd, input="1\ne 5375\na 5\nlang zh-CN\nlang en\nlang zh-CN\nq\n",
                                      capture_output=True, text=True, encoding="utf-8", cwd=ROOT, timeout=100)
            self.assertEqual(switched.returncode, 0, switched.stderr)
            self.assertIn("Tracking #5", switched.stdout)
            self.assertIn(translator("zh-CN")("Tracking #{id}", id=5), switched.stdout)
            self.assertIn(translator("zh-CN")("Energy depleted") + "\n", switched.stdout)
            self.assertIn("AntDied", switched.stdout)
            self.assertEqual((Path(tmp)/"terminal-language.txt").read_text().strip(), "zh-CN")
            reopened = subprocess.run(cmd, input="q\n", capture_output=True, text=True, encoding="utf-8", cwd=ROOT, timeout=20)
            self.assertIn(translator("zh-CN")("Founding colony"), reopened.stdout)


class GeometryTests(unittest.TestCase):
    def test_half_open_rock_and_backfill(self):
        g = dict(solid=[0, 0, 0, 5, 5, 5], voids=[[1, 1, 1, 4, 4, 5]], rocks=[[2, 2, 2, 3, 3, 3]],
                 origin_m=[0, 0, 0], quantum_m=.001, body_half_q=1)
        first = slice_at(g, [], "z", 2)
        self.assertEqual(first["rows"][2], "10201")
        edits = [dict(kind=1, box_q=[1, 1, 1, 4, 4, 4]), dict(kind=0, box_q=[0, 2, 2, 3, 3, 3])]
        last = slice_at(g, edits, "z", 2)
        self.assertEqual(last["rows"][2], "00211")
        self.assertEqual(last["rows"][3], "11111")
        self.assertEqual(clear_centers(g, edits, last)[2], "00000")


if __name__ == "__main__":
    unittest.main()
