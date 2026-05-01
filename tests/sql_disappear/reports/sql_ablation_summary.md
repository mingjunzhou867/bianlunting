# SQL 链路消融实验汇总

## 测试目的

本组实验用于评估不同 SQL 生成链路在政策审查数据库场景中的可靠性，重点验证：

- 仅依靠大模型根据自然语言直接生成 SQL 是否可行
- 提供数据库 schema 后是否能提升 SQL 可执行性
- 关闭自动修复后，SQL Harness 的基础链路效果如何
- 完整 SQL Harness 是否能通过执行校验和错误修复显著提升最终结果正确性

## 测试内容

| 测试组 | 测试脚本 / 报告位置 | 测试内容 |
| --- | --- | --- |
| Direct LLM | `tests/sql_disappear/reports` | 只把自然语言问题输入 LLM，让模型直接生成 SQL，不提供 schema，不使用 Harness 约束。 |
| Schema-aware LLM | `tests/sql_schema_baseline/reports` | 输入自然语言问题和数据库 schema，让 LLM 单次生成 SQL，不使用 retry、auto repair、漂移检测。 |
| Harness w/o Repair | `tests/sql_no_repair/reports` | 使用 SQL Harness 的提示组织、语法检查、执行校验和结果对比，但关闭 retry/auto repair。 |
| Full SQL Harness | `tests/sql_test/reports/all_samples_20260430_174723.json` | 完整 SQL Harness：SQL 生成、语法校验、数据库执行、结果集对比、错误反馈修复、结构漂移检测。 |

## 测试指标

| 指标 | 含义 |
| --- | --- |
| `sql_generation_success_rate` | 是否成功生成 SQL 文本。 |
| `syntax_pass_rate` / `first_syntax_pass_rate` | SQL 是否通过 `EXPLAIN` 等语法检查。 |
| `execution_success_rate` / `first_execution_success_rate` | SQL 是否能在真实数据库中执行。 |
| `result_match_rate` / `final_result_match_rate` | 生成 SQL 与 gold SQL 的执行结果是否一致。 |
| `retry_trigger_rate` | 完整 Harness 中触发重试修复的样本比例。 |
| `retry_repair_success_rate` | 触发重试后最终修复成功的比例。 |
| `structural_warning_rate` | 结果匹配但 SQL 结构存在额外过滤、额外 JOIN、投影差异等漂移风险的比例。 |
| `avg_latency_ms` / `final_avg_latency_ms` | 平均耗时。 |

## 实验结果

| 测试组 | 生成成功率 | 语法通过率 | 执行成功率 | 结果匹配率 | 平均耗时 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Direct LLM | 100.00% | 0.00% | 0.00% | 0.00% | 5440.59 ms |
| Schema-aware LLM | 100.00% | 96.25% | 96.25% | 48.75% | 5047.56 ms |
| Harness w/o Repair | 100.00% | 100.00% | 100.00% | 65.00% | 6419.77 ms |
| Full SQL Harness | 100.00% | 100.00% | 100.00% | 87.50% | 8974.95 ms |

## 分类结果对比

| 类别 | Harness w/o Repair | Full SQL Harness |
| --- | ---: | ---: |
| `simple_test` | 65.00% | 100.00% |
| `condition_test` | 65.00% | 75.00% |
| `sum_test` | 55.00% | 95.00% |
| `muti_test` | 75.00% | 80.00% |

## 修复与漂移指标

| 指标 | Harness w/o Repair | Full SQL Harness |
| --- | ---: | ---: |
| retry_trigger_rate | 0.00% | 37.50% |
| retry_repair_success_rate | 0.00% | 66.67% |
| avg_retry_count | 0.00 | 0.50 |
| structural_warning_rate | 32.50% | 7.50% |
| failure_count | 28 | 10 |

## 分析结论

1. **Direct LLM 基本不可用。**

   Direct LLM 虽然生成成功率为 `100.00%`，但语法通过率、执行成功率和结果匹配率均为 `0.00%`。主要原因是模型在没有 schema 约束时容易编造表名或字段名，导致 SQL 无法在真实数据库中执行。

2. **Schema-aware LLM 能显著提升可执行性，但结果正确性不足。**

   加入 schema 后，语法通过率和执行成功率均提升到 `96.25%`，说明 schema 能有效减少表名、字段名幻觉。但结果匹配率只有 `48.75%`，说明“SQL 能执行”并不等于“查询语义正确”。

3. **Harness 基础链路优于普通 schema-aware 生成。**

   Harness w/o Repair 的结果匹配率达到 `65.00%`，相比 Schema-aware LLM 提升 `16.25` 个百分点。这说明 SQL Harness 的提示组织、约束表达、真实执行校验和结果对比机制对 SQL 正确性有明显帮助。

4. **自动修复模块贡献显著。**

   完整 SQL Harness 的最终结果匹配率达到 `87.50%`，相比关闭修复的 Harness 提升 `22.50` 个百分点。完整链路中 `37.50%` 的样本触发重试，触发重试后的修复成功率为 `66.67%`，说明错误反馈和 retry repair 是提升 SQL 可靠性的关键模块。

5. **结构漂移检测提升可信性。**

   Harness w/o Repair 的结构漂移告警率为 `32.50%`，完整 SQL Harness 降至 `7.50%`。这说明完整链路不仅提升结果匹配率，也减少了“结果可能碰巧正确，但 SQL 结构偏离用户意图”的风险。

## 报告表述建议

SQL 消融实验表明，普通大模型直接生成 SQL 在真实数据库场景下容易出现表名、字段名幻觉，缺乏可用性；加入 schema 后可以显著提升语法和执行成功率，但仍难以保证查询语义正确。项目构建的 SQL Harness 通过结构化提示、语法检查、真实数据库执行、结果集对比、错误反馈修复和结构漂移检测，将最终结果匹配率提升至 `87.50%`。相比关闭修复机制的 Harness，完整链路提升 `22.50` 个百分点，验证了 SQL Harness 在可执行、可验证、可修复和可信检测方面的有效性。
