<script setup>
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import DebateSessionView from './components/DebateSessionView.vue'
import HistorySessionList from './components/HistorySessionList.vue'
import ManualSupplementPanel from './components/ManualSupplementPanel.vue'
import {
  applyStreamEventToSession,
  buildEmptySession,
  normalizeSession,
  resolveSelectedSessionId,
} from './sessionState.js'

document.documentElement.classList.remove('dark')

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api'
const HISTORY_URL = `${API_BASE}/debates`
const STREAM_URL = `${API_BASE}/debate_stream`
const INTENT_URL = `${API_BASE}/intent`

const idCardInput = ref('')
const userQueryInput = ref('')
const activeIdCard = ref('')
const historyItems = ref([])
const selectedSessionId = ref('')
const activeSession = ref(null)

const activeTab = ref('input')

const historyLoading = ref(false)
const sessionLoading = ref(false)
const liveLoading = ref(false)
const intentLoading = ref(false)
const abortController = ref(null)

const historyError = ref('')
const sessionError = ref('')
const liveError = ref('')
const streamDebateOnly = ref(false)

const intentResult = ref(null)
const selectedPolicyId = ref('')
const policyConditions = ref([])
const policyConditionsMeta = ref(null)
const conditionsLoading = ref(false)
const ID_CARD_REGEX = /^\d{17}[\dXx]$/
const moduleGavelUrl = '/image/gov/module-gavel.png'

const personas = [
  { id: '42090219800101000A', tag: 'A 张完美', type: 'success' },
  { id: '42090219850505000B', tag: 'B 李老板', type: 'danger' },
  { id: '42090219760310000D', tag: 'D 赵争议', type: 'warning' },
  { id: '42090219780815000E', tag: 'E 陈灰色', type: 'warning' },
  { id: '42090219700505000I', tag: 'I 钱幽灵', type: 'info' },
]

const buildSupplementId = () => `supp_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`

const manualStanceLabel = (stance) => {
  if (stance === 'support') return '支持该条款'
  if (stance === 'refute') return '反驳该条款'
  return '人工核验'
}

const getClauseById = (session, clauseId) => {
  const rows = Array.isArray(session?.adjudication_report?.clause_results)
    ? session.adjudication_report.clause_results
    : []
  return rows.find((row) => row?.clause_id === clauseId) || null
}

const toManualEvidenceItem = (session, supplement) => {
  const evidenceId = supplement.evidence_id || `manual_${supplement.supplement_id}`
  const stance = supplement.stance || 'support'
  const stanceLabel = manualStanceLabel(stance)
  const supportsConclusion = stance === 'refute' ? false : true
  return {
    evidence_id: evidenceId,
    rule_id: supplement.clause_id,
    target_id_card: session.id_card,
    target: `人工核验证据(${supplement.clause_id})`,
    category: 'manual_supplement',
    sql: '-- manual supplement evidence',
    result_raw: [
      {
        source: 'manual',
        supplement_id: supplement.supplement_id,
        clause_id: supplement.clause_id,
        stance,
        manual_stance: stance,
        manual_verified: true,
      },
    ],
    result_summary: `[人工核验][${stanceLabel}] ${supplement.detail}`,
    supports_conclusion: supportsConclusion,
    confidence: 1.0,
    exec_status: 'success',
    diagnostic_code: 'ok',
    diagnostic_label: '人工核验补证',
    diagnostic_detail: `人工核验补证（${stanceLabel}，高优先级）`,
    diagnostic_hint: '人工核验补证优先级最高，将覆盖同条款系统证据',
    manual_verified: true,
    manual_stance: stance,
    created_at: supplement.submitted_at || new Date().toISOString(),
  }
}

const handleQuickTest = (id) => {
  if (!liveLoading.value) {
    idCardInput.value = id
  }
}

const idCardState = computed(() => {
  const value = idCardInput.value.trim()
  if (!value) return 'empty'
  return ID_CARD_REGEX.test(value) ? 'valid' : 'invalid'
})

const groupedConditions = computed(() => {
  const groups = { necessary: [], sufficient: [], exclusion: [] }
  ;(policyConditions.value || []).forEach((item) => {
    const key = String(item?.category || '')
    if (key.includes('排除')) groups.exclusion.push(item)
    else if (key.includes('必须') || key.includes('基础')) groups.necessary.push(item)
    else groups.sufficient.push(item)
  })
  return groups
})

const policySummary = (reason = '') => {
  const text = String(reason || '').trim()
  if (!text) return ['暂无摘要', '请以规则明细为准']
  if (text.length <= 30) return [text, '请结合条件清单确认']
  return [text.slice(0, 30), text.slice(30, 60) || '请结合条件清单确认']
}

const conditionStateClass = (cond) => {
  const tag = String(cond?.tag_type || '')
  if (tag === 'success') return 'state-dot--ok'
  if (tag === 'danger') return 'state-dot--error'
  if (tag === 'warning') return 'state-dot--warn'
  return 'state-dot--pending'
}

const conditionStatusMeta = (cond) => {
  const tag = String(cond?.tag_type || '')
  if (tag === 'success') return { type: 'info', label: '待取证' }
  if (tag === 'danger') return { type: 'warning', label: '重点核查' }
  if (tag === 'warning') return { type: 'warning', label: '需评议' }
  return { type: 'info', label: '待取证' }
}

const conditionCategoryTagType = (cond) => {
  const category = String(cond?.category || '')
  if (category.includes('排除')) return 'danger'
  if (category.includes('推断') || category.includes('灵活') || category.includes('额度')) return 'warning'
  return 'info'
}

const conditionBasisText = (cond) =>
  cond?.pass_condition || cond?.check_logic || cond?.description || '以政策结构化规则为准'

const currentViewLabel = computed(() => {
  if (activeTab.value === 'input') return '视图一：用户输入'
  if (activeTab.value === 'cognition') return '视图二：取证规划中心'
  if (activeTab.value === 'tribunal') return '视图三：多智能体辩论庭'
  if (activeTab.value === 'verdict') return '视图四：裁决结果与补证复核'
  return '历史会话'
})

const flowCompleted = computed(() => {
  const session = activeSession.value
  return Boolean(session?.final_conclusion) || Boolean(session?.completed_at) || session?.status === 'completed'
})

const overallFlowStep = computed(() => {
  const session = activeSession.value
  const hasFinal = Boolean(session?.final_conclusion) || Boolean(session?.completed_at) || session?.status === 'completed'
  if (hasFinal) return 4

  const history = Array.isArray(session?.history) ? session.history : []
  const hasRound = history.some((round) => Number(round?.round_num ?? 0) >= 1)
  if (hasRound) return 3

  const traceCount = Array.isArray(session?.system_traces) ? session.system_traces.length : 0
  const evidenceCount = Array.isArray(session?.evidence) ? session.evidence.length : 0
  const hasRetrievalAssets = traceCount > 0 || evidenceCount > 0
  if (hasRetrievalAssets || liveLoading.value) return 2

  return 1
})

const finalVerdictLabel = computed(() => {
  const session = activeSession.value
  const conclusion = String(session?.final_conclusion || '')
  const stance = String(session?.final_stance || '').toLowerCase()
  if (!conclusion && !stance) return ''
  const negativeHit = /不符合|不满足|驳回|不通过|拒绝/.test(conclusion) || stance.includes('refute') || stance.includes('reject')
  if (negativeHit) return '不符合'
  return '符合'
})

const finalVerdictClass = computed(() => {
  if (!finalVerdictLabel.value) return ''
  return finalVerdictLabel.value === '符合' ? 'flow-verdict--pass' : 'flow-verdict--fail'
})

const gotoFlowStep = (step) => {
  if (step === 1) activeTab.value = 'input'
  else if (step === 2) activeTab.value = 'cognition'
  else if (step === 3) activeTab.value = 'tribunal'
  else if (step === 4) activeTab.value = 'verdict'
}

const retrievalProgressPct = computed(() => {
  const session = activeSession.value
  if (!session) return 0
  if (overallFlowStep.value > 2) return 100
  if (overallFlowStep.value < 2) return 0

  const traceCount = Array.isArray(session.system_traces) ? session.system_traces.length : 0
  const evidenceCount = Array.isArray(session.evidence) ? session.evidence.length : 0
  if (!liveLoading.value) return 100

  // 没有显式检索进度事件时，用“可观测资产”估算推进程度。
  // 进入评判阶段会自动变为 100（见 overallFlowStep > 2 分支）。
  const fromTraces = Math.min(55, traceCount * 6)
  const fromEvidence = evidenceCount > 0 ? Math.min(40, 20 + evidenceCount * 6) : 0
  return Math.min(95, Math.max(8, fromTraces + fromEvidence))
})

const currentDebateRound = computed(() => {
  const history = Array.isArray(activeSession.value?.history) ? activeSession.value.history : []
  let maxRound = 0
  history.forEach((round) => {
    const num = Number(round?.round_num ?? 0)
    if (Number.isFinite(num)) {
      maxRound = Math.max(maxRound, Math.floor(num))
    }
  })
  return Math.max(1, maxRound)
})

const globalViewSteps = [
  { key: 'input' },
  { key: 'cognition' },
  { key: 'tribunal' },
  { key: 'verdict' },
]

const globalViewIndex = computed(() => {
  return Math.min(globalViewSteps.length - 1, Math.max(0, overallFlowStep.value - 1))
})

const globalProgressPct = computed(() => {
  if (globalViewSteps.length <= 1) return 0
  return (globalViewIndex.value / (globalViewSteps.length - 1)) * 100
})

