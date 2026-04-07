# Phase 3: Verification and Hardening - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase hardens the now end-to-end save/read/view flow. It is limited to regression coverage, contract-drift protection, and operational/developer documentation around completed-session persistence, retrieval APIs, and the new history UI. It does not add new product capabilities, auth, retention policy, or broader redesign work.

</domain>

<decisions>
## Implementation Decisions

### Verification scope
- Phase 3 should focus on the completed-session save/read/view chain rather than reopening unrelated legacy feature areas
- Verification should explicitly cover the user-visible journeys that now matter end to end: successful save, retrieval list/detail, and frontend history viewing over saved sessions
- Existing evidence-collector and agent tests remain useful background coverage, but Phase 3 should prioritize regressions introduced by the new persistence/retrieval/history work
- The highest-value target is cross-layer confidence that one completed debate can be saved, read back, and shown consistently without contract drift

### Frontend hardening depth
- Phase 3 should add at least lightweight automated confidence over the new history UI rather than relying on build-only validation forever
- The first frontend test layer should stay minimal and smoke-oriented, not a broad UI testing expansion
- Frontend hardening should focus on the key transitions already introduced in Phase 2.1: blank state, history selection, live run state, and post-run history refresh behavior
- This phase should avoid turning into a full frontend testing infrastructure project unless a very small setup is enough to lock the new flows

### Documentation audience and shape
- Documentation should primarily help future maintainers and local integrators understand the saved-session model and how to run the feature successfully
- The first documentation pass should include both backend contract guidance and practical local setup/verification notes
- Documentation should explain the storage model, the retrieval entry points, the frontend history dependency on backend schema/data, and the expected developer verification commands
- Planning summaries alone are not sufficient as the main documentation surface for this phase

### Guardrail style
- Phase 3 should prefer guardrails that catch contract drift early: focused tests, schema/runtime alignment checks, and clear local verification instructions
- Operational guardrails should stay lightweight and explicit rather than introducing heavy new runtime enforcement layers
- The current known warning about large frontend build chunks should be documented and, if practical, lightly mitigated, but it should not expand into a major performance phase
- The already-known MySQL DDL dependency should be documented clearly so future local setups do not fail silently

### Claude's Discretion
- Whether frontend smoke coverage lands as a tiny added test harness or another equally small automated check
- Exact document split between README-style usage notes and deeper architecture/contract notes
- Whether the large-chunk warning is only documented or also receives a small low-risk mitigation inside this phase

</decisions>

<specifics>
## Specific Ideas

- The most important hardening story is now "save -> retrieve -> render" rather than any one layer in isolation
- Good Phase 3 verification should make it hard for future schema tweaks or API-shape changes to silently break the new history UI
- Documentation should make it obvious that running the frontend history feature assumes the updated MySQL schema and saved-session mock/real data exist
- Frontend hardening should stay intentionally narrow: prove the new history UX is stable without exploding scope

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- [tests/test_debate.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/tests/test_debate.py): already covers debate orchestration and persistence-hook behavior for successful and failed saves
- [tests/test_persistence_contract.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/tests/test_persistence_contract.py): already locks key schema/runtime and retrieval-contract expectations
- [tests/test_retrieval_api.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/tests/test_retrieval_api.py): already covers the backend retrieval route contract
- [frontend/src/App.vue](/c:/Users/afrangry/PycharmProjects/bysj_t2s/frontend/src/App.vue): now contains the combined live/history state machine that Phase 3 needs to protect

### Established Patterns
- Backend regression coverage currently uses Python `unittest` with focused mocking rather than heavyweight end-to-end infrastructure
- Frontend validation currently has a successful production build path but no dedicated automated test stack yet
- Planning summaries already exist per plan, so Phase 3 documentation should complement them rather than duplicating them

### Integration Points
- Phase 3 can extend backend tests without changing the core persistence architecture
- Frontend hardening should target the new history-view interactions introduced in [App.vue](/c:/Users/afrangry/PycharmProjects/bysj_t2s/frontend/src/App.vue), [DebateSessionView.vue](/c:/Users/afrangry/PycharmProjects/bysj_t2s/frontend/src/components/DebateSessionView.vue), and [HistorySessionList.vue](/c:/Users/afrangry/PycharmProjects/bysj_t2s/frontend/src/components/HistorySessionList.vue)
- Documentation should likely reference [data/schema/mysql_ddl.sql](/c:/Users/afrangry/PycharmProjects/bysj_t2s/data/schema/mysql_ddl.sql), [data/mock_data/personas_mock.sql](/c:/Users/afrangry/PycharmProjects/bysj_t2s/data/mock_data/personas_mock.sql), [api/main.py](/c:/Users/afrangry/PycharmProjects/bysj_t2s/api/main.py), and the frontend entry points together

</code_context>

<deferred>
## Deferred Ideas

- Authentication, authorization, or audit policy for viewing saved sessions
- Data retention and cleanup workflows
- Broad frontend performance optimization beyond small low-risk warning cleanup
- New history browsing features such as global recent sessions, filters, or comparison views

</deferred>

---
*Phase: 03-verification-and-hardening*
*Context gathered: 2026-03-23*
