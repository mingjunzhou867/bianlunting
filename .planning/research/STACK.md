# Research: Stack and Delivery Shape for v1.1

**Milestone:** v1.1 Dynamic Evidence Planning Design  
**Focus:** stack choices and delivery boundaries for schema cognition, dictionary loading, evidence planning, and dynamic Text-to-SQL

## Existing Baseline

The current system already has:

- Python backend with FastAPI + SQLAlchemy + MySQL
- Vue frontend for demonstration and history playback
- static SQL-template driven evidence collection
- multi-agent debate orchestration with persistence and retrieval

## Recommended Stack Direction

### 1. Keep the core orchestration inside the current Python backend

Why:

- the existing evidence, agent, and persistence layers already live in Python
- schema introspection, dictionary loading, query generation, and execution all fit naturally beside the current backend
- this keeps future migration cost lower than introducing a second orchestration runtime now

### 2. Treat dictionary files as explicit first-class artifacts

Recommended artifact shape:

- JSON files under `dicts/`
- each file includes field name, natural-language description, value count, and code-to-meaning map
- future generation may be automated, but this milestone only needs the contract, not the generator implementation

### 3. Treat MCP as an integration style, not the first design anchor

Recommended stance:

- define tool contracts first
- make those contracts transport-agnostic
- decide later whether they run in-process, via stdio MCP, or via SSE transport

This avoids over-designing transport before the actual tool interface is stable.

### 4. Preserve the current SQL-template engine as a fallback baseline

Why:

- it is the only grounded and already-tested query path in the project
- the future dynamic engine needs a regression anchor
- replacing the baseline too early would make it harder to judge whether dynamic SQL improved or degraded reliability

## What Not To Add Yet

- do not add a second database just to store cognition graphs
- do not add vector databases or generic agent memory infrastructure yet
- do not commit to a full standalone tool microservice until contracts are frozen
- do not force the frontend into the architecture discussion unless a backend contract depends on it

## Design Implication

The milestone should define:

- stable artifact formats
- stable input/output contracts
- migration boundaries from static templates to dynamic query generation

It should not yet optimize deployment topology.
