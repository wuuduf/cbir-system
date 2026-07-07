<template>
  <main class="page">
    <BlockingOverlay
      :visible="loading"
      title="正在评估"
      message="正在计算 mAP、P@K 和 PR 曲线"
      description="评估期间页面操作会暂时锁定，完成后自动恢复。"
    />

    <section class="panel eval-tools">
      <div class="tool-row">
        <div class="feature-strip">
          <el-segmented v-model="feature" :options="featureOptions" :disabled="loading" />
        </div>
        <el-select v-model="metric" style="width: 150px" :disabled="loading">
          <el-option label="余弦" value="cosine" />
          <el-option label="欧氏" value="euclidean" />
          <el-option label="直方图相交" value="intersection" />
          <el-option label="加权距离" value="weighted" />
        </el-select>
        <el-input-number v-model="k" :min="1" :max="100" controls-position="right" :disabled="loading" />
        <el-input-number
          v-model="sample"
          :min="10"
          :max="5000"
          :step="10"
          controls-position="right"
          :disabled="loading"
        />
        <el-button type="primary" :loading="loading" @click="runEvaluate">评估当前特征</el-button>
      </div>

      <div class="compare-box">
        <div class="compare-head">
          <div>
            <strong>同场对比</strong>
            <span>在同一数据集、K 值、样本数和相似度设置下，对多个特征进行横向比较。</span>
          </div>
          <el-button type="primary" plain :loading="loading" @click="runCompare">评估对比特征</el-button>
        </div>
        <div class="compare-scroll">
          <el-checkbox-group v-model="compareFeatures" :disabled="loading">
            <el-checkbox-button
              v-for="option in featureOptions"
              :key="option.value"
              :label="option.value"
            >
              {{ option.label }}
            </el-checkbox-button>
          </el-checkbox-group>
        </div>
      </div>

      <div v-if="summaryCards.length" class="summary">
        <div v-for="card in summaryCards" :key="card.title" class="summary-card">
          <span>{{ card.title }}</span>
          <strong>{{ card.value }}</strong>
          <small>{{ card.detail }}</small>
        </div>
      </div>

      <div v-if="selectedDeepModel && !comparisonResults.length" class="deep-model-banner">
        <strong>当前模型：{{ selectedDeepModel.name }}</strong>
        <span>
          {{ deepModelKind(selectedDeepModel) }}
          <template v-if="selectedDeepModel.best_acc"> · acc {{ numberText(selectedDeepModel.best_acc) }}</template>
          <template v-if="selectedDeepModel.best_p_at_k"> · P@K {{ numberText(selectedDeepModel.best_p_at_k) }}</template>
        </span>
      </div>
    </section>

    <MetricChart :result="result" :comparison-results="comparisonResults" />

    <section v-if="comparisonResults.length" class="panel comparison-table">
      <div class="section-title">
        <strong>对比结果</strong>
        <span>数值越高表示检索效果越好，耗时越低表示计算越快。</span>
      </div>
      <el-table :data="comparisonResults" stripe>
        <el-table-column prop="label" label="特征" min-width="120" />
        <el-table-column prop="metric" label="相似度" width="110" />
        <el-table-column label="mAP" width="110">
          <template #default="{ row }">{{ row.map.toFixed(4) }}</template>
        </el-table-column>
        <el-table-column :label="`P@${k}`" width="110">
          <template #default="{ row }">{{ row.p_at_k.toFixed(4) }}</template>
        </el-table-column>
        <el-table-column label="样本数" width="100">
          <template #default="{ row }">{{ row.query_count }}</template>
        </el-table-column>
        <el-table-column label="耗时(ms)" width="110">
          <template #default="{ row }">{{ Math.round(row.elapsed_ms) }}</template>
        </el-table-column>
      </el-table>
    </section>

    <section v-if="result || comparisonResults.length" class="panel ai-panel">
      <div class="section-title">
        <strong>AI 结果分析</strong>
        <span>把当前评估指标发送给后端配置的 DeepSeek 模型，生成文字分析。</span>
      </div>
      <div class="ai-actions">
        <el-button type="primary" :loading="analysisLoading" @click="runAnalysis">生成分析</el-button>
        <el-button text @click="$router.push('/admin')">API 配置</el-button>
        <el-button text :disabled="!hasSavedState" @click="clearSavedState">清空缓存</el-button>
      </div>
      <div v-if="analysis" class="analysis-content">
        <MarkdownRenderer :content="analysis" />
      </div>
      <el-alert
        v-else
        type="info"
        show-icon
        :closable="false"
        title="AI 分析只读取评估指标，不会读取或上传 API Key。"
      />
    </section>

    <section v-if="result || comparisonResults.length" class="panel conclusion">
      <strong>实验结论</strong>
      <p>{{ conclusionText }}</p>
    </section>
  </main>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref, watch } from 'vue'
