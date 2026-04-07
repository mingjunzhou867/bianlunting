# Phase 5 Dictionary Artifact Contract

## Status

Draft accepted for milestone `v1.1` Phase 5.

This document defines the reusable dictionary asset contract for the future database-cognition layer.

It is intentionally design-level:

- it defines what a dictionary artifact must look like
- it does not define the generator script implementation
- it does not define MCP request and response payloads
- it does not define how one specific runtime task slices excerpts out of a dictionary

That downstream task-time packaging belongs in [05-SEMANTIC-PACKET-CONTRACT.md](/c:/Users/afrangry/PycharmProjects/bysj_t2s/.planning/phases/05-database-cognition-and-dictionary-memory/05-SEMANTIC-PACKET-CONTRACT.md).

## Purpose

The project needs a long-lived, human-readable, machine-usable representation of code-value semantics that can be reused across policies, prompts, tools, and later evidence-planning steps.

The immediate motivation is to reduce hallucination in cases where database values are encoded in ways that are not self-explanatory, such as:

- status codes
- category codes
- insurer type codes
- employment form codes
- organization type codes
- values that appear as `0/1`, `101/102`, `M/F`, or other compact business encodings

The artifact contract must therefore preserve readability while being structured enough for later tooling.

## Design Principles

### 1. Stay close to `ADC310.json`

The starting point is the existing dictionary example:

- [ADC310.json](/c:/Users/afrangry/PycharmProjects/bysj_t2s/dicts/ADC310.json)

The project explicitly chooses to evolve that style rather than replace it with an abstract metadata-heavy schema that is harder for humans to read.

### 2. Treat dictionaries as semantic assets, not field dumps

Dictionary files represent domain meaning.

They are not owned by a single database column unless the domain itself is single-use.

This is why filenames are based on dictionary IDs rather than physical field names.

### 3. Keep reusable knowledge separate from task-time packaging

The dictionary artifact stores stable semantic knowledge.

It should not absorb:

- per-request prompt trimming
- full-load versus excerpt runtime decisions
- task-specific policy reasoning
- query-intent planning logic

### 4. Favor explicit linkage over hidden assumptions

If a dictionary serves one or more fields, the artifact should say so directly.

If a dictionary has business aliases or interpretive caveats, the artifact should say so directly.

### 5. Preserve hand-editability

Even if dictionaries are generated later, humans should still be able to inspect and correct them without needing a special viewer.

## Scope

This contract covers:

- filename and identity rules
- required top-level fields
- optional metadata extensions
- source-field linkage rules
- reuse expectations
- authoring and generation expectations

This contract does not yet cover:

- the runtime excerpt algorithm
- field-level override implementation mechanics
- prompt wording
- MCP transport design
- how `text_to_sql` consumes dictionary excerpts

## Canonical File Identity

Each dictionary file is named by semantic dictionary ID.

Examples:

- `ADC310.json`
- `INSURER_STATUS.json`
- `EMPLOYMENT_FORM.json`

The filename should answer:

- what semantic code system is this?

It should not answer:

- which one database field happened to use this code today?

This keeps the artifact stable even if multiple tables or fields point at the same underlying dictionary.

## Canonical Top-Level Shape

The baseline top-level structure remains intentionally close to `ADC310.json`:

```json
{
  "name": "ADC310",
  "description": "就业困难人员类别",
  "total_count": 18,
  "common_values": [],
  "values": {
    "050": "大龄就业困难人员"
  }
}
```

Phase 5 formalizes that this shape is still valid as the readable core.

The first approved enhancement set is:

- `source_refs`
- `aliases`
- `notes`

An enhanced example shape therefore looks like:

```json
{
  "name": "ADC310",
  "description": "就业困难人员类别",
  "total_count": 18,
  "common_values": ["050", "993"],
  "source_refs": [
    {
      "table": "hardship_certification",
      "field": "hardship_category",
      "role": "primary_code_field"
    }
  ],
  "aliases": [
    "困难人员类别",
    "就业困难类别"
  ],
  "notes": [
    "不同政策条款可能只承认其中的部分类别",
    "下游任务不应默认把全量码值注入所有 prompt"
  ],
  "values": {
    "050": "大龄就业困难人员",
    "993": "离校2年内未就业的高校毕业生"
  }
}
```

This example is illustrative.

It defines the contract direction without freezing an implementation-specific generator.

## Field Contract

### `name`

Required.

Meaning:

- the stable semantic dictionary ID

Rules:

- should match the filename stem unless a future migration note explicitly says otherwise
- should be short, stable, and system-usable

### `description`

Required.

Meaning:

- a human-readable description of the semantic domain

Rules:

- should be understandable without opening schema documentation
- should describe the business meaning, not the file source

### `total_count`

Required.

Meaning:

- the number of known values in `values`

Rules:

