# Phase 6: Evidence Planning and Dynamic Query Engine Contracts - Context

**Phase:** 6  
**Milestone:** v1.1 Dynamic Evidence Planning Design  
**Status:** Executed

## Goal

Define the contracts that turn a task-trimmed semantic packet into:

- reusable check-question templates
- question-driven evidence plans
- structured query intents for dynamic Text-to-SQL
- bounded repair behavior
- auditable Evidence v2 artifacts

This phase is where the design stops being only about "understanding the database" and becomes about "planning and executing evidence retrieval in a controlled way."

## Prior Decisions Carried In

From Phase 4:

- the formal task entrypoint is `person_id + policy_id + optional qualification scope`
- MCP is the formal tool framing
- `text_to_sql` is the first tool that must run end-to-end
- dynamic SQL is the target architecture
- static SQL templates remain only as migration-period baseline and regression reference

From Phase 5:

- the database-cognition layer outputs one task-level semantic packet
- the packet is sectioned around `task`, `fields`, `relations`, `time_semantics`, and `dict_excerpt`
- dictionary artifacts are long-lived semantic assets
- dictionary content enters downstream work excerpt-first by default
- time semantics are first-class context

## Reusable Existing Assets

Phase 6 is not designing in a vacuum.

The current codebase already contains a static predecessor to several Phase 6 concepts:

- [sql_templates.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/text2sql/sql_templates.py)
  - existing static `RULE_REGISTRY`
  - implicit question catalog hidden behind `rule_id`
  - category split such as qualification, calculation, and proactive
- [evidence_collector.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/text2sql/evidence_collector.py)
  - current `rule_id -> SQL -> execute -> EvidenceItem` chain
  - early auto-verdict behavior
  - current bundle assembly model
- [evidence_model.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/evidence/evidence_model.py)
  - `EvidenceItem` and `EvidenceBundle` as the current evidence prototype
- [test_evidence_collector.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/tests/test_evidence_collector.py)
  - current regression anchor for what the static pipeline is capable of expressing

Implication:

- Phase 6 should upgrade and reframe these ideas
- it should not pretend there is no existing evidence pipeline
- it should avoid locking new contracts that cannot explain how current assets map forward

## Gray Areas Resolved In Discussion

### 1. Check-question templates are qualification-item-first

The project chooses to define reusable check-question templates with qualification items as the primary anchor.

That means the conceptual order is:

1. qualification item
2. linked policy clause references
3. linked conflict or ambiguity patterns
4. downstream evidence needs

Why this was chosen:

- the system's core job is still to judge policy eligibility
- evidence planning is easier if each template answers "what must be verified for this qualification item?"
- policy clauses and conflict patterns still matter, but they become linked metadata rather than the primary organizing key

### 2. Evidence plan items are question-driven

The smallest planning unit is one verification question, not one raw table access.

That means a plan item is centered on:

- one question to answer

and then carries:

- the evidence targets needed to answer it
- the relevant fields
- the time window or time semantics
- the priority
- the missing-evidence handling expectation

Implication:

- one question may map to multiple evidence targets
- one policy item may produce multiple plan items
- later query generation should trace back to question identity rather than only table identity

### 3. Dynamic query uses bounded retries with explicit stop conditions

The project chooses a bounded, auditable dynamic-query chain:

1. `evidence plan item`
2. `query_intent`
3. `text_to_sql`
4. execution
5. optional `auto_debug_sql`
6. explicit success or stop outcome

The chain should not repair forever until something runs.

The baseline stance is:

- one initial SQL generation attempt
- a small bounded number of repair attempts after execution or validation failure
- then an explicit stopped or escalated state

Phase 6 does not lock the exact numeric retry count, but it does lock the behavior class:

- retries are finite
- failures must be surfaced structurally
- semantic uncertainty is a valid stop outcome

### 4. Evidence v2 is a complete object and debate consumption is summary-first

The project chooses to define Evidence v2 as a full auditable object, not a thin query-result wrapper.

The full object should be capable of carrying:

- provenance
- dictionary references
- query-intent references
- execution status
- time scope
- repair history
- result summary
- result payload or result reference

But debate agents should not be forced to consume the full low-level object by default.

The default handoff should be:

- summary-first
- traceable by reference
- detailed artifacts available when needed

## Formal Artifacts Produced By Phase 6

Phase 6 now has three formal contract documents:

- [06-QUESTION-AND-PLAN-CONTRACT.md](/c:/Users/afrangry/PycharmProjects/bysj_t2s/.planning/phases/06-evidence-planning-and-dynamic-query-engine-contracts/06-QUESTION-AND-PLAN-CONTRACT.md)
  - formalizes qualification-item-first check-question templates
  - formalizes question-driven evidence-plan items
  - formalizes traceability from qualification item to question template to plan item
