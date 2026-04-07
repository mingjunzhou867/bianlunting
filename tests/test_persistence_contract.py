"""Contract tests for debate persistence schema and serializers."""
from __future__ import annotations

import json
import unittest
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import get_args
from unittest.mock import patch

from agents.base_agent import AgentJudgment
from agents.debate_orchestrator import DebateRecord
from agents.debate_persistence import (
    DebateSessionNotFoundError,
    build_completed_session_records,
    get_saved_session_detail,
    list_saved_sessions,
)
from evidence.evidence_model import EvidenceBundle, EvidenceItem


DDL_PATH = Path("data/schema/mysql_ddl.sql")
CONCLUSIONS = get_args(AgentJudgment.model_fields["conclusion"].annotation)
STANCES = get_args(AgentJudgment.model_fields["stance"].annotation)
PASS_CONCLUSION = CONCLUSIONS[0]
FAIL_CONCLUSION = CONCLUSIONS[1]
SUPPORT_STANCE = STANCES[0]
OPPOSE_STANCE = STANCES[1]


def build_bundle() -> EvidenceBundle:
    id_card = "42090219760310000D"
    return EvidenceBundle(
        id_card=id_card,
        items=[
            EvidenceItem(
                evidence_id="RULE_001_1",
                rule_id="RULE_001",
                target_id_card=id_card,
                target="employment_registration",
                category="qualification",
                sql="SELECT 1",
                result_raw=[{"company_id": "91420900000000001X"}],
                result_summary="employment exists",
                supports_conclusion=True,
                confidence=1.0,
                exec_status="success",
            )
        ],
    )


def build_history() -> list[DebateRecord]:
    judgments = [
        AgentJudgment(
            agent_id="agent_1",
            agent_role="strict",
            debate_round=0,
            conclusion=PASS_CONCLUSION,
            stance=SUPPORT_STANCE,
            confidence=0.91,
            evidence_refs=["RULE_001"],
            reasoning="strict agrees",
            dissent_points=[],
            key_finding="strict finding",
        ),
        AgentJudgment(
            agent_id="agent_2",
            agent_role="lenient",
            debate_round=0,
            conclusion=PASS_CONCLUSION,
            stance=SUPPORT_STANCE,
            confidence=0.88,
            evidence_refs=["RULE_001"],
            reasoning="lenient agrees",
            dissent_points=[],
            key_finding="lenient finding",
        ),
        AgentJudgment(
            agent_id="agent_3",
            agent_role="explorer",
            debate_round=0,
            conclusion=FAIL_CONCLUSION,
            stance=OPPOSE_STANCE,
            confidence=0.62,
            evidence_refs=["RULE_001"],
            reasoning="explorer disagrees",
            dissent_points=["possible conflict"],
            key_finding="explorer finding",
        ),
    ]
    return [DebateRecord(judgments, 0)]


class FakeResult:
    def __init__(self, rows: list[dict[str, object]]):
        self._rows = rows

    def mappings(self) -> "FakeResult":
        return self

    def all(self) -> list[dict[str, object]]:
        return self._rows

    def first(self) -> dict[str, object] | None:
        return self._rows[0] if self._rows else None


class FakeSession:
    def __init__(self, rows: list[dict[str, object]]):
        self._rows = rows

    def execute(self, *_args, **_kwargs) -> FakeResult:
        return FakeResult(self._rows)


