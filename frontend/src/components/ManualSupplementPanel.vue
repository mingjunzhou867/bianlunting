<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  session: { type: Object, default: null },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['submit-supplement', 'rerun-review'])

const selectedClauseId = ref('')
const selectedStance = ref('support')
const supplementText = ref('')

const clauseResults = computed(() => {
  if (!props.session?.adjudication_report?.clause_results) return []
  return Array.isArray(props.session.adjudication_report.clause_results)
    ? props.session.adjudication_report.clause_results
    : []
})

const supplementItems = computed(() => (
  Array.isArray(props.session?.manual_supplements) ? props.session.manual_supplements : []
))

const pendingCount = computed(() => (
  supplementItems.value.filter((item) => item?.status === 'pending_review').length
))

const canSubmit = computed(() => (
  !props.disabled && Boolean(selectedClauseId.value) && Boolean(supplementText.value.trim())
))

watch(
  () => clauseResults.value,
  (rows) => {
    if (!rows.length) {
      selectedClauseId.value = ''
      return
    }
    if (!rows.some((row) => row?.clause_id === selectedClauseId.value)) {
      selectedClauseId.value = rows[0]?.clause_id || ''
    }
  },
  { immediate: true, deep: true },
)

const findClauseById = (clauseId) => (
  clauseResults.value.find((item) => item?.clause_id === clauseId) || null
)

const statusText = (status) => {
  if (status === 'pending_review') return '已提交待复核'
  if (status === 'adopted') return '已采纳'
  if (status === 'not_adopted') return '未采纳'
  return status || '未知状态'
}

const statusTagType = (status) => {
  if (status === 'pending_review') return 'warning'
  if (status === 'adopted') return 'success'
  if (status === 'not_adopted') return 'danger'
  return 'info'
}

const stanceText = (stance) => {
  if (stance === 'support') return '支持该条款'
  if (stance === 'refute') return '反驳该条款'
  return '人工核验'
}

const formatDateTime = (value) => {
  if (!value) return '-'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return String(value)
  return parsed.toLocaleString('zh-CN', { hour12: false })
}

const handleSubmit = () => {
  if (!canSubmit.value) return
  const clause = findClauseById(selectedClauseId.value)
  emit('submit-supplement', {
    clause_id: selectedClauseId.value,
    clause_text: clause?.clause_text || '',
    baseline_status: clause?.semantic_display_label || clause?.status || '',
    baseline_effect: clause?.semantic_decision_effect || '',
    detail: supplementText.value.trim(),
    stance: selectedStance.value,
  })
  supplementText.value = ''
}

const handleRerun = () => {
  if (props.disabled) return
  emit('rerun-review')
}
</script>

<template>
  <el-card class="manual-panel" shadow="never">
    <template #header>
      <div class="manual-panel-head">
        <div>
          <div class="manual-panel-title">补证复核</div>
          <div class="manual-panel-subtitle">
            人工核验证据优先级最高。提交后进入“已提交待复核”，重新复核后会直接按人工核验结果采纳。
          </div>
        </div>
        <el-button
          type="primary"
          plain
          :disabled="props.disabled || pendingCount === 0"
          @click="handleRerun"
        >
          重新复核 ({{ pendingCount }})
        </el-button>
      </div>
    </template>

    <div class="manual-form">
      <el-select
        v-model="selectedClauseId"
        placeholder="选择要补证的条款"
        :disabled="props.disabled || !clauseResults.length"
        filterable
        class="manual-form-item"
      >
        <el-option
          v-for="clause in clauseResults"
          :key="clause.clause_id"
          :label="`${clause.clause_id} | ${clause.semantic_display_label || clause.status || '-'}`"
          :value="clause.clause_id"
        />
      </el-select>

      <el-select
        v-model="selectedStance"
        :disabled="props.disabled"
        class="manual-form-item manual-form-item--stance"
      >
        <el-option label="支持该条款（人工确认满足）" value="support" />
        <el-option label="反驳该条款（人工确认不满足）" value="refute" />
      </el-select>

      <el-input
        v-model="supplementText"
        type="textarea"
        :rows="3"
        resize="vertical"
        placeholder="请输入人工核验结论与说明（高置信度，将覆盖同条款系统证据）"
        :disabled="props.disabled"
      />

      <div class="manual-form-actions">
        <el-button type="primary" :disabled="!canSubmit" @click="handleSubmit">
          提交补证
        </el-button>
      </div>
    </div>

    <el-divider />

    <div class="manual-list">
      <div v-if="!supplementItems.length" class="manual-empty">
        暂无补证记录
      </div>
      <div v-for="item in supplementItems" :key="item.supplement_id" class="manual-item">
        <div class="manual-item-head">
          <div class="manual-item-title">{{ item.clause_id || '-' }}</div>
          <el-tag :type="statusTagType(item.status)" size="small">
            {{ statusText(item.status) }}
          </el-tag>
        </div>
        <div class="manual-item-detail">{{ item.detail || '-' }}</div>
        <div class="manual-item-meta">
          <span>提交时间: {{ formatDateTime(item.submitted_at) }}</span>
          <span>立场: {{ stanceText(item.stance) }}</span>
          <span>基线状态: {{ item.baseline_status || '-' }}</span>
        </div>
        <div class="manual-item-review">复核说明: {{ item.review_reason || '-' }}</div>
      </div>
    </div>
  </el-card>
</template>

<style scoped>
.manual-panel {
  margin-top: 16px;
  border-radius: 16px;
}

.manual-panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.manual-panel-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.manual-panel-subtitle {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.5;
}

.manual-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.manual-form-item {
  width: 100%;
}

.manual-form-item--stance {
  max-width: 320px;
}

.manual-form-actions {
  display: flex;
  justify-content: flex-end;
}

.manual-empty {
  color: var(--text-muted);
  font-size: 13px;
}

.manual-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.manual-item {
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 10px 12px;
  background: var(--bg-card-alt);
}

.manual-item-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.manual-item-title {
  font-weight: 700;
  color: var(--text-primary);
}

.manual-item-detail {
  margin-top: 8px;
  line-height: 1.6;
  color: var(--text-primary);
  white-space: pre-wrap;
}

.manual-item-meta {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  color: var(--text-muted);
  font-size: 12px;
}

.manual-item-review {
  margin-top: 8px;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.6;
}

@media (max-width: 960px) {
  .manual-panel-head {
    flex-direction: column;
    align-items: stretch;
  }

  .manual-form-item--stance {
    max-width: none;
  }
}
</style>

