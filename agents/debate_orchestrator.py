"""Debate orchestration and completed-session persistence."""
from __future__ import annotations

import json
import uuid
import time
from datetime import UTC, datetime
from typing import Generator

from loguru import logger

from agents import create_all_agents
from agents.adjudication_report import build_adjudication_report
from agents.agent_arbiter import ConservativeArbiter
from agents.base_agent import (
    AgentJudgment,
    CONCLUSION_FAIL,
    CONCLUSION_MISSING,
    CONCLUSION_PASS,
    DebateToolPolicy,
    STANCE_OPPOSE,
    STANCE_PENDING,
    STANCE_SUPPORT,
)
from agents.decision_semantics import (
    aggregate_final_conclusion_from_judgments,
    build_item_semantics,
)
from portrait import PersonaBuilder
from agents.empirical_case_retriever import retrieve_empirical_cases
from agents.debate_persistence import (
    DebatePersistenceError,
    build_debate_result,
    persist_completed_session,
)
from config.settings import settings
from evidence.evidence_model import EvidenceBundle
from evidence.evidence_projection import EvidenceProjection, EvidenceSummaryCard
from cognition.evidence_planner import EvidencePlanner
from text2sql.dynamic.dynamic_collector import DynamicEvidenceCollector
from tools.tool_registry import ToolRegistry


DEFAULT_TASK_HEADER = "灵活就业社保补贴资格认定"
DEFAULT_POLICY_SCOPE = "灵活就业补贴政策规则"


def project_evidence(bundle: EvidenceBundle, task_header: str = DEFAULT_TASK_HEADER, policy_scope: str = DEFAULT_POLICY_SCOPE) -> EvidenceProjection:
    """Reshape retrieved evidence into the summary-first debate format."""

    cards: list[EvidenceSummaryCard] = []
    uncertainty_markers: list[str] = []

    for item in bundle.items:
        semantic = build_item_semantics(item)
        if semantic["semantic_decision_effect"] == "support":
            status = "supports"
        elif semantic["semantic_decision_effect"] == "oppose":
            status = "contradicts"
        elif semantic["semantic_is_missing_data"]:
            status = "missing"
        else:
            status = "unresolved"

        cards.append(
            EvidenceSummaryCard(
                card_id=f"card_{item.rule_id}",
                question=item.target,
                finding=item.result_summary,
                status=status,
                confidence=item.confidence,
                artifact_refs=[item.evidence_id],
            )
        )

        if status == "unresolved":
            uncertainty_markers.append(f"[{item.rule_id}] {item.target}: 需 Agent 进一步判定")
        elif status == "missing":
            uncertainty_markers.append(f"[{item.rule_id}] {item.target}: 数据缺失({item.exec_status})")

    resolved_count = sum(1 for card in cards if card.status in ("supports", "contradicts"))
    unresolved_count = sum(1 for card in cards if card.status in ("unresolved", "missing"))

    return EvidenceProjection(
        task_header=task_header,
        target_person=bundle.id_card,
        policy_scope=policy_scope,
        cards=cards,
        uncertainty_markers=uncertainty_markers,
        total_cards=len(cards),
        resolved_count=resolved_count,
        unresolved_count=unresolved_count,
    )


