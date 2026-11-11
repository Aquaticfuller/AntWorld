"""Check that reconciliation keeps the original measurement boundaries and budgets."""

import unittest

from reconcile_s6_4_rm02_performance import MIB, admission_checks, expected_schedule, frozen_gates, verify_sample


class ReconciliationTests(unittest.TestCase):
    def test_only_foreground_maximum_is_limited_to_twenty_ms(self):
        cell = {
            "control_p50_ratio": 1.10,
            "ratios": {"p50": 1.10, "p95": 1.20},
            "foreground_cut_ms": {"p95": 5, "maximum": 20},
            "peak_paired_increment_bytes": 16 * MIB,
            "maximum_final_flush_ms": 256,
        }
        self.assertTrue(all(frozen_gates(cell).values()))
        cell["foreground_cut_ms"]["maximum"] = 20.001
        self.assertFalse(frozen_gates(cell)["foreground_max"])
        cell["foreground_cut_ms"]["p95"] = 5.001
        self.assertFalse(frozen_gates(cell)["foreground_p95"])
        cell["ratios"]["p50"] = 1.10001
        cell["ratios"]["p95"] = 1.20001
        cell["peak_paired_increment_bytes"] += 1
        cell["control_p50_ratio"] = .8999
        self.assertEqual(set(frozen_gates(cell).values()), {False})

    def test_end_to_end_still_charges_terminal_persistence(self):
        identity = expected_schedule(1)[0]
        row = identity | dict(sim_ms="10000", sqlite_bytes="4096", peak_queue_bytes="300", events="4",
                              setup_ms="10", observer_init_ms="10", checkpoint_ms="10", restore_ms="10",
                              advance_ms="30", total_ms="132", flush_ms="100")
        cut = identity | dict(sim_ms="10000", cursor="4", examined="4", selected="2",
                              dropped="0", payload_bytes="300", records="67", capture_ms="1", publish_ms="1")
        self.assertEqual(verify_sample(row, [cut]), 2)
        with self.assertRaisesRegex(ValueError, "total omits"):
            verify_sample(row | {"total_ms": "32"}, [cut])
        for update in ({"examined": "3"}, {"dropped": "1"}, {"records": "66"}, {"payload_bytes": str(3 * MIB + 1)}):
            with self.subTest(update=update), self.assertRaisesRegex(ValueError, "cut coverage or payload quota"):
                verify_sample(row, [cut | update])
        with self.assertRaisesRegex(ValueError, "missing or unexpected cuts"):
            verify_sample(row, [])

    def test_admission_recomputes_load_and_sensor_gates(self):
        base = dict(system_busy_pct="2", processor_busy_pct="6", nonidle_wall_all_valid="True",
                    wall_delta_ns="1000000000", ac="1", battery_saver="0", sensor_age_s="1",
                    package_temperature_c="54", package_power_w="7", p0_t0_effective_clock_mhz="500")
        rows = [base.copy() for _ in range(60)]
        self.assertTrue(admission_checks(rows)[1])
        rows[0]["sensor_age_s"] = "10.001"
        self.assertFalse(admission_checks(rows)[1])
        rows[0] = base.copy()
        for row in rows[-4:]:
            row["processor_busy_pct"] = "25"
        self.assertFalse(admission_checks(rows)[1])


if __name__ == "__main__":
    unittest.main()
