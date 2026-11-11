#!/usr/bin/env python3
"""Reproduce the six recorded Phase 3 negative checks without editing the evidence."""

import json
import unittest
from copy import deepcopy
from unittest.mock import patch

import verify_scientific_integration as integration
import verify_scientific_validation_plan as plan


class Phase3RejectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = plan.read_index(plan.SOURCES, "SourceContextId")
        cls.blockers = plan.read_index(plan.BLOCKER_FILE, "BlockerId")
        cls.protocols = plan.read_index(plan.PROTOCOLS, "BlockerId")
        cls.priorities = plan.read_index(plan.PARAMETER_FILE, "ParameterKey")
        cls.rules = plan.read_index(plan.RULES, "RuleId")

    def assert_rejects_protocols(self, protocols, reason):
        with self.assertRaisesRegex(ValueError, reason):
            plan.verify_protocols(protocols, self.blockers, self.sources)

    def test_missing_protocol(self):
        protocols = self.protocols.copy()
        del protocols["BR-09"]
        self.assert_rejects_protocols(protocols, "exactly one protocol")

    def test_development_data_named_as_holdout(self):
        protocols = deepcopy(self.protocols)
        protocols["BR-03"]["HeldOutDatasetId"] = "B01"
        self.assert_rejects_protocols(protocols, "BR-03: holdout or execution status overstated")

    def test_invented_protocol_pass(self):
        protocols = deepcopy(self.protocols)
        protocols["BR-04"]["ExecutionStatus"] = "PASS"
        self.assert_rejects_protocols(protocols, "BR-04: holdout or execution status overstated")

    def test_accepted_source_locator_changed(self):
        protocols = deepcopy(self.protocols)
        record = protocols["BR-02"]
        sources = json.loads(record["AcceptedSourceLinksJson"])
        sources[0]["Locators"] = "Injected source locator"
        record["AcceptedSourceLinksJson"] = json.dumps(sources)
        self.assert_rejects_protocols(protocols, "BR-02: changed accepted source link")

    def test_duplicate_parameter_assessment(self):
        rules = deepcopy(self.rules)
        rules["E02"]["ParameterKeys"] += ";PhysiologyConfig.egg_duration"
        with self.assertRaisesRegex(ValueError, r"PhysiologyConfig\.egg_duration: duplicate or incompatible"):
            plan.parameter_rules(rules, self.priorities, self.sources, self.protocols)

    def test_shared_trajectory_lineage_split(self):
        expected = plan.availability(self.sources, self.protocols)
        changed = deepcopy(expected)
        related = next(row for row in changed if row["DatasetId"] == "B2-F03")
        related["SplitGroupId"] = "B2-F03"
        with patch.object(integration, "rows", return_value=changed):
            with self.assertRaisesRegex(ValueError, r"\(B2-F03\): unexpected fields SplitGroupId"):
                integration.check_table(plan.REVIEW / plan.DATA, expected, False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
