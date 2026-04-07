# Phase 7 Blueprint: Staged Implementation and Migration

**Status:** Executed  
**Phase:** 7  
**Scope:** post-`v1.1` implementation order

## Purpose

This document turns the completed `v1.1` design milestone into a concrete build order.

It answers:

- what to build first
- what to preserve during migration
- what to delay until later milestones

It does not implement anything itself.

## Design Principles

1. Later implementation proceeds in staged slices rather than a full rewrite.
2. The current static retrieval runtime remains baseline, fallback, and regression oracle during migration.
3. New retrieval contracts should be introduced behind stable downstream boundaries.
4. Debate agents should not be rewritten into freeform tool callers.
5. Deferred work stays explicitly outside this milestone.

## Migration Baseline

The current static runtime remains valuable during migration:

- [evidence_collector.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/text2sql/evidence_collector.py) remains the baseline
- the same path remains the fallback
- the same path remains the regression oracle for shadow comparison

This is important because it gives later implementation:

- a known-good behavior reference
- a rollback path
- a comparison point while the dynamic path matures

## First Slice: Adapter Boundary

The first slice should not attempt to implement the new retrieval pipeline yet.

It should build the adapter boundary from current evidence objects into the future debate-ready interface.

Concretely, this slice should:

- project current `EvidenceItem` and `EvidenceBundle` into the future agent-facing evidence projection
- preserve the current static collector path untouched as the source of evidence
- adapt prompt assembly to consume the projection shape rather than a raw bundle assumption
- avoid changing debate-agent responsibility or prompt flow too early

Why this comes first:

- it stabilizes the downstream interface
- it lets later retrieval work plug in behind a known projection contract
- it reduces migration risk by preserving current runtime behavior while shifting only the boundary

## Second Slice: New Retrieval Pipeline Behind The Boundary

The second slice should introduce the new retrieval pipeline without yet rewriting the debate layer.

Concretely, this slice should add:

- semantic packet consumer
- evidence planning
- `query_intent`
- `text_to_sql`
- bounded repair
- Evidence v2 generation

The key rule is:

- the new retrieval path should terminate in the same downstream projection contract established in the first slice

Why this comes second:

- retrieval can evolve while the debate surface stays stable
- old and new retrieval paths can be compared behind the same output boundary
- the system can shadow or compare outputs before fully switching over

## Third Slice: Connect New Retrieval Output Into Debate Orchestration

The third slice connects the new retrieval output into the live orchestration path.

Concretely, this slice should:

- connect the new projection-producing retrieval path into debate orchestration
- keep debate agents as consumers of prepared evidence
- avoid rewriting agents into freeform tool callers
- preserve orchestrator ownership of any future gap escalation hooks

This is where the new path becomes operationally meaningful, but it should still sit behind the same debate-ready input contract.

## Orchestrator Role During Migration

[debate_orchestrator.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/agents/debate_orchestrator.py) is the natural control point for migration.

It should remain the place where:

- prepared evidence enters debate
- future projection adapters are applied
- future mediated gap paths would be triggered
- old path versus new path selection can be controlled

This keeps the architecture disciplined:

- upstream tools prepare
- orchestrator routes
- agents judge

## What Should Not Happen During Migration

The following would be migration mistakes:

- replacing everything in one full rewrite
- removing the static path before the new path is comparable
- changing the debate layer and retrieval layer at the same time with no stable adapter
- allowing debate agents to directly own `text_to_sql`

## Comparison Strategy

During migration, the old static path should act as a comparison oracle.

That means future implementation should be able to compare:

- old prepared evidence versus new prepared evidence
- old projection behavior versus new projection behavior
- old debate outcomes versus new debate outcomes when inputs differ

This does not need to be built in `v1.1`, but the blueprint makes comparison part of the expected migration posture.

## Deferred Items

The following remain intentionally outside the current milestone and outside the first post-`v1.1` implementation slices:

- full agent-driven evidence-gap loops
- post-debate rule engine execution
- concrete MCP transport and deployment topology
- large-scale evaluation harnesses
- learning-loop automation and retained repair-artifact reuse

These items are still part of the broader direction, but they are not required to begin implementing the staged migration above.

## Why The Blueprint Is Ordered This Way

The ordering is intentional:

1. stabilize downstream projection
2. replace upstream retrieval behind that projection
3. connect the new path into live orchestration

This is safer than:

- changing prompts, retrieval, and orchestration all at once
- forcing the debate layer to absorb unfinished upstream churn

## Development Guidance Value

This document should be strong enough for later implementation planning to answer:

- what the first coding slice should change
- what must remain stable during migration
- what the current static runtime still provides
- which later ideas stay deferred

If a future plan proposes a monolithic rewrite with no baseline, no fallback, and no regression oracle, it is misaligned with this blueprint.