const faqStage = ref('input')
const faqItems = [
  { stage: 'input', q: '为什么要先做身份录入与政策匹配？', a: '先锁定政策后再取证，能显著减少误检和重复执行。' },
  { stage: 'input', q: 'Top-3 政策该怎么选？', a: '优先选择匹配度高且匹配原因最贴近当前诉求的政策。' },
  { stage: 'input', q: '身份证号校验通过但仍无法进入下一步？', a: '请确认需求描述不为空，并点击“识别意图”完成政策候选加载。' },
  { stage: 'input', q: '政策匹配分数很接近时怎么办？', a: '优先查看匹配原因与业务场景是否一致，再结合条件清单做最终选择。' },
  { stage: 'retrieval', q: '检索进度一直偏慢怎么办？', a: '通常是数据量大或查询复杂，先核对身份证号与政策是否选对。' },
  { stage: 'retrieval', q: '条件清单为空是什么原因？', a: '可能未完成政策选择，或当前政策还没有结构化条件配置。' },
  { stage: 'retrieval', q: '检索进度到 100% 后下一步没切换？', a: '一般会在证据与系统轨迹就绪后自动进入评判，请稍等几秒刷新状态。' },
  { stage: 'retrieval', q: '看到“暂无结构化条件”还可以继续吗？', a: '可以继续，但建议先确认政策版本是否完整，避免结论依据不足。' },
  { stage: 'judge', q: '为什么会进入多轮评判？', a: '当智能体结论分歧较大时，系统会继续追加轮次来收敛共识。' },
  { stage: 'judge', q: '第几轮算结束？', a: '达到最大轮次或共识阈值后自动结束，并进入结果生成。' },
  { stage: 'judge', q: '轮次增加会影响最终结论吗？', a: '会，新增轮次会引入更多证据交叉验证，用于提升结论稳定性。' },
  { stage: 'judge', q: '评判阶段可以手动终止吗？', a: '可以，点击顶部“停止分析”后会保留当前已生成结果用于后续复核。' },
  { stage: 'result', q: '“符合/不符合”由什么决定？', a: '由最终裁决结论综合证据一致性、规则命中和人工补证结果得出。' },
  { stage: 'result', q: '结果出来后还能复核吗？', a: '可以，在裁决页可继续补证并发起复核流程。' },
  { stage: 'result', q: '为什么结果是“不符合”但部分条件看起来通过？', a: '存在排除条件命中或关键必要条件失败时，最终结论仍会判为不符合。' },
  { stage: 'result', q: '审核结论可以导出给外部系统吗？', a: '可以按会话记录留痕，后续可由接口或审计视图导出结构化结果。' },
]

const faqVisibleItems = computed(() => {
  return faqItems.filter((item) => item.stage === faqStage.value)
})

const readJson = async (response) => {
  try {
    return await response.json()
  } catch {
    return null
  }
}

const fetchConditions = async (policyId) => {
  if (!policyId) {
    policyConditions.value = []
    policyConditionsMeta.value = null
    return
  }
  conditionsLoading.value = true
  try {
    const res = await fetch(`${API_BASE}/policy/${policyId}/conditions`)
    const payload = await readJson(res)
    if (res.ok && payload?.status === 'success') {
      policyConditions.value = payload.data.conditions || []
      policyConditionsMeta.value = {
        policy_name: payload.data.policy_name,
        policy_type: payload.data.policy_type,
        description: payload.data.description,
      }
    } else {
      policyConditions.value = []
      policyConditionsMeta.value = null
    }
  } catch {
    policyConditions.value = []
    policyConditionsMeta.value = null
  } finally {
    conditionsLoading.value = false
  }
}

watch(selectedPolicyId, (newId) => {
  fetchConditions(newId)
})

const runIntentRecognition = async () => {
  const query = userQueryInput.value.trim()
  if (!query) {
    ElMessage.warning('请输入需求描述。')
    return
  }
  intentLoading.value = true
  intentResult.value = null
  selectedPolicyId.value = ''
  policyConditions.value = []
  policyConditionsMeta.value = null

  try {
    const res = await fetch(INTENT_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_query: query }),
    })
    const payload = await readJson(res)
    if (!res.ok || payload?.status !== 'success') {
      throw new Error(payload?.detail || '意图识别失败')
    }
    intentResult.value = payload.data
    const candidates = payload.data.candidate_policies || []
    if (candidates.length > 0) {
      selectedPolicyId.value = candidates[0].policy_id
    }
  } catch (error) {
    ElMessage.error(error.message || '意图识别失败')
  } finally {
    intentLoading.value = false
  }
}

const handleConfirmAndStart = () => {
  const idCard = idCardInput.value.trim()
  if (!idCard) {
    ElMessage.warning('请输入身份证号码。')
    return
  }
  if (!selectedPolicyId.value) {
    ElMessage.warning('请先选择一个政策。')
    return
  }
  ElMessage.success('政策已确认，正在启动分析...')
  startStreamDebate()
}

const fetchHistory = async () => {
  historyLoading.value = true
  historyError.value = ''

  try {
    const response = await fetch(HISTORY_URL)
    const payload = await readJson(response)

    if (!response.ok || payload?.status !== 'success') {
      throw new Error(payload?.detail || `历史会话加载失败 (${response.status})`)
    }

    historyItems.value = Array.isArray(payload?.data?.history) ? payload.data.history : []
  } catch (error) {
    historyItems.value = []
    historyError.value = error.message || '历史会话加载失败'
  } finally {
    historyLoading.value = false
  }
}

const selectHistorySession = async (sessionId) => {
  if (!sessionId) return
  if (liveLoading.value) {
    ElMessage.warning('实时分析进行中，请等待当前流程完成后再切换历史会话。')
    return
  }

  activeTab.value = 'tribunal'

  const previousSelectedSessionId = selectedSessionId.value
  selectedSessionId.value = sessionId
  sessionLoading.value = true
  sessionError.value = ''

  try {
    const response = await fetch(`${HISTORY_URL}/${encodeURIComponent(sessionId)}`)
    const payload = await readJson(response)

    if (!response.ok || payload?.status !== 'success') {
      throw new Error(payload?.detail || `历史详情加载失败 (${response.status})`)
    }

    activeSession.value = normalizeSession(payload.data, activeIdCard.value)
    activeIdCard.value = activeSession.value.id_card
    idCardInput.value = activeSession.value.id_card
  } catch (error) {
    selectedSessionId.value = previousSelectedSessionId
    sessionError.value = error.message || '历史详情加载失败'
    ElMessage.error(sessionError.value)
  } finally {
    sessionLoading.value = false
  }
}

const syncHistoryAfterLive = async (sessionId) => {
  await fetchHistory()
  selectedSessionId.value = resolveSelectedSessionId({
    historyItems: historyItems.value,
    selectedSessionId: selectedSessionId.value,
    finalSessionId: sessionId,
  })
}

const handleStreamEvent = ({ event, data }) => {
  if (!activeSession.value) return
  if (streamDebateOnly.value && (event === 'system_trace' || event === 'evidence')) return

  activeSession.value = applyStreamEventToSession(activeSession.value, { event, data }, activeIdCard.value)

  if (event === 'round_start') {
    activeTab.value = 'tribunal'
  }

  if (event === 'debate_final') {
    selectedSessionId.value = data?.session_id ?? ''
  }
}

const stopAnalysis = () => {
  if (abortController.value) {
    abortController.value.abort()
    abortController.value = null
  }
}

const startStreamDebate = async (options = {}) => {
  const idCard = (options.idCard ?? idCardInput.value).trim()
  const requestedPolicyId = options.policyId ?? selectedPolicyId.value
  const reusedEvidence = Array.isArray(options.evidence) ? options.evidence : null
  const manualSupplements = Array.isArray(options.manualSupplements) ? options.manualSupplements : []
  const reviewMode = options.reviewMode ?? ''
  const debateOnly = Boolean(options.debateOnly)
  const startTab = options.startTab ?? 'cognition'

  activeTab.value = startTab
  activeIdCard.value = idCard
  historyItems.value = []
  selectedSessionId.value = ''
  activeSession.value = {
    ...buildEmptySession(idCard),
    policy_id: requestedPolicyId || '',
    evidence: reusedEvidence ?? [],
    manual_supplements: manualSupplements,
  }
  historyError.value = ''
  sessionError.value = ''
  liveError.value = ''
  liveLoading.value = true
  streamDebateOnly.value = debateOnly

  abortController.value = new AbortController()
  void fetchHistory()

  const requestBody = { id_card: idCard }
  if (requestedPolicyId) {
    requestBody.confirmed_policy_id = requestedPolicyId
  } else if (userQueryInput.value.trim()) {
    requestBody.user_query = userQueryInput.value.trim()
  }
  if (reusedEvidence && reusedEvidence.length > 0) {
    requestBody.reuse_evidence = true
    requestBody.evidence = reusedEvidence
    if (manualSupplements.length > 0) {
      requestBody.manual_supplements = manualSupplements
    }
  }

  let finalSessionId = ''

  try {
    const response = await fetch(STREAM_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody),
      signal: abortController.value.signal,
    })

    const contentType = response.headers.get('content-type') || ''
    if (contentType.includes('application/json')) {
      const payload = await readJson(response)
      if (payload?.status === 'need_confirmation') {
        intentResult.value = payload.data
        const candidates = payload.data?.candidate_policies || []
        if (candidates.length > 0) {
          selectedPolicyId.value = candidates[0].policy_id
        }
        activeTab.value = 'input'
        ElMessage.info('请在“用户输入”视图中选择政策后重新提交。')
        return
      }
    }

    if (!response.ok || !response.body) {
      const payload = await readJson(response)
      throw new Error(payload?.detail || `实时分析启动失败 (${response.status})`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    while (true) {
      const { value, done } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      let boundary = buffer.indexOf('\n\n')

      while (boundary !== -1) {
        const chunk = buffer.slice(0, boundary)
        buffer = buffer.slice(boundary + 2)

        if (chunk.startsWith('data: ')) {
          let parsed = null
          try {
            parsed = JSON.parse(chunk.slice(6))
          } catch {
            // malformed chunk
            console.error('Malformed SSE chunk:', chunk)
          }

          if (parsed) {
            try {
              handleStreamEvent(parsed)
              if (parsed?.event === 'debate_final') {
                finalSessionId = parsed?.data?.session_id ?? ''
              }
            } catch (error) {
              console.error('Failed to apply stream event:', parsed, error)
            }
          }
        }

        boundary = buffer.indexOf('\n\n')
      }
    }

    await syncHistoryAfterLive(finalSessionId)
    if (reviewMode === 'manual_supplement') {
      ElMessage.success('补证复核已完成，已更新采纳结果。')
    } else {
      ElMessage.success('实时分析完成，历史会话已刷新。')
    }
  } catch (error) {
    if (error.name === 'AbortError') {
      ElMessage.info('已停止实时分析，当前页面内容已保留。')
    } else {
      liveError.value = error.message || '实时分析失败'
      ElMessage.error(liveError.value)
    }
  } finally {
    abortController.value = null
    liveLoading.value = false
    streamDebateOnly.value = false
  }
}

