# Phase 1: 适配器边界（Slice 1） - Context

**Gathered:** 2026-03-24 (discuss mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

在不触动取证逻辑的前提下，稳固 Debate agent 的下游接口，使后续取证管道替换对 agent 完全透明。交付 `project_evidence()` 函数、agent prompt 改造、Slice 1 回归测试套件。

</domain>

<decisions>
## Implementation Decisions

### Projection 数据结构
- **D-01:** 新建 `evidence/evidence_projection.py`，定义 `EvidenceProjection` 和 `EvidenceSummaryCard` 两个 Pydantic BaseModel（与项目现有 EvidenceItem、AgentJudgment 模式一致）
- **D-02:** `EvidenceProjection` 包含 task_header、target_person、policy_scope、cards（list[EvidenceSummaryCard]）、uncertainty_markers、total_cards、resolved_count、unresolved_count
- **D-03:** `EvidenceSummaryCard` 包含 card_id、question、finding、status（supports/contradicts/unresolved/missing）、confidence、artifact_refs

### Agent Prompt 改造
- **D-04:** 新增 `format_projection()` 函数（在 base_agent.py 中），接收 EvidenceProjection，输出 agent 可读文本
- **D-05:** `judge()` 和 `debate_respond()` 签名改为接收 `EvidenceProjection` 而非 `EvidenceBundle`
- **D-06:** 保留 `format_evidence_bundle()` 不删除（零删除约束），但 agent 主路径不再调用它
- **D-07:** orchestrator 在调用 agent 之前先调 `project_evidence(bundle)` 转换为 EvidenceProjection

### 回归测试
- **D-08:** 三层测试：单元测试（project_evidence 输入输出）、prompt 对比测试（新旧 prompt 信息不丢失且 token 数不超过旧值）、手动 LLM 对比（固定 seed 跑一次记录到 reports/）
- **D-09:** 自动化测试聚焦确定性验证（数据结构、字段完整性、token 数），LLM 结论对比作为手动验证

### 适配器集成
- **D-10:** `project_evidence()` 作为 `debate_orchestrator.py` 模块级纯函数，签名：`def project_evidence(bundle: EvidenceBundle) -> EvidenceProjection`
- **D-11:** 本 Phase 仅支持 EvidenceBundle 输入，不支持 Evidence v2（Phase 3 交付物）
- **D-12:** project_evidence() 内部不调用 text_to_sql / get_dict / auto_debug_sql（工具隔离约束）

### Claude's Discretion
- format_projection() 的具体文本格式化样式
- EvidenceSummaryCard.status 的映射逻辑细节（从 EvidenceItem 的 exec_status + supports_conclusion 推导）
- uncertainty_markers 的聚合逻辑

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### v1.1 设计合约（Agent-Evidence 边界）
- `.planning/milestones/v1.1-phases/07-agent-tool-boundary-and-implementation-blueprint/07-AGENT-EVIDENCE-PROJECTION-CONTRACT.md` — 定义 debate agent 接收的 projection 结构、summary card 概念、与 Evidence v2 的关系
- `.planning/milestones/v1.1-phases/07-agent-tool-boundary-and-implementation-blueprint/07-PROMPT-AND-TOOL-BOUNDARY-CONTRACT.md` — 定义 agent prompt 边界和工具隔离规则
- `.planning/milestones/v1.1-phases/07-agent-tool-boundary-and-implementation-blueprint/07-IMPLEMENTATION-BLUEPRINT.md` — 三切片渐进实现蓝图

### v1.1 设计合约（Evidence v2）
- `.planning/milestones/v1.1-phases/06-evidence-planning-and-dynamic-query-engine-contracts/06-EVIDENCE-V2-CONTRACT.md` — Evidence v2 结构定义（Phase 1 projection 需与之兼容）

### 现有代码（改造对象）
- `agents/debate_orchestrator.py` — 新增 project_evidence() 的目标文件
- `agents/base_agent.py` — judge() 和 debate_respond() 改造对象，format_evidence_bundle() 所在文件
- `evidence/evidence_model.py` — EvidenceBundle 和 EvidenceItem 定义

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `EvidenceBundle` / `EvidenceItem` (Pydantic models): project_evidence() 的输入数据源
- `format_evidence_bundle()`: 现有格式化逻辑，新 format_projection() 可参考其输出结构
- `AgentJudgment` (Pydantic model): agent 输出结构不变，保持兼容

### Established Patterns
- 所有数据模型用 Pydantic BaseModel（EvidenceItem、EvidenceBundle、AgentJudgment）
- Agent 基类定义 judge() / debate_respond() 抽象接口，子类只定义 SYSTEM_PROMPT 和 TEMPERATURE
- 格式化函数为模块级函数（如 format_evidence_bundle），不是类方法

### Integration Points
- `DebateOrchestrator._run_round_zero()` 和 `_run_debate_round()` 是调用 agent.judge()/debate_respond() 的入口
- `_build_stream_evidence()` 直接从 bundle.items 构造 SSE payload — 不受 projection 改造影响
- `build_debate_result()` 和 `persist_completed_session()` 消费 DebateRecord — 不受影响

</code_context>

<specifics>
## Specific Ideas

- EvidenceSummaryCard 的 question 字段应映射自 EvidenceItem.target（自然语言描述）
- finding 字段映射自 EvidenceItem.result_summary
- status 映射规则：exec_status="success" + supports_conclusion=True → "supports"；exec_status="success" + supports_conclusion=False → "contradicts"；exec_status="success" + supports_conclusion=None → "unresolved"；exec_status in ("no_data","failed","field_missing") → "missing"
- task_header 固定为 "灵活就业社保补贴资格认定"（当前系统仅处理该策略）
- policy_scope 固定为 "灵活就业社保补贴"（Phase 4 才引入 policy_id 参数化）

</specifics>

<deferred>
## Deferred Ideas

- Evidence v2 输入支持 — Phase 3 交付 Evidence v2 后再扩展
- policy_id 参数化 — Phase 4 接入编排时实现
- 多策略 task_header / policy_scope 动态化 — Phase 4

</deferred>

---

*Phase: 01-adapter-boundary*
*Context gathered: 2026-03-24*