class DebateRecord:
    """Internal round record shared by API responses and persistence."""

    _STANCE_BY_CONCLUSION = {
        CONCLUSION_PASS: STANCE_SUPPORT,
        CONCLUSION_FAIL: STANCE_OPPOSE,
        CONCLUSION_MISSING: STANCE_PENDING,
    }
    _FINAL_CONCLUSION_PRIORITY = {
        CONCLUSION_PASS: 2,
        CONCLUSION_FAIL: 1,
        CONCLUSION_MISSING: 0,
    }

    def __init__(self, judgments: list[AgentJudgment], round_num: int):
        self.round_num = round_num
        self.judgments = judgments

        stances = [self._effective_stance(judgment) for judgment in judgments]
        self.total = len(stances)
        counts = {stance: stances.count(stance) for stance in set(stances)}

        if counts:
            self.majority_count = max(counts.values())
            leaders = [
                stance
                for stance in (STANCE_SUPPORT, STANCE_OPPOSE, STANCE_PENDING)
                if counts.get(stance, 0) == self.majority_count
            ]
            self.majority_stance = leaders[0] if len(leaders) == 1 else STANCE_PENDING
            self.consensus_rate = self.majority_count / self.total
        else:
            self.majority_stance = STANCE_PENDING
            self.majority_count = 0
            self.consensus_rate = 0.0

        self.is_consensus_reached = self.consensus_rate >= settings.consensus_threshold

    def get_final_conclusion(self) -> str:
        return aggregate_final_conclusion_from_judgments(self.judgments)

    @classmethod
    def _effective_stance(cls, judgment: AgentJudgment) -> str:
        expected_stance = cls._STANCE_BY_CONCLUSION.get(judgment.conclusion)
        if expected_stance and judgment.stance != expected_stance:
            logger.warning(
                "Normalize mismatched stance: agent={} conclusion={} stance={} -> {}",
                judgment.agent_id,
                judgment.conclusion,
                judgment.stance,
                expected_stance,
            )
            return expected_stance
        return judgment.stance

    def to_dict(self) -> dict[str, object]:
        return {
            "round_num": self.round_num,
            "judgments": [judgment.model_dump() for judgment in self.judgments],
            "total": self.total,
            "majority_stance": self.majority_stance,
            "majority_count": self.majority_count,
            "consensus_rate": self.consensus_rate,
            "is_consensus_reached": self.is_consensus_reached,
        }


