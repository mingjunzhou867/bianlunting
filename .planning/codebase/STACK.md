# Technology Stack

**Analysis Date:** 2026-03-23

## Languages

**Primary:**
- Python 3.x - Backend API, agent orchestration, database access, evidence collection
- SQL (MySQL 8.0+) - Business schema, mock data, evidence query templates, debate log persistence target

**Secondary:**
- JavaScript (ES modules) - Vue frontend entry and component code in `frontend/src/`
- Markdown - Project docs and planning artifacts

## Runtime

**Environment:**
- Python runtime - Runs FastAPI app, LLM agents, SQLAlchemy, test scripts
- Node.js runtime - Runs frontend dev/build via Vite
- Browser runtime - Consumes `/api/debate_stream` via Server-Sent Events

**Package Manager:**
- Python packages via `requirements.txt`
- npm in `frontend/`
- Lockfile: `frontend/package-lock.json` present

## Frameworks

**Core:**
- FastAPI - HTTP API in [api/main.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/api/main.py)
- SQLAlchemy 2.x - Database execution and session lifecycle in [config/database.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/config/database.py)
- Pydantic 2.x - Settings and domain models in `config/` and `evidence/`
- Vue 3.5 - Frontend app in `frontend/src/`
- Vite 8 - Frontend dev server and build tool
- Element Plus 2.13 - UI component library for the demo frontend

**Testing:**
- No unified test runner configured at repo root
- Python script-style tests under `tests/` are run manually, for example `python -m tests.test_debate`

**Build/Dev:**
- Uvicorn - Local API server entry from [api/main.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/api/main.py)
- Vite - Frontend dev/build in `frontend/package.json`

## Key Dependencies

**Critical:**
- `openai` - LLM provider client used by agent layer
- `anthropic` - Alternate LLM provider client supported by settings
- `pymysql` - MySQL driver used by SQLAlchemy
- `SQLAlchemy` - Query execution and transaction/session abstraction
- `pydantic` / `pydantic-settings` - Structured models and `.env` loading
- `loguru` - Logging across backend modules

**Infrastructure:**
- `vue` - Frontend application framework
- `element-plus` - UI widgets for evidence board and agent result display
- `@vitejs/plugin-vue` - Vue integration for Vite

## Configuration

**Environment:**
- Backend settings are loaded from `config/.env` by [config/settings.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/config/settings.py)
- Key env vars include LLM provider credentials and MySQL connection settings
- Debate behavior is configured through `system_date`, `debate_max_rounds`, and `consensus_threshold`

**Build:**
- Python dependencies are declared in [requirements.txt](/c:/Users/afrangry/PycharmProjects/bysj_t2s/requirements.txt)
- Frontend scripts and dependencies are declared in [frontend/package.json](/c:/Users/afrangry/PycharmProjects/bysj_t2s/frontend/package.json)

## Platform Requirements

**Development:**
- Local MySQL instance expected
- Python environment with packages from `requirements.txt`
- Node.js/npm for frontend work

**Production:**
- Current repo appears optimized for local/demo execution rather than a formal deployment target
- Backend expects a reachable MySQL database and outbound access to the configured LLM provider

---
*Stack analysis: 2026-03-23*
*Update after major dependency changes*
