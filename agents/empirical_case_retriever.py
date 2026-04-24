from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from evidence.evidence_projection import EvidenceProjection


CASES_PATH = Path(__file__).resolve().parent / "data" / "empirical_cases.json"


@dataclass(frozen=True)
class EmpiricalCaseSummary:
    case_id: str
    case_label: str
    final_conclusion: str
    final_stance: str
    key_pattern: list[str]
    risk_points: list[str]
    summary: str
    score: int
    matched_signals: list[str]

    def to_prompt_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "case_label": self.case_label,
            "final_conclusion": self.final_conclusion,
            "final_stance": self.final_stance,
            "key_pattern": self.key_pattern,
            "risk_points": self.risk_points,
            "summary": self.summary,
            "score": self.score,
            "matched_signals": self.matched_signals,
        }


def retrieve_empirical_cases(projection: EvidenceProjection, *, top_k: int = 3) -> list[EmpiricalCaseSummary]:
    case_defs = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    current_signals = _extract_projection_signals(projection)
    ranked: list[EmpiricalCaseSummary] = []
    for case_def in case_defs:
        matched = [signal for signal in current_signals if signal in (case_def.get("key_pattern", []) + case_def.get("risk_points", []))]
        ranked.append(
            EmpiricalCaseSummary(
                case_id=case_def["case_id"],
                case_label=case_def["case_label"],
                final_conclusion=case_def["final_conclusion"],
                final_stance=case_def["final_stance"],
                key_pattern=list(case_def.get("key_pattern", [])),
                risk_points=list(case_def.get("risk_points", [])),
                summary=case_def.get("summary", ""),
                score=len(matched),
                matched_signals=matched,
            )
        )
    ranked.sort(key=lambda item: (item.score, item.case_id), reverse=True)
    return [item for item in ranked[:top_k] if item.score > 0] or ranked[:1]


def _extract_projection_signals(projection: EvidenceProjection) -> list[str]:
    signals: set[str] = set()
    for card in projection.cards:
        text = f"{card.question} {card.finding}".strip()
        if card.status == "supports":
            if any(token in text for token in ("??", "??")):
                signals.add("??????????")
            if any(token in text for token in ("????", "??")):
                signals.add("??????????")
            if any(token in text for token in ("??", "??")):
                signals.add("????????")
            if any(token in text for token in ("??", "??", "??")):
                signals.add("????????????")
        if card.status == "contradicts":
            if any(token in text for token in ("??", "??", "?????")):
                signals.add("??????????????")
            if any(token in text for token in ("??", "??", "??")):
                signals.add("????????")
            signals.add("?????????")
        if card.status == "missing":
            if any(token in text for token in ("??", "??")):
                signals.add("????????")
            if any(token in text for token in ("??", "??")):
                signals.add("??????")
            if any(token in text for token in ("????", "??")):
                signals.add("????????")
        if card.status == "unresolved":
            signals.add("?????????")
            if any(token in text for token in ("??", "??", "??")):
                signals.add("????????")
                signals.add("????????????")
        if any(token in text for token in ("??", "??")) and card.status in {"supports", "unresolved"}:
            signals.add("??????")
        if any(token in text for token in ("??", "??")):
            signals.add("????")
    if not any(signal.startswith("??") or signal.startswith("??") for signal in signals):
        signals.add("?????????")
    return list(signals)
