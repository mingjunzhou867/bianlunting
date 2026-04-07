# Milestone v1.2 Requirements：扩展系统实现——三切片迁移

> 基于 v1.1 设计合约，将扩展架构落地为真实可运行代码。
> v1.0 静态链路全程保留为 fallback 和回归基准，不删除。

---

## Slice 1：适配器边界（ADAPTER）

> 目标：稳固下游接口，让后续取证管道替换对 debate agent 透明。

- [ ] **ADAPTER-01**：在 `debate_orchestrator.py` 中实现 `project_evidence()` 函数，将 `EvidenceBundle` 转换为 summary-first 的 agent-facing evidence projection（含 task header、evidence summaries、uncertainty markers、traceable references）
- [ ] **ADAPTER-02**：修改 `base_agent.py` 的 `judge()` 和 `debate_respond()` 方法，消费 projection 格式而非裸 `EvidenceBundle`，prompt 内容更紧凑
- [ ] **ADAPTER-03**：在现有测试基础上验证 Slice 1 不改变辩论输出行为（静态链路作为回归基准，测试对比前后结论一致性）

---

## Slice 2a：前置理解与取证准备层（PREP）

> 目标：让系统在取证前先"理解数据库"，生成任务裁剪的语义上下文和取证计划。

- [ ] **PREP-01**：编写 `scripts/generate_dicts.py`，扫描数据库枚举字段自动生成 ADC310 增强格式字典文件（含 `source_refs`、`aliases`、`notes` 扩展字段），存入 `dicts/` 目录
- [ ] **PREP-02**：实现数据库语义包生成器（`cognition/semantic_packet.py`），按 `person_id + policy_id` 输出五区块任务裁剪语义包（task / fields / relations / time_semantics / dict_excerpt），摘录优先，不全量灌输
- [ ] **PREP-03**：实现核查问题模板库（`cognition/question_templates.py`），以 qualification-item-first 组织可复用核查模板，覆盖 BASIC / EXCL / INFER / CALC 规则类型
- [ ] **PREP-04**：实现取证规划模块（`cognition/evidence_planner.py`），输入 `person_id + policy_id`，输出问题驱动的取证计划（含关键证据项、涉及表字段、时间范围、查询优先级、证据缺失判定条件）

---

## Slice 2b：取证执行与证据构建层（EXEC）

> 目标：把取证计划真正执行出来，构建可审计的标准化证据对象。

- [ ] **EXEC-01**：实现 `text_to_sql` 工具（`retrieval/text_to_sql.py`），接收 `query_intent` 结构化对象，运行时生成 SQL 并执行，返回含执行状态的结构化结果
- [ ] **EXEC-02**：实现 `auto_debug_sql` 工具（`retrieval/auto_debug_sql.py`），基于执行错误信息有限次自修正（≤3次），明确止损条件（超限或语义不确定时输出 stopped 状态而非无限重试）
- [ ] **EXEC-03**：实现 Evidence v2 构建器（`evidence/evidence_v2.py`），生成带溯源（query_intent ref）、dict refs、修复历史、执行状态的正式证据对象，支持 summary-first 下游消费

---

## Slice 3：接入编排（ORCH）

> 目标：将新取证管道接入主流程，新旧路径可并存对照，验证功能完整。

- [ ] **ORCH-01**：将新取证管道接入 `DebateOrchestrator`，保留静态路径作为 fallback，支持通过配置项（`use_dynamic_retrieval: bool`）切换新旧路径
- [ ] **ORCH-02**：`POST /api/debate` 和 `POST /api/debate_stream` 入参增加可选 `policy_id` 字段，编排器据此加载对应资格策略（缺省时使用默认灵活就业补贴策略）
- [ ] **ORCH-03**：运行同一 Persona 分别经过新旧两条路径，对比证据输出和最终辩论结论差异，记录对比结果为验证报告

---

## 范围外（本里程碑不做）

- 规则推理校验层（`rules/rule_engine.py`）— 推迟到 v1.3
- 持久化全链路 save→read 回归测试（schema drift 检测）— 推迟到 v1.3
- 批量评测实验（50 案例、消融实验）— 推迟到 v1.4
- MCP 传输协议（stdio/SSE transport）— 推迟，本里程碑用 Python 函数边界实现相同语义
- 前端界面改造 — 暂不动，新层通过现有 SSE 流透传

---

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| ADAPTER-01 | Phase 1 | pending |
| ADAPTER-02 | Phase 1 | pending |
| ADAPTER-03 | Phase 1 | pending |
| PREP-01 | Phase 2 | pending |
| PREP-02 | Phase 2 | pending |
| PREP-03 | Phase 2 | pending |
| PREP-04 | Phase 2 | pending |
| EXEC-01 | Phase 3 | pending |
| EXEC-02 | Phase 3 | pending |
| EXEC-03 | Phase 3 | pending |
| ORCH-01 | Phase 4 | pending |
| ORCH-02 | Phase 4 | pending |
| ORCH-03 | Phase 4 | pending |
