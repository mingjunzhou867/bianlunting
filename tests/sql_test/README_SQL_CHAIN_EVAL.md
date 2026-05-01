# SQL Chain Evaluation

`run_sql_chain_eval.py` uses the JSON cases in this directory to evaluate the Text2SQL chain.

The case field `question` is sent to the SQL generation chain. The case field `sql` is treated as gold SQL and is executed to produce the expected result set. The evaluator compares execution results instead of requiring exact SQL text equality.

## Run

```powershell
python tests\sql_test\run_sql_chain_eval.py
```

Useful options:

```powershell
python tests\sql_test\run_sql_chain_eval.py --category simple_test --limit 5
python tests\sql_test\run_sql_chain_eval.py --simple-all
python tests\sql_test\run_sql_chain_eval.py --max-retries 3
```

Save category reports without overwriting the default report:

```powershell
python tests\sql_test\run_sql_chain_eval.py --category condition_test --report-prefix condition_test
python tests\sql_test\run_sql_chain_eval.py --category sum_test --report-prefix sum_test
python tests\sql_test\run_sql_chain_eval.py --category muti_test --report-prefix muti_test
```

Append a timestamp when you want to keep multiple runs of the same category:

```powershell
python tests\sql_test\run_sql_chain_eval.py --category simple_test --report-prefix simple_test --timestamp-report
```

Reports are written to:

```text
tests/sql_test/sql_chain_eval_report.json
tests/sql_test/sql_chain_eval_report.csv
```

## Summary Metrics

- `sql_generation_success_rate`
- `first_syntax_pass_rate`
- `first_execution_success_rate`
- `first_result_match_rate`
- `final_syntax_pass_rate`
- `final_execution_success_rate`
- `final_result_match_rate`
- `retry_trigger_rate`
- `retry_repair_success_rate`
- `avg_retry_count`
- `first_avg_latency_ms`
- `final_avg_latency_ms`
- `p95_final_latency_ms`
- `structural_warning_rate`
- `structural_warnings`

## Notes

The evaluator only allows `SELECT` or CTE SQL. If the gold SQL cannot execute against the current database, the case is marked as `gold_sql_error` so dataset or database issues are separated from generated SQL failures.

Structural warnings do not fail a case by themselves. They mark SQL shape drift when the final SQL result matches but the generated SQL adds filters or joins that the gold SQL did not contain, such as `extra_join`, `extra_id_card_filter`, `extra_is_valid_filter`, or projection column differences.
