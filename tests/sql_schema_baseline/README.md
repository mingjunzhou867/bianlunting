# Schema-Aware LLM SQL Ablation

This experiment is the second SQL baseline:

**Question + database schema -> SQL, one-shot generation.**

It compares against:

- `tests/sql_disappear`: question-only Direct LLM baseline
- `tests/sql_test`: full SQL Harness

## What This Test Uses

- Natural-language `question`
- Database table/column schema context
- One LLM generation
- Gold SQL execution-result comparison

## What This Test Removes

- No Harness `EvidencePlanItem`
- No Harness schema notes
- No retry
- No auto repair
- No structural drift check

## Run

```powershell
python tests\sql_schema_baseline\run_schema_llm_eval.py
python tests\sql_schema_baseline\run_schema_llm_eval.py --category simple_test --limit 2
```

Reports are written to `tests/sql_schema_baseline/reports`.
