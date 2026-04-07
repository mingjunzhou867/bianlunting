"""
main.py — 项目主入口
当前阶段（第一阶段）：冒烟测试
  1. 加载并打印配置
  2. 测试数据库连接
  3. 测试 LLM API 连通性

后续阶段会在此逐步添加：
  - evidence_collector 取证
  - debate_orchestrator 辩论编排
  - 批量评测入口
"""
import sys
from loguru import logger
from rich.console import Console
from rich.table import Table
from rich import box

from config.settings import settings
from config.database import ping_database
from config.llm_client import ping_llm

console = Console()


def print_config_summary():
    """打印当前配置摘要（不显示敏感的 API Key 明文）"""
    table = Table(title="⚙️  当前系统配置", box=box.ROUNDED, show_lines=True)
    table.add_column("配置项", style="cyan", width=22)
    table.add_column("值", style="white")

    table.add_row("LLM 提供商",    settings.llm_provider)
    table.add_row("模型",          settings.llm_model)
    table.add_row("API Key",       "***已配置***" if settings.llm_api_key else "⚠️  未配置")
    table.add_row("API Base URL",  settings.get_effective_base_url() or "(使用默认)")
    table.add_row("数据库",        f"{settings.db_host}:{settings.db_port}/{settings.db_name}")
    table.add_row("系统模拟日期",  settings.system_date)
    table.add_row("辩论最大轮数",  str(settings.debate_max_rounds))
    table.add_row("共识阈值",      f"{settings.consensus_threshold:.0%}")

    console.print(table)


def smoke_test() -> bool:
    """
    冒烟测试：验证数据库和 LLM 均可用。
    返回 True 表示全部通过。
    """
    console.rule("[bold blue]🚀 系统冒烟测试")

    # 1. 配置摘要
    print_config_summary()
    console.print()

    # 2. 数据库连接测试
    console.print("[bold]📦 测试数据库连接...[/bold]")
    db_ok = ping_database()

    # 3. LLM API 测试
    console.print("[bold]🤖 测试 LLM API 连通性...[/bold]")
    llm_ok = ping_llm()

    # 4. 结果汇总
    console.print()
    console.rule("[bold]测试结果")
    console.print(f"  数据库：{'[green]✅ 通过[/green]' if db_ok  else '[red]❌ 失败[/red]'}")
    console.print(f"  LLM：  {'[green]✅ 通过[/green]' if llm_ok else '[red]❌ 失败[/red]'}")
    console.print()

    if db_ok and llm_ok:
        console.print("[bold green]🎉 所有检查通过，系统就绪！[/bold green]")
    else:
        console.print("[bold red]⚠️  部分检查未通过，请检查 config/.env 配置。[/bold red]")

    return db_ok and llm_ok


if __name__ == "__main__":
    # 配置 loguru 日志格式
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <7}</level> | {message}",
    )

    success = smoke_test()
    sys.exit(0 if success else 1)
