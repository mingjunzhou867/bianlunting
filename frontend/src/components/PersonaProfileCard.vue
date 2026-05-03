<script setup>
const props = defineProps({
  profile: { type: Object, required: true },
})

const toList = (value) => (Array.isArray(value) ? value : [])

const resolveRiskType = (riskLevel) => {
  if (riskLevel === 'low') return 'success'
  if (riskLevel === 'high') return 'danger'
  return 'warning'
}

const resolveRiskLabel = (riskLevel) => {
  if (riskLevel === 'low') return '低'
  if (riskLevel === 'high') return '高'
  return '中'
}

const overview = props.profile?.evidence_overview || {}

const buildFocusItems = (profile) => {
  const items = []

  if (profile?.substantive_dispute) {
    items.push({
      type: 'warning',
      title: '核心争议',
      content: profile.substantive_dispute,
    })
  }

  const disputePoint = toList(profile?.dispute_points)[0]
  if (disputePoint) {
    items.push({
      type: 'danger',
      title: '最可能引发辩论的点',
      content: disputePoint,
    })
  }

  const missingPoint = toList(profile?.missing_signals)[0]
  if (missingPoint) {
    items.push({
      type: 'info',
      title: '当前证据缺口',
      content: missingPoint,
    })
  }

  return items.slice(0, 3)
}

const buildAttentionItems = (profile) => {
  const rows = []

  toList(profile?.risk_signals).slice(0, 2).forEach((item) => {
    rows.push({
      type: 'danger',
      label: '风险信号',
      text: item,
    })
  })

  toList(profile?.missing_signals).slice(0, 2).forEach((item) => {
    rows.push({
      type: 'warning',
      label: '待核实',
      text: item,
    })
  })

  toList(profile?.dispute_points).slice(0, 2).forEach((item) => {
    rows.push({
      type: 'info',
      label: '建议先辩',
      text: item,
    })
  })

  return rows.slice(0, 5)
}
</script>

<template>
  <el-card class="persona-card" shadow="never">
    <div class="persona-head">
      <div class="persona-head-left">
        <div class="persona-tag-row">
          <el-tag v-if="profile.mock_persona_code" type="primary">画像 {{ profile.mock_persona_code }}</el-tag>
          <el-tag type="info" effect="plain">{{ profile.archetype || '未知类型' }}</el-tag>
          <el-tag :type="resolveRiskType(profile.risk_level)" effect="plain">
            争议强度：{{ resolveRiskLabel(profile.risk_level) }}
          </el-tag>
        </div>
        <div class="persona-title">{{ profile.title || '未命名画像' }}</div>
        <div class="persona-summary">{{ profile.summary_line || '暂无画像摘要' }}</div>
      </div>

      <div class="persona-overview">
        <div class="overview-item">
          <div class="overview-label">支持证据数</div>
          <div class="overview-value">{{ overview.supports ?? 0 }}</div>
        </div>
        <div class="overview-item">
          <div class="overview-label">反向证据数</div>
          <div class="overview-value">{{ overview.contradicts ?? 0 }}</div>
        </div>
        <div class="overview-item">
          <div class="overview-label">缺口证据数</div>
          <div class="overview-value">{{ overview.missing ?? 0 }}</div>
        </div>
      </div>
    </div>

    <div class="persona-focus-grid">
      <div class="focus-panel">
        <div class="section-title">本案焦点</div>
        <div v-if="buildFocusItems(profile).length" class="focus-list">
          <div v-for="item in buildFocusItems(profile)" :key="item.title" class="focus-item">
            <el-tag :type="item.type" effect="plain" size="small">{{ item.title }}</el-tag>
            <div class="focus-text">{{ item.content }}</div>
          </div>
        </div>
        <div v-else class="signal-empty">暂无焦点信息</div>
      </div>

      <div class="focus-panel">
        <div class="section-title">辩论前应关注什么</div>
        <div v-if="buildAttentionItems(profile).length" class="attention-list">
          <div v-for="(item, index) in buildAttentionItems(profile)" :key="`${item.label}-${index}`" class="attention-item">
            <el-tag :type="item.type" effect="dark" size="small">{{ item.label }}</el-tag>
            <div class="attention-text">{{ item.text }}</div>
          </div>
        </div>
        <div v-else class="signal-empty">暂无额外提示</div>
      </div>
    </div>

    <div class="persona-core-grid">
      <div class="core-block">
        <div class="core-label">画像</div>
        <div class="core-text">{{ profile.portrait || '暂无' }}</div>
      </div>
      <div class="core-block">
        <div class="core-label">核心意图</div>
        <div class="core-text">{{ profile.core_intent || '暂无' }}</div>
      </div>
      <div class="core-block core-block--wide">
        <div class="core-label">实质争议</div>
        <div class="core-text">{{ profile.substantive_dispute || '暂无' }}</div>
      </div>
    </div>

    <div class="signal-grid">
      <div class="signal-block signal-positive">
        <div class="signal-title">正向信号</div>
        <ul v-if="toList(profile.positive_signals).length" class="signal-list">
          <li v-for="item in toList(profile.positive_signals)" :key="item">{{ item }}</li>
        </ul>
        <div v-else class="signal-empty">暂无</div>
      </div>

      <div class="signal-block signal-risk">
        <div class="signal-title">风险信号</div>
        <ul v-if="toList(profile.risk_signals).length" class="signal-list">
          <li v-for="item in toList(profile.risk_signals)" :key="item">{{ item }}</li>
        </ul>
        <div v-else class="signal-empty">暂无</div>
      </div>

      <div class="signal-block signal-missing">
        <div class="signal-title">缺失信号</div>
        <ul v-if="toList(profile.missing_signals).length" class="signal-list">
          <li v-for="item in toList(profile.missing_signals)" :key="item">{{ item }}</li>
        </ul>
        <div v-else class="signal-empty">暂无</div>
      </div>
    </div>

    <div v-if="toList(profile.dispute_points).length" class="persona-section">
      <div class="section-title">争议拆解</div>
      <div class="dispute-points">
        <div v-for="item in toList(profile.dispute_points)" :key="item" class="dispute-chip">
          {{ item }}
        </div>
      </div>
    </div>

    <div v-if="toList(profile.fact_cards).length" class="persona-section">
      <div class="section-title">案件事实底卡</div>
      <div class="fact-grid">
        <div v-for="fact in toList(profile.fact_cards)" :key="`${fact.label}-${fact.value}`" class="fact-card">
          <div class="fact-label">{{ fact.label }}</div>
          <div class="fact-value">{{ fact.value }}</div>
        </div>
      </div>
    </div>
  </el-card>
