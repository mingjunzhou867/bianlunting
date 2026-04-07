# Phase 2: 前置理解与取证准备层（Slice 2a） - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

在不影响现有前端、且不改坏当前 `/api/debate` 与 `/api/debate_stream` 主链路的前提下，完成 cognition 第一层“前置理解与取证准备层”的接口冻结与最小骨架落地。Phase 2 只交付内部接口、契约和种子资产，不接入现有编排运行时。

本 Phase 的目标交付物集中在：

- `scripts/generate_dicts.py`
- `dicts/`
- `cognition/semantic_packet.py`
- `cognition/question_templates.py`
- `cognition/evidence_planner.py`

</domain>

<decisions>
## Implementation Decisions

### 接口暴露边界
- **D-01:** 本 Phase 仅提供 cognition 目录内的 Python 内部服务/模型接口，不新增前端可见 API，不新增必须接入现有页面的后端入口。
- **D-02:** 与现有运行时完全旁路隔离；`DebateOrchestrator`、`/api/debate`、`/api/debate_stream` 本 Phase 不接线、不改主路径行为。
- **D-03:** 如需人工验证，优先通过样例装配或脚本级调用完成，不把验证方式设计成对外运行时契约。

### 字典资产起步方式
- **D-04:** 字典层采用“种子字典 + 生成器骨架”策略，而不是本 Phase 就追求全库全量扫描。
- **D-05:** `dicts/ADC310.json` 作为首个规范参照继续保留；新增字典文件与生成器输出必须遵循 v1.1 Phase 5 已接受的 dictionary artifact contract。
- **D-06:** `scripts/generate_dicts.py` 本 Phase 的重点是冻结输入/输出接口、生成流程和文件契约，而不是承诺覆盖所有数据库码值域。
- **D-07:** 首批字典资产允许少量种子样例，但不得退化为纯手工维护方案；后续全量生成能力留给后续 phase 扩展。

### Semantic Packet 形态
- **D-08:** `cognition/semantic_packet.py` 先实现强类型骨架，固定五段结构：`task`、`fields`、`relations`、`time_semantics`、`dict_excerpt`。
- **D-09:** 该结构服务于正式任务入口：`person_id + policy_id + optional qualification scope`。
- **D-10:** Packet 内容以“精简但结构完整”为原则，先保证下游程序可消费，不做富文本化或自由 prose 化。
- **D-11:** `dict_excerpt` 默认采用 excerpt-first 原则，只保留任务相关的字典摘要，不默认注入整本字典。

### 问题模板组织方式
- **D-12:** `cognition/question_templates.py` 按“问题类型”组织模板，而不是按具体政策条款分目录组织。
- **D-13:** 本 Phase 至少预留与 v1.1 Phase 6 一致的模板分类能力，覆盖 BASIC / EXCL / INFER / CALC 这类问题族。
- **D-14:** 模板是可复用的资格核验问题模式，不直接绑定某条 SQL，也不绑定现有静态规则执行器。

### Evidence Planner 输出粒度
- **D-15:** `cognition/evidence_planner.py` 采用“一问一项”的计划输出粒度，每个资格问题对应一个 evidence-plan item。
- **D-16:** 计划链路必须保持显式可追踪：`qualification item -> question template -> evidence plan item`。
- **D-17:** plan item 是语义规划对象，不是 SQL 列表；其中 `evidence_targets`、`relevant_fields`、`time semantics`、`missing strategy` 需要有明确位置。

### 与现有代码的兼容方式
- **D-18:** 当前 `text2sql/sql_templates.py` 与 `text2sql/evidence_collector.py` 继续作为现网静态链路存在，本 Phase 不替换它们。
- **D-19:** cognition 第一层交付的是可被未来 Slice 2b/3 消费的准备层接口，因此允许先有数据模型、构造器、注册表、样例装配，而暂不接入动态查询执行。

