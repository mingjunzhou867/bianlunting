# Direct LLM Baseline SQL Ablation

This directory contains the first SQL ablation experiment:

**Direct LLM Baseline: natural-language question directly generates SQL.**

It is used as a baseline against the full SQL Harness in `tests/sql_test/run_sql_chain_eval.py`.

## What This Test Removes

- No `EvidencePlanItem`
- No schema notes
- No retry
- No auto repair
- No structural drift check

Each sample sends only `question` to the configured LLM once.

## Run

```powershell
python tests\sql_disappear\run_direct_llm_eval.py
```

Useful options:

```powershell
python tests\sql_disappear\run_direct_llm_eval.py --category simple_test --limit 2
python tests\sql_disappear\run_direct_llm_eval.py --category condition_test
python tests\sql_disappear\run_direct_llm_eval.py --timestamp-report
```

## Reports

Reports are written to:

```text
tests/sql_disappear/reports/direct_llm_eval_report.json
tests/sql_disappear/reports/direct_llm_eval_report.csv
```

## Metrics

- `case_count`
- `evaluated_case_count`
- `gold_sql_error_count`
- `sql_generation_success_rate`
- `syntax_pass_rate`
- `execution_success_rate`
- `result_match_rate`
- `avg_latency_ms`
- `p95_latency_ms`
- `failure_reasons`
- `category_metrics`
