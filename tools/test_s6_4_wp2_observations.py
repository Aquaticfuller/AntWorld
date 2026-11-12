"""Regression tests for observation time, causal joins and censoring."""

from collections import defaultdict
import unittest

from analyze_s6_4_wp2 import Individual, Trace, body_balance, coverage
from read_s6_4_rm02_sidecar import Fact
from run_s6_4_wp2 import matrix


class Capture:
    def __init__(self):
        self.tables = defaultdict(list)

    def row(self, table, row):
        self.tables[table].append(row)


def event(number, time, kind, source=0, payload=0, mass=(0, 0, 0, 0), care=()):
    return Fact(number, time, source, number, 1, payload, 0, kind, mass, 3, "Success", care, (0., 0., 0.), 1)


class ObservationTests(unittest.TestCase):
    def test_program_time_does_not_fill_unobserved_activity(self):
        ant = Individual("adult", "worker", (0., 0., 0.), rates=(1, 1, 1, 1, 1), program="Nurse")
        ant.advance(100, 10)
        self.assertEqual(ant.program_ms["Nurse"], 90)
        self.assertEqual(coverage([(0, 20, "Walk"), (30, 50, "Inactive"), (40, 55, "Inactive")], 10, 100),
                         dict(known_active_ms=10, known_inactive_ms=25, timed_locomotor_ms=10, unobserved_activity_ms=55))
        with self.assertRaisesRegex(ValueError, "overlapping active and inactive"):
            coverage([(0, 20, "Walk"), (10, 20, "Inactive")], 0, 100)

    def test_energy_and_water_balance_use_separate_committed_fluxes(self):
        ant = Individual("adult", "queen", (0., 0., 0.))
        ant.initial_state = dict(energy_nj=100, body_water_ug=60, dissipated_nj=0, exported_nj=0, water_lost_ug=0)
        ant.pulse.update(carb=5, water=20)
        ant.work["egg_water"] = 10
        after = dict(energy_nj=85, body_water_ug=65, dissipated_nj=15, exported_nj=10, water_lost_ug=5,
                     yield_nj_per_ug=2)
        self.assertTrue(body_balance(ant, after))
        self.assertFalse(body_balance(ant, after | {"body_water_ug": 70}))

    def test_started_care_is_right_censored_and_unmatched_feed_is_rejected(self):
        out = Capture()
        trace = Trace(dict(mode="test"), dict(horizon_ms="100"), dict(world_id="world", world=(1, 1)),
                      {1: Individual("adult", "queen", (0., 0., 0.)), 2: Individual("larva", "worker", (0., 0., 0.))},
                      out)
        trace.fact(event(1, 10, "BiologicalObservation", care=(2, 5, 2, 9, 10, 1, 0., 0., 0.)))
        with self.assertRaisesRegex(ValueError, "matching conserved gift"):
            trace.custody_event(event(2, 20, "BiologicalObservation", source=10, mass=(0, 2, 0, 0)),
                                "FeedBrood", "Completed", 2, 10)
        trace.fact(event(3, 40, "BiologicalObservation", care=(1, 3, 2, 10, 40, 0, 0., 0., 0.)))
        trace.finish()
        statuses = {r["state"]: r["endpoint_status"] for r in out.tables["open_bouts"]}
        self.assertEqual(statuses, {"SELECTED_ONLY": "UNOBSERVED", "STARTED": "RIGHT_CENSORED"})
        self.assertEqual(out.tables["individuals"][0]["known_active_ms"], 90)

    def test_frozen_case_identities(self):
        cases = list(matrix())
        self.assertEqual(len(cases), len({c["case"] for c in cases}))
        self.assertEqual({mode: sum(c["mode"] == mode for c in cases) for mode in ("activity", "integrated", "b01", "b02")},
                         {"activity": 48, "integrated": 24, "b01": 36, "b02": 120})


if __name__ == "__main__":
    unittest.main()