### Claude's Discretion
- `generate_dicts.py` 的具体命令行参数形式与最小输入源组织方式
- Semantic Packet 各 section 的精确字段命名与 dataclass/Pydantic 选型
- Question template 注册表的代码组织细节
- Evidence planner 中 priority、missing strategy、conflict strategy 的枚举命名

</decisions>

<canonical_refs>
## Canonical References

### 业务目标来源
- `项目总体计划书.md` — `5.2 目标升级架构（业务设计视角）` 中“第一层：前置理解与取证准备层”

### v1.1 已冻结的前置契约
- `.planning/milestones/v1.1-phases/05-database-cognition-and-dictionary-memory/05-DICT-CONTRACT.md`
- `.planning/milestones/v1.1-phases/05-database-cognition-and-dictionary-memory/05-SEMANTIC-PACKET-CONTRACT.md`
- `.planning/milestones/v1.1-phases/06-evidence-planning-and-dynamic-query-engine-contracts/06-QUESTION-AND-PLAN-CONTRACT.md`
- `.planning/milestones/v1.1-phases/06-evidence-planning-and-dynamic-query-engine-contracts/06-DYNAMIC-QUERY-CONTRACT.md`

### 当前 milestone 上下文
- `.planning/ROADMAP.md` — v1.2 当前 Phase 2 边界与交付物
- `.planning/phases/01-adapter-boundary/01-CONTEXT.md` — 已完成 Slice 1 的 agent 边界约束

</canonical_refs>

<specifics>
## Specific Ideas

- 当前 phase 聚焦“先理解任务与数据库，再决定该查什么”，因此交付重点是 preparation interfaces，而不是查询执行。
- 代码产出应尽量集中在 `cognition/`，辅以必要的 `dicts/` 和 `scripts/`。
- 不影响现有前端是硬约束；即使后端新增内部对象，也不应要求前端做任何跟随改动。
- 现阶段优先保证后续可接线性，而不是追求数据库认知资产的一次性做满。

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `dicts/ADC310.json`: 已存在的字典样例，可作为 dictionary artifact contract 的基准参照。
- `text2sql/sql_templates.py`: 现有静态问题到 SQL 模板的前身资产，可用于反向提炼 question template 的来源。
- `text2sql/evidence_collector.py`: 当前静态取证链路入口，本 Phase 只参考其任务语义，不直接改造其运行路径。
- `evidence/evidence_model.py`: 现有统一证据对象定义，后续 Slice 2b 需要与 cognition 输出衔接。

### Established Patterns
- 项目核心数据对象目前多采用 Pydantic BaseModel；cognition 新接口可延续这一模式以降低后续接线成本。
- 现有主链路已经在 Phase 1 固化了 agent 消费边界，因此本 Phase 只需准备上游 cognition 契约，不应回头冲击 agent 层。
- 当前仓库内尚无成型的 `cognition/` 与 `scripts/` 结构，这意味着本 Phase 可以以“新模块骨架”方式整洁落地。

### Integration Points
- 未来 Slice 2b 会消费 `question_templates` 与 `evidence_planner`，把规划结果交给动态 Text-to-SQL / Auto Debugger。
- 未来 Slice 3 才会考虑将 preparation/execution outputs 接入 `DebateOrchestrator` 的动态检索开关。
- 本 Phase 自身的成功标准不是运行时替换，而是下游 planner/implementer 可以在不再追问用户的情况下继续拆计划和落代码。

</code_context>

<deferred>
## Deferred Ideas

- 全库码值域的全量扫描与稳定生成
- cognition 内部接口的对外 API 化或前端可见化
- 动态 Text-to-SQL 执行、SQL 自动修复与 Evidence v2 组装
- 基于 `policy_id` 的运行时接线与 `DebateOrchestrator` 集成
- 任何会改变当前 `/api/debate`、`/api/debate_stream` 行为的改造

</deferred>

---

*Phase: 02-cognition-prep*
*Context gathered: 2026-03-24*
