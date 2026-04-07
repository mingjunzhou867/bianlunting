<script setup>
import AgentCard from './AgentCard.vue'
import EvidenceBoard from './EvidenceBoard.vue'

const props = defineProps({
  session: { type: Object, default: null },
  liveLoading: { type: Boolean, default: false },
  sessionLoading: { type: Boolean, default: false },
  currentView: { type: String, default: 'all' },
})

const emit = defineEmits(['restart'])

const formatDateTime = (value) => {
  if (!value) {
    return '未记录'
  }

  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }

  return parsed.toLocaleString('zh-CN', { hour12: false })
}

const hasJudgments = (session) =>
  Array.isArray(session?.history) &&
  session.history.some((round) => Array.isArray(round?.judgments) && round.judgments.length > 0)

const resolveConclusionType = (conclusion) => {
  if (conclusion === '符合') {
    return 'success'
  }
  if (conclusion === '不符合') {
    return 'danger'
  }
  return 'warning'
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
        <el-tag :type="resolveConclusionType(props.session.final_conclusion)" size="large">
          最终结论：{{ props.session.final_conclusion || '分析中' }}
        </el-tag>
        <el-tag :type="props.session.is_consensus_reached ? 'success' : 'warning'" effect="plain" size="large">
          {{ props.session.is_consensus_reached ? '已达成共识' : '多数意见收敛' }}
        </el-tag>
      </div>

      <div v-if="props.liveLoading || props.sessionLoading" class="session-loading">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>{{ props.liveLoading ? '正在更新实时会话...' : '正在加载历史详情...' }}</span>
      </div>
    </el-card>

    <section v-if="(props.currentView === 'all' || props.currentView === 'cognition') && props.session.system_traces && props.session.system_traces.length" class="session-section">
      <div class="section-heading">
        <div class="section-title">智理追踪 (Cognition Trace)</div>
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
          <span class="cursor-blink">██</span>
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
              {{ roundRecord.round_num === 0 ? 'Round 0 初始判断' : `Round ${roundRecord.round_num} 辩论回合` }}
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

    <section v-if="(props.currentView === 'all' || props.currentView === 'tribunal') && props.session.final_conclusion" class="session-section">
      <div class="section-heading">
        <div class="section-title">最终判定</div>
        <div class="section-subtitle">展示本次会话的最终结论与立场</div>
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
            :color="props.session.is_consensus_reached ? '#3fb950' : '#d29922'"
            :width="90"
          />
        </div>
      </el-card>
    </section>
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
  background: rgba(10, 15, 20, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 16px;
  backdrop-filter: blur(10px);
  font-family: Consolas, Monaco, monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #a0aec0;
  max-height: 280px;
  overflow-y: auto;
  box-shadow: inset 0 0 20px rgba(0, 0, 0, 0.5);
}

.trace-line {
  display: flex;
  gap: 10px;
  margin-bottom: 6px;
  animation: fadeIn 0.3s ease-in-out;
}

.trace-prompt {
  color: #4299e1;
  font-weight: bold;
  flex-shrink: 0;
}

.trace-text {
  word-break: break-all;
}

.trace-success .trace-text { color: #48bb78; }
.trace-warning .trace-text { color: #ecc94b; }
.trace-danger .trace-text { color: #f56565; }

.cursor-blink {
  animation: blink 1s step-end infinite;
  color: #4299e1;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
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
  font-size: 18px;
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

@media (max-width: 960px) {
  .session-meta-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
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
