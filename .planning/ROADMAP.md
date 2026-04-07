# Roadmap: Multi-Agent Policy Review System

## Active Milestone

### v1.2 — 扩展系统实现——三切片迁移

> **目标**：将 v1.1 设计合约落地为真实可运行代码，按三切片顺序渐进实现扩展架构，同时保留 v1.0 静态链路作为回归基准。
>
> **编号说明**：v1.0 / v1.1 已归档，本里程碑 Phase 编号从 Phase 1 重新起始（--reset-phase-numbers 模式）。

---

### 关键约束（全程有效）

| 约束 | 说明 |
|------|------|
| v1.0 静态链路保留 | 任何 Phase 均不得删除现有静态 SQL 路径代码，全程作为 fallback 和回归基准 |
| Debate agent 工具隔离 | Debate agent 不直接调用 `text_to_sql` / `get_dict` / `auto_debug_sql`；这些工具仅由取证层调用 |
| MCP 传输推迟 | stdio/SSE transport 不在本里程碑，使用 Python 函数边界实现相同语义 |
| 规则引擎 / 批量评测推迟 | `rule_engine.py`、消融实验、50 案例批量评测均不在本里程碑 |

---

### Phase 1 — 适配器边界（Slice 1）

**对应需求**：ADAPTER-01, ADAPTER-02, ADAPTER-03

**目标**：在不触动取证逻辑的前提下，稳固 Debate agent 的下游接口，使后续取证管道替换对 agent 完全透明。

#### 交付物

| 文件 | 内容 |
|------|------|
| `debate_orchestrator.py` | 新增 `project_evidence()` 函数 |
| `base_agent.py` | `judge()` 和 `debate_respond()` 改为消费 projection 格式 |
| `tests/test_slice1_regression.py` | Slice 1 回归测试套件 |

#### 成功验收标准

1. **接口隔离可验证**：`project_evidence()` 可独立调用，输入任意 `EvidenceBundle`，输出包含 task header、evidence summaries、uncertainty markers、traceable references 的标准 projection 对象，调用链中不出现 `text_to_sql` / `get_dict` / `auto_debug_sql`。
2. **Prompt 紧凑性可测量**：改造后 `judge()` 和 `debate_respond()` 接收的 prompt token 数不超过改造前，且不丢失任何证据摘要字段。
3. **回归一致性通过**：同一 Persona 输入经新旧两种 prompt 构造路径，Debate agent 最终裁定结论（eligible / not-eligible / uncertain）一致，测试结果写入断言日志。
4. **零删除约束满足**：`git diff` 中不出现现有静态 SQL 路径文件的删除记录，所有新增逻辑为纯增量。

---

### Phase 2 — 前置理解与取证准备层（Slice 2a）

**对应需求**：PREP-01, PREP-02, PREP-03, PREP-04

**目标**：让系统在取证执行前先"理解数据库"，生成任务裁剪的语义上下文和取证计划，为 Slice 2b 提供结构化输入。

#### 交付物

| 文件 | 内容 |
|------|------|
| `scripts/generate_dicts.py` | 枚举字段扫描脚本，产出 ADC310 增强格式字典 |
| `dicts/` | 脚本输出目录，含各枚举字段字典文件 |
| `cognition/semantic_packet.py` | 任务裁剪语义包生成器 |
| `cognition/question_templates.py` | 核查问题模板库 |
| `cognition/evidence_planner.py` | 取证规划模块 |

#### 成功验收标准

1. **字典生成可重复执行**：`generate_dicts.py` 在空 `dicts/` 目录下幂等运行，输出文件包含 `source_refs`、`aliases`、`notes` 扩展字段，覆盖全部枚举列。
2. **语义包五区块完整**：`SemanticPacket` 输出对象必须包含 task / fields / relations / time_semantics / dict_excerpt 五个区块，dict_excerpt 为摘录（非全量灌输），输入不同 `policy_id` 时输出内容可区分。
3. **模板库规则类型覆盖**：`QuestionTemplates` 返回的模板集合覆盖 BASIC / EXCL / INFER / CALC 四类规则类型，每类至少一条可实例化模板。
4. **取证计划结构可验证**：`EvidencePlanner` 对任意合法 `(person_id, policy_id)` 输出含关键证据项、涉及表字段、时间范围、查询优先级、证据缺失判定条件的计划对象，结构通过 schema 断言。

---

### Phase 3 — 取证执行与证据构建层（Slice 2b）

**对应需求**：EXEC-01, EXEC-02, EXEC-03

