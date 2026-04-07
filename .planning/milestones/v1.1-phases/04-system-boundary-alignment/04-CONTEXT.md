# Phase 4: System Boundary Alignment - Context

**Phase:** 4  
**Milestone:** v1.1 Dynamic Evidence Planning Design  
**Status:** Context gathered

## Goal

Freeze the core language and boundary decisions for the expanded system before later phases define detailed contracts.

This phase is about:

- what the expanded system is
- what each major layer is responsible for
- what the formal task entrypoint is
- what counts as database cognition
- how MCP is positioned in the architecture
- how the future dynamic SQL path relates to the current static template path

This phase is not about:

- implementation details
- protocol transport details
- field-by-field final schema design for Evidence v2
- final prompt wording
- replacing current production code now

## Existing Baseline

The shipped `v1.0` system already provides:

- static SQL-template driven evidence collection
- evidence objects passed into debate agents
- multi-agent debate orchestration
- persistence and retrieval of completed debate sessions
- a frontend that can replay saved sessions

Relevant baseline assets:

- [sql_templates.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/text2sql/sql_templates.py) — current static SQL baseline
- [evidence_collector.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/text2sql/evidence_collector.py) — current evidence execution path
- [evidence_model.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/evidence/evidence_model.py) — current evidence-object shape
- [base_agent.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/agents/base_agent.py) — current downstream agent consumer pattern
- [ADC310.json](/c:/Users/afrangry/PycharmProjects/bysj_t2s/dicts/ADC310.json) — example code-dictionary artifact

## Decisions Locked In This Discussion

### 1. This milestone remains design-only

- no production code changes are required
- phase outputs are definitions, boundaries, and guidance for later phases

### 2. Formal task entrypoint

The expanded system should treat the pre-debate preparation input as:

- `person_id`
- `policy_id`
- optional qualification scope

This means the system should no longer be described as receiving only a bare person identifier.

### 3. Database cognition output shape

The database-cognition layer should not dump the whole schema into downstream prompts.

Its first-class output is a **task-trimmed semantic packet** containing only the task-relevant slice of:

- field semantics
- code-value dictionary fragments
- relation hints
- temporal semantics

It should not require:

- full raw DDL injection by default
- full-database graph injection by default
- template SQL injection by default

### 4. MCP is the chosen tool framing

The expanded architecture should describe tool interaction using MCP, not a transport-agnostic placeholder.

However, tool rollout is phased:

- `text_to_sql` is the first MCP tool that must run end-to-end
- `get_dict`, `plan_evidence`, and `auto_debug_sql` remain part of the target architecture
- those additional tools are expected to be introduced later rather than all at once

### 5. Dynamic SQL is the target architecture

The target architecture should describe dynamic SQL generation as the primary path.

The current static SQL-template system is still important, but only as:

- migration-period baseline
- regression comparison anchor

It is not the intended long-term formal architecture.

## Boundary Matrix

| Layer / Module | Owns | Input | Output | Deliberately Does Not Own |
|----------------|------|-------|--------|----------------------------|
| Schema cognition | schema metadata, field meaning, alias knowledge, code-dictionary linkage, temporal semantics | database schema + dictionary artifacts + task scope | task-relevant semantic packet | query execution, policy decision |
| Question template layer | reusable核查问题模板 and policy-to-check mapping | policy clauses, qualification items, conflict patterns | reusable check templates | SQL generation, final evidence judgment |
| Evidence planning | task-specific evidence decomposition and priority | `person_id + policy_id + optional qualification scope` + semantic packet + check templates | evidence plan | direct debate, final decision |
| Prompt rewriter | restructuring one evidence-plan item into query intent | one evidence-plan item + semantic packet | structured query intent | database execution, final policy logic |
| `text_to_sql` MCP | runtime query generation and execution-facing SQL output | structured query intent + task-scoped semantics | candidate SQL / execution-ready SQL | long-term memory, final decision |
| `auto_debug_sql` MCP | SQL error repair and retry suggestion | SQL + error feedback + task-scoped semantics | patched SQL / stop signal | planning new evidence items |
| Evidence artifact builder | auditable evidence construction | execution result + query lineage + task context | evidence artifact | debate reasoning |
| Debate agents | judgment, debate, voting, dissent | evidence artifacts + selected task context | judgments and debate output | raw schema exploration as primary mode |
| Rule validation layer | later conflict check against hard rules | evidence artifacts + debate result | validation status / escalation marker | replacing debate itself |
| Learning/eval support | retention of reusable errors, fixes, and regression artifacts | execution/debate history | reusable support artifacts | immediate runtime orchestration in Phase 4 |

## Prompt-Context Boundary Rules

### Always-present context

- the formal task identifiers
- the current qualification scope if one exists
- the minimum task-trimmed semantic packet needed for the current unit of work

### On-demand context

- relevant dictionary fragments
- relation hints outside the first semantic slice
- reusable question templates
- prior repair examples
- regression/reference baselines when needed for comparison

### Never blindly injected by default

- full raw DDL for the entire database
- all dictionary files
- all historical SQL templates
- all prior debate history
- all future-phase schema sketches

## Boundary Implications For Later Phases

### For Phase 5

Phase 5 should define:

- what metadata is needed to build the semantic packet
- how dictionary artifacts are structured and indexed
- how task trimming decides what dictionary content to surface

### For Phase 6

Phase 6 should define:

- what `plan_evidence` must output
- what `text_to_sql` MCP takes as input and returns
- where `auto_debug_sql` begins and ends
- how Evidence v2 records query intent, execution trace, and repair history

### For Phase 7

Phase 7 should define:

- what debate agents receive from MCP-backed preparation and query layers
- which contexts are always loaded vs on-demand
- how the future MCP tool family is staged beyond the first runnable `text_to_sql`

## Deferred Questions

These are deliberately not locked in Phase 4:

- final transport choice for each MCP tool
- exact JSON schema of the semantic packet
- exact JSON schema of question templates and evidence plans
- exact Evidence v2 field list
- exact prompt strategy for each downstream agent
- exact MCP transport/runtime packaging for each future tool
- exact stop/retry policy values for `auto_debug_sql`

## Discussion Summary

Phase 4 is now grounded by five concrete choices:

1. design-only milestone
2. `person_id + policy_id + optional qualification scope` as formal task input
3. task-trimmed semantic packet as database-cognition output
4. MCP as the formal tool framing, with `text_to_sql` first
5. dynamic SQL as target path, static templates as migration-period baseline only

This phase also established:

6. a boundary matrix for the major new layers/modules
7. prompt-context rules for always-present, on-demand, and never-blindly-injected context
