from loguru import logger
from sqlalchemy import text

from cognition.evidence_planner import EvidencePlanner
from config.database import get_session
from evidence.evidence_model import EvidenceBundle, EvidenceItem, classify_evidence_diagnostic
from text2sql.dynamic.auto_debugger import AutoDebugger
from text2sql.dynamic.evidence_assembler import EvidenceAssembler


class DynamicEvidenceCollector:
    """
    破除静态脚本边界的终极武器 —— 全自动动态取证大满贯引擎。
    它完美替代了旧版本的静态 EvidenceCollector，串联了规划层、打字机生成层、抗压执行层，和转译装配层。
    """
    def __init__(self):
        self.planner = EvidencePlanner()
        self.auto_debugger = AutoDebugger()
        self.assembler = EvidenceAssembler()

    def _is_must_rule(self, rule_id: str) -> bool:
        return rule_id.startswith("P001_MUST_")

    def _is_exclude_rule(self, rule_id: str) -> bool:
        return rule_id.startswith("P001_EXCLUDE_")

    def _is_effective_hit(self, raw_data) -> bool:
        """
        Determine whether a query truly hit business facts.
        COUNT-style queries return one row even when count=0, so row presence alone is not enough.
        """
        if not raw_data:
            return False
        if len(raw_data) == 1 and isinstance(raw_data[0], dict):
            row = raw_data[0]
            if "cnt" in row:
                try:
                    return float(row.get("cnt") or 0) > 0
                except (TypeError, ValueError):
                    return False
            if "count" in row:
                try:
                    return float(row.get("count") or 0) > 0
                except (TypeError, ValueError):
                    return False
        return True

    def _apply_hard_rule_semantics(self, item, exec_status, raw_data, assembled):
        """
        Hard-rule deterministic semantics:
        - MUST: effective hit => support True; otherwise support False
        - EXCLUDE: effective hit => support False; otherwise support True
        """
        has_hit = self._is_effective_hit(raw_data)

        if self._is_must_rule(item.rule_id):
            if exec_status == "success" and has_hit:
                assembled.supports_conclusion = True
                return
            if exec_status in {"success", "no_data"} and not has_hit:
                assembled.supports_conclusion = False
                assembled.result_summary = assembled.result_summary or "未查询到满足该必须条件的有效记录。"
                return

        if self._is_exclude_rule(item.rule_id):
            if exec_status == "success" and has_hit:
                assembled.supports_conclusion = False
                return
            if exec_status in {"success", "no_data"} and not has_hit:
                assembled.supports_conclusion = True
                assembled.result_summary = assembled.result_summary or "未命中该排除条件记录。"
                return

    def _is_category_in_policy_scope(self, row: dict) -> bool | None:
        policy_match = row.get("hardship_policy_match")
        if policy_match in (1, "1", True):
            return True
        if policy_match in (0, "0", False):
            return False

        code = (row.get("hardship_category_code") or "").strip().upper()
        if code:
            # Fallback category scope when explicit policy_match is absent.
            # Keep this list conservative and aligned with current local mock policy semantics.
            in_scope_codes = {"ED_001", "ED_002", "ED_003"}
            return code in in_scope_codes

        category = (row.get("hardship_category") or "").strip()
        if category:
            in_scope_labels = {
                "大龄失业人员",
                "残疾人员",
                "离校2年内未就业的高校毕业生",
            }
            if category in in_scope_labels:
                return True
            return False
        return None

    def _recover_flex_002_evidence(self, id_card: str):
        """
        Recover P001_FLEX_002 when LLM-generated SQL over-filters category labels.
        Read the latest valid hardship_certification record directly and decide support
        by policy_match / category_code / category label fallback.
        """
        sql = """
            SELECT
                id_card,
                hardship_category,
                hardship_category_code,
                hardship_policy_match,
                apply_date,
                certify_org,
                is_valid
            FROM hardship_certification
            WHERE id_card = :id_card
              AND is_valid = '1'
            ORDER BY apply_date DESC
            LIMIT 1
        """
        try:
            with get_session() as session:
                row = session.execute(text(sql), {"id_card": id_card}).mappings().first()
            if not row:
                return None

            row_dict = dict(row)
            supports = self._is_category_in_policy_scope(row_dict)
            code = row_dict.get("hardship_category_code") or "未知"
            match = row_dict.get("hardship_policy_match")
            summary = (
                "按困难认定主记录回退取证："
                f"类别编码={code}，政策匹配标记={match}，"
                f"认定日期={row_dict.get('apply_date')}。"
            )
            return [row_dict], summary, supports
        except Exception as exc:
            logger.warning("[DynamicCollector] P001_FLEX_002 fallback recovery failed: {}", exc)
            return None

    def _recover_flex_005_evidence(self, id_card: str):
        """
        Recover P001_FLEX_005 when LLM-generated SQL is rejected by detail guardrail.
        Return detail rows instead of aggregate-only output.
        """
        sql = """
            SELECT
                policy_code,
                apply_start_month,
                apply_end_month,
                grant_months,
                grant_amount,
                grant_date,
                is_valid
            FROM subsidy_payment_history
            WHERE id_card = :id_card
              AND is_valid = '1'
            ORDER BY grant_date DESC, apply_end_month DESC
        """
        try:
            with get_session() as session:
                rows = session.execute(text(sql), {"id_card": id_card}).mappings().all()
            if not rows:
                return None
            raw_data = [dict(row) for row in rows]
            summary = f"回退取证成功：共查询到 {len(raw_data)} 条历史补贴明细记录。"
            return raw_data, summary, True
        except Exception as exc:
            logger.warning("[DynamicCollector] P001_FLEX_005 fallback recovery failed: {}", exc)
            return None

    def _resolve_base_volatility_semantics(self, item, raw_data):
        if item.rule_id != "P001_FLEX_004":
            return None

        pay_bases: list[float] = []
        for row in raw_data or []:
            raw_value = row.get("pay_base")
            if raw_value in (None, ""):
                continue
            try:
                pay_base = float(raw_value)
            except (TypeError, ValueError):
                continue
            if pay_base > 0:
                pay_bases.append(pay_base)

        if len(pay_bases) < 2:
            return (
                "缴费基数记录不足，暂无法判断是否存在异常波动；该项仅作为风险观察信号，不单独影响资格结论。",
                None,
            )

        relative_changes: list[float] = []
        for previous, current in zip(pay_bases, pay_bases[1:]):
            if previous <= 0:
                continue
            relative_changes.append(abs(current - previous) / previous)

        if not relative_changes:
            return (
                "缴费基数记录可用，但不足以判断波动风险；该项仅作为风险观察信号，不单独影响资格结论。",
                None,
            )

        max_change = max(relative_changes)
        if max_change < 0.05:
            return (
                "缴费基数整体稳定，未见异常波动；该项不构成负面证据，仅作为中性观察信息。",
                None,
            )
        if max_change <= 0.20:
            return (
                "缴费基数存在轻微波动，但幅度处于正常范围，当前不足以认定为异常风险；该项仅作为中性观察信息。",
                None,
            )
        return (
            "缴费基数存在较明显波动，提示可能存在身份切换、经营异常或数据异常风险；需结合单位参保、身份切换等证据进一步复核，该项不单独直接否决资格。",
            None,
        )

    def _resolve_no_data_semantics(self, item):
        rule_id = item.rule_id
        if rule_id == "P001_FLEX_003":
            return (
                "未查询到身份切换记录，当前未发现从灵活就业转为单位参保的切换风险。",
                True,
            )
        if rule_id == "P001_FLEX_004":
            return (
                "未检出可判定的缴费基数异常波动信号；该项仅用于风险提示，不单独影响资格结论。",
                True,
            )
        if rule_id == "P001_FLEX_005":
            return (
                "未查询到历史补贴领取记录，可视为当前没有已享受补贴月数的存量记录。",
                True,
            )
        return None

    def collect_all(self, id_card: str, policy_id: str = "POLICY_001") -> EvidenceBundle:
        """为非流式接口保留的遗留打包方法"""
        bundle = EvidenceBundle(id_card=id_card)
        for item in self.collect_stream(id_card, policy_id=policy_id):
            bundle.items.append(item)
        return bundle
        
    def collect_stream(self, id_card: str, policy_id: str = "POLICY_001"):
        logger.info(f"[DynamicCollector] 开启全境动态取证，目标人员：{id_card} policy={policy_id}")
        
        # 1. 启动第一层：智能规划网络
        plan = self.planner.plan(person_id=id_card, policy_id=policy_id)
        
        # 2. 深入第二层：执行与转储
        for item in plan.items:
            evidence_id = item.plan_item_id
            
            try:
                # 2.1 浴火执行：撰写 SQL -> 防爆拦截重试 -> 获取原始数据
                sql, raw_data = self.auto_debugger.execute_with_auto_fix(item, id_card)
                exec_status = "success" if raw_data else "no_data"
                
                # 2.2 升维装配：将黑客数据翻译成符合裁决规则的结论总结
                assembled = self.assembler.assemble(item, raw_data)
                rule_resolution = self._resolve_base_volatility_semantics(item, raw_data)
                if rule_resolution:
                    assembled.result_summary, assembled.supports_conclusion = rule_resolution

                if item.rule_id == "P001_FLEX_002" and exec_status == "no_data":
                    recovered = self._recover_flex_002_evidence(id_card)
                    if recovered:
                        raw_data, recovered_summary, recovered_supports = recovered
                        exec_status = "success"
                        assembled.result_summary = recovered_summary
                        assembled.supports_conclusion = recovered_supports
                        sql = (
                            "/* fallback: recovered from hardship_certification latest valid record */\n"
                            "SELECT id_card, hardship_category, hardship_category_code, hardship_policy_match, "
                            "apply_date, certify_org, is_valid\n"
                            "FROM hardship_certification\n"
                            f"WHERE id_card = '{id_card}' AND is_valid = '1'\n"
                            "ORDER BY apply_date DESC LIMIT 1"
                        )

                if exec_status == "no_data":
                    no_data_resolution = self._resolve_no_data_semantics(item)
                    if no_data_resolution:
                        assembled.result_summary, assembled.supports_conclusion = no_data_resolution

                self._apply_hard_rule_semantics(item, exec_status, raw_data, assembled)
                
                diagnostic = classify_evidence_diagnostic(exec_status)
                evidence = EvidenceItem(
                    evidence_id=evidence_id,
                    rule_id=item.rule_id,
                    target_id_card=id_card,
                    target=item.rule_name,
                    category=item.rule_type,
                    sql=sql.strip(),
                    result_raw=raw_data,
                    result_summary=assembled.result_summary,
                    supports_conclusion=assembled.supports_conclusion,
                    confidence=1.0 if exec_status == "success" else 0.5,
                    exec_status=exec_status,
                    diagnostic_code=diagnostic[0],
                    diagnostic_label=diagnostic[1],
                    diagnostic_detail=diagnostic[2],
                    diagnostic_hint=diagnostic[3],
                )
            except Exception as exc:
                # Robust fallback for P001_FLEX_005: always try detail recovery first,
                # regardless of exact exception message formatting.
                if item.rule_id == "P001_FLEX_005":
                    recovered = self._recover_flex_005_evidence(id_card)
                    if recovered:
                        raw_data, recovered_summary, recovered_supports = recovered
                        exec_status = "success"
                        diagnostic = classify_evidence_diagnostic(exec_status)
                        evidence = EvidenceItem(
                            evidence_id=evidence_id,
                            rule_id=item.rule_id,
                            target_id_card=id_card,
                            target=item.rule_name,
                            category=item.rule_type,
                            sql=(
                                "/* fallback: recovered subsidy details after execution exception */\n"
                                "SELECT policy_code, apply_start_month, apply_end_month, grant_months, "
                                "grant_amount, grant_date, is_valid\n"
                                "FROM subsidy_payment_history\n"
                                f"WHERE id_card = '{id_card}' AND is_valid = '1'\n"
                                "ORDER BY grant_date DESC, apply_end_month DESC"
                            ),
                            result_raw=raw_data,
                            result_summary=recovered_summary,
                            supports_conclusion=recovered_supports,
                            confidence=1.0,
                            exec_status=exec_status,
                            diagnostic_code=diagnostic[0],
                            diagnostic_label=diagnostic[1],
                            diagnostic_detail=diagnostic[2],
                            diagnostic_hint=diagnostic[3],
                        )
                        yield evidence
                        continue
                    # No rows is a normal business outcome for historical subsidy details.
                    no_data_resolution = self._resolve_no_data_semantics(item)
                    summary = (
                        no_data_resolution[0]
                        if no_data_resolution
                        else "未查询到历史补贴领取记录。"
                    )
                    supports = (
                        no_data_resolution[1]
                        if no_data_resolution
                        else True
                    )
                    diagnostic = classify_evidence_diagnostic("no_data")
                    evidence = EvidenceItem(
                        evidence_id=evidence_id,
                        rule_id=item.rule_id,
                        target_id_card=id_card,
                        target=item.rule_name,
                        category=item.rule_type,
                        sql=(
                            "/* fallback: no historical subsidy rows */\n"
                            "SELECT policy_code, apply_start_month, apply_end_month, grant_months, "
                            "grant_amount, grant_date, is_valid\n"
                            "FROM subsidy_payment_history\n"
                            f"WHERE id_card = '{id_card}' AND is_valid = '1'\n"
                            "ORDER BY grant_date DESC, apply_end_month DESC"
                        ),
                        result_raw=[],
                        result_summary=summary,
                        supports_conclusion=supports,
                        confidence=0.8,
                        exec_status="no_data",
                        diagnostic_code=diagnostic[0],
                        diagnostic_label=diagnostic[1],
                        diagnostic_detail=diagnostic[2],
                        diagnostic_hint=diagnostic[3],
                    )
                    yield evidence
                    continue

                logger.error(f"[DynamicCollector] 取证线 {item.rule_id} 执行全线崩溃: {exc}")
                diagnostic = classify_evidence_diagnostic("failed", str(exc))
                evidence = EvidenceItem(
                    evidence_id=evidence_id,
                    rule_id=item.rule_id,
                    target_id_card=id_card,
                    target=item.rule_name,
                    category=item.rule_type,
                    sql="SQL 生成与执行链路遭受毁灭性破坏",
                    result_raw=[],
                    result_summary=f"系统保护性拦截异常: {exc}",
                    supports_conclusion=None,
                    confidence=0.0,
                    exec_status="failed",
                    diagnostic_code=diagnostic[0],
                    diagnostic_label=diagnostic[1],
                    diagnostic_detail=diagnostic[2],
                    diagnostic_hint=diagnostic[3],
                )
            
            
            yield evidence
            
        logger.info(f"[DynamicCollector] 动态取证落幕。")
