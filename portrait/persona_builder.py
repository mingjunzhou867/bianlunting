from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import text

from config.database import get_session
from config.settings import settings
from evidence.evidence_model import EvidenceBundle, EvidenceItem
from policy.policy_router import get_policy


FIXTURE_CODE_BY_ID = {
    "42090219800101000A": "A",
    "42090219850505000B": "B",
    "42090219680401000C": "C",
    "42090219760310000D": "D",
    "42090219780815000E": "E",
    "42090219710321000F": "F",
    "42090219820620000G": "G",
    "42090220010901000H": "H",
    "42090219700505000I": "I",
}

LIFE_STATUS_ALIVE = "生存"
LIFE_STATUS_DEAD = "死亡"
LIFE_STATUS_UNKNOWN = "未知"


class PersonaFactCard(BaseModel):
    label: str
    value: str


class EvidenceOverview(BaseModel):
    supports: int = 0
    contradicts: int = 0
    missing: int = 0
    unresolved: int = 0
    total: int = 0


class PersonaProfile(BaseModel):
    mock_persona_code: str | None = None
    title: str
    archetype: str
    portrait: str
    summary_line: str
    core_intent: str
    substantive_dispute: str
    risk_level: str = Field(default="medium")
    fact_cards: list[PersonaFactCard] = Field(default_factory=list)
    positive_signals: list[str] = Field(default_factory=list)
    risk_signals: list[str] = Field(default_factory=list)
    missing_signals: list[str] = Field(default_factory=list)
    dispute_points: list[str] = Field(default_factory=list)
    evidence_overview: EvidenceOverview = Field(default_factory=EvidenceOverview)


@dataclass
class PersonContext:
    person: dict[str, Any] | None
    unemployment: dict[str, Any] | None
    hardship: dict[str, Any] | None
    active_employment: dict[str, Any] | None
    employment_history: list[dict[str, Any]]
    personal_payments: list[dict[str, Any]]
    unit_payments: list[dict[str, Any]]
    change_logs: list[dict[str, Any]]
    subsidy_rows: list[dict[str, Any]]
    shareholder_rows: list[dict[str, Any]]
    legal_person_rows: list[dict[str, Any]]
    inactive_self_business_rows: list[dict[str, Any]]