const handleSubmitSupplement = (payload) => {
  if (!activeSession.value) return

  const clauseId = String(payload?.clause_id || '').trim()
  const detail = String(payload?.detail || '').trim()
  if (!clauseId || !detail) {
    ElMessage.warning('请先选择条款并填写补证说明。')
    return
  }

  const clause = getClauseById(activeSession.value, clauseId)
  if (!clause) {
    ElMessage.warning('未找到对应条款，无法提交补证。')
    return
  }

  const currentSupplements = Array.isArray(activeSession.value.manual_supplements)
    ? activeSession.value.manual_supplements
    : []
  const supplement = {
    supplement_id: buildSupplementId(),
    clause_id: clauseId,
    clause_text: payload?.clause_text || clause?.clause_text || '',
    detail,
    stance: payload?.stance || 'support',
    baseline_status: payload?.baseline_status || clause?.semantic_display_label || clause?.status || '',
    baseline_effect: payload?.baseline_effect || clause?.semantic_decision_effect || '',
    status: 'pending_review',
    submitted_at: new Date().toISOString(),
  }

  activeSession.value = {
    ...activeSession.value,
    manual_supplements: [...currentSupplements, supplement],
  }
  ElMessage.success('补证已提交，状态已标记为“已提交待复核”。')
}

const buildSupplementReviewPayload = (session) => {
  const currentSupplements = Array.isArray(session?.manual_supplements) ? session.manual_supplements : []
  const normalizedSupplements = currentSupplements.map((item) => (
    item?.supplement_id
      ? item
      : { ...item, supplement_id: buildSupplementId() }
  ))
  const pendingSupplements = normalizedSupplements.filter((item) => item?.status === 'pending_review')

  const latestPendingByClauseId = new Map()
  pendingSupplements.forEach((item) => {
    const clauseId = String(item?.clause_id || '').trim()
    if (!clauseId) return
    // Each rerun only keeps the latest supplement for one clause.
    latestPendingByClauseId.set(clauseId, item)
  })
  const latestPendingSupplements = Array.from(latestPendingByClauseId.values())

  const pendingEvidenceItems = latestPendingSupplements.map((item) => {
    const normalized = item?.evidence_id ? item : { ...item, evidence_id: `manual_${item.supplement_id}` }
    return {
      supplement: normalized,
      evidence: toManualEvidenceItem(session, normalized),
    }
  })

  const evidenceIds = new Set(pendingEvidenceItems.map((item) => item.evidence.evidence_id))
  const overriddenClauseIds = new Set(
    pendingEvidenceItems
      .map((item) => String(item.evidence.rule_id || '').trim())
      .filter(Boolean),
  )

  const baseEvidence = Array.isArray(session?.evidence)
    ? session.evidence.filter((item) => {
      const evidenceId = String(item?.evidence_id || '')
      const ruleId = String(item?.rule_id || '').trim()
      if (evidenceIds.has(evidenceId)) return false
      if (overriddenClauseIds.has(ruleId)) return false
      return true
    })
    : []

  const supplementById = new Map(pendingEvidenceItems.map((item) => [item.supplement.supplement_id, item.supplement]))
  const nextSupplements = normalizedSupplements.map((item) => supplementById.get(item.supplement_id) || item)

  return {
    evidence: [...baseEvidence, ...pendingEvidenceItems.map((item) => item.evidence)],
    supplements: nextSupplements,
  }
}

const rerunSupplementReview = () => {
  const session = activeSession.value
  if (!session) {
    ElMessage.warning('当前没有可复核会话。')
    return
  }
  if (liveLoading.value) {
    ElMessage.warning('当前分析进行中，请稍后再试。')
    return
  }

  const pendingCount = (Array.isArray(session.manual_supplements) ? session.manual_supplements : [])
    .filter((item) => item?.status === 'pending_review')
    .length
  if (pendingCount === 0) {
    ElMessage.warning('暂无“已提交待复核”的补证记录。')
    return
  }

  const { evidence, supplements } = buildSupplementReviewPayload(session)
  activeSession.value = { ...session, manual_supplements: supplements }
  startStreamDebate({
    idCard: session.id_card || idCardInput.value,
    policyId: session.policy_id || selectedPolicyId.value,
    evidence,
    debateOnly: true,
    startTab: 'verdict',
    manualSupplements: supplements,
    reviewMode: 'manual_supplement',
  })
}

const restartHistoryDebate = (session) => {
  const idCard = session?.id_card?.trim?.() ?? ''
  const policyId = session?.policy_id ?? ''
  const evidence = Array.isArray(session?.evidence) ? session.evidence : []
  const manualSupplements = Array.isArray(session?.manual_supplements) ? session.manual_supplements : []

  if (!idCard) {
    ElMessage.warning('历史会话缺少身份证号，无法重新发起辩论。')
    return
  }

  idCardInput.value = idCard
  userQueryInput.value = ''
  intentResult.value = null
  selectedPolicyId.value = policyId

  ElMessage.success('已按历史会话参数重新发起辩论。')
  startStreamDebate({
    idCard,
    policyId,
    evidence,
    debateOnly: true,
    startTab: 'tribunal',
    manualSupplements,
  })
}

const handleBeforeUnload = (e) => {
  if (liveLoading.value) {
    e.preventDefault()
    e.returnValue = ''
  }
}

onMounted(() => {
  fetchHistory()
  window.addEventListener('beforeunload', handleBeforeUnload)
})

onUnmounted(() => {
  window.removeEventListener('beforeunload', handleBeforeUnload)
})
</script>

