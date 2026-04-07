# Research: Architecture Direction for v1.1

**Milestone:** v1.1 Dynamic Evidence Planning Design  
**Focus:** how the expanded layers fit the existing system without rewriting `v1.0`

## Recommended Layer Model

### Layer 1: Pre-understanding and evidence preparation

Responsibilities:

- schema cognition
- dictionary resolution
- check-question templates
- evidence-plan generation

Outputs:

- normalized task context
- relevant dictionary references
- evidence plan

### Layer 2: Evidence execution and evidence construction

Responsibilities:

- prompt rewriting
- runtime Text-to-SQL generation
- SQL execution
- auto-debug loop
- evidence object construction

Outputs:

- auditable evidence artifacts
- execution summaries
- repair traces

### Layer 3: Multi-agent debate and judgment

Responsibilities:

- consume evidence artifacts instead of raw database assumptions
- independently judge
- debate
- vote

Outputs:

- debate conclusions
- dissent
- unresolved ambiguity markers

### Layer 4: Post-rule validation and human review

Responsibilities:

- compare debate outcome with rule-engine results later
- detect conflicts
- trigger human-review pathways

Outputs:

- final label or review escalation marker

### Layer 5: Continuous-learning and evaluation support

Responsibilities:

- retain useful repair and failure artifacts
- define evaluation data expectations
- support future regression loops

Outputs:

- reusable memory artifacts for future milestones

## Recommended Migration Shape

Do not replace the existing flow all at once.

Recommended conceptual path:

1. keep current static evidence path as reference behavior
2. define schema cognition and dictionary contracts
3. define evidence-plan and dynamic query contracts
4. define agent/tool boundary
5. implement later behind explicit comparison or fallback gates

## Architectural Boundaries That Matter

- schema cognition is not the same thing as evidence planning
- evidence planning is not the same thing as SQL generation
- dynamic SQL is not trusted by default just because it ran
- debate agents should not become substitute query planners
- MCP transport should not decide system structure before tool semantics are stable

## Design Implication

The most important output of this milestone is boundary clarity, not component count.
