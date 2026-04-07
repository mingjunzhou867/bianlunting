export const buildEmptySession = (idCard) => ({
  session_id: '',
  id_card: idCard,
  policy_id: '',
  status: 'running',
  source_endpoint: '/api/debate_stream',
  system_traces: [],
  evidence: [],
  history: [{ round_num: 0, judgments: [] }],
  final_conclusion: '',
  final_stance: '',
  consensus_rate: 0,
  is_consensus_reached: false,
  rounds_taken: 0,
  started_at: '',
  completed_at: '',
  view_source: 'live',
})

export const normalizeSession = (payload, fallbackIdCard = '') => ({
  session_id: payload?.session_id ?? '',
  id_card: payload?.id_card ?? fallbackIdCard,
  policy_id: payload?.policy_id ?? '',
  status: payload?.status ?? 'completed',
  source_endpoint: payload?.source_endpoint ?? '',
  system_traces: Array.isArray(payload?.system_traces) ? payload.system_traces : [],
  evidence: Array.isArray(payload?.evidence) ? payload.evidence : [],
  history: Array.isArray(payload?.history)
    ? payload.history.map((round) => ({
      round_num: Number(round?.round_num ?? 0),
      judgments: Array.isArray(round?.judgments) ? round.judgments : [],
    }))
    : [],
  final_conclusion: payload?.final_conclusion ?? '',
  final_stance: payload?.final_stance ?? '',
  consensus_rate: Number(payload?.consensus_rate ?? 0),
  is_consensus_reached: Boolean(payload?.is_consensus_reached),
  rounds_taken: Number(payload?.rounds_taken ?? 0),
  started_at: payload?.started_at ?? '',
  completed_at: payload?.completed_at ?? '',
  view_source: payload?.view_source ?? 'saved',
})

const normalizeRoundNum = (value) => {
  const num = Number(value ?? 0)
  return Number.isFinite(num) && num >= 0 ? Math.floor(num) : 0
}

const ensureRound = (history, roundNum) => {
  const nextHistory = Array.isArray(history)
    ? history.map((round) => ({
      ...round,
      judgments: Array.isArray(round?.judgments) ? [...round.judgments] : [],
    }))
    : []

  while (nextHistory.length <= roundNum) {
    nextHistory.push({ round_num: nextHistory.length, judgments: [] })
  }

  return nextHistory
}

export const applyStreamEventToSession = (session, payload, activeIdCard = '') => {
  if (!session) {
    return session
  }

  const { event, data } = payload ?? {}

  if (event === 'system_trace') {
    return {
      ...session,
      system_traces: [...(session.system_traces || []), data],
    }
  }

  if (event === 'evidence') {
    return {
      ...session,
      evidence: Array.isArray(data) ? data : [],
    }
  }

  if (event === 'round_start') {
    const roundNum = normalizeRoundNum(data)
    return {
      ...session,
      history: ensureRound(session.history, roundNum),
    }
  }

  if (event === 'agent_judgment') {
    const roundNum = normalizeRoundNum(data?.debate_round)
    const nextHistory = ensureRound(session.history, roundNum)
    if (!nextHistory[roundNum]) {
      nextHistory[roundNum] = { round_num: roundNum, judgments: [] }
    }
    nextHistory[roundNum].judgments.push(data)
    return {
      ...session,
      history: nextHistory,
    }
  }

  if (event === 'debate_final') {
    const finalSession = normalizeSession(
      {
        ...data,
        id_card: activeIdCard,
        view_source: 'live',
      },
      activeIdCard,
    )

    // API 推送的 debate_final 事件只含精简结果结构，
    // 需要从当前的 live session 传承完整的过程资产，防止视图 1 被清空
    finalSession.system_traces = session.system_traces || []
    // Preserve live-only stream state because debate_final is intentionally compact.
    finalSession.evidence = (session.evidence && session.evidence.length)
      ? session.evidence
      : (Array.isArray(data?.evidence) ? data.evidence : [])

    return finalSession
  }

  return session
}

export const resolveSelectedSessionId = ({
  historyItems = [],
  selectedSessionId = '',
  finalSessionId = '',
} = {}) => {
  if (finalSessionId) {
    return finalSessionId
  }

  if (selectedSessionId) {
    return selectedSessionId
  }

  return historyItems[0]?.session_id ?? ''
}
