"""Regression tests for debate orchestration and persistence hooks."""
from __future__ import annotations

import json
import unittest
from typing import get_args
from unittest.mock import patch

from agents.agent_empirical import EmpiricalReasoningAgent
from agents.agent_lenient import LenientBusinessAgent
from agents.base_agent import AgentJudgment
from agents.debate_orchestrator import DebateOrchestrator, DebateRecord, project_evidence
from agents.debate_persistence import DebatePersistenceError
from evidence.evidence_model import EvidenceBundle, EvidenceItem
from evidence.evidence_projection import EvidenceProjection


CONCLUSIONS = get_args(AgentJudgment.model_fields["conclusion"].annotation)
STANCES = get_args(AgentJudgment.model_fields["stance"].annotation)
PASS_CONCLUSION = CONCLUSIONS[0]
FAIL_CONCLUSION = CONCLUSIONS[1]
MISSING_CONCLUSION = CONCLUSIONS[2]
SUPPORT_STANCE = STANCES[0]
OPPOSE_STANCE = STANCES[1]
PENDING_STANCE = STANCES[2]


class StubAgent:
    def __init__(self, agent_id: str, agent_role: str, conclusion: str, stance: str):
        self.AGENT_ID = agent_id
        self.AGENT_ROLE = agent_role
        self._conclusion = conclusion
        self._stance = stance

    def judge(self, projection: EvidenceProjection, debate_round: int = 0, **_kwargs) -> AgentJudgment:
        evidence_refs = [projection.cards[0].card_id] if projection.cards else []
        return AgentJudgment(
            agent_id=self.AGENT_ID,
            agent_role=self.AGENT_ROLE,
            debate_round=debate_round,
            conclusion=self._conclusion,
            stance=self._stance,
            confidence=0.9,
            evidence_refs=evidence_refs,
            reasoning=f"{self.AGENT_ROLE} initial judgment",
            dissent_points=[],
            key_finding=f"{self.AGENT_ROLE} key finding",
        )

    def debate_respond(
        self,
        projection: EvidenceProjection,
        previous_judgments: list[AgentJudgment],
        debate_round: int = 1,
        **_kwargs,
    ) -> AgentJudgment:
        return self.judge(projection, debate_round=debate_round)


def build_bundle(id_card: str = "42090219760310000D") -> EvidenceBundle:
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
                result_raw=[{"is_valid": "1"}],
                result_summary="employment exists",
                supports_conclusion=True,
                confidence=1.0,
                exec_status="success",
            )
        ],
    )


class DebateOrchestratorPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle = build_bundle()
        self.orchestrator = DebateOrchestrator()
        self.orchestrator.collector.collect_all = lambda _id_card, policy_id="POLICY_001": self.bundle
        self.orchestrator.collector.collect_stream = lambda _id_card, policy_id="POLICY_001": iter(self.bundle.items)
        self.orchestrator.agents = [
            StubAgent("agent_1", "strict", PASS_CONCLUSION, SUPPORT_STANCE),
            StubAgent("agent_2", "lenient", PASS_CONCLUSION, SUPPORT_STANCE),
            StubAgent("agent_3", "explorer", PASS_CONCLUSION, SUPPORT_STANCE),
            StubAgent("agent_4", "auditor", FAIL_CONCLUSION, OPPOSE_STANCE),
            StubAgent("agent_5", "empirical", PASS_CONCLUSION, SUPPORT_STANCE),
        ]

    @patch("agents.debate_orchestrator.persist_completed_session")
    def test_run_debate_persists_completed_session_once(self, persist_mock) -> None:
        result = self.orchestrator.run_debate(self.bundle.id_card)

        self.assertEqual(result["id_card"], self.bundle.id_card)
        self.assertEqual(result["final_conclusion"], PASS_CONCLUSION)
        self.assertEqual(result["final_stance"], SUPPORT_STANCE)
        self.assertEqual(result["rounds_taken"], 0)
        self.assertEqual(len(result["history"]), 1)
        self.assertIn("arbiter_result", result)
        self.assertIn("summary", result["arbiter_result"])

        persist_mock.assert_called_once()
        kwargs = persist_mock.call_args.kwargs
        self.assertEqual(kwargs["source_endpoint"], "/api/debate")
        self.assertEqual(kwargs["session_id"], result["session_id"])
        self.assertEqual(kwargs["bundle"].id_card, self.bundle.id_card)
        self.assertEqual(len(kwargs["history"]), 1)
        self.assertTrue(kwargs["final_record"].is_consensus_reached)

    @patch("agents.debate_orchestrator.persist_completed_session")
    def test_run_debate_stream_keeps_sse_shape_and_persists_on_success(self, persist_mock) -> None:
        events = list(self.orchestrator.run_debate_stream(self.bundle.id_card))
        payloads = [json.loads(event.removeprefix("data: ").strip()) for event in events]

        self.assertEqual(payloads[0]["event"], "system_trace")
        self.assertEqual(payloads[-1]["event"], "debate_final")
        self.assertEqual(payloads[-1]["data"]["final_conclusion"], PASS_CONCLUSION)
        self.assertEqual(payloads[-1]["data"]["session_id"], persist_mock.call_args.kwargs["session_id"])
        self.assertIn("history", payloads[-1]["data"])
        self.assertIn("arbiter_result", payloads[-1]["data"])
        self.assertTrue(any(payload["event"] == "evidence" for payload in payloads))
        self.assertTrue(any(payload["event"] == "agent_judgment" for payload in payloads))

        persist_mock.assert_called_once()
        kwargs = persist_mock.call_args.kwargs
        self.assertEqual(kwargs["source_endpoint"], "/api/debate_stream")
        self.assertEqual(kwargs["bundle"].id_card, self.bundle.id_card)

    @patch(
        "agents.debate_orchestrator.persist_completed_session",
        side_effect=DebatePersistenceError("write failed"),
    )
    def test_run_debate_surfaces_persistence_failures(self, _persist_mock) -> None:
        with self.assertRaises(DebatePersistenceError):
            self.orchestrator.run_debate(self.bundle.id_card)

    @patch(
        "agents.debate_orchestrator.persist_completed_session",
        side_effect=DebatePersistenceError("write failed"),
    )
    def test_run_debate_stream_surfaces_persistence_failures(self, _persist_mock) -> None:
        stream = self.orchestrator.run_debate_stream(self.bundle.id_card)
        with self.assertRaises(DebatePersistenceError):
            list(stream)