- should reflect the full dictionary, not just the excerpt used by one task
- may be used later for sanity checks and excerpt/full-load decisions

### `common_values`

Optional but recommended.

Meaning:

- a small list of codes that are disproportionately common or especially worth surfacing

Rules:

- must not be treated as the authoritative full domain
- may be empty
- should remain a convenience field, not a logic field

### `values`

Required.

Meaning:

- the code-to-meaning mapping

Rules:

- keys are code literals as stored or interpreted in the database domain
- values are the human-readable meanings
- readability matters more than compression

`values` is still the center of the artifact.

The rest of the metadata exists to explain how and where the dictionary should be used.

## Approved Enhancement Metadata

### `source_refs`

Optional in theory, expected in practice for generated or maintained artifacts.

Meaning:

- explicit references to the table/field pairs that use this dictionary

Purpose:

- avoids duplicating one semantic dictionary into many per-field files
- makes downstream lookup and tracing explicit
- helps later tooling discover candidate dictionaries for a task

Conceptual shape:

```json
[
  {
    "table": "hardship_certification",
    "field": "hardship_category",
    "role": "primary_code_field"
  }
]
```

Phase 5 does not freeze every possible child key.

It does freeze three expectations:

- each reference identifies a table
- each reference identifies a field
- each reference may optionally describe usage role or context

The system should assume one dictionary may have multiple `source_refs`.

### `aliases`

Optional.

Meaning:

- alternative names by which humans, prompts, business documents, or future tools may refer to the same dictionary domain

Purpose:

- supports prompt-facing wording without renaming the canonical dictionary asset
- helps map colloquial names to stable IDs

Examples:

- business shorthand
- policy wording variants
- interface-facing labels

Aliases should not become a hidden replacement for `name`.

`name` stays canonical.

### `notes`

Optional.

Meaning:

- short semantic caveats, interpretation reminders, or usage warnings that matter across tasks

Purpose:

- preserves low-volume but high-value domain knowledge
- helps downstream consumers avoid naive misuse of the code set

Good note examples:

- a code set may be broader than one policy cares about
- some values are often confused with similar business concepts
- later phases should prefer excerpting by relevance instead of full injection

Bad note examples:

- task-specific reasoning for one person
- SQL snippets
- generator implementation instructions

## Reuse Model

One dictionary file may serve multiple source fields.

This is the default expectation, not an exception.

Why this matters:

- semantic meaning often outlives one physical column layout
- duplicated per-field dictionaries create drift risk
- downstream tools benefit from a stable semantic anchor

The preferred model is:

1. define the dictionary once at the semantic-domain level
2. link all known source fields through `source_refs`
3. introduce targeted override behavior later only if a real mismatch appears

Phase 5 deliberately does not design the override mechanism yet.

It only records the rule that duplication is not the default answer.

## Relation To Physical Schema

The dictionary contract complements schema understanding.

It does not replace schema metadata.

Schema metadata answers questions like:

- what table is this field in?
- what datatype does it have?
- how does it join to other entities?

Dictionary metadata answers questions like:

- what do the encoded values mean?
- which fields reuse the same code domain?
- what business aliases or caveats should a downstream consumer know?

This distinction is important because later phases will combine both into one task-trimmed semantic packet.

## Generation and Maintenance Expectations

Phase 5 is not implementing the generator, but it does define the intended maintenance stance.

The project expects that future dictionary assets can be:

- created manually for early coverage
- generated or refreshed from database metadata and business references later
- reviewed by humans before being treated as trusted semantic assets

The contract therefore favors:

- stable field names
- readable JSON
- explicit metadata
- minimal hidden behavior

## What Does Not Belong Here

The dictionary artifact must not turn into:

- a full schema dump
- a policy clause repository
- a prompt template
- an evidence-plan item
- a SQL library
- a runtime trace object

If content answers:

- why this specific task needs only codes `050` and `993`

then it belongs later in the semantic packet, not here.

If content answers:

- how to query records that contain these codes

then it belongs later in evidence-planning or dynamic-query contracts, not here.

## Authoring Checklist

A dictionary artifact is acceptable for this project when:

- the file is named by semantic dictionary ID
- `name`, `description`, `total_count`, and `values` are present
- the artifact remains readable without custom tooling
- `source_refs` explain where the dictionary is used
- `aliases` and `notes` add semantic help rather than noise
- the file represents reusable long-lived knowledge rather than task-time prompt packaging

## Development Guidance Value

This contract is intended to be implementation-guiding, not merely inspirational.

A later developer should be able to use it to answer:

- how should new dictionary files be named?
- what must every dictionary file contain?
- how should one dictionary serve multiple fields?
- where should business aliases and caveats live?
- what information should not be mixed into the dictionary itself?

If a future design or implementation choice conflicts with those answers, this contract should be treated as the baseline decision until a later phase explicitly revises it.
