# Coding Conventions

**Analysis Date:** 2026-03-23

## Naming Patterns

**Files:**
- Python modules use `snake_case.py`
- Vue components use `PascalCase.vue`
- Tests use `test_*.py`

**Functions:**
- Python functions and methods use `snake_case`
- Frontend handlers use `camelCase` with `handle*` naming for event processing

**Variables:**
- Python locals and instance members use `snake_case`
- Frontend locals use `camelCase`
- Constants use `UPPER_SNAKE_CASE` when declared as module-level constants

**Types:**
- Pydantic models use `PascalCase`
- No `I*` interface prefix pattern observed

## Code Style

**Formatting:**
- No formatter config found in inspected files
- Python code generally uses docstrings, explicit returns, and moderate function sizes
- String quoting is mixed but double quotes are common in Python source
- Semicolons are avoided in Python and mostly avoided in frontend code

**Linting:**
- No lint configuration found at repo root or frontend root from inspected files

## Import Organization

**Order:**
1. Standard library imports
2. Third-party packages
3. Internal modules

**Grouping:**
- Python files usually separate groups with blank lines
- Vue files keep a short flat import block at the top

## Error Handling

**Patterns:**
- Throw or raise on boundary validation failures
- Catch exceptions around agent calls and degrade into fallback judgments
- Database session helper centralizes commit/rollback behavior in [config/database.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/config/database.py)

**Error Types:**
- API layer uses `HTTPException`
- Internal services mostly raise generic exceptions and log details with context

## Logging

**Framework:**
- `loguru`
- Levels observed: `debug`, `info`, `warning`, `error`

**Patterns:**
- Log state transitions at evidence collection and debate orchestration boundaries
- DB insert failures are logged inline inside persistence loops

## Comments

**When to Comment:**
- Chinese module docstrings explain file purpose and business semantics
- Inline comments are used to label flow steps and domain-specific reasoning

**JSDoc/TSDoc:**
- Not used in frontend files inspected
- Python docstrings are the dominant documentation style

## Function Design

**Size:**
- Business functions are often medium-sized and process an entire workflow step
- Debate orchestration methods are relatively large and mix control flow with persistence

**Parameters:**
- Backend functions usually accept a small number of explicit parameters
- Structured models are preferred for rich data exchange

**Return Values:**
- Backend returns plain dicts for API/result payloads
- Pydantic models are used for intermediate structured data

## Module Design

**Exports:**
- Python packages use `__init__.py` barrel-style exports in `agents/`
- Vue app relies on direct component imports

**Barrel Files:**
- `agents/__init__.py` is the clearest barrel example

## Prescriptive Notes For New Work

- Match existing backend style: Pydantic models for structured contracts, `loguru` for logging, SQLAlchemy text queries for DB interaction
- Keep new persistence logic out of the frontend; the frontend currently acts as a consumer of shaped backend events/data
- Prefer extracting dedicated persistence/query modules rather than growing [agents/debate_orchestrator.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/agents/debate_orchestrator.py) indefinitely

---
*Convention analysis: 2026-03-23*
*Update when patterns change*
