# Plan 01-01 Summary

## Outcome

Defined one canonical persistence contract for successful debate sessions and aligned it across runtime serialization and MySQL DDL.

## Delivered

- Added [agents/debate_persistence.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/agents/debate_persistence.py) as the shared serialization and write helper
- Added a new `debate_session` table in [data/schema/mysql_ddl.sql](/c:/Users/afrangry/PycharmProjects/bysj_t2s/data/schema/mysql_ddl.sql) for query-friendly session summaries plus a full snapshot payload
- Reworked `agent_debate_log` in [data/schema/mysql_ddl.sql](/c:/Users/afrangry/PycharmProjects/bysj_t2s/data/schema/mysql_ddl.sql) to match actual runtime judgment fields instead of the old mismatched scenario/final-verdict schema

## Canonical Contract

- Persist only successful completed sessions
- Save summary fields for future history lists: `session_id`, `id_card`, `status`, `source_endpoint`, conclusion, stance, consensus, rounds, evidence count, timestamps
- Save a full snapshot payload that extends the existing debate result with evidence details and full round history
- Save per-round per-agent judgments as structured rows for later inspection and drift detection

## Verification

- Contract assertions added in [tests/test_persistence_contract.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/tests/test_persistence_contract.py)
