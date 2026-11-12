"""Check the WP-6A evidence, case design and exact-arithmetic falsifiers."""

from collections import Counter
import csv
from fractions import Fraction
import unittest

from wp6a_budget_screen import (
    CHECK_SEEDS, PACKAGE, POPULATIONS, PRIMARY_SEEDS, accessible_protein, legacy_warm,
    nominal, ordinary, ordinary_cases, read_envelope, results, screen, strict_positive_units, validate,
)


def rows(name):
    with (PACKAGE / name).open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


class Policy(unittest.TestCase):
    def test_every_root_retains_its_blocker(self):
        roots = rows("BR_EVIDENCE_AND_READINESS.csv")
        self.assertEqual([r["BR"] for r in roots], [f"BR-{n:02}" for n in range(1, 10)])
        self.assertTrue(all(r["HistoricalBiologicalStatus"] == "BIOLOGICAL_BLOCKED" for r in roots))
        self.assertTrue(all(r["CurrentSimulationReadiness"] in {"NOT_READY", "ENGINEERING_ONLY"} for r in roots))
        self.assertEqual([r["BR"] for r in roots if r["CurrentSimulationReadiness"] == "NOT_READY"],
                         ["BR-01", "BR-04", "BR-07"])
        grades = {"A", "B", "C", "D"}
        self.assertTrue(all(r["DirectConstraintGrade"] in grades and r["MechanismGrade"] in grades and
                            r["RetainedNegatives"] and r["MandatoryRemediation"] for r in roots))

    def test_all_scales_have_normal_and_adverse_endpoints(self):
        matrix = rows("MULTISCALE_ACCEPTANCE_MATRIX.csv")
        self.assertEqual({r["Scale"] for r in matrix}, {"Micro", "Colony", "LongTerm"})
        self.assertEqual(len({r["Id"] for r in matrix}), len(matrix))
        self.assertTrue(all(r["NegativeControl"] and r["PositiveOrNormal"] and r["UncertaintyOrDecision"] for r in matrix))


class Budget(unittest.TestCase):
    def setUp(self):
        self.envelope = read_envelope()
        self.profile = nominal(self.envelope)

    def test_original_budget_has_no_warm_hatch(self):
        for pop, clock in zip(POPULATIONS, (1_442_880_000, 1_356_480_000), strict=True):
            budget = legacy_warm(self.envelope, pop)
            self.assertEqual(budget["legacy_hatch_clock_ms"], clock)
            self.assertEqual(budget["legacy_energy_exhaustion_ms"], 500_000_000)
            self.assertEqual(budget["legacy_water_exhaustion_ms"], 720_000_000)
            self.assertEqual(budget["optimistic_hatch"], 0)

    def test_zero_energy_tie_cannot_hatch(self):
        profile = self.profile | {"borisovka_egg": Fraction(16), "egg_basal": Fraction(25_500_000)}
        record = screen(profile, "borisovka")
        self.assertEqual(record["hatch_energy_margin_nj"], 0)
        self.assertEqual(record["optimistic_hatch"], 0)
        self.assertEqual(strict_positive_units(10, 5), 3)
        self.assertEqual(strict_positive_units(-1, 5), 0)

    def test_closed_stock_and_contact_falsifiers(self):
        for case in results(self.envelope):
            if case["case"] in {"egg_fuel_stress", "egg_water_stress"}:
                self.assertEqual(case["optimistic_hatch"], 0)
            if case["case"] in {"no_care", "maternal_fuel_stress"}:
                self.assertEqual(case["ideal_path_with_mother_alive_to_emergence"], 0)
            if case["case"] == "nominal":
                self.assertEqual(case["opening_opportunities"], 12)
                self.assertEqual(case["optimistic_opening_eggs_upper_bound"], 12)
                self.assertEqual(case["minimum_local_rations"], 5)
                self.assertEqual(case["ideal_path_with_mother_alive_to_emergence"], 1)

    def test_locked_protein_is_bounded_and_finite(self):
        p = self.profile
        self.assertEqual(accessible_protein(p, 0, "F2"), 600)
        self.assertEqual(accessible_protein(p, 3, "F2"), 600)
        self.assertEqual(accessible_protein(p, Fraction(15, 2), "F2"), 900)
        self.assertEqual(accessible_protein(p, 12, "F2"), 1200)
        self.assertEqual(accessible_protein(p, 99, "F2"), accessible_protein(p, 0, "F1"))

    def test_invalid_setup_has_no_outcome(self):
        with self.assertRaisesRegex(ValueError, "exceed wet mass"):
            validate(self.profile | {"foundress_wet_mass": 1})
        with self.assertRaisesRegex(ValueError, "rate.*ordering"):
            validate(self.profile | {"larva_basal": 1})

    def test_opening_opportunities_never_bypass_available_material(self):
        profile = self.profile | {"maternal_protein": 60}
        f1 = screen(profile, "borisovka", "F1")
        f2 = screen(profile, "borisovka", "F2")
        self.assertEqual((f1["optimistic_opening_eggs_upper_bound"], f2["optimistic_opening_eggs_upper_bound"]), (3, 1))
        self.assertEqual(f1["ideal_path_with_mother_alive_to_emergence"], 0)

    def test_frozen_matrix_and_pairs(self):
        self.assertEqual(len(list(ordinary(self.envelope))), 32)
        cases = list(ordinary_cases(self.envelope))
        self.assertEqual(len({c["case"] for c in cases}), 960)
        self.assertEqual(Counter(c["group"] for c in cases), {"primary": 768, "check": 192})
        self.assertEqual({c["software_seed"] for c in cases if c["group"] == "primary"}, set(PRIMARY_SEEDS))
        self.assertEqual({c["software_seed"] for c in cases if c["group"] == "check"}, set(CHECK_SEEDS))
        for on, off in zip(cases[::2], cases[1::2], strict=True):
            self.assertTrue(on["care_enabled"] and not off["care_enabled"])
            self.assertEqual(on["parameters"], off["parameters"])
            self.assertEqual(on["software_seed"], off["software_seed"])


if __name__ == "__main__":
    unittest.main()