<template>
  <el-container direction="vertical" class="app-shell gov-app-shell">
    <el-header class="app-header">
      <div class="header-top">
        <div class="header-inner">
          <div class="header-row">
            <div class="gov-title-wrap">
              <img
                class="brand-round-logo"
                src="./assets/zhicetong-logo-new.png"
                alt="智策通"
              />
              <div class="brand-block">
                <div class="header-title">智策通</div>
                <div class="brand-divider"></div>
                <div class="header-subtitle">基于大模型的多Agent辩论与T2SQL取证的政策研判系统</div>
              </div>
            </div>
            <div class="header-right">
              <el-tag type="primary" effect="dark" class="phase-pill">
                Phase 2.1 <span class="online-dot" aria-hidden="true"></span>
              </el-tag>
              <el-button v-if="liveLoading" type="danger" plain size="small" @click="stopAnalysis">
                <el-icon><CircleCloseFilled /></el-icon> 停止分析
              </el-button>
              <div class="global-audit-progress" aria-label="全局审核进度">
                <div class="global-progress-track">
                  <div class="global-progress-fill" :style="{ width: `${globalProgressPct}%` }"></div>
                  <div
                    v-for="(step, index) in globalViewSteps"
                    :key="step.key"
                    class="global-progress-node"
                    :class="{
                      'global-progress-node--done': index < globalViewIndex,
                      'global-progress-node--active': index === globalViewIndex,
                    }"
                  >
                    <span class="global-progress-dot">{{ index + 1 }}</span>
                  </div>
                </div>
              </div>
              <img class="module-gavel" :src="moduleGavelUrl" alt="module gavel" />
            </div>
          </div>
        </div>
      </div>
    </el-header>

    <el-main class="main-workspace gov-main-workspace">
      <el-tabs v-model="activeTab" class="dashboard-tabs">

        <!-- ========== 视图一 ========== -->
        <el-tab-pane label="🟦 视图一：用户输入 (Intent Input)" name="input">
          <el-scrollbar height="100%">
            <div class="input-view">
              <div class="flow-strip">
                <div class="flow-sidebar-head">
                  <div class="flow-sidebar-title">当前办理进度</div>
                  <div class="flow-sidebar-subtitle">请按步骤完成信息录入</div>
                </div>

                <div class="flow-cards" :class="{ 'flow-cards--completed': flowCompleted }">
                  <!-- Step 1 -->
                  <div
                    class="flow-card flow-card--step"
                    :class="{ 'flow-card--active': overallFlowStep === 1, 'flow-card--done': overallFlowStep > 1 }"
                    @click="gotoFlowStep(1)"
                  >
                    <div class="flow-card-bar" v-if="overallFlowStep === 1"></div>
                    <div class="flow-card-header">
                      <div class="flow-num" :class="{ 'flow-num--done': overallFlowStep > 1 }">01</div>
                      <div class="flow-card-titles">
                        <div class="flow-card-title">身份录入与政策锁定</div>
                        <div class="flow-card-desc">
                          {{ selectedPolicyId ? '已选政策，准备进入取证检索' : '录入身份证号与需求，完成政策匹配' }}
                        </div>
                      </div>
                      <el-icon v-if="overallFlowStep > 1" class="flow-check"><Select /></el-icon>
                    </div>
                    <div class="flow-result-pill" v-if="selectedPolicyId">已锁定政策</div>
                  </div>
                  <div class="flow-connector" :class="{ 'flow-connector--next': overallFlowStep === 1 }"></div>

                  <!-- Step 2 -->
                  <div
                    class="flow-card flow-card--step"
                    :class="{ 'flow-card--active': overallFlowStep === 2, 'flow-card--done': overallFlowStep > 2, 'flow-card--disabled': overallFlowStep < 2 }"
                    @click="gotoFlowStep(2)"
                  >
                    <div class="flow-card-bar" v-if="overallFlowStep === 2"></div>
                    <div class="flow-card-header">
                      <div class="flow-num" :class="{ 'flow-num--done': overallFlowStep > 2, 'flow-num--pending': overallFlowStep < 2 }">02</div>
                      <div class="flow-card-titles">
                        <div class="flow-card-title" :class="{ 'flow-card-title--disabled': overallFlowStep < 2 }">身份取证检索</div>
                        <div class="flow-card-desc" :class="{ 'flow-card-desc--disabled': overallFlowStep < 2 }">
                          {{ overallFlowStep < 2 ? '需先完成政策锁定' : (overallFlowStep > 2 ? '检索完成，进入智能体评判' : '正在检索证据与画像…') }}
                        </div>
                      </div>
                      <el-icon v-if="overallFlowStep > 2" class="flow-check"><Select /></el-icon>
                    </div>
                    <div class="flow-inline-progress" v-if="overallFlowStep >= 2">
                      <el-progress
                        :percentage="retrievalProgressPct"
                        :stroke-width="6"
                        :show-text="false"
                        color="#9F1D22"
                      />
                      <div class="flow-inline-progress-meta">
                        <span>检索进度</span>
                        <span class="flow-inline-progress-val">{{ Math.round(retrievalProgressPct) }}%</span>
                      </div>
                    </div>
                  </div>
                  <div class="flow-connector" :class="{ 'flow-connector--next': overallFlowStep === 2 }"></div>

                  <!-- Step 3 -->
                  <div
                    class="flow-card flow-card--step"
                    :class="{ 'flow-card--active': overallFlowStep === 3, 'flow-card--done': overallFlowStep > 3, 'flow-card--disabled': overallFlowStep < 3 }"
                    @click="gotoFlowStep(3)"
                  >
                    <div class="flow-card-bar" v-if="overallFlowStep === 3"></div>
                    <div class="flow-card-header">
                      <div class="flow-num" :class="{ 'flow-num--done': overallFlowStep > 3, 'flow-num--pending': overallFlowStep < 3 }">03</div>
                      <div class="flow-card-titles">
                        <div class="flow-card-title" :class="{ 'flow-card-title--disabled': overallFlowStep < 3 }">智能体评判</div>
                        <div class="flow-card-desc" :class="{ 'flow-card-desc--disabled': overallFlowStep < 3 }">
                          {{ overallFlowStep < 3 ? '等待取证完成' : (overallFlowStep > 3 ? '评判结束，进入结果生成' : '多轮辩论中，汇聚分歧与共识') }}
                        </div>
                      </div>
                      <el-icon v-if="overallFlowStep > 3" class="flow-check"><Select /></el-icon>
                    </div>
                    <span class="flow-round-pill flow-round-pill--corner" v-if="overallFlowStep >= 3">第 {{ currentDebateRound }} 轮</span>
                  </div>
                  <div class="flow-connector" :class="{ 'flow-connector--next': overallFlowStep === 3 }"></div>

                  <!-- Step 4 -->
                  <div
                    class="flow-card flow-card--step"
                    :class="{ 'flow-card--active': overallFlowStep === 4, 'flow-card--done': flowCompleted, 'flow-card--disabled': overallFlowStep < 4 }"
                    @click="gotoFlowStep(4)"
                  >
                    <div class="flow-card-bar" v-if="overallFlowStep === 4"></div>
                    <div class="flow-card-header">
                      <div class="flow-num" :class="{ 'flow-num--done': flowCompleted, 'flow-num--pending': overallFlowStep < 4 }">04</div>
                      <div class="flow-card-titles">
                        <div class="flow-card-title" :class="{ 'flow-card-title--disabled': overallFlowStep < 4 }">审核结论生成</div>
                        <div class="flow-card-desc" :class="{ 'flow-card-desc--disabled': overallFlowStep < 4 }">
                          {{ liveLoading && overallFlowStep === 4 ? '生成中…' : '输出裁决与复核入口，并可留痕审计' }}
                        </div>
                      </div>
                      <el-icon v-if="flowCompleted" class="flow-check"><Select /></el-icon>
                    </div>
                    <div v-if="finalVerdictLabel" class="flow-verdict-pill" :class="finalVerdictClass">
                      结论：{{ finalVerdictLabel }}
                    </div>
                  </div>
                </div>

                <div class="flow-foot">
                  <div class="flow-faq">
                    <div class="flow-faq-title">常见问题</div>
                    <el-select v-model="faqStage" class="faq-stage-select" size="small">
                      <el-option label="身份录入与政策锁定" value="input" />
                      <el-option label="身份取证检索" value="retrieval" />
                      <el-option label="智能体评判" value="judge" />
                      <el-option label="审核结论生成" value="result" />
                    </el-select>
                    <div class="faq-scroll">
                      <div class="faq-list">
                        <div v-for="(item, idx) in faqVisibleItems" :key="`${item.stage}-${idx}`" class="faq-item">
                          <div class="faq-q">Q：{{ item.q }}</div>
                          <div class="faq-a">A：{{ item.a }}</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="input-view-left">
                <!-- 左上：输入区 -->
                <div class="input-section">
                  <div class="section-head input-section-head">
                    <div>
                      <div class="section-title">
                        <el-icon><EditPen /></el-icon> 需求输入
                      </div>
                      <div class="section-helper">
                        系统将基于政策条款、业务数据与智能体评议生成可追溯结论。
                      </div>
                    </div>
                  </div>
                  <el-input v-model="idCardInput" :disabled="liveLoading" clearable placeholder="身份证号" class="idcard-field">
                    <template #prepend>身份证号</template>
                    <template #suffix>
                      <el-icon v-if="idCardState === 'valid'" class="idcard-icon idcard-icon--ok"><SuccessFilled /></el-icon>
                      <el-icon v-else-if="idCardState === 'invalid'" class="idcard-icon idcard-icon--error"><WarningFilled /></el-icon>
                    </template>
                  </el-input>
                  <el-input
                    v-model="userQueryInput"
                    :disabled="liveLoading"
                    clearable
                    type="textarea"
                    :rows="4"
                    placeholder="请输入一句话需求，例如：判断这个人能否领取灵活就业补贴"
                    class="query-field"
                    @keyup.ctrl.enter="runIntentRecognition"
                  />
                  <div class="input-actions">
                    <el-button
                      type="primary"
                      :loading="intentLoading"
                      :disabled="intentLoading || liveLoading"
                      @click="runIntentRecognition"
                    >
                      <el-icon><Search /></el-icon> {{ intentLoading ? '识别中...' : '识别意图' }}
                    </el-button>
                    <el-divider direction="vertical" />
                    <span class="toolbar-label">快速填充：</span>
                    <el-button
                      v-for="persona in personas"
                      :key="persona.id"
                      :type="persona.type"
                      plain
                      size="small"
                      class="quick-tag-btn"
                      :disabled="liveLoading"
                      @click="handleQuickTest(persona.id)"
                    >
                      {{ persona.tag }}
                    </el-button>
                  </div>
                </div>

                <!-- 政策匹配 & 条件清单（同级左右版块） -->
                <div class="match-grid">
                  <!-- 左：政策匹配 -->
                  <div class="policy-section">
                    <div class="section-head">
                      <div class="section-title">
                        <el-icon><List /></el-icon> 政策匹配 Top-3
                      </div>
                    </div>

                    <div v-if="!intentResult" class="policy-empty">
                      <div class="policy-skeleton" v-for="idx in 3" :key="idx">
                        <div class="skeleton-line skeleton-line--title"></div>
                        <div class="skeleton-line"></div>
                        <div class="skeleton-line skeleton-line--short"></div>
                      </div>
                    </div>

                    <el-radio-group
                      v-else
                      v-model="selectedPolicyId"
                      class="policy-radio-group"
                    >
                      <el-radio
                        v-for="(policy, idx) in (intentResult.candidate_policies || [])"
                        :key="policy.policy_id"
                        :value="policy.policy_id"
                        border
                        class="policy-radio-card"
                        :class="{ 'policy-radio-card--top': idx === 0, 'policy-radio-card--selected': selectedPolicyId === policy.policy_id }"
                      >
                        <div class="policy-radio-inner">
                          <div class="policy-radio-header">
                            <span class="policy-radio-rank">{{ idx === 0 ? 'Top 1' : `Top ${idx + 1}` }}</span>
                            <span class="policy-radio-name">{{ policy.policy_name }}</span>
                            <span class="policy-score-badge">{{ (policy.match_score * 100).toFixed(0) }}%</span>
                          </div>
                          <el-progress
                            :percentage="Number((policy.match_score * 100).toFixed(0))"
                            :stroke-width="6"
                            :show-text="false"
                            color="#9F1D22"
                          />
                          <div class="policy-radio-reason">{{ policySummary(policy.match_reason)[0] }}</div>
                          <div class="policy-radio-reason">{{ policySummary(policy.match_reason)[1] }}</div>
                          <div class="policy-radio-extra">预计办理时长：1-3 个工作日</div>
                        </div>
                      </el-radio>
                    </el-radio-group>

                    <div v-if="intentResult?.ambiguities?.length" class="intent-ambiguities">
                      <el-alert type="warning" :closable="false" show-icon>
                        <template #title>
                          <span>歧义提示：{{ intentResult.ambiguities.join('；') }}</span>
                        </template>
                      </el-alert>
                    </div>
                  </div>

                  <!-- 右：条件清单 -->
                  <div class="conditions-section">
                    <div class="conditions-panel conditions-panel--embedded">
                      <div class="conditions-head">
                        <div>
                          <div class="section-title">
                            <el-icon><Document /></el-icon> 审核规则清单
                          </div>
                          <div class="conditions-current-policy">
                            当前政策：{{ policyConditionsMeta?.policy_name || '待选择政策' }}
                          </div>
                        </div>
                      </div>

                      <div class="conditions-scroll">
                        <div v-if="!selectedPolicyId" class="conditions-empty-center">
                          请先完成政策匹配选择
                        </div>

                        <div v-else-if="conditionsLoading" class="conditions-loading">
                          <el-icon class="is-loading"><Loading /></el-icon>
                          <span>加载条件中...</span>
                        </div>

                        <div v-else class="conditions-content">
                          <div v-if="policyConditionsMeta" class="conditions-meta">
                            <h3>{{ policyConditionsMeta.policy_name }}</h3>
                            <el-tag size="small" effect="plain">{{ policyConditionsMeta.policy_type }}</el-tag>
                            <p>{{ policyConditionsMeta.description }}</p>
                          </div>

                          <div v-if="policyConditions.length === 0" class="conditions-empty-text">
                            该政策暂无结构化判定条件。
                          </div>

                          <div v-else class="conditions-list">
                            <div class="condition-group" v-if="groupedConditions.necessary.length">
                              <div class="condition-group-title">必要条件</div>
                              <div
                                v-for="cond in groupedConditions.necessary"
                                :key="cond.rule_id"
                                class="condition-card"
                              >
                                <div class="condition-header">
                                  <el-tag :type="conditionCategoryTagType(cond)" size="small">{{ cond.category }}</el-tag>
                                  <span class="condition-id">{{ cond.rule_id }}</span>
                                  <el-tag
                                    class="condition-status-tag"
                                    :type="conditionStatusMeta(cond).type"
                                    effect="plain"
                                    size="small"
                                  >
                                    {{ conditionStatusMeta(cond).label }}
                                  </el-tag>
                                </div>
                                <div class="condition-desc">{{ cond.description }}</div>
                                <div class="condition-basis">
                                  <span>判断依据</span>
                                  <p>{{ conditionBasisText(cond) }}</p>
                                </div>
                              </div>
                            </div>
                            <div class="condition-group" v-if="groupedConditions.sufficient.length">
                              <div class="condition-group-title">充分条件</div>
                              <div
                                v-for="cond in groupedConditions.sufficient"
                                :key="cond.rule_id"
                                class="condition-card"
                              >
                                <div class="condition-header">
                                  <el-tag :type="conditionCategoryTagType(cond)" size="small">{{ cond.category }}</el-tag>
                                  <span class="condition-id">{{ cond.rule_id }}</span>
                                  <el-tag
                                    class="condition-status-tag"
                                    :type="conditionStatusMeta(cond).type"
                                    effect="plain"
                                    size="small"
                                  >
                                    {{ conditionStatusMeta(cond).label }}
                                  </el-tag>
                                </div>
                                <div class="condition-desc">{{ cond.description }}</div>
                                <div class="condition-basis">
                                  <span>判断依据</span>
                                  <p>{{ conditionBasisText(cond) }}</p>
                                </div>
                              </div>
                            </div>
                            <div class="condition-group" v-if="groupedConditions.exclusion.length">
                              <div class="condition-group-title">排除条件</div>
                              <div
                                v-for="cond in groupedConditions.exclusion"
                                :key="cond.rule_id"
                                class="condition-card"
                              >
                                <div class="condition-header">
                                  <el-tag :type="conditionCategoryTagType(cond)" size="small">{{ cond.category }}</el-tag>
                                  <span class="condition-id">{{ cond.rule_id }}</span>
                                  <el-tag
                                    class="condition-status-tag"
                                    :type="conditionStatusMeta(cond).type"
                                    effect="plain"
                                    size="small"
                                  >
                                    {{ conditionStatusMeta(cond).label }}
                                  </el-tag>
                                </div>
                                <div class="condition-desc">{{ cond.description }}</div>
                                <div class="condition-basis">
                                  <span>判断依据</span>
                                  <p>{{ conditionBasisText(cond) }}</p>
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div class="confirm-footer confirm-footer--embedded">
                  <div class="confirm-hint">
                    分析过程将保留命中政策、取证 SQL、证据来源、智能体意见与最终裁决依据。
                  </div>
                  <el-button
                    type="primary"
                    size="large"
                    :disabled="!selectedPolicyId || !idCardInput.trim() || liveLoading"
                    :loading="liveLoading"
                    @click="handleConfirmAndStart"
                  >
                    <el-icon><Right /></el-icon> 确认并启动取证分析
                  </el-button>
                </div>
              </div>

            </div>
          </el-scrollbar>
        </el-tab-pane>

        <!-- ========== 视图二 ========== -->
        <el-tab-pane label="🧠 视图二：取证规划中心 (Cognition Center)" name="cognition">
          <el-scrollbar height="100%">
            <div class="session-pane-inner">
              <el-alert v-if="liveError" type="error" :closable="false" show-icon class="session-alert">
                {{ liveError }}
              </el-alert>
              <DebateSessionView
                :session="activeSession"
                :live-loading="liveLoading"
                :session-loading="sessionLoading"
                current-view="cognition"
                @restart="restartHistoryDebate"
              />
            </div>
          </el-scrollbar>
        </el-tab-pane>

        <!-- ========== 视图三 ========== -->
        <el-tab-pane label="🏛️ 视图三：多智能体辩论庭 (Multi-Agent Tribunal)" name="tribunal">
          <el-scrollbar height="100%">
            <div class="session-pane-inner">
              <el-alert v-if="sessionError" type="warning" :closable="false" show-icon class="session-alert">
                {{ sessionError }}
              </el-alert>
              <DebateSessionView
                :session="activeSession"
                :live-loading="liveLoading"
                :session-loading="sessionLoading"
                current-view="tribunal"
                @restart="restartHistoryDebate"
              />
            </div>
          </el-scrollbar>
        </el-tab-pane>

        <!-- ========== 视图四 ========== -->
        <el-tab-pane label="⚖️ 视图四：裁决结果与补证复核 (Final Verdict)" name="verdict">
          <el-scrollbar height="100%">
            <div class="session-pane-inner">
              <el-alert v-if="sessionError" type="warning" :closable="false" show-icon class="session-alert">
                {{ sessionError }}
              </el-alert>
              <DebateSessionView
                :session="activeSession"
                :live-loading="liveLoading"
                :session-loading="sessionLoading"
                current-view="verdict"
                @restart="restartHistoryDebate"
              />
              <ManualSupplementPanel
                :session="activeSession"
                :disabled="liveLoading || sessionLoading"
                @submit-supplement="handleSubmitSupplement"
                @rerun-review="rerunSupplementReview"
              />
            </div>
          </el-scrollbar>
        </el-tab-pane>

        <el-tab-pane label="📚 历史会话 (History)" name="audit">
          <div class="audit-pane-inner">
            <HistorySessionList
              :items="historyItems"
              :loading="historyLoading"
              :error="historyError"
              :active-id-card="activeIdCard"
              :selected-session-id="selectedSessionId"
              :disabled="liveLoading"
              @select="selectHistorySession"
            />
          </div>
        </el-tab-pane>
      </el-tabs>
      <el-backtop :right="24" :bottom="24" />
    </el-main>
  </el-container>
