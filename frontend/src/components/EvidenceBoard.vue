<script setup>
defineProps({
  items: { type: Array, default: () => [] },
})

const tagByDiagnostic = {
  missing_column: { type: 'danger', text: '查询失败' },
  missing_table: { type: 'danger', text: '查询失败' },
  table_corrupted: { type: 'danger', text: '查询失败' },
  sql_error: { type: 'danger', text: '查询失败' },
  db_connection_error: { type: 'danger', text: '查询失败' },
  query_error: { type: 'danger', text: '查询失败' },
  unknown_error: { type: 'danger', text: '查询失败' },
}

const resolveResultMeta = (item) => {
  const execStatus = String(item?.exec_status || '')
  const diagnosticCode = String(item?.diagnostic_code || '')

  if (execStatus === 'no_data' || diagnosticCode === 'empty_result') {
    return { type: 'info', text: '查询成功但无结果' }
  }

  if (execStatus === 'failed' || execStatus === 'field_missing') {
    return { type: 'danger', text: '错误查询' }
  }

  if (tagByDiagnostic[diagnosticCode]) {
    return tagByDiagnostic[diagnosticCode]
  }

  if (item?.supports_conclusion === true) {
    return { type: 'success', text: '支持证据' }
  }

  if (item?.supports_conclusion === false) {
    return { type: 'danger', text: '反对证据' }
  }

  return { type: 'warning', text: '中性证据' }
}

const SEMANTIC_CATEGORY_CLASS = {
  basic: 'cat-must',
  exclusion: 'cat-excl',
  flexible: 'cat-flex',
  inference: 'cat-flex',
  calculation: 'cat-default',
}

const getCategoryClass = (item) => {
  const semanticCategory = String(item?.semantic_category || '').toLowerCase()
  return SEMANTIC_CATEGORY_CLASS[semanticCategory] || 'cat-default'
}

const getResultColumns = (resultRaw) => {
  if (!resultRaw || resultRaw.length === 0) return []
  return Object.keys(resultRaw[0])
}

const resolveEmptyText = (item) => {
  if (item?.diagnostic_detail) return item.diagnostic_detail
  if (item?.exec_status === 'field_missing') return '查询依赖字段缺失，当前结果不可用。'
  if (item?.exec_status === 'failed') return 'SQL 执行失败，无法获取数据。'
  if (item?.exec_status === 'no_data') return 'SQL 正常执行，但未返回匹配记录。'
  return '查询结果为空，没有匹配记录。'
}
</script>

