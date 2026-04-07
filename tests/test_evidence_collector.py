"""
test_evidence_collector.py — 取证模块验证脚本

对 9 个 Persona 分别执行 collect_all / collect_proactive，
检查证据完整性、自动verdict、异常处理等关键逻辑。

用法：
    python -m tests.test_evidence_collector
"""
import sys
from typing import Optional

from loguru import logger
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

# ── 项目导入 ──────────────────────────────────────────────
from config.settings import settings
from config.database import ping_database
from evidence.evidence_model import EvidenceBundle, EvidenceItem
from text2sql.evidence_collector import EvidenceCollector

console = Console()

# ── 9 个 Persona 定义 ──────────────────────────────────────
PERSONAS = [
    {
        "id_card": "42090219800101000A",
        "name": "张完美",
        "tag": "A-完美过审",
        "expect_qualification": "全部通过",
        "checks": [
            ("BASIC_001", "success", True,  "基本信息应查到且通过"),
            ("BASIC_002", "success", True,  "社保缴费记录应存在"),
            ("BASIC_003", "success", True,  "灵活就业登记应存在"),
            ("BASIC_004", "success", True,  "失业登记应有效"),
            ("BASIC_005", "success", True,  "困难认定应有效"),
            ("EXCL_001", "no_data", True,   "无工商登记 → 不触发排斥"),
            ("EXCL_005", "no_data", True,   "无股东记录 → 不触发排斥"),
            ("EXCL_008", "no_data", True,   "无单位医保缴费 → 不触发排斥"),
        ],
    },
    {
        "id_card": "42090219850505000B",
        "name": "李老板",
        "tag": "B-隐蔽拒审",
        "expect_qualification": "股东排斥",
        "checks": [
            ("BASIC_001", "success", True,  "基本信息应查到"),
            ("EXCL_005", "success", False,  "⚠️ 应查到股东记录 → 排斥"),
        ],
    },
    {
        "id_card": "42090219680401000C",
        "name": "王精算",
        "tag": "C-精准算账",
        "expect_qualification": "基础通过+精算测试",
        "checks": [
            ("BASIC_001", "success", True,  "基本信息应查到"),
            ("CALC_002", "success", None,   "历史已领月数应有数据"),
            ("CALC_003", "success", None,   "退休距离应有数据"),
            ("CALC_004", "success", None,   "灵活就业缴费月数应有数据"),
        ],
    },
    {
        "id_card": "42090219760310000D",
        "name": "赵争议",
        "tag": "D-薛定谔困难人员",
        "expect_qualification": "争议型",
        "checks": [
            ("BASIC_001", "success", True,  "基本信息应查到"),
            ("BASIC_004", "no_data", False, "无失业登记 → 不通过"),
            ("BASIC_005", "no_data", False, "无困难认定 → 不通过"),
        ],
    },
    {
        "id_card": "42090219780815000E",
        "name": "陈灰色",
        "tag": "E-已注销个体户",
        "expect_qualification": "排斥争议",
        "checks": [
            ("BASIC_001", "success", True,  "基本信息应查到"),
            ("EXCL_001", "success", False,  "⚠️ business_role=个体工商户 → 触发排斥"),
        ],
    },
    {
        "id_card": "42090219710321000F",
        "name": "吴边界",
        "tag": "F-退休年龄线上女性",
        "expect_qualification": "年龄争议",
        "checks": [
            ("BASIC_001", "success", True,  "基本信息应查到"),
            ("EXCL_007", "success", None,   "年龄/退休信息应有数据"),
            ("CALC_002", "success", None,   "历史已领月数应有数据(18个月)"),
            ("CALC_003", "success", None,   "退休距离应有数据"),
        ],
    },
    {
        "id_card": "42090219820620000G",
        "name": "孙迷雾",
        "tag": "G-事业单位临聘",
        "expect_qualification": "推断争议",
        "checks": [
            ("BASIC_001", "success", True,  "基本信息应查到"),
            ("EXCL_008", "success", False,  "⚠️ 应查到历史单位医保缴费(101) → 触发排斥"),
        ],
    },
    {
        "id_card": "42090220010901000H",
        "name": "郑重叠",
        "tag": "H-高校毕业生算账",
        "expect_qualification": "精算+排斥交叉",
        "checks": [
            ("BASIC_001", "success", True,  "基本信息应查到"),
            ("EXCL_008", "success", False,  "⚠️ 12月医保310有101记录 → 触发排斥"),
            ("CALC_002", "success", None,   "历史已领月数应有数据(6个月)"),
        ],
    },
    {
        "id_card": "42090219700505000I",
        "name": "钱幽灵",
        "tag": "I-死亡标记幽灵人",
        "expect_qualification": "数据矛盾",
        "checks": [
            ("BASIC_001", "success", False, "基本信息应查到，但 life_status=死亡 → 基础条件不通过"),
        ],
    },
]


def check_item(item: EvidenceItem, expected_status: str, expected_support: Optional[bool], desc: str) -> tuple[bool, str]:
    """
    检查单条证据是否符合预期。
    返回 (passed, message)。
    """
    issues = []

    # 检查执行状态
    if item.exec_status != expected_status:
        issues.append(f"exec_status 期望 '{expected_status}' 实际 '{item.exec_status}'")

    # 检查 supports_conclusion（None 表示不检查具体值，只要不报错）
    if expected_support is not None and item.supports_conclusion != expected_support:
        issues.append(f"supports 期望 {expected_support} 实际 {item.supports_conclusion}")

    if issues:
        return False, f"❌ {desc} → {'; '.join(issues)}"
    return True, f"✅ {desc}"


