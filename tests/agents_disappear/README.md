# Agent Chain Ablation Experiments

This directory contains ablation experiments for the policy debate agent chain.

The full-chain reference is:

```text
tests/agents_test/multi_agent_eval.py
```

## Experiments

### Single Agent

```powershell
python tests\agents_disappear\run_single_agent_eval.py
```

Uses one strict-compliance agent to judge from evidence directly.

### Pro-Con Debate

```powershell
python tests\agents_disappear\run_pro_con_eval.py
```

Uses strict-compliance and lenient-business agents as a two-side debate.

### No Evidence Constraint

```powershell
python tests\agents_disappear\run_no_evidence_constraint_eval.py
```

Runs the full agent set, but hides evidence cards from debate prompts. SQL
evidence is still collected for metric calculation, but agents cannot directly
ground their answer in those cards.

## Smoke Tests

```powershell
python tests\agents_disappear\run_single_agent_eval.py --limit 1 --persona-mode off
python tests\agents_disappear\run_pro_con_eval.py --limit 1 --persona-mode off
python tests\agents_disappear\run_no_evidence_constraint_eval.py --limit 1 --persona-mode off
```

## Outputs

Reports are written under:

```text
tests/agents_disappear/reports/
```

Each experiment writes:

- `latest_results.json`
- `latest_results.csv`
- `latest_summary.md`

## Main Metrics

- `conclusion_accuracy`
- `overall_pass_rate`
- `reason_completeness_rate`
- `avg_evidence_reference_rate`
- `conflict_identification_rate`
- `consensus_reached_rate`
- `avg_agent_valid_response_rate`
- `avg_total_time_sec`
- `difficulty_metrics`