</template>

<style scoped>
.app-shell {
  height: 100vh;
  color: var(--color-text-main);
  --ui-transition: all 0.2s ease-in-out;
  --color-primary-red: #A83A36;
  --color-primary-red-dark: #8F2E2B;
  --color-red-light-bg: #F8EDEA;
  --color-gov-blue: #2F5F9F;
  --color-text-main: #243447;
  --color-text-secondary: #64748B;
  --color-border: #E6E8EC;
  --color-card-bg: #FFFFFF;
  --color-page-bg: #FAF6F3;
}

.app-header {
  height: auto;
  padding: 0;
  border-bottom: none;
  background: transparent;
}

.header-top {
  height: 104px;
  background:
    linear-gradient(180deg, rgba(250, 246, 243, 0.94), rgba(248, 250, 252, 0.96)),
    linear-gradient(90deg, rgba(168, 58, 54, 0.045), rgba(47, 95, 159, 0.035)),
    url('/image/gov/try1.png') center center / cover no-repeat;
  background-blend-mode: normal, multiply, normal;
  border-bottom: none;
  position: relative;
}

.header-top::after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 1px;
  background: linear-gradient(90deg, var(--color-primary-red), rgba(168, 58, 54, 0.12), transparent);
}

.header-bottom {
  height: 48px;
  background: #7A161A;
  box-shadow: inset 0 2px 4px rgba(100, 116, 139, 0.1);
}

.header-inner {
  height: 100%;
  padding: 0 24px;
  display: flex;
  align-items: center;
}

.header-inner--bottom {
  gap: 18px;
}

