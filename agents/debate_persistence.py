"""
Persistence helpers for completed debate sessions.

This module defines the canonical storage contract used by the runtime and the
MySQL DDL. Only successfully completed sessions are persisted.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from typing import Any, Sequence

from sqlalchemy import text

from agents.decision_semantics import build_item_semantics, conclusion_tag_type
from config.database import get_session
from evidence.evidence_model import EvidenceBundle, EvidenceItem


class DebatePersistenceError(RuntimeError):
    """Raised when a completed debate session cannot be persisted."""


class DebateSessionNotFoundError(LookupError):
    """Raised when a saved debate session cannot be found."""


@dataclass(frozen=True)
class PersistedDebateSession:
    """Canonical persisted payload for one completed debate session."""

    session_row: dict[str, Any]
    log_rows: list[dict[str, Any]]
    snapshot: dict[str, Any]


def _model_dump(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def _isoformat(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat()


def _normalize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return _isoformat(value)
    if isinstance(value, Decimal):
        return float(value)
    return value


def serialize_evidence_item(item: EvidenceItem) -> dict[str, Any]:
    return {
        "evidence_id": item.evidence_id,
        "rule_id": item.rule_id,
        "target_id_card": item.target_id_card,
        "target": item.target,
        "category": item.category,
        "sql": item.sql,
        "result_raw": item.result_raw,
        "result_summary": item.result_summary,
        "time_range": item.time_range,
        "supports_conclusion": item.supports_conclusion,
        "confidence": item.confidence,
        "exec_status": item.exec_status,
        "diagnostic_code": item.diagnostic_code,
        "diagnostic_label": item.diagnostic_label,
        "diagnostic_detail": item.diagnostic_detail,
        "diagnostic_hint": item.diagnostic_hint,
        "manual_verified": item.manual_verified,
        "manual_stance": item.manual_stance,
        "created_at": _isoformat(item.created_at),
        **build_item_semantics(item),
    }


def serialize_evidence_bundle(bundle: EvidenceBundle) -> list[dict[str, Any]]:
    return [serialize_evidence_item(item) for item in bundle.items]


def serialize_history(history: Sequence[Any]) -> list[dict[str, Any]]:
    serialized_history: list[dict[str, Any]] = []
    for record in history:
        serialized_history.append(
            {
                "round_num": record.round_num,
                "judgments": [_model_dump(judgment) for judgment in record.judgments],
                "total": record.total,
                "majority_stance": record.majority_stance,
                "majority_count": record.majority_count,
                "consensus_rate": record.consensus_rate,
                "is_consensus_reached": record.is_consensus_reached,
            }
        )
    return serialized_history


def build_debate_result(
    session_id: str,
    bundle: EvidenceBundle,
    history: Sequence[Any],
    final_record: Any,
    arbiter_result: dict[str, Any] | None = None,
    adjudication_report: dict[str, Any] | None = None,
    manual_supplements: list[dict[str, Any]] | None = None,
    persona: dict[str, Any] | None = None,
) -> dict[str, Any]:
    final_conclusion = final_record.get_final_conclusion()
    return {
        "session_id": session_id,
        "id_card": bundle.id_card,
        "evidence_count": len(bundle.items),
        "rounds_taken": final_record.round_num,
        "final_conclusion": final_conclusion,
        "final_conclusion_tag_type": conclusion_tag_type(final_conclusion),
        "final_stance": final_record.majority_stance,
        "consensus_rate": final_record.consensus_rate,
        "is_consensus_reached": final_record.is_consensus_reached,
        "history": serialize_history(history),
        "arbiter_result": arbiter_result or {},
        "adjudication_report": adjudication_report or {},
        "manual_supplements": manual_supplements or [],
        "persona": persona or {},
    }


def build_completed_session_records(
    session_id: str,
    source_endpoint: str,
    bundle: EvidenceBundle,
    history: Sequence[Any],
    final_record: Any,
    started_at: datetime,
    completed_at: datetime,
    policy_id: str = "POLICY_001",
    arbiter_result: dict[str, Any] | None = None,
    adjudication_report: dict[str, Any] | None = None,
    manual_supplements: list[dict[str, Any]] | None = None,
    persona: dict[str, Any] | None = None,
) -> PersistedDebateSession:
    history_payload = serialize_history(history)
    evidence_payload = serialize_evidence_bundle(bundle)
    result_payload = build_debate_result(
        session_id,
        bundle,
        history,
        final_record,
        arbiter_result=arbiter_result,
        adjudication_report=adjudication_report,
        manual_supplements=manual_supplements,
        persona=persona,
    )
    agent_count = len(history[0].judgments) if history else 0

    session_row = {
        "session_id": session_id,
        "id_card": bundle.id_card,
        "policy_id": policy_id,
        "status": "completed",
        "source_endpoint": source_endpoint,
        "final_conclusion": result_payload["final_conclusion"],
        "final_stance": result_payload["final_stance"],
        "consensus_rate": final_record.consensus_rate,
        "is_consensus_reached": int(final_record.is_consensus_reached),
        "rounds_taken": final_record.round_num,
        "evidence_count": len(bundle.items),
        "agent_count": agent_count,
        "started_at": started_at,
        "completed_at": completed_at,
    }

    snapshot = {
        **result_payload,
        "policy_id": policy_id,
        "status": session_row["status"],
        "source_endpoint": source_endpoint,
        "started_at": _isoformat(started_at),
        "completed_at": _isoformat(completed_at),
        "summary": {
            "status": session_row["status"],
            "policy_id": policy_id,
            "source_endpoint": source_endpoint,
            "final_conclusion": session_row["final_conclusion"],
            "final_stance": session_row["final_stance"],
            "consensus_rate": session_row["consensus_rate"],
            "is_consensus_reached": bool(session_row["is_consensus_reached"]),
            "rounds_taken": session_row["rounds_taken"],
            "evidence_count": session_row["evidence_count"],
            "agent_count": session_row["agent_count"],
        },
        "evidence": evidence_payload,
    }

    session_row["snapshot_payload"] = _json_dumps(snapshot)

    log_rows: list[dict[str, Any]] = []
    for record in history:
        for judgment in record.judgments:
            log_rows.append(
                {
                    "session_id": session_id,
                    "id_card": bundle.id_card,
                    "debate_round": record.round_num,
                    "agent_id": judgment.agent_id,
                    "agent_role": judgment.agent_role,
                    "conclusion": judgment.conclusion,
                    "stance": judgment.stance,
                    "confidence": judgment.confidence,
                    "evidence_refs": _json_dumps(judgment.evidence_refs),
                    "reasoning": judgment.reasoning,
                    "dissent_points": _json_dumps(judgment.dissent_points),
                    "key_finding": judgment.key_finding,
                    "round_majority_stance": record.majority_stance,
                    "round_consensus_rate": record.consensus_rate,
                    "round_is_consensus_reached": int(record.is_consensus_reached),
                }
            )

    return PersistedDebateSession(
        session_row=session_row,
        log_rows=log_rows,
        snapshot=snapshot,
    )


def _build_history_summary_row(row: dict[str, Any]) -> dict[str, Any]:
    summary_fields = [
        "session_id",
        "id_card",
        "policy_id",
        "status",
        "source_endpoint",
        "final_conclusion",
        "final_stance",
        "consensus_rate",
        "is_consensus_reached",
        "rounds_taken",
        "evidence_count",
        "completed_at",
    ]
    summary = {
        field: _normalize_value(row[field])
        for field in summary_fields
        if field in row
    }
    if "is_consensus_reached" in summary:
        summary["is_consensus_reached"] = bool(summary["is_consensus_reached"])
    return summary


def list_saved_sessions(id_card: str = None) -> list[dict[str, Any]]:
    where_clause = "WHERE id_card = :id_card" if id_card else ""
    query_sql = text(
        f"""
        SELECT
            session_id,
            id_card,
            policy_id,
            status,
            source_endpoint,
            final_conclusion,
            final_stance,
            consensus_rate,
            is_consensus_reached,
            rounds_taken,
            evidence_count,
            completed_at
        FROM debate_session
        {where_clause}
        ORDER BY completed_at DESC, created_at DESC
        """
    )

    with get_session() as session:
        params = {"id_card": id_card} if id_card else {}
        rows = session.execute(query_sql, params).mappings().all()

    return [_build_history_summary_row(dict(row)) for row in rows]


def _apply_detail_defaults(row: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    detail = dict(snapshot)
    detail.setdefault("session_id", row["session_id"])
    detail.setdefault("id_card", row["id_card"])
    detail.setdefault("status", row["status"])
    detail.setdefault("source_endpoint", row["source_endpoint"])
    detail.setdefault("completed_at", _normalize_value(row["completed_at"]))
    return detail


def get_saved_session_detail(session_id: str) -> dict[str, Any]:
    query_sql = text(
        """
        SELECT
            session_id,
            id_card,
            status,
            source_endpoint,
            completed_at,
            snapshot_payload
        FROM debate_session
        WHERE session_id = :session_id
        """
    )

    with get_session() as session:
        row = session.execute(query_sql, {"session_id": session_id}).mappings().first()

    if row is None:
        raise DebateSessionNotFoundError(f"Saved debate session not found: {session_id}")

    row_dict = dict(row)
    snapshot = json.loads(row_dict["snapshot_payload"])
    return _apply_detail_defaults(row_dict, snapshot)


def persist_completed_session(
    session_id: str,
    source_endpoint: str,
    bundle: EvidenceBundle,
    history: Sequence[Any],
    final_record: Any,
    started_at: datetime,
    completed_at: datetime,
    policy_id: str = "POLICY_001",
    arbiter_result: dict[str, Any] | None = None,
    adjudication_report: dict[str, Any] | None = None,
    manual_supplements: list[dict[str, Any]] | None = None,
    persona: dict[str, Any] | None = None,
) -> PersistedDebateSession:
    persisted = build_completed_session_records(
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

    insert_session_sql = text(
        """
        INSERT INTO debate_session (
            session_id,
            id_card,
            policy_id,
            status,
            source_endpoint,
            final_conclusion,
            final_stance,
            consensus_rate,
            is_consensus_reached,
            rounds_taken,
            evidence_count,
            agent_count,
            started_at,
            completed_at,
            snapshot_payload
        ) VALUES (
            :session_id,
            :id_card,
            :policy_id,
            :status,
            :source_endpoint,
            :final_conclusion,
            :final_stance,
            :consensus_rate,
            :is_consensus_reached,
            :rounds_taken,
            :evidence_count,
            :agent_count,
            :started_at,
            :completed_at,
            :snapshot_payload
        )
        """
    )

    insert_log_sql = text(
        """
        INSERT INTO agent_debate_log (
            session_id,
            id_card,
            debate_round,
            agent_id,
            agent_role,
            conclusion,
            stance,
            confidence,
            evidence_refs,
            reasoning,
            dissent_points,
            key_finding,
            round_majority_stance,
            round_consensus_rate,
            round_is_consensus_reached
        ) VALUES (
            :session_id,
            :id_card,
            :debate_round,
            :agent_id,
            :agent_role,
            :conclusion,
            :stance,
            :confidence,
            :evidence_refs,
            :reasoning,
            :dissent_points,
            :key_finding,
            :round_majority_stance,
            :round_consensus_rate,
            :round_is_consensus_reached
        )
        """
    )

    try:
        with get_session() as session:
            session.execute(insert_session_sql, persisted.session_row)
            for row in persisted.log_rows:
                session.execute(insert_log_sql, row)
    except Exception as exc:
        raise DebatePersistenceError(
            f"Failed to persist completed debate session {session_id}"
        ) from exc

    return persisted
