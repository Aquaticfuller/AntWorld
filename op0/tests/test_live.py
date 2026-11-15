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
from op0.index import Catalog
from op0.live import ROOT, LiveSession, NativeCore, core_path
from op0.query import ReadAPI
from op0.server import bind


BINARY = Path(os.environ.get("M0_LIVE_CORE", core_path())).resolve()


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
        source = ROOT / "experiments/m0/portable-demo/borisovka-shaft-1-slots.zip"
        with ZipFile(source) as witness, closing(NativeCore(BINARY, self.folder)) as core:
            core.call("NEW 270001 1")
            self.assertEqual(sha256(core.call(f"ADVANCE {90 * DAY}")).digest(),
                             sha256(witness.read("final.frame")).digest())
        self.assertEqual(list(self.folder.iterdir()), [])

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