class PersonaBuilder:
    def build(
        self,
        id_card: str,
        policy_id: str = "POLICY_001",
        evidence_bundle: EvidenceBundle | None = None,
        final_conclusion: str | None = None,
    ) -> dict[str, Any]:
        ctx = self._load_context(id_card)
        ctx = self._apply_evidence_overrides(ctx, evidence_bundle)
        evidence_overview = self._build_evidence_overview(evidence_bundle)
        classification = self._classify(ctx, evidence_overview)

        name = (ctx.person or {}).get("name") or id_card
        code = FIXTURE_CODE_BY_ID.get(id_card)
        title_prefix = f"{code} {name}" if code else name
        title = f"{title_prefix} — {classification['archetype']}"

        profile = PersonaProfile(
            mock_persona_code=code,
            title=title,
            archetype=classification["archetype"],
            portrait=classification["portrait"],
            summary_line=classification["summary_line"],
            core_intent=self._build_core_intent(policy_id, classification["archetype"]),
            substantive_dispute=classification["substantive_dispute"],
            risk_level=classification["risk_level"],
            fact_cards=self._build_fact_cards(ctx, final_conclusion),
            positive_signals=classification["positive_signals"],
            risk_signals=classification["risk_signals"],
            missing_signals=classification["missing_signals"],
            dispute_points=classification["dispute_points"],
            evidence_overview=evidence_overview,
        )
        return profile.model_dump()

    def _load_context(self, id_card: str) -> PersonContext:
        with get_session() as session:
            person = session.execute(
                text(
                    """
                    SELECT id_card, name, gender, birth_date, hukou_region, life_status, system_status, business_role
                    FROM person
                    WHERE id_card = :id_card
                    """
                ),
                {"id_card": id_card},
            ).mappings().first()

            unemployment = session.execute(
                text(
                    """
                    SELECT id_card, unemployment_date, unemployment_reason, register_date, cancel_date, is_valid
                    FROM unemployment_registration
                    WHERE id_card = :id_card AND is_valid = '1'
                    ORDER BY register_date DESC, unemployment_date DESC
                    LIMIT 1
                    """
                ),
                {"id_card": id_card},
            ).mappings().first()

            hardship = session.execute(
                text(
                    """
                    SELECT id_card, hardship_category, apply_date, certify_org, cancel_date, is_valid
                    FROM hardship_certification
                    WHERE id_card = :id_card AND is_valid = '1'
                    ORDER BY apply_date DESC
                    LIMIT 1
                    """
                ),
                {"id_card": id_card},
            ).mappings().first()

            active_employment = session.execute(
                text(
                    """
                    SELECT e.id_card, e.company_id, c.company_name, c.company_type,
                           e.employment_form, e.employment_date, e.contract_start_date,
                           e.contract_end_date, e.sync_date, e.is_valid
                    FROM employment_registration e
                    LEFT JOIN company_info c ON e.company_id = c.company_id
                    WHERE e.id_card = :id_card AND e.is_valid = '1'
                    ORDER BY COALESCE(e.contract_start_date, e.employment_date, e.sync_date) DESC
                    LIMIT 1
                    """
                ),
                {"id_card": id_card},
            ).mappings().first()

            employment_history = session.execute(
                text(
                    """
                    SELECT e.id_card, e.company_id, c.company_name, c.company_type,
                           e.employment_form, e.employment_date, e.contract_start_date,
                           e.contract_end_date, e.sync_date, e.is_valid
                    FROM employment_registration e
                    LEFT JOIN company_info c ON e.company_id = c.company_id
                    WHERE e.id_card = :id_card
                    ORDER BY COALESCE(e.contract_start_date, e.employment_date, e.sync_date) DESC
                    LIMIT 6
                    """
                ),
                {"id_card": id_card},
            ).mappings().all()

            personal_payments = session.execute(
                text(
                    """
                    SELECT pay_month, insurance_type, insurer_status, pay_base, company_id
                    FROM social_insurance_payment
                    WHERE id_card = :id_card AND is_valid = '1' AND insurer_status = '102'
                    ORDER BY pay_month DESC, insurance_type ASC
                    LIMIT 12
                    """
                ),
                {"id_card": id_card},
            ).mappings().all()

            unit_payments = session.execute(
                text(
                    """
                    SELECT s.pay_month, s.insurance_type, s.insurer_status, s.pay_base, s.company_id,
                           c.company_name, c.company_type
                    FROM social_insurance_payment s
                    LEFT JOIN company_info c ON s.company_id = c.company_id
                    WHERE s.id_card = :id_card AND s.is_valid = '1' AND s.insurer_status = '101'
                    ORDER BY s.pay_month DESC, s.insurance_type ASC
                    LIMIT 12
                    """
                ),
                {"id_card": id_card},
            ).mappings().all()

            change_logs = session.execute(
                text(
                    """
                    SELECT l.insurance_type, l.old_status, l.new_status, l.event_date,
                           l.related_company_id, c.company_name, c.company_type
                    FROM insurance_change_log l
                    LEFT JOIN company_info c ON l.related_company_id = c.company_id
                    WHERE l.id_card = :id_card AND l.is_valid = '1'
                    ORDER BY l.event_date DESC
                    LIMIT 6
                    """
                ),
                {"id_card": id_card},
            ).mappings().all()

            subsidy_rows = session.execute(
                text(
                    """
                    SELECT policy_code, first_enjoy_month, apply_start_month, apply_end_month,
                           grant_months, grant_amount, grant_date, is_valid
                    FROM subsidy_payment_history
                    WHERE id_card = :id_card AND is_valid = '1'
                    ORDER BY COALESCE(grant_date, STR_TO_DATE(CONCAT(apply_end_month, '01'), '%Y%m%d')) DESC
                    LIMIT 12
                    """
                ),
                {"id_card": id_card},
            ).mappings().all()

            shareholder_rows = session.execute(
                text(
                    """
                    SELECT s.company_id, c.company_name, c.company_type, s.share_ratio, s.is_valid
                    FROM company_shareholder s
                    LEFT JOIN company_info c ON s.company_id = c.company_id
                    WHERE s.id_card = :id_card AND s.is_valid = '1'
                    ORDER BY s.share_ratio DESC, s.company_id ASC
                    LIMIT 6
                    """
                ),
                {"id_card": id_card},
            ).mappings().all()

            legal_person_rows = session.execute(
                text(
                    """
                    SELECT company_id, company_name, company_type, is_valid
                    FROM company_info
                    WHERE legal_person_id_card = :id_card AND is_valid = '1'
                    ORDER BY company_id ASC
                    LIMIT 6
                    """
                ),
                {"id_card": id_card},
            ).mappings().all()

            inactive_self_business_rows = session.execute(
                text(
                    """
                    SELECT company_id, company_name, company_type, is_valid
                    FROM company_info
                    WHERE legal_person_id_card = :id_card AND company_type = '个体工商户' AND is_valid = '0'
                    ORDER BY company_id ASC
                    LIMIT 6
                    """
                ),
                {"id_card": id_card},
            ).mappings().all()

        return PersonContext(
            person=dict(person) if person else None,
            unemployment=dict(unemployment) if unemployment else None,
            hardship=dict(hardship) if hardship else None,
            active_employment=dict(active_employment) if active_employment else None,
            employment_history=[dict(item) for item in employment_history],
            personal_payments=[dict(item) for item in personal_payments],
            unit_payments=[dict(item) for item in unit_payments],
            change_logs=[dict(item) for item in change_logs],
            subsidy_rows=[dict(item) for item in subsidy_rows],
            shareholder_rows=[dict(item) for item in shareholder_rows],
            legal_person_rows=[dict(item) for item in legal_person_rows],
            inactive_self_business_rows=[dict(item) for item in inactive_self_business_rows],
        )

    def _build_evidence_overview(self, bundle: EvidenceBundle | None) -> EvidenceOverview:
        if bundle is None:
            return EvidenceOverview()

        supports = contradicts = missing = unresolved = 0
        for item in bundle.items:
            if item.supports_conclusion is True:
                supports += 1
            elif item.supports_conclusion is False:
                contradicts += 1
            elif item.exec_status in {"failed", "field_missing", "no_data"}:
                missing += 1
            else:
                unresolved += 1

        return EvidenceOverview(
            supports=supports,
            contradicts=contradicts,
            missing=missing,
            unresolved=unresolved,
            total=len(bundle.items),
        )

    def _apply_evidence_overrides(self, ctx: PersonContext, bundle: EvidenceBundle | None) -> PersonContext:
        """Override portrait-critical fields with reviewed evidence when available."""
        if bundle is None:
            return ctx

        person = dict(ctx.person or {})
        if not person:
            return ctx

        inferred_life_status = self._infer_life_status_from_bundle(bundle)
        if inferred_life_status:
            person["life_status"] = inferred_life_status

        return PersonContext(
            person=person,
            unemployment=ctx.unemployment,
            hardship=ctx.hardship,
            active_employment=ctx.active_employment,
            employment_history=ctx.employment_history,
            personal_payments=ctx.personal_payments,
            unit_payments=ctx.unit_payments,
            change_logs=ctx.change_logs,
            subsidy_rows=ctx.subsidy_rows,
            shareholder_rows=ctx.shareholder_rows,
            legal_person_rows=ctx.legal_person_rows,
            inactive_self_business_rows=ctx.inactive_self_business_rows,
        )

    def _infer_life_status_from_bundle(self, bundle: EvidenceBundle) -> str | None:
        if not bundle.items:
            return None

        # Manual supplement has highest priority in reviewed sessions.
        sorted_items = sorted(
            bundle.items,
            key=lambda item: 0 if bool(getattr(item, "manual_verified", False)) else 1,
        )

        for item in sorted_items:
            if not self._is_life_status_evidence(item):
                continue

            inferred = self._infer_life_status_from_item(item)
            if inferred:
                return inferred

        return None

    def _is_life_status_evidence(self, item: EvidenceItem) -> bool:
        text = " ".join(
            str(part or "")
            for part in (
                item.rule_id,
                item.target,
                item.result_summary,
                item.diagnostic_detail,
            )
        ).lower()
        keywords = ("life_status", "生存", "死亡", "生命状态", "存活")
        return any(keyword in text for keyword in keywords)

    def _infer_life_status_from_item(self, item: EvidenceItem) -> str | None:
        manual_stance = str(getattr(item, "manual_stance", "") or "").strip().lower()
        if manual_stance == "support":
            return LIFE_STATUS_ALIVE
        if manual_stance == "refute":
            return LIFE_STATUS_DEAD

        if item.supports_conclusion is True:
            return LIFE_STATUS_ALIVE
        if item.supports_conclusion is False:
            return LIFE_STATUS_DEAD

        text = " ".join(
            str(part or "")
            for part in (item.result_summary, item.diagnostic_detail, item.target)
        )
        if LIFE_STATUS_DEAD in text or "非生存" in text:
            return LIFE_STATUS_DEAD
        if LIFE_STATUS_ALIVE in text or "存活" in text:
            return LIFE_STATUS_ALIVE
        return None

    def _classify(self, ctx: PersonContext, evidence_overview: EvidenceOverview) -> dict[str, Any]:
        person = ctx.person or {}
        name = person.get("name") or "该对象"
        life_status = str(person.get("life_status") or "")
        business_role = str(person.get("business_role") or "")
        hardship_category = str((ctx.hardship or {}).get("hardship_category") or "")
        employment_form = str((ctx.active_employment or {}).get("employment_form") or "")
        company_name = str((ctx.active_employment or {}).get("company_name") or "")
        company_type = str((ctx.active_employment or {}).get("company_type") or "")
        employment_date = self._fmt_date((ctx.active_employment or {}).get("employment_date"))
        sync_date = self._fmt_date((ctx.active_employment or {}).get("sync_date"))
        latest_personal_month = self._latest_month(ctx.personal_payments)
        latest_unit_month = self._latest_month(ctx.unit_payments)
        subsidy_months = sum(int(row.get("grant_months") or 0) for row in ctx.subsidy_rows)
        has_personal_pay = bool(ctx.personal_payments)
        has_unit_pay = bool(ctx.unit_payments)
        has_unemployment = ctx.unemployment is not None
        has_hardship = ctx.hardship is not None
        has_active_employment = ctx.active_employment is not None
        has_shareholder = bool(ctx.shareholder_rows)
        has_legal_person = bool(ctx.legal_person_rows)
        has_switch_to_unit = any(
            str(row.get("old_status") or "") == "102" and str(row.get("new_status") or "") == "101"
            for row in ctx.change_logs
        )
        public_unit_trace = any(
            str(row.get("company_type") or "") == "事业单位" for row in ctx.unit_payments
        ) or company_type == "事业单位"
        retirement_months = self._months_to_retirement(ctx.person)
        positive_signals: list[str] = []
        risk_signals: list[str] = []
        missing_signals: list[str] = []
        dispute_points: list[str] = []

        if person.get("life_status") == "生存":
            positive_signals.append("生命状态正常")
        else:
            risk_signals.append(f"生命状态标记为{life_status or '异常'}")

        if has_unemployment:
            positive_signals.append("存在有效失业登记")
        else:
            missing_signals.append("缺少有效失业登记")

        if has_hardship:
            positive_signals.append(f"困难认定有效（{hardship_category or '已认定'}）")
        else:
            missing_signals.append("缺少有效困难认定")

        if employment_form == "灵活就业":
            positive_signals.append("当前登记为灵活就业")
        elif employment_form:
            risk_signals.append(f"当前登记为{employment_form}")
        else:
            missing_signals.append("缺少当前就业登记")

        if has_personal_pay:
            positive_signals.append(f"存在个人灵活就业缴费（最近 {latest_personal_month or '未知月份'}）")
        else:
            missing_signals.append("缺少灵活就业缴费记录")

        if has_unit_pay:
            risk_signals.append(f"存在单位缴费记录（最近 {latest_unit_month or '未知月份'}）")
        if has_shareholder:
            risk_signals.append("存在有效企业股东身份")
        if has_legal_person:
            risk_signals.append("存在有效企业法人身份")
        if has_switch_to_unit:
            risk_signals.append("存在 102→101 身份切换日志")
        if subsidy_months > 0:
            positive_signals.append(f"历史已享受补贴 {subsidy_months} 个月")

        if life_status and life_status != "生存":
            archetype = "死亡标记の幽灵人"
            portrait = "系统生命状态异常，但后续仍残留缴费/领补痕迹。"
            summary_line = f"{name} 被系统标记为非生存状态，但业务流水仍在继续，属于高风险的数据可信度冲突样本。"
            substantive_dispute = "基础资格首先要求‘人仍然存在’，但缴费或领补流水又在表面上证明该人仍在业务系统中活动，争议核心从资格判断转向数据真伪。"
            dispute_points.extend([
                f"person.life_status={life_status}",
                "生命状态与后续社保/补贴流水相互冲突",
                "是否应直接拒审，还是先转人工核验数据源",
            ])
            risk_level = "high"
        elif has_shareholder or has_legal_person:
            archetype = "隐蔽拒审型（明确欺诈）"
            company_desc = self._join_company_names(ctx.shareholder_rows or ctx.legal_person_rows)
            portrait = f"表面基础条件可过，但背后仍挂着有效商事身份（{company_desc or '企业法人/股东身份'}）。"
            summary_line = f"{name} 的主要风险不在基础登记，而在隐藏的商事身份排斥项，属于容易‘表面过审、实质应拒’的样本。"
            substantive_dispute = "表层失业/困难/缴费链条可能成立，但企业法人或股东身份属于强排斥信号，实质争议在于是否存在隐匿经营或套利领补。"
            dispute_points.extend([
                "基础资格可能齐全，但商事身份与补贴对象定位冲突",
                "是否应以有效股东/法人关系直接否决资格",
            ])
            risk_level = "high"
        elif business_role == "个体工商户" and (ctx.inactive_self_business_rows or (has_unemployment and not has_shareholder and not has_legal_person)):
            archetype = "已注销个体户の身份困境"
            portrait = "工商身份残留仍写着个体户，但经营主体已停业或注销。"
            summary_line = f"{name} 的关键问题不是有没有就业困难，而是系统‘历史标签’与‘当前有效身份’不一致。"
            substantive_dispute = "排斥条件到底看当前有效工商身份，还是看 person.business_role 里的历史残留标签；这会直接影响系统是否机械性拒绝。"
            dispute_points.extend([
                "person.business_role 仍为个体工商户",
                "工商主体已注销或不再有效",
                "当前状态与历史标签谁应优先作为裁决依据",
            ])
            risk_level = "medium"
        elif has_active_employment and employment_form == "全日制用工" and has_personal_pay and has_switch_to_unit:
            latest_change = self._fmt_date((ctx.change_logs[0] or {}).get("event_date")) if ctx.change_logs else "近期"
            archetype = "薛定谔的困难人员（功能三辩论）"
            portrait = f"{employment_date or '近期'}入职{company_name or '某单位'}，但系统社保切换到单位缴费的动作要到 {latest_change or '后续'} 才落地，名义上仍像未就业。"
            summary_line = f"{name} 处在‘已入职’与‘未完全切换参保身份’的窗口期，是典型的状态同步滞后争议样本。"
            substantive_dispute = "实质争议不是有没有工作，而是系统应按合同入职时间认定其已就业，还是按社保身份切换完成时间继续把他视作困难人员。"
            dispute_points.extend([
                f"有效就业登记显示 {employment_date or '近期'} 已入职 {company_name or '某单位'}",
                f"最近个人缴费仍停留在 {latest_personal_month or '近期月份'}",
                f"身份切换日志显示 {latest_change or '后续'} 才从 102 变为 101",
            ])
            risk_level = "high"
        elif public_unit_trace and has_personal_pay:
            archetype = "事业单位临聘の财政供养之谜"
            portrait = "曾出现事业单位/财政供养痕迹，后续又转成个人缴费，身份性质存在遮蔽。"
            summary_line = f"{name} 的争议点在于其是否真正属于灵活就业对象，还是带有事业单位用工残影。"
            substantive_dispute = "单位性质若属于事业单位或财政供养口径，即便后续出现个人缴费，也可能不属于政策希望补贴的对象。"
            dispute_points.extend([
                "历史单位缴费带有事业单位特征",
                "后续转为个人缴费是否足以洗脱原单位供养属性",
            ])
            risk_level = "high"
        elif hardship_category.find("高校毕业生") >= 0 or (ctx.person and self._age_years(ctx.person) is not None and self._age_years(ctx.person) <= 26 and subsidy_months > 0):
            archetype = "高校毕业生の算账噩梦"
            portrait = f"高校毕业生专项口径与历史已领 {subsidy_months} 个月补贴叠加，核心难点转向月数精算。"
            summary_line = f"{name} 不一定卡在准入，而更容易卡在‘还能领几个月、按哪种上限算’的精算争议上。"
            substantive_dispute = "既要判断其是否仍落在高校毕业生专项窗口内，又要核算历史已享受月数与普通困难人员口径是否叠加或互斥。"
            dispute_points.extend([
                "高校毕业生专项口径与普通困难人员口径可能重叠",
                f"历史已领取 {subsidy_months} 个月，剩余额度必须重算",
            ])
            risk_level = "medium"
        elif retirement_months is not None and retirement_months <= 3 and str((ctx.person or {}).get("gender") or "") == "女":
            archetype = "退休年龄线上的女性"
            portrait = "已到或逼近女性退休年龄线，资格与补贴月数都会被退休口径牵动。"
            summary_line = f"{name} 的关键不是有没有困难身份，而是退休年龄到底按 50 岁、55 岁还是岗位属性来认定。"
            substantive_dispute = "一旦退休年龄口径不同，既会影响‘能不能领’，也会影响‘还能领几个月’，属于资格与精算的双重边界争议。"
            dispute_points.extend([
                f"距默认退休线仅剩 {max(retirement_months, 0)} 个月",
                "岗位属性不清会改变退休年龄认定",
            ])
            risk_level = "high" if retirement_months <= 0 else "medium"
        elif subsidy_months >= 12:
            archetype = "精准算账型（功能二测试）"
            portrait = f"历史已领取 {subsidy_months} 个月补贴，基础资格大概率已过，核心转向剩余额度和退休窗口。"
            summary_line = f"{name} 更像精算题而不是准入题，系统需要先把历史已领月数、退休时间和当前缴费月数算清。"
            substantive_dispute = "实质争议不在‘能否进入政策’，而在‘还能领多少、以哪条上限为准、领取后还剩多少’。"
            dispute_points.extend([
                f"历史累计已领 {subsidy_months} 个月",
                "剩余额度需与退休窗口、缴费月数共同取最小值",
            ])
            risk_level = "medium"
        elif life_status == "生存" and has_unemployment and has_hardship and employment_form == "灵活就业" and has_personal_pay and not has_unit_pay and not has_shareholder and not has_legal_person and evidence_overview.missing <= 1:
            archetype = "完美过审型（正向基准）"
            portrait = "各项登记无缝衔接，标准补贴候选人。"
            summary_line = f"{name} 的失业登记、困难认定、灵活就业登记与个人缴费链条完整，适合作为正向通过基准样本。"
            substantive_dispute = "当前几乎没有实质争议，系统主要任务是确认不存在隐藏排斥项，并进入后续金额/月份核算。"
            dispute_points.extend([
                "基础资格链条完整且时间线顺畅",
                "未发现有效商事身份或单位缴费排斥信号",
            ])
            risk_level = "low"
        else:
            archetype = "待核画像（证据汇总型）"
            portrait = "已形成基础身份、就业、社保与历史补贴的统一摘要，但仍需围绕关键缺口继续取证。"
            summary_line = f"{name} 目前尚未呈现单一、明确的人设类型，更像需要继续补证的综合待核案件。"
            substantive_dispute = "当前争议焦点并非单一标签，而是多项基础条件、排斥条件与时间线证据尚未完全闭环。"
            dispute_points.extend([
                "系统已形成统一画像，但仍存在关键证据待补齐",
                "需避免各 Agent 在同一事实基础上重复推理",
            ])
            risk_level = "medium" if evidence_overview.missing < 3 else "high"

        return {
            "archetype": archetype,
            "portrait": portrait,
            "summary_line": summary_line,
            "substantive_dispute": substantive_dispute,
            "positive_signals": positive_signals,
            "risk_signals": risk_signals,
            "missing_signals": missing_signals,
            "dispute_points": dispute_points,
            "risk_level": risk_level,
        }

    def _build_core_intent(self, policy_id: str, archetype: str) -> str:
        policy = get_policy(policy_id)
        policy_name = policy.policy_name if policy else policy_id
        if policy_id == "POLICY_003":
            return "围绕企业社会保险补贴主动服务，识别该对象是否应被系统主动筛入服务名单，并解释筛入/筛出的关键依据。"

        mapping = {
            "完美过审型（正向基准）": f"确认其是否可按 {policy_name} 的标准链路直接通过资格核验，并进入后续月数/金额计算。",
            "隐蔽拒审型（明确欺诈）": f"识别其表面合规之下是否藏有 {policy_name} 的强排斥项，防止误发补贴。",
            "精准算账型（功能二测试）": f"在默认准入成立的前提下，精确核算 {policy_name} 的可领月数、剩余额度与边界月份。",
            "薛定谔的困难人员（功能三辩论）": f"厘清其在入职与社保切换窗口中的真实状态，判断是否仍应被纳入 {policy_name} 的补贴对象。",
            "已注销个体户の身份困境": f"明确 {policy_name} 的排斥条件应以当前有效身份还是历史残留标签为准，避免机械拒审。",
            "退休年龄线上的女性": f"先明确退休口径，再判断其在 {policy_name} 下是否仍具备申领窗口与剩余月数。",
            "事业单位临聘の财政供养之谜": f"识别其是否实质属于财政供养/单位用工对象，从而判断是否应被 {policy_name} 排除。",
            "高校毕业生の算账噩梦": f"统一高校毕业生专项口径、历史领取记录与当前 {policy_name} 规则，避免月数计算冲突。",
            "死亡标记の幽灵人": f"先核实数据可信度和生命状态，再决定是否允许其进入 {policy_name} 的自动审核链。",
        }
        return mapping.get(archetype, f"在进入多 Agent 辩论前，先统一该对象在 {policy_name} 下的身份状态、就业状态、社保状态与关键争议。")

    def _build_fact_cards(self, ctx: PersonContext, final_conclusion: str | None) -> list[PersonaFactCard]:
        person = ctx.person or {}
        cards: list[PersonaFactCard] = [
            PersonaFactCard(label="姓名 / 身份证", value=f"{person.get('name') or '未知'} / {person.get('id_card') or '未知'}"),
            PersonaFactCard(label="户籍 / 生存状态", value=f"{person.get('hukou_region') or '未知'} / {person.get('life_status') or '未知'}"),
            PersonaFactCard(label="失业登记", value=self._describe_unemployment(ctx.unemployment)),
            PersonaFactCard(label="困难认定", value=self._describe_hardship(ctx.hardship)),
            PersonaFactCard(label="当前就业状态", value=self._describe_employment(ctx.active_employment)),
            PersonaFactCard(label="个人缴费", value=self._describe_payments(ctx.personal_payments, expected_status='102')),
            PersonaFactCard(label="单位缴费", value=self._describe_payments(ctx.unit_payments, expected_status='101')),
            PersonaFactCard(label="历史补贴", value=self._describe_subsidy(ctx.subsidy_rows)),
        ]
        if final_conclusion:
            cards.append(PersonaFactCard(label="当前系统结论", value=final_conclusion))
        return cards

    def _describe_unemployment(self, row: dict[str, Any] | None) -> str:
        if not row:
            return "未查询到有效失业登记"
        return f"{self._fmt_date(row.get('register_date')) or '未知日期'} 登记失业"

    def _describe_hardship(self, row: dict[str, Any] | None) -> str:
        if not row:
            return "未查询到有效困难认定"
        return f"{row.get('hardship_category') or '已认定'} / {self._fmt_date(row.get('apply_date')) or '未知日期'}"

    def _describe_employment(self, row: dict[str, Any] | None) -> str:
        if not row:
            return "未查询到有效当前就业登记"
        form = row.get('employment_form') or '未知形式'
        company = row.get('company_name') or row.get('company_id') or '未知单位'
        date_text = self._fmt_date(row.get('employment_date')) or self._fmt_date(row.get('contract_start_date')) or '未知日期'
        return f"{form} / {company} / {date_text}"

    def _describe_payments(self, rows: list[dict[str, Any]], expected_status: str) -> str:
        if not rows:
            return "未查询到记录"
        months = sorted({str(row.get('pay_month') or '') for row in rows if row.get('pay_month')}, reverse=True)
        latest = months[0] if months else '未知月份'
        span = len(months)
        status_text = '个人灵活就业' if expected_status == '102' else '单位缴费'
        return f"{status_text} {span} 个有效月份，最近 {latest}"

    def _describe_subsidy(self, rows: list[dict[str, Any]]) -> str:
        if not rows:
            return "暂无历史补贴记录"
        total_months = sum(int(row.get("grant_months") or 0) for row in rows)
        latest = rows[0]
        return f"累计 {total_months} 个月，最近一笔 {latest.get('policy_code') or '未知政策'}"

    def _months_to_retirement(self, person: dict[str, Any] | None) -> int | None:
        if not person or not person.get('birth_date'):
            return None
        birth = self._to_date(person.get('birth_date'))
        if birth is None:
            return None
        gender = str(person.get('gender') or '')
        retire_age = 60 if gender == '男' else 55
        system_day = self._to_date(settings.system_date)
        if system_day is None:
            return None
        retirement_date = date(birth.year + retire_age, birth.month, min(birth.day, 28 if birth.month == 2 else birth.day))
        return (retirement_date.year - system_day.year) * 12 + (retirement_date.month - system_day.month)

    def _age_years(self, person: dict[str, Any] | None) -> int | None:
        if not person or not person.get('birth_date'):
            return None
        birth = self._to_date(person.get('birth_date'))
        system_day = self._to_date(settings.system_date)
        if birth is None or system_day is None:
            return None
        years = system_day.year - birth.year
        if (system_day.month, system_day.day) < (birth.month, birth.day):
            years -= 1
        return years

    def _join_company_names(self, rows: list[dict[str, Any]]) -> str:
        names = [str(row.get('company_name') or row.get('company_id') or '').strip() for row in rows]
        names = [name for name in names if name]
        return '、'.join(names[:3])

    def _latest_month(self, rows: list[dict[str, Any]]) -> str | None:
        months = sorted({str(row.get('pay_month') or '') for row in rows if row.get('pay_month')}, reverse=True)
        return months[0] if months else None

    def _fmt_date(self, value: Any) -> str | None:
        d = self._to_date(value)
        if d is None:
            return None
        return d.isoformat()

    def _to_date(self, value: Any) -> date | None:
        if value is None or value == "":
            return None
        if isinstance(value, date):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue
        return None
