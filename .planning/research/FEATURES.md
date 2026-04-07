# Research: Feature Shape for v1.1

**Milestone:** v1.1 Dynamic Evidence Planning Design  
**Focus:** which expanded capabilities are table stakes for the next architecture and which are intentionally deferred

## Table Stakes

### Database cognition

The system must know more than table names:

- field meaning
- code-value semantics
- aliases
- key relationships
- time semantics
- business meaning relevant to policy judgment

### On-demand dictionary loading

The system should not inject every code dictionary into every prompt. It needs:

- field-targeted lookup
- partial loading
- prompt references to only the needed dictionary slices

### Evidence planning

Before debate starts, the system should know:

- what must be checked
- which evidence items support each qualification item
- which tables and fields are relevant
- which time windows matter
- what missing evidence means

### Dynamic query generation with repair boundaries

Dynamic Text-to-SQL is only useful if the design also defines:

- query intent rewriting
- error-aware debugging
- observation/logging
- stop conditions
- fallback behavior

### Evidence object upgrade

Evidence must support:

- planning
- execution
- debate
- explanation
- future replay and learning

## Differentiators

### MCP-ready tool interface

Not because MCP itself is the research goal, but because tool boundaries make the architecture more demonstrable and less magical.

### Continuous-learning artifact model

What gets retained later:

- failure types
- fixed SQL patches
- successful repair examples
- prompt rewrites
- reusable check templates

## Anti-Features For This Milestone

- no attempt to design a general-purpose autonomous analyst for every database
- no promise that dynamic SQL fully replaces all static safety nets in one step
- no hard commitment that every future feature must use MCP transport
- no scope expansion into full production governance, large-scale evaluation, or policy-ontology work yet

## Design Implication

This milestone should turn the feature expansion into explicit contracts and deferred lists, so later implementation is guided by scope instead of optimism.
