# 多智能体评测脚本

本目录用于独立评测“取证链路 -> 辩论链路 -> 结果输出链路”，不接入 FastAPI，不写入系统历史会话表。

## 文件

- `multi_agent_eval.py`: 独立评测入口。
- `policy_eval_samples.json`: 简单、中等、复杂三类样本。
- `outputs/`: 默认结果输出目录。

## 运行

默认使用样本里的 `sql_template` 进入现有 SQL 执行、证据装配、辩论和裁决链路：

```powershell
python tests/agents_test/multi_agent_eval.py --samples tests/agents_test/policy_eval_samples.json
```

只跑前 1 个样本：

```powershell
python tests/agents_test/multi_agent_eval.py --limit 1
```

只跑指定样本：

```powershell
python tests/agents_test/multi_agent_eval.py --case-id complex_001
```

让当前 LLM Text-to-SQL 参与 SQL 生成：

```powershell
python tests/agents_test/multi_agent_eval.py --sql-mode dynamic
```

画像开关：

```powershell
# 默认：simple/medium 关闭画像，complex 开启画像
python tests/agents_test/multi_agent_eval.py --persona-mode auto

# 全部关闭画像，用于基础链路评测
python tests/agents_test/multi_agent_eval.py --persona-mode off

# 全部开启画像，用于系统真实链路对照
python tests/agents_test/multi_agent_eval.py --persona-mode full
```

## 输出

- `outputs/latest_results.json`: 完整证据、辩论、裁决和指标。
- `outputs/latest_summary.md`: 汇总表。

## 指标

- `conclusion_accuracy`: 最终结论是否匹配期望。
- `reason_completeness_rate`: 理由文本是否覆盖样本要求关键词。
- `avg_evidence_reference_rate`: Agent 输出对期望规则引用的覆盖率。
- `conflict_identification_rate`: 复杂冲突样本是否识别出冲突/风险/复核信号。

## 注意

脚本会真实调用当前项目配置的数据库和 LLM。数据库样本数据、模型输出和配置变化都会影响评测结果。
