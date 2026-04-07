---
phase: 01-adapter-boundary
plan: 03
status: completed
requirements_completed: [ADAPTER-02]
---

# Phase 1 Plan 03 Summary

Switched the live debate path to consume projection-format evidence.

Artifacts produced:

- `agents/base_agent.py`
- `agents/debate_orchestrator.py`

Key outcomes:

- added `format_projection()` as the summary-first prompt renderer
- updated `judge()` and `debate_respond()` to accept `EvidenceProjection`
- routed both synchronous and streaming orchestration through the projection boundary before agent calls
