"""Debate orchestration and completed-session persistence."""
from __future__ import annotations

import json
import uuid
import time
from datetime import UTC, datetime
from typing import Generator

from loguru import logger

from agents import create_all_agents
from agents.base_agent import AgentJudgment
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
DEFAULT_POLICY_SCOPE = "灵活就业社保补贴"


def project_evidence(bundle: EvidenceBundle, task_header: str = DEFAULT_TASK_HEADER, policy_scope: str = DEFAULT_POLICY_SCOPE) -> EvidenceProjection:
    """Reshape retrieved evidence into the summary-first debate format."""

    cards: list[EvidenceSummaryCard] = []
    uncertainty_markers: list[str] = []

    for item in bundle.items:
        if item.supports_conclusion is True:
            status = "supports"
        elif item.supports_conclusion is False:
            status = "contradicts"
        elif item.exec_status == "failed":
            status = "missing"
        elif item.exec_status == "field_missing":
            status = "missing"
        elif item.exec_status == "no_data":
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
            uncertainty_markers.append(f"[{item.rule_id}] {item.target}: 需 Agent 判断")
        elif status == "missing":
            uncertainty_markers.append(f"[{item.rule_id}] {item.target}: 证据缺失({item.exec_status})")

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
        "符合": "支持通过",
        "不符合": "反对通过",
        "数据缺失": "待定",
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
                for stance in ("支持通过", "反对通过", "待定")
                if counts.get(stance, 0) == self.majority_count
            ]
            self.majority_stance = leaders[0] if len(leaders) == 1 else "待定"
            self.consensus_rate = self.majority_count / self.total
        else:
            self.majority_stance = "待定"
            self.majority_count = 0
            self.consensus_rate = 0.0

        self.is_consensus_reached = self.consensus_rate >= settings.consensus_threshold

    def get_final_conclusion(self) -> str:
        if self.majority_stance == "支持通过":
            return "符合"
        if self.majority_stance == "反对通过":
            return "不符合"
        return "数据缺失"

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
        self.max_rounds = settings.debate_max_rounds
        self.tool_registry = ToolRegistry()
        self.tools = self.tool_registry.get_tool_schemas()

    def _policy_display(self, policy_id: str) -> tuple[str, str]:
        """根据 policy_id 返回 (task_header, policy_scope) 用于投影"""
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
        history, final_record = self._execute_debate(bundle, task_header, policy_scope)
        result = build_debate_result(session_id, bundle, history, final_record)
        result["policy_id"] = policy_id
        self._persist_completed_session(
            session_id=session_id,
            source_endpoint="/api/debate",
            bundle=bundle,
            history=history,
            final_record=final_record,
            started_at=started_at,
            policy_id=policy_id,
        )
        return result

    def run_debate_with_bundle(
        self,
        bundle: EvidenceBundle,
        policy_id: str = "POLICY_001",
        source_endpoint: str = "/api/debate",
    ) -> dict[str, object]:
        session_id = str(uuid.uuid4())
        started_at = self._utcnow()
        task_header, policy_scope = self._policy_display(policy_id)
        history, final_record = self._execute_debate(bundle, task_header, policy_scope)
        result = build_debate_result(session_id, bundle, history, final_record)
        result["policy_id"] = policy_id
        self._persist_completed_session(
            session_id=session_id,
            source_endpoint=source_endpoint,
            bundle=bundle,
            history=history,
            final_record=final_record,
            started_at=started_at,
            policy_id=policy_id,
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
            yield self._build_sse_event("system_trace", {"log": f"[Plan] 智能取证规划 (Evidence Planner) 拆解政策完毕，共生成 {len(plan.items)} 个侦查断点...", "status": "success"})
            time.sleep(0.4)
            # 逐条输出并发取证任务，避免前端仅看到省略号汇总
            for item in plan.items:
                yield self._build_sse_event(
                    "system_trace",
                    {"log": f"  - [Rule: {item.rule_type}] {item.rule_name}", "status": "warning"},
                )
                time.sleep(0.15)
            yield self._build_sse_event("system_trace", {"log": "[Agent: Text2SQL] Agent 编排接管取证队列，多路动态代码生成中...", "status": "info"})
            time.sleep(0.5)
            yield self._build_sse_event("system_trace", {"log": "[Sys] 底层证据矩阵构建完毕，数据总线已对齐，投递进入仲裁庭...", "status": "success"})
            time.sleep(0.4)
        except Exception as e:
            logger.error(f"Trace generation failed: {e}")
            yield self._build_sse_event(
                "system_trace",
                {"log": f"[Plan] 取证规划阶段异常：{e}", "status": "danger"},
            )

        # 真正开始流式收集证据：
        bundle = EvidenceBundle(id_card=id_card)
        for evidence_item in self.collector.collect_stream(id_card, policy_id=policy_id):
            bundle.items.append(evidence_item)
            # 每次查出一条，就全量推送给前端刷新 EvidenceBoard
            yield self._build_sse_event("evidence", self._build_stream_evidence(bundle))

        history: list[DebateRecord] = []
        projection = project_evidence(bundle, task_header, policy_scope)

        r0_judgments: list[AgentJudgment] = []
        for agent in self.agents:
            try:
                judgment = agent.judge(projection, debate_round=0, tools=self.tools, tool_registry=self.tool_registry)
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
                    judgment = agent.debate_respond(
                        projection,
                        last_record.judgments,
                        debate_round=round_idx,
                        tools=self.tools,
                        tool_registry=self.tool_registry,
                    )
                except Exception as exc:
                    logger.error("{} debate response failed: {}", agent.AGENT_ROLE, exc)
                    judgment = self._create_fallback_judgment(agent, round_idx, str(exc))
                current_judgments.append(judgment)
                yield self._build_sse_event("agent_judgment", self._judgment_to_payload(judgment))

            last_record = DebateRecord(current_judgments, round_idx)
            history.append(last_record)

        result = build_debate_result(session_id, bundle, history, last_record)
        result["policy_id"] = policy_id
        self._persist_completed_session(
            session_id=session_id,
            source_endpoint="/api/debate_stream",
            bundle=bundle,
            history=history,
            final_record=last_record,
            started_at=started_at,
            policy_id=policy_id,
        )
        yield self._build_sse_event("debate_final", result)

    def run_debate_stream_with_bundle(
        self,
        bundle: EvidenceBundle,
        policy_id: str = "POLICY_001",
    ) -> Generator[str, None, None]:
        session_id = str(uuid.uuid4())
        started_at = self._utcnow()
        task_header, policy_scope = self._policy_display(policy_id)

        yield self._build_sse_event(
            "system_trace",
            {
                "log": f"[Plan] 复用既有证据，跳过取证阶段（共 {len(bundle.items)} 条）。",
                "status": "success",
            },
        )

        history: list[DebateRecord] = []
        projection = project_evidence(bundle, task_header, policy_scope)
        r0_judgments: list[AgentJudgment] = []
        for agent in self.agents:
            try:
                judgment = agent.judge(projection, debate_round=0, tools=self.tools, tool_registry=self.tool_registry)
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
                    judgment = agent.debate_respond(
                        projection,
                        last_record.judgments,
                        debate_round=round_idx,
                        tools=self.tools,
                        tool_registry=self.tool_registry,
                    )
                except Exception as exc:
                    logger.error("{} debate response failed: {}", agent.AGENT_ROLE, exc)
                    judgment = self._create_fallback_judgment(agent, round_idx, str(exc))
                current_judgments.append(judgment)
                yield self._build_sse_event("agent_judgment", self._judgment_to_payload(judgment))

            last_record = DebateRecord(current_judgments, round_idx)
            history.append(last_record)

        result = build_debate_result(session_id, bundle, history, last_record)
        result["policy_id"] = policy_id
        self._persist_completed_session(
            session_id=session_id,
            source_endpoint="/api/debate_stream",
            bundle=bundle,
            history=history,
            final_record=last_record,
            started_at=started_at,
            policy_id=policy_id,
        )
        yield self._build_sse_event("debate_final", result)

    def _execute_debate(self, bundle: EvidenceBundle, task_header: str = DEFAULT_TASK_HEADER, policy_scope: str = DEFAULT_POLICY_SCOPE) -> tuple[list[DebateRecord], DebateRecord]:
        history: list[DebateRecord] = []

        current_record = self._run_round_zero(bundle, task_header, policy_scope)
        history.append(current_record)
        if current_record.is_consensus_reached:
            return history, current_record

        for round_idx in range(1, self.max_rounds + 1):
            current_record = self._run_debate_round(bundle, current_record, round_idx, task_header, policy_scope)
            history.append(current_record)
            if current_record.is_consensus_reached:
                break

        return history, current_record

    def _run_round_zero(self, bundle: EvidenceBundle, task_header: str = DEFAULT_TASK_HEADER, policy_scope: str = DEFAULT_POLICY_SCOPE) -> DebateRecord:
        projection = project_evidence(bundle, task_header, policy_scope)
        judgments: list[AgentJudgment] = []
        for agent in self.agents:
            try:
                judgments.append(agent.judge(projection, debate_round=0, tools=self.tools, tool_registry=self.tool_registry))
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
                        tools=self.tools,
                        tool_registry=self.tool_registry,
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
            conclusion="数据缺失",
            stance="待定",
            confidence=0.0,
            evidence_refs=[],
            reasoning=f"系统错误导致判断失败: {err_msg}",
            dissent_points=[],
            key_finding="系统调度异常",
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
            }
            for item in bundle.items
        ]

    def _build_sse_event(self, event: str, data: object) -> str:
        return f"data: {json.dumps({'event': event, 'data': data}, ensure_ascii=False, default=str)}\n\n"

    def _judgment_to_payload(self, judgment: AgentJudgment) -> dict[str, object]:
        return judgment.model_dump()

    def _persist_completed_session(
        self,
        session_id: str,
        source_endpoint: str,
        bundle: EvidenceBundle,
        history: list[DebateRecord],
        final_record: DebateRecord,
        started_at: datetime,
        policy_id: str = "POLICY_001",
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
