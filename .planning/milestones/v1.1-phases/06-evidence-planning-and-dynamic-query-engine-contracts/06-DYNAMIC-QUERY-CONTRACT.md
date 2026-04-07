# Phase 6 Contract: Dynamic Query Chain

**Status:** Executed  
**Phase:** 6  
**Scope:** query-side contract only

## Purpose

This document defines how one question-driven evidence-plan item becomes a dynamic retrieval attempt that is observable, repairable, and bounded.

The chain must preserve meaning from planning while avoiding a return to "stored SQL is the system's memory."

The canonical flow is:

`plan item -> query_intent -> text_to_sql -> execution -> optional auto_debug_sql -> terminal outcome`

## Scope

This contract defines:

- the role of `query_intent`
- how runtime SQL is generated
- how execution and validation fit in the same chain
- when repair is allowed
- when the system must stop instead of looping
- what runtime trace should be retained

This contract does not define:

- final MCP wire format
- exact model prompts
- final downstream debate packaging

## Design Principles

1. SQL is generated at runtime, not stored as canonical knowledge.
2. `query_intent` is a first-class intermediate artifact.
3. Repair is bounded and explicit.
4. Semantic uncertainty is a valid stop outcome.
5. Runtime traces must support audit and debugging.

## Canonical Flow

The Phase 6 dynamic-query chain is:

1. receive one question-driven evidence-plan item
2. derive one structured `query_intent`
3. send that intent to `text_to_sql`
4. execute the produced SQL candidate
5. validate runtime outcome
6. if needed, allow bounded `auto_debug_sql`
7. return a terminal outcome that later Evidence v2 can record

This contract rejects two failure modes:

- infinite repair loops
- one-shot fatalism where any first failure ends the attempt

## Query Intent

`query_intent` is the semantic bridge between planning and SQL generation.

It is not:

- a raw SQL string
- a copied plan item
- a final evidence object

It is a retrieval-oriented interpretation of the plan item.

### Minimum Conceptual Coverage

The exact field list can evolve later, but a compliant `query_intent` must express:

- which plan item it serves
- which question it is trying to answer
- which entity or entities are in scope
- which evidence targets matter
- which fields or facts are needed
- which time semantics apply
- which filters are mandatory
- which ambiguity warnings remain active
- what answer shape is expected

### Why Query Intent Exists

Without `query_intent`, the system falls back into one of two bad patterns:

- planning objects become pseudo-SQL
- Text-to-SQL receives vague natural-language requests with weak traceability

`query_intent` prevents both. It is the smallest object that still carries retrieval semantics.

## Runtime Text-to-SQL

`text_to_sql` is the first runnable tool in the expanded architecture.

Its job is to translate one `query_intent` into one or more SQL candidates suitable for execution against the current schema.

The generator should be grounded by:

- the task-level semantic packet
- relevant dictionary excerpts
- table and field semantics
- the originating plan item and question

It should not rely on:

- hidden memorized SQL templates as the primary authority
- raw debate-agent improvisation

## Execution and Validation

The SQL candidate must be executed and evaluated as part of the same chain.

Execution validation should distinguish at least these classes:

- syntactically invalid
- field or table mismatch
- execution failure
- empty but valid result
- semantically suspicious result
- valid and usable result

The system must not collapse all failure into a single generic "bad SQL" bucket.

## Auto Debug / Repair

`auto_debug_sql` is allowed only as a bounded repair stage.

Its purpose is not to keep generating forever until something runs. Its purpose is to repair one query attempt when there is a reason to believe the underlying retrieval goal still makes sense.

Repair may respond to:

- schema mismatch
- field mismatch
- join error
- filter misuse
- obvious time-window misuse

Repair should not silently rewrite the business meaning of the question.

## Bounded Retry Stance

Phase 6 locks the behavior class even though it does not lock the final retry count.

The stance is:

- one initial generation attempt
- a small finite number of repair attempts
- then a terminal stop outcome

This is a design rule, not an optional implementation preference.

## Explicit Stop Conditions

The chain must stop when one of the following is true:

- required fields or tables cannot be resolved
- repeated repair does not produce a valid executable query
- the semantic packet cannot disambiguate the retrieval goal
- the result appears unsafe or misleading for the original question
- the system detects that repair would change the question rather than repair the query

Terminal outcomes may include:

- success
- no usable data
- stopped for unresolved schema gap
- stopped for semantic ambiguity
- stopped after bounded repair exhaustion
- escalated for human or higher-layer review

## Observability

The dynamic-query chain must remain inspectable.

At minimum, runtime trace should preserve:

- source plan item reference
- source question reference
- `query_intent` reference
- generated SQL candidate or candidates
- execution outcome per attempt
- repair attempts and reasons
- terminal stop reason

This observability is required for debugging, evaluation, and later learning loops.

## Runtime Trace Versus Long-Term Memory

Generated SQL is an execution trace, not the canonical knowledge layer.

That means:

- SQL strings may be logged or attached to evidence provenance
- SQL strings may help debugging and regression comparison
- SQL strings should not become the main persistent representation of policy logic

The long-term architectural memory should remain in:

- qualification items
- question templates
- evidence plans
- dictionary assets
- semantic packets

## Relationship To Current Static Collector

The current predecessor lives in [evidence_collector.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/text2sql/evidence_collector.py).

That file currently performs something closer to:

`rule_id -> SQL -> execute -> EvidenceItem`

The future mapping is:

- `rule_id` lineage becomes question lineage
- collector execution becomes one runtime stage inside a broader chain
- auto verdict hints become later evidence interpretation inputs, not the whole planning model

This makes the old collector a migration baseline, not the owner of future retrieval contracts.

## What Does Not Belong In This Contract

The following are intentionally deferred:

- exact retry count
- final repair prompt structure
- final MCP transport
- final Evidence v2 field-level schema
- final agent-facing context projection

## Development Guidance Value

This document is intended to guide the first implementation slice of dynamic retrieval.

A developer should be able to use it to decide:

- where `query_intent` sits
- why execution and repair are one bounded chain
- what outcomes must be represented explicitly
- why generated SQL is traceable but not canonical

If a future implementation jumps directly from plan item to stored SQL template lookup, or allows unconstrained repair loops, it is misaligned with this contract.
