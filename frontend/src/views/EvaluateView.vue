<template>
  <main class="page">
    <BlockingOverlay
      :visible="loading"
      title="正在评估"
      message="正在计算 mAP、P@K 和 PR 曲线"
      description="评估期间已锁定页面操作，完成后会自动恢复。"
    />
    <section class="panel eval-tools">
      <div class="tool-row">
        <el-segmented v-model="feature" :options="featureOptions" :disabled="loading" />
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
        <el-button type="primary" :loading="loading" @click="runEvaluate">评估</el-button>
      </div>
      <div v-if="result" class="summary">
        <el-statistic title="mAP" :value="result.map" :precision="4" />
        <el-statistic :title="`P@${result.k}`" :value="result.p_at_k" :precision="4" />
        <el-statistic title="样本数" :value="result.query_count" />
        <el-statistic title="耗时(ms)" :value="Math.round(result.elapsed_ms)" />
      </div>
    </section>

    <MetricChart :result="result" />

    <section v-if="result" class="panel conclusion">
      <strong>实验结论</strong>
      <p>
        {{ featureLabel }} 在 {{ store.currentDataset }} 上的 mAP 为
        {{ result.map.toFixed(4) }}，P@{{ result.k }} 为
        {{ result.p_at_k.toFixed(4) }}。
      </p>
    </section>
  </main>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { computed, ref, watch } from 'vue'
import { evaluateFeature } from '../api/cbir'
import BlockingOverlay from '../components/BlockingOverlay.vue'
import MetricChart from '../components/MetricChart.vue'
import { useAppStore } from '../store/useAppStore'

const store = useAppStore()
const feature = ref('deep')
const metric = ref('cosine')
const k = ref(12)
const sample = ref(100)
const loading = ref(false)
const result = ref(null)

const featureOptions = [
  { label: 'HSV', value: 'color_hist' },
  { label: '颜色矩', value: 'color_moments' },
  { label: 'GLCM', value: 'glcm' },
  { label: 'LBP', value: 'lbp' },
  { label: 'Hu', value: 'hu' },
  { label: 'EOH', value: 'eoh' },
  { label: '深度', value: 'deep' },
  { label: 'CLIP', value: 'clip' }
]

const featureLabel = computed(() => {
  return featureOptions.find((item) => item.value === feature.value)?.label || feature.value
})

async function runEvaluate() {
  loading.value = true
  try {
    result.value = await evaluateFeature({
      dataset: store.currentDataset,
      feature: feature.value,
      metric: metric.value,
      k: k.value,
      sample: sample.value
    })
    ElMessage.success('评估完成')
  } finally {
    loading.value = false
  }
}

watch(
  () => store.currentDataset,
  () => {
    result.value = null
  }
)

watch(feature, (value) => {
  if (value === 'deep' || value === 'clip') {
    metric.value = 'cosine'
  }
})

</script>

<style scoped>
.eval-tools {
  display: grid;
  gap: 18px;
  margin-bottom: 18px;
}

.tool-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.conclusion {
  margin-top: 18px;
}

.conclusion p {
  margin: 8px 0 0;
  color: var(--text-muted);
}

@media (max-width: 760px) {
  .summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
