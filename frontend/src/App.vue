<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import DebateSessionView from './components/DebateSessionView.vue'
import HistorySessionList from './components/HistorySessionList.vue'
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

const personas = [
  { id: '42090219800101000A', tag: 'A 张完美', type: 'success' },
  { id: '42090219850505000B', tag: 'B 李老板', type: 'danger' },
  { id: '42090219760310000D', tag: 'D 赵争议', type: 'warning' },
  { id: '42090219780815000E', tag: 'E 陈灰色', type: 'warning' },
  { id: '42090219700505000I', tag: 'I 钱幽灵', type: 'info' },
]

const handleQuickTest = (id) => {
  if (!liveLoading.value) {
    idCardInput.value = id
  }
}

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
        ElMessage.info('请在「用户输入」视图中选择政策后重新提交。')
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
    ElMessage.success('实时分析完成，历史会话已刷新。')
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

const restartHistoryDebate = (session) => {
  const idCard = session?.id_card?.trim?.() ?? ''
  const policyId = session?.policy_id ?? ''
  const evidence = Array.isArray(session?.evidence) ? session.evidence : []

  if (!idCard) {
    ElMessage.warning('历史会话缺少身份证号，无法重新发起辩论。')
    return
  }

  idCardInput.value = idCard
  userQueryInput.value = ''
  intentResult.value = null
  selectedPolicyId.value = policyId

  ElMessage.success('已按历史会话参数重新发起辩论。')
  startStreamDebate({ idCard, policyId, evidence, debateOnly: true, startTab: 'tribunal' })
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
  <el-container direction="vertical" class="app-shell">
    <el-header class="app-header">
      <div class="header-inner">
        <div class="header-row">
          <div>
            <div class="header-title">多 Agent 辩论判定台</div>
            <div class="header-subtitle">输入需求 → 意图识别 → 取证规划 → 多智能体辩论 → 决策审计</div>
          </div>
          <div class="header-right">
            <el-tag type="primary" effect="plain">Phase 2.1</el-tag>
            <el-button v-if="liveLoading" type="danger" plain size="small" @click="stopAnalysis">
              <el-icon><CircleCloseFilled /></el-icon> 停止分析
            </el-button>
          </div>
        </div>
      </div>
    </el-header>

    <el-main class="main-workspace">
      <el-tabs v-model="activeTab" class="dashboard-tabs">

        <!-- ========== 用户输入视图 ========== -->
        <el-tab-pane label="📝 用户输入 (Intent Input)" name="input">
          <el-scrollbar height="100%">
            <div class="input-view">
              <div class="input-view-left">
                <!-- 左上：输入区 -->
                <div class="input-section">
                  <div class="section-title">
                    <el-icon><EditPen /></el-icon> 需求输入
                  </div>
                  <el-input
                    v-model="idCardInput"
                    :disabled="liveLoading"
                    clearable
                    placeholder="身份证号"
                    class="input-field"
                  >
                    <template #prepend>身份证号</template>
                  </el-input>
                  <el-input
                    v-model="userQueryInput"
                    :disabled="liveLoading"
                    clearable
                    type="textarea"
                    :rows="3"
                    placeholder="请输入一句话需求，如：判断这个人能不能领灵活就业补贴"
                    class="input-field"
                    @keyup.ctrl.enter="runIntentRecognition"
                  />
                  <div class="input-actions">
                    <el-button
                      type="primary"
                      :loading="intentLoading"
                      :disabled="intentLoading || liveLoading"
                      @click="runIntentRecognition"
                    >
                      <el-icon><Search /></el-icon> 识别意图
                    </el-button>
                    <el-divider direction="vertical" />
                    <span class="toolbar-label">快速填入：</span>
                    <el-button
                      v-for="persona in personas"
                      :key="persona.id"
                      :type="persona.type"
                      plain
                      size="small"
                      :disabled="liveLoading"
                      @click="handleQuickTest(persona.id)"
                    >
                      {{ persona.tag }}
                    </el-button>
                  </div>
                </div>

                <!-- 左下：Top-3 政策选择 -->
                <div class="policy-section">
                  <div class="section-title">
                    <el-icon><List /></el-icon> 政策匹配 Top-3
                  </div>

                  <div v-if="!intentResult" class="policy-empty">
                    <el-empty description="请先输入需求并点击「识别意图」" :image-size="80" />
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
                      :class="{ 'policy-radio-card--top': idx === 0 }"
                    >
                      <div class="policy-radio-inner">
                        <div class="policy-radio-header">
                          <span class="policy-radio-rank">#{{ idx + 1 }}</span>
                          <span class="policy-radio-name">{{ policy.policy_name }}</span>
                          <el-tag
                            :type="policy.match_score >= 0.8 ? 'success' : policy.match_score >= 0.5 ? 'warning' : 'info'"
                            size="small"
                            effect="plain"
                          >
                            {{ (policy.match_score * 100).toFixed(0) }}%
                          </el-tag>
                        </div>
                        <div class="policy-radio-reason">{{ policy.match_reason }}</div>
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
              </div>

              <!-- 右侧：条件展示 -->
              <div class="input-view-right">
                <div class="section-title">
                  <el-icon><Document /></el-icon> 判定条件清单
                </div>

                <div v-if="!selectedPolicyId" class="conditions-empty">
                  <el-empty description="请在左侧选择一个政策" :image-size="80" />
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
                    <div
                      v-for="cond in policyConditions"
                      :key="cond.rule_id"
                      class="condition-card"
                    >
                      <div class="condition-header">
                        <el-tag :type="cond.tag_type" size="small">{{ cond.category }}</el-tag>
                        <span class="condition-id">{{ cond.rule_id }}</span>
                      </div>
                      <div class="condition-desc">{{ cond.description }}</div>
                      <div v-if="cond.pass_condition" class="condition-detail">
                        <el-icon><SuccessFilled /></el-icon> {{ cond.pass_condition }}
                      </div>
                      <div v-if="cond.fail_condition" class="condition-detail condition-detail--fail">
                        <el-icon><CircleCloseFilled /></el-icon> {{ cond.fail_condition }}
                      </div>
                      <div v-if="cond.check_logic" class="condition-detail condition-detail--logic">
                        <el-icon><InfoFilled /></el-icon> {{ cond.check_logic }}
                      </div>
                      <div v-if="cond.formula" class="condition-detail condition-detail--formula">
                        <el-icon><Odometer /></el-icon> {{ cond.formula }}
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 右下角确认按钮 -->
                <div class="confirm-footer">
                  <el-button
                    type="primary"
                    size="large"
                    :disabled="!selectedPolicyId || !idCardInput.trim() || liveLoading"
                    :loading="liveLoading"
                    @click="handleConfirmAndStart"
                  >
                    <el-icon><Right /></el-icon> 确认并开始分析
                  </el-button>
                </div>
              </div>
            </div>
          </el-scrollbar>
        </el-tab-pane>

        <!-- ========== 视图一 ========== -->
        <el-tab-pane label="🖥️ 视图一：取证规划中心 (Cognition Center)" name="cognition">
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

        <!-- ========== 视图二 ========== -->
        <el-tab-pane label="🏛️ 视图二：多智能体辩论庭 (Multi-Agent Tribunal)" name="tribunal">
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

        <!-- ========== 视图三 ========== -->
        <el-tab-pane label="📊 视图三：决策审计看板 (Global Audit)" name="audit">
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
    </el-main>
  </el-container>
</template>

<style scoped>
.app-shell {
  height: 100vh;
}

.app-header {
  height: auto;
  padding: 0;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-card);
}

