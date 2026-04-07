# Architecture

**Analysis Date:** 2026-03-23

## Pattern Overview

**Overall:** Demo-style full-stack monolith with a Python backend, a Vue frontend, and a database-backed evidence + debate workflow

**Key Characteristics:**
- Request-driven backend with synchronous agent orchestration
- Shared structured evidence model passed into multiple heterogeneous agents
- Streamed UI updates through Server-Sent Events
- MySQL used both as evidence source and intended persistence layer for debate traces

## Layers

**API Layer:**
- Purpose: Expose debate execution over HTTP
- Contains: FastAPI endpoints in [api/main.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/api/main.py)
- Depends on: orchestration and evidence services
- Used by: Vue frontend and any external HTTP client

**Orchestration Layer:**
- Purpose: Control evidence collection, round-based agent judgment, consensus checks, and persistence
- Contains: [agents/debate_orchestrator.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/agents/debate_orchestrator.py)
- Depends on: evidence collector, agent factory, database session helper
- Used by: API layer

**Agent Layer:**
- Purpose: Produce structured judgments from evidence and prior debate turns
- Contains: [agents/base_agent.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/agents/base_agent.py) and role-specific agent modules in `agents/`
- Depends on: LLM client and evidence models
- Used by: orchestration layer

**Evidence Layer:**
- Purpose: Execute SQL templates and normalize query results into structured evidence
- Contains: [text2sql/evidence_collector.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/text2sql/evidence_collector.py), `text2sql/sql_templates.py`, [evidence/evidence_model.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/evidence/evidence_model.py)
- Depends on: database layer
- Used by: API and orchestration layers

**Persistence Layer:**
- Purpose: Provide database connectivity and target schema for both business facts and debate logs
- Contains: [config/database.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/config/database.py), [data/schema/mysql_ddl.sql](/c:/Users/afrangry/PycharmProjects/bysj_t2s/data/schema/mysql_ddl.sql)
- Depends on: environment configuration
- Used by: evidence collector and debate orchestrator

**Presentation Layer:**
- Purpose: Trigger a debate session and visualize evidence, per-round judgments, and final conclusion
- Contains: [frontend/src/App.vue](/c:/Users/afrangry/PycharmProjects/bysj_t2s/frontend/src/App.vue) and components in `frontend/src/components/`
- Depends on: streaming API contract
- Used by: human operator/demo user

## Data Flow

**Debate Stream Request:**

1. Frontend posts `id_card` to `/api/debate_stream` in [frontend/src/App.vue](/c:/Users/afrangry/PycharmProjects/bysj_t2s/frontend/src/App.vue)
2. FastAPI endpoint in [api/main.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/api/main.py) returns a `StreamingResponse`
3. `DebateOrchestrator.run_debate_stream()` creates a `session_id`
4. `EvidenceCollector.collect_all()` queries MySQL and builds an `EvidenceBundle`
5. Orchestrator yields `evidence` SSE event
6. Five agents each produce round-0 `AgentJudgment` values
7. Orchestrator persists round judgments to `agent_debate_log`
8. If consensus is not reached, additional rounds are executed using previous judgments as context
9. Orchestrator writes a final verdict row, builds a result dict, and emits `debate_final`
10. Frontend hydrates its local `currentData.debate.history` and final verdict state

**State Management:**
- Backend debate execution is request-scoped and stateless in memory after response completion
- Persistence is attempted per round via MySQL inserts
- Frontend keeps debate state only in browser memory during the active session
- No retrieval/read model exists yet for previously completed debates

## Key Abstractions

**EvidenceBundle / EvidenceItem:**
- Purpose: Normalize database facts into a shared debate input format
- Examples: [evidence/evidence_model.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/evidence/evidence_model.py)
- Pattern: Pydantic domain model

**AgentJudgment:**
- Purpose: Enforce a structured output contract for every agent turn
- Examples: [agents/base_agent.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/agents/base_agent.py)
- Pattern: Pydantic model returned by heterogeneous agents

**DebateRecord:**
- Purpose: Group one round of judgments and compute majority/convergence data
- Examples: [agents/debate_orchestrator.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/agents/debate_orchestrator.py)
- Pattern: in-memory round aggregate

## Entry Points

**Backend API:**
- Location: [api/main.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/api/main.py)
- Triggers: HTTP `POST /api/debate` and `POST /api/debate_stream`
- Responsibilities: Validate request body, invoke orchestrator, shape response/stream

**Frontend App:**
- Location: `frontend/src/main.js` and [frontend/src/App.vue](/c:/Users/afrangry/PycharmProjects/bysj_t2s/frontend/src/App.vue)
- Triggers: User clicks quick-test or submits an ID card
- Responsibilities: Open stream, consume SSE chunks, render evidence and debate state

**Manual Tests:**
- Location: [tests/test_debate.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/tests/test_debate.py)
- Triggers: `python -m tests.test_debate`
- Responsibilities: Exercise end-to-end orchestration against a database

## Error Handling

**Strategy:** Catch exceptions near agent and API boundaries, then degrade to fallback judgments or HTTP 500

**Patterns:**
- Agent failures are converted into fallback `AgentJudgment` records in [agents/debate_orchestrator.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/agents/debate_orchestrator.py)
- Database insert failures inside debate logging are logged but not re-raised, so the debate can still complete
- API handlers in [api/main.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/api/main.py) raise `HTTPException` on top-level failure

## Cross-Cutting Concerns

**Logging:**
- `loguru` is used across evidence collection, orchestration, and DB utilities

**Validation:**
- Pydantic models validate request payloads, settings, evidence, and agent judgments

**Persistence Contract Risk:**
- The debate log write path in [agents/debate_orchestrator.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/agents/debate_orchestrator.py) does not match the `agent_debate_log` schema declared in [data/schema/mysql_ddl.sql](/c:/Users/afrangry/PycharmProjects/bysj_t2s/data/schema/mysql_ddl.sql)
- This is the most important architectural gap for the requested “save everything and reuse later” feature

---
*Architecture analysis: 2026-03-23*
*Update when major patterns change*