def run_persona_checks(collector: EvidenceCollector, persona: dict) -> tuple[int, int, list[str]]:
    """
    对单个 Persona 执行全量取证并校验。
    返回 (passed_count, total_checks, detail_messages)。
    """
    id_card = persona["id_card"]
    name = persona["name"]

    # 执行全量取证（功能一+二）
    bundle = collector.collect_all(id_card)

    passed = 0
    total = len(persona["checks"])
    details = []

    # 基础完整性检查
    if not bundle.items:
        details.append(f"❌ 取证结果为空！collect_all 返回 0 条证据")
        return 0, total, details

    details.append(f"📋 共取证 {len(bundle.items)} 条 | 成功 {bundle.success_count} 条 | 失败规则: {bundle.failed_rules or '无'}")

    # 逐条检验
    rule_map = bundle.by_rule
    for rule_id, exp_status, exp_support, desc in persona["checks"]:
        if rule_id not in rule_map:
            details.append(f"❌ 规则 {rule_id} 未在取证结果中找到")
            continue

        item = rule_map[rule_id]
        ok, msg = check_item(item, exp_status, exp_support, desc)
        if ok:
            passed += 1
        details.append(f"  [{rule_id}] {msg}")

    return passed, total, details


def run_proactive_checks(collector: EvidenceCollector) -> list[str]:
    """测试功能三：主动服务（全库扫描型规则）"""
    details = []
    try:
        bundle = collector.collect_proactive()
        details.append(f"📋 主动服务取证完成，共 {len(bundle.items)} 条证据")
        for item in bundle.items:
            status_icon = "✅" if item.exec_status == "success" else ("⚪" if item.exec_status == "no_data" else "❌")
            details.append(f"  [{item.rule_id}] {status_icon} {item.exec_status} | {item.result_summary[:80]}")
    except Exception as e:
        details.append(f"❌ 主动服务取证异常: {e}")
    return details


def run_all_tests():
    """主测试流程"""
    console.rule("[bold blue]🧪 取证模块（EvidenceCollector）验证测试")
    console.print()

    # 0. 前置检查：数据库连通
    console.print("[bold]📦 检查数据库连接...[/bold]")
    if not ping_database():
        console.print("[bold red]❌ 数据库连接失败，终止测试。请检查 config/.env[/bold red]")
        return False

    console.print("[green]✅ 数据库连接正常[/green]\n")

    collector = EvidenceCollector()
    total_passed = 0
    total_checks = 0
    all_ok = True

    # 1. 逐个 Persona 测试
    for persona in PERSONAS:
        tag = persona["tag"]
        name = persona["name"]
        id_card = persona["id_card"]

        console.rule(f"[bold cyan]🎭 {tag} — {name} ({id_card})")

        try:
            passed, total, details = run_persona_checks(collector, persona)
        except Exception as e:
            console.print(f"[bold red]💥 取证过程发生异常: {e}[/bold red]")
            import traceback
            traceback.print_exc()
            all_ok = False
            continue

        total_passed += passed
        total_checks += total

        # 打印详情
        for line in details:
            console.print(line)

        # 状态标记
        if passed == total:
            console.print(f"\n[bold green]✅ {name}: {passed}/{total} 检查项全部通过[/bold green]")
        else:
            console.print(f"\n[bold yellow]⚠️  {name}: {passed}/{total} 检查项通过，存在不符预期项[/bold yellow]")
            all_ok = False

        console.print()

    # 2. 功能三：主动服务测试
    console.rule("[bold cyan]🔍 功能三：主动服务取证（全库扫描）")
    proactive_details = run_proactive_checks(collector)
    for line in proactive_details:
        console.print(line)
    console.print()

    # 3. 汇总报告
    console.rule("[bold blue]📊 测试汇总")

    summary_table = Table(box=box.ROUNDED, show_lines=True)
    summary_table.add_column("指标", style="cyan")
    summary_table.add_column("结果", style="white")

    summary_table.add_row("测试 Persona 数", str(len(PERSONAS)))
    summary_table.add_row("总检查项", str(total_checks))
    summary_table.add_row("通过检查项", f"[green]{total_passed}[/green]")
    summary_table.add_row("失败检查项", f"[red]{total_checks - total_passed}[/red]" if total_checks > total_passed else "[green]0[/green]")
    summary_table.add_row("整体结果", "[bold green]✅ 全部通过[/bold green]" if all_ok else "[bold yellow]⚠️ 存在异常[/bold yellow]")

    console.print(summary_table)
    console.print()

    if all_ok:
        console.print(Panel(
            "[bold green]🎉 取证模块验证通过！可以进入第三阶段：Agent 开发。[/bold green]",
            border_style="green",
        ))
    else:
        console.print(Panel(
            "[bold yellow]⚠️  部分检查未通过，请根据上方详情排查 SQL 模板或数据问题。[/bold yellow]",
            border_style="yellow",
        ))

    return all_ok


if __name__ == "__main__":
    logger.remove()
    logger.add(
        sys.stderr,
        level="DEBUG",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <7}</level> | {message}",
    )

    success = run_all_tests()
    sys.exit(0 if success else 1)
