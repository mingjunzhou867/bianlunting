<script setup>
import { ref } from 'vue'
import AgentCard from './AgentCard.vue'
import EvidenceBoard from './EvidenceBoard.vue'
import PersonaProfileCard from './PersonaProfileCard.vue'

const props = defineProps({
  session: { type: Object, default: null },
  liveLoading: { type: Boolean, default: false },
  sessionLoading: { type: Boolean, default: false },
  currentView: { type: String, default: 'all' },
})

const emit = defineEmits(['restart'])
const evidenceDetailVisible = ref(false)
const evidenceDetailText = ref('')

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api'

const formatDateTime = (value) => {
  if (!value) return '未记录'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleString('zh-CN', { hour12: false })
}

const canDownloadOfficialReport = (session) => Boolean(session?.session_id && session?.final_conclusion)

const resolveOfficialReportUrl = (session) => {
  if (!canDownloadOfficialReport(session)) return ''
  const rawUrl = session?.official_report?.download_url || `/debates/${session.session_id}/official_report.pdf`
  if (/^https?:\/\//.test(rawUrl)) return rawUrl
  const hostBase = API_BASE.replace(/\/api\/?$/, '')
  if (rawUrl.startsWith('/api/')) return `${hostBase}${rawUrl}`
  if (rawUrl.startsWith('/')) return `${API_BASE}${rawUrl}`
  return `${API_BASE}/${rawUrl}`
}

const resolveOfficialReportFilename = (session) => session?.official_report?.filename || `政务数据辅助审核裁决书_${session?.session_id || 'session'}.pdf`

const hasJudgments = (session) =>
  Array.isArray(session?.history) &&
  session.history.some((round) => Array.isArray(round?.judgments) && round.judgments.length > 0)

const getConclusionTagType = (conclusion, explicitType) => {
  if (explicitType) return explicitType
  if (conclusion === '符合') return 'success'
  if (conclusion === '不符合') return 'danger'
  return 'warning'
}

const hasArbiterResult = (session) =>
  Boolean(session?.arbiter_result && Object.keys(session.arbiter_result).length)

const hasAdjudicationReport = (session) =>
  Boolean(session?.adjudication_report && Object.keys(session.adjudication_report).length)

const getClauseTagType = (item) => item?.semantic_tag_type || 'info'

const getClauseLabel = (item) => item?.semantic_display_label || item?.status || '-'

const resolveClauseTooltip = (item) => {
  if (!item) return '暂无说明'
  const reason = item.reason || '暂无原因'
  const hint = item.action_hint || '暂无建议'
  const missing = (item.missing_fields || []).length
    ? item.missing_fields.join(', ')
    : '无'
  return `原因：${reason}\n缺失：${missing}\n建议：${hint}`
}

const getEvidenceByRef = (evidenceRef) => {
  if (!evidenceRef) return null
  const refText = String(evidenceRef)
  const ruleId = refText.startsWith('card_') ? refText.slice(5) : ''
  const evidenceList = Array.isArray(props.session?.evidence) ? props.session.evidence : []
  return evidenceList.find((item) => {
    if (!item || typeof item !== 'object') return false
    return (
      item.evidence_id === refText ||
      item.rule_id === refText ||
      (ruleId && item.rule_id === ruleId)
    )
  }) || null
}

const resolveEvidenceDetail = (evidenceRef) => {
  if (!evidenceRef) return '未提供证据编号'
  const hit = getEvidenceByRef(evidenceRef)
  if (!hit) return `证据编号：${evidenceRef}\n未找到对应证据内容`

  const lines = [
    `证据编号：${evidenceRef}`,
    `条款：${hit.rule_id || '-'}`,
    `描述：${hit.target || '-'}`,
    `摘要：${hit.result_summary || '暂无摘要'}`,
  ]
  if (hit.diagnostic_detail) lines.push(`诊断：${hit.diagnostic_detail}`)
  return lines.join('\n')
}

const getEvidenceStatusTag = (item) => {
  if (!item) return { type: 'info', text: '未定位' }
  if (item.manual_verified) return { type: 'warning', text: '人工复核' }
  if (item.supports_conclusion === true) return { type: 'success', text: '支持结论' }
  if (item.supports_conclusion === false) return { type: 'danger', text: '反对结论' }
  if (item.exec_status === 'no_data') return { type: 'info', text: '无命中' }
  if (item.exec_status === 'failed' || item.exec_status === 'field_missing') {
    return { type: 'danger', text: '查询异常' }
  }
  return { type: 'warning', text: '待仲裁' }
}

const getDecisiveEvidenceCards = (session) => {
  const refs = Array.isArray(session?.arbiter_result?.decisive_evidence_refs)
    ? session.arbiter_result.decisive_evidence_refs
    : []
  return refs.map((ref) => ({ ref, item: getEvidenceByRef(ref) })).filter((row) => row.ref)
}

const getFocusClauseIds = (session) => {
  const ids = Array.isArray(session?.adjudication_report?.debate_digest?.focus_clauses)
    ? session.adjudication_report.debate_digest.focus_clauses
    : []
  return new Set(ids)
}

const getClausePriorityBadges = (item, focusClauseIds) => {
  const badges = []
  if (focusClauseIds.has(item?.clause_id)) badges.push({ type: 'danger', text: '有分歧' })
  if ((item?.evidence_refs || []).some((ref) => getEvidenceByRef(ref)?.manual_verified)) {
    badges.push({ type: 'warning', text: '人工复核' })
  }
  if (item?.semantic_decision_effect === 'oppose') badges.push({ type: 'danger', text: '决定性' })
  if (item?.status === '待补充' || item?.status === '待补证' || item?.semantic_is_missing_data) {
    badges.push({ type: 'warning', text: '待补证' })
  }
  return badges
}

const getImportantClauses = (session) => {
  const rows = Array.isArray(session?.adjudication_report?.clause_results)
    ? [...session.adjudication_report.clause_results]
    : []
  const focusClauseIds = getFocusClauseIds(session)
  const score = (item) => {
    let value = 0
    if (focusClauseIds.has(item?.clause_id)) value += 4
    if (item?.semantic_decision_effect === 'oppose') value += 3
    if (item?.status === '待补充' || item?.status === '待补证' || item?.semantic_is_missing_data) value += 2
    if ((item?.evidence_refs || []).some((ref) => getEvidenceByRef(ref)?.manual_verified)) value += 1
    return value
  }
  return rows.sort((a, b) => score(b) - score(a)).slice(0, 6)
}

const getAgentPanels = (session) => ([
  {
    key: 'support',
    title: '支持结论的 Agent 观点',
    type: 'success',
    items: Array.isArray(session?.arbiter_result?.supporting_points)
      ? session.arbiter_result.supporting_points
      : [],
    empty: '当前没有支持结论的归纳要点',
  },
  {
    key: 'oppose',
    title: '反对/保留的 Agent 观点',
    type: 'danger',
    items: Array.isArray(session?.arbiter_result?.opposing_points)
      ? session.arbiter_result.opposing_points
      : [],
    empty: '当前没有明显的反方或保留意见',
  },
])

const openEvidenceDetail = (evidenceRef) => {
  evidenceDetailText.value = resolveEvidenceDetail(evidenceRef)
  evidenceDetailVisible.value = true
}
</script>

<template>
  <div v-if="!props.session" class="session-empty">
    <div class="session-empty-copy">左侧选择历史会话，或输入身份证号发起新的实时分析。</div>
  </div>

  <div v-else class="session-view">
    <el-card class="session-overview" shadow="never">
      <div class="session-overview-head">
        <div>
          <div class="session-title">
            {{ props.session.view_source === 'live' ? '当前实时会话' : '历史会话详情' }}
          </div>
          <div class="session-subtitle">
            身份证号：{{ props.session.id_card || '未提供' }}
          </div>
        </div>

        <div class="session-tags">
          <el-button
            v-if="props.session.view_source !== 'live'"
            type="primary"
            plain
            size="small"
            :disabled="props.liveLoading || props.sessionLoading"
            @click="emit('restart', props.session)"
          >
            重新发起辩论
          </el-button>
          <a
            v-if="canDownloadOfficialReport(props.session)"
            class="official-report-button"
            :href="resolveOfficialReportUrl(props.session)"
            :download="resolveOfficialReportFilename(props.session)"
            target="_blank"
            rel="noopener"
          >
            下载政府公文 PDF
          </a>
          <el-tag :type="props.session.view_source === 'live' ? 'primary' : 'info'" effect="plain">
            {{ props.session.view_source === 'live' ? '实时分析' : '已保存会话' }}
          </el-tag>
          <el-tag type="info" effect="plain">
            {{ props.session.source_endpoint || '未知来源' }}
          </el-tag>
        </div>
      </div>

      <div class="session-meta-grid">
        <div class="meta-card">
          <div class="meta-label">会话 ID</div>
          <div class="meta-value mono">{{ props.session.session_id || '实时生成中' }}</div>
        </div>
        <div class="meta-card">
          <div class="meta-label">完成时间</div>
          <div class="meta-value">{{ formatDateTime(props.session.completed_at) }}</div>
        </div>
        <div class="meta-card">
          <div class="meta-label">辩论轮次</div>
          <div class="meta-value">{{ props.session.rounds_taken ?? 0 }}</div>
        </div>
        <div class="meta-card">
          <div class="meta-label">共识比例</div>
          <div class="meta-value">{{ Math.round((props.session.consensus_rate ?? 0) * 100) }}%</div>
        </div>
      </div>

      <div class="session-status-row">
        <el-tag :type="getConclusionTagType(props.session.final_conclusion, props.session.final_conclusion_tag_type)" size="large">
          最终结论：{{ props.session.final_conclusion || '分析中' }}
        </el-tag>
        <el-tag :type="props.session.is_consensus_reached ? 'success' : 'warning'" effect="plain" size="large">
          {{ props.session.is_consensus_reached ? '已达成共识' : '多数意见收敛中' }}
        </el-tag>
      </div>

      <div v-if="props.liveLoading || props.sessionLoading" class="session-loading">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>{{ props.liveLoading ? '正在更新实时会话...' : '正在加载历史详情...' }}</span>
      </div>
    </el-card>

    <section
      v-if="(props.currentView === 'all' || props.currentView === 'cognition') && props.session.system_traces && props.session.system_traces.length"
      class="session-section"
    >
      <div class="section-heading">
        <div class="section-title">推理轨迹 (Cognition Trace)</div>
        <div class="section-subtitle">动态取证与代理思考工作流可视化</div>
      </div>
      <div class="trace-console">
        <div
          v-for="(trace, index) in props.session.system_traces"
          :key="index"
          class="trace-line"
          :class="`trace-${trace.status || 'info'}`"
        >
          <span class="trace-prompt">>_</span>
          <span class="trace-text">{{ trace.log }}</span>
        </div>
        <div v-if="props.session.status === 'running'" class="trace-line trace-pulse">
          <span class="trace-prompt">>_</span>
          <span class="cursor-blink">▋</span>
        </div>
      </div>
    </section>

    <section v-if="props.currentView === 'all' || props.currentView === 'cognition'" class="session-section">
      <div class="section-heading">
        <div class="section-title">证据面板</div>
        <div class="section-subtitle">复用同一套证据渲染，支持实时与历史会话</div>
      </div>
      <EvidenceBoard v-if="props.session.evidence?.length" :items="props.session.evidence" />
      <el-empty v-else description="当前会话暂无证据项" />
    </section>

    <section
      v-if="props.currentView === 'tribunal' && props.session.persona && Object.keys(props.session.persona).length"
      class="session-section"
    >
      <div class="section-heading">
        <div class="section-title">人物画像</div>
        <div class="section-subtitle">仅在辩论界面展示对象画像、核心意图与实质争议</div>
      </div>
      <PersonaProfileCard :profile="props.session.persona" />
    </section>

    <section v-if="props.currentView === 'all' || props.currentView === 'tribunal'" class="session-section">
      <div class="section-heading">
        <div class="section-title">辩论过程</div>
        <div class="section-subtitle">按轮次查看各 Agent 的判断与推理</div>
      </div>

      <div v-if="hasJudgments(props.session)" class="round-list">
        <div
          v-for="roundRecord in props.session.history"
          :key="roundRecord.round_num"
          v-show="roundRecord.judgments?.length"
          class="round-block"
        >
          <el-divider content-position="left">
            <el-tag :type="roundRecord.round_num === 0 ? 'primary' : 'danger'" effect="light">
              {{ roundRecord.round_num === 0 ? 'Round 1 初始判断' : `Round ${Number(roundRecord.round_num) + 1} 辩论回合` }}
            </el-tag>
          </el-divider>

          <div class="round-cards">
            <AgentCard
              v-for="judgment in roundRecord.judgments"
              :key="`${judgment.agent_id}-${roundRecord.round_num}`"
              :judgment="judgment"
              :is-debate="roundRecord.round_num > 0"
            />
          </div>
        </div>
      </div>

      <el-empty v-else description="当前会话还没有可展示的辩论记录" />
    </section>

    <section
      v-if="(props.currentView === 'all' || props.currentView === 'verdict') && props.session.final_conclusion"
      class="session-section"
    >
      <div class="section-heading">
        <div class="section-title">最终裁决</div>
        <div class="section-subtitle">先看结论，再看依据、分歧与重点条款</div>
      </div>

      <el-card class="final-card" shadow="always">
        <div class="final-card-main">
          <div class="final-label">结论</div>
          <div class="final-conclusion">{{ props.session.final_conclusion }}</div>
          <div class="final-stance">{{ props.session.final_stance || '待定' }}</div>
        </div>

        <div class="final-side">
          <el-progress
            type="circle"
            :percentage="Math.round((props.session.consensus_rate ?? 0) * 100)"
            :color="props.session.is_consensus_reached ? '#2E7D5B' : '#A06A2A'"
            :width="90"
          />
        </div>
      </el-card>

      <div v-if="hasAdjudicationReport(props.session) || hasArbiterResult(props.session)" class="verdict-grid">
        <el-card v-if="hasAdjudicationReport(props.session)" class="verdict-panel" shadow="never">
          <template #header>
            <div class="panel-head">
              <div class="panel-title">最终裁决依据</div>
              <el-tag type="info" effect="plain">
                置信度 {{ Math.round(((props.session.adjudication_report?.summary?.confidence ?? 0) * 100)) }}%
              </el-tag>
            </div>
          </template>
          <div class="verdict-summary">
            {{ props.session.adjudication_report?.summary?.top_reason || props.session.arbiter_result?.summary || '暂无裁决摘要' }}
          </div>
          <div class="verdict-reasoning">
            {{ props.session.arbiter_result?.why_majority_holds || '暂无多数意见解释' }}
          </div>
          <div v-if="(props.session.adjudication_report?.next_actions || []).length" class="action-list">
            <div
              v-for="(action, index) in props.session.adjudication_report.next_actions"
              :key="`action-${index}`"
              class="action-item"
            >
              <el-tag size="small" effect="plain">{{ action.type || '建议' }}</el-tag>
              <div class="action-copy">
                <div class="action-title">{{ action.title }}</div>
                <div class="action-detail">{{ action.detail }}</div>
              </div>
            </div>
          </div>
        </el-card>

        <el-card v-if="hasArbiterResult(props.session)" class="verdict-panel" shadow="never">
          <template #header>
            <div class="panel-head">
              <div class="panel-title">Agent 分歧面板</div>
              <el-tag :type="props.session.is_consensus_reached ? 'success' : 'warning'" effect="plain">
                {{ props.session.is_consensus_reached ? '多数意见已稳定' : '仍有保留分歧' }}
              </el-tag>
            </div>
          </template>
          <div class="disagreement-grid">
            <div
              v-for="panel in getAgentPanels(props.session)"
              :key="panel.key"
              class="disagreement-col"
            >
              <div class="disagreement-title">
                <el-tag :type="panel.type" effect="dark" size="small">{{ panel.title }}</el-tag>
              </div>
              <div
                v-for="(item, index) in panel.items"
                :key="`${panel.key}-${index}`"
                class="disagreement-item"
              >
                {{ item }}
              </div>
              <div v-if="!panel.items.length" class="arbiter-empty">
                {{ panel.empty }}
              </div>
            </div>
          </div>
          <div class="arbiter-footnote">
            {{ props.session.arbiter_result?.summary || '暂无仲裁总结' }}
          </div>
        </el-card>
      </div>
    </section>

    <section
      v-if="(props.currentView === 'all' || props.currentView === 'verdict') && hasArbiterResult(props.session)"
      class="session-section"
    >
      <div class="section-heading">
        <div class="section-title">关键采纳证据</div>
        <div class="section-subtitle">直接展示仲裁阶段最终采用的证据，不再只看编号</div>
      </div>

      <div v-if="getDecisiveEvidenceCards(props.session).length" class="evidence-highlight-grid">
        <el-card
          v-for="row in getDecisiveEvidenceCards(props.session)"
          :key="row.ref"
          class="evidence-highlight-card"
          shadow="never"
        >
          <div class="evidence-highlight-head">
            <div>
              <div class="evidence-highlight-id">{{ row.item?.rule_id || row.ref }}</div>
              <div class="evidence-highlight-target">{{ row.item?.target || '未找到对应证据内容' }}</div>
            </div>
            <el-tag :type="getEvidenceStatusTag(row.item).type" effect="plain">
              {{ getEvidenceStatusTag(row.item).text }}
            </el-tag>
          </div>
          <div class="evidence-highlight-summary">
            {{ row.item?.result_summary || '当前证据仅保留引用编号，请从证据面板查看详情。' }}
          </div>
          <div class="evidence-highlight-meta">
            <span>引用：{{ row.ref }}</span>
            <span v-if="row.item?.manual_verified">来源：人工补证覆盖</span>
            <span v-else>来源：系统取证</span>
          </div>
          <el-button text type="primary" class="evidence-detail-trigger" @click="openEvidenceDetail(row.ref)">
            查看证据详情
          </el-button>
        </el-card>
      </div>
      <el-empty v-else description="暂无关键采纳证据" />
    </section>

    <section
      v-if="(props.currentView === 'all' || props.currentView === 'verdict') && hasAdjudicationReport(props.session)"
      class="session-section"
    >
      <div class="section-heading">
        <div class="section-title">重点条款</div>
        <div class="section-subtitle">优先展示决定结果、有分歧、待补证或人工复核的条款</div>
      </div>

      <el-card class="report-card" shadow="never">
        <div
          v-for="item in getImportantClauses(props.session)"
          :key="item.clause_id"
          class="clause-row"
        >
          <div class="clause-head">
            <div class="clause-title-row">
              <el-tag effect="plain" size="small">{{ item.clause_id }}</el-tag>
              <el-tooltip placement="top" effect="light">
                <template #content>
                  <div class="tooltip-pre">{{ resolveClauseTooltip(item) }}</div>
                </template>
                <el-tag :type="getClauseTagType(item)" size="small">{{ getClauseLabel(item) }}</el-tag>
              </el-tooltip>
            </div>
            <div class="clause-badges">
              <el-tag
                v-for="badge in getClausePriorityBadges(item, getFocusClauseIds(props.session))"
                :key="`${item.clause_id}-${badge.text}`"
                :type="badge.type"
                effect="plain"
                size="small"
              >
                {{ badge.text }}
              </el-tag>
            </div>
          </div>
          <div class="clause-text">{{ item.clause_text }}</div>
          <div class="clause-reason">{{ item.reason }}</div>
        </div>
        <div v-if="!getImportantClauses(props.session).length" class="arbiter-empty">
          暂无条款结果
        </div>
      </el-card>
    </section>

    <section
      v-if="(props.currentView === 'all' || props.currentView === 'verdict') && hasArbiterResult(props.session)"
      class="session-section"
    >
      <div class="section-heading">
        <div class="section-title">剩余风险</div>
        <div class="section-subtitle">保留仲裁阶段的风险提示，辅助答辩展示系统审慎性</div>
      </div>

      <el-card class="arbiter-card" shadow="never">
        <div
          v-for="(item, index) in props.session.arbiter_result.remaining_risks || []"
          :key="`risk-${index}`"
          class="arbiter-item"
        >
          {{ item }}
        </div>
        <div v-if="!(props.session.arbiter_result.remaining_risks || []).length" class="arbiter-empty">
          暂无剩余风险
        </div>
      </el-card>
    </section>

    <el-dialog v-model="evidenceDetailVisible" title="证据详情" width="620px" append-to-body>
      <div class="tooltip-pre">{{ evidenceDetailText }}</div>
    </el-dialog>
  </div>
</template>

<style scoped>
.session-empty {
  min-height: 360px;
  border: 1px dashed var(--border-color);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.01);
}