<template>
  <div class="evidence-list">
    <div
      v-for="item in items"
      :key="`${item.rule_id}-${item.target}`"
      class="evidence-item"
    >
      <div class="evidence-head">
        <div class="head-left">
          <span class="category-badge" :class="getCategoryClass(item)">{{ item.category }}</span>
          <div class="evidence-title">{{ item.target }}</div>
          <div class="evidence-sub">条款编号：{{ item.rule_id }}</div>
        </div>
        <el-tag
          :type="resolveResultMeta(item).type"
          effect="dark"
          size="small"
          class="result-tag"
        >
          {{ resolveResultMeta(item).text }}
        </el-tag>
      </div>

      <div class="evidence-steps">
        <div class="step">
          <div class="step-badge step-1">1</div>
          <div class="step-body">
            <div class="step-label">核查目标 <span class="step-type">自然语言</span></div>
            <div class="step-content step-text">{{ item.target }}</div>
          </div>
        </div>

        <div class="step">
          <div class="step-badge step-2">2</div>
          <div class="step-body">
            <div class="step-label">底层查询脚本 <span class="step-type">SQL</span></div>
            <pre class="step-content step-sql">{{ item.sql || '（无执行脚本）' }}</pre>
          </div>
        </div>

        <div class="step">
          <div class="step-badge step-3">3</div>
          <div class="step-body">
            <div class="step-label">
              SQL 执行结果 <span class="step-type">原始数据</span>
              <span v-if="item.result_raw && item.result_raw.length" class="row-count">{{ item.result_raw.length }} 行</span>
            </div>

            <div v-if="item.result_raw && item.result_raw.length" class="step-content step-table-wrap">
              <table class="result-table">
                <thead>
                  <tr>
                    <th v-for="col in getResultColumns(item.result_raw)" :key="col">{{ col }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, idx) in item.result_raw" :key="idx">
                    <td v-for="col in getResultColumns(item.result_raw)" :key="col">
                      {{ row[col] ?? '-' }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div v-else class="step-content step-empty">
              {{ resolveEmptyText(item) }}
            </div>

            <div v-if="item.diagnostic_hint" class="step-hint">
              排查建议：{{ item.diagnostic_hint }}
            </div>
          </div>
        </div>

        <div class="step">
          <div class="step-badge step-4">4</div>
          <div class="step-body">
            <div class="step-label">智能摘要结论 <span class="step-type">摘要</span></div>
            <div class="step-content step-summary">{{ item.result_summary || '暂无摘要。' }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.evidence-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.evidence-item {
  border: 1px solid var(--border-color);
  border-radius: 12px;
  background: var(--bg-card-alt);
  overflow: hidden;
  animation: fadeInUp 0.35s ease-out;
}

.evidence-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 18px 12px;
  border-bottom: 1px solid var(--border-color);
  background: rgba(255, 255, 255, 0.03);
}

.head-left {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.category-badge {
  display: inline-block;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 99px;
  letter-spacing: 0.4px;
}

.cat-must {
  background: #dbeafe;
  color: #1d4ed8;
}

.cat-excl {
  background: #fee2e2;
  color: #b91c1c;
}

.cat-flex {
  background: #fef9c3;
  color: #92400e;
}

.cat-default {
  background: #f1f5f9;
  color: #475569;
}

.evidence-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.4;
}

.evidence-sub {
  font-size: 11px;
  color: var(--text-muted);
  font-family: Consolas, monospace;
}

.result-tag {
  flex-shrink: 0;
  margin-top: 2px;
}

.evidence-steps {
  display: flex;
  flex-direction: column;
  padding: 16px 18px;
  gap: 12px;
}

.step {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.step-badge {
  flex-shrink: 0;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  font-size: 11px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 2px;
}

.step-1 {
  background: #ede9fe;
  color: #7c3aed;
}

.step-2 {
  background: #dbeafe;
  color: #2563eb;
}

.step-3 {
  background: #dcfce7;
  color: #16a34a;
}

.step-4 {
  background: #fef3c7;
  color: #d97706;
}

.step-body {
  flex: 1;
  min-width: 0;
}

.step-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  margin-bottom: 5px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.step-type {
  font-weight: 600;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  background: rgba(148, 163, 184, 0.15);
  color: var(--text-muted);
  letter-spacing: 0.3px;
}

.row-count {
  font-size: 10px;
  color: #16a34a;
  background: #dcfce7;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 600;
}

.step-content {
  font-size: 13px;
  line-height: 1.6;
  border-radius: 8px;
  word-break: break-all;
}

.step-text {
  color: var(--text-primary);
  padding: 8px 12px;
  background: rgba(148, 163, 184, 0.08);
  border-left: 3px solid #7c3aed;
}

.step-sql {
  font-family: Consolas, Monaco, 'Courier New', monospace;
  font-size: 12px;
  background: #0f172a;
  color: #7dd3fc;
  padding: 10px 14px;
  margin: 0;
  white-space: pre-wrap;
  border-left: 3px solid #2563eb;
  overflow-x: auto;
}

.step-table-wrap {
  overflow-x: auto;
}

.result-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  background: #fff;
}

.result-table th,
.result-table td {
  border: 1px solid #e5e7eb;
  padding: 6px 8px;
  text-align: left;
  vertical-align: top;
}

.result-table th {
  background: #f8fafc;
  font-weight: 700;
  color: #334155;
}

.step-empty {
  padding: 10px 12px;
  background: #fff7ed;
  border-left: 3px solid #f97316;
  color: #9a3412;
}

.step-hint {
  margin-top: 8px;
  font-size: 12px;
  color: #92400e;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
  padding: 8px 10px;
}

.step-summary {
  padding: 10px 12px;
  background: #f8fafc;
  border-left: 3px solid #d97706;
  color: #1e293b;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
