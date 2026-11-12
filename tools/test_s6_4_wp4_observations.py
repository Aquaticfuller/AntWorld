"""Regression checks for independent WP-4 budget decoding and short probes."""

import argparse
from pathlib import Path
import unittest

from read_s6_4_rm02_sidecar import Fact
from s6_4_wp4_budget import Individual
from verify_s6_4_wp3 import rows


ROOT = Path(__file__).resolve().parents[1]
HOUR = 3_600_000
DAY = 24 * HOUR


class AccountChecks(unittest.TestCase):
    def setUp(self):
        entered = Fact(1, 0, 0, 1, 1, 0, 0, "AntSeeded", (0, 0, 0, 0), 3, "Success", ())
        self.mother = Individual(dict(born_ms=0, initial_carbs_ug=0, initial_protein_ug=21, initial_crop_water_ug=0,
                                      initial_other_ug=0), entered)

    def test_body_water_is_not_crop_water(self):
        self.mother.apply("egg_export", (0, 20, 200, 0))
        self.assertEqual(self.mother.remaining, (0, 1, 0, 0))
        self.assertEqual(self.mother.flows["egg_export"], (0, 20, 200, 0))

    def test_invalid_crop_reconstruction_fails(self):
        with self.assertRaisesRegex(ValueError, "overdraw"):
            self.mother.apply("egg_export", (0, 22, 200, 0))


class ArchivedAssays(unittest.TestCase):
    def test_gift_phases_and_zero_resolution(self):
        uptake = rows(ANALYSIS / "uptake.csv")
        inputs = rows(ANALYSIS / "fixture_inputs.csv")
        for arm, time in (("before", 6 * HOUR), ("on", 12 * HOUR)):
            key = f"pulse-{arm}-1-legacy-1"
            transfer, = (r for r in inputs if r["case"] == key)
            positive, = (r for r in uptake if r["case"] == key and r["status"] == "positive")
            self.assertEqual(transfer["resolution"], "NutritionTransferred")
            self.assertEqual(int(positive["at_ms"]), time)
            self.assertGreater(int(positive["event_id"]), int(transfer["event_id"]))
            self.assertEqual(tuple(int(positive[f"uptake_{part}_ug"]) for part in ("carbs", "protein", "water")),
                             (60, 0, 20))
        sham, = (r for r in inputs if r["case"] == "pulse-sham-1-legacy-1")
        self.assertEqual((sham["resolution"], sham["outcome"], int(sham["committed_carbs_ug"])),
                         ("ActionRejected", "EmptyInventory", 0))
        self.assertFalse(any(r["case"] == "pulse-none-1-legacy-1" for r in inputs))

    def test_clocks_keep_original_deaths_and_timing_sentinels(self):
        states = rows(ANALYSIS / "offspring_stages.csv")
        for profile, warm in (("borisovka", 1_442_880_000), ("st-petersburg", 1_356_480_000)):
            for arm in ("seed", "funded", "sentinel", "energy-tie"):
                case = f"clock-{arm}-0-{profile}-1"
                egg = next(r for r in states if r["case"] == case and r["stage"] == "egg")
                expected = ("transition", warm, "") if arm == "sentinel" else (
                    "death", warm if arm == "energy-tie" else 500_000_000, "energy_depleted")
                self.assertEqual((egg["endpoint"], int(egg["duration_ms"]), egg["death_cause"]), expected)

    def test_same_child_progression_and_negative_arms(self):
        inputs = rows(ANALYSIS / "fixture_inputs.csv")
        stages = rows(ANALYSIS / "offspring_stages.csv")
        for arm in ("full", "low-protein", "none"):
            case = f"brood-{arm}-3-legacy-1"
            invalid, = (r for r in inputs if r["case"] == case and int(r["execute_ms"]) == 2 * DAY + 1)
            self.assertEqual((invalid["resolution"], invalid["outcome"]), ("ActionRejected", "InvalidStage"))
            individual = [r for r in stages if r["case"] == case and r["entity"] == invalid["recipient"]]
            self.assertEqual([r["stage"] for r in individual], ["egg", "larva", "pupa", "adult"] if arm == "full"
                             else ["egg", "larva"])
            if arm != "full":
                self.assertEqual(individual[-1]["endpoint"], "death")

    def test_all_scientific_roots_are_retained(self):
        scientific = rows(ROOT / "research/s6_4_wp4/SCIENTIFIC_CLOSURE.csv")
        self.assertEqual({r["BR"] for r in scientific}, {f"BR-{i:02}" for i in range(1, 10)})
        self.assertEqual({r["BiologicalStatus"] for r in scientific}, {"BLOCKED"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("analysis", type=Path)
    ANALYSIS = parser.parse_args().analysis
    unittest.main(argv=[__file__])
