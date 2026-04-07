# Phase 2: Retrieval APIs - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase adds backend read APIs over the completed debate sessions saved in Phase 1. It does not expand into new write behavior, frontend history UI, auth, or replay workflows. The phase is limited to one list-by-`id_card` entry point and one detail-by-`session_id` entry point.

</domain>

<decisions>
## Implementation Decisions

### History list shape
- The `id_card` history endpoint should return summary-only items in the first version
- Results should be sorted newest first by `completed_at`
- The first version should not add pagination yet
- Summary rows should stay focused on list-view essentials rather than embedding full detail payloads

### Detail response strategy
- The `session_id` detail endpoint should be snapshot-first
- The saved `snapshot_payload` is the canonical detail source for Phase 2
- The API may add a thin outer response wrapper, but should not rebuild the whole detail object from row data by default
- `agent_debate_log` remains available for verification and future extension, but not as the primary detail assembly path in Phase 2

### Empty and error semantics
- `id_card` history queries with no saved sessions should return an empty list rather than an error
- `session_id` detail queries with no matching saved session should return HTTP 404
- The existing API response style should stay clear and backend-friendly rather than overloading all misses into `200 OK`

### Retrieval API boundary
- Phase 2 should expose exactly two read entry points
- Do not add "recent sessions", broad filtering, or convenience browsing endpoints in this phase
- Keep the phase aligned tightly with the roadmap so Phase 3 can focus on hardening instead of trimming scope

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- [agents/debate_persistence.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/agents/debate_persistence.py): already defines the canonical saved snapshot shape and the summary fields stored in `debate_session`
- [data/schema/mysql_ddl.sql](/c:/Users/afrangry/PycharmProjects/bysj_t2s/data/schema/mysql_ddl.sql): already provides the two storage surfaces Phase 2 will read from: `debate_session` and `agent_debate_log`
- [api/main.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/api/main.py): already establishes the current FastAPI routing and response style for debate-related endpoints
- [config/database.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/config/database.py): already provides the SQLAlchemy text-query session pattern used elsewhere in the backend

### Established Patterns
- FastAPI handlers currently return a plain JSON envelope for non-stream endpoints
- SQLAlchemy `text(...)` queries are the current backend data-access pattern
- The current product boundary prefers backend-first delivery before any frontend history page work

### Integration Points
- Phase 2 will likely add read helpers near or inside the persistence layer rather than embedding SQL directly in route handlers
- The list endpoint should query `debate_session` by `id_card`
- The detail endpoint should load one `debate_session` row by `session_id` and deserialize `snapshot_payload`
- Existing `/api/debate` and `/api/debate_stream` contracts should remain unchanged while new read endpoints are added alongside them

</code_context>

<specifics>
## Specific Ideas

- Summary list items should stay lightweight enough for a future left-side history panel
- Likely summary fields include `session_id`, `id_card`, `status`, `source_endpoint`, `final_conclusion`, `final_stance`, `consensus_rate`, `rounds_taken`, `evidence_count`, and `completed_at`
- Detail responses should preserve the saved evidence snapshot and round history exactly as captured at completion time
- Because the detail API is snapshot-first, Phase 2 can stay consistent with Phase 1 and avoid accidental drift caused by reconstructing history from multiple tables
- The list API should be simple enough that a future frontend can call it repeatedly without needing pagination or filter state on day one

</specifics>

<deferred>
## Deferred Ideas

- Pagination for the history list
- Filtering by conclusion, time range, or source endpoint
- A "recent sessions" endpoint not tied to one `id_card`
- Returning both snapshot detail and expanded row-level log detail in the first version
- Frontend history navigation and layout work

</deferred>

---
*Phase: 02-retrieval-apis*
*Context gathered: 2026-03-23*
