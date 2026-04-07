<script setup>
defineProps({
  items: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  activeIdCard: { type: String, default: '' },
  selectedSessionId: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['select'])

const formatDateTime = (value) => {
  if (!value) {
    return '未完成'
  }

  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }

  return parsed.toLocaleString('zh-CN', { hour12: false })
}

const resolveConclusionType = (conclusion) => {
  if (conclusion === '符合') {
    return 'success'
  }
  if (conclusion === '不符合') {
    return 'danger'
  }
  return 'warning'
}

const POLICY_DISPLAY = {
  'POLICY_001': { name: '灵活就业补贴', color: '#409eff' },
  'POLICY_002': { name: '失业补贴', color: '#e6a23c' },
  'POLICY_003': { name: '主动服务', color: '#67c23a' },
}

const policyLabel = (policyId) => {
  return POLICY_DISPLAY[policyId]?.name ?? policyId ?? '未标记'
}

const policyTagType = (policyId) => {
  if (policyId === 'POLICY_001') return 'primary'
  if (policyId === 'POLICY_002') return 'warning'
  if (policyId === 'POLICY_003') return 'success'
  return 'info'
}
</script>

<template>
  <div class="history-shell">
    <div class="history-header">
      <div>
        <div class="history-title">历史会话</div>
        <div class="history-subtitle">
          系统的所有历史记录
        </div>
      </div>

      <el-tag type="info" size="small" effect="plain">
        {{ items.length }} 条
      </el-tag>
    </div>

    <el-alert
      v-if="error"
      type="warning"
      :closable="false"
      show-icon
      class="history-alert"
    >
      {{ error }}
    </el-alert>

    <el-scrollbar class="history-scroll">
      <div class="history-list">
        <div v-if="loading && !items.length" class="history-state">
          正在加载历史会话...
        </div>

        <div v-else-if="!items.length" class="history-state">
          系统尚无已保存的历史记录。
        </div>

        <button
          v-for="item in items"
          :key="item.session_id"
          type="button"
          class="history-item"
          :class="{ 'history-item--active': item.session_id === selectedSessionId }"
          :disabled="disabled"
          @click="emit('select', item.session_id)"
        >
          <div class="history-item-head">
            <div class="history-item-tags">
              <el-tag :type="resolveConclusionType(item.final_conclusion)" size="small">
                {{ item.final_conclusion || '待定' }}
              </el-tag>
              <el-tag :type="policyTagType(item.policy_id)" size="small" effect="plain">
                {{ policyLabel(item.policy_id) }}
              </el-tag>
            </div>
            <span class="history-time">{{ formatDateTime(item.completed_at) }}</span>
          </div>

          <div class="history-stance">{{ item.final_stance || '暂无立场' }}</div>

          <div class="history-meta">
            <span>身份证: {{ item.id_card }}</span>
            <span>{{ item.source_endpoint || '未知来源' }}</span>
            <span>{{ item.rounds_taken ?? 0 }} 轮</span>
            <span>{{ Math.round((item.consensus_rate ?? 0) * 100) }}%</span>
          </div>
        </button>
      </div>
    </el-scrollbar>
  </div>
</template>

<style scoped>
.history-shell {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.history-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 16px;
  border-bottom: 1px solid var(--border-color);
}

.history-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.history-subtitle {
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.6;
}

.history-alert {
  margin: 12px;
  margin-bottom: 0;
}

.history-scroll {
  flex: 1;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
}

.history-state {
  padding: 18px 12px;
  border: 1px dashed var(--border-color);
  border-radius: 12px;
  color: var(--text-dim);
  font-size: 13px;
  line-height: 1.7;
}

.history-item {
  width: 100%;
  padding: 14px;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  background: var(--bg-card);
  color: inherit;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.2s ease, transform 0.2s ease, background 0.2s ease;
}

.history-item:hover:not(:disabled) {
  border-color: var(--accent-blue);
  transform: translateY(-1px);
}

.history-item:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.history-item--active {
  border-color: var(--accent-blue);
  background: rgba(88, 166, 255, 0.08);
}

.history-item-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.history-item-tags {
  display: flex;
  gap: 6px;
  align-items: center;
}

.history-time {
  font-size: 12px;
  color: var(--text-muted);
}

.history-stance {
  margin-top: 10px;
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
}

.history-meta {
  margin-top: 10px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 12px;
  color: var(--text-muted);
}
</style>
