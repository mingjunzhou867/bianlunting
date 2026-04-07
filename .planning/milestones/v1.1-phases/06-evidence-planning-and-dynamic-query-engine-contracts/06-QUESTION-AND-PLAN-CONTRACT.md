# Phase 6 Contract: Question Templates and Evidence Plans

**Status:** Executed  
**Phase:** 6  
**Scope:** planning-side contract only

## Purpose

This document defines the planning-side bridge between the Phase 5 semantic packet and the future dynamic-query chain.

The core shift is:

- from static `rule_id` lookup
- to reusable qualification-driven questions
- to task-specific evidence plans

The planning layer answers:

- what must be verified
- why it must be verified
- what evidence is likely needed

It does not answer:

- what SQL should be written
- how SQL should be repaired
- how debate prompts are finally packaged

## Design Principles

1. Qualification item first.
2. Questions before SQL.
3. Task plans inherit from reusable templates.
4. Traceability must remain visible from policy intent to runtime retrieval.
5. Planning stays semantic and auditable instead of collapsing into implementation detail.

## Contract Layers

Phase 6 planning uses three linked layers:

1. qualification item
2. reusable check-question template
3. task-specific evidence-plan item

This means the canonical lineage is:

`policy qualification item -> check-question template -> evidence-plan item`

The old static chain hid this inside `RULE_REGISTRY` and `rule_id`. The new contract makes that lineage explicit.

## Qualification Item Layer

A qualification item is the planning anchor. It represents one policy-facing thing the system must decide or verify.

Examples:

- person is alive and system-active
- person belongs to a hardship category
- person is currently in flexible employment
- person should be excluded because of shareholder or business identity
- person sits inside a retirement-edge ambiguity

The qualification item owns:

- business identity
- policy-facing meaning
- linked clause references
- conflict or ambiguity tags
- default answer expectation

The qualification item does not own:

- SQL strings
- table-specific execution details
- repair strategy

## Reusable Check-Question Template

A reusable check-question template is the canonical question pattern derived from one qualification item.

Its job is to express:

- the question to answer
- the kinds of evidence likely needed
- the time semantics that matter
- the typical ambiguity patterns to watch for

The template is reusable across people, policies, and task scopes because it is not bound to one SQL statement.

### Minimum Conceptual Fields

The contract does not freeze final field names, but a compliant template must cover:

- `qualification_item_id`
- `question_id`
- `question_text`
- `question_type`
- `linked_policy_clauses`
- `linked_conflict_patterns`
- `expected_answer_shape`
- `suggested_evidence_targets`
- `suggested_fields`
- `time_semantics_hint`
- `default_missing_evidence_behavior`

### Question Type Direction

The template should support at least these families:

- fact check
- exclusion check
- status check
- temporal continuity check
- calculation-supporting check
- conflict-resolution check

This keeps the question layer policy-aware without binding it to one physical query pattern.

## Task-Specific Evidence Plan

An evidence plan is generated at task time for:

- `person_id`
- `policy_id`
- optional qualification scope

The plan is a collection of question-driven items, not a list of tables and not a list of SQL prompts.

Its job is to translate reusable question patterns into retrieval work for one concrete case.

## Question-Driven Evidence Plan Item

One evidence-plan item centers on one verification question.

That item may require:

- one evidence target
- multiple evidence targets
- one time window
- several linked time interpretations

The question remains the primary unit. Table access is secondary.

### Minimum Conceptual Fields

The contract does not freeze final code schema, but a compliant plan item must cover:

- `plan_item_id`
- `task_id`
- `qualification_item_id`
- `question_id`
- `question_text`
- `priority`
- `evidence_targets`
- `relevant_fields`
- `entity_scope`
- `time_window_or_time_rule`
- `expected_answer_shape`
- `missing_evidence_strategy`
- `conflict_strategy`
- `notes_for_query_generation`

### Evidence Target Semantics

`evidence_targets` describe where evidence is likely to come from, such as:

- `person`
- `employment_registration`
- `unemployment_registration`
- `social_insurance_payment`
- `hardship_certification`
- `company_shareholder`
- `insurance_change_log`

Targets are hints for retrieval planning. They are not equivalent to final SQL source sets.

### Time Semantics

A compliant plan item must carry temporal meaning explicitly when time matters.

Examples:

- latest valid record
- current status at system date
- continuous months before current period
- status during benefit application window
- contradiction between historical and current state

This preserves the Phase 5 principle that time semantics are first-class context.

### Missing-Evidence Strategy

The planning layer must decide what missing evidence means before query generation starts.

Typical strategies include:

- missing means likely not satisfied
- missing means unknown and should be escalated
- missing means search adjacent source
- missing means continue but mark low confidence

This prevents dynamic SQL from inventing semantics during failure handling.

## Trace Model

The trace model is a formal requirement of this contract.

Every plan item must be traceable backward to:

1. its qualification item
2. its reusable question template
3. the policy clause references that justified the template

This makes later explanation and audit possible without storing static SQL as the primary source of meaning.

## Relationship To Existing Static Assets

The current codebase already contains a predecessor in [sql_templates.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/text2sql/sql_templates.py).

That predecessor expresses:

- implicit question patterns hidden behind `rule_id`
- category groupings such as qualification, calculation, and proactive
- direct table-and-SQL coupling

Phase 6 does not discard that history. Instead, it maps it forward:

- `rule_id` becomes a migration-era anchor, not the long-term planning contract
- `RULE_REGISTRY` hints at what questions exist, but not in the correct reusable form
- static rule categories remain useful as reference during migration and regression comparison

In short:

- old system: `rule_id -> SQL -> result`
- new system: `qualification item -> question template -> plan item -> query intent -> SQL -> evidence`

## What Does Not Belong In This Contract

The following are intentionally outside this document:

- final `query_intent` schema
- SQL prompt wording
- auto-repair loop design
- final Evidence v2 field schema
- final debate-agent prompt packaging

Those belong to later Phase 6 and Phase 7 artifacts.

## Development Guidance Value

This document is intended to be executable guidance for later implementation.

A developer should be able to use it to decide:

- what new planning objects need to exist
- how planning differs from semantic-packet construction
- why one plan item is question-centered instead of table-centered
- how to preserve traceability while migrating away from static SQL templates

If a future implementation proposes a design where plan items are only table scans or SQL prompts, that proposal is misaligned with this contract.
