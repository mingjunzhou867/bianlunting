"""
test_agents.py — Agent 独立判断验证脚本

对3类典型 Persona 跑全部5个 Agent，验证：
  1. 非争议人物（张完美/李老板）→ Agent 结论基本一致
  2. 争议人物（赵争议/陈灰色）  → Agent 之间产生明显分歧

用法：
    python -m tests.test_agents
    python -m tests.test_agents --persona A   # 只测张完美
    python -m tests.test_agents --persona D   # 只测赵争议
"""
import sys
import argparse
from loguru import logger
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from config.database import ping_database
from text2sql.evidence_collector import EvidenceCollector
from agents import create_all_agents

console = Console()

# 测试用 Persona（选4个有代表性的）
TEST_PERSONAS = {
    "A": {
        "id_card": "42090219800101000A",
        "name": "张完美",
        "tag": "A-完美过审",
        "expect": "全部通过，5 Agent 高度一致",
    },
    "B": {
        "id_card": "42090219850505000B",
        "name": "李老板",
        "tag": "B-隐蔽拒审",
        "expect": "股东排斥，5 Agent 应一致拒绝",
    },
    "D": {
        "id_card": "42090219760310000D",
        "name": "赵争议",
        "tag": "D-薛定谔困难",
        "expect": "争议型：Agent 应产生明显分歧",
    },
    "E": {
        "id_card": "42090219780815000E",
        "name": "陈灰色",
        "tag": "E-已注销个体户",
        "expect": "争议型：排斥边界，Agent 立场不一",
    },
    "I": {
        "id_card": "42090219700505000I",
        "name": "钱幽灵",
        "tag": "I-死亡标记",
        "expect": "数据矛盾：应触发数据缺失或分歧",
    },
}

STANCE_COLOR = {
    "支持通过": "green",
    "反对通过": "red",
    "待定": "yellow",
}

CONCLUSION_ICON = {
    "符合": "✅",
    "不符合": "❌",
    "数据缺失": "❓",
}


def run_one_persona(persona: dict, collector: EvidenceCollector) -> dict:
    """对单个 Persona 运行全部 5 个 Agent，返回结果汇总"""
    id_card = persona["id_card"]
    name = persona["name"]

    console.print(f"\n[bold cyan]📦 取证中 → {name} ({id_card})...[/bold cyan]")

    # 取证
    bundle = collector.collect_all(id_card)
    console.print(
        f"  取证完成：{len(bundle.items)} 条证据，成功 {bundle.success_count} 条"
    )

    # 依次让 5 个 Agent 独立判断
    agents = create_all_agents()
    judgments = []

    for agent in agents:
        console.print(f"  [dim]→ {agent.AGENT_ROLE} 判断中...[/dim]")
        try:
            j = agent.judge(bundle, debate_round=0)
            judgments.append(j)
        except Exception as e:
            logger.error(f"[{agent.AGENT_ID}] 判断异常: {e}")
            console.print(f"  [red]  ❌ {agent.AGENT_ROLE} 异常: {e}[/red]")

    return {"persona": persona, "bundle": bundle, "judgments": judgments}


