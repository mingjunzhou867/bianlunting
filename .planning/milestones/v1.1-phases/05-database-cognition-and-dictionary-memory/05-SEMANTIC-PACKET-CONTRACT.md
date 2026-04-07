# Phase 5 Task-Trimmed Semantic Packet Contract

## Status

Draft accepted for milestone `v1.1` Phase 5.

This document defines the task-level semantic output of the future database-cognition layer.

It answers a different question from the dictionary contract:

- the dictionary contract defines reusable long-lived semantic assets
- this packet contract defines the task-specific bundle created from those assets for one downstream task

## Purpose

Later tools and agents should not be forced to consume:

- raw schema dumps
- full dictionary corpora
- ad hoc prose-only background notes

They need a task-trimmed semantic bundle that is:

- structured
- inspectable
- minimal by default
- expandable when needed

The semantic packet is that bundle.

## Canonical Input Context

The packet is built for the formal task entrypoint established in Phase 4:

- `person_id`
- `policy_id`
- optional qualification scope

The packet exists to prepare later evidence-planning and query-generation work for that task.

It is not a general-purpose database encyclopedia response.

## Relationship To The Dictionary Contract

The semantic packet consumes reusable assets defined in:

- [05-DICT-CONTRACT.md](/c:/Users/afrangry/PycharmProjects/bysj_t2s/.planning/phases/05-database-cognition-and-dictionary-memory/05-DICT-CONTRACT.md)

That means:

- dictionary files remain the long-lived semantic source
- the packet carries only the task-relevant portion of that knowledge
- packet content should remain traceable back to dictionary assets where applicable

The packet should therefore derive dictionary snippets from fields like:

- `name`
- `source_refs`
- `aliases`
- `notes`
- `values`

but it should not duplicate the full reusable asset by default.

## Design Principles

### 1. Task-level, not global

The packet is assembled for one concrete task.

It should answer:

- what semantic context does this task need right now?

It should not answer:

- everything the system knows about the whole database.

### 2. Sectional, not flat

The packet is organized as sections or cards.

This helps later systems:

- inject only needed sections
- render them for debugging
- extend the format without breaking every consumer

### 3. Structured, not prose-only

The packet may contain short prose explanations, but it should not be a free-form essay.

Later tooling should be able to reliably locate:

- field semantics
- relationship hints
- time semantics
- dictionary excerpts

### 4. Excerpt-first by default

Dictionary knowledge should enter the packet as a relevant excerpt unless there is a good reason to provide the full dictionary.

### 5. Time semantics are first-class

Temporal meaning often changes policy interpretation.

It cannot be buried as a field footnote.

## Canonical Packet Sections

Phase 5 freezes the first-class section set as:

- `task`
- `fields`
- `relations`
- `time_semantics`
- `dict_excerpt`

These names are the current baseline.

Later phases may refine child fields inside each section, but should not casually replace the section model itself.

## Section Contract

### `task`

Purpose:

- identify the task the packet was built for
- state the policy or qualification scope that drove semantic trimming

This section should anchor the rest of the packet.

Expected contents include:

- `person_id`
- `policy_id`
- optional qualification scope
- optionally a concise task summary

This section answers:

- what is this packet for?

### `fields`

Purpose:

- provide field-level semantic cards relevant to the task

Each card should explain the business meaning of fields that downstream evidence planning or query generation may touch.

Examples of useful field-card content:

- table name
- field name
- business meaning
- known aliases
- whether the field is coded or direct-value
- whether special interpretation caveats exist

This section should not become a full schema export.

It should contain only fields relevant to the task and near-future downstream steps.

### `relations`

Purpose:

- provide task-relevant relationship hints between entities, tables, or records

Examples:

- person to hardship certification
- person to social insurance payments
- person to employment registration

This section is not a full ER diagram.

It is a trimmed relationship view that helps later tooling understand:

- where evidence is likely to be found
- how entities relate
- which joins or semantic connections matter

### `time_semantics`

Purpose:

- provide the temporal interpretation rules relevant to the task

This section is mandatory in the conceptual contract, even if a specific task later has little temporal complexity.

Examples of what belongs here:

- validity windows
- counting windows
- current versus historical interpretation
- month-level versus day-level granularity
- effective-date semantics
- lag or sync semantics when business state and system records diverge

Time semantics deserve their own section because the same field may mean something different depending on:

- when it was effective
- what time granularity a policy clause expects
- whether the task is asking about a current state, a history window, or a qualifying period

### `dict_excerpt`

Purpose:

- carry only the task-relevant portions of dictionary knowledge

This section bridges the long-lived dictionary artifacts and the immediate task.

Expected content may include:

