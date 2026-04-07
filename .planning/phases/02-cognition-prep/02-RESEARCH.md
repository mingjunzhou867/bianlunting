# Phase 2: 前置理解与取证准备层（Slice 2a） - Research

**Researched:** 2026-03-24
**Status:** Ready for planning

## Goal

找到最稳妥的 Phase 2 落地方式：先把 cognition 第一层做成可执行的内部接口和种子资产，同时保持与现有前端、`/api/debate`、`/api/debate_stream` 主链路完全隔离。

## Findings

### 1. 当前代码库已经有足够的“语义种子”，但还没有 cognition 模块骨架

现有资产里已经有三类可复用来源：

- `dicts/ADC310.json` 提供了字典工件的可读样式锚点
- `text2sql/sql_templates.py` 隐含了静态时代的问题分类与核验意图
- `text2sql/evidence_collector.py` 与 `evidence/evidence_model.py` 暗含了后续 planner / execution 需要衔接的证据目标语义

但仓库中还没有正式的 `cognition/` 模块实现，也没有 `scripts/generate_dicts.py`。

Implication:

- Phase 2 应以“新模块骨架 + 明确接口”的方式推进
- 不要急着把运行时接到主链路上

### 2. 最安全的实现方式是“强类型接口 + 可注入数据提供者”，而不是直接做数据库耦合实现

用户已经锁定：

- 先实现接口
- 不影响现有前端
- 不改坏 `/api/debate` 和 `/api/debate_stream`

这意味着当前 phase 更适合交付：

- 明确的 Pydantic 数据模型
- builder / planner 接口
- 注册表与样例装配
- 针对接口行为的单元测试

而不适合交付：

- 直接读库的正式运行时逻辑
- 对外 API
- 编排接线

Implication:

- 所有核心模块都应该支持注入 provider / registry / resolver
- 默认实现可以是样例级或骨架级，但输出契约必须稳定

### 3. 字典生成器的核心不是“扫完整个库”，而是先冻结工件契约和生成流程

Phase 5 已经冻结了 dictionary artifact contract：

- 保持接近 `ADC310.json`
- 文件名按 semantic dictionary ID
- 允许 `source_refs`、`aliases`、`notes`

因此本 phase 中 `scripts/generate_dicts.py` 的价值主要在于：

- 定义输入源组织方式
- 定义生成流程
- 定义如何写入 `dicts/`
- 提供至少一个种子级可验证输出

Implication:

- `generate_dicts.py` 应支持 dry-run / manifest / write 之类的最小接口
- 不要承诺在本 phase 内完成全量库扫描

### 4. Semantic Packet 和 Question Templates 是并行准备层，Evidence Planner 是收口层

从 v1.1 的已冻结契约可以得到一个清晰依赖链：

- `semantic_packet` 负责任务裁剪后的数据库理解
- `question_templates` 负责资格核验问题模式
- `evidence_planner` 负责把“任务上下文 + 问题模板”变成 question-driven plan items

Implication:

- 计划拆分应让 `semantic_packet` 与 `question_templates` 分别成件
- `evidence_planner` 放在最后收口，避免同时承担上游建模和下游规划两种变化

### 5. 本 phase 的主要风险是过早滑向 Slice 2b 或 Slice 3

最常见的范围漂移方向有：

- 让 `semantic_packet` 直接变成动态查询输入
- 让 `question_templates` 重新退化成静态 SQL 模板
- 让 `evidence_planner` 直接生成 SQL 或执行查询
- 为了“方便验证”去修改现有 API 或 orchestrator

Implication:

- 所有计划都需要把“内部接口 only / runtime bypass / no frontend impact”写成硬约束

## Recommendations

### Recommended plan split

- Plan `02-01`: `generate_dicts.py` 与种子字典工件
- Plan `02-02`: `semantic_packet.py` 的强类型模型与 builder 接口
- Plan `02-03`: `question_templates.py` 的 qualification-aware 模板注册表
- Plan `02-04`: `evidence_planner.py` 的 question-driven plan 输出

### Recommended dependency shape

- `02-01` 先建立基础目录和字典资产约定
- `02-02` 与 `02-03` 依赖 `02-01`，可以并行执行
- `02-04` 依赖 `02-02` 和 `02-03`

### Recommended verification shape

- 以 importable module + typed model assertions + deterministic unit tests 为主
- 明确验证“不触发现有 debate 主链”和“不需要前端改动”
- planner 的验证重点放在 traceability 与 plan item 粒度，而不是查询正确性

## Risks To Watch

- 把字典生成器做成一次性脚本，没有稳定输出契约
- 让 Semantic Packet 退化成自由文本说明
- 让 Question Template 丢掉 qualification item / question type 的双重语义
- 让 Evidence Planner 输出按表分组，而不是一问一项
- 为了联调而提前侵入 `DebateOrchestrator` 或 API 路由
