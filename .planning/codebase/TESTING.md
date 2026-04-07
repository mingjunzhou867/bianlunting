# Testing Patterns

**Analysis Date:** 2026-03-23

## Test Framework

**Runner:**
- No unified test framework config found
- Backend verification is currently script-style Python modules under `tests/`

**Assertion Library:**
- Native Python assertions and rich/log-style output patterns appear to be used

**Run Commands:**
```bash
python -m tests.test_debate
python -m tests.test_agents
python -m tests.test_evidence_collector
npm --prefix frontend run build
```

## Test File Organization

**Location:**
- Separate `tests/` tree at repo root

**Naming:**
- `test_*.py` naming for backend tests

**Structure:**
```text
tests/
  test_agents.py
  test_debate.py
  test_evidence_collector.py
```

## Test Structure

**Patterns:**
- Tests are oriented around executable scripts and smoke/integration verification
- `test_debate.py` runs the real orchestrator and expects a working database
- Console output is part of the current verification ergonomics

## Mocking

**Framework:**
- No dedicated mocking framework observed from inspected files

**Patterns:**
- Current tests appear closer to integration checks than isolated unit tests
- Real DB and real orchestration flow are expected in at least some tests

## Fixtures and Factories

**Test Data:**
- Persona fixtures live in `tests/test_agents.py`
- Mock SQL data is stored under `data/mock_data/`

## Coverage

**Requirements:**
- No automated coverage target or enforcement found

**Configuration:**
- No coverage config found

## Test Types

**Unit Tests:**
- Limited evidence of isolated unit tests

**Integration Tests:**
- Strongest existing pattern
- Debate flow test exercises collector + agents + DB persistence together

**Frontend Tests:**
- None observed

## Common Patterns

**Database-dependent verification:**
- Tests often assume a live MySQL instance and seeded persona data

**Manual follow-up:**
- `test_debate.py` explicitly asks the operator to inspect `agent_debate_log` after execution
- This indicates persistence is only partially asserted today

## Gaps Relevant To Current Feature

- No automated test currently verifies that a completed debate session can be reloaded later
- No test asserts a stable persisted schema for full session payloads, evidence snapshots, or agent intermediate reasoning
- No API-level test exists for a future “query historical debate result” flow

---
*Testing analysis: 2026-03-23*
*Update when test patterns change*
