# Phase 7: Agent Tool Boundary and Implementation Blueprint - Context

**Gathered:** 2026-03-24  
**Status:** Executed

<domain>
## Phase Boundary

Phase 7 defines the final handoff between the already-designed preparation/query layers and the existing multi-agent debate layer.

This phase delivers:

- the contract for what debate agents receive
- the contract for what debate agents no longer invent from raw database state
- the contract for what tools belong to planning/query orchestration versus debate-time reasoning
- the prompt-context loading rules
- the implementation blueprint that stages later coding without breaking the shipped `v1.0` runtime

This phase does not add new runtime capability and does not reopen:

- dictionary contract design
- semantic packet design
- planning-side question design
- dynamic-query retry semantics
- Evidence v2 provenance design

</domain>

<decisions>
## Implementation Decisions

### Agent Input Contract

- **D-01:** Debate agents should receive an agent-facing evidence projection derived from Evidence v2, not raw database rows and not raw SQL traces.
- **D-02:** The default debate input should be `summary-first`, but richer than a one-line summary. It should include:
  - task header
  - qualification scope
  - compact semantic packet excerpt relevant to the question set
  - evidence summary cards
  - confidence and status markers
  - references back to Evidence v2 artifact IDs
  - visible uncertainty and contradiction notes
- **D-03:** Debate agents should not be expected to infer field semantics, code dictionaries, or time interpretation from raw database state. Those belong to upstream cognition and retrieval layers.
- **D-04:** Debate agents may reason over contradictions and insufficiency, but they should treat evidence lineage as already prepared and should not reconstruct provenance themselves.

### Agent and Tool Responsibility Boundary

- **D-05:** In the target architecture, planning/query tools own:
  - semantic packet assembly
  - dictionary lookup and excerpting
  - evidence-plan generation
  - query-intent construction
  - Text-to-SQL execution and bounded repair
  - Evidence v2 construction
- **D-06:** Debate agents are consumers of prepared evidence, not primary database explorers.
- **D-07:** Phase 7 locks the default rule that debate agents do not call `text_to_sql`, `get_dict`, or `auto_debug_sql` directly during ordinary debate turns.
- **D-08:** If an agent believes evidence is missing, it should emit a structured "gap / challenge / needs-more-evidence" signal rather than directly querying the database.
- **D-09:** Any future second-pass retrieval should be orchestrator-mediated, not freeform per-agent tool use. That keeps the architecture from collapsing back into ad hoc agent probing.

### Prompt-Context Loading Rules

- **D-10:** Always-present context for debate agents should be limited to:
  - role prompt
  - task header
  - policy or qualification scope
  - debate objective and output schema
  - agent-facing evidence projection for the current task
  - prior round judgments when applicable
- **D-11:** On-demand context may include:
  - additional dictionary excerpts
  - detailed provenance for one evidence artifact
  - repair history when a contradiction depends on retrieval instability
  - selected semantic packet subsections not already present in the default bundle
- **D-12:** Context that should never be blindly injected into debate prompts includes:
  - full database schema dumps
  - full dictionaries by default
  - raw SQL traces by default
  - complete repair logs by default
  - full untrimmed Evidence v2 payloads
- **D-13:** The architecture should preserve "reference before expansion": default prompts receive compact summaries plus IDs, and expansion happens only when the orchestrator judges it necessary.

### Implementation Blueprint

- **D-14:** Later implementation should proceed in staged slices instead of a full rewrite.
- **D-15:** The first implementation slice should build the adapter boundary:
  - project current `EvidenceItem` and `EvidenceBundle` into the future agent-facing evidence projection
  - keep the current static collector path as baseline
  - avoid changing agent behavior and prompt surface too early
- **D-16:** The second slice should introduce the new retrieval pipeline behind the boundary:
  - semantic packet consumer
  - evidence planning
  - `query_intent`
  - `text_to_sql`
  - bounded repair
  - Evidence v2 generation
- **D-17:** The third slice should connect the new retrieval output to debate orchestration through the projection contract, so existing agents can consume the new path without being rewritten into tool-callers.
- **D-18:** Migration should preserve the old static chain as:
  - regression baseline
  - fallback path
  - comparison oracle during shadow evaluation
- **D-19:** Full agent-driven evidence-gap loops, richer tool choreography, and post-debate rule validation remain deferred beyond this milestone.

### Agent's Discretion

- The planner and later implementer may choose exact naming for the agent-facing evidence projection.
- The planner may decide whether the projection is represented as one composite object or as several smaller prompt cards, as long as `summary-first + traceable-by-reference` remains intact.
- The planner may decide whether orchestrator-mediated second-pass retrieval is represented as a future hook, an explicit event type, or a deferred interface placeholder.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Baseline

- `.planning/PROJECT.md` - milestone purpose, constraints, non-goals, and five-layer system definition
- `.planning/REQUIREMENTS.md` - Phase 7 requirement targets, especially `AGENT-01`, `AGENT-03`, `READY-01`, and `READY-02`
- `.planning/ROADMAP.md` - official Phase 7 scope and success criteria
- `.planning/STATE.md` - current milestone position and next-step routing

