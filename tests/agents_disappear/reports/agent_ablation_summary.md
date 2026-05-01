# Agent 链路消融实验汇总

## 测试目的

本组实验用于评估政策审查场景中不同智能体链路设计对最终决策质量的影响，重点验证：

- 单 Agent 是否足以完成政策判断
- 正反辩论是否提升理由完整性和证据覆盖
- 去除证据约束后，多 Agent 是否仍然可靠
- 完整多智能体链路是否在可解释性、证据引用和综合决策质量上最优

## 测试内容

| 测试组 | 测试脚本 / 报告位置 | 测试内容 |
| --- | --- | --- |
| Single Agent | `tests/agents_disappear/reports/single_agent` | 仅使用一个严格合规 Agent，根据 SQL 取证结果直接给出政策资格判断。 |
| Pro-Con Debate | `tests/agents_disappear/reports/pro_con_debate` | 使用严格合规 Agent 与宽松业务 Agent 进行正反辩论，再形成裁决。 |
| No Evidence Constraint | `tests/agents_disappear/reports/no_evidence_constraint` | 保留完整 Agent 数量，但隐藏证据卡片，测试无证据约束下的判断质量。 |
| Full Multi-Agent | `tests/agents_test/outputs` | 完整链路：SQL 取证、证据卡片、多角色辩论、共识判断、仲裁裁决。 |

## 测试指标

| 指标 | 含义 |
| --- | --- |
| `conclusion_accuracy` | 最终结论标签是否正确，只判断 `pass / fail / missing`。 |
| `decision_quality_score` | 综合决策质量分，结合结论正确性、理由完整性、证据引用、规则覆盖和冲突识别。 |
| `overall_pass_rate` | 严格通过率，要求结论正确、理由完整、证据引用达标、规则覆盖完整且无取证失败。 |
| `reason_completeness_rate` | Agent 输出理由是否覆盖样本期望关键词。 |
| `avg_evidence_reference_rate` | Agent 输出中对预期规则/证据的平均引用覆盖率。 |
| `consensus_reached_rate` | 智能体是否达到系统设定共识阈值。 |
| `conflict_identification_rate` | 对复杂冲突样本，是否识别出冲突、风险或复核信号。 |

## 综合质量分公式

`decision_quality_score` 的计算方式为：

```text
decision_quality_score =
0.35 * conclusion_correct
+ 0.25 * reason_complete
+ 0.20 * evidence_referenced
+ 0.10 * rule_coverage_pass
+ 0.10 * conflict_pass
```

其中：

- `conclusion_correct`：最终结论是否正确
- `reason_complete`：理由是否完整
- `evidence_referenced`：证据引用是否达到最低要求
- `rule_coverage_pass`：政策规则是否全部覆盖
- `conflict_pass`：需要识别冲突时是否识别；不需要冲突时默认通过

该指标用于避免只看最终标签准确率，从而更符合政务审查中“可解释、可追溯、可复核”的要求。

## 实验结果

| 测试组 | 结论准确率 | 综合决策质量分 | 严格通过率 | 理由完整率 | 平均证据引用率 | 共识率 | 冲突识别率 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Single Agent | 87.50% | 80.83% | 41.67% | 70.83% | 62.50% | 100.00% | 100.00% |
| Pro-Con Debate | 87.50% | 85.63% | 54.17% | 83.33% | 68.75% | 79.17% | 100.00% |
| No Evidence Constraint | 12.50% | 43.12% | 0.00% | 75.00% | 0.00% | 100.00% | 100.00% |
| Full Multi-Agent | 87.50% | 91.04% | 70.83% | 91.67% | 84.72% | 91.67% | 100.00% |

## 分析结论

1. **无证据约束组表现最差。**

   No Evidence Constraint 的结论准确率仅为 `12.50%`，严格通过率为 `0.00%`，平均证据引用率为 `0.00%`。这说明即使保留多 Agent 结构，如果没有 SQL 取证结果和证据卡片约束，系统无法形成可靠判断。

2. **高共识不等于高可靠。**

   No Evidence Constraint 的共识率为 `100.00%`，但综合决策质量分只有 `43.12%`。这说明多个 Agent 在缺少证据时可能一致给出保守或错误判断，因此多 Agent 共识必须建立在证据约束之上。

3. **正反辩论优于单 Agent。**

   Pro-Con Debate 相比 Single Agent，综合决策质量分从 `80.83%` 提升到 `85.63%`，严格通过率从 `41.67%` 提升到 `54.17%`，理由完整率从 `70.83%` 提升到 `83.33%`。说明正反视角可以提升解释质量和规则覆盖。

4. **完整多智能体链路综合效果最好。**

   Full Multi-Agent 的综合决策质量分达到 `91.04%`，严格通过率达到 `70.83%`，证据引用率达到 `84.72%`，均为四组最高。该结果说明完整链路不仅能给出正确结论，还能提供更充分的理由、更高的证据引用和更稳定的可解释裁决。

## 报告表述建议

本实验表明，政策审查智能体系统的核心优势并不只体现在最终标签准确率上，而体现在证据约束、理由完整性、冲突识别和可追溯裁决能力上。单 Agent 和正反辩论在已有证据输入下可以保持较高结论准确率，但完整多智能体链路在综合决策质量上表现最优。去除证据约束后，系统虽然仍能形成共识，但结论准确率和证据引用能力显著下降，证明“SQL 取证 + 证据卡片 + 多角色辩论 + 仲裁裁决”的完整链路具有必要性。
