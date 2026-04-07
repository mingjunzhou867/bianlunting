from __future__ import annotations

import unittest

from evidence.evidence_model import classify_evidence_diagnostic


class EvidenceDiagnosticTests(unittest.TestCase):
    def test_no_data_is_classified_as_empty_result(self) -> None:
        diagnostic = classify_evidence_diagnostic("no_data")
        self.assertEqual(diagnostic[0], "empty_result")

    def test_missing_table_error_is_classified(self) -> None:
        diagnostic = classify_evidence_diagnostic("failed", "Table 'demo.subsidy_payment_history' doesn't exist")
        self.assertEqual(diagnostic[0], "missing_table")

    def test_unknown_column_error_is_classified(self) -> None:
        diagnostic = classify_evidence_diagnostic("failed", "Unknown column 'grant_date' in 'field list'")
        self.assertEqual(diagnostic[0], "missing_column")

    def test_table_corruption_error_is_classified(self) -> None:
        diagnostic = classify_evidence_diagnostic("failed", "Table './db/foo' is marked as crashed and should be repaired")
        self.assertEqual(diagnostic[0], "table_corrupted")

    def test_connection_error_is_classified(self) -> None:
        diagnostic = classify_evidence_diagnostic("failed", "MySQL server has gone away")
        self.assertEqual(diagnostic[0], "db_connection_error")


if __name__ == "__main__":
    unittest.main()
