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
          <el-statistic title="耗时(ms)" :value="elapsed" :precision="2" />
        </div>
        <ResultGrid :hits="hits" @select="loadHistogram" />
        <HistogramChart :data="histogramData" @type-change="changeHistogramType" />
      </section>
    </div>
  </main>
</template>

<script setup>
import { computed, ref } from 'vue'
import BlockingOverlay from '../components/BlockingOverlay.vue'
import QueryPanel from '../components/QueryPanel.vue'
import ResultGrid from '../components/ResultGrid.vue'
import HistogramChart from '../components/HistogramChart.vue'
import { fetchHistogram, searchByFile, searchByText } from '../api/cbir'
import { useAppStore } from '../store/useAppStore'

const store = useAppStore()
const loading = ref(false)
const hits = ref([])
const elapsed = ref(0)
const selectedHit = ref(null)
const histogramType = ref('hsv')
const histogramData = ref(null)
const lastQuery = ref({ mode: 'image', text: '', clipText: '', translated: false })

const searchTitle = computed(() => (lastQuery.value.mode === 'text' ? 'CLIP 文本搜图' : '图像特征检索'))
const searchSubtitle = computed(() => {
  if (lastQuery.value.mode === 'text') {
    if (lastQuery.value.translated && lastQuery.value.clipText) {
      return `文本查询：${lastQuery.value.text}；CLIP 英文检索词：${lastQuery.value.clipText}`
    }
    return `文本查询：${lastQuery.value.text}`
  }
  return '传统特征、深度特征、CLIP 与综合检索统一切换。'
})

async function handleSearch(payload) {
  loading.value = true
  try {
    const result = await searchByFile({
      dataset: store.currentDataset,
      file: payload.file,
      feature: payload.feature,
      metric: payload.metric,
      weights: payload.weights
    })
    hits.value = result.hits
    elapsed.value = result.elapsed_ms
    lastQuery.value = { mode: 'image', text: '', clipText: '', translated: false }
    selectedHit.value = hits.value[0] || null
    if (selectedHit.value) {
      await loadHistogram(selectedHit.value)
    }
  } finally {
    loading.value = false
  }
}

async function handleTextSearch(payload) {
  loading.value = true
  try {
    const result = await searchByText({
      dataset: store.currentDataset,
      text: payload.text
    })
    hits.value = result.hits
    elapsed.value = result.elapsed_ms
    lastQuery.value = {
      mode: 'text',
      text: result.query?.text || payload.text,
      clipText: result.query?.clip_text || payload.text,
      translated: Boolean(result.query?.translated)
    }
    selectedHit.value = hits.value[0] || null
    if (selectedHit.value) {
      await loadHistogram(selectedHit.value)
    }
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
}

async function changeHistogramType(type) {
  histogramType.value = type
  if (selectedHit.value) {
    await loadHistogram(selectedHit.value)
  }
}
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
</style>
