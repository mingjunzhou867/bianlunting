# Phase 6 Contract: Evidence v2

**Status:** Executed  
**Phase:** 6  
**Scope:** evidence-artifact direction

## Purpose

This document defines the target direction for Evidence v2: the auditable artifact produced after planning-driven retrieval and bounded dynamic-query execution.

The goal is to move beyond the current thin result wrapper and define an evidence object that can support:

- debate
- explanation
- audit
- debugging
- later evaluation

## Design Principles

1. Evidence is an artifact, not just a result blob.
2. Provenance must be visible from planning through execution.
3. Time scope and dictionary context are first-class evidence features.
4. Debate agents should receive summaries first, with traceable access to detail.
5. Evidence must remain compatible with migration from the current prototype.

## Canonical Role Of Evidence v2

Evidence v2 is the object produced after the dynamic-query chain reaches a terminal outcome for one evidence-plan item.

It is responsible for representing:

- what was being checked
- what retrieval path was attempted
- what happened during execution
- what the usable result means

It is not merely:

- a SQL row dump
- a static `rule_id` wrapper
- a final policy verdict

## Minimum Object Direction

The final implementation schema is intentionally deferred, but a compliant Evidence v2 object must make room for:

- artifact identity
- source task identity
- source qualification item identity
- source question identity
- source plan item identity
- evidence target context
- time scope or time interpretation
- dictionary references
- query-intent reference
- runtime execution trace reference
- terminal execution outcome
- repair history
- summary for downstream consumption
- structured payload or payload reference

## Provenance Requirements

Evidence v2 must preserve provenance across layers.

At minimum, a future reader must be able to trace one evidence object backward to:

1. the task that requested it
2. the question that motivated it
3. the plan item that scoped it
4. the query intent that shaped retrieval
5. the runtime attempts that produced the final state

This makes evidence auditable without reintroducing SQL strings as the primary semantic layer.

## Dictionary Provenance

Because Phase 5 made dictionary memory first-class, Evidence v2 must also be able to record dictionary lineage where relevant.

Examples:

- which dictionary IDs were used
- which excerpt entries were injected
- whether code-value resolution affected interpretation

This matters when the result meaning depends on values such as:

- hardship-category codes
- insurer-status codes
- gender encodings
- business-role codes

## Query Provenance

Evidence v2 must preserve query-side lineage sufficiently for debugging and evaluation.

That includes room for:

- `query_intent` reference
- generated SQL reference or trace
- execution result class
- repair attempts
- terminal stop reason

This does not mean the full SQL must always be copied into every agent prompt. It means the evidence artifact must remain able to point back to what happened.

## Time Scope

Evidence v2 must treat temporal meaning as part of the artifact itself, not just an afterthought in a summary string.

Examples:

- current-state check as of system date
- historical continuity over a month range
- latest valid record
- contradiction between historical and current state

Time scope is necessary both for audit and for later explanation to debate agents or reviewers.

## Relationship To Current Prototype

The current predecessor lives in [evidence_model.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/evidence/evidence_model.py).

Today the system has:

- `EvidenceItem`
- `EvidenceBundle`

Those models already contain useful seeds:

- `rule_id`
- `result_summary`
- `exec_status`
- raw result storage

Phase 6 maps them forward like this:

- `rule_id` becomes migration-era lineage, not the final semantic anchor
- `result_summary` remains valuable but no longer stands alone
- `exec_status` remains valuable but must sit beside richer provenance
- bundle assembly remains useful, but future grouping should be able to reason over plan and question lineage

So Evidence v2 is an upgrade path, not a denial that the current prototype exists.

## Summary-First Downstream Consumption

Phase 6 locks one important downstream stance:

- debate agents consume a summary-first view by default
- detailed provenance stays available by reference

This is the right balance for the current architecture because:

- full raw traces are useful for audit and debugging
- most debate steps need usable summaries instead of low-level runtime detail
- Phase 7 still needs room to design the final handoff format

In other words:

- full Evidence v2 is the canonical artifact
- agent-facing evidence view is a projection or packaged view derived from it

## What Evidence v2 Must Avoid

The following would be regressions:

- storing only raw rows with no question lineage
- storing only summaries with no execution trace
- losing which dictionary excerpt shaped interpretation
- collapsing repair attempts into one opaque error message
- forcing debate agents to parse raw SQL as their main evidence input

## What Does Not Belong In This Contract

Phase 6 intentionally does not finalize:

- the exact field-by-field Pydantic schema
- final storage layout
- final agent prompt packaging
- final evaluation metrics

Those belong to later implementation and Phase 7 handoff work.

## Development Guidance Value

This document is intended to be a real development baseline.

A future implementation should be able to use it to decide:

- what new provenance the evidence model must carry
- how evidence relates to planning and query execution
- why summary-first downstream use is compatible with a richer internal artifact
- how to upgrade from `EvidenceItem` without inventing a second unrelated evidence lineage

If a future implementation still treats evidence as only `SQL + rows + one summary line`, it is misaligned with this contract.
