# Phase 7 Research: Agent Tool Boundary and Implementation Blueprint

## Purpose

Phase 7 is the final design phase of milestone `v1.1`.

Its job is not to invent new runtime capability. Its job is to convert the already-settled Phase 4-6 architecture into an implementation-ready handoff model.

That means the research question is:

- how should the existing debate runtime consume future prepared evidence without collapsing back into agent-led database exploration?

## Inputs From Prior Phases

Phase 7 does not stand alone.

It inherits:

- formal task entrypoint and MCP framing from Phase 4
- dictionary and semantic-packet contracts from Phase 5
- evidence planning, query-intent, bounded repair, and Evidence v2 direction from Phase 6

The remaining work is the downstream edge:

- what agents see
- what they no longer do
- how prompt context is staged
- how implementation should migrate safely from `v1.0`

## Reusable Runtime Baseline

The current runtime already gives useful anchors:

- `agents/base_agent.py`
  - current prompt assembly boundary
  - current judgment schema
- `agents/debate_orchestrator.py`
  - current turn sequencing boundary
  - natural point for enforcing debate-time tool restrictions
- `evidence/evidence_model.py`
  - current evidence prototype
  - natural bridge for a migration adapter
- `text2sql/evidence_collector.py`
  - current static retrieval boundary
  - natural baseline and regression oracle during migration

This means Phase 7 planning should not propose a blank-slate rewrite.

## Planning Implications

Phase 7 planning should preserve these truths:

1. Debate agents are downstream consumers, not upstream retrievers.
2. The future agent-facing input is a projection of Evidence v2, not a new unrelated evidence lineage.
3. Prompt loading should remain tiered, with compact default context and explicit expansion rules.
4. Implementation should be staged so the current shipped runtime remains usable as:
   - baseline
   - fallback
   - regression reference

## Natural Plan Decomposition

The scope splits cleanly into three work packages:

1. agent-facing evidence projection and debate input contract
2. prompt-context loading rules plus debate/tool boundary enforcement model
3. implementation blueprint and migration sequencing

This decomposition has good dependency order:

- the input contract should come first
- prompt loading and tool boundary build on the input contract
- implementation blueprint comes last because it depends on both contracts being settled

## What Good Planning Should Avoid

Phase 7 plans should avoid:

- turning debate agents into freeform tool callers
- over-specifying final runtime code structure
- reopening already-settled Phase 5 or Phase 6 contracts
- writing vague migration guidance like "adapt old path to new path" without concrete target states

## Expected Deliverables

By the end of planning, Phase 7 should be ready to execute as documentation work that produces:

- a formal agent-facing evidence projection contract
- a formal prompt-context and tool-boundary contract
- a formal implementation blueprint and migration roadmap

It should also move project state to "ready for execution" without touching runtime code.