class DebateOrchestrator:
    """Run synchronous and streaming debate flows using Dynamic Evidence collection."""

    def __init__(self):
        self.collector = DynamicEvidenceCollector()
        self.agents = create_all_agents()
        self.arbiter = ConservativeArbiter()
        self.max_rounds = settings.debate_max_rounds
        self.tool_registry = ToolRegistry()
        self.tools = self.tool_registry.get_tool_schemas()
        # Debate agents judge from projected evidence first. Supplemental query is allowed,
        # but only as a bounded follow-up when a specific gap or challenge point needs verification.
        self.debate_tool_policy = DebateToolPolicy(
            allow_tools=True,
            require_existing_evidence_first=True,
            max_tool_calls_per_turn=1,
            allowed_tool_names=("get_dict", "text_to_sql"),
        )

    def _empirical_case_context(self, agent, projection: EvidenceProjection) -> list[dict] | None:
        if getattr(agent, "AGENT_ID", "") != "agent_empirical":
            return None
        return [case.to_prompt_dict() for case in retrieve_empirical_cases(projection)]

    def _policy_display(self, policy_id: str) -> tuple[str, str]:
        """閺嶈宓?policy_id 鏉╂柨娲?(task_header, policy_scope) 閻劋绨幎鏇炲"""
        from policy.policy_router import get_policy
        cfg = get_policy(policy_id)
        if cfg:
            return f"{cfg.policy_name}{cfg.policy_type}", cfg.policy_name
        return DEFAULT_TASK_HEADER, DEFAULT_POLICY_SCOPE

    def run_debate(self, id_card: str, policy_id: str = "POLICY_001") -> dict[str, object]:
        session_id = str(uuid.uuid4())
        started_at = self._utcnow()

        bundle = self.collector.collect_all(id_card, policy_id=policy_id)
        task_header, policy_scope = self._policy_display(policy_id)
        persona = self._build_persona(bundle, policy_id, None)
        history, final_record = self._execute_debate(bundle, task_header, policy_scope, persona_context=persona)
        arbiter_result = self._build_arbiter_result(bundle, history, final_record, task_header, policy_scope)
        adjudication_report = self._build_adjudication_report(
            policy_id,
            bundle,
            history,
            final_record,
            arbiter_result,
        )
        result = build_debate_result(
            session_id,
            bundle,
            history,
            final_record,
            arbiter_result=arbiter_result,
            adjudication_report=adjudication_report,
            persona=persona,
        )
        result["policy_id"] = policy_id
        self._persist_completed_session(
            session_id=session_id,
            source_endpoint="/api/debate",
            bundle=bundle,
            history=history,
            final_record=final_record,
            started_at=started_at,
            policy_id=policy_id,
            arbiter_result=arbiter_result,
            adjudication_report=adjudication_report,
            persona=persona,
        )
        return result

    def run_debate_with_bundle(
        self,
        bundle: EvidenceBundle,
        policy_id: str = "POLICY_001",
        source_endpoint: str = "/api/debate",
        manual_supplements: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        bundle = self._prioritize_manual_evidence(bundle)
        session_id = str(uuid.uuid4())
        started_at = self._utcnow()
        task_header, policy_scope = self._policy_display(policy_id)
        persona = self._build_persona(bundle, policy_id, None)
        history, final_record = self._execute_debate(bundle, task_header, policy_scope, persona_context=persona)
        arbiter_result = self._build_arbiter_result(bundle, history, final_record, task_header, policy_scope)
        adjudication_report = self._build_adjudication_report(
            policy_id,
            bundle,
            history,
            final_record,
            arbiter_result,
        )
        resolved_manual_supplements = self._resolve_manual_supplements(manual_supplements, adjudication_report)
        result = build_debate_result(
            session_id,
            bundle,
            history,
            final_record,
            arbiter_result=arbiter_result,
            adjudication_report=adjudication_report,
            manual_supplements=resolved_manual_supplements,
            persona=persona,
        )
        result["policy_id"] = policy_id
        self._persist_completed_session(
            session_id=session_id,
            source_endpoint=source_endpoint,
            bundle=bundle,
            history=history,
            final_record=final_record,
            started_at=started_at,
            policy_id=policy_id,
            arbiter_result=arbiter_result,
            adjudication_report=adjudication_report,
            manual_supplements=resolved_manual_supplements,
            persona=persona,
        )
        return result

    def run_debate_stream(self, id_card: str, policy_id: str = "POLICY_001") -> Generator[str, None, None]:
        session_id = str(uuid.uuid4())
        started_at = self._utcnow()
        task_header, policy_scope = self._policy_display(policy_id)

        try:
            planner = EvidencePlanner()
            plan = planner.plan(person_id=id_card, policy_id=policy_id)
            
            yield self._build_sse_event("system_trace", {"log": f"[Sys] 成功加载系统目标：{plan.packet_summary}", "status": "info"})
            time.sleep(0.3)
            yield self._build_sse_event("system_trace", {"log": f"[Plan] Evidence Planner 已完成拆解，共生成 {len(plan.items)} 个侦查断点。", "status": "success"})
            time.sleep(0.4)
            # 逐条输出取证任务，避免前端只看到聚合摘要。
            for item in plan.items:
                yield self._build_sse_event(
                    "system_trace",
                    {"log": f"  - [Rule: {item.rule_type}] {item.rule_name}", "status": "warning"},
                )
                time.sleep(0.15)
            yield self._build_sse_event("system_trace", {"log": "[Agent: Text2SQL] Agent 鎺ョ鍙栬瘉闃熷垪锛屽璺姩鎬佷唬鐮佺敓鎴愪腑...", "status": "info"})
            time.sleep(0.5)
            yield self._build_sse_event("system_trace", {"log": "[Sys] 搴曞眰璇佹嵁鐭╅樀鏋勫缓瀹屾瘯锛屾暟鎹€荤嚎宸插榻愶紝鎶曞叆杩涘叆浠茶搴?..", "status": "success"})
            time.sleep(0.4)
        except Exception as e:
            logger.error(f"Trace generation failed: {e}")
            yield self._build_sse_event(
                "system_trace",
                {"log": f"[Plan] 取证规划阶段异常：{e}", "status": "danger"},
            )

        # 鐪熸寮€濮嬫祦寮忔敹闆嗚瘉鎹細
        bundle = EvidenceBundle(id_card=id_card)
        for evidence_item in self.collector.collect_stream(id_card, policy_id=policy_id):
            bundle.items.append(evidence_item)
            # 濮ｅ繑顐奸弻銉ュ毉娑撯偓閺夆槄绱濈亸鍗炲弿闁插繑甯归柅浣虹舶閸撳秶顏崚閿嬫煀 EvidenceBoard
            yield self._build_sse_event("evidence", self._build_stream_evidence(bundle))

        history: list[DebateRecord] = []
        projection = project_evidence(bundle, task_header, policy_scope)
        persona = self._build_persona(bundle, policy_id, None)
        yield self._build_sse_event("persona_ready", persona)

        r0_judgments: list[AgentJudgment] = []
        for agent in self.agents:
            try:
                case_summaries = self._empirical_case_context(agent, projection)
                judgment = agent.judge(
                    projection,
                    debate_round=0,
                    case_summaries=case_summaries,
                    persona_context=persona,
                    tools=self.tools,
                    tool_registry=self.tool_registry,
                    tool_policy=self.debate_tool_policy,
                )
            except Exception as exc:
                logger.error("{} round-0 judgment failed: {}", agent.AGENT_ROLE, exc)
                judgment = self._create_fallback_judgment(agent, 0, str(exc))
            r0_judgments.append(judgment)
            yield self._build_sse_event("agent_judgment", self._judgment_to_payload(judgment))

        last_record = DebateRecord(r0_judgments, 0)
        history.append(last_record)

        for round_idx in range(1, self.max_rounds + 1):
            if last_record.is_consensus_reached:
                break

            yield self._build_sse_event("round_start", round_idx)
            current_judgments: list[AgentJudgment] = []
            for agent in self.agents:
                try:
                    case_summaries = self._empirical_case_context(agent, projection)
                    judgment = agent.debate_respond(
                        projection,
                        last_record.judgments,
                        debate_round=round_idx,
                        case_summaries=case_summaries,
                        persona_context=persona,
                        tools=self.tools,
                        tool_registry=self.tool_registry,
                        tool_policy=self.debate_tool_policy,
                    )
                except Exception as exc:
                    logger.error("{} debate response failed: {}", agent.AGENT_ROLE, exc)
                    judgment = self._create_fallback_judgment(agent, round_idx, str(exc))
                current_judgments.append(judgment)
                yield self._build_sse_event("agent_judgment", self._judgment_to_payload(judgment))

            last_record = DebateRecord(current_judgments, round_idx)
            history.append(last_record)

        arbiter_result = self._build_arbiter_result(bundle, history, last_record, task_header, policy_scope)
        adjudication_report = self._build_adjudication_report(
            policy_id,
            bundle,
            history,
            last_record,
            arbiter_result,
        )
        result = build_debate_result(
            session_id,
            bundle,
            history,
            last_record,
            arbiter_result=arbiter_result,
            adjudication_report=adjudication_report,
            persona=persona,
        )
        result["policy_id"] = policy_id
        self._persist_completed_session(
            session_id=session_id,
            source_endpoint="/api/debate_stream",
            bundle=bundle,
            history=history,
            final_record=last_record,
            started_at=started_at,
            policy_id=policy_id,
            arbiter_result=arbiter_result,
            adjudication_report=adjudication_report,
            persona=persona,
        )
        yield self._build_sse_event("debate_final", result)

    def run_debate_stream_with_bundle(
        self,
        bundle: EvidenceBundle,
        policy_id: str = "POLICY_001",
        manual_supplements: list[dict[str, object]] | None = None,
    ) -> Generator[str, None, None]:
        bundle = self._prioritize_manual_evidence(bundle)
        session_id = str(uuid.uuid4())
        started_at = self._utcnow()
        task_header, policy_scope = self._policy_display(policy_id)

        yield self._build_sse_event(
            "system_trace",
            {
                "log": f"[Plan] 复用现有证据，跳过取证阶段（共 {len(bundle.items)} 条）。",
                "status": "success",
            },
        )
        yield self._build_sse_event(
            "system_trace",
            {
                "log": "[Plan] 人工核验补证已启用最高优先级：同条款将覆盖系统证据。",
                "status": "warning",
            },
        )

        history: list[DebateRecord] = []
        projection = project_evidence(bundle, task_header, policy_scope)
        persona = self._build_persona(bundle, policy_id, None)
        yield self._build_sse_event("persona_ready", persona)
        r0_judgments: list[AgentJudgment] = []
        for agent in self.agents:
            try:
                case_summaries = self._empirical_case_context(agent, projection)
                judgment = agent.judge(
                    projection,
                    debate_round=0,
                    case_summaries=case_summaries,
                    persona_context=persona,
                    tools=self.tools,
                    tool_registry=self.tool_registry,
                    tool_policy=self.debate_tool_policy,
                )
            except Exception as exc:
                logger.error("{} round-0 judgment failed: {}", agent.AGENT_ROLE, exc)
                judgment = self._create_fallback_judgment(agent, 0, str(exc))
            r0_judgments.append(judgment)
            yield self._build_sse_event("agent_judgment", self._judgment_to_payload(judgment))

        last_record = DebateRecord(r0_judgments, 0)
        history.append(last_record)

        for round_idx in range(1, self.max_rounds + 1):
            if last_record.is_consensus_reached:
                break
            yield self._build_sse_event("round_start", round_idx)
            current_judgments: list[AgentJudgment] = []
            for agent in self.agents:
                try:
                    case_summaries = self._empirical_case_context(agent, projection)
                    judgment = agent.debate_respond(
                        projection,
                        last_record.judgments,
                        debate_round=round_idx,
                        case_summaries=case_summaries,
                        persona_context=persona,
                        tools=self.tools,
                        tool_registry=self.tool_registry,
                        tool_policy=self.debate_tool_policy,
                    )
                except Exception as exc:
                    logger.error("{} debate response failed: {}", agent.AGENT_ROLE, exc)
                    judgment = self._create_fallback_judgment(agent, round_idx, str(exc))
                current_judgments.append(judgment)
                yield self._build_sse_event("agent_judgment", self._judgment_to_payload(judgment))

            last_record = DebateRecord(current_judgments, round_idx)
            history.append(last_record)

        arbiter_result = self._build_arbiter_result(bundle, history, last_record, task_header, policy_scope)
        adjudication_report = self._build_adjudication_report(
            policy_id,
            bundle,
            history,
            last_record,
            arbiter_result,
        )
        resolved_manual_supplements = self._resolve_manual_supplements(manual_supplements, adjudication_report)
        result = build_debate_result(
            session_id,
            bundle,
            history,
            last_record,
            arbiter_result=arbiter_result,
            adjudication_report=adjudication_report,
            manual_supplements=resolved_manual_supplements,
            persona=persona,
        )
        result["policy_id"] = policy_id
        self._persist_completed_session(
            session_id=session_id,
            source_endpoint="/api/debate_stream",
            bundle=bundle,
            history=history,
            final_record=last_record,
            started_at=started_at,
            policy_id=policy_id,
            arbiter_result=arbiter_result,
            adjudication_report=adjudication_report,
            manual_supplements=resolved_manual_supplements,
            persona=persona,
        )
        yield self._build_sse_event("debate_final", result)

    def _execute_debate(
        self,
        bundle: EvidenceBundle,
        task_header: str = DEFAULT_TASK_HEADER,
        policy_scope: str = DEFAULT_POLICY_SCOPE,
        persona_context: dict | None = None,
    ) -> tuple[list[DebateRecord], DebateRecord]:
        history: list[DebateRecord] = []

        current_record = self._run_round_zero(bundle, task_header, policy_scope, persona_context=persona_context)
        history.append(current_record)
        if current_record.is_consensus_reached:
            return history, current_record

        for round_idx in range(1, self.max_rounds + 1):
            current_record = self._run_debate_round(
                bundle,
                current_record,
                round_idx,
                task_header,
                policy_scope,
                persona_context=persona_context,
            )
            history.append(current_record)
            if current_record.is_consensus_reached:
                break

        return history, current_record

    def _run_round_zero(
        self,
        bundle: EvidenceBundle,
        task_header: str = DEFAULT_TASK_HEADER,
        policy_scope: str = DEFAULT_POLICY_SCOPE,
        persona_context: dict | None = None,
    ) -> DebateRecord:
        projection = project_evidence(bundle, task_header, policy_scope)
        judgments: list[AgentJudgment] = []
        for agent in self.agents:
            try:
                judgments.append(
                    agent.judge(
                        projection,
                        debate_round=0,
                        case_summaries=self._empirical_case_context(agent, projection),
                        persona_context=persona_context,
                        tools=self.tools,
                        tool_registry=self.tool_registry,
                        tool_policy=self.debate_tool_policy,
                    )
                )
            except Exception as exc:
                logger.error("{} round-0 judgment failed: {}", agent.AGENT_ROLE, exc)
                judgments.append(self._create_fallback_judgment(agent, 0, str(exc)))
        return DebateRecord(judgments, 0)

    def _run_debate_round(
        self,
        bundle: EvidenceBundle,
        previous_record: DebateRecord,
        round_idx: int,
        task_header: str = DEFAULT_TASK_HEADER,
        policy_scope: str = DEFAULT_POLICY_SCOPE,
        persona_context: dict | None = None,
    ) -> DebateRecord:
        projection = project_evidence(bundle, task_header, policy_scope)
        judgments: list[AgentJudgment] = []
        for agent in self.agents:
            try:
                judgments.append(
                    agent.debate_respond(
                        projection,
                        previous_record.judgments,
                        debate_round=round_idx,
                        case_summaries=self._empirical_case_context(agent, projection),
                        persona_context=persona_context,
                        tools=self.tools,
                        tool_registry=self.tool_registry,
                        tool_policy=self.debate_tool_policy,
                    )
                )
            except Exception as exc:
                logger.error("{} debate response failed: {}", agent.AGENT_ROLE, exc)
                judgments.append(self._create_fallback_judgment(agent, round_idx, str(exc)))
        return DebateRecord(judgments, round_idx)

    def _create_fallback_judgment(self, agent, round_idx: int, err_msg: str) -> AgentJudgment:
        return AgentJudgment(
            agent_id=agent.AGENT_ID,
            agent_role=agent.AGENT_ROLE,
            debate_round=round_idx,
            conclusion=CONCLUSION_MISSING,
            stance=STANCE_PENDING,
            confidence=0.0,
            evidence_refs=[],
            reasoning=f"缁崵绮洪柨娆掝嚖鐎佃壈鍤ч崚銈嗘焽婢惰精瑙? {err_msg}",
            dissent_points=[],
            key_finding="兜底判定：Agent 执行异常，结论降级为待定。",
        )

    def _build_stream_evidence(self, bundle: EvidenceBundle) -> list[dict[str, object]]:
        return [
            {
                "rule_id": item.rule_id,
                "target": item.target,
                "category": item.category,
                "exec_status": item.exec_status,
                "diagnostic_code": item.diagnostic_code,
                "diagnostic_label": item.diagnostic_label,
                "diagnostic_detail": item.diagnostic_detail,
                "diagnostic_hint": item.diagnostic_hint,
                "supports_conclusion": item.supports_conclusion,
                "result_summary": item.result_summary,
                "sql": item.sql,
                "result_raw": item.result_raw,
                **build_item_semantics(item),
            }
            for item in bundle.items
        ]

    def _build_sse_event(self, event: str, data: object) -> str:
        return f"data: {json.dumps({'event': event, 'data': data}, ensure_ascii=False, default=str)}\n\n"

    def _judgment_to_payload(self, judgment: AgentJudgment) -> dict[str, object]:
        return judgment.model_dump()

    def _build_arbiter_result(
        self,
        bundle: EvidenceBundle,
        history: list[DebateRecord],
        final_record: DebateRecord,
        task_header: str,
        policy_scope: str,
    ) -> dict[str, object]:
        projection = project_evidence(bundle, task_header, policy_scope)
        return self.arbiter.explain(projection, history, final_record).to_dict()

    def _build_adjudication_report(
        self,
        policy_id: str,
        bundle: EvidenceBundle,
        history: list[DebateRecord],
        final_record: DebateRecord,
        arbiter_result: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return build_adjudication_report(
            policy_id=policy_id,
            bundle=bundle,
            history=history,
            final_record=final_record,
            arbiter_result=arbiter_result or {},
        )

    def _build_persona(
        self,
        bundle: EvidenceBundle,
        policy_id: str,
        final_conclusion: str | None,
    ) -> dict[str, object]:
        try:
            builder = PersonaBuilder()
            return builder.build(
                id_card=bundle.id_card,
                policy_id=policy_id,
                evidence_bundle=bundle,
                final_conclusion=final_conclusion,
            )
        except Exception as exc:
            logger.exception("Persona build failed: id_card={} policy_id={}", bundle.id_card, policy_id)
            return {
                "error": str(exc),
                "title": f"{bundle.id_card} 画像构建失败",
                "archetype": "画像构建失败",
            }

    def _persist_completed_session(
        self,
        session_id: str,
        source_endpoint: str,
        bundle: EvidenceBundle,
        history: list[DebateRecord],
        final_record: DebateRecord,
        started_at: datetime,
        policy_id: str = "POLICY_001",
        arbiter_result: dict[str, object] | None = None,
        adjudication_report: dict[str, object] | None = None,
        manual_supplements: list[dict[str, object]] | None = None,
        persona: dict[str, object] | None = None,
    ) -> None:
        completed_at = self._utcnow()
        try:
            persist_completed_session(
                session_id=session_id,
                source_endpoint=source_endpoint,
                bundle=bundle,
                history=history,
                final_record=final_record,
                started_at=started_at,
                completed_at=completed_at,
                policy_id=policy_id,
                arbiter_result=arbiter_result,
                adjudication_report=adjudication_report,
                manual_supplements=manual_supplements,
                persona=persona,
            )
        except DebatePersistenceError:
            logger.exception(
                "Completed debate session persistence failed: session={} endpoint={}",
                session_id,
                source_endpoint,
            )
            raise

    def _utcnow(self) -> datetime:
        return datetime.now(UTC).replace(tzinfo=None)

    def _is_manual_evidence(self, item) -> bool:
        if bool(getattr(item, "manual_verified", False)):
            return True
        return str(getattr(item, "category", "") or "") == "manual_supplement"

    def _prioritize_manual_evidence(self, bundle: EvidenceBundle) -> EvidenceBundle:
        chosen: dict[str, object] = {}
        manual_locked: dict[str, bool] = {}

        for item in bundle.items:
            rule_id = str(getattr(item, "rule_id", "") or "").strip()
            if not rule_id:
                continue

            is_manual = self._is_manual_evidence(item)
            if rule_id not in chosen:
                chosen[rule_id] = item
                manual_locked[rule_id] = is_manual
                continue

            if manual_locked.get(rule_id, False):
                if is_manual:
                    chosen[rule_id] = item
                continue

            if is_manual:
                chosen[rule_id] = item
                manual_locked[rule_id] = True
            else:
                chosen[rule_id] = item

        prioritized_items = list(chosen.values())
        if len(prioritized_items) == len(bundle.items):
            return bundle
        return EvidenceBundle(
            id_card=bundle.id_card,
            collected_at=bundle.collected_at,
            items=prioritized_items,
        )

    def _resolve_manual_supplements(
        self,
        manual_supplements: list[dict[str, object]] | None,
        adjudication_report: dict[str, object] | None,
    ) -> list[dict[str, object]]:
        if not manual_supplements:
            return []

        clause_rows = (
            adjudication_report.get("clause_results", [])
            if isinstance(adjudication_report, dict)
            else []
        )
        clause_by_id = {
            str(row.get("clause_id", "")).strip(): row
            for row in clause_rows
            if isinstance(row, dict) and row.get("clause_id")
        }

        reviewed_at = self._utcnow().isoformat()
        resolved: list[dict[str, object]] = []

        for raw in manual_supplements:
            if not isinstance(raw, dict):
                continue

            row = dict(raw)
            status = str(row.get("status") or "pending_review")
            clause_id = str(row.get("clause_id") or "").strip()
            if status != "pending_review" or not clause_id:
                resolved.append(row)
                continue

            clause = clause_by_id.get(clause_id)
            stance = str(row.get("stance") or "support").strip().lower()

            review_status = ""
            review_effect = ""
            review_reason = "人工核验补证为最高优先级，已直接采纳。"
            adopted = True

            if isinstance(clause, dict):
                review_status = str(clause.get("semantic_display_label") or clause.get("status") or "")
                review_effect = str(clause.get("semantic_decision_effect") or "")
                if stance == "support":
                    review_reason = "人工核验补证（支持）为最高优先级，已直接采纳。"
                elif stance == "refute":
                    review_reason = "人工核验补证（反驳）为最高优先级，已直接采纳。"
                else:
                    review_reason = "人工核验补证为最高优先级，已直接采纳。"

            row["status"] = "adopted" if adopted else "not_adopted"
            row["reviewed_at"] = reviewed_at
            row["review_status"] = review_status
            row["review_effect"] = review_effect
            row["review_reason"] = review_reason
            resolved.append(row)

        return resolved
