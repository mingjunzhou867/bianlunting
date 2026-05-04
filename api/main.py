"""FastAPI entrypoint for debate and retrieval APIs."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

# Allow running `python api/main.py` from repo root on Windows/Python.
if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from agents.debate_orchestrator import DebateOrchestrator
from agents.debate_persistence import (
    DebateSessionNotFoundError,
    confirm_manual_review,
    get_saved_session_detail,
    list_saved_sessions,
)
from evidence.evidence_model import EvidenceBundle, EvidenceItem, classify_evidence_diagnostic
from intent.intent_understanding_agent import IntentUnderstandingAgent
from policy.policy_router import get_policy
from reports.official_report_generator import ensure_official_report


DEFAULT_POLICY_ID = "POLICY_001"
VALID_EXEC_STATUSES = {"success", "no_data", "failed", "field_missing"}

app = FastAPI(title="Debate API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = DebateOrchestrator()
intent_agent = IntentUnderstandingAgent()


class DebateRequest(BaseModel):
    id_card: str = Field(..., min_length=1)
    user_query: str | None = None
    confirmed_policy_id: str | None = None
    reuse_evidence: bool = False
    evidence: list[dict[str, Any]] | None = None
    manual_supplements: list[dict[str, Any]] | None = None


class IntentRequest(BaseModel):
    user_query: str = Field(..., min_length=1)


class ManualReviewConfirmRequest(BaseModel):
    manual_supplements: list[dict[str, Any]] | None = None


def _normalize_confidence(value: Any, default: float = 1.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, number))


def _resolve_policy_id(request: DebateRequest) -> tuple[str | None, JSONResponse | None]:
    if request.confirmed_policy_id:
        return request.confirmed_policy_id, None

    if request.user_query and request.user_query.strip():
        intent = intent_agent.understand(request.user_query.strip())
        if intent.need_confirmation:
            return None, JSONResponse(
                status_code=200,
                content={"status": "need_confirmation", "data": intent.model_dump()},
            )
        return intent.policy_id or DEFAULT_POLICY_ID, None

    return DEFAULT_POLICY_ID, None


def _build_bundle_from_payload(id_card: str, raw_items: list[dict[str, Any]] | None) -> EvidenceBundle:
    if not raw_items:
        raise HTTPException(status_code=422, detail="reuse_evidence=true 时 evidence 不能为空")

    items: list[EvidenceItem] = []
    for idx, raw in enumerate(raw_items):
        if not isinstance(raw, dict):
            raise HTTPException(status_code=422, detail=f"evidence[{idx}] 必须为对象")

        rule_id = str(raw.get("rule_id") or f"REUSED_{idx + 1:03d}")
        exec_status = str(raw.get("exec_status") or "success")
        if exec_status not in VALID_EXEC_STATUSES:
            exec_status = "failed"

        error_message = str(raw.get("diagnostic_detail") or raw.get("result_summary") or "")
        code, label, detail, hint = classify_evidence_diagnostic(exec_status, error_message=error_message)

        item_payload: dict[str, Any] = {
            "evidence_id": str(raw.get("evidence_id") or f"REUSED_{rule_id}_{idx + 1}"),
            "rule_id": rule_id,
            "target_id_card": str(raw.get("target_id_card") or id_card),
            "target": str(raw.get("target") or rule_id),
            "category": str(raw.get("category") or "reused"),
            "sql": str(raw.get("sql") or ""),
            "result_raw": raw.get("result_raw") if isinstance(raw.get("result_raw"), list) else [],
            "result_summary": str(raw.get("result_summary") or ""),
            "time_range": raw.get("time_range"),
            "supports_conclusion": raw.get("supports_conclusion"),
            "confidence": _normalize_confidence(raw.get("confidence"), default=1.0),
            "exec_status": exec_status,
            "diagnostic_code": str(raw.get("diagnostic_code") or code),
            "diagnostic_label": str(raw.get("diagnostic_label") or label),
            "diagnostic_detail": str(raw.get("diagnostic_detail") or detail),
            "diagnostic_hint": str(raw.get("diagnostic_hint") or hint),
            "manual_verified": bool(raw.get("manual_verified") or False),
            "manual_stance": str(raw.get("manual_stance") or raw.get("stance") or "") or None,
        }
        if raw.get("created_at") is not None:
            item_payload["created_at"] = raw.get("created_at")

        try:
            items.append(EvidenceItem(**item_payload))
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"evidence[{idx}] 非法: {exc}") from exc

    return EvidenceBundle(id_card=id_card, items=items)


def _policy_conditions(policy_id: str) -> list[dict[str, Any]]:
    policy = get_policy(policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail=f"Policy not found: {policy_id}")

    rows: list[dict[str, Any]] = []

    for rule in policy.structured_rules.basic_conditions:
        rows.append(
            {
                "rule_id": rule.rule_id,
                "category": "基础条件",
                "tag_type": "success",
                "description": rule.description,
                "pass_condition": rule.pass_condition,
                "fail_condition": rule.fail_condition,
                "check_logic": rule.check_logic,
                "formula": rule.formula,
            }
        )

    for rule in policy.structured_rules.exclusion_conditions:
        rows.append(
            {
                "rule_id": rule.rule_id,
                "category": "排除条件",
                "tag_type": "danger",
                "description": rule.description,
                "pass_condition": rule.pass_condition,
                "fail_condition": rule.fail_condition,
                "check_logic": rule.check_logic,
                "formula": rule.formula,
            }
        )

    for rule in policy.structured_rules.inference_rules:
        rows.append(
            {
                "rule_id": rule.rule_id,
                "category": "合理推断",
                "tag_type": "warning",
                "description": rule.description,
                "pass_condition": rule.pass_condition,
                "fail_condition": rule.fail_condition,
                "check_logic": rule.check_logic,
                "formula": rule.formula,
            }
        )

    for rule in policy.structured_rules.calculation_rules:
        rows.append(
            {
                "rule_id": rule.rule_id,
                "category": "额度计算",
                "tag_type": "info",
                "description": rule.description,
                "pass_condition": rule.pass_condition,
                "fail_condition": rule.fail_condition,
                "check_logic": rule.check_logic,
                "formula": rule.formula,
            }
        )

    return rows


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/intent")
def recognize_intent(payload: IntentRequest) -> dict[str, Any]:
    intent = intent_agent.understand(payload.user_query.strip())
    return {"status": "success", "data": intent.model_dump()}


@app.get("/api/policy/{policy_id}/conditions")
def get_policy_conditions(policy_id: str) -> dict[str, Any]:
    policy = get_policy(policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail=f"Policy not found: {policy_id}")

    return {
        "status": "success",
        "data": {
            "policy_id": policy.policy_id,
            "policy_name": policy.policy_name,
            "policy_type": policy.policy_type,
            "description": policy.description,
            "conditions": _policy_conditions(policy_id),
        },
    }


@app.post("/api/debate")
def run_debate(request: DebateRequest) -> Any:
    policy_id, early_response = _resolve_policy_id(request)
    if early_response is not None:
        return early_response

    if request.reuse_evidence:
        bundle = _build_bundle_from_payload(request.id_card.strip(), request.evidence)
        result = orchestrator.run_debate_with_bundle(
            bundle,
            policy_id=policy_id or DEFAULT_POLICY_ID,
            source_endpoint="/api/debate",
            manual_supplements=request.manual_supplements,
        )
    else:
        result = orchestrator.run_debate(request.id_card.strip(), policy_id=policy_id or DEFAULT_POLICY_ID)
    return {"status": "success", "data": result}


@app.post("/api/debate_stream")
def run_debate_stream(request: DebateRequest) -> Any:
    policy_id, early_response = _resolve_policy_id(request)
    if early_response is not None:
        return early_response

    if request.reuse_evidence:
        bundle = _build_bundle_from_payload(request.id_card.strip(), request.evidence)
        stream = orchestrator.run_debate_stream_with_bundle(
            bundle,
            policy_id=policy_id or DEFAULT_POLICY_ID,
            manual_supplements=request.manual_supplements,
        )
    else:
        stream = orchestrator.run_debate_stream(request.id_card.strip(), policy_id=policy_id or DEFAULT_POLICY_ID)
    return StreamingResponse(stream, media_type="text/event-stream")


@app.get("/api/debates")
def get_debate_history(id_card: str | None = Query(default=None, min_length=1)) -> dict[str, Any]:
    normalized_id_card = id_card.strip() if id_card else None
    history = list_saved_sessions(id_card=normalized_id_card)
    return {"status": "success", "data": {"id_card": normalized_id_card or "", "history": history}}


@app.get("/api/debates/{session_id}")
def get_debate_detail(session_id: str) -> dict[str, Any]:
    try:
        detail = get_saved_session_detail(session_id)
    except DebateSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "success", "data": detail}


@app.post("/api/debates/{session_id}/manual_review/confirm")
def confirm_debate_manual_review(session_id: str, request: ManualReviewConfirmRequest) -> dict[str, Any]:
    """Confirm that manual evidence review is complete and make the PDF downloadable."""
    try:
        detail = confirm_manual_review(session_id, manual_supplements=request.manual_supplements)
        ensure_official_report(detail, force=True)
    except DebateSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"补证复核确认失败: {exc}") from exc
    return {"status": "success", "data": detail}


@app.get("/api/debates/{session_id}/official_report.pdf")
def download_official_report(session_id: str) -> FileResponse:
    """Download the official-style PDF generated for a completed debate session."""
    try:
        detail = get_saved_session_detail(session_id)
        pdf_path = ensure_official_report(detail)
    except DebateSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF 裁决报告生成失败: {exc}") from exc

    filename = f"政务数据辅助审核裁决书_{session_id}.pdf"
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=filename,
    )


if __name__ == "__main__":
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=False)