.current-view-name {
  color: #fff;
  font-size: 14px;
  white-space: nowrap;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.gov-title-wrap {
  display: flex;
  align-items: center;
  gap: 14px;
}

.gov-emblem {
  width: 58px;
  height: 58px;
  border-radius: 10px;
  flex: 0 0 auto;
}

.module-gavel {
  width: 260px;
  height: 260px;
  object-fit: contain;
  opacity: 0.24;
  position: absolute;
  right: -54px;
  bottom: -36px;
  z-index: 2;
  pointer-events: none;
  filter: sepia(0.18) saturate(0.9) hue-rotate(330deg);
}

.header-right :deep(.el-button) {
  height: 34px;
}

.brand-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.brand-round-logo {
  width: 72px;
  height: 72px;
  object-fit: contain;
  flex: 0 0 auto;
  border-radius: 50%;
  filter: saturate(0.88) contrast(1.04);
  mix-blend-mode: multiply;
}

.brand-divider {
  width: 34px;
  height: 1px;
  background: rgba(168, 58, 54, 0.28);
}

.header-subtitle {
  font-size: 12px;
  color: var(--color-text-secondary);
  letter-spacing: 0;
}

.top-action-btn {
  font-size: 15px;
  color: #334155;
  padding: 0 10px;
  border-radius: 10px;
  transition: var(--ui-transition);
}

.top-action-btn :deep(.el-icon) {
  font-size: 20px;
  color: #64748B;
}

.top-action-btn span {
  color: #64748B;
  font-size: 15px;
}

.top-action-btn:hover {
  color: #9F1D22;
  background: #FDF2F2;
}

.top-action-btn:hover :deep(.el-icon),
.top-action-btn:hover span {
  color: #9F1D22;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.global-audit-progress {
  position: absolute;
  z-index: 3;
  width: 340px;
  min-width: 300px;
  top: 42px;
  right: 108px;
  border: 1px solid rgba(168, 58, 54, 0.12);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  box-shadow: 0 4px 10px rgba(100, 116, 139, 0.08);
  padding: 8px 14px;
  backdrop-filter: blur(4px);
}

.global-progress-track {
  position: relative;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  align-items: center;
}

.global-progress-track::before {
  content: "";
  position: absolute;
  left: 8%;
  right: 8%;
  top: 50%;
  height: 3px;
  transform: translateY(-50%);
  border-radius: 999px;
  background: #E2E8F0;
}

.global-progress-fill {
  position: absolute;
  left: 8%;
  top: 50%;
  height: 3px;
  transform: translateY(-50%);
  max-width: 84%;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--color-primary-red), var(--color-gov-blue));
  transition: width 0.2s ease-in-out;
}

.global-progress-node {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  min-width: 0;
}

.global-progress-dot {
  width: 18px;
  height: 18px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #64748B;
  background: #F5F7FA;
  border: 1px solid #E2E8F0;
  font-size: 10px;
  font-weight: 900;
  box-shadow: 0 2px 6px rgba(100, 116, 139, 0.12);
}

.global-progress-node--done .global-progress-dot {
  color: #fff;
  background: var(--color-gov-blue);
  border-color: var(--color-gov-blue);
}

.global-progress-node--active .global-progress-dot {
  color: #fff;
  background: var(--color-primary-red);
  border-color: var(--color-primary-red);
  box-shadow:
    0 0 0 2px rgba(168, 58, 54, 0.14),
    0 4px 10px rgba(100, 116, 139, 0.12);
}

.header-title {
  font-size: 48px;
  font-family: "Source Han Serif SC", "Noto Serif CJK SC", "SimSun", "Songti SC", "Microsoft YaHei", sans-serif;
  font-weight: 900;
  color: var(--color-primary-red-dark);
  letter-spacing: 0;
  line-height: 1;
  transform: none;
  text-shadow: 0 1px 0 rgba(255, 255, 255, 0.84);
  -webkit-text-stroke: 0;
  font-variant-east-asian: traditional;
}

.gov-title-wrap {
  min-height: auto;
}

.phase-pill {
  border-radius: 999px !important;
  background: #EFF6FF !important;
  color: #173B73 !important;
  border-color: rgba(30, 90, 168, 0.28) !important;
  font-size: 12px;
  font-weight: 800;
  padding: 4px 10px;
  box-shadow: none;
  position: absolute;
  top: 14px;
  right: 108px;
  z-index: 4;
}

.online-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #173B73;
  margin-left: 6px;
  box-shadow: 0 0 0 2px rgba(30, 90, 168, 0.18);
}

.header-location {
  display: none;
}

.top-progress {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: 0;
  padding: 6px 10px;
  border-radius: 12px;
  background: rgba(159, 29, 34, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.22);
}

.top-step {
  color: rgba(255, 255, 255, 0.5);
  font-size: 14px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 999px;
  border: 1px solid transparent;
}

.top-step span {
  width: 18px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: rgba(100, 116, 139, 0.3);
  font-size: 10px;
  font-weight: 700;
  color: #fff;
}

.top-step--active {
  background: #9F1D22;
  color: #fff;
  font-weight: 800;
  border-color: rgba(255, 255, 255, 0.55);
  box-shadow:
    0 0 0 2px rgba(159, 29, 34, 0.25),
    0 6px 16px rgba(100, 116, 139, 0.28);
}

.top-step--active span {
  background: rgba(255, 255, 255, 0.18);
}

.top-step--done {
  color: #fff;
}

.top-step--done span {
  width: 18px;
  height: 18px;
  font-size: 18px;
  background: transparent;
  color: #fff;
  font-weight: 900;
}

.top-step-line {
  width: 34px;
  height: 1px;
  border-top: 2px dashed rgba(255, 255, 255, 0.25);
}

.top-step-line--done {
  border-top-style: solid;
  border-top-color: rgba(159, 29, 34, 0.95);
}

.toolbar-label {
  font-size: 12px;
  color: var(--text-muted);
}

.top-action-btn {
  color: #334155;
}

.avatar-entry {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
}

/* ===== 用户输入视图 ===== */
.input-view {
  display: grid;
  grid-template-columns: 296px minmax(0, 1fr);
  grid-template-areas: "flow left";
  gap: 0 18px;
  width: min(100%, 1440px);
  max-width: 1440px;
  margin: 0 auto;
  padding: 18px clamp(18px, 3vw, 28px) 28px;
  min-height: calc(100vh - 158px);
  align-items: stretch;
  box-sizing: border-box;
}

.flow-strip {
  grid-area: flow;
  width: 100%;
  box-sizing: border-box;
  padding: 14px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  position: static;
  min-height: calc(100vh - 184px);
  overflow: visible;
  box-shadow: 0 3px 12px rgba(36, 52, 71, 0.05);
}

.flow-rail-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 12px;
}

/* ==== Flow sidebar v2 (card-based) ==== */
.flow-sidebar-head {
  margin-bottom: 16px;
}

.flow-sidebar-title {
  font-size: 15px;
  font-weight: 800;
  color: var(--color-text-main);
}

.flow-sidebar-subtitle {
  margin-top: 6px;
  font-size: 12px;
  color: #64748B;
}

