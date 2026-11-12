"""Exercise observed absences, action provenance and corruption detection on real WP-3 archives."""

from contextlib import closing
import sqlite3
import unittest

from analyze_s6_4_wp3 import individual_rows
from s6_4_wp3_cases import Case
from verify_s6_4_wp3 import extracted, verify_live
from build_s6_4_wp2_evidence import ROOT


BASELINE = ROOT / "experiments/s6_4_wp3/baseline"
SCOUT = Case("scout", "near", "blind", 0, "fresh", 7)
DEPLETED = Case("disruption", "deplete", "absent", 1, "fresh", 7)
BLOCKED = Case("disruption", "wall", "absent", 1, "fresh", 43)


class Observations(unittest.TestCase):
    def test_depletion_retains_fixture_debit_and_censoring(self):
        with extracted(BASELINE, DEPLETED) as folder:
            config, summary, facts = verify_live(DEPLETED, folder)
            data, trips, case = individual_rows(DEPLETED, config, summary, facts, folder)
        self.assertGreater(case["depletion_ug"], 0)
        fixture = next(i for i in data if i["role"] == "fixture")
        self.assertEqual(fixture["positive_collection_status"], "COMMITTED_FACT")
        self.assertEqual(fixture["positive_delivery_status"], "RIGHT_CENSORED")
        self.assertTrue(any(t["role"] == "fixture" and t["terminal_status"] == "RIGHT_CENSORED" for t in trips))

    def test_blind_label_and_passive_nonparticipation_remain_distinct(self):
        with extracted(BASELINE, SCOUT) as folder:
            config, summary, facts = verify_live(SCOUT, folder)
            data, _, case = individual_rows(SCOUT, config, summary, facts, folder)
        self.assertEqual(config["trail_weight"], "0")
        self.assertGreater(case["release_marked_cells"], 0)
        passive = next(i for i in data if i["role"] == "passive")
        self.assertEqual(passive["departure_status"], "RIGHT_CENSORED")
        self.assertEqual(passive["cue_to_activation_cause"], "UNOBSERVED")
        scout = next(i for i in data if i["role"] == "scout")
        self.assertEqual(scout["death_status"], "COMMITTED_FACT")
        self.assertEqual(scout["positive_delivery_status"], "COMMITTED_FACT")

    def test_wall_has_motion_without_local_food_or_delivery(self):
        with extracted(BASELINE, BLOCKED) as folder:
            config, summary, facts = verify_live(BLOCKED, folder)
            data, _, _ = individual_rows(BLOCKED, config, summary, facts, folder)
        worker = next(i for i in data if i["role"] == "forager")
        self.assertGreater(worker["committed_moves"], 0)
        self.assertEqual(worker["local_food_choice_status"], "RIGHT_CENSORED")
        self.assertEqual(worker["positive_delivery_status"], "RIGHT_CENSORED")

    def test_sidecar_digest_corruption_is_rejected(self):
        with extracted(BASELINE, DEPLETED) as folder:
            with closing(sqlite3.connect(folder / "observer.sqlite")) as db:
                db.execute("UPDATE cuts SET digest=zeroblob(32) WHERE seq=2")
                db.commit()
            with self.assertRaisesRegex(ValueError, "invalid cut digest"):
                verify_live(DEPLETED, folder)

    def test_post_cut_view_cursor_corruption_is_rejected(self):
        with extracted(BASELINE, SCOUT) as folder:
            path = folder / "actors.csv"
            rows = path.read_text(encoding="utf-8").splitlines()
            columns = rows[1].split(",")
            columns[1] = str(int(columns[1]) + 1)
            rows[1] = ",".join(columns)
            path.write_text("\n".join(rows) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unbound observation row"):
                verify_live(SCOUT, folder)


if __name__ == "__main__":
    unittest.main()
