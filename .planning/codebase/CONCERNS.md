# Codebase Concerns

**Analysis Date:** 2026-03-23

## Tech Debt

**Debate persistence contract mismatch:**
- Issue: Backend inserts fields like `session_id`, `agent_id`, `conclusion`, `confidence`, `evidence_refs`, `reasoning`, `dissent_points`, `key_finding`
- Files: [agents/debate_orchestrator.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/agents/debate_orchestrator.py), [data/schema/mysql_ddl.sql](/c:/Users/afrangry/PycharmProjects/bysj_t2s/data/schema/mysql_ddl.sql)
- Why: Code and schema evolved independently
- Impact: Debate log writes can fail or silently diverge from the intended schema, which directly blocks “save everything for later reuse”
- Fix approach: Define a single persisted debate model, align DDL and insert/read code, add migration-safe tests

**Persistence split across row logs only:**
- Issue: Current implementation stores per-agent rows and a final verdict row, but not a canonical session snapshot containing evidence, round history, and query-ready metadata
- Files: [agents/debate_orchestrator.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/agents/debate_orchestrator.py), [api/main.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/api/main.py)
- Why: Current code focuses on live execution/demo display
- Impact: Reconstructing a full historical debate is hard and potentially lossy
- Fix approach: Add a session-level persistence model plus retrieval API(s)

## Known Bugs

**`agent_debate_log` schema likely incompatible with runtime inserts:**
- Symptoms: Insert exceptions during debate persistence, or a DB schema forced to drift from DDL comments
- Trigger: Run debate flow against a database created strictly from [data/schema/mysql_ddl.sql](/c:/Users/afrangry/PycharmProjects/bysj_t2s/data/schema/mysql_ddl.sql)
- Workaround: Manually modify database schema to match runtime code
- Root cause: Column names and meanings differ between DDL and application insert SQL

## Security Considerations

**Open API surface:**
- Risk: Anyone who can reach the backend can trigger debate execution
- File: [api/main.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/api/main.py)
- Current mitigation: None observed
- Recommendations: Add auth or at least environment-gated access controls before exposing outside local/demo use

**Potential over-persistence of sensitive evidence:**
- Risk: The requested feature intends to save full debate content, which may include identity data, evidence SQL, and reasoning traces
- Files: [data/schema/mysql_ddl.sql](/c:/Users/afrangry/PycharmProjects/bysj_t2s/data/schema/mysql_ddl.sql), [agents/debate_orchestrator.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/agents/debate_orchestrator.py)
- Current mitigation: None beyond local schema design
- Recommendations: Decide explicitly what to store raw vs summarized, and define retention/access rules

## Performance Bottlenecks

**Per-request synchronous debate execution:**
- Problem: `/api/debate` and `/api/debate_stream` execute evidence collection plus all agent calls inline
- Files: [api/main.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/api/main.py), [agents/debate_orchestrator.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/agents/debate_orchestrator.py)
- Measurement: No formal numbers found
- Cause: No background job queue or async fan-out
- Improvement path: Add asynchronous execution model or persisted session/job abstraction if usage grows

## Fragile Areas

**`DebateOrchestrator` mixes too many responsibilities:**
- Why fragile: It owns round control, fallback logic, streaming, DB persistence, and final result shaping
- Common failures: New persistence features can accidentally break live streaming or final verdict handling
- Safe modification: Extract persistence and history reconstruction into dedicated services before expanding storage requirements
- Test coverage: Limited, and not schema-contract focused

**Frontend depends on live-only stream contract:**
- Why fragile: `App.vue` is wired for immediate SSE events, not historical session loading
- File: [frontend/src/App.vue](/c:/Users/afrangry/PycharmProjects/bysj_t2s/frontend/src/App.vue)
- Common failures: Adding retrieval/history UX without a normalized session payload will cause duplication or inconsistent shaping
- Safe modification: Introduce one stable backend DTO for both live final payload and historical retrieval
- Test coverage: No frontend tests observed

## Scaling Limits

**Historical retrieval feature is missing entirely:**
- Current capacity: Live debate execution only
- Limit: No path exists to fetch old sessions after the request ends
- Symptoms at limit: Results cannot be reused by later workflows or UIs
- Scaling path: Add persisted session table(s), indexes, and query API endpoints

## Dependencies at Risk

**LLM provider dependency on live network access:**
- Risk: Debate flow depends on external provider availability and API compatibility
- Impact: Historical replay and deterministic audit are hard if only live LLM responses exist
- Migration plan: Persist final structured outputs and key intermediate artifacts so future reads do not require recomputation

## Missing Critical Features

**Historical debate query capability:**
- Problem: No API or service can load a completed debate by session, person, or scenario
- Current workaround: Manually inspect database rows if persistence succeeded
- Blocks: “以后被调用” 这个需求目前无法成立
- Implementation complexity: Medium

**Canonical session persistence model:**
- Problem: There is no explicit design for saving all evidence, participants, session status, round history, and final result as one queryable resource
- Current workaround: Rely on raw per-row inserts into `agent_debate_log`
- Blocks: Reuse, audit, replay, analytics, and UI history views
- Implementation complexity: Medium to High

## Test Coverage Gaps

**Persistence schema contract:**
- What's not tested: DDL and runtime insert SQL compatibility
- Risk: Core persistence can break unnoticed
- Priority: High
- Difficulty to test: Low to Medium

**Historical retrieval flow:**
- What's not tested: Save-complete-session then read-it-back behavior
- Risk: Future reuse feature may be implemented partially and regress silently
- Priority: High
- Difficulty to test: Medium

---
*Concerns audit: 2026-03-23*
*Update as issues are fixed or new ones discovered*
