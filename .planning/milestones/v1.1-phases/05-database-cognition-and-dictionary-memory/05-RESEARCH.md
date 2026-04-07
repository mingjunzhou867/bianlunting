# Phase 5: Database Cognition and Dictionary Memory Design - Research

**Researched:** 2026-03-24  
**Status:** Ready for planning

## Goal

Find the safest way to formalize dictionary artifacts and task-level semantic packets without turning Phase 5 into implementation or protocol work.

## Findings

### 1. `ADC310.json` is already the right style anchor for the first dictionary family

The example in [ADC310.json](/c:/Users/afrangry/PycharmProjects/bysj_t2s/dicts/ADC310.json) has three important properties:

- it is readable by humans
- it is already close to prompt/tool consumption shape
- it separates top-level metadata from the code-to-meaning map cleanly enough for extension

Implication:

- Phase 5 should evolve this shape rather than replace it with a more abstract but harder-to-read format

### 2. The key contract split is “dictionary artifact” versus “semantic packet”

If these are not separated, later phases will blur:

- what exists as reusable long-lived knowledge
- what is selected per task
- what is loaded into prompt context right now

Implication:

- one plan should define the reusable dictionary artifact family
- a separate plan should define the task-level semantic packet and loading/excerpt rules

### 3. Naming dictionaries by semantic ID is more stable than naming them by physical field

The user explicitly chose:

- dictionary ID naming like `ADC310.json`
- multi-field reuse via metadata such as `source_refs`

Implication:

- Phase 5 should describe dictionary artifacts as semantic assets first, field-linked assets second

### 4. Time semantics need to be treated as first-class context, not as a late add-on

This is important because policy logic often depends on:

- validity windows
- counting windows
- month/day granularity
- current vs historical interpretation

Implication:

- the semantic packet contract must reserve a real section for time semantics

### 5. The phase remains design-only, so verification should focus on clarity and boundary quality

The most relevant verification questions are:

- can a reader distinguish reusable dictionary knowledge from task-time semantic packaging?
- is excerpt-first loading explicit?
- are time semantics elevated to first-class context?
- is the output actionable for later phases without prematurely deciding implementation details?

## Recommendations

### Recommended plan split

- Plan `05-01`: formalize the ADC310-like enhanced dictionary artifact contract, naming rules, and multi-field reuse model
- Plan `05-02`: formalize the task-level semantic packet contract, excerpt/full-load rules, and time-semantics sectioning

### Recommended verification shape

- confirm the dictionary contract stays human-readable and machine-usable
- confirm packet structure is sectional, not a flat dump
- confirm excerpt-first loading is explicit and full-load is exceptional
- confirm no plan drifts into generator implementation or MCP payload design

## Risks To Watch

- overloading the dictionary contract with too much governance/versioning detail too early
- collapsing semantic packets back into raw schema dumps
- treating `common_values` as mandatory instead of optional support data
- letting Phase 5 drift into Phase 6 by over-designing `plan_evidence` or `text_to_sql` schemas
