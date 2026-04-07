# Phase 7 Contract: Agent-Facing Evidence Projection

**Status:** Executed  
**Phase:** 7  
**Scope:** debate-agent input contract

## Purpose

This document defines what debate agents receive from the upstream cognition, planning, and query layers.

The goal is to preserve the Phase 6 "summary-first" direction while making the downstream input concrete enough that later implementation does not drift back to:

- raw SQL as agent context
- raw database rows as agent context
- freeform agent reconstruction of semantics and provenance

## Design Principles

1. Debate agents consume prepared evidence rather than discover evidence from scratch.
2. The downstream input is summary-first, not detail-first.
3. The downstream input must still be structured enough to support real contradiction analysis.
4. The downstream input is derived from Evidence v2, not a competing evidence lineage.
5. Detail remains available by reference when escalation is warranted.

## Canonical Role

The agent-facing evidence projection is the debate-ready view of one prepared evidence set.

It sits between:

- the canonical internal evidence artifact, Evidence v2
- the current debate prompt surface in [base_agent.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/agents/base_agent.py)

Its job is to give agents the information needed to judge, challenge, and compare evidence without forcing them to parse low-level retrieval traces.

## What Debate Agents Receive By Default

The default debate input should include:

- task header
- policy or qualification scope
- compact semantic packet excerpt relevant to the current question set
- evidence summary cards
- confidence and status markers
- contradiction and insufficiency notes
- references back to Evidence v2 artifact IDs

This is richer than a one-line summary but lighter than a full internal artifact dump.

## Minimum Projection Sections

The exact field schema can evolve later, but a compliant projection must make room for:

- task identity
- target person identity
- policy identity
- qualification scope
- evidence card list
- card-level status and confidence signals
- contradiction or uncertainty markers
- artifact references
- optional escalation hints

## Evidence Summary Cards

An evidence summary card is the main reading unit agents should consume.

Each card should communicate:

- what question or qualification item it relates to
- what the usable evidence says
- whether it supports, contradicts, or leaves the point unresolved
- what level of confidence or stability the retrieval path had
- which artifact ID or IDs support the summary

This gives agents something debate-friendly while preserving traceability.

## Relationship To Evidence v2

The projection is an adaptation of Evidence v2.

That means:

- Evidence v2 remains the canonical auditable artifact
- the projection is a downstream view designed for debate consumption
- every projection card should be traceable back to one or more Evidence v2 artifact IDs

This contract rejects a dual-lineage design where:

- one evidence system exists for retrieval
- another unrelated evidence system exists for debate

Instead, there is one canonical evidence lineage with different consumption views.

## What Debate Agents Should No Longer Invent

Debate agents should no longer be expected to infer:

- field semantics from raw column names
- code dictionaries from raw coded values
- time interpretation from raw timestamps or months alone
- provenance structure from SQL output
- whether retrieval was stable or repaired, unless the projection explicitly surfaces that signal

Those responsibilities belong to upstream layers:

- database cognition
- evidence planning
- dynamic query
- Evidence v2 construction

## What Debate Agents Still Own

Debate agents still own:

- policy judgment
- contradiction analysis
- insufficiency analysis
- dissent and challenge
- weighing what prepared evidence implies

They remain reasoners, not retrievers.

## What Debate Agents Do Not Receive By Default

Debate agents do not receive by default:

- raw SQL traces
- raw database rows
- full untrimmed Evidence v2 payloads
- full dictionary payloads
- full repair histories

Those may exist behind references, but they are not the default debate prompt surface.

## Visible Uncertainty

The projection must not hide instability.

If useful interpretation depends on retrieval fragility or contradiction, the projection should expose compact visible signals such as:

- unresolved
- contradictory
- retrieval instability
- missing evidence
- low confidence

This allows agents to reason honestly without needing low-level execution traces in every prompt.

## Compatibility With Current Runtime

The current runtime uses [EvidenceBundle](/c:/Users/afrangry/PycharmProjects/bysj_t2s/evidence/evidence_model.py) and prompt formatting in [base_agent.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/agents/base_agent.py).

Phase 7 intentionally points toward a migration path where:

- current `EvidenceItem` and `EvidenceBundle` can be adapted into the future projection
- debate prompts can evolve behind a stable input contract
- the debate layer does not need to be rewritten into a low-level query consumer

## What This Contract Must Avoid

The following would be regressions:

- feeding raw SQL directly to debate agents as their normal context
- forcing debate agents to infer semantics from coded values with no dictionary grounding
- making the projection so thin that agents must reconstruct provenance mentally
- creating a second debate-only evidence lineage unrelated to Evidence v2

## Development Guidance Value

This document should be strong enough for future implementation to answer:

- what the default debate-ready evidence input is
- how it relates to Evidence v2
- what structured detail is included by default
- what agents must no longer infer from raw state

If a future implementation still prompts agents with raw SQL, raw database rows, or ungrounded coded values as the ordinary path, it is misaligned with this contract.
