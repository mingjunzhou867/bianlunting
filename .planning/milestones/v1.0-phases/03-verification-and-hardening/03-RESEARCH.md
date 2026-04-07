# Phase 3: Verification and Hardening - Research

**Researched:** 2026-03-23
**Status:** Ready for planning

## Goal

Research the lowest-risk way to harden the new saved-session flow so future changes are more likely to break in tests or docs before they break the live demo.

## Findings

### 1. Backend coverage is strong at the layer level, but the new chain still needs tighter end-to-end guardrails

- [tests/test_debate.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/tests/test_debate.py) already protects the orchestrator's persistence hook behavior for `/api/debate` and `/api/debate_stream`
- [tests/test_persistence_contract.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/tests/test_persistence_contract.py) already locks the serializer shape, the key DDL strings, and the retrieval helper contract
- [tests/test_retrieval_api.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/tests/test_retrieval_api.py) already protects the route-level response semantics
- The remaining gap is confidence that the same saved-session shape still satisfies the frontend history renderer's expectations when fields drift or edge states change

### 2. The frontend now has real state transitions worth testing, but there is still no dedicated frontend test stack

- [frontend/src/App.vue](/c:/Users/afrangry/PycharmProjects/bysj_t2s/frontend/src/App.vue) now owns non-trivial history/list/detail/live coordination logic
- [frontend/package.json](/c:/Users/afrangry/PycharmProjects/bysj_t2s/frontend/package.json) still has only `dev`, `build`, and `preview` scripts, with no test dependencies
- Adding a full Vitest + DOM stack is possible, but it would likely require new packages and expand Phase 3 into test-infrastructure work
- A lower-risk option is to extract the history/live state-shaping logic that matters most into plain JavaScript helpers and cover them with a tiny Node-based smoke test path, while keeping SFC/build validation in place

### 3. Documentation for the new saved-session feature is still fragmented

- [frontend/README.md](/c:/Users/afrangry/PycharmProjects/bysj_t2s/frontend/README.md) is still the default Vue/Vite starter text and does not explain the history UI at all
- The root [README.md](/c:/Users/afrangry/PycharmProjects/bysj_t2s/README.md) does not currently serve as a reliable saved-session setup guide
- There is no dedicated document that ties together:
  - the MySQL schema prerequisite in [data/schema/mysql_ddl.sql](/c:/Users/afrangry/PycharmProjects/bysj_t2s/data/schema/mysql_ddl.sql)
  - the optional reset/mock workflow in [data/mock_data/personas_mock.sql](/c:/Users/afrangry/PycharmProjects/bysj_t2s/data/mock_data/personas_mock.sql)
  - the retrieval endpoints in [api/main.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/api/main.py)
  - the frontend history dependency on saved-session rows

### 4. The two operational risks are already known and should be captured explicitly

- The new retrieval/history flow assumes the updated Phase 1 schema has been applied before the backend and frontend are exercised
- The production frontend build now passes, but Vite still warns about large output chunks
- That warning is worth recording so future maintainers do not mistake it for a surprise regression
- It should only receive a code-level mitigation if a very small, low-risk adjustment is obvious during execution

## Recommendations

### Recommended plan split

- Plan `03-01`: add focused regression coverage for the save/read/render contract, including a minimal automated frontend smoke layer that does not require a broad new testing stack
- Plan `03-02`: add maintainer-facing documentation for schema prerequisites, retrieval usage, local verification, and known operational caveats

### Recommended frontend hardening shape

- Prefer extracting small pure helpers from the new history/live state machine so the critical transitions can be tested without mounting the full app in a browser-like environment
- Keep the automated frontend scope intentionally narrow:
  - blank initial state
  - summary-list to detail selection behavior
  - live-session normalization
  - post-run history refresh/selection behavior

### Recommended documentation shape

- Add one dedicated saved-session guide under `docs/` as the canonical maintainer/integrator reference
- Update the root and frontend README surfaces so they point to that guide instead of leaving discovery to planning files
- Include concrete verification commands for both Python tests and frontend build/smoke checks

## Risks To Watch

- Phase 3 could accidentally become a generic frontend testing phase if the first smoke solution is not kept small
- Documentation work could drift into a full product manual instead of focusing on the saved-session chain and local setup
- A code-level chunk-warning mitigation could create unnecessary churn if it is attempted without a very clear low-risk adjustment

## Planning Implications

- Plans should build on the existing Python `unittest` pattern rather than inventing a new backend test architecture
- Plans should treat lightweight frontend automation as a confidence layer for state transitions, not a full component-test program
- Plans should make the DDL prerequisite and mock-data reset behavior impossible to miss in local setup docs
- Plans should preserve the current product scope: harden the existing feature, do not add new browsing or governance capabilities

---
*Phase: 03-verification-and-hardening*
*Research completed: 2026-03-23*
