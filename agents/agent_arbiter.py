"""Conservative arbiter that explains, but does not alter, the majority result."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Sequence

from agents.base_agent import AgentJudgment
from evidence.evidence_projection import EvidenceProjection


@dataclass(frozen=True)
class ArbiterResult:
    summary: str
    decisive_evidence_refs: list[str]
    supporting_points: list[str]
    opposing_points: list[str]
    why_majority_holds: str
    remaining_risks: list[str]
    explanation_confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ConservativeArbiter:
    _STANCE_TO_STATUS = {
        "支持通过": "supports",
        "反对通过": "contradicts",
        "待定": "missing",
    }

    def explain(
        self,
        projection: EvidenceProjection,
        history: Sequence[Any],
        final_record: Any,
    ) -> ArbiterResult:
        latest_judgments: list[AgentJudgment] = list(final_record.judgments or [])
        majority_stance = final_record.majority_stance
        majority_status = self._STANCE_TO_STATUS.get(majority_stance, "missing")

        decisive_refs = self._collect_decisive_refs(projection, latest_judgments, majority_status)
        supporting_points = self._collect_points(latest_judgments, {"支持通过"}, limit=3)
        opposing_points = self._collect_points(latest_judgments, {"反对通过", "待定"}, limit=3)
        remaining_risks = self._collect_remaining_risks(projection, latest_judgments, final_record)
        explanation_confidence = self._estimate_confidence(projection, final_record)

        summary = (
            f"本次仲裁基于已证实事实维持多数意见，最终结论为“{final_record.get_final_conclusion()}”。"
            f" 当前共有 {final_record.majority_count}/{final_record.total} 个 Agent 支持该立场。"
        )
        why_majority_holds = self._build_why_majority_holds(
            projection,
            final_record,
            decisive_refs,
            remaining_risks,
            history,
        )

        return ArbiterResult(
            summary=summary,
            decisive_evidence_refs=decisive_refs,
            supporting_points=supporting_points,
            opposing_points=opposing_points,
            why_majority_holds=why_majority_holds,
            remaining_risks=remaining_risks,
            explanation_confidence=explanation_confidence,
        )

    def _collect_decisive_refs(
        self,
        projection: EvidenceProjection,
        latest_judgments: Sequence[AgentJudgment],
        majority_status: str,
    ) -> list[str]:
        refs: list[str] = []
        for judgment in latest_judgments:
            if judgment.stance == "支持通过" and majority_status == "supports":
                refs.extend(judgment.evidence_refs)
            elif judgment.stance == "反对通过" and majority_status == "contradicts":
                refs.extend(judgment.evidence_refs)

        if not refs:
            refs.extend(card.card_id for card in projection.cards if card.status == majority_status)

        if majority_status == "supports" and not refs:
            refs.extend(card.card_id for card in projection.cards if card.status == "missing")

        ordered: list[str] = []
        seen: set[str] = set()
        for ref in refs:
            if ref and ref not in seen:
                ordered.append(ref)
                seen.add(ref)
            if len(ordered) >= 5:
                break
        return ordered

    def _collect_points(
        self,
        judgments: Sequence[AgentJudgment],
        include_stances: set[str],
        limit: int,
    ) -> list[str]:
        points: list[str] = []
        for judgment in judgments:
            if judgment.stance not in include_stances:
                continue
            text = judgment.key_finding.strip() or judgment.reasoning.strip()
            if not text:
                continue
            points.append(f"{judgment.agent_role}: {text}")
            if len(points) >= limit:
                break
        return points

    def _collect_remaining_risks(
        self,
        projection: EvidenceProjection,
        latest_judgments: Sequence[AgentJudgment],
        final_record: Any,
    ) -> list[str]:
        risks: list[str] = []
        for marker in projection.uncertainty_markers[:3]:
            risks.append(marker)

        if projection.resolved_count > 0:
            risks.append("当前结论以已证实事实为主，未发现的排除项按未发现风险处理。")

        for judgment in latest_judgments:
            for point in judgment.dissent_points:
                if point and point not in risks:
                    risks.append(point)
                if len(risks) >= 5:
                    return risks

        if not risks and not final_record.is_consensus_reached:
            risks.append("多数意见已形成，但尚未达到系统设定的稳定共识阈值。")

        return risks

    def _estimate_confidence(self, projection: EvidenceProjection, final_record: Any) -> float:
        evidence_factor = (
            projection.resolved_count / projection.total_cards
            if projection.total_cards > 0
            else 0.3
        )
        confidence = 0.55 * final_record.consensus_rate + 0.45 * evidence_factor
        return round(max(0.0, min(1.0, confidence)), 4)

    def _build_why_majority_holds(
        self,
        projection: EvidenceProjection,
        final_record: Any,
        decisive_refs: Sequence[str],
        remaining_risks: Sequence[str],
        history: Sequence[Any],
    ) -> str:
        evidence_summary = (
            f"已解析 {projection.resolved_count}/{projection.total_cards} 条证据，"
            f"经历 {len(history)} 轮判断后，多数立场稳定收敛为“{final_record.majority_stance}”。"
        )
        decisive_summary = (
            f" 决定性证据主要集中在 {', '.join(decisive_refs)}。"
            if decisive_refs
            else ""
        )
        risk_summary = (
            f" 仍需关注 {len(remaining_risks)} 项风险，但这些风险当前不足以推翻多数结论。"
            if remaining_risks
            else " 当前未发现足以推翻多数结论的关键异议。"
        )
        return f"{evidence_summary}{decisive_summary}{risk_summary}"
