# Phase 5: Database Cognition and Dictionary Memory Design - Context

**Phase:** 5  
**Milestone:** v1.1 Dynamic Evidence Planning Design  
**Status:** Executed

## Goal

Define the formal contract for database cognition and dictionary memory so later phases can build evidence planning and dynamic query generation on a grounded semantic base.

This phase is about:

- what a reusable dictionary artifact looks like
- how dictionary files are named and reused
- what belongs in the task-trimmed semantic packet
- how dictionary content is loaded into that packet
- why time semantics must be treated as first-class semantic context

This phase is not about:

- implementing the dictionary generator
- implementing MCP tools
- designing the exact `plan_evidence` schema
- designing the exact `text_to_sql` MCP schema
- writing prompt wording

## Prior Decisions Carried In

From Phase 4:

- the formal task entrypoint is `person_id + policy_id + optional qualification scope`
- the database-cognition layer must emit a task-trimmed semantic packet
- MCP is the formal tool framing, but only `text_to_sql` must run first
- dynamic SQL is the target architecture
- static SQL templates remain only as migration-period baseline

## Reusable Example Artifact

The reference example for the first dictionary-file family is:

- [ADC310.json](/c:/Users/afrangry/PycharmProjects/bysj_t2s/dicts/ADC310.json)

What is valuable about this example:

- it is readable without extra tooling
- it clearly separates metadata from code-to-meaning values
- it is already close to what an agent or tool can consume

## Decisions Locked In During Discussion

### 1. Dictionary files should use an "ADC310 enhanced" shape

The first formal contract should stay close to `ADC310.json`, not replace it with a more abstract but harder-to-read structure.

The baseline top-level shape remains:

- `name`
- `description`
- `total_count`
- `common_values`
- `values`

The first approved enhancement set adds metadata for:

- `source_refs`
- `aliases`
- `notes`

Meaning:

- `source_refs` tells the system which table/field pairs this dictionary serves
- `aliases` gives alternative business names or prompt-facing names
- `notes` captures usage caveats or interpretation reminders

### 2. Dictionary files are named by dictionary ID, not physical field name

The naming scheme stays centered on a stable dictionary identifier like `ADC310`.

The file itself records which fields use it.

This means:

- one dictionary file may serve multiple source fields
- physical database fields do not each need their own duplicated dictionary file
- field-specific differences, if needed later, should be handled by metadata or targeted overrides rather than forced duplication

### 3. One dictionary may serve multiple fields

The design explicitly allows one-to-many reuse through `source_refs`.

This keeps:

- code dictionaries stable at the semantic-domain level
- source-field linkage explicit
- downstream prompt loading simpler than maintaining many duplicated field-specific files

### 4. The task-trimmed semantic packet is task-level and card/section oriented

The semantic packet should not be one flat JSON blob and should not be plain text only.

Its first-class organization is partitioned into sections such as:

- `task`
- `fields`
- `relations`
- `time_semantics`
- `dict_excerpt`

This makes it easier to:

- trim by task
- inject only the needed sections
- extend the packet later without breaking every consumer

### 5. Dictionary content is excerpted by default, not always injected in full

The default loading rule is:

- inject only the task-relevant excerpt
- include the full dictionary only when the dictionary is small or the full set is genuinely needed

This protects against:

- prompt bloat
- irrelevant code injection
- avoidable context noise

### 6. Time semantics are first-class context

Time semantics are not just field footnotes.

They are represented as their own semantic section alongside:

- field semantics
- relation hints
- dictionary excerpts

Examples of what belongs here later:

- effective windows
- counting windows
- month versus day granularity
- current-valid versus historical-reference distinctions

## Executed Contract Decisions

Phase 5 execution turns discussion choices into implementation-guiding contracts.

### Dictionary contract decisions now treated as baseline

- the canonical dictionary artifact remains ADC310-like in top-level readability
- the required readable core is `name`, `description`, `total_count`, `common_values`, and `values`
- the first approved enhancement metadata is `source_refs`, `aliases`, and `notes`
- filenames are based on semantic dictionary ID, not physical field names
- one dictionary file may legitimately serve multiple source fields
- the dictionary artifact is treated as reusable long-lived semantic knowledge
- task-time excerpting behavior is explicitly separated into the semantic packet contract

### Semantic packet decisions now treated as baseline

- the database-cognition layer outputs one task-level semantic packet for `person_id + policy_id + optional qualification scope`
- the packet is sectioned rather than flat
- the first-class sections are `task`, `fields`, `relations`, `time_semantics`, and `dict_excerpt`
- dictionary content enters the packet excerpt-first by default
- full dictionary inclusion is allowed only as an explicit exception
- time semantics are a peer section, not a field footnote

## Formal Artifacts Produced By Phase 5

Phase 5 execution produced two baseline design contracts:

- [05-DICT-CONTRACT.md](/c:/Users/afrangry/PycharmProjects/bysj_t2s/.planning/phases/05-database-cognition-and-dictionary-memory/05-DICT-CONTRACT.md)
- [05-SEMANTIC-PACKET-CONTRACT.md](/c:/Users/afrangry/PycharmProjects/bysj_t2s/.planning/phases/05-database-cognition-and-dictionary-memory/05-SEMANTIC-PACKET-CONTRACT.md)

These two artifacts divide responsibilities clearly:

- the dictionary contract defines reusable semantic assets
- the semantic packet contract defines how those assets are trimmed into one task-level bundle

## Dictionary Contract Direction

The discussion and execution together establish a future dictionary artifact family shaped like:

- semantic-domain ID as filename
- human-readable description
- code/value mapping
- optional common or high-frequency values
- explicit source-field references
- aliases for business and prompt-facing naming
- notes for caveats and interpretation reminders

This keeps the artifact:

- machine-usable
- human-readable
- prompt-friendly

## Semantic Packet Direction

The discussion and execution together establish a future task-level packet shaped like:

- task identity block
- relevant field cards
- relevant relation cards
- time-semantics block
- dictionary excerpt block

The packet should be:

- minimal by default
- expandable on demand
- structured enough to feed tools and agents without becoming a raw schema dump

## Boundary Implications For Later Phases

### For Phase 6

Phase 6 should assume:

- the semantic packet already exists as a task-level structured input
- dictionary excerpts are fed into downstream tools as excerpts first
- time semantics can be referenced as their own block rather than re-derived ad hoc
- the dictionary contract is stable enough that evidence-planning and dynamic-query contracts do not need to rename or reframe dictionary assets

### For Phase 7

Phase 7 should assume:

- debate agents should not receive all dictionary material by default
- prompt-context rules can now distinguish dictionary excerpts from other semantic sections
- the handoff from cognition to tools and agents starts from a structured packet, not a schema dump

## Deferred Questions

These remain intentionally open after Phase 5 execution:

- exact generator workflow that will produce or refresh dictionary files
- exact field-level override mechanism if one source field needs local semantic tweaks
- exact runtime heuristic for deciding excerpt versus full load
- exact child-field schema of each field card, relation card, and time card
- exact transport payloads for future MCP tools that consume the packet

## Execution Summary

Phase 5 is grounded by six concrete choices:

1. dictionary artifacts should follow an ADC310-like enhanced shape
2. filenames should be based on dictionary ID
3. one dictionary may serve multiple fields through `source_refs`
4. semantic packets should be task-level and section/card oriented
5. dictionary content should be excerpted by default, full only when necessary
6. time semantics are first-class context

That means the milestone now has a stable design answer for:

- `SCHEMA-01`
- `SCHEMA-02`
- `SCHEMA-03`

at the contract-definition level.