import { analyzeEvaluation, evaluateFeature, fetchDeepModels } from '../api/cbir'
import BlockingOverlay from '../components/BlockingOverlay.vue'
import MarkdownRenderer from '../components/MarkdownRenderer.vue'
import MetricChart from '../components/MetricChart.vue'
import { useAppStore } from '../store/useAppStore'

const EVALUATE_CACHE_KEY = 'cbir-evaluate-state-v2'

const store = useAppStore()
const feature = ref('deep_triplet')
const metric = ref('cosine')
const k = ref(12)
const sample = ref(100)
const loading = ref(false)
const analysisLoading = ref(false)
const result = ref(null)
const comparisonResults = ref([])
const analysis = ref('')
const deepModels = ref([])
const compareFeatures = ref(['color_hist', 'lbp', 'deep_cnn', 'deep_triplet', 'clip'])
const restoredDataset = ref('')
const hasSavedState = ref(false)

const featureOptions = [
  { label: 'HSV', value: 'color_hist' },
  { label: '颜色矩', value: 'color_moments' },
  { label: 'GLCM', value: 'glcm' },
  { label: 'LBP', value: 'lbp' },
  { label: 'Hu', value: 'hu' },
  { label: 'EOH', value: 'eoh' },
  { label: 'CNN 深度', value: 'deep_cnn' },
  { label: 'Triplet', value: 'deep_triplet' },
  { label: 'DINOv2', value: 'dinov2' },
  { label: 'CLIP', value: 'clip' }
]

const featureLabel = computed(() => labelOf(feature.value))
const selectedDeepModel = computed(() => {
  if (feature.value === 'deep_cnn') {
    return deepModels.value.find((model) => model.name === 'cifar_resnet18.pt') || null
  }
  if (feature.value === 'deep_triplet') {
    return deepModels.value.find((model) => model.name === 'cifar_resnet18_metric.pt') || null
  }
  return null
})

const evaluatedRows = computed(() => {
  if (comparisonResults.value.length) return comparisonResults.value
  return result.value ? [result.value] : []
})

const summaryCards = computed(() => {
  const rows = evaluatedRows.value
  if (!rows.length) return []
  if (comparisonResults.value.length) {
    const bestMap = bestBy(rows, 'map')
    const bestPk = bestBy(rows, 'p_at_k')
    const fastest = bestBy(rows, 'elapsed_ms', false)
    const avgMap = rows.reduce((sum, item) => sum + Number(item.map || 0), 0) / rows.length
    return [
      { title: '最高 mAP', value: bestMap.map.toFixed(4), detail: bestMap.label },
      { title: `最高 P@${k.value}`, value: bestPk.p_at_k.toFixed(4), detail: bestPk.label },
      { title: '最快耗时', value: `${Math.round(fastest.elapsed_ms)} ms`, detail: fastest.label },
      { title: '对比规模', value: `${rows.length} 组`, detail: `平均 mAP ${avgMap.toFixed(4)}` }
    ]
  }
  const current = rows[0]
  return [
    { title: 'mAP', value: current.map.toFixed(4), detail: current.label },
    { title: `P@${current.k}`, value: current.p_at_k.toFixed(4), detail: current.metric },
    { title: '样本数', value: String(current.query_count), detail: store.currentDataset },
    { title: '耗时', value: `${Math.round(current.elapsed_ms)} ms`, detail: '单特征评估' }
  ]
})