.header-inner {
  padding: 14px 24px;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-title {
  font-size: 20px;
  font-weight: 800;
  color: var(--text-primary);
}

.header-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-muted);
}

.toolbar-label {
  font-size: 12px;
  color: var(--text-muted);
}

/* ===== 用户输入视图 ===== */
.input-view {
  display: flex;
  gap: 24px;
  max-width: 1440px;
  margin: 0 auto;
  padding: 24px 32px 40px;
  min-height: 100%;
}

.input-view-left {
  flex: 0 0 420px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.input-view-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary, #303133);
  margin-bottom: 14px;
}

.input-section {
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-color, #e4e7ed);
  border-radius: 12px;
  padding: 20px;
}

.input-field {
  margin-bottom: 12px;
}

.input-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 4px;
}

.policy-section {
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-color, #e4e7ed);
  border-radius: 12px;
  padding: 20px;
  flex: 1;
}

.policy-empty {
  padding: 20px 0;
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
  padding: 12px 14px;
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
  border-color: var(--el-color-primary-light-5);
}

.policy-radio-inner {
  width: 100%;
}

.policy-radio-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.policy-radio-rank {
  font-size: 12px;
  font-weight: 700;
  color: var(--el-color-primary);
  min-width: 20px;
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
  color: var(--el-text-color-secondary);
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
}

.conditions-loading {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

.conditions-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.conditions-meta {
  margin-bottom: 16px;
  padding: 16px;
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-color, #e4e7ed);
  border-radius: 12px;
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
  gap: 10px;
  flex: 1;
  overflow-y: auto;
}

.condition-card {
  padding: 14px 16px;
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-color, #e4e7ed);
  border-radius: 10px;
  transition: border-color 0.2s;
}

.condition-card:hover {
  border-color: var(--el-color-primary-light-5);
}

.condition-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.condition-id {
  font-size: 11px;
  color: var(--el-text-color-placeholder);
  font-family: monospace;
}

.condition-desc {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  line-height: 1.5;
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
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color, #e4e7ed);
  display: flex;
  justify-content: flex-end;
}

/* ===== Tabs & 通用 ===== */
.main-workspace {
  padding: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.dashboard-tabs {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.dashboard-tabs :deep(.el-tabs__header) {
  margin: 0;
  padding: 12px 24px;
  background: var(--bg-base);
  border-bottom: none;
}

.dashboard-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.dashboard-tabs :deep(.el-tabs__nav-scroll) {
  display: flex;
  justify-content: center;
}

.dashboard-tabs :deep(.el-tabs__nav) {
  background: var(--bg-card);
  border-radius: 999px;
  padding: 5px;
  border: 1px solid var(--border-color);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
  display: flex;
  gap: 3px;
}

.dashboard-tabs :deep(.el-tabs__active-bar) {
  display: none;
}

.dashboard-tabs :deep(.el-tabs__item) {
  height: 36px;
  line-height: 36px;
  padding: 0 20px !important;
  border-radius: 999px;
  font-weight: 600;
  font-size: 13px;
  color: var(--text-muted) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border: none;
}

.dashboard-tabs :deep(.el-tabs__item:hover:not(.is-active)) {
  color: var(--text-primary) !important;
  background: rgba(0, 0, 0, 0.02);
}

.dashboard-tabs :deep(.el-tabs__item.is-active) {
  color: var(--accent-blue) !important;
  background: #eff6ff;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

.dashboard-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow: hidden;
  padding: 0;
  background: var(--bg-base);
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
    flex-direction: column;
  }

  .input-view-left {
    flex: none;
  }

  .session-pane-inner {
    padding: 16px 16px 32px;
  }
}
</style>
