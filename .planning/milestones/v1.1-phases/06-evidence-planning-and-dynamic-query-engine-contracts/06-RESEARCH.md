# Phase 6: Evidence Planning and Dynamic Query Engine Contracts - Research

**Researched:** 2026-03-24  
**Status:** Ready for planning

## Goal

Find the safest way to formalize evidence planning, dynamic query generation, bounded repair, and Evidence v2 without collapsing the new design back into the old static `rule_id -> SQL -> result` pipeline.

## Findings

### 1. The current static pipeline already contains useful conceptual seeds

The existing assets in:

- [sql_templates.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/text2sql/sql_templates.py)
- [evidence_collector.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/text2sql/evidence_collector.py)
- [evidence_model.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/evidence/evidence_model.py)

already imply:

- hidden question cataloging
- evidence grouping
- execution outcomes
- early summary and verdict fields

Implication:

- Phase 6 should explicitly upgrade these concepts
- it should not merely restate the old static registry in new words

### 2. The most important contract split is between planning artifacts and execution artifacts

If Phase 6 tries to define everything in one document, the boundary will blur between:

- a reusable verification question
- a task-specific plan item
- a query intent
- an executed evidence artifact

Implication:

- one plan should formalize question templates and question-driven evidence plans
- one plan should formalize query-intent and bounded dynamic-query behavior
- one plan should formalize Evidence v2 and explain how it supersedes the current `EvidenceItem`

### 3. Question-driven planning is the stable bridge between Phase 5 cognition and dynamic query

The user locked:

- qualification-item-first question templates
- question-driven evidence plan items

Implication:

- Phase 6 should make the "question" the stable handoff key between cognition and execution
- this avoids dropping directly from semantic packet to SQL generation

### 4. Bounded retries and explicit stop states must be designed together

The dynamic-query contract cannot just say "there is an auto debugger."

It must also say:

- what counts as a retryable failure
- what counts as a semantic stop
- what gets preserved in trace history

Implication:

- query contract planning should bundle generation, execution, repair, and stop conditions into one wave

### 5. Evidence v2 is the most likely place for accidental Phase 7 leakage

Because the discussion already established:

- Evidence v2 should be a complete auditable object
- debate agents should consume a summary-first view by default

there is a temptation to fully design the agent-facing projection now.

Implication:

- Phase 6 should define the full evidence artifact and only the minimal carry-forward assumption for summary-first consumption
- it should not fully design final agent prompt packaging yet

## Recommendations

### Recommended plan split

- Plan `06-01`: formalize qualification-item-first question templates and question-driven evidence-plan items
- Plan `06-02`: formalize `query_intent`, `text_to_sql`, bounded repair, and explicit stop conditions
- Plan `06-03`: formalize Evidence v2 and map current static assets to the new execution artifact model

### Recommended verification shape

- confirm question templates are anchored on qualification items, not on SQL or raw clauses alone
- confirm evidence plans are question-driven and not just table checklists
- confirm query generation and repair are bounded and auditable
- confirm Evidence v2 is richer than the current `EvidenceItem` and traceable back to question/plan context

## Risks To Watch

- letting evidence-plan items collapse back into static SQL templates
- making `query_intent` too vague to constrain Text-to-SQL
- defining repair as open-ended "try until success"
- letting Evidence v2 become either too thin to be useful or so broad that it swallows Phase 7 handoff design