def print_result_table(result: dict):
    """打印单个 Persona 的判断结果表格"""
    persona = result["persona"]
    judgments = result["judgments"]

    console.print()
    console.rule(f"[bold]🎭 {persona['tag']} — {persona['name']}")
    console.print(f"[dim]预期：{persona['expect']}[/dim]")
    console.print()

    if not judgments:
        console.print("[red]没有获得任何 Agent 的判断结果[/red]")
        return

    # 判断结果表格
    table = Table(box=box.ROUNDED, show_lines=True, title="Agent 独立判断结果")
    table.add_column("Agent", style="cyan", width=16)
    table.add_column("结论", width=8)
    table.add_column("立场", width=10)
    table.add_column("置信度", width=7)
    table.add_column("关键发现", style="white")

    for j in judgments:
        icon = CONCLUSION_ICON.get(j.conclusion, "?")
        stance_color = STANCE_COLOR.get(j.stance, "white")
        table.add_row(
            j.agent_role,
            f"{icon} {j.conclusion}",
            f"[{stance_color}]{j.stance}[/{stance_color}]",
            f"{j.confidence:.0%}",
            j.key_finding or j.reasoning[:40] + "…",
        )

    console.print(table)

    # 共识分析
    conclusions = [j.conclusion for j in judgments]
    stances = [j.stance for j in judgments]
    most_common_conclusion = max(set(conclusions), key=conclusions.count)
    agree_count = conclusions.count(most_common_conclusion)
    agree_rate = agree_count / len(judgments)

    stance_counts = {s: stances.count(s) for s in set(stances)}

    if agree_rate >= 0.8:
        color = "green"
        label = f"高共识（{agree_count}/{len(judgments)} 一致：{most_common_conclusion}）"
    elif agree_rate >= 0.6:
        color = "yellow"
        label = f"低度共识（{agree_count}/{len(judgments)} 倾向：{most_common_conclusion}）"
    else:
        color = "red"
        label = f"明显分歧（支持通过 {stance_counts.get('支持通过',0)} / 反对 {stance_counts.get('反对通过',0)} / 待定 {stance_counts.get('待定',0)}）"

    console.print(f"\n  共识度：[{color}]{label}[/{color}]")

    # 展示质疑点（发散探索 Agent 最有价值）
    for j in judgments:
        if j.dissent_points:
            console.print(f"\n  [{j.agent_role}] 质疑点：")
            for point in j.dissent_points[:3]:
                console.print(f"    • {point}")

    return agree_rate


def run_tests(persona_keys: list[str]):
    """主测试流程"""
    console.rule("[bold blue]🤖 Agent 独立判断能力验证")
    console.print()

    # 数据库连接检查
    if not ping_database():
        console.print("[red]❌ 数据库连接失败，终止测试[/red]")
        sys.exit(1)

    collector = EvidenceCollector()
    all_results = []

    for key in persona_keys:
        if key not in TEST_PERSONAS:
            console.print(f"[yellow]⚠️ 未知 Persona 键: {key}，跳过[/yellow]")
            continue
        persona = TEST_PERSONAS[key]
        result = run_one_persona(persona, collector)
        all_results.append(result)

    # 逐个打印结果
    console.print()
    console.rule("[bold blue]📊 结果汇总")

    agree_rates = []
    for result in all_results:
        rate = print_result_table(result)
        if rate is not None:
            agree_rates.append((result["persona"]["tag"], rate))

    # 总结
    console.print()
    console.rule("[bold blue]✅ 测试总结")
    summary = Table(box=box.SIMPLE)
    summary.add_column("Persona")
    summary.add_column("共识度")
    summary.add_column("判断")

    for tag, rate in agree_rates:
        color = "green" if rate >= 0.8 else ("yellow" if rate >= 0.6 else "red")
        label = "高共识（正常）" if rate >= 0.8 else ("低共识（可辩论）" if rate >= 0.6 else "明显分歧（争议）")
        summary.add_row(tag, f"[{color}]{rate:.0%}[/{color}]", label)

    console.print(summary)
    console.print()

    non_controversial = [(t, r) for t, r in agree_rates if t.startswith(("A-", "B-"))]
    controversial = [(t, r) for t, r in agree_rates if not t.startswith(("A-", "B-"))]

    if non_controversial:
        avg_nc = sum(r for _, r in non_controversial) / len(non_controversial)
        console.print(f"  非争议人物平均共识度：[green]{avg_nc:.0%}[/green]（期望 ≥ 80%）")

    if controversial:
        avg_c = sum(r for _, r in controversial) / len(controversial)
        console.print(f"  争议人物平均共识度：[yellow]{avg_c:.0%}[/yellow]（期望 < 70%）")

    if non_controversial and controversial and avg_nc > avg_c + 0.1:
        console.print(Panel(
            "[bold green]🎉 Agent 能有效区分争议与非争议案例！可以进入第四阶段：辩论编排。[/bold green]",
            border_style="green",
        ))
    else:
        console.print(Panel(
            "[bold yellow]⚠️ 部分结果不符合预期，请检查 Agent Prompt 或取证数据。[/bold yellow]",
            border_style="yellow",
        ))


if __name__ == "__main__":
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <7}</level> | {message}",
    )

    parser = argparse.ArgumentParser(description="Agent 独立判断验证")
    parser.add_argument(
        "--persona",
        nargs="*",
        default=list(TEST_PERSONAS.keys()),
        help="要测试的 Persona 键（A B D E I），默认全部",
    )
    args = parser.parse_args()

    run_tests(args.persona)
