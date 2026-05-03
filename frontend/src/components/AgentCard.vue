<script setup>
defineProps({
  judgment: { type: Object, required: true },
  isDebate: { type: Boolean, default: false },
})

const ROLE_META = {
  '严格合规 Agent': { short: '严' },
  '宽松业务 Agent': { short: '宽' },
  '审计挑战 Agent': { short: '审' },
  '探索分析 Agent': { short: '探' },
}

const FACT_LABELS = {
  BASIC_001: '基础身份核验',
  BASIC_002: '困难身份核验',
  BASIC_003: '就业登记核验',
  BASIC_004: '社保身份核验',
  BASIC_005: '生命状态核验',
  EMP_SYNC: '就业登记同步',
  CHANGE_LOG: '险种变更日志',
  PAY_102: '灵活就业个人缴费',
  BASIC_LIFE: '生命状态冲突',
  SUBSIDY_LOG: '补贴发放记录',
}

const resolveRoleMeta = (role) => ROLE_META[role] ?? { short: '辩' }

const resolveStanceType = (stance) => {
  if (stance === '支持通过') return 'success'
  if (stance === '反对通过') return 'danger'
  return 'warning'
}

const toList = (value) => (Array.isArray(value) ? value : [])

const sanitizeDisplayText = (value) => {
  const text = typeof value === 'string' ? value.trim() : String(value ?? '').trim()
  if (!text) return ''
  if (
    text.startsWith('{') ||
    text.startsWith('[') ||
    /^```(?:json)?/i.test(text) ||
    text.includes('"conclusion"') ||
    text.includes('"stance"')
  ) {
    return '（结构化输出已解析，原始 JSON 已隐藏）'
  }
  return text
}
</script>

<template>
  <el-card shadow="hover" class="agent-card">
    <template #header>
      <div class="agent-header">
        <div class="agent-title">
          <span class="agent-badge">{{ resolveRoleMeta(judgment.agent_role).short }}</span>
          <div>
            <div class="agent-name">{{ judgment.agent_role }}</div>
            <div class="agent-meta">
              <span>结论：{{ judgment.conclusion || '待定' }}</span>
              <span>置信度：{{ Math.round((judgment.confidence ?? 0) * 100) }}%</span>
            </div>
          </div>
        </div>

        <div class="agent-tags">
          <el-tag :type="resolveStanceType(judgment.stance)" effect="light">
            {{ judgment.stance || '待定' }}
          </el-tag>
          <el-tag v-if="isDebate" type="info" effect="plain">
            第 {{ judgment.debate_round }} 轮
          </el-tag>
        </div>
      </div>
    </template>

    <div class="agent-section">
      <div class="section-label">推理说明</div>
      <div class="reasoning-text">{{ sanitizeDisplayText(judgment.reasoning) || '暂无推理说明。' }}</div>
    </div>

    <div v-if="toList(judgment.evidence_refs).length" class="agent-section">
      <div class="section-label">引用证据</div>
      <div class="ref-list">
        <el-tag
          v-for="ref in toList(judgment.evidence_refs)"
          :key="ref"
          size="small"
          type="info"
          effect="plain"
        >
          {{ FACT_LABELS[ref] || ref }}
        </el-tag>
      </div>
    </div>

    <div v-if="judgment.key_finding" class="agent-section">
      <div class="section-label">关键发现</div>
      <div class="finding-text">{{ sanitizeDisplayText(judgment.key_finding) }}</div>
    </div>

    <el-alert
      v-if="toList(judgment.dissent_points).filter(Boolean).length"
      type="warning"
      :closable="false"
      class="dissent-alert"
    >
      <template #title>保留意见</template>
      <ul class="dissent-list">
        <li v-for="point in toList(judgment.dissent_points).filter(Boolean)" :key="point">
          {{ sanitizeDisplayText(point) }}
        </li>
      </ul>
    </el-alert>
  </el-card>
</template>

<style scoped>
.agent-card {
  border-left: 3px solid var(--accent-blue);
}

.agent-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.agent-title {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.agent-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 999px;
  background: var(--bg-card-alt);
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 700;
}

.agent-name {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.agent-meta {
  margin-top: 4px;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  font-size: 12px;
  color: var(--text-muted);
}

.agent-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.agent-section + .agent-section {
  margin-top: 14px;
}

.section-label {
  margin-bottom: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
}

.reasoning-text,
.finding-text {
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--text-primary);
  line-height: 1.75;
}

.reasoning-text {
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(248, 250, 252, 0.5);
}

.ref-list {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.dissent-alert {
  margin-top: 14px;
}

.dissent-list {
  margin: 6px 0 0;
  padding-left: 18px;
  color: var(--text-primary);
}
</style>