const conclusionText = computed(() => {
  if (comparisonResults.value.length) {
    const rows = comparisonResults.value
    const bestMap = bestBy(rows, 'map')
    const bestPk = bestBy(rows, 'p_at_k')
    const fastest = bestBy(rows, 'elapsed_ms', false)
    return `本次在 ${store.currentDataset} 上共对比 ${rows.length} 个特征。${bestMap.label} 的 mAP 最高，为 ${bestMap.map.toFixed(4)}；${bestPk.label} 的 P@${bestPk.k} 最高，为 ${bestPk.p_at_k.toFixed(4)}；${fastest.label} 耗时最低，约 ${Math.round(fastest.elapsed_ms)} ms。`
  }
  if (!result.value) return ''
  return `${featureLabel.value} 在 ${store.currentDataset} 上的 mAP 为 ${result.value.map.toFixed(4)}，P@${result.value.k} 为 ${result.value.p_at_k.toFixed(4)}。`
})

async function runEvaluate() {
  loading.value = true
  try {
    const data = await evaluateFeature({
      dataset: store.currentDataset,
      feature: feature.value,
      metric: metric.value,
      k: k.value,
      sample: sample.value
    })
    result.value = withLabel(data)
    comparisonResults.value = []
    analysis.value = ''
    saveState()
    ElMessage.success('评估完成')
  } finally {
    loading.value = false
  }
}

async function runCompare() {
  if (!compareFeatures.value.length) {
    ElMessage.warning('请至少选择一个对比特征')
    return
  }
  loading.value = true
  try {
    const rows = []
    for (const item of compareFeatures.value) {
      const data = await evaluateFeature({
        dataset: store.currentDataset,
        feature: item,
        metric: metricForFeature(item),
        k: k.value,
        sample: sample.value
      })
      rows.push(withLabel(data))
    }
    comparisonResults.value = rows
    result.value = rows[0] || null
    analysis.value = ''
    saveState()
    ElMessage.success('对比评估完成')
  } finally {
    loading.value = false
  }
}

async function runAnalysis() {
  const items = comparisonResults.value.length ? comparisonResults.value : result.value ? [result.value] : []
  if (!items.length) {
    ElMessage.warning('请先完成评估')
    return
  }
  analysisLoading.value = true
  try {
    const response = await analyzeEvaluation({
      dataset: store.currentDataset,
      metric: metric.value,
      sample: sample.value,
      items: items.map((item) => ({
        feature: item.feature,
        feature_label: item.label || labelOf(item.feature),
        metric: item.metric,
        map: item.map,
        p_at_k: item.p_at_k,
        k: item.k,
        query_count: item.query_count,
        elapsed_ms: item.elapsed_ms,
        pr_curve: item.pr_curve || []
      }))
    })
    analysis.value = response.content
    saveState()
    ElMessage.success('AI 分析完成')
  } finally {
    analysisLoading.value = false
  }
}

watch(
  () => store.currentDataset,
  (dataset) => {
    if (restoredDataset.value && restoredDataset.value !== dataset) {
      result.value = null
      comparisonResults.value = []
      analysis.value = ''
      clearSavedState(false)
    }
  }
)

watch(feature, (value) => {
  if (value === 'deep_cnn' || value === 'deep_triplet' || value === 'clip' || value === 'dinov2') {
    metric.value = 'cosine'
  }
  saveState()
})

watch([metric, k, sample, compareFeatures], saveState, { deep: true })

function saveState() {
  const payload = {
    dataset: store.currentDataset,
    feature: feature.value,
    metric: metric.value,
    k: k.value,
    sample: sample.value,
    compareFeatures: compareFeatures.value,
    result: result.value,
    comparisonResults: comparisonResults.value,
    analysis: analysis.value,
    savedAt: new Date().toISOString()
  }
  localStorage.setItem(EVALUATE_CACHE_KEY, JSON.stringify(payload))
  hasSavedState.value = true
}

function restoreState() {
  const raw = localStorage.getItem(EVALUATE_CACHE_KEY)
  hasSavedState.value = Boolean(raw)
  if (!raw) return
  try {
    const payload = JSON.parse(raw)
    if (payload.dataset && payload.dataset !== store.currentDataset) return
    restoredDataset.value = payload.dataset || store.currentDataset
    feature.value = payload.feature || feature.value
    metric.value = payload.metric || metric.value
    k.value = Number(payload.k || k.value)
    sample.value = Number(payload.sample || sample.value)
    compareFeatures.value = Array.isArray(payload.compareFeatures) ? payload.compareFeatures : compareFeatures.value
    result.value = payload.result || null
    comparisonResults.value = Array.isArray(payload.comparisonResults) ? payload.comparisonResults : []
    analysis.value = payload.analysis || ''
  } catch {
    localStorage.removeItem(EVALUATE_CACHE_KEY)
    hasSavedState.value = false
  }
}

