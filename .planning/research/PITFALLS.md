# Research: Pitfalls for v1.1

**Milestone:** v1.1 Dynamic Evidence Planning Design  
**Focus:** common failure modes when expanding from a static evidence pipeline to a dynamic evidence-planning system

## Pitfall 1: Scope explosion disguised as architecture

Risk:

- schema cognition
- policy templates
- dynamic SQL
- MCP
- learning loop
- evaluation

can easily become six projects instead of one milestone.

Prevention:

- keep this milestone design-only
- define boundaries and deferrals explicitly
- separate “must define now” from “must implement later”

## Pitfall 2: Mistaking more prompt context for better grounding

Risk:

- injecting full dictionaries or full schema dumps into every prompt increases noise
- larger prompts can still hallucinate while becoming less explainable

Prevention:

- design for targeted, on-demand loading
- define what gets loaded always, conditionally, or never

## Pitfall 3: Replacing the static baseline too early

Risk:

- once the current stable path disappears, the team loses the ability to compare dynamic behavior against known-good behavior

Prevention:

- keep the existing static SQL-template path as baseline during future implementation phases
- treat migration as additive first

## Pitfall 4: Making MCP the product instead of a tool boundary

Risk:

- transport choice starts driving the architecture before the tool contract is even clear

Prevention:

- define `get_dict`, planning, query-generation, and debug contracts first
- decide later whether those contracts are exposed via MCP, local calls, or both

## Pitfall 5: Under-specifying observability

Risk:

- dynamic SQL sounds powerful until the first broken join, wrong code meaning, or time-window error cannot be reconstructed

Prevention:

- require repair traces, execution status, prompt-to-query lineage, and stop conditions in the design

## Pitfall 6: Confusing design deliverables with implementation deliverables

Risk:

- the team starts promising runtime results during a phase that should only define boundaries

Prevention:

- make documentation, contracts, and roadmap quality the success criteria for this milestone
