# Agent Ablation Evaluation Summary

- suite_id: `multi_agent_policy_eval_v1`
- generated_at: `2026-04-30T13:54:06.816028+00:00`
- experiment: `Pro-Con Debate`
- case_count: `24`
- conclusion_accuracy: `87.50%`
- decision_quality_score: `85.63%`
- overall_pass_rate: `54.17%`
- reason_completeness_rate: `83.33%`
- avg_evidence_reference_rate: `68.75%`
- consensus_reached_rate: `79.17%`
- conflict_identification_rate: `100.00%`

| Case | Difficulty | Expected | Actual | Conclusion | Quality | Overall | Evidence Ref | Conflict |
| --- | --- | --- | --- | --- | ---: | --- | ---: | --- |
| simple_001 | simple | pass | pass | True | 100.00% | True | 100.00% | N/A |
| simple_002 | simple | pass | pass | True | 100.00% | True | 100.00% | N/A |
| simple_003 | simple | pass | pass | True | 100.00% | True | 100.00% | N/A |
| simple_004 | simple | pass | pass | True | 75.00% | False | 100.00% | N/A |
| simple_005 | simple | pass | pass | True | 100.00% | True | 100.00% | N/A |
| simple_006 | simple | pass | pass | True | 100.00% | True | 100.00% | N/A |
| simple_007 | simple | fail | fail | True | 100.00% | True | 100.00% | N/A |
| simple_008 | simple | pass | pass | True | 100.00% | True | 100.00% | N/A |
| simple_009 | simple | pass | pass | True | 75.00% | False | 100.00% | N/A |
| simple_010 | simple | pass | pass | True | 100.00% | True | 100.00% | N/A |
| medium_001 | medium | pass | pass | True | 100.00% | True | 100.00% | N/A |
| medium_002 | medium | pass | pass | True | 100.00% | True | 100.00% | N/A |
| medium_003 | medium | pass | pass | True | 100.00% | True | 100.00% | N/A |
| medium_004 | medium | pass | missing | False | 65.00% | False | 100.00% | N/A |
| medium_005 | medium | fail | fail | True | 100.00% | True | 100.00% | N/A |
| medium_006 | medium | missing | missing | True | 100.00% | True | 100.00% | N/A |
| complex_001 | complex | fail | fail | True | 80.00% | False | 0.00% | True |
| complex_002 | complex | fail | fail | True | 55.00% | False | 0.00% | True |
| complex_003 | complex | missing | missing | True | 80.00% | False | 0.00% | True |
| complex_004 | complex | fail | fail | True | 80.00% | False | 0.00% | True |
| complex_005 | complex | fail | missing | False | 65.00% | False | 50.00% | True |
| complex_006 | complex | fail | missing | False | 45.00% | False | 0.00% | True |
| complex_007 | complex | fail | fail | True | 80.00% | False | 0.00% | True |
| complex_008 | complex | missing | missing | True | 55.00% | False | 0.00% | True |
