<template>
  <main class="page">
    <BlockingOverlay
      :visible="loading"
      title="正在检索"
      message="正在提取特征并查找相似图像"
      description="CIFAR-10 全量索引较大，检索完成后会自动显示结果。"
    />
    <div class="grid">
      <QueryPanel :loading="loading" @search="handleSearch" @text-search="handleTextSearch" />
      <section class="content">
        <div class="panel summary">
          <div>
            <strong>{{ searchTitle }}</strong>
            <p class="muted">{{ searchSubtitle }}</p>
          </div>
          <div class="summary-actions">
            <el-segmented v-model="displayMode" :options="displayModeOptions" />
            <el-button text :disabled="!hasSavedState" @click="clearSavedState">清空缓存</el-button>
          </div>
          <el-statistic title="耗时(ms)" :value="elapsed" :precision="2" />
        </div>
        <ResultGrid :hits="hits" :display-mode="displayMode" @select="loadHistogram" />
        <HistogramChart :data="histogramData" @type-change="changeHistogramType" />
      </section>
    </div>
  </main>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import BlockingOverlay from '../components/BlockingOverlay.vue'
import QueryPanel from '../components/QueryPanel.vue'
import ResultGrid from '../components/ResultGrid.vue'
import HistogramChart from '../components/HistogramChart.vue'
import { fetchHistogram, searchByFile, searchByText } from '../api/cbir'
import { useAppStore } from '../store/useAppStore'

const SEARCH_CACHE_KEY = 'cbir-search-state-v2'

const store = useAppStore()
const loading = ref(false)
const hits = ref([])
const elapsed = ref(0)
const selectedHit = ref(null)
const histogramType = ref('hsv')
const histogramData = ref(null)
const hasSavedState = ref(false)
const restoredDataset = ref('')
const lastQuery = ref(defaultQuery())
const displayMode = ref(localStorage.getItem('cbir-search-display-mode') || 'original')
const displayModeOptions = [
  { label: '原始尺寸', value: 'original' },
  { label: '平滑放大', value: 'smooth' }
]

const searchTitle = computed(() => (lastQuery.value.mode === 'text' ? 'CLIP 文本搜图' : '图像特征检索'))
const searchSubtitle = computed(() => {
  if (lastQuery.value.mode === 'text') {
    if (lastQuery.value.translated && lastQuery.value.clipText) {
      return `文本查询：${lastQuery.value.text}；CLIP 英文检索词：${lastQuery.value.clipText}`
    }
    return lastQuery.value.text ? `文本查询：${lastQuery.value.text}` : '可上传图片或输入文本进行检索。'
  }
  if (lastQuery.value.calibrated) {
    return `已启用 CIFAR-10 分布外校准：CIFAR 置信度 ${percentText(lastQuery.value.cifarConfidence)}，分数缩放 ${percentText(lastQuery.value.scoreScale)}，CLIP 判断 ${lastQuery.value.gatePrompt}`
  }
  return '传统特征、深度特征、CLIP 与综合检索统一切换。'
})

async function handleSearch(payload) {
  loading.value = true
  try {
    const data = await searchByFile({
      dataset: store.currentDataset,
      file: payload.file,
      feature: payload.feature,
      metric: payload.metric,
      weights: payload.weights
    })
    hits.value = data.hits
    elapsed.value = data.elapsed_ms
    lastQuery.value = {
      mode: 'image',
      text: '',
      clipText: '',
      translated: false,
      calibrated: Boolean(data.query?.score_calibrated),
      cifarConfidence: data.query?.cifar10_confidence ?? null,
      scoreScale: data.query?.score_scale ?? null,
      gatePrompt: data.query?.clip_gate_top_prompt || '',
      feature: payload.feature,
      metric: payload.metric
    }
    selectedHit.value = hits.value[0] || null
    if (selectedHit.value) {
      await loadHistogram(selectedHit.value)
    }
    saveState()
  } finally {
    loading.value = false
  }
}

