"""Generate presentation-ready charts for SQL chain evaluation reports."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


DEFAULT_REPORT = Path(__file__).resolve().parent / "reports" / "all_samples_20260430_174723.json"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "reports" / "visuals"


def load_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def configure_matplotlib() -> None:
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 140
    plt.rcParams["savefig.dpi"] = 220


def pct(value: float) -> float:
    return round(value * 100, 2)


def save(fig: plt.Figure, output_dir: Path, name: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / name
    fig.savefig(path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return path


def chart_kpi_cards(summary: dict[str, Any], output_dir: Path) -> Path:
    metrics = [
        ("SQL生成成功率", pct(summary["sql_generation_success_rate"]), "%", "#1f77b4"),
        ("SQL执行成功率", pct(summary["final_execution_success_rate"]), "%", "#2ca02c"),
        ("初次结果匹配率", pct(summary["first_result_match_rate"]), "%", "#ff7f0e"),
        ("最终结果匹配率", pct(summary["final_result_match_rate"]), "%", "#2ca02c"),
        ("修复提升幅度", pct(summary["final_result_match_rate"] - summary["first_result_match_rate"]), "百分点", "#9467bd"),
        ("结构偏差率", pct(summary["structural_warning_rate"]), "%", "#d62728"),
    ]

    fig, ax = plt.subplots(figsize=(13, 6.4))
    fig.patch.set_facecolor("#f6f8fb")
    ax.set_axis_off()
    ax.set_title("SQL链路全样本评估核心指标", fontsize=22, fontweight="bold", pad=18)

    for idx, (label, value, unit, color) in enumerate(metrics):
        row, col = divmod(idx, 3)
        x = 0.05 + col * 0.315
        y = 0.54 - row * 0.34
        card = FancyBboxPatch(
            (x, y),
            0.27,
            0.24,
            boxstyle="round,pad=0.018,rounding_size=0.025",
            linewidth=1.2,
            edgecolor="#d7dde8",
            facecolor="white",
            transform=ax.transAxes,
        )
        ax.add_patch(card)
        ax.text(x + 0.025, y + 0.165, label, fontsize=13, color="#3b4559", transform=ax.transAxes)
        ax.text(x + 0.025, y + 0.07, f"{value:g}", fontsize=30, fontweight="bold", color=color, transform=ax.transAxes)
        ax.text(x + 0.15, y + 0.081, unit, fontsize=13, color="#5b6578", transform=ax.transAxes)

    ax.text(
        0.05,
        0.05,
        "样本覆盖：简单查询、条件查询、聚合查询、多表查询，共80条。结果匹配以SQL执行结果为准。",
        fontsize=12,
        color="#5b6578",
        transform=ax.transAxes,
    )
    return save(fig, output_dir, "01_kpi_cards.png")


def chart_accuracy_lift(summary: dict[str, Any], output_dir: Path) -> Path:
    first = pct(summary["first_result_match_rate"])
    final = pct(summary["final_result_match_rate"])
    lift = final - first

    fig, ax = plt.subplots(figsize=(9.5, 6))
    fig.patch.set_facecolor("white")
    bars = ax.bar(["初次结果匹配率", "最终结果匹配率"], [first, final], color=["#ffb000", "#2ca02c"], width=0.48)
    ax.set_ylim(0, 100)
    ax.set_ylabel("匹配率（%）")
    ax.set_title("错误诊断与重试后的结果匹配率提升", fontsize=18, fontweight="bold", pad=16)
    ax.grid(axis="y", alpha=0.18)
    ax.spines[["top", "right"]].set_visible(False)

    for bar in bars:
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 2,
            f"{bar.get_height():.1f}%",
            ha="center",
            va="bottom",
            fontsize=14,
            fontweight="bold",
        )
    ax.annotate(
        f"+{lift:.1f} 个百分点",
        xy=(1, final),
        xytext=(0.5, 93),
        arrowprops={"arrowstyle": "->", "color": "#6f42c1", "lw": 2},
        ha="center",
        fontsize=14,
        color="#6f42c1",
        fontweight="bold",
    )
    return save(fig, output_dir, "02_accuracy_lift.png")


def build_category_rows(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        grouped[case["category"]].append(case)

    rows: list[dict[str, Any]] = []
    for category, items in sorted(grouped.items()):
        total = len(items)
        rows.append(
            {
                "category": category.replace("_test", ""),
                "total": total,
                "first": 100 * sum(bool(item["first_result_match"]) for item in items) / total,
                "final": 100 * sum(bool(item["final_success"]) for item in items) / total,
                "warning": 100 * sum(bool(item.get("has_structural_warnings")) for item in items) / total,
            }
        )
    return rows


def chart_category_comparison(cases: list[dict[str, Any]], output_dir: Path) -> Path:
    rows = build_category_rows(cases)
    labels = [row["category"] for row in rows]
    first = [row["first"] for row in rows]
    final = [row["final"] for row in rows]

    fig, ax = plt.subplots(figsize=(11, 6.2))
    x = range(len(labels))
    width = 0.34
    ax.bar([i - width / 2 for i in x], first, width=width, label="初次结果匹配率", color="#ffb000")
    ax.bar([i + width / 2 for i in x], final, width=width, label="最终结果匹配率", color="#2ca02c")
    ax.set_xticks(list(x), labels)
    ax.set_ylim(0, 105)
    ax.set_ylabel("匹配率（%）")
    ax.set_title("不同SQL场景下的结果匹配表现", fontsize=18, fontweight="bold", pad=16)
    ax.legend(loc="lower right")
    ax.grid(axis="y", alpha=0.18)
    ax.spines[["top", "right"]].set_visible(False)

    for i, value in enumerate(final):
        ax.text(i + width / 2, value + 2, f"{value:.0f}%", ha="center", fontsize=11, fontweight="bold")
    return save(fig, output_dir, "03_category_comparison.png")


def chart_final_outcome(summary: dict[str, Any], output_dir: Path) -> Path:
    total = summary["total_cases"]
    success = round(summary["final_result_match_rate"] * total)
    failed = total - success
    warnings = round(summary["structural_warning_rate"] * total)
    clean_success = max(success - warnings, 0)

    values = [clean_success, warnings, failed]
    labels = ["匹配且无结构偏差", "匹配但有结构警告", "最终未匹配"]
    colors = ["#2ca02c", "#ffb000", "#d62728"]

    fig, ax = plt.subplots(figsize=(8.4, 7))
    wedges, _texts, autotexts = ax.pie(
        values,
        labels=labels,
        colors=colors,
        startangle=90,
        autopct=lambda p: f"{p:.1f}%",
        pctdistance=0.72,
        wedgeprops={"linewidth": 1, "edgecolor": "white"},
    )
    for text in autotexts:
        text.set_color("white")
        text.set_fontweight("bold")
        text.set_fontsize(12)
    ax.set_title("最终结果质量分布", fontsize=18, fontweight="bold", pad=16)
    ax.legend(wedges, [f"{label}: {value}条" for label, value in zip(labels, values)], loc="lower center", bbox_to_anchor=(0.5, -0.08), ncol=1)
    return save(fig, output_dir, "04_final_quality_donut.png")


def classify_failure(case: dict[str, Any]) -> str:
    case_id = case["case_id"]
    if case_id in {"condition_test:17", "condition_test:18", "condition_test:19", "condition_test:20", "muti_test:07", "muti_test:12"}:
        return "聚合列名/投影差异"
    if case_id in {"muti_test:10", "muti_test:14"}:
        return "多表JOIN语义偏差"
    if case_id == "condition_test:14":
        return "排序/TopN差异"
    if case_id == "sum_test:14":
        return "企业维度映射偏差"
    return "其他语义差异"


def chart_failure_reasons(cases: list[dict[str, Any]], output_dir: Path) -> Path:
    failed = [case for case in cases if not case["final_success"]]
    counts = Counter(classify_failure(case) for case in failed)
    labels = list(counts.keys())
    values = list(counts.values())

    fig, ax = plt.subplots(figsize=(10, 5.6))
    bars = ax.barh(labels, values, color=["#4c78a8", "#f58518", "#e45756", "#72b7b2"][: len(values)])
    ax.set_xlabel("失败案例数")
    ax.set_title("剩余未匹配案例的问题分布", fontsize=18, fontweight="bold", pad=16)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", alpha=0.18)
    for bar in bars:
        ax.text(bar.get_width() + 0.08, bar.get_y() + bar.get_height() / 2, f"{int(bar.get_width())}条", va="center", fontsize=12)
    ax.set_xlim(0, max(values or [1]) + 1)
    return save(fig, output_dir, "05_failure_reasons.png")


def write_markdown(paths: list[Path], report_path: Path, output_dir: Path) -> Path:
    md_path = output_dir / "VISUAL_SUMMARY.md"
    lines = [
        "# SQL链路全样本评估图示说明",
        "",
        f"数据来源：`{report_path}`",
        "",
        "## 图示清单",
        "",
    ]
    captions = {
        "01_kpi_cards.png": "核心指标卡：适合放在评估结果首页。",
        "02_accuracy_lift.png": "匹配率提升图：突出从初次生成到最终修复后的提升幅度。",
        "03_category_comparison.png": "分类表现对比：展示简单、条件、聚合、多表场景的差异。",
        "04_final_quality_donut.png": "最终质量分布：区分无偏差匹配、有结构警告匹配、未匹配。",
        "05_failure_reasons.png": "剩余问题分布：说明后续优化方向。",
    }
    for path in paths:
        lines.extend([f"### {path.name}", "", captions.get(path.name, ""), "", f"![{path.name}]({path.name})", ""])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate SQL evaluation charts.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configure_matplotlib()
    data = load_report(args.report)
    summary = data["summary"]
    cases = data["cases"]

    paths = [
        chart_kpi_cards(summary, args.output_dir),
        chart_accuracy_lift(summary, args.output_dir),
        chart_category_comparison(cases, args.output_dir),
        chart_final_outcome(summary, args.output_dir),
        chart_failure_reasons(cases, args.output_dir),
    ]
    md_path = write_markdown(paths, args.report, args.output_dir)
    print(f"Generated {len(paths)} charts:")
    for path in paths:
        print(path)
    print(md_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