**目标**：将 Phase 2 产出的取证计划真正执行出来，构建可审计的标准化 Evidence v2 对象，供 Phase 1 适配器消费。

#### 交付物

| 文件 | 内容 |
|------|------|
| `retrieval/text_to_sql.py` | 运行时 Text-to-SQL 工具，接收 `query_intent` |
| `retrieval/auto_debug_sql.py` | SQL 自修正工具，≤3 次止损 |
| `evidence/evidence_v2.py` | Evidence v2 构建器，生成带溯源的证据对象 |

#### 成功验收标准

1. **text_to_sql 端到端可执行**：给定合法 `query_intent` 结构化对象，`text_to_sql` 能生成可执行 SQL 并返回含 `status`（success / error）、`rows`、`sql_text` 的结构化结果；该工具不由 Debate agent 直接调用。
2. **auto_debug_sql 止损可观察**：注入语法错误 SQL 后，`auto_debug_sql` 最多自修正 3 次，超限时返回 `status: stopped` 而非抛出异常或无限重试；修复历史记录在返回对象中。
3. **Evidence v2 溯源完整**：`EvidenceV2` 对象包含 `query_intent_ref`、`dict_refs`、`repair_history`、`exec_status` 字段，能被 `project_evidence()` 正常消费并生成 summary-first projection。

---

### Phase 4 — 接入编排（Slice 3）

**对应需求**：ORCH-01, ORCH-02, ORCH-03

**目标**：将新取证管道接入主流程，新旧路径并存可切换，完成功能完整性验证并输出对比报告。

#### 交付物

| 文件 | 内容 |
|------|------|
| `debate_orchestrator.py` | 接入新管道，`use_dynamic_retrieval` 配置开关 |
| `api/debate_routes.py`（或同等路由文件） | `POST /api/debate` 和 `POST /api/debate_stream` 增加 `policy_id` 可选字段 |
| `reports/v1.2-path-comparison.md` | 新旧路径对比验证报告 |

#### 成功验收标准

1. **配置开关生效**：将 `use_dynamic_retrieval` 设为 `false` 时，`DebateOrchestrator` 完全走 v1.0 静态路径，静态路径代码无任何删减；设为 `true` 时，走新取证管道，两种模式均能完成完整辩论会话。
2. **policy_id 参数透传**：`POST /api/debate` 请求体中传入 `policy_id` 时，编排器加载对应资格策略；不传时默认加载灵活就业补贴策略，两种情况均通过接口测试断言。
3. **对比报告可读可存档**：同一 Persona 经新旧两条路径运行后，对比报告包含证据字段覆盖率、最终裁定结论、关键 diff 三个维度，文件持久化写入 `reports/` 目录。
4. **全链路无回归**：v1.0 现有的 save / read / render 功能在 Phase 4 完成后仍能通过原有测试，不因编排器修改引入回归。

---

### 需求覆盖总表

| Phase | Slice | REQ-IDs | 覆盖数 |
|-------|-------|---------|--------|
| Phase 1 | Slice 1 — 适配器边界 | ADAPTER-01, ADAPTER-02, ADAPTER-03 | 3 |
| Phase 2 | Slice 2a — 前置准备层 | PREP-01, PREP-02, PREP-03, PREP-04 | 4 |
| Phase 3 | Slice 2b — 取证执行层 | EXEC-01, EXEC-02, EXEC-03 | 3 |
| Phase 4 | Slice 3 — 接入编排 | ORCH-01, ORCH-02, ORCH-03 | 3 |
| **合计** | | | **13 / 13 (100%)** |

---

### 范围外（本里程碑不做）

- `rules/rule_engine.py` 规则推理校验层 → 推迟至 v1.3
- 持久化全链路 save→read 回归测试（schema drift 检测）→ 推迟至 v1.3
- 批量评测实验（50 案例、消融实验）→ 推迟至 v1.4
- MCP 传输协议（stdio / SSE transport）→ 推迟，本里程碑以 Python 函数边界实现相同语义
- 前端界面改造 → 暂不动，新层通过现有 SSE 流透传

---

## Archived Milestones

- [v1.1: Dynamic Evidence Planning Design](/c:/Users/afrangry/PycharmProjects/bysj_t2s/.planning/milestones/v1.1-ROADMAP.md) - shipped 2026-03-24, 4 phases, 10 plans
- [v1.0: Debate Persistence and Retrieval](/c:/Users/afrangry/PycharmProjects/bysj_t2s/.planning/milestones/v1.0-ROADMAP.md) - shipped 2026-03-24, 4 phases, 9 plans

---

*Created: 2026-03-24 | Milestone: v1.2*
