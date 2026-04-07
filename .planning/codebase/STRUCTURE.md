# Codebase Structure

**Analysis Date:** 2026-03-23

## Directory Layout

```text
bysj_t2s/
├── agents/              # Multi-agent judgment roles and debate orchestrator
├── api/                 # FastAPI entrypoint and HTTP endpoints
├── config/              # Settings, database, and LLM client configuration
├── data/                # MySQL DDL and mock SQL data
│   ├── mock_data/       # Seed/mock records for demo cases
│   └── schema/          # Database schema definitions
├── docs/                # Additional documentation
├── evidence/            # Shared evidence domain models
├── frontend/            # Vue + Vite demo UI
│   └── src/             # App entry and components
├── tests/               # Script-style backend tests
├── text2sql/            # SQL template registry and evidence collection logic
├── .codex/              # GSD workflow assets and skills
├── main.py              # CLI/info entry for environment summary
├── requirements.txt     # Python dependencies
└── README.md            # Project background and scope
```

## Directory Purposes

**agents/**
- Purpose: Core debate system implementation
- Contains: `debate_orchestrator.py`, `base_agent.py`, five role-specific agent files, package exports
- Key files: [agents/debate_orchestrator.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/agents/debate_orchestrator.py), [agents/base_agent.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/agents/base_agent.py)
- Subdirectories: None

**api/**
- Purpose: Backend HTTP surface
- Contains: FastAPI bootstrap and route definitions
- Key files: [api/main.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/api/main.py)
- Subdirectories: None

**config/**
- Purpose: Backend runtime configuration and infrastructure helpers
- Contains: settings, database session helper, LLM client
- Key files: [config/settings.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/config/settings.py), [config/database.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/config/database.py)
- Subdirectories: None

**data/**
- Purpose: Business schema and demo data
- Contains: MySQL DDL and mock insert/reset SQL
- Key files: [data/schema/mysql_ddl.sql](/c:/Users/afrangry/PycharmProjects/bysj_t2s/data/schema/mysql_ddl.sql)
- Subdirectories: `schema/`, `mock_data/`

**evidence/**
- Purpose: Shared structured evidence models passed through the system
- Contains: package init and [evidence/evidence_model.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/evidence/evidence_model.py)
- Key files: [evidence/evidence_model.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/evidence/evidence_model.py)
- Subdirectories: None

**text2sql/**
- Purpose: SQL execution and rule-to-query mapping
- Contains: `sql_templates.py`, [text2sql/evidence_collector.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/text2sql/evidence_collector.py)
- Key files: [text2sql/evidence_collector.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/text2sql/evidence_collector.py)
- Subdirectories: None

**frontend/**
- Purpose: Demo UI for triggering debates and streaming results
- Contains: `package.json`, Vite config, Vue source
- Key files: [frontend/src/App.vue](/c:/Users/afrangry/PycharmProjects/bysj_t2s/frontend/src/App.vue)
- Subdirectories: `src/components/`, `src/assets/`

**tests/**
- Purpose: Manual/integration-oriented backend verification scripts
- Contains: `test_debate.py`, `test_agents.py`, `test_evidence_collector.py`
- Key files: [tests/test_debate.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/tests/test_debate.py)
- Subdirectories: None

## Key File Locations

**Entry Points:**
- [api/main.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/api/main.py): FastAPI server entry and API routes
- [main.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/main.py): local summary/diagnostic entry
- [frontend/src/App.vue](/c:/Users/afrangry/PycharmProjects/bysj_t2s/frontend/src/App.vue): primary frontend interaction flow

**Configuration:**
- [config/settings.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/config/settings.py): backend env-derived settings
- [config/database.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/config/database.py): SQLAlchemy engine/session helper
- [requirements.txt](/c:/Users/afrangry/PycharmProjects/bysj_t2s/requirements.txt): Python dependency list
- [frontend/package.json](/c:/Users/afrangry/PycharmProjects/bysj_t2s/frontend/package.json): frontend scripts and deps

**Core Logic:**
- [agents/debate_orchestrator.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/agents/debate_orchestrator.py): debate rounds, consensus, DB persistence
- [agents/base_agent.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/agents/base_agent.py): shared agent output contract and LLM call flow
- [text2sql/evidence_collector.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/text2sql/evidence_collector.py): SQL execution to evidence mapping
- [data/schema/mysql_ddl.sql](/c:/Users/afrangry/PycharmProjects/bysj_t2s/data/schema/mysql_ddl.sql): database schema contract

**Testing:**
- [tests/test_debate.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/tests/test_debate.py): end-to-end debate flow smoke test
- [tests/test_agents.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/tests/test_agents.py): agent output inspection
- [tests/test_evidence_collector.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/tests/test_evidence_collector.py): evidence collection validation

**Documentation:**
- [README.md](/c:/Users/afrangry/PycharmProjects/bysj_t2s/README.md): project scope and competition framing
- `.planning/codebase/`: brownfield map for future planning

## Naming Conventions

**Files:**
- Python modules use `snake_case.py`
- Vue single-file components use `PascalCase.vue`
- Test files use `test_*.py`

**Directories:**
- Backend directories use lowercase names by concern (`agents`, `api`, `config`, `text2sql`)
- Frontend source follows standard `src/components` layout

**Special Patterns:**
- `__init__.py` files expose package-level exports
- SQL schema and mock data live under `data/schema/` and `data/mock_data/`

## Where to Add New Code

**New persistence feature around completed debates:**
- Primary backend code: `agents/` or a new persistence/query service module under `api/` or `config/`-adjacent backend package
- Schema changes: `data/schema/`
- Read APIs for historical debates: `api/`
- Frontend retrieval/history UI: `frontend/src/`
- Tests: `tests/`

**New evidence/query rule:**
- SQL template registry: `text2sql/sql_templates.py`
- Evidence execution logic: [text2sql/evidence_collector.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/text2sql/evidence_collector.py)
- Schema support if needed: [data/schema/mysql_ddl.sql](/c:/Users/afrangry/PycharmProjects/bysj_t2s/data/schema/mysql_ddl.sql)

## Special Directories

**.codex/**
- Purpose: Local GSD workflow assets and skills
- Source: Repo-managed automation resources
- Committed: Yes

**data/mock_data/**
- Purpose: Demo/reset SQL for mock personas
- Source: Manually maintained sample dataset
- Committed: Yes

---
*Structure analysis: 2026-03-23*
*Update when directory structure changes*
