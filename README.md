# bianlunting

## Debate Persistence and Retrieval

This repository implements a multi-agent debate system for policy eligibility review. The current shipped baseline focuses on saving completed debate sessions, retrieving them later, and rendering saved history in the frontend.

## Current Capabilities

- `POST /api/debate`: returns one completed debate result
- `POST /api/debate_stream`: returns the live debate process over SSE
- `GET /api/debates?id_card=...`: returns saved session summaries for a person
- `GET /api/debates/{session_id}`: returns one saved session snapshot
- Frontend history browsing and replay for saved sessions

## Local Prerequisites

Apply the MySQL schema before running the saved-session flow:

1. `data/schema/mysql_ddl.sql`
2. `data/mock_data/personas_mock.sql` if you want demo data

Notes:

- `mysql_ddl.sql` rebuilds tables and may drop existing data
- `personas_mock.sql` resets mock/demo data and is not for production data

## Common Commands

Backend tests:

```powershell
python -m unittest tests.test_debate tests.test_persistence_contract tests.test_retrieval_api
```

Frontend smoke tests:

```powershell
npm.cmd --prefix frontend run test
```

Frontend production build:

```powershell
npm.cmd --prefix frontend run build
```
