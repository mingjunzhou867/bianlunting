# Phase 7 Contract: Prompt Loading and Tool Boundary

**Status:** Executed  
**Phase:** 7  
**Scope:** debate-time prompt classes and tool ownership

## Purpose

This document defines:

- what debate-time context is always present
- what context is loaded only on demand
- what context must never be blindly injected
- which tools belong to planning/query orchestration rather than debate-time reasoning

The goal is to preserve the architectural discipline established by Phases 4-6.

## Design Principles

1. Debate-time prompts should stay compact by default.
2. Expansion should be explicit and justified.
3. Debate agents remain consumers of prepared evidence, not owners of retrieval tools.
4. Any future evidence-gap escalation should be mediated by orchestration.
5. The prompt-loading contract must build on the semantic packet and Evidence v2, not reopen them.

## Prompt Context Classes

Phase 7 locks three debate-time context classes:

- always-present
- on-demand
- never blindly injected

This three-class model is a formal contract, not a convenience guideline.

## Always-Present Context

Always-present context is the compact default context debate agents should receive in ordinary operation.

It includes:

- role prompt
- task header
- policy or qualification scope
- debate objective and output schema
- agent-facing evidence projection for the current task
- prior round judgments when applicable

This is the minimum stable package needed for disciplined debate behavior.

## On-Demand Context

On-demand context is material that may be injected when the orchestrator decides the default package is not enough.

It may include:

- additional dictionary excerpts
- detailed provenance for one evidence artifact
- repair history when a contradiction depends on retrieval instability
- selected semantic packet subsections not already present in the default bundle

This preserves the "reference before expansion" rule:

- default prompts get compact summaries and references
- deeper detail is expanded only when needed

## Never Blindly Injected Context

The following should never be blindly injected into ordinary debate prompts:

- full database schema dumps
- full dictionaries by default
- raw SQL traces by default
- complete repair logs by default
- full untrimmed Evidence v2 payloads

These may still exist for audit or debugging, but they are not part of the normal debate surface.

## Relationship To The Semantic Packet

The semantic packet defined in [05-SEMANTIC-PACKET-CONTRACT.md](/c:/Users/afrangry/PycharmProjects/bysj_t2s/.planning/phases/05-database-cognition-and-dictionary-memory/05-SEMANTIC-PACKET-CONTRACT.md) remains upstream.

Debate prompts should not receive the entire packet by default.

Instead:

- the default path uses compact relevant excerpts inside the agent-facing evidence projection
- deeper sections such as `fields`, `relations`, `time_semantics`, or `dict_excerpt` may be expanded on demand

This preserves the excerpt-first and task-trimmed design.

## Tool Ownership Boundary

Phase 7 locks the following ownership model.

Planning/query orchestration owns:

- semantic packet assembly
- dictionary lookup and excerpting
- evidence-plan generation
- query-intent construction
- Text-to-SQL execution
- bounded repair
- Evidence v2 construction

Debate agents own:

- policy judgment
- challenge and dissent
- contradiction analysis
- insufficiency analysis over prepared evidence

## What Debate Agents Do Not Directly Call

During ordinary debate turns, debate agents do not directly call:

- `text_to_sql`
- `get_dict`
- `auto_debug_sql`

This is a hard directional choice for the architecture.

It prevents the system from collapsing back into:

- agent-led schema exploration
- per-agent ad hoc querying
- uncontrolled retrieval loops inside debate

## Mediated Evidence-Gap Path

Phase 7 still leaves room for future retrieval escalation, but the path is mediated.

When an agent detects a missing or insufficient evidence situation, the preferred behavior is:

1. the agent emits a structured gap, challenge, or `needs-more-evidence` signal
2. the orchestrator decides whether a second-pass retrieval is warranted
3. any additional retrieval remains in the planning/query tool boundary
4. updated evidence re-enters debate through the same projection model

This means future multi-pass behavior, if added, is orchestrator-mediated rather than freeform per-agent probing.

## Relationship To The Dynamic Query Contract

The dynamic-query chain defined in [06-DYNAMIC-QUERY-CONTRACT.md](/c:/Users/afrangry/PycharmProjects/bysj_t2s/.planning/phases/06-evidence-planning-and-dynamic-query-engine-contracts/06-DYNAMIC-QUERY-CONTRACT.md) already owns:

- `query_intent`
- `text_to_sql`
- execution
- bounded repair
- terminal outcomes

Phase 7 does not reopen that.

Instead, it states that debate agents sit downstream of those outcomes and should not absorb query ownership back into their prompt surface.

## Relationship To Current Runtime

The current runtime in [debate_orchestrator.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/agents/debate_orchestrator.py) already centralizes debate sequencing.

That makes the orchestrator the natural place for:

- future gap escalation handling
- future on-demand context expansion
- enforcing debate-time tool restrictions

The current prompt assembly in [base_agent.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/agents/base_agent.py) is the natural place to study how the projection can be consumed without exposing raw low-level artifacts.

## What This Contract Must Avoid

The following would be regressions:

- always injecting full semantic packet content
- always injecting full dictionaries
- always injecting SQL traces
- allowing debate agents to query tools directly during normal rounds
- letting repair history dominate ordinary prompt context

## Development Guidance Value

This document should be strong enough for future implementation to answer:

- what debate prompts contain by default
- what requires explicit expansion
- what should never be blindly injected
- which tools belong to orchestration rather than debate
- how future second-pass retrieval should be staged if added later

If a future implementation lets ordinary debate prompts balloon into full schema and SQL dumps, or turns each debate agent into a freeform retriever, it is misaligned with this contract.