.flow-cards {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.flow-card {
  position: relative;
  border-radius: 8px;
  background: #fff;
  border: 1px solid var(--color-border);
  box-shadow: none;
  padding: 11px;
  transition: var(--ui-transition);
  cursor: pointer;
}

.flow-card--step {
  min-height: 88px;
}

.flow-card:hover:not(.flow-card--disabled) {
  box-shadow: 0 4px 12px rgba(36, 52, 71, 0.08);
  transform: translateY(-1px);
}

.flow-card--disabled {
  opacity: 0.7;
}

.flow-card--enabled {
  opacity: 1;
}

.flow-card--active {
  border-color: rgba(168, 58, 54, 0.28);
  border-left: 3px solid var(--color-primary-red);
  background: linear-gradient(180deg, #fff, rgba(248, 237, 234, 0.42));
  box-shadow: 0 4px 14px rgba(36, 52, 71, 0.07);
  animation: none;
}

.flow-card-bar {
  position: absolute;
  left: 0;
  top: 14px;
  width: 4px;
  height: 28px;
  border-radius: 3px;
  background: var(--color-primary-red);
}

.flow-card-header {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.flow-num {
  width: 28px;
  height: 28px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 12px;
  color: #fff;
  background: var(--color-primary-red);
  flex: 0 0 auto;
}

.flow-num--done {
  background: var(--color-gov-blue);
}

.flow-num--pending {
  background: #64748B;
}

.flow-card-titles {
  min-width: 0;
}

.flow-card-title {
  font-size: 13px;
  font-weight: 800;
  color: #334155;
}

.flow-card-title--muted {
  color: #334155;
}

.flow-card-title--disabled {
  color: #64748B;
}

.flow-card-desc {
  margin-top: 4px;
  font-size: 11px;
  color: #64748B;
  line-height: 1.45;
}

.flow-card-desc--disabled {
  color: #64748B;
}

.flow-check {
  margin-left: auto;
  color: #2E7D5B;
  margin-top: 4px;
  font-size: 16px;
}

.flow-card-tip {
  margin-top: 10px;
  background: rgba(160, 106, 42, 0.14);
  border-left: 3px solid #A06A2A;
  padding: 8px 12px;
  border-radius: 4px;
  color: #A06A2A;
  font-size: 12px;
  display: flex;
  align-items: flex-start;
  gap: 6px;
}

.flow-card-tip :deep(.el-icon) {
  color: #A06A2A;
  margin-top: 1px;
}

.flow-mini-dots {
  display: flex;
  gap: 6px;
  margin-top: 10px;
}

.mini-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #64748B;
}

.mini-dot--active {
  background: #9F1D22;
  transform: scale(1.2);
}

.mini-dot--ok {
  background: #2E7D5B;
}

.flow-connector {
  height: 10px;
  margin-left: 14px;
  border-left: 1px dashed #CBD5E1;
}

.flow-connector--next {
  border-left-style: solid;
  border-left-color: var(--color-primary-red);
}

.flow-result-pill {
  margin-top: 10px;
  font-size: 11px;
  color: #2E7D5B;
  background: rgba(46, 125, 91, 0.12);
  border-radius: 999px;
  padding: 3px 10px;
  display: inline-flex;
  align-items: center;
}

.flow-inline-progress {
  margin-top: 12px;
}

.flow-inline-progress :deep(.el-progress-bar__outer) {
  background: rgba(100, 116, 139, 0.24);
}

.flow-inline-progress-meta {
  margin-top: 6px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
  color: #64748B;
}

.flow-inline-progress-val {
  color: #7A161A;
  font-weight: 800;
}

.flow-round-pill {
  font-size: 11px;
  font-weight: 900;
  color: #7A161A;
  background: rgba(255, 235, 238, 0.95);
  border: 1px solid rgba(159, 29, 34, 0.28);
  padding: 2px 8px;
  border-radius: 999px;
  white-space: nowrap;
}

.flow-round-pill--corner {
  position: absolute;
  right: 12px;
  bottom: 10px;
}

.flow-verdict-pill {
  margin-top: 10px;
  font-size: 12px;
  font-weight: 800;
  border-radius: 999px;
  padding: 4px 10px;
  display: inline-flex;
  align-items: center;
}

.flow-verdict--pass {
  color: #2E7D5B;
  background: rgba(46, 125, 91, 0.12);
  border: 1px solid rgba(46, 125, 91, 0.42);
}

.flow-verdict--fail {
  color: #9F1D22;
  background: rgba(159, 29, 34, 0.18);
  border: 1px solid rgba(159, 29, 34, 0.5);
}

.flow-cards--completed .flow-card:nth-child(1),
.flow-cards--completed .flow-card:nth-child(3),
.flow-cards--completed .flow-card:nth-child(5) {
  min-height: 96px;
}

.flow-prehint {
  margin-top: 10px;
  font-size: 11px;
  color: #64748B;
  font-style: italic;
}

.flow-status-row {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 11px;
}

.flow-status-inline--ok {
  color: #2E7D5B;
}

.flow-status-inline--wait {
  color: #A06A2A;
}

.flow-foot {
  margin-top: 14px;
}

.flow-duration {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 12px;
  color: #64748B;
  margin-bottom: 10px;
}

.flow-faq {
  padding: 10px;
  border: 1px dashed rgba(100, 116, 139, 0.24);
  border-radius: 8px;
  background: rgba(248, 250, 252, 0.72);
  overflow: visible;
  opacity: 0.72;
}

.flow-faq-title {
  font-size: 12px;
  font-weight: 800;
  color: var(--color-text-secondary);
  margin-bottom: 8px;
}

.faq-stage-select {
  margin-bottom: 10px;
  width: 100%;
}

.faq-scroll {
  overflow: visible;
  padding-right: 2px;
  scrollbar-width: none;
}

.faq-scroll::-webkit-scrollbar {
  width: 0;
  height: 0;
}

.faq-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.faq-item {
  border: 0;
  border-top: 1px solid #E6E8EC;
  border-radius: 0;
  padding: 8px 0 0;
  background: transparent;
}

.faq-q {
  font-size: 12px;
  font-weight: 800;
  color: #334155;
  margin-bottom: 4px;
}

.faq-a {
  font-size: 12px;
  color: #64748B;
  line-height: 1.6;
}

@keyframes flowPulse {
  0%, 100% { box-shadow: 0 1px 2px rgba(100, 116, 139, 0.08); }
  50% { box-shadow: 0 0 0 3px rgba(197, 139, 43, 0.2); }
}

.flow-step {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  min-width: 0;
  padding: 6px 0 6px 8px;
  border-left: 4px solid transparent;
  border-radius: 6px;
}

.flow-step--active .flow-index {
  background: #9F1D22;
  color: #fff;
}

.flow-step--active .flow-text {
  color: #334155;
  font-weight: 700;
}

.flow-step--active {
  border-left-color: #9F1D22;
}

.flow-step-texts {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.flow-index {
  width: 24px;
  height: 24px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  background: #F5F7FA;
  border: 1px solid var(--border-color, rgba(100, 116, 139, 0.24));
  margin-top: 1px;
}

.flow-text {
  font-size: 13px;
  color: #334155;
  white-space: normal;
}

.flow-subtext {
  font-size: 11px;
  color: #64748B;
  line-height: 1.35;
}

.flow-tip-mini {
  font-size: 11px;
  color: #64748B;
}

.flow-rail-line {
  height: 10px;
  width: 1px;
  background: var(--border-color, rgba(100, 116, 139, 0.24));
  margin: 2px 11px;
}

.flow-status {
  display: flex;
  gap: 6px;
  margin-top: 2px;
  align-items: baseline;
}

.flow-status-tag {
  font-size: 12px;
  border-radius: 999px;
  padding: 1px 8px;
  line-height: 20px;
  height: 20px;
}

.flow-status-tag--ok {
  color: #fff;
  background: #2E7D5B;
}

.flow-status-tag--wait {
  color: #334155;
  background: #F5F7FA;
}

.input-view-left {
  grid-area: left;
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-width: 0;
  min-height: calc(100vh - 184px);
}

.input-view-right {
  grid-area: right;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  border: 1px solid var(--border-color, rgba(100, 116, 139, 0.24));
  border-radius: 12px;
  padding: 20px;
  background: rgba(255, 255, 255, 0.9);
  min-height: calc(100vh - 210px);
}

.conditions-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  flex: 1;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  padding: 20px;
  background: rgba(255, 255, 255, 0.95);
}

.conditions-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.conditions-close {
  color: #64748B;
}

.conditions-locked {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
  border: 1px dashed #F5F7FA;
  border-radius: 12px;
  padding: 18px;
  background: #fff;
  color: #64748B;
}

.conditions-locked-title {
  font-size: 14px;
  font-weight: 800;
  color: #334155;
}

.conditions-locked-text {
  font-size: 12px;
  line-height: 1.6;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 700;
  color: var(--color-text-main);
  margin-bottom: 10px;
}

.section-title::before {
  content: "";
  width: 4px;
  height: 20px;
  border-radius: 2px;
  background: var(--color-primary-red);
}

.section-helper {
  margin-top: -4px;
  margin-bottom: 14px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--color-text-secondary);
}

.input-section-head {
  align-items: flex-start;
  margin-bottom: 4px;
}

.input-section {
  background: var(--color-card-bg);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  padding: 18px;
  box-shadow: 0 3px 12px rgba(36, 52, 71, 0.05);
  transition: var(--ui-transition);
}

.input-section:focus-within {
  border-color: rgba(168, 58, 54, 0.5);
  box-shadow: 0 0 0 3px rgba(168, 58, 54, 0.1);
}

.idcard-field {
  width: 100%;
  max-width: 420px;
}

.idcard-field :deep(.el-input-group__prepend) {
  min-width: 96px;
  justify-content: center;
  color: #334155 !important;
}

.query-field {
  width: 100%;
  margin-top: 10px;
}

.query-field :deep(.el-textarea__inner) {
  min-height: 86px;
}

.query-field :deep(.el-textarea__inner) {
  transition: all 0.2s ease-in-out;
}

.query-field :deep(.el-textarea__inner:focus) {
  border-color: var(--color-primary-red) !important;
  box-shadow: 0 0 0 3px rgba(168, 58, 54, 0.1) !important;
}

.input-field {
  max-width: 320px;
  margin-bottom: 12px;
}

.idcard-icon--ok {
  color: #2E7D5B;
}

.idcard-icon--error {
  color: #9F1D22;
}

.query-meta-row {
  display: flex;
  justify-content: space-between;
  margin-top: -4px;
  margin-bottom: 8px;
}

.query-counter {
  font-size: 12px;
  color: #64748B;
}

.input-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 4px;
}

.input-actions :deep(.el-button--primary) {
  min-width: 108px;
}

.policy-section {
  background: var(--color-card-bg);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  padding: 18px;
  flex: 1;
  box-shadow: 0 3px 12px rgba(36, 52, 71, 0.05);
  transition: var(--ui-transition);
}

.match-grid {
  display: grid;
  grid-template-columns: minmax(360px, 0.92fr) minmax(420px, 1.08fr);
  gap: 18px;
  align-items: stretch;
  flex: 1;
  min-height: 0;
}

.conditions-section {
  min-width: 0;
  border-radius: 12px;
}

.conditions-panel--embedded {
  padding: 16px;
  background: rgba(255, 255, 255, 0.96);
}

.conditions-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: hidden;
  padding-right: 6px;
}

.conditions-section:hover .conditions-scroll {
  overflow-y: auto;
}

.conditions-empty-center {
  min-height: 320px;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: rgba(100, 116, 139, 0.72);
  font-size: 12px;
  border: 1px dashed rgba(100, 116, 139, 0.18);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.7);
}