- [06-DYNAMIC-QUERY-CONTRACT.md](/c:/Users/afrangry/PycharmProjects/bysj_t2s/.planning/phases/06-evidence-planning-and-dynamic-query-engine-contracts/06-DYNAMIC-QUERY-CONTRACT.md)
  - formalizes `query_intent`
  - formalizes the dynamic retrieval chain from planning to bounded repair and terminal outcome
  - formalizes observability while keeping SQL as runtime trace rather than long-term memory
- [06-EVIDENCE-V2-CONTRACT.md](/c:/Users/afrangry/PycharmProjects/bysj_t2s/.planning/phases/06-evidence-planning-and-dynamic-query-engine-contracts/06-EVIDENCE-V2-CONTRACT.md)
  - formalizes Evidence v2 as a richer auditable artifact
  - formalizes provenance from planning, dictionary context, query execution, and repair history
  - records the summary-first downstream stance without prematurely freezing Phase 7 packaging

## Locked Direction For Each Contract Area

### Check-question template direction

Phase 6 defines a reusable question template around a qualification-item spine.

The template makes room for:

- qualification item identity
- question identity
- linked policy clauses
- typical conflict patterns
- expected answer type
- likely evidence targets
- relevant time semantics

The key point is that question templates describe what must be answered before they describe how SQL will be written.

### Evidence plan direction

Phase 6 defines evidence plans as collections of question-driven plan items.

Each plan item can express at least:

- which question it serves
- what evidence targets it needs
- what fields matter
- what time window or temporal interpretation matters
- how important the item is
- what to do if evidence is missing, contradictory, or unavailable

The plan therefore sits between:

- semantic packet understanding
- dynamic query execution

and does not collapse into either one.

### Query-intent and dynamic-query direction

Phase 6 defines a new explicit `query_intent` layer.

This layer exists between:

- evidence planning
- SQL generation

Its job is to express intended retrieval semantics without committing to one SQL string too early.

The dynamic-query contract therefore distinguishes:

- question intent
- query intent
- SQL candidate
- execution result
- repair attempts

The repair contract also makes stop conditions explicit.

Examples of stop-worthy cases:

- missing required fields or tables
- semantic ambiguity that the packet cannot resolve
- repeated SQL failure after bounded repair
- unsafe or misleading query behavior

### Evidence v2 direction

Phase 6 defines Evidence v2 as the canonical artifact produced after query execution and repair handling.

It upgrades the current `EvidenceItem` idea from:

- query result plus short summary

to:

- auditable evidence object with provenance and execution trace

At minimum, the contract makes room for:

- evidence identity
- source plan item and question identity
- target entity or table context
- dictionary references
- query-intent reference
- execution outcome
- time scope
- repair history
- result summary
- structured result payload or structured result reference

## Execution Summary

Phase 6 execution answers the design-side requirement set for:

- `PLAN-01`
- `PLAN-02`
- `PLAN-03`
- `DSQL-01`
- `DSQL-02`
- `DSQL-03`
- `DSQL-04`
- `EVID-01`
- `EVID-02`

The answers are intentionally at the contract-definition level, not the implementation level.

What is now settled:

- how planning-side questions and plan items should be shaped
- why `query_intent` exists as a distinct intermediate object
- how bounded repair and stop semantics fit into the dynamic-query chain
- what makes Evidence v2 meaningfully richer than the current `EvidenceItem` prototype

What remains for Phase 7:

- the agent/tool handoff contract
- prompt-context loading rules
- the implementation-ready blueprint that connects these artifacts to future build phases

## Boundary Implications For Later Phases

### For Phase 7

Phase 7 should now assume:

- debate agents receive evidence summaries plus references, not raw SQL as their main working context
- tool-boundary discussion can start from a concrete handoff chain
- prompt-context loading rules can distinguish semantic-packet input from evidence-object output

### For Later Implementation

Implementation work after `v1.1` should assume:

- the current static `RULE_REGISTRY` is a migration baseline, not the final contract owner
- the future dynamic path needs traceability from qualification item all the way to evidence object
- bounded failure and stop behavior are part of the design, not an optional hardening pass

## Deferred Questions

These remain intentionally open after Phase 6 execution:

- the exact child-field schema of a check-question template
- the exact child-field schema of a question-driven plan item
- the exact numeric retry limit for `auto_debug_sql`
- the exact field-by-field schema of `query_intent`
- the exact field-by-field schema of Evidence v2
- whether the future agent-facing evidence view is a projection of Evidence v2 or a sibling contract

## Close

Phase 6 is now grounded by four concrete choices:

1. check-question templates are qualification-item-first
2. evidence plan items are question-driven
3. dynamic query uses bounded retries and explicit stop conditions
4. Evidence v2 is a complete auditable object, while debate agents consume a summary-first view by default

That is enough to treat Phase 6 as executed and to move the project forward to final handoff design in Phase 7.