- dictionary ID
- why the dictionary matters for this task
- relevant code-value pairs
- referenced aliases
- relevant notes
- trace back to `source_refs` where helpful

This section should be explicit enough that downstream consumers do not need to guess why a code set was included.

## Illustrative Shape

The exact final field names may evolve, but the contract target is roughly:

```json
{
  "task": {
    "person_id": "4209...",
    "policy_id": "POLICY_X",
    "qualification_scope": ["item_a", "item_b"]
  },
  "fields": [
    {
      "table": "hardship_certification",
      "field": "hardship_category",
      "meaning": "困难人员类别代码",
      "aliases": ["困难类别"]
    }
  ],
  "relations": [
    {
      "from": "person.id_card",
      "to": "hardship_certification.id_card",
      "meaning": "人员与困难认定记录关联"
    }
  ],
  "time_semantics": [
    {
      "topic": "validity_window",
      "meaning": "困难认定有效期需要与申请期对齐"
    }
  ],
  "dict_excerpt": [
    {
      "dict_name": "ADC310",
      "source_refs": [
        {
          "table": "hardship_certification",
          "field": "hardship_category"
        }
      ],
      "values": {
        "050": "大龄就业困难人员",
        "993": "离校2年内未就业的高校毕业生"
      },
      "notes": [
        "仅列出当前任务涉及的类别"
      ]
    }
  ]
}
```

This example is contractual in shape, not in exact final syntax.

Its purpose is to show that the packet is:

- structured
- sectional
- traceable
- excerpt-oriented

## Excerpt-First Rule

The default loading rule is:

- include only the dictionary excerpt relevant to the current task

This is now a formal project rule, not a vague preference.

Reasons:

- reduces prompt bloat
- lowers irrelevant semantic noise
- makes downstream reasoning easier to inspect
- keeps attention on the codes actually tied to the current policy or evidence path

Examples of excerpting:

- only include hardship-category codes relevant to the current qualification scope
- only include insurer-status values that matter for the current policy path
- only include employment-form values tied to the evidence items under consideration

## Full-Dictionary Inclusion Is Exceptional

Full dictionary inclusion is allowed, but it is the exception.

Phase 5 does not attempt to define the runtime heuristic in algorithmic detail.

It does define the boundary:

Full inclusion is justified only when one or more of these conditions is true:

- the dictionary is very small and full inclusion is cheaper than excerpt selection
- the task genuinely needs global category comparison instead of a narrow subset
- ambiguity resolution requires showing neighboring values, not just one or two codes
- downstream debugging would become misleading if only a narrow slice were shown

This means the burden of proof is on full-load behavior, not on excerpt behavior.

## Time Semantics As First-Class Context

The packet must include time semantics as its own section because later phases will need to distinguish between at least four kinds of temporal meaning:

1. state validity
2. counting and accumulation windows
3. event chronology
4. granularity interpretation

Examples:

- whether a record is currently valid or historically present
- whether eligibility depends on whole months versus exact dates
- whether a policy cares about when a status began, ended, or changed
- whether system lag means the database record and the real-world state are slightly misaligned

If time semantics are hidden inside field notes, later `plan_evidence` and `text_to_sql` design will be forced to rediscover them inconsistently.

This contract prevents that drift.

## What Does Not Belong In The Packet

The semantic packet should not contain:

- raw SQL
- generated SQL history
- execution traces
- debate conclusions
- full policy prose archives unless strictly task-relevant
- every table and field in the database
- every known dictionary by default

Those belong to later phases or other layers.

## Consumer Expectations

Later consumers of the packet should be able to assume:

- the packet is already task-trimmed
- coded fields have enough semantic grounding to avoid naive guessing
- task-relevant relationships are explicit
- temporal meaning is explicit
- dictionary excerpts are intentional and traceable

They should not assume:

- the packet is a full schema encyclopedia
- every ambiguity has already been solved
- every dictionary is loaded in full

## Debuggability Value

This format is also meant to help humans debug system behavior later.

A maintainer should be able to inspect one packet and understand:

- what task the system believed it was solving
- which fields and relations it thought mattered
- which dictionary values it exposed to downstream tools
- which temporal assumptions it surfaced

That is one of the reasons the packet is sectional instead of hidden inside a large prompt string.

## Development Guidance Value

This contract should be strong enough for future implementation work to begin without reopening the same conceptual debate.

A later developer should be able to answer:

- what sections must the cognition layer emit?
- how should dictionary content enter the packet?
- when is full-dictionary loading acceptable?
- where do temporal semantics live?
- what information must remain outside the packet?

If implementation choices start contradicting those answers, this document should be treated as the baseline authority until a later phase explicitly updates it.