.confirm-footer--embedded {
  margin-top: -2px;
  border: 1px solid var(--color-border);
  background: rgba(255, 255, 255, 0.96);
  padding: 12px 14px;
  border-radius: 10px;
  position: static;
  box-shadow: 0 3px 12px rgba(36, 52, 71, 0.05);
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.section-head .section-title {
  margin-bottom: 0;
}

.policy-empty {
  padding: 8px 0;
}

.policy-skeleton {
  border: 1px solid rgba(100, 116, 139, 0.18);
  border-radius: 8px;
  padding: 12px;
  position: relative;
}

.policy-skeleton::before {
  content: "";
  position: absolute;
  left: 0;
  top: 10px;
  bottom: 10px;
  width: 3px;
  border-radius: 2px;
  background: #9F1D22;
}

.policy-skeleton + .policy-skeleton {
  margin-top: 12px;
}

.skeleton-line {
  height: 10px;
  background: linear-gradient(90deg, #F5F7FA 25%, #F5F7FA 50%, #F5F7FA 75%);
  background-size: 200% 100%;
  animation: skeletonPulse 1.2s infinite;
  border-radius: 6px;
}

.skeleton-line + .skeleton-line {
  margin-top: 8px;
}

.skeleton-line--title {
  width: 60%;
}

.skeleton-line--short {
  width: 45%;
}

.policy-radio-group {
  display: flex;
  flex-direction: column;
  width: 100%;
  gap: 10px;
}

.policy-radio-group :deep(.el-radio) {
  width: 100%;
  height: auto !important;
  margin-right: 0;
  align-items: flex-start;
  padding: 11px 12px;
  box-sizing: border-box;
}

.policy-radio-group :deep(.el-radio__input) {
  margin-top: 3px;
}

.policy-radio-group :deep(.el-radio__label) {
  flex: 1;
  white-space: normal;
  line-height: 1.5;
  padding-left: 8px;
}

.policy-radio-card--top :deep(.el-radio.is-bordered) {
  border-color: rgba(168, 58, 54, 0.42);
  background: linear-gradient(180deg, #fff, var(--color-red-light-bg));
}

.policy-radio-card:not(.policy-radio-card--top) :deep(.el-radio.is-bordered) {
  border-color: var(--color-border);
  background: #fff;
}

.policy-radio-card--selected :deep(.el-radio.is-bordered) {
  border-color: var(--color-primary-red) !important;
}

.policy-radio-inner {
  width: 100%;
}

.policy-radio-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.policy-score-badge {
  margin-left: auto;
  font-size: 11px;
  color: #fff;
  background: var(--color-primary-red);
  border-radius: 999px;
  padding: 2px 8px;
}

.policy-radio-rank {
  font-size: 11px;
  font-weight: 800;
  color: var(--color-primary-red-dark);
  min-width: 44px;
}

.policy-radio-name {
  font-weight: 600;
  font-size: 14px;
  color: var(--el-text-color-primary);
  flex: 1;
}

.policy-radio-reason {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.5;
  color: #64748B;
}

.policy-radio-extra {
  margin-top: 4px;
  font-size: 12px;
  color: #64748B;
}

.quick-tag-btn {
  border-color: rgba(168, 58, 54, 0.32) !important;
  color: var(--color-primary-red) !important;
  background: #fff !important;
  height: 32px !important;
  line-height: 32px !important;
  padding: 0 10px !important;
  margin: 0 !important;
}

.quick-tag-btn:hover {
  background: var(--color-red-light-bg) !important;
}

.intent-ambiguities {
  margin-top: 12px;
}

/* ===== 右侧条件区 ===== */
.conditions-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 360px;
}

.conditions-empty--red {
  color: #9F1D22;
  font-weight: 600;
  flex-direction: column;
  gap: 8px;
}

.conditions-empty--red :deep(.el-icon) {
  font-size: 30px;
}

.conditions-loading {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--el-text-color-secondary);
  font-size: 14px;
  min-height: 360px;
}

.conditions-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 360px;
}

.conditions-current-policy {
  margin-top: -4px;
  margin-bottom: 12px;
  font-size: 12px;
  color: var(--color-text-secondary);
}

.conditions-policy-pill {
  align-self: flex-start;
  margin-bottom: 10px;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--color-primary-red);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
}

.conditions-meta {
  margin-bottom: 14px;
  padding: 14px;
  background: #FAFBFC !important;
  border: 1px solid var(--color-border);
  border-radius: 8px;
}

.condition-group + .condition-group {
  margin-top: 12px;
}

.condition-group-title {
  border-left: 3px solid var(--color-primary-red);
  background: var(--color-red-light-bg);
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 8px;
}

.conditions-meta h3 {
  margin: 0 0 6px;
  font-size: 16px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
}

.conditions-meta p {
  margin: 8px 0 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  line-height: 1.6;
}

.conditions-empty-text {
  padding: 40px 0;
  text-align: center;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

.conditions-list {
  display: flex;
  flex-direction: column;
  gap: 9px;
  flex: 1;
  overflow-y: auto;
  max-height: calc(100vh - 330px);
  scrollbar-width: none;
}

.conditions-list::-webkit-scrollbar {
  width: 0;
  height: 0;
}

.condition-card {
  padding: 12px 14px;
  background: var(--color-card-bg);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  transition: all 0.2s ease-in-out;
}

.condition-card:hover {
  border-color: rgba(168, 58, 54, 0.36);
  background: #FAFBFC;
}

.condition-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.condition-id {
  font-size: 11px;
  color: var(--color-text-secondary);
  font-family: monospace;
  background: #F8FAFC;
  border: 1px solid #E6E8EC;
  border-radius: 999px;
  padding: 2px 8px;
}

.condition-status-tag {
  margin-left: auto;
}

.condition-desc {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text-main);
  line-height: 1.55;
  word-break: break-word;
}

.condition-basis {
  margin-top: 8px;
  display: grid;
  grid-template-columns: 58px minmax(0, 1fr);
  gap: 8px;
  align-items: start;
  font-size: 12px;
  color: var(--color-text-secondary);
}

.condition-basis span {
  color: var(--color-gov-blue);
  font-weight: 700;
}

.condition-basis p {
  margin: 0;
  line-height: 1.55;
}

.state-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.state-dot--pending {
  background: #64748B;
}

.state-dot--ok {
  background: #2E7D5B;
}

.state-dot--error {
  background: #9F1D22;
}

.state-dot--warn {
  background: #A06A2A;
}

.condition-detail {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.55;
  color: var(--el-color-success);
  display: flex;
  align-items: flex-start;
  gap: 4px;
}

.condition-detail--fail {
  color: var(--el-color-danger);
}

.condition-detail--logic {
  color: var(--el-color-warning);
}

.condition-detail--formula {
  color: var(--el-color-info);
}

.confirm-footer {
  margin-top: 24px;
  padding: 12px 4px 4px;
  border-top: 1px solid var(--border-color, rgba(100, 116, 139, 0.24));
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  position: sticky;
  bottom: 0;
  background: linear-gradient(180deg, rgba(255,255,255,0), rgba(255,255,255,0.88) 30%, rgba(255,255,255,0.94));
}

.confirm-hint {
  margin-right: auto;
  font-size: 12px;
  line-height: 1.6;
  color: var(--color-text-secondary);
  max-width: 620px;
}

.confirm-footer :deep(.el-button--primary) {
  border-radius: 8px;
  min-width: 210px;
  height: 42px;
  background: var(--color-primary-red);
  border-color: var(--color-primary-red);
  transition: all 0.2s ease-in-out;
}

.confirm-footer :deep(.el-button--primary:hover) {
  background: var(--color-primary-red-dark);
  border-color: var(--color-primary-red-dark);
}

.confirm-footer :deep(.el-button--primary.is-disabled) {
  background: #64748B;
  border-color: #64748B;
}

.confirm-footer :deep(.el-button--primary.is-disabled:hover) {
  background: #64748B;
  border-color: #64748B;
}

.confirm-footer :deep(.el-button.is-plain) {
  color: #9F1D22;
  border-color: #9F1D22;
  background: #fff;
}

@keyframes skeletonPulse {
  0% { background-position: 100% 0; }
  100% { background-position: 0 0; }
}

/* ===== Tabs 与通用样式 ===== */
.main-workspace {
  padding: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.dashboard-tabs {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.dashboard-tabs :deep(.el-tabs__header) {
  margin: 0;
  padding: 8px clamp(18px, 3vw, 28px);
  background: var(--color-primary-red);
  border-bottom: none;
  overflow: visible;
}

.dashboard-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.dashboard-tabs :deep(.el-tabs__nav-scroll) {
  display: flex;
  justify-content: center;
  width: 100%;
  overflow: visible;
}

.dashboard-tabs :deep(.el-tabs__nav) {
  background: transparent;
  border-radius: 0;
  padding: 0;
  border: none;
  box-shadow: none;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: center;
  width: 100%;
  max-width: 100%;
  margin: 0 auto;
}

.dashboard-tabs :deep(.el-tabs__active-bar) {
  display: none;
}

.dashboard-tabs :deep(.el-tabs__item) {
  height: 34px;
  line-height: 34px;
  padding: 0 14px !important;
  border-radius: 999px;
  font-weight: 600;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.74) !important;
  transition: all 0.2s ease-in-out;
  border: 1px solid transparent;
  box-shadow: none;
  max-width: 100%;
  white-space: nowrap;
  flex: 0 1 auto;
}

.dashboard-tabs :deep(.el-tabs__item:hover:not(.is-active)) {
  color: #fff !important;
  background: rgba(143, 46, 43, 0.36);
  border-color: rgba(255, 255, 255, 0.12);
}

.dashboard-tabs :deep(.el-tabs__item.is-active) {
  color: var(--color-primary-red-dark) !important;
  background: #fff;
  box-shadow: 0 3px 9px rgba(36, 52, 71, 0.12);
  border-color: rgba(255, 255, 255, 0.56);
}

.dashboard-tabs :deep(.el-tabs__item .el-icon) {
  margin-right: 6px;
}

:deep(.el-backtop) {
  background: #9F1D22;
  color: #fff;
  box-shadow: 0 2px 8px rgba(100, 116, 139, 0.2);
}

.conditions-mobile-drawer :deep(.el-drawer__header) {
  margin-bottom: 8px;
}

.dashboard-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow: hidden;
  padding: 0;
  background: var(--bg-base);
  min-width: 0;
}

.dashboard-tabs :deep(.el-tab-pane) {
  height: 100%;
}

.session-pane-inner {
  max-width: 1440px;
  margin: 0 auto;
  padding: 24px 32px 40px;
}

.audit-pane-inner {
  height: 100%;
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.session-alert {
  margin-bottom: 16px;
}

@media (max-width: 1100px) {
  .input-view {
    grid-template-columns: 1fr;
    grid-template-areas:
      "flow"
      "left";
    gap: 14px;
    width: 100%;
    padding: 16px;
  }

  .match-grid {
    grid-template-columns: 1fr;
  }

  .input-view-left {
    flex: none;
  }

  .flow-strip {
    position: static;
    min-height: auto;
    padding: 12px 10px;
    width: 100%;
    overflow: visible;
  }

  .flow-rail-title {
    display: block;
  }

  .flow-strip:hover .flow-rail-title {
    display: block;
  }

  .flow-step-texts {
    display: flex;
  }

  .flow-strip:hover .flow-step-texts {
    display: flex;
  }

  .session-pane-inner {
    padding: 16px 16px 32px;
  }
}

@media (max-width: 1280px) {
  .input-view {
    grid-template-columns: 280px minmax(0, 1fr);
    grid-template-areas: "flow left";
  }

  .match-grid {
    grid-template-columns: 1fr;
  }
}
</style>
