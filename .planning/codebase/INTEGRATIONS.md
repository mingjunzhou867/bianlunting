# External Integrations

**Analysis Date:** 2026-03-23

## APIs & External Services

**LLM Providers:**
- OpenAI-compatible chat endpoint - Used by the agent layer to generate judgments and debate responses
  - SDK/Client: `openai` package, routed through `config/llm_client.py`
  - Auth: `LLM_API_KEY` in `config/.env`
  - Configuration: `LLM_PROVIDER`, `LLM_BASE_URL`, `LLM_MODEL`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`

- Anthropic - Alternate configured provider path
  - SDK/Client: `anthropic` package
  - Auth: `LLM_API_KEY` in `config/.env`
  - Configuration: selected via `LLM_PROVIDER=anthropic`

## Data Storage

**Databases:**
- MySQL - Primary operational datastore and schema source
  - Connection: composed from `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_CHARSET`
  - Client: SQLAlchemy + PyMySQL in [config/database.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/config/database.py)
  - Schema source: [data/schema/mysql_ddl.sql](/c:/Users/afrangry/PycharmProjects/bysj_t2s/data/schema/mysql_ddl.sql)
  - Mock data: `data/mock_data/`

**Caching:**
- None observed

**File Storage:**
- None observed for uploaded artifacts or debate archives

## Authentication & Identity

**Auth Provider:**
- None observed
- API is currently open and CORS allows all origins in [api/main.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/api/main.py)

## Monitoring & Observability

**Logs:**
- `loguru` application logs only
  - Integration: in-process logging, no external sink observed

**Analytics / Error Tracking:**
- None observed

## CI/CD & Deployment

**Hosting:**
- No deployment manifests or platform config found
- Local run pattern appears to be `uvicorn` for backend and `vite` for frontend

**CI Pipeline:**
- No GitHub Actions or other CI pipeline detected from inspected files

## Environment Configuration

**Development:**
- Backend secrets live in `config/.env`
- Frontend API URL is hardcoded to `http://localhost:8000/api/debate_stream` in [frontend/src/App.vue](/c:/Users/afrangry/PycharmProjects/bysj_t2s/frontend/src/App.vue)
- MySQL is required for realistic backend behavior and persistence

**Production:**
- No separate staging/production configuration layer observed
- No secret management abstraction beyond local env file

## Webhooks & Callbacks

**Incoming:**
- None observed

**Outgoing:**
- None observed

---
*Integration audit: 2026-03-23*
*Update when adding/removing external services*