async function handleTextSearch(payload) {
  loading.value = true
  try {
    const data = await searchByText({
      dataset: store.currentDataset,
      text: payload.text
    })
    hits.value = data.hits
    elapsed.value = data.elapsed_ms
    lastQuery.value = {
      mode: 'text',
      text: data.query?.text || payload.text,
      clipText: data.query?.clip_text || payload.text,
      translated: Boolean(data.query?.translated),
      calibrated: false,
      cifarConfidence: null,
      scoreScale: null,
      gatePrompt: '',
      feature: 'clip_text',
      metric: 'cosine'
    }
    selectedHit.value = hits.value[0] || null
    if (selectedHit.value) {
      await loadHistogram(selectedHit.value)
    }
    saveState()
  } finally {
    loading.value = false
  }
}

async function loadHistogram(hit) {
  selectedHit.value = hit
  histogramData.value = await fetchHistogram({
    dataset: store.currentDataset,
    imageId: hit.image_id,
    type: histogramType.value
  })
  saveState()
}

async function changeHistogramType(type) {
  histogramType.value = type
  if (selectedHit.value) {
    await loadHistogram(selectedHit.value)
  } else {
    saveState()
  }
}

function saveState() {
  const payload = {
    dataset: store.currentDataset,
    hits: hits.value,
    elapsed: elapsed.value,
    selectedHit: selectedHit.value,
    histogramType: histogramType.value,
    histogramData: histogramData.value,
    lastQuery: lastQuery.value,
    displayMode: displayMode.value,
    savedAt: new Date().toISOString()
  }
  localStorage.setItem(SEARCH_CACHE_KEY, JSON.stringify(payload))
  hasSavedState.value = true
}

function restoreState() {
  const raw = localStorage.getItem(SEARCH_CACHE_KEY)
  hasSavedState.value = Boolean(raw)
  if (!raw) return
  try {
    const payload = JSON.parse(raw)
    if (payload.dataset && payload.dataset !== store.currentDataset) return
    restoredDataset.value = payload.dataset || store.currentDataset
    hits.value = Array.isArray(payload.hits) ? payload.hits : []
    elapsed.value = Number(payload.elapsed || 0)
    selectedHit.value = payload.selectedHit || null
    histogramType.value = payload.histogramType || histogramType.value
    histogramData.value = payload.histogramData || null
    lastQuery.value = payload.lastQuery || defaultQuery()
    displayMode.value = payload.displayMode || displayMode.value
  } catch {
    localStorage.removeItem(SEARCH_CACHE_KEY)
    hasSavedState.value = false
  }
}

function clearSavedState(showMessage = true) {
  localStorage.removeItem(SEARCH_CACHE_KEY)
  hasSavedState.value = false
  hits.value = []
  elapsed.value = 0
  selectedHit.value = null
  histogramData.value = null
  lastQuery.value = defaultQuery()
  if (showMessage) {
    ElMessage.success('检索缓存已清空')
  }
}

function defaultQuery() {
  return {
    mode: 'image',
    text: '',
    clipText: '',
    translated: false,
    calibrated: false,
    cifarConfidence: null,
    scoreScale: null,
    gatePrompt: '',
    feature: '',
    metric: ''
  }
}

function percentText(value) {
  if (value === null || value === undefined || value === '') return '-'
  return `${(Number(value) * 100).toFixed(1)}%`
}

watch(displayMode, (value) => {
  localStorage.setItem('cbir-search-display-mode', value)
  saveState()
})

watch(
  () => store.currentDataset,
  (dataset) => {
    if (restoredDataset.value && restoredDataset.value !== dataset) {
      clearSavedState(false)
    }
  }
)

onMounted(restoreState)
</script>

<style scoped>
.content {
  display: grid;
  gap: 16px;
}

.summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.summary p {
  margin: 6px 0 0;
}

.summary-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

@media (max-width: 900px) {
  .summary,
  .summary-actions {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