class DebateProjectionTests(unittest.TestCase):
    def test_no_data_with_affirmative_semantics_projects_as_support(self) -> None:
        bundle = EvidenceBundle(
            id_card="42090219800101000A",
            items=[
                EvidenceItem(
                    evidence_id="plan_p001_flex_003",
                    rule_id="P001_FLEX_003",
                    target_id_card="42090219800101000A",
                    target="identity risk",
                    category="flexible rule",
                    sql="SELECT ...",
                    result_raw=[],
                    result_summary="no risky identity switch record was found",
                    supports_conclusion=True,
                    confidence=0.5,
                    exec_status="no_data",
                )
            ],
        )

        projection = project_evidence(bundle)

        self.assertEqual(projection.cards[0].status, "supports")
        self.assertEqual(projection.unresolved_count, 0)
        self.assertEqual(projection.resolved_count, 1)


class DebateJudgmentNormalizationTests(unittest.TestCase):
    def test_majority_uses_conclusion_when_stance_is_misaligned(self) -> None:
        judgments = [
            AgentJudgment(
                agent_id="agent_strict",
                agent_role="strict",
                debate_round=0,
                conclusion=FAIL_CONCLUSION,
                stance=PENDING_STANCE,
                confidence=0.9,
                evidence_refs=[],
                reasoning="strict",
                dissent_points=[],
                key_finding="strict",
            ),
            AgentJudgment(
                agent_id="agent_lenient",
                agent_role="lenient",
                debate_round=0,
                conclusion=PASS_CONCLUSION,
                stance=SUPPORT_STANCE,
                confidence=0.8,
                evidence_refs=[],
                reasoning="lenient",
                dissent_points=[],
                key_finding="lenient",
            ),
            AgentJudgment(
                agent_id="agent_explorer",
                agent_role="explorer",
                debate_round=0,
                conclusion=FAIL_CONCLUSION,
                stance=OPPOSE_STANCE,
                confidence=0.8,
                evidence_refs=[],
                reasoning="explorer",
                dissent_points=[],
                key_finding="explorer",
            ),
        ]

        record = DebateRecord(judgments, 0)

        self.assertEqual(record.majority_stance, OPPOSE_STANCE)
        self.assertEqual(record.get_final_conclusion(), FAIL_CONCLUSION)

    def test_lenient_missing_is_downgraded_to_support_when_only_supporting_evidence_exists(self) -> None:
        projection = EvidenceProjection(
            task_header="qualification",
            target_person="42090219800101000A",
            policy_scope="subsidy",
            cards=[
                {
                    "card_id": "card_1",
                    "question": "base condition",
                    "finding": "satisfied",
                    "status": "supports",
                    "confidence": 0.9,
                    "artifact_refs": ["e1"],
                },
                {
                    "card_id": "card_2",
                    "question": "history subsidy",
                    "finding": "not found yet",
                    "status": "missing",
                    "confidence": 0.5,
                    "artifact_refs": ["e2"],
                },
            ],
            total_cards=2,
            resolved_count=1,
            unresolved_count=1,
        )
        judgment = AgentJudgment(
            agent_id="agent_lenient",
            agent_role="lenient",
            debate_round=0,
            conclusion=MISSING_CONCLUSION,
            stance=PENDING_STANCE,
            confidence=0.55,
            evidence_refs=[],
            reasoning="some evidence is still missing but the existing evidence is supportive overall.",
            dissent_points=[],
            key_finding="",
        )

        normalized = LenientBusinessAgent()._postprocess_judgment(judgment, projection)

        self.assertEqual(normalized.conclusion, PASS_CONCLUSION)
        self.assertEqual(normalized.stance, SUPPORT_STANCE)
        self.assertGreaterEqual(normalized.confidence, 0.65)

    def test_empirical_missing_is_downgraded_to_support_when_only_supporting_evidence_exists(self) -> None:
        projection = EvidenceProjection(
            task_header="qualification",
            target_person="42090219800101000A",
            policy_scope="subsidy",
            cards=[
                {
                    "card_id": "card_1",
                    "question": "base condition",
                    "finding": "satisfied",
                    "status": "supports",
                    "confidence": 0.9,
                    "artifact_refs": ["e1"],
                }
            ],
            total_cards=1,
            resolved_count=1,
            unresolved_count=0,
        )
        judgment = AgentJudgment(
            agent_id="agent_empirical",
            agent_role="empirical",
            debate_round=0,
            conclusion=MISSING_CONCLUSION,
            stance=PENDING_STANCE,
            confidence=0.5,
            evidence_refs=[],
            reasoning="the remaining unknowns are small relative to the current evidence support.",
            dissent_points=[],
            key_finding="",
        )

        normalized = EmpiricalReasoningAgent()._postprocess_judgment(judgment, projection)

        self.assertEqual(normalized.conclusion, PASS_CONCLUSION)
        self.assertEqual(normalized.stance, SUPPORT_STANCE)
        self.assertGreaterEqual(normalized.confidence, 0.65)


if __name__ == "__main__":
    unittest.main()