.session-empty-copy {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 360px;
  color: var(--text-dim);
  font-size: 14px;
}

.session-view {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.session-overview-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.session-title {
  font-size: 22px;
  font-weight: 800;
  color: var(--text-primary);
}

.session-subtitle {
  margin-top: 6px;
  color: var(--text-muted);
}

.session-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.official-report-button,
.official-report-inline {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 24px;
  padding: 5px 11px;
  border: 1px solid var(--el-color-success-light-5);
  border-radius: 999px;
  background: var(--el-color-success-light-9);
  color: var(--el-color-success);
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
  text-decoration: none;
}

.official-report-button:hover,
.official-report-inline:hover {
  border-color: var(--el-color-success);
  background: var(--el-color-success-light-8);
}

.session-meta-grid {
  margin-top: 18px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.meta-card {
  padding: 14px;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  background: var(--bg-card-alt);
}

.meta-label {
  font-size: 12px;
  color: var(--text-muted);
}

.meta-value {
  margin-top: 8px;
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  word-break: break-word;
}

.mono {
  font-family: Consolas, Monaco, monospace;
  font-size: 12px;
}

.session-status-row {
  margin-top: 18px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.session-loading {
  margin-top: 16px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--text-muted);
}

.trace-console {
  background:
    linear-gradient(180deg, rgba(239, 246, 255, 0.86), rgba(248, 250, 252, 0.92)),
    rgba(47, 95, 159, 0.08);
  border: 1px solid rgba(47, 95, 159, 0.16);
  border-radius: 12px;
  padding: 16px;
  backdrop-filter: blur(4px);
  font-family: Consolas, Monaco, monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #243447;
  max-height: 280px;
  overflow-y: auto;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.55);
}

.trace-line {
  display: flex;
  gap: 10px;
  margin-bottom: 6px;
  animation: fadeIn 0.3s ease-in-out;
}

.trace-prompt {
  color: rgba(47, 95, 159, 0.82);
  font-weight: bold;
  flex-shrink: 0;
}

.trace-text {
  word-break: break-all;
}

.trace-success .trace-text {
  color: #2E7D5B;
}

.trace-warning .trace-text {
  color: #A06A2A;
}

.trace-danger .trace-text {
  color: #9F1D22;
}

.cursor-blink {
  animation: blink 1s step-end infinite;
  color: #2F5F9F;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes blink {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0;
  }
}

