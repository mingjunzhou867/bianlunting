# Phase 1: Persistence Foundation - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers a stable persistence foundation for completed debate sessions. It defines what a successful completed session stores, aligns the schema with runtime write behavior, and prepares the data model so later phases can query saved sessions without rerunning the debate workflow.

</domain>

<decisions>
## Implementation Decisions

### Saved content boundary
- Evidence snapshots should store both raw rows and summaries, not just rule references
- Agent intermediate process should store every round's full structured judgment fields
- Successful session records should include complete execution metadata, not only final conclusion
- The canonical full snapshot should extend the current `debate_final` payload rather than inventing an unrelated response shape

### Session status semantics
- Only successfully completed debate sessions are persisted for later retrieval
- Failed or interrupted sessions are not persisted as historical records in this phase
- If a debate run fails, partial evidence and partial round history are discarded rather than stored
- Successful stored sessions may still use a richer internal/final status model than a bare success flag

### Query-oriented summary shape
- Historical retrieval should support `id_card`-based history lists and `session_id`-based detail lookup
- History results should keep all successful sessions, sorted newest first
- Summary/list data should at minimum expose timestamp, conclusion, status, and rounds taken
- Detail responses should return structured summary fields plus the full saved snapshot

### Claude's Discretion
- Exact field names and table split between session-level and detail-level storage
- Whether full snapshot lives in one JSON column or a small set of payload columns
- How to map current runtime objects into persisted summary fields as long as the locked decisions above are preserved

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- [agents/debate_orchestrator.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/agents/debate_orchestrator.py): already creates `session_id`, `history`, and final result dicts that can seed the canonical snapshot
- [evidence/evidence_model.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/evidence/evidence_model.py): already defines structured evidence objects suitable for snapshot serialization
- [agents/base_agent.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/agents/base_agent.py): already defines the structured `AgentJudgment` shape for per-round persistence

### Established Patterns
- Backend returns plain dict payloads from orchestrator methods and streams shaped SSE events from [api/main.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/api/main.py)
- SQLAlchemy text queries are the existing pattern for database writes and reads
- The current system treats `/api/debate` and `/api/debate_stream` as two entry points over the same orchestration logic

### Integration Points
- Persistence changes must integrate into both `run_debate()` and `run_debate_stream()`
- MySQL schema alignment starts from [data/schema/mysql_ddl.sql](/c:/Users/afrangry/PycharmProjects/bysj_t2s/data/schema/mysql_ddl.sql)
- Future retrieval APIs will depend on the summary fields and full snapshot shape defined by this phase

</code_context>

<specifics>
## Specific Ideas

- "全部内容" in this phase means the debated person, execution status, final result, evidence used, and each agent's intermediate process
- The user wants future reuse through backend APIs first, not frontend history pages first
- Historical value is focused on successful completed debates rather than failed-run auditing
- Future history UX should feel like ChatGPT/Gemini: a left-side history list and a central detail pane
- If no history item is selected and no ID card is provided, the center area should remain empty in the future UI
- Clicking a history item should load the full saved debate process into the center pane in a future phase
- Entering an ID card and submitting should show the current live agent state for that ID card in the center pane in a future phase
- Phase 1 should shape persisted summary/detail payloads so that later history UI can reuse them without redesigning the storage model

</specifics>

<deferred>
## Deferred Ideas

- Frontend history list/detail pages - deferred to a later phase
- ChatGPT/Gemini-style left-history + center-detail interface implementation - deferred to a later phase
- Persisting failed or interrupted sessions for audit/operations - not included in this phase
- Replaying old debates by rerunning the LLM workflow - not included in this phase

</deferred>

---
*Phase: 01-persistence-foundation*
*Context gathered: 2026-03-23*
