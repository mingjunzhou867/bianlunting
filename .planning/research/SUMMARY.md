# Research Summary: v1.1 Dynamic Evidence Planning Design

**Researched:** 2026-03-24  
**Status:** Ready for requirements and roadmap

## Stack Additions

- no new runtime stack is required yet; the current Python backend remains the right design anchor
- dictionary artifacts under `dicts/` should become first-class inputs to future planning and query-generation flows
- MCP should remain an optional transport for tool contracts, not the first architectural commitment

## Feature Table Stakes

- database cognition that covers schema structure plus code-value meaning
- on-demand dictionary loading instead of full prompt stuffing
- pre-debate evidence planning
- dynamic Text-to-SQL with rewrite, repair, observability, and stop rules
- upgraded evidence objects with provenance and repair history

## Architecture Direction

- preserve the shipped `v1.0` runtime as baseline behavior
- define five layers with explicit boundaries
- keep schema cognition, planning, SQL generation, and debate as distinct responsibilities

## Watch Out For

- scope explosion
- prompt bloat from loading too much dictionary data
- replacing the static SQL baseline too early
- overcommitting to MCP transport before tool semantics are defined
- weak observability around dynamic SQL

## Milestone Implication

`v1.1` should be a design milestone that produces stable contracts and an implementation-ready phase blueprint, not a premature coding milestone.