class DebatePersistenceContractTests(unittest.TestCase):
    def test_serializer_covers_summary_and_full_snapshot_needs(self) -> None:
        bundle = build_bundle()
        history = build_history()
        final_record = history[-1]
        persisted = build_completed_session_records(
            session_id="session-123",
            source_endpoint="/api/debate",
            bundle=bundle,
            history=history,
            final_record=final_record,
            started_at=datetime(2026, 3, 23, 10, 0, 0),
            completed_at=datetime(2026, 3, 23, 10, 1, 0),
        )

        self.assertEqual(persisted.session_row["id_card"], bundle.id_card)
        self.assertEqual(persisted.session_row["status"], "completed")
        self.assertEqual(persisted.session_row["source_endpoint"], "/api/debate")
        self.assertEqual(persisted.session_row["final_conclusion"], PASS_CONCLUSION)
        self.assertEqual(persisted.session_row["rounds_taken"], 0)
        self.assertEqual(len(persisted.log_rows), 3)

        snapshot = json.loads(persisted.session_row["snapshot_payload"])
        self.assertEqual(snapshot["summary"]["final_conclusion"], PASS_CONCLUSION)
        self.assertEqual(snapshot["summary"]["evidence_count"], 1)
        self.assertEqual(snapshot["history"][0]["judgments"][0]["agent_id"], "agent_1")
        self.assertEqual(snapshot["evidence"][0]["rule_id"], "RULE_001")
        self.assertEqual(snapshot["evidence"][0]["result_raw"][0]["company_id"], "91420900000000001X")

    def test_mysql_ddl_matches_runtime_contract(self) -> None:
        ddl = DDL_PATH.read_text(encoding="utf-8")

        for expected in [
            "CREATE TABLE IF NOT EXISTS debate_session",
            "session_id               VARCHAR(36)  PRIMARY KEY",
            "source_endpoint          VARCHAR(32)  NOT NULL",
            "snapshot_payload         LONGTEXT     NOT NULL",
            "CREATE TABLE IF NOT EXISTS agent_debate_log",
            "session_id                 VARCHAR(36)  NOT NULL",
            "evidence_refs              LONGTEXT     NOT NULL",
            "dissent_points             LONGTEXT     NOT NULL",
            "round_majority_stance      VARCHAR(20)  NOT NULL",
            "round_consensus_rate       DECIMAL(5,4) NOT NULL",
        ]:
            self.assertIn(expected, ddl)

    def test_list_saved_sessions_returns_summary_only_rows(self) -> None:
        rows = [
            {
                "session_id": "session-2",
                "id_card": "42090219760310000D",
                "status": "completed",
                "source_endpoint": "/api/debate_stream",
                "final_conclusion": FAIL_CONCLUSION,
                "final_stance": OPPOSE_STANCE,
                "consensus_rate": 0.8,
                "is_consensus_reached": 1,
                "rounds_taken": 1,
                "evidence_count": 5,
                "completed_at": datetime(2026, 3, 23, 10, 5, 0),
                "snapshot_payload": '{"too":"heavy"}',
            },
            {
                "session_id": "session-1",
                "id_card": "42090219760310000D",
                "status": "completed",
                "source_endpoint": "/api/debate",
                "final_conclusion": PASS_CONCLUSION,
                "final_stance": SUPPORT_STANCE,
                "consensus_rate": 1.0,
                "is_consensus_reached": 1,
                "rounds_taken": 0,
                "evidence_count": 1,
                "completed_at": datetime(2026, 3, 22, 10, 0, 0),
                "snapshot_payload": '{"too":"heavy"}',
            },
        ]

        @contextmanager
        def fake_get_session():
            yield FakeSession(rows)

        with patch("agents.debate_persistence.get_session", fake_get_session):
            history = list_saved_sessions("42090219760310000D")

        self.assertEqual([item["session_id"] for item in history], ["session-2", "session-1"])
        self.assertEqual(history[0]["completed_at"], "2026-03-23T10:05:00")
        self.assertTrue(history[0]["is_consensus_reached"])
        self.assertNotIn("snapshot_payload", history[0])

    def test_list_saved_sessions_returns_empty_list_when_no_rows_exist(self) -> None:
        @contextmanager
        def fake_get_session():
            yield FakeSession([])

        with patch("agents.debate_persistence.get_session", fake_get_session):
            history = list_saved_sessions("42090219760310000D")

        self.assertEqual(history, [])

    def test_get_saved_session_detail_uses_snapshot_payload_as_primary_source(self) -> None:
        snapshot = {
            "session_id": "session-123",
            "id_card": "42090219760310000D",
            "final_conclusion": PASS_CONCLUSION,
            "history": [{"round_num": 0, "judgments": []}],
            "summary": {"final_conclusion": PASS_CONCLUSION},
        }
        rows = [
            {
                "session_id": "session-123",
                "id_card": "42090219760310000D",
                "status": "completed",
                "source_endpoint": "/api/debate",
                "completed_at": datetime(2026, 3, 23, 10, 1, 0),
                "snapshot_payload": json.dumps(snapshot, ensure_ascii=False),
            }
        ]

        @contextmanager
        def fake_get_session():
            yield FakeSession(rows)

        with patch("agents.debate_persistence.get_session", fake_get_session):
            detail = get_saved_session_detail("session-123")

        self.assertEqual(detail["session_id"], "session-123")
        self.assertEqual(detail["final_conclusion"], PASS_CONCLUSION)
        self.assertEqual(detail["completed_at"], "2026-03-23T10:01:00")
        self.assertEqual(detail["history"][0]["round_num"], 0)

    def test_get_saved_session_detail_applies_row_defaults_needed_by_history_ui(self) -> None:
        snapshot = {
            "session_id": "session-123",
            "id_card": "42090219760310000D",
            "history": [{"round_num": 0, "judgments": []}],
            "evidence": [{"rule_id": "RULE_001"}],
        }
        rows = [
            {
                "session_id": "session-123",
                "id_card": "42090219760310000D",
                "status": "completed",
                "source_endpoint": "/api/debate_stream",
                "completed_at": datetime(2026, 3, 23, 10, 1, 0),
                "snapshot_payload": json.dumps(snapshot, ensure_ascii=False),
            }
        ]

        @contextmanager
        def fake_get_session():
            yield FakeSession(rows)

        with patch("agents.debate_persistence.get_session", fake_get_session):
            detail = get_saved_session_detail("session-123")

        self.assertEqual(detail["status"], "completed")
        self.assertEqual(detail["source_endpoint"], "/api/debate_stream")
        self.assertEqual(detail["completed_at"], "2026-03-23T10:01:00")
        self.assertEqual(detail["evidence"][0]["rule_id"], "RULE_001")

    def test_get_saved_session_detail_raises_explicit_not_found(self) -> None:
        @contextmanager
        def fake_get_session():
            yield FakeSession([])

        with patch("agents.debate_persistence.get_session", fake_get_session):
            with self.assertRaises(DebateSessionNotFoundError):
                get_saved_session_detail("missing-session")


if __name__ == "__main__":
    unittest.main()
