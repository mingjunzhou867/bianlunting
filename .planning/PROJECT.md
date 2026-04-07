# Multi-Agent Policy Review System

## Project State

`v1.0` and `v1.1` are archived as shipped milestones.

What shipped so far:

- `v1.0` delivered completed-session persistence, retrieval APIs, history browsing, and hardening around the save/read/render chain
- `v1.1` delivered the design contracts for database cognition, dictionary memory, evidence planning, dynamic query, Evidence v2, agent handoff, and staged implementation

## Core Value

The system should produce grounded policy-eligibility decisions by preparing the right evidence before agent debate, keeping database semantics explicit enough to reduce hallucination and support auditability.

## Current State

- The shipped runtime baseline is still the `v1.0` system: save completed debate sessions, retrieve them later, and render saved history in the frontend
- The shipped design baseline now also includes the full `v1.1` contract set for the next-generation architecture
- Future coding should start from the `v1.1` contracts instead of reopening the architecture, dictionary, evidence, or agent-boundary debates

## Current Milestone: v1.2 扩展系统实现——三切片迁移

**Goal:** 将 v1.1 设计合约落地为真实可运行代码，按三切片顺序渐进实现扩展架构，同时保留 v1.0 静态链路作为回归基准

**Target features:**
- Slice 1：适配器边界——Evidence Projection 适配器 + Agent Prompt 改造 + 回归测试
- Slice 2a：前置准备层——字典生成脚本、数据库语义包生成器、核查问题模板库、取证规划模块
- Slice 2b：取证执行层——text_to_sql 工具、auto_debug_sql 工具、Evidence v2 构建器
- Slice 3：接入编排——新管道接入 DebateOrchestrator、API 入参扩展 policy_id、新旧路径对比验证

## Design Baseline From v1.1

The archived `v1.1` milestone defined the expanded system as five coordinated layers:

1. **Pre-understanding and Evidence Preparation**  
   Owns schema cognition, code-dictionary resolution, task-scoped semantic packet construction, reusable check-question templates, and evidence-plan generation.  
   Does not own SQL execution, debate, or final rule validation.

2. **Evidence Execution and Evidence Construction**  
   Owns query-intent rewriting, runtime Text-to-SQL, execution feedback, debug/retry loop, and evidence artifact construction.  
   Does not own deciding policy outcome on its own or storing SQL as canonical knowledge.

3. **Multi-Agent Debate and Judgment**  
   Owns independent judgment, debate, voting, and dissent capture.  
   Does not own ad hoc raw-database exploration as its primary working mode.

4. **Post-rule Validation and Human Review**  
   Owns later rule-engine comparison, conflict labeling, and human-review escalation points.  
   Does not own replacing the debate layer during this design milestone.

5. **Continuous-learning and Evaluation Support**  
   Owns retention of useful repair and error artifacts, regression support, and future evaluation hooks.  
   Does not own full learning-loop automation in `v1.1`.

## Design Decisions Kept Active

- Formal task entrypoint: `person_id + policy_id + optional qualification scope`
- MCP is the formal tool framing for the expanded architecture
- `text_to_sql` is the first tool that must run end-to-end
- `get_dict`, `plan_evidence`, and `auto_debug_sql` remain target tools but are intentionally staged behind the first `text_to_sql` slice
- dynamic SQL is the target architecture
- the current static SQL-template path remains only as migration-period baseline and regression reference

## Constraints

- must build on the existing Python + FastAPI + SQLAlchemy + MySQL + Vue codebase
- must preserve the already shipped `v1.0` save/read/render capability while future architecture work begins
- must reduce hallucination risk by grounding query-generation behavior in schema and dictionary context
- must treat dynamic SQL as a runtime artifact, not a long-term blind memory dump
- must avoid turning future milestones into a vague "AI can do everything" rewrite

## Archived Milestones

- [v1.1 roadmap archive](/c:/Users/afrangry/PycharmProjects/bysj_t2s/.planning/milestones/v1.1-ROADMAP.md)
- [v1.1 requirements archive](/c:/Users/afrangry/PycharmProjects/bysj_t2s/.planning/milestones/v1.1-REQUIREMENTS.md)
- [v1.1 milestone audit](/c:/Users/afrangry/PycharmProjects/bysj_t2s/.planning/v1.1-MILESTONE-AUDIT.md)
- [v1.0 roadmap archive](/c:/Users/afrangry/PycharmProjects/bysj_t2s/.planning/milestones/v1.0-ROADMAP.md)
- [v1.0 requirements archive](/c:/Users/afrangry/PycharmProjects/bysj_t2s/.planning/milestones/v1.0-REQUIREMENTS.md)
- [v1.0 milestone audit](/c:/Users/afrangry/PycharmProjects/bysj_t2s/.planning/v1.0-MILESTONE-AUDIT.md)

<details>
<summary>Archived v1.1 Milestone Brief</summary>

`v1.1` was intentionally design-first. It defined:

- the five-layer expanded system model
- the database-cognition and dictionary-memory contracts
- the semantic packet and excerpt-first dictionary loading rules
- the evidence planning, dynamic query, and Evidence v2 contracts
- the debate-agent evidence projection, prompt boundary, and staged migration blueprint

It did not implement the new runtime path yet. That work is reserved for the next milestone.

</details>

---
*Last updated: 2026-03-24 after starting milestone v1.2*
