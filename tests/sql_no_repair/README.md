# SQL Harness Without Repair Ablation

This experiment disables the SQL Harness retry/repair loop.

It still uses the existing Harness prompt, SQL safety check, syntax check,
database execution, result comparison, and structural warning logic.

## Purpose

Compare this result with the full Harness in `tests/sql_test` to measure the
value of automatic error feedback and retry repair.

## Run

```powershell
python tests\sql_no_repair\run_no_repair_eval.py
python tests\sql_no_repair\run_no_repair_eval.py --category simple_test --limit 2
```

Reports are written to `tests/sql_no_repair/reports`.
