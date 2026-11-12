"""Negative controls for independent cohort and soil reconciliation."""

import unittest

from s6_4_wp5_cohorts import incidence
from s6_4_wp5_geometry import Grid


def box(kind, low, high, **extra):
    return dict(kind=kind, **{f"min_{a}_q": n for a, n in zip("xyz", low, strict=True)},
                **{f"max_{a}_q": n for a, n in zip("xyz", high, strict=True)}, **extra)


class Cohorts(unittest.TestCase):
    def test_tied_censor_remains_at_risk_for_observed_endpoints(self):
        stages = [dict(duration_ms=30, endpoint=e) for e in ("death", "transition", "right_censored")]
        point, = incidence(stages)
        self.assertEqual(point[:4], (30, 3, 1 / 3, 1 / 3))
        self.assertAlmostEqual(point[4], 1 / 3)

    def test_no_endpoint_when_last_observation_is_censored(self):
        point, = incidence([dict(duration_ms=1, endpoint="right_censored")])
        self.assertEqual(point, (1, 1, 0, 0, 1))


class Geometry(unittest.TestCase):
    def setUp(self):
        self.grid = Grid([box("solid", (0, 0, 0), (12, 4, 4)), box("void", (0, 0, 0), (12, 4, 4))])
        self.plug = box("fill", (6, 0, 0), (7, 4, 4), volume_q3=16)

    def test_fill_invalidates_and_excavation_restores_body_sweep(self):
        a, b = (3, 2, 2), (9, 2, 2)
        self.assertTrue(self.grid.swept(a, b, 2))
        self.grid.edit(self.plug, False)
        self.assertFalse(self.grid.swept(a, b, 2))
        self.grid.edit(self.plug, True)
        self.assertTrue(self.grid.swept(a, b, 2))

    def test_bad_reported_amount_does_not_change_replay(self):
        with self.assertRaisesRegex(ValueError, "edit amount differs"):
            self.grid.edit(self.plug | {"volume_q3": 15}, False)
        self.assertEqual(len(self.grid.void), 192)

    def test_rock_cannot_become_void(self):
        grid = Grid([box("solid", (0, 0, 0), (2, 2, 2)), box("rock", (1, 0, 0), (2, 2, 2))])
        with self.assertRaisesRegex(ValueError, "non-editable"):
            grid.edit(box("excavate", (1, 0, 0), (2, 1, 1), volume_q3=1), True)


if __name__ == "__main__":
    unittest.main()