function clearSavedState(showMessage = true) {
  localStorage.removeItem(EVALUATE_CACHE_KEY)
  hasSavedState.value = false
  if (showMessage) {
    result.value = null
    comparisonResults.value = []
    analysis.value = ''
    ElMessage.success('评估缓存已清空')
  }
}

function metricForFeature(value) {
  if (value === 'color_hist' || value === 'lbp' || value === 'eoh') return metric.value
  return metric.value === 'intersection' ? 'cosine' : metric.value
}

function bestBy(rows, key, highIsBest = true) {
  return [...rows].sort((a, b) => {
    const diff = Number(a[key] || 0) - Number(b[key] || 0)
    return highIsBest ? -diff : diff
  })[0]
}

function withLabel(data) {
  return { ...data, label: labelOf(data.feature) }
}

function labelOf(value) {
  return featureOptions.find((item) => item.value === value)?.label || value
}

function deepModelKind(model) {
  return model.training_objective ? 'Triplet 度量学习模型' : '分类 CNN 模型'
}

function numberText(value) {
  return Number(value).toFixed(4)
}

onMounted(async () => {
  restoreState()
  try {
    const data = await fetchDeepModels()
    deepModels.value = data.models || []
  } catch {
    deepModels.value = []
  }
})
</script>

<style scoped>
.eval-tools {
  display: grid;
  gap: 18px;
  min-width: 0;
  margin-bottom: 18px;
  overflow: hidden;
}

.tool-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  min-width: 0;
}

.feature-strip,
.compare-scroll {
  max-width: 100%;
  min-width: 0;
  overflow-x: auto;
  overflow-y: hidden;
  padding-bottom: 2px;
  scrollbar-width: thin;
}

.feature-strip {
  flex: 1 1 100%;
}

.feature-strip :deep(.el-segmented),
.compare-scroll :deep(.el-checkbox-group) {
  width: max-content;
  min-width: max-content;
}

.compare-box {
  display: grid;
  gap: 12px;
  min-width: 0;
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: color-mix(in srgb, var(--control-bg), #2563eb 4%);
}

.compare-head,
.section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.compare-head div,
.section-title {
  min-width: 0;
}

.compare-head span,
.section-title span {
  display: block;
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 14px;
}

.summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.summary-card {
  min-width: 0;
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--control-bg);
}

.summary-card span,
.summary-card small {
  display: block;
  color: var(--text-muted);
}

.summary-card strong {
  display: block;
  margin: 6px 0;
  color: var(--text);
  font-size: 26px;
  line-height: 1.1;
}

.summary-card small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.deep-model-banner {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid color-mix(in srgb, #0f766e, transparent 68%);
  border-radius: 8px;
  background: color-mix(in srgb, var(--control-bg), #0f766e 7%);
}

.deep-model-banner span {
  color: var(--text-muted);
}

.comparison-table,
.ai-panel,
.conclusion {
  margin-top: 18px;
  min-width: 0;
}

.ai-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin: 14px 0;
}

.analysis-content {
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--control-bg);
}

.conclusion p {
  margin: 8px 0 0;
  color: var(--text-muted);
}

@media (max-width: 980px) {
  .summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .eval-tools {
    gap: 14px;
    padding: 12px;
  }

  .tool-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    align-items: stretch;
    gap: 10px;
  }

  .feature-strip {
    grid-column: 1 / -1;
  }

  .tool-row :deep(.el-select),
  .tool-row :deep(.el-input-number) {
    width: 100% !important;
  }

  .tool-row > .el-button {
    grid-column: 1 / -1;
    width: 100%;
  }

  .compare-box {
    padding: 12px;
  }

  .compare-head > .el-button {
    width: 100%;
  }

  .summary {
    grid-template-columns: 1fr;
  }

  .compare-head,
  .section-title {
    align-items: flex-start;
    flex-direction: column;
  }

  .deep-model-banner {
    align-items: flex-start;
    flex-direction: column;
  }

  .comparison-table {
    overflow-x: auto;
  }

  .comparison-table :deep(.el-table) {
    min-width: 680px;
  }
}
</style>
