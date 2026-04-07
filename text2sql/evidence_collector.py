"""Evidence collector used by debate orchestration."""
from __future__ import annotations

from typing import Any

from loguru import logger
from sqlalchemy import text

from config.database import get_session
from config.settings import settings
from evidence.evidence_model import EvidenceBundle, EvidenceItem, classify_evidence_diagnostic


class EvidenceCollector:
    """Retrieve evidence items from registered SQL templates."""

    def __init__(self, system_date: str | None = None):
        self.system_date = system_date or settings.system_date

    def collect(self, rule_id: str, id_card: str | None = None) -> EvidenceItem:
        registry = self._load_registry()
        rule = registry["RULE_REGISTRY"][rule_id]
        suffix = id_card[-4:] if id_card else "SCAN"
        evidence_id = f"{rule_id}_{suffix}"

        params: dict[str, Any] = {"system_date": self.system_date}
        if rule["needs_id_card"]:
            if not id_card:
                raise ValueError(f"规则 {rule_id} 需要 id_card 参数")
            params["id_card"] = id_card

        try:
            rows = self._execute(rule["sql"], params)
            exec_status = "success" if rows else "no_data"
        except Exception as exc:
            logger.error("EvidenceCollector rule {} failed: {}", rule_id, exc)
            diagnostic = classify_evidence_diagnostic("failed", str(exc))
            return EvidenceItem(
                evidence_id=evidence_id,
                rule_id=rule_id,
                target_id_card=id_card or "N/A",
                target=rule["target"],
                category=rule["category"],
                sql=rule["sql"].strip(),
                result_raw=[],
                result_summary=f"SQL 执行异常: {exc}",
                supports_conclusion=None,
                confidence=0.0,
                exec_status="failed",
                diagnostic_code=diagnostic[0],
                diagnostic_label=diagnostic[1],
                diagnostic_detail=diagnostic[2],
                diagnostic_hint=diagnostic[3],
            )

        diagnostic = classify_evidence_diagnostic(exec_status)
        return EvidenceItem(
            evidence_id=evidence_id,
            rule_id=rule_id,
            target_id_card=id_card or "N/A",
            target=rule["target"],
            category=rule["category"],
            sql=rule["sql"].strip(),
            result_raw=rows,
            result_summary=self._summarize(rule["target"], rows),
            supports_conclusion=self._auto_verdict(rule.get("auto_verdict"), rows),
            confidence=1.0 if exec_status == "success" else 0.5,
            exec_status=exec_status,
            diagnostic_code=diagnostic[0],
            diagnostic_label=diagnostic[1],
            diagnostic_detail=diagnostic[2],
            diagnostic_hint=diagnostic[3],
        )

    def collect_qualification(self, id_card: str) -> EvidenceBundle:
        registry = self._load_registry()
        bundle = EvidenceBundle(id_card=id_card)
        for rule_id in registry["QUALIFICATION_RULE_IDS"]:
            bundle.items.append(self.collect(rule_id, id_card))
        return bundle

    def collect_calculation(self, id_card: str) -> EvidenceBundle:
        registry = self._load_registry()
        bundle = EvidenceBundle(id_card=id_card)
        for rule_id in registry["CALCULATION_RULE_IDS"]:
            bundle.items.append(self.collect(rule_id, id_card))
        return bundle

    def collect_proactive(self, id_card: str | None = None) -> EvidenceBundle:
        registry = self._load_registry()
        bundle = EvidenceBundle(id_card=id_card or "SCAN")
        for rule_id in registry["PROACTIVE_RULE_IDS"]:
            needs_id_card = registry["RULE_REGISTRY"][rule_id]["needs_id_card"]
            bundle.items.append(self.collect(rule_id, id_card if needs_id_card else None))
        return bundle

    def collect_all(self, id_card: str) -> EvidenceBundle:
        registry = self._load_registry()
        bundle = EvidenceBundle(id_card=id_card)
        for rule_id in registry["QUALIFICATION_RULE_IDS"] + registry["CALCULATION_RULE_IDS"]:
            bundle.items.append(self.collect(rule_id, id_card))
        return bundle

    def _execute(self, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        with get_session() as session:
            result = session.execute(text(sql), params)
            columns = result.keys()
            return [dict(zip(columns, row)) for row in result.fetchall()]

    def _auto_verdict(self, auto_verdict: str | None, rows: list[dict[str, Any]]) -> bool | None:
        if auto_verdict == "pass_if_data":
            return bool(rows)
        if auto_verdict == "fail_if_data":
            return not bool(rows)
        return None

    def _summarize(self, target: str, rows: list[dict[str, Any]]) -> str:
        if not rows:
            return f"{target}: 未查到数据"

        first = rows[0]
        preview = "，".join(f"{key}={value}" for key, value in list(first.items())[:4])
        suffix = f"（共 {len(rows)} 条）" if len(rows) > 1 else ""
        return f"{target}: {preview}{suffix}"

    def _load_registry(self) -> dict[str, Any]:
        try:
            from text2sql.sql_templates import (
                CALCULATION_RULE_IDS,
                PROACTIVE_RULE_IDS,
                QUALIFICATION_RULE_IDS,
                RULE_REGISTRY,
            )
        except Exception as exc:
            raise RuntimeError("SQL 模板注册表当前不可用，无法执行取证。") from exc

        return {
            "RULE_REGISTRY": RULE_REGISTRY,
            "QUALIFICATION_RULE_IDS": QUALIFICATION_RULE_IDS,
            "CALCULATION_RULE_IDS": CALCULATION_RULE_IDS,
            "PROACTIVE_RULE_IDS": PROACTIVE_RULE_IDS,
        }
