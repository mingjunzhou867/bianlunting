import assert from 'node:assert/strict'

import {
  applyStreamEventToSession,
  buildEmptySession,
  normalizeSession,
  resolveSelectedSessionId,
} from '../sessionState.js'

const testBuildEmptySession = () => {
  const session = buildEmptySession('42090219760310000D')

  assert.equal(session.id_card, '42090219760310000D')
  assert.equal(session.view_source, 'live')
  assert.equal(session.history.length, 1)
  assert.deepEqual(session.history[0], { round_num: 0, judgments: [] })
}

const testNormalizeSession = () => {
  const normalized = normalizeSession(
    {
      history: [{ round_num: '1', judgments: null }],
      consensus_rate: '0.6667',
      rounds_taken: '1',
    },
    '42090219760310000D',
  )

  assert.equal(normalized.id_card, '42090219760310000D')
  assert.equal(normalized.history[0].round_num, 1)
  assert.deepEqual(normalized.history[0].judgments, [])
  assert.equal(normalized.consensus_rate, 0.6667)
  assert.equal(normalized.rounds_taken, 1)
  assert.equal(normalized.view_source, 'saved')
}

const testApplyRoundUpdates = () => {
  let session = buildEmptySession('42090219760310000D')

  session = applyStreamEventToSession(session, { event: 'round_start', data: 1 }, session.id_card)
  session = applyStreamEventToSession(
    session,
    {
      event: 'agent_judgment',
      data: {
        debate_round: 1,
        agent_id: 'agent_explorer',
        conclusion: '数据缺失',
      },
    },
    session.id_card,
  )

  assert.equal(session.history.length, 2)
  assert.equal(session.history[1].round_num, 1)
  assert.equal(session.history[1].judgments.length, 1)
  assert.equal(session.history[1].judgments[0].agent_id, 'agent_explorer')
}

const testInvalidRoundNumberFallsBackToRoundZero = () => {
  let session = buildEmptySession('42090219760310000D')

  session = applyStreamEventToSession(
    session,
    {
      event: 'agent_judgment',
      data: {
        debate_round: { bad: true },
        agent_id: 'agent_empirical',
        conclusion: '符合',
      },
    },
    session.id_card,
  )

  assert.equal(session.history[0].judgments.length, 1)
  assert.equal(session.history[0].judgments[0].agent_id, 'agent_empirical')
}

const testApplyFinalEvent = () => {
  const session = applyStreamEventToSession(
    buildEmptySession('42090219760310000D'),
    {
      event: 'debate_final',
      data: {
        session_id: 'sess-D-20260321-001',
        final_conclusion: '不符合',
        final_stance: '反对通过',
        history: [{ round_num: 0, judgments: [] }],
        evidence: [{ rule_id: 'EMP_SYNC' }],
      },
    },
    '42090219760310000D',
  )

  assert.equal(session.session_id, 'sess-D-20260321-001')
  assert.equal(session.id_card, '42090219760310000D')
  assert.equal(session.view_source, 'live')
  assert.equal(session.evidence[0].rule_id, 'EMP_SYNC')
}

const testResolveSelectedSessionId = () => {
  const historyItems = [
    { session_id: 'sess-newest' },
    { session_id: 'sess-older' },
  ]

  assert.equal(
    resolveSelectedSessionId({
      historyItems,
      selectedSessionId: 'sess-older',
      finalSessionId: 'sess-live',
    }),
    'sess-live',
  )
  assert.equal(
    resolveSelectedSessionId({
      historyItems,
      selectedSessionId: 'sess-older',
    }),
    'sess-older',
  )
  assert.equal(
    resolveSelectedSessionId({
      historyItems,
    }),
    'sess-newest',
  )
}

testBuildEmptySession()
testNormalizeSession()
testApplyRoundUpdates()
testInvalidRoundNumberFallsBackToRoundZero()
testApplyFinalEvent()
testResolveSelectedSessionId()

console.log('SESSION_STATE_SMOKE_OK')