.session-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-heading {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.section-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
}

.section-subtitle {
  color: var(--text-muted);
  font-size: 12px;
}

.round-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.round-block {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.round-cards {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.final-card {
  border-width: 2px;
}

.final-card-main {
  text-align: center;
}

.final-label {
  color: var(--text-muted);
  font-size: 12px;
}

.final-conclusion {
  margin-top: 10px;
  font-size: 40px;
  font-weight: 800;
  color: var(--text-primary);
}

.final-stance {
  margin-top: 8px;
  color: var(--text-muted);
}

.final-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.verdict-grid,
.evidence-highlight-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.verdict-panel,
.report-card,
.arbiter-card,
.evidence-highlight-card {
  border-radius: 16px;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.panel-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}

.verdict-summary {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.6;
}

.verdict-reasoning,
.arbiter-footnote {
  margin-top: 10px;
  color: var(--text-secondary);
  line-height: 1.7;
}

.action-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 14px;
}

.action-item {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 12px;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  background: var(--bg-card-alt);
}

.action-copy {
  min-width: 0;
}

.action-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
}

.action-detail {
  margin-top: 4px;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.disagreement-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.disagreement-col {
  padding: 14px;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  background: var(--bg-card-alt);
}

.disagreement-title {
  margin-bottom: 10px;
}

.disagreement-item {
  margin-top: 8px;
  line-height: 1.65;
  color: var(--text-secondary);
}

.evidence-highlight-card {
  border: 1px solid var(--border-color);
}

.evidence-highlight-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.evidence-highlight-id {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
}

.evidence-highlight-target {
  margin-top: 6px;
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.evidence-highlight-summary {
  margin-top: 12px;
  color: var(--text-primary);
  line-height: 1.7;
}

.evidence-highlight-meta {
  margin-top: 10px;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  color: var(--text-muted);
  font-size: 12px;
}

.evidence-detail-trigger {
  margin-top: 10px;
  padding-left: 0;
}

.clause-row {
  margin-top: 12px;
  padding: 12px;
  border: 1px dashed var(--border-color);
  border-radius: 10px;
  background: var(--bg-card);
}

.clause-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.clause-title-row,
.clause-badges {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.clause-text {
  margin-top: 8px;
  color: var(--text-primary);
  line-height: 1.6;
}

.clause-reason {
  margin-top: 8px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.arbiter-item {
  margin-top: 10px;
  line-height: 1.6;
  color: var(--text-secondary);
}

.arbiter-empty {
  margin-top: 10px;
  color: var(--text-muted);
  font-size: 13px;
}

.tooltip-pre {
  max-width: 360px;
  white-space: pre-wrap;
  line-height: 1.6;
}

@media (max-width: 960px) {
  .session-meta-grid,
  .verdict-grid,
  .evidence-highlight-grid,
  .disagreement-grid {
    grid-template-columns: 1fr;
  }

  .final-card :deep(.el-card__body) {
    flex-direction: column;
    text-align: center;
  }
}

@media (max-width: 600px) {
  .session-meta-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
