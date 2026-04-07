# Phase 4: System Boundary Alignment - Research

**Researched:** 2026-03-24  
**Status:** Ready for planning

## Goal

Identify the lowest-risk way to turn the user’s expanded architecture idea into a bounded design phase instead of an implementation blur.

## Findings

### 1. The current repo already has one stable reference chain, so Phase 4 should anchor itself to that baseline instead of redesigning from scratch

- [sql_templates.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/text2sql/sql_templates.py) is the current evidence-query baseline
- [evidence_collector.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/text2sql/evidence_collector.py) is the current execution path from rule/query choice to evidence object
- [evidence_model.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/evidence/evidence_model.py) is the current evidence contract that downstream agents already consume
- [base_agent.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/agents/base_agent.py) and the existing debate stack prove the repo already has a meaningful “evidence in, judgment out” boundary

Implication:

- Phase 4 should define how the new architecture grows from this baseline
- it should not pretend the system is greenfield

### 2. The user’s expansion is mostly about pre-debate preparation, not about replacing debate itself

The strongest additions are:

- database cognition
- dictionary memory
- reusable check-question templates
- evidence planning
- dynamic Text-to-SQL with repair

The debate layer remains important, but it is no longer the only “smart” layer.

Implication:

- Phase 4 should freeze a layered vocabulary that makes the preparation layers first-class

### 3. The user has now explicitly locked two high-impact architecture choices

Locked choices from discuss-phase:

- MCP is the formal tool framing
- `text_to_sql` is the first tool that needs to run end-to-end
- dynamic SQL is the target path
- current static templates remain only as migration-period baseline

Implication:

- Phase 4 planning should stop treating MCP as optional
- it should also stop describing static templates as a long-term coequal path

### 4. The biggest current risk is ambiguity, not missing implementation

The project can easily drift if Phase 4 does not explicitly define:

- the formal task input
- what the database-cognition layer emits
- what is always in prompt context vs loaded on demand
- what belongs in future phases rather than Phase 4

Implication:

- the best Phase 4 plans are documentation-heavy and decision-focused
- verification should focus on requirement coverage and deferred-scope clarity, not runtime tests

## Recommendations

### Recommended plan split

- Plan `04-01`: write the canonical system-definition artifacts for the expanded five-layer model, task entrypoint, vocabulary, and module boundary matrix
- Plan `04-02`: write the tool and migration-position artifacts for MCP-first rollout, `text_to_sql` first-run scope, static-template migration role, and explicit deferred list

### Recommended verification shape

- verify every Phase 4 requirement is tied to a concrete written artifact
- verify no plan accidentally commits to implementation-level details that belong in Phase 5-7
- verify the dynamic/static SQL language stays aligned with the user’s latest decisions

## Risks To Watch

- Phase 4 may accidentally start designing Evidence v2 fields in too much detail before Phase 6
- MCP may sprawl from “tool framing” into premature transport and deployment discussions
- the task-trimmed semantic packet may be described too vaguely unless the artifact names and boundary rules are explicit

## Planning Implications

- Phase 4 plans should modify only planning artifacts plus `todolist.md` if a locked decision needs to be made legible to future readers
- plans should end with planning/state sync so downstream phases see Phase 4 as complete and do not reopen settled questions
