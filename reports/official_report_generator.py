"""Official-style PDF report generation for completed debate sessions.

The module intentionally does not require any database schema change. It renders a
completed session snapshot into a PDF stored under ``generated_reports/`` and the
API serves the file by session_id.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        BaseDocTemplate,
        Frame,
        FrameBreak,
        KeepTogether,
        LongTable,
        PageBreak,
        PageTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )
except ModuleNotFoundError as exc:
    REPORTLAB_IMPORT_ERROR = exc
else:
    REPORTLAB_IMPORT_ERROR = None

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = PROJECT_ROOT / "generated_reports"
REPORT_URL_PREFIX = "/api/debates"
CJK_FONT_NAME = "GovCJK"
CID_FALLBACK_FONT_NAME = "STSong-Light"

_CONCLUSION_MAP = {
    "符合": "符合办理条件",
    "不符合": "不符合办理条件",
    "数据缺失": "材料/数据需补正后复核",
    "待定": "待补充审查",
    "pass": "符合办理条件",
    "fail": "不符合办理条件",
    "missing": "材料/数据需补正后复核",
}

_STANCE_MAP = {
    "support": "支持通过",
    "oppose": "反对通过",
    "pending": "待定/需补证",
    "supports": "支持通过",
    "contradicts": "反对通过",
    "missing": "数据缺失",
    "unresolved": "待核验",
}

_STATUS_MAP = {
    "success": "查询成功",
    "no_data": "未命中记录",
    "failed": "查询失败",
    "field_missing": "字段缺失",
}


def build_official_report_metadata(session_id: str) -> dict[str, Any]:
    """Return a stable front-end friendly download descriptor."""
    safe_id = _safe_session_id(session_id)
    return {
        "available": bool(safe_id),
        "filename": f"official_adjudication_report_{safe_id}.pdf",
        "download_url": f"{REPORT_URL_PREFIX}/{safe_id}/official_report.pdf",
        "title": "政府公文式裁决报告",
    }


def get_report_path(session_id: str) -> Path:
    safe_id = _safe_session_id(session_id)
    return REPORT_DIR / f"official_adjudication_report_{safe_id}.pdf"


def ensure_official_report(session_snapshot: dict[str, Any], force: bool = False) -> Path:
    """Create the PDF if it does not already exist, then return its path."""
    if REPORTLAB_IMPORT_ERROR is not None:
        raise RuntimeError("缺少 reportlab 依赖，请先安装 requirements.txt 后再生成 PDF 报告") from REPORTLAB_IMPORT_ERROR

    session_id = str(session_snapshot.get("session_id") or "").strip()
    if not session_id:
        raise ValueError("session_snapshot 缺少 session_id，无法生成 PDF 报告")

    pdf_path = get_report_path(session_id)
    if pdf_path.exists() and not force:
        return pdf_path

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    _register_fonts()
    _render_pdf(session_snapshot, pdf_path)
    return pdf_path


def _safe_session_id(session_id: str) -> str:
    text = str(session_id or "").strip()
    return re.sub(r"[^a-zA-Z0-9_-]", "_", text) or "unknown_session"


def _candidate_cjk_font_paths() -> list[Path]:
    return [
        Path("/Library/Fonts/Arial Unicode.ttf"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/Deng.ttf"),
    ]


def _register_fonts() -> None:
    # Prefer system CJK fonts when available. The project never ships font files;
    # it only points ReportLab to fonts already installed on the host OS.
    global CJK_FONT_NAME
    try:
        pdfmetrics.getFont(CJK_FONT_NAME)
        return
    except KeyError:
        pass

    for font_path in _candidate_cjk_font_paths():
        if not font_path.exists():
            continue
        try:
            pdfmetrics.registerFont(TTFont("GovCJK", str(font_path)))
            CJK_FONT_NAME = "GovCJK"
            return
        except Exception:
            continue

    CJK_FONT_NAME = CID_FALLBACK_FONT_NAME
    try:
        pdfmetrics.getFont(CJK_FONT_NAME)
    except KeyError:
        pdfmetrics.registerFont(UnicodeCIDFont(CJK_FONT_NAME))

def _as_text(value: Any, default: str = "-") -> str:
    if value is None:
        return default
    if isinstance(value, bool):
        return "是" if value else "否"
    text = str(value).strip()
    return text if text else default


def _shorten(value: Any, limit: int = 160) -> str:
    text = _as_text(value, "")
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return "-"
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _pct(value: Any) -> str:
    try:
        return f"{float(value) * 100:.0f}%"
    except (TypeError, ValueError):
        return "-"


def _format_datetime(value: Any) -> str:
    if not value:
        return datetime.now().strftime("%Y年%m月%d日 %H:%M")
    text = str(value)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.strftime("%Y年%m月%d日 %H:%M")
    except ValueError:
        return text


def _decision_label(conclusion: Any) -> str:
    text = _as_text(conclusion)
    return _CONCLUSION_MAP.get(text, text)


def _stance_label(stance: Any) -> str:
    text = _as_text(stance)
    return _STANCE_MAP.get(text, text)


def _status_label(status: Any) -> str:
    text = _as_text(status)
    return _STATUS_MAP.get(text, text)


def _manual_stance_result_label(stance: Any) -> str:
    text = str(stance or "").strip().lower()
    if text in {"support", "supports", "pass", "符合"}:
        return "符合"
    if text in {"refute", "oppose", "reject", "fail", "不符合", "反驳"}:
        return "不符合"
    return "未证实"


def _normalize_clause_result_label(value: Any) -> str:
    text = _as_text(value, "未证实")
    if any(token in text for token in ["不符合", "反对", "排除", "失败"]):
        return "不符合"
    if any(token in text for token in ["符合", "支持", "通过"]):
        return "符合"
    if str(value).lower() == "true":
        return "符合"
    if str(value).lower() == "false":
        return "不符合"
    return "未证实"


def _manual_review_summary(snapshot: dict[str, Any]) -> str:
    review = snapshot.get("manual_review") if isinstance(snapshot.get("manual_review"), dict) else {}
    confirmed = bool(snapshot.get("manual_review_confirmed") or review.get("confirmed"))
    supplement_count = review.get("supplement_count")
    if supplement_count is None:
        supplement_count = len(snapshot.get("manual_supplements") or []) if isinstance(snapshot.get("manual_supplements"), list) else 0
    confirmed_at = review.get("confirmed_at")
    if confirmed:
        base = f"已确认完成（人工补证 {supplement_count} 条）"
        return f"{base}，确认时间：{_format_datetime(confirmed_at)}" if confirmed_at else base
    return f"未确认完成（人工补证 {supplement_count} 条）"


def _latest_manual_supplements_by_clause(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = snapshot.get("manual_supplements")
    if not isinstance(rows, list):
        return {}
    latest: dict[str, dict[str, Any]] = {}
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        clause_id = str(raw.get("clause_id") or "").strip()
        if not clause_id:
            continue
        if str(raw.get("status") or "").strip() == "not_adopted":
            continue
        latest[clause_id] = raw
    return latest


def _evidence_by_rule(evidence: list[Any]) -> dict[str, dict[str, Any]]:
    mapping: dict[str, dict[str, Any]] = {}
    manual_mapping: dict[str, dict[str, Any]] = {}
    for raw in evidence:
        if not isinstance(raw, dict):
            continue
        rule_id = str(raw.get("rule_id") or "").strip()
        if not rule_id:
            continue
        if bool(raw.get("manual_verified")) or str(raw.get("category") or "") == "manual_supplement":
            manual_mapping[rule_id] = raw
        elif rule_id not in mapping:
            mapping[rule_id] = raw
    mapping.update(manual_mapping)
    return mapping


def _build_policy_evidence_table_rows(
    snapshot: dict[str, Any],
    clause_rows: list[Any],
    evidence: list[Any],
) -> list[list[Any]]:
    data = [["政策序号", "内容", "符合/不符合/未证实", "证据摘要"]]
    manual_by_clause = _latest_manual_supplements_by_clause(snapshot)
    evidence_map = _evidence_by_rule(evidence)
    seen_clause_ids: set[str] = set()

    for raw in clause_rows:
        if not isinstance(raw, dict):
            continue
        clause_id = _as_text(raw.get("clause_id"))
        if not clause_id or clause_id == "-":
            continue
        seen_clause_ids.add(clause_id)
        manual = manual_by_clause.get(clause_id)
        evidence_item = evidence_map.get(clause_id, {})

        if manual:
            status = _manual_stance_result_label(manual.get("stance"))
            summary = f"【人工复核】{_as_text(manual.get('detail'))}"
        else:
            status = _normalize_clause_result_label(raw.get("semantic_display_label") or raw.get("status"))
            summary = (
                evidence_item.get("result_summary")
                or evidence_item.get("diagnostic_detail")
                or raw.get("reason")
                or raw.get("action_hint")
                or "-"
            )

        content = raw.get("clause_text") or raw.get("description") or raw.get("clause_name") or raw.get("title") or "-"
        data.append([clause_id, _shorten(content, 220), status, _shorten(summary, 260)])

    for clause_id, manual in manual_by_clause.items():
        if clause_id in seen_clause_ids:
            continue
        data.append([
            clause_id,
            _shorten(manual.get("clause_text") or "人工补证复核条款", 220),
            _manual_stance_result_label(manual.get("stance")),
            _shorten(f"【人工复核】{_as_text(manual.get('detail'))}", 260),
        ])

    for rule_id, item in evidence_map.items():
        if rule_id in seen_clause_ids or rule_id in manual_by_clause:
            continue
        data.append([
            rule_id,
            _shorten(item.get("target") or rule_id, 220),
            _normalize_clause_result_label(item.get("semantic_display_label") or item.get("semantic_decision_effect") or item.get("supports_conclusion")),
            _shorten(item.get("result_summary") or item.get("diagnostic_detail"), 260),
        ])

    return data


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "GovTitle",
            parent=base["Title"],
            fontName=CJK_FONT_NAME,
            fontSize=22,
            leading=30,
            textColor=colors.HexColor("#9b1c1c"),
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "GovSubtitle",
            parent=base["Normal"],
            fontName=CJK_FONT_NAME,
            fontSize=11,
            leading=18,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#555555"),
        ),
        "docno": ParagraphStyle(
            "GovDocNo",
            parent=base["Normal"],
            fontName=CJK_FONT_NAME,
            fontSize=10,
            leading=16,
            alignment=TA_RIGHT,
            textColor=colors.HexColor("#666666"),
        ),
        "h1": ParagraphStyle(
            "GovH1",
            parent=base["Heading1"],
            fontName=CJK_FONT_NAME,
            fontSize=15,
            leading=22,
            textColor=colors.HexColor("#8b0000"),
            spaceBefore=12,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "GovH2",
            parent=base["Heading2"],
            fontName=CJK_FONT_NAME,
            fontSize=12,
            leading=18,
            textColor=colors.HexColor("#303133"),
            spaceBefore=8,
            spaceAfter=6,
        ),
        "normal": ParagraphStyle(
            "GovNormal",
            parent=base["Normal"],
            fontName=CJK_FONT_NAME,
            fontSize=9.5,
            leading=15,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#303133"),
        ),
        "small": ParagraphStyle(
            "GovSmall",
            parent=base["Normal"],
            fontName=CJK_FONT_NAME,
            fontSize=8,
            leading=12,
            textColor=colors.HexColor("#666666"),
        ),
        "seal": ParagraphStyle(
            "GovSeal",
            parent=base["Normal"],
            fontName=CJK_FONT_NAME,
            fontSize=11,
            leading=18,
            alignment=TA_RIGHT,
            textColor=colors.HexColor("#9b1c1c"),
        ),
    }


def _p(text: Any, style: ParagraphStyle) -> Paragraph:
    escaped = _as_text(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Paragraph(escaped, style)


def _kv_table(rows: list[tuple[str, Any]], styles: dict[str, ParagraphStyle]) -> Table:
    data = [[_p(label, styles["small"]), _p(value, styles["normal"])] for label, value in rows]
    table = Table(data, colWidths=[34 * mm, 132 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), CJK_FONT_NAME),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f7f1e8")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#7a2e2e")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d6c2aa")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _long_table(data: list[list[Any]], col_widths: list[float], styles: dict[str, ParagraphStyle]) -> LongTable:
    converted = [[_p(cell, styles["normal"] if r else styles["small"]) for cell in row] for r, row in enumerate(data)]
    table = LongTable(converted, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), CJK_FONT_NAME),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#8b1a1a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d9d9d9")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#faf7f3")]),
            ]
        )
    )
    return table


def _draw_page(canvas, doc) -> None:
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(colors.HexColor("#9b1c1c"))
    canvas.setLineWidth(1.2)
    canvas.line(18 * mm, height - 17 * mm, width - 18 * mm, height - 17 * mm)
    canvas.setFont(CJK_FONT_NAME, 8)
    canvas.setFillColor(colors.HexColor("#777777"))
    canvas.drawString(18 * mm, 12 * mm, "电子生成文件 - 供政务资格审核演示与存档使用")
    canvas.drawRightString(width - 18 * mm, 12 * mm, f"第 {doc.page} 页")
    canvas.restoreState()


def _render_pdf(snapshot: dict[str, Any], pdf_path: Path) -> None:
    styles = _styles()
    doc = BaseDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=24 * mm,
        bottomMargin=20 * mm,
        title="政务资格审核裁决报告",
        author="多 Agent 政务数据决策系统",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([PageTemplate(id="official", frames=[frame], onPage=_draw_page)])

    story: list[Any] = []
    session_id = _as_text(snapshot.get("session_id"))
    id_card = _as_text(snapshot.get("id_card"))
    policy_id = _as_text(snapshot.get("policy_id"))
    final_conclusion = _decision_label(snapshot.get("final_conclusion"))
    final_stance = _stance_label(snapshot.get("final_stance"))
    completed_at = _format_datetime(snapshot.get("completed_at"))
    consensus = _pct(snapshot.get("consensus_rate"))
    adjudication = snapshot.get("adjudication_report") if isinstance(snapshot.get("adjudication_report"), dict) else {}
    arbiter = snapshot.get("arbiter_result") if isinstance(snapshot.get("arbiter_result"), dict) else {}
    persona = snapshot.get("persona") if isinstance(snapshot.get("persona"), dict) else {}
    evidence = snapshot.get("evidence") if isinstance(snapshot.get("evidence"), list) else []
    history = snapshot.get("history") if isinstance(snapshot.get("history"), list) else []
    summary = adjudication.get("summary") if isinstance(adjudication.get("summary"), dict) else {}
    meta = adjudication.get("meta") if isinstance(adjudication.get("meta"), dict) else {}

    story.extend(
        [
            _p("政务数据辅助审核裁决书", styles["title"]),
            _p("灵活就业社会保险补贴资格认定专用文书", styles["subtitle"]),
            Spacer(1, 4 * mm),
            _p(f"文书编号：政数审〔{datetime.now().year}〕{_safe_session_id(session_id)[:8]}号", styles["docno"]),
            Spacer(1, 2 * mm),
            Table([[""]], colWidths=[166 * mm], rowHeights=[1.2 * mm], style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#b91c1c"))])),
            Spacer(1, 6 * mm),
        ]
    )

    story.append(_p("一、案件基本信息", styles["h1"]))
    story.append(
        _kv_table(
            [
                ("申请/审核对象", id_card),
                ("适用政策", f"{_as_text(meta.get('policy_name'), policy_id)}（{policy_id}）"),
                ("系统会话编号", session_id),
                ("完成时间", completed_at),
                ("最终结论", final_conclusion),
                ("多数立场", final_stance),
                ("共识比例", consensus),
                ("证据数量", _as_text(snapshot.get("evidence_count") or len(evidence))),
                ("人工补证复核", _manual_review_summary(snapshot)),
            ],
            styles,
        )
    )

    story.append(_p("二、对象画像与实质争议", styles["h1"]))
    persona_rows = [
        ("画像标题", persona.get("title") or persona.get("name") or f"{id_card} 审核对象画像"),
        ("画像类型", persona.get("archetype") or persona.get("persona_type") or persona.get("type") or "未归类"),
        ("核心意图", persona.get("core_intent") or persona.get("intent") or "申请政策资格认定与补贴办理"),
        ("实质争议", persona.get("substantive_dispute") or persona.get("dispute") or summary.get("top_reason") or "围绕关键资格条款、排除事项与数据一致性进行审核。"),
        ("画像摘要", persona.get("summary") or persona.get("description") or "系统根据证据面板、政策条款与辩论结果自动生成对象画像。"),
    ]
    story.append(_kv_table(persona_rows, styles))

    story.append(_p("三、综合裁决意见", styles["h1"]))
    story.append(
        _kv_table(
            [
                ("裁决结论", final_conclusion),
                ("主要理由", summary.get("top_reason") or arbiter.get("summary") or "关键条款已完成系统审核与仲裁。"),
                ("多数意见", arbiter.get("why_majority_holds") or "多数 Agent 意见已归并并提交仲裁。"),
                ("解释置信度", _pct(summary.get("confidence"))),
                ("人工复核状态", _manual_review_summary(snapshot)),
            ],
            styles,
        )
    )

    clause_rows = adjudication.get("clause_results") if isinstance(adjudication.get("clause_results"), list) else []
    story.append(_p("四、政策条款与证据汇总", styles["h1"]))
    merged_rows = _build_policy_evidence_table_rows(snapshot, clause_rows, evidence)
    if len(merged_rows) > 1:
        story.append(_long_table(merged_rows, [25 * mm, 61 * mm, 31 * mm, 49 * mm], styles))
    else:
        story.append(_p("本次会话未保存结构化条款与证据明细。", styles["normal"]))

    story.append(PageBreak())
    story.append(_p("五、多 Agent 辩论结构", styles["h1"]))
    if history:
        for round_row in history:
            round_num = _as_text(round_row.get("round_num"), "0")
            story.append(_p(f"第 {round_num} 轮辩论", styles["h2"]))
            judgments = round_row.get("judgments") if isinstance(round_row.get("judgments"), list) else []
            if judgments:
                data = [["Agent", "结论", "立场", "置信度", "核心意见"]]
                for judgment in judgments:
                    data.append(
                        [
                            _as_text(judgment.get("agent_role") or judgment.get("agent_id")),
                            _decision_label(judgment.get("conclusion")),
                            _stance_label(judgment.get("stance")),
                            _pct(judgment.get("confidence")),
                            _shorten(judgment.get("key_finding") or judgment.get("reasoning"), 160),
                        ]
                    )
                story.append(_long_table(data, [34 * mm, 25 * mm, 25 * mm, 20 * mm, 62 * mm], styles))
                story.append(Spacer(1, 3 * mm))
            else:
                story.append(_p("本轮暂无 Agent 发言记录。", styles["normal"]))
    else:
        story.append(_p("本次会话未保存辩论过程。", styles["normal"]))

    story.append(_p("六、后续办理建议", styles["h1"]))
    actions = adjudication.get("next_actions") if isinstance(adjudication.get("next_actions"), list) else []
    if actions:
        data = [["类型", "事项", "说明"]]
        for action in actions:
            data.append([
                _as_text(action.get("type")),
                _as_text(action.get("title")),
                _shorten(action.get("detail"), 220),
            ])
        story.append(_long_table(data, [24 * mm, 44 * mm, 98 * mm], styles))
    else:
        story.append(_p("建议保留本裁决书与证据快照，按最终结论进入办理、补证或复核流程。", styles["normal"]))

    risks = arbiter.get("remaining_risks") if isinstance(arbiter.get("remaining_risks"), list) else []
    story.append(_p("七、审慎性与剩余风险提示", styles["h1"]))
    if risks:
        for idx, risk in enumerate(risks, start=1):
            story.append(_p(f"{idx}. {_shorten(risk, 260)}", styles["normal"]))
    else:
        story.append(_p("本次仲裁未记录显著剩余风险；仍建议以原始业务系统数据与人工复核结果为最终办理依据。", styles["normal"]))

    story.append(Spacer(1, 12 * mm))
    story.append(_p("生成机关：政务数据智能审核辅助系统", styles["seal"]))
    story.append(_p(f"生成时间：{datetime.now().strftime('%Y年%m月%d日 %H:%M')}", styles["seal"]))
    story.append(_p("（电子文书，系统自动生成）", styles["seal"]))

    doc.build(story)