</template>

<style scoped>
.persona-card {
  border: 1px solid var(--border-color);
  background: linear-gradient(180deg, rgba(30, 90, 168, 0.04), rgba(255, 255, 255, 0.02));
}

.persona-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 18px;
}

.persona-head-left {
  flex: 1;
  min-width: 0;
}

.persona-tag-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.persona-title {
  margin-top: 12px;
  font-size: 24px;
  font-weight: 800;
  color: var(--text-primary);
  line-height: 1.35;
}

.persona-summary {
  margin-top: 8px;
  color: var(--text-muted);
  line-height: 1.7;
}

.persona-overview {
  display: grid;
  grid-template-columns: repeat(3, minmax(92px, 1fr));
  gap: 10px;
  min-width: 320px;
}

.overview-item {
  padding: 12px;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  background: var(--bg-card);
  text-align: center;
}

.overview-label {
  font-size: 12px;
  color: var(--text-muted);
}

.overview-value {
  margin-top: 8px;
  font-size: 24px;
  font-weight: 800;
  color: var(--text-primary);
}

.persona-focus-grid,
.persona-core-grid,
.signal-grid {
  margin-top: 18px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.signal-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.focus-panel,
.core-block,
.signal-block,
.fact-card {
  padding: 14px;
  border-radius: 12px;
  border: 1px solid var(--border-color);
  background: var(--bg-card);
}

.focus-panel {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.7), rgba(245, 247, 250, 0.9));
}

.focus-list,
.attention-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 10px;
}

.focus-item,
.attention-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.focus-text,
.attention-text,
.core-text {
  line-height: 1.75;
  color: var(--text-primary);
}

.core-block--wide {
  grid-column: 1 / -1;
}

.core-label,
.section-title,
.signal-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-muted);
  letter-spacing: 0.3px;
}

.signal-positive {
  border-left: 3px solid var(--accent-green);
}

.signal-risk {
  border-left: 3px solid var(--accent-red);
}

.signal-missing {
  border-left: 3px solid var(--accent-amber);
}

.signal-list {
  margin: 10px 0 0;
  padding-left: 18px;
  color: var(--text-primary);
  line-height: 1.8;
}

.signal-empty {
  margin-top: 10px;
  color: var(--text-dim);
}

.persona-section {
  margin-top: 18px;
}

.dispute-points {
  margin-top: 10px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.dispute-chip {
  padding: 8px 10px;
  border-radius: 999px;
  background: rgba(197, 139, 43, 0.12);
  color: #C58B2B;
  font-size: 12px;
  line-height: 1.5;
}

.fact-grid {
  margin-top: 10px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.fact-label {
  font-size: 12px;
  color: var(--text-muted);
}

.fact-value {
  margin-top: 8px;
  color: var(--text-primary);
  line-height: 1.7;
  word-break: break-word;
}

@media (max-width: 1200px) {
  .persona-head {
    flex-direction: column;
  }

  .persona-overview {
    width: 100%;
    min-width: 0;
  }

  .persona-focus-grid,
  .persona-core-grid,
  .signal-grid,
  .fact-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .persona-focus-grid,
  .persona-core-grid,
  .signal-grid,
  .fact-grid,
  .persona-overview {
    grid-template-columns: 1fr;
  }
}
</style>
