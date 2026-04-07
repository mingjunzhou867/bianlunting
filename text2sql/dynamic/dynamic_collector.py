from loguru import logger

from cognition.evidence_planner import EvidencePlanner
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

    def _resolve_no_data_semantics(self, item):
        rule_id = item.rule_id
        if rule_id == "P001_FLEX_003":
            return (
                "未查询到身份切换记录，当前未发现从灵活就业转为单位参保的切换风险。",
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
                if exec_status == "no_data":
                    no_data_resolution = self._resolve_no_data_semantics(item)
                    if no_data_resolution:
                        assembled.result_summary, assembled.supports_conclusion = no_data_resolution
                
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