### Prior Design Contracts

- `.planning/phases/04-system-boundary-alignment/04-CONTEXT.md` - formal task entrypoint, MCP framing, and dynamic-SQL direction
- `.planning/phases/05-database-cognition-and-dictionary-memory/05-DICT-CONTRACT.md` - dictionary asset contract and excerpt-first strategy
- `.planning/phases/05-database-cognition-and-dictionary-memory/05-SEMANTIC-PACKET-CONTRACT.md` - semantic packet sections and loading assumptions
- `.planning/phases/06-evidence-planning-and-dynamic-query-engine-contracts/06-QUESTION-AND-PLAN-CONTRACT.md` - planning-side trace model
- `.planning/phases/06-evidence-planning-and-dynamic-query-engine-contracts/06-DYNAMIC-QUERY-CONTRACT.md` - query chain and bounded repair model
- `.planning/phases/06-evidence-planning-and-dynamic-query-engine-contracts/06-EVIDENCE-V2-CONTRACT.md` - evidence-artifact and provenance direction

### Phase 7 Formal Artifacts

- `.planning/phases/07-agent-tool-boundary-and-implementation-blueprint/07-AGENT-EVIDENCE-PROJECTION-CONTRACT.md` - formal downstream debate input contract
- `.planning/phases/07-agent-tool-boundary-and-implementation-blueprint/07-PROMPT-AND-TOOL-BOUNDARY-CONTRACT.md` - formal prompt-loading and tool-ownership contract
- `.planning/phases/07-agent-tool-boundary-and-implementation-blueprint/07-IMPLEMENTATION-BLUEPRINT.md` - staged migration and post-milestone build order

### Current Runtime Reference Points

- `agents/base_agent.py` - current debate-agent prompt surface and judgment schema
- `agents/debate_orchestrator.py` - current orchestration boundary and round flow
- `evidence/evidence_model.py` - current `EvidenceItem` / `EvidenceBundle` prototype
- `text2sql/evidence_collector.py` - current static retrieval boundary
- `text2sql/sql_templates.py` - current static rule registry and migration baseline
- `dicts/ADC310.json` - readable example of dictionary assets the future system should consume by excerpt

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `agents/base_agent.py`: already centralizes common prompt assembly and judgment parsing, so it is the natural place to study what the future agent-facing evidence projection must satisfy.
- `agents/debate_orchestrator.py`: already owns turn sequencing and is the natural enforcement point for "agents consume prepared evidence rather than directly query tools."
- `evidence/evidence_model.py`: provides a concrete migration baseline for mapping from current evidence objects into a future projection and then into Evidence v2.
- `text2sql/evidence_collector.py`: shows the current static retrieval chain that later slices should preserve as fallback and regression oracle.

### Established Patterns

- The current runtime already separates retrieval from debate at a coarse level, even though the retrieval side is still static-template based.
- Evidence is already bundled before agents debate, so the future architecture should preserve that pre-debate packaging instinct rather than switching to freeform live querying.
- Agent prompts currently expect compact readable evidence, which supports the Phase 6 summary-first direction.

### Integration Points

- A future agent-facing evidence projection should likely sit between retrieval completion and `BaseAgent` prompt assembly.
- Orchestrator-level handling is the right place for any future "evidence gap" escalation hook.
- Migration should protect the current debate flow by adapting inputs at the boundary rather than rewriting all agents at once.

</code_context>

<specifics>
## Specific Ideas

- The project should visibly demonstrate tool use and long-term semantic grounding, but debate-time behavior should still look disciplined rather than chaotic.
- The preferred architecture is "upstream tools prepare, downstream agents judge," not "every agent independently explores the database."
- The future system should feel more capable than `v1.0` while still being explainable enough for graduation-project and competition review.

</specifics>

<deferred>
## Deferred Ideas

- A fully interactive multi-pass debate where agents can repeatedly request more evidence mid-round is deferred beyond `v1.1`.
- The post-debate rule engine remains deferred to a later milestone.
- Concrete MCP transport and deployment topology remain deferred.
- Large-scale evaluation and learning-loop automation remain deferred.

</deferred>

## Execution Summary

Phase 7 execution completed the final design-side requirement set for this milestone:

- `AGENT-01`
- `AGENT-02`
- `AGENT-03`
- `READY-01`
- `READY-02`

What is now settled:

- what debate agents receive from upstream layers
- what debate agents should no longer infer or directly do
- how debate-time prompt loading is tiered
- how future implementation should migrate in staged slices

What remains after this phase is milestone-level closure work rather than new design scope:

- milestone audit if desired
- milestone archive and next-milestone setup

---

*Phase: 07-agent-tool-boundary-and-implementation-blueprint*  
*Context gathered: 2026-03-24*
