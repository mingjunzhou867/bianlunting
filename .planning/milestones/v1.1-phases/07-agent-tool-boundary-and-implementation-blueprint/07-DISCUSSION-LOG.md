# Phase 7: Agent Tool Boundary and Implementation Blueprint - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `07-CONTEXT.md`; this log preserves the alternatives considered.

**Date:** 2026-03-24  
**Phase:** 07-agent-tool-boundary-and-implementation-blueprint  
**Areas discussed:** Agent input contract, Agent/tool responsibility boundary, Prompt-context loading rules, Implementation blueprint

---

## Agent Input Contract

| Option | Description | Selected |
|--------|-------------|----------|
| Summary plus raw SQL | Keep prompts small but expose low-level execution traces directly to agents | |
| Summary-first evidence projection | Give agents readable evidence summaries, uncertainty markers, and references back to richer artifacts | X |
| Full Evidence v2 by default | Give agents the full provenance object every time | |

**User's choice:** Discussed and locked around the summary-first projection path.  
**Notes:** This follows the Phase 6 decision that full Evidence v2 remains canonical while debate consumption defaults to readable summaries plus traceable references.

---

## Agent and Tool Responsibility Boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Free agent tool use | Let debate agents call retrieval tools directly during debate | |
| Orchestrator-mediated gap signaling | Agents consume prepared evidence and emit structured "needs more evidence" signals when necessary | X |
| Planner-only retrieval forever | Never allow any later retrieval escalation path | |

**User's choice:** Discussed and locked around orchestrator-mediated escalation rather than free agent probing.  
**Notes:** This preserves the "show tools, not chaos" goal and keeps the architecture from sliding back into direct agent database exploration.

---

## Prompt-Context Loading Rules

| Option | Description | Selected |
|--------|-------------|----------|
| Everything up front | Always inject full semantic packet, full dictionaries, SQL traces, and evidence details | |
| Tiered loading | Keep task header and evidence summaries always-on, with deeper provenance and dictionary details available on demand | X |
| Ultra-minimal only | Give agents almost no context and force them to infer gaps | |

**User's choice:** Discussed and locked around tiered loading.  
**Notes:** Always-on context should stay compact; expansion should happen only when the orchestrator judges it necessary.

---

## Implementation Blueprint

| Option | Description | Selected |
|--------|-------------|----------|
| Full rewrite | Replace the current static collector and debate pipeline in one step | |
| Staged migration | Build adapter boundary first, then new retrieval pipeline, then connect the projection to debate flow | X |
| Agent-first rewrite | Rewrite debate agents into tool callers before stabilizing the boundary | |

**User's choice:** Discussed and locked around staged migration.  
**Notes:** The current static path remains the regression baseline and fallback while the new retrieval architecture is introduced behind the handoff boundary.

---

## Agent's Discretion

- Exact naming of the future agent-facing evidence projection
- Exact representation format of projection cards versus one composite object
- Exact placeholder shape for future orchestrator-mediated evidence-gap hooks

## Deferred Ideas

- Fully interactive agent-driven evidence requests during live debate
- Concrete MCP transport/deployment topology
- Rule-engine execution layer
- Large-scale evaluation and learning-loop automation
