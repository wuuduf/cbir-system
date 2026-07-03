<template>
  <section class="panel query-panel">
    <el-upload
      drag
      :auto-upload="false"
      :limit="1"
      :on-change="handleChange"
      :on-remove="handleRemove"
      accept="image/jpeg,image/png,image/bmp,image/webp"
    >
      <el-icon class="upload-icon"><UploadFilled /></el-icon>
      <div>拖入或选择查询图片</div>
    </el-upload>

    <img v-if="previewUrl" class="preview" :src="previewUrl" alt="查询图预览" />

    <el-form label-position="top" class="form">
      <el-form-item label="CLIP 文本搜图">
        <div class="text-search">
          <el-input
            v-model="textQuery"
            clearable
            placeholder="例如：红色汽车 / a red car"
            :prefix-icon="Search"
            @keyup.enter="submitText"
          />
          <el-button type="primary" plain :loading="loading" :disabled="!textQuery.trim()" @click="submitText">
            搜图
          </el-button>
        </div>
      </el-form-item>

      <!-- 检索特征按“颜色 / 纹理 / 形状 / 深度与综合”分组展示，对齐实训指导的特征分类。 -->
      <el-form-item label="检索特征">
        <el-radio-group v-model="feature" class="feature-groups">
          <div v-for="group in featureGroups" :key="group.key" class="feature-group">
            <div class="feature-group-head">
              <span class="group-dot" :class="`dot-${group.key}`" />
              <span class="group-name">{{ group.label }}</span>
              <span class="group-desc">{{ group.desc }}</span>
            </div>
            <div class="feature-grid" :style="{ gridTemplateColumns: `repeat(${group.columns}, minmax(0, 1fr))` }">
              <el-radio-button v-for="item in group.items" :key="item.value" :label="item.value">
                {{ item.label }}
              </el-radio-button>
            </div>
          </div>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="相似度">
        <el-select v-model="metric">
          <el-option v-for="item in metricOptions" :key="item.value" :label="metricLabel(item)" :value="item.value" />
        </el-select>
      </el-form-item>
      <div class="metric-hint">
        <strong>{{ selectedFeatureLabel }} 推荐：{{ recommendedMetricLabel }}</strong>
        <p>{{ selectedFeatureTip }}</p>
      </div>
      <div v-if="feature === 'fusion'" class="weights">
        <label v-for="item in weightItems" :key="item.key">
          <span>{{ item.label }} {{ normalizedWeights[item.key].toFixed(2) }}</span>
          <el-slider v-model="weights[item.key]" :min="0" :max="100" />
        </label>
      </div>
      <el-button type="primary" :loading="loading" :disabled="!selectedFile" @click="submit">
        检索
      </el-button>
    </el-form>
  </section>
</template>

<script setup>
import { Search, UploadFilled } from '@element-plus/icons-vue'
import { computed, ref, watch } from 'vue'

const emit = defineEmits(['search', 'text-search'])
defineProps({
  loading: {
    type: Boolean,
    default: false
  }
})

const selectedFile = ref(null)
const previewUrl = ref('')
const textQuery = ref('')
const feature = ref('color_hist')
const metric = ref('intersection')

// 特征按类型分组：颜色 / 纹理 / 形状 / 深度与综合，每组包含若干具体特征。
const featureGroups = [
  {
    key: 'color',
    label: '颜色特征',
    desc: '描述整体色彩分布',
    columns: 2,
    items: [
      {
        value: 'color_hist',
        label: 'HSV 直方图',
        recommendedMetric: 'intersection',
        tip: 'HSV 是归一化直方图，直方图相交最能直接比较颜色分布重叠程度。'
      },
      {
        value: 'color_moments',
        label: '颜色矩',
        recommendedMetric: 'euclidean',
        tip: '颜色矩是均值、方差、偏度等连续统计量，用欧氏距离比较数值差异更直观。'
      }
    ]
  },
  {
    key: 'texture',
    label: '纹理特征',
    desc: '描述表面结构与粗糙度',
    columns: 2,
    items: [
      {
        value: 'glcm',
        label: 'GLCM',
        recommendedMetric: 'euclidean',
        tip: 'GLCM 纹理特征由对比度、相关性、能量、熵等统计量组成，欧氏距离适合比较这些连续特征。'
      },
      {
        value: 'lbp',
        label: 'LBP',
        recommendedMetric: 'intersection',
        tip: 'LBP 输出局部纹理模式直方图，直方图相交适合衡量纹理模式分布重叠。'
      }
    ]
  },
  {
    key: 'shape',
    label: '形状特征',
    desc: '描述边缘与轮廓',
    columns: 2,
    items: [
      {
        value: 'hu',
        label: 'Hu 矩',
        recommendedMetric: 'euclidean',
        tip: 'Hu 矩是形状不变矩数值向量，经过对数压缩后用欧氏距离比较形状差异更合适。'
      },
      {
        value: 'eoh',
        label: '边缘方向直方图',
        recommendedMetric: 'intersection',
        tip: 'EOH 是边缘方向直方图，直方图相交适合比较方向分布是否相似。'
      }
    ]
  },
  {
    key: 'advanced',
    label: '深度与综合',
    desc: '语义特征与多特征融合',
    columns: 3,
    items: [
      {
        value: 'deep',
        label: '深度特征',
        recommendedMetric: 'cosine',
        tip: '深度特征已经做 L2 归一化，余弦相似度能稳定比较语义方向是否接近。'
      },
      {
        value: 'clip',
        label: 'CLIP 图像',
        recommendedMetric: 'cosine',
        tip: 'CLIP 图像特征与文本特征位于同一语义空间，适合语义相似图片检索。'
      },
      {
        value: 'fusion',
        label: '综合特征',
        recommendedMetric: 'weighted',
        tip: '综合特征融合颜色、纹理、形状和深度，使用加权距离最能体现各特征权重。'
      }
    ]
  }
]
const featureOptions = featureGroups.flatMap((group) => group.items)
const metricOptions = [
  { label: '直方图相交', value: 'intersection' },
  { label: '余弦相似度', value: 'cosine' },
  { label: '欧氏距离', value: 'euclidean' },
  { label: '加权距离', value: 'weighted' }
]
// 综合检索默认以颜色/纹理/形状为主，深度可选；这样在没有训练深度模型时也能正常融合。
const weights = ref({
  color: 30,
  texture: 25,
  shape: 25,
  deep: 20
})
const weightItems = [
  { key: 'color', label: '颜色' },
  { key: 'texture', label: '纹理' },
  { key: 'shape', label: '形状' },
  { key: 'deep', label: '深度' }
]

const normalizedWeights = computed(() => {
  const total = Object.values(weights.value).reduce((sum, value) => sum + value, 0) || 1
  return Object.fromEntries(Object.entries(weights.value).map(([key, value]) => [key, value / total]))
})
const selectedFeature = computed(() => featureOptions.find((item) => item.value === feature.value) || featureOptions[0])
const selectedFeatureLabel = computed(() => selectedFeature.value.label)
const selectedFeatureTip = computed(() => selectedFeature.value.tip)
const recommendedMetricLabel = computed(() => {
  return metricOptions.find((item) => item.value === selectedFeature.value.recommendedMetric)?.label || ''
})

watch(feature, () => {
  metric.value = selectedFeature.value.recommendedMetric
})

function metricLabel(item) {
  return item.value === selectedFeature.value.recommendedMetric ? `${item.label}（推荐）` : item.label
}

function handleChange(uploadFile) {
  selectedFile.value = uploadFile.raw
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
  }
  previewUrl.value = URL.createObjectURL(uploadFile.raw)
}

function handleRemove() {
  selectedFile.value = null
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
  }
  previewUrl.value = ''
}

function submit() {
  if (selectedFile.value) {
    emit('search', {
      file: selectedFile.value,
      feature: feature.value,
      metric: metric.value,
      weights: feature.value === 'fusion' ? normalizedWeights.value : null
    })
  }
}

function submitText() {
  const text = textQuery.value.trim()
  if (text) {
    emit('text-search', { text })
  }
}
</script>

<style scoped>
.query-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.upload-icon {
  font-size: 28px;
  color: var(--accent);
  transition: transform 180ms ease;
}

:deep(.el-upload-dragger) {
  border-radius: 8px;
  background:
    linear-gradient(135deg, rgba(37, 99, 235, 0.08), rgba(15, 118, 110, 0.07)),
    var(--panel-solid);
  border-color: rgba(37, 99, 235, 0.24);
  transition:
    border-color 180ms ease,
    box-shadow 180ms ease,
    transform 180ms ease;
}

:deep(.el-upload-dragger:hover) {
  border-color: var(--accent);
  box-shadow: 0 14px 28px rgba(37, 99, 235, 0.12);
  transform: translateY(-2px);
}

:deep(.el-upload-dragger:hover) .upload-icon {
  transform: translateY(-2px) scale(1.05);
}

.preview {
  width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: contain;
  border: 1px solid var(--panel-border);
  border-radius: 8px;
  background: var(--control-bg);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.04);
  animation: preview-in 220ms ease both;
}

.form {
  display: grid;
  gap: 4px;
}

.text-search {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
  width: 100%;
}

/* 特征分组：每组一个标题条 + 一组按钮，视觉上按类型分区。 */
.feature-groups {
  display: grid;
  gap: 12px;
  width: 100%;
}

.feature-group {
  display: grid;
  gap: 8px;
  padding: 10px;
  border: 1px solid var(--panel-border);
  border-radius: 8px;
  background: color-mix(in srgb, var(--control-bg), var(--accent) 3%);
}

.feature-group-head {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.group-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  transform: translateY(1px);
}

.dot-color {
  background: #ef4444;
}

.dot-texture {
  background: #f59e0b;
}

.dot-shape {
  background: #0f766e;
}

.dot-advanced {
  background: #2563eb;
}

.group-name {
  font-size: 13px;
  font-weight: 700;
}

.group-desc {
  font-size: 12px;
  color: var(--text-muted);
}

.metric-hint {
  display: grid;
  gap: 4px;
  padding: 10px 12px;
  margin-top: 4px;
  border: 1px solid color-mix(in srgb, var(--accent), transparent 70%);
  border-radius: 8px;
  background: color-mix(in srgb, var(--control-bg), var(--accent) 5%);
}

.metric-hint strong {
  font-size: 13px;
}

.metric-hint p {
  margin: 0;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.5;
}

.weights {
  display: grid;
  gap: 8px;
  padding: 10px;
  margin-top: 6px;
  border: 1px solid var(--panel-border);
  border-radius: 8px;
  background: color-mix(in srgb, var(--control-bg), var(--accent) 4%);
}

.weights label {
  display: grid;
  gap: 4px;
  font-size: 13px;
}

:deep(.feature-grid) {
  display: grid;
  gap: 8px;
}

:deep(.el-radio-button__inner) {
  width: 100%;
  border-left: 1px solid var(--el-border-color);
  border-radius: 6px;
}

@keyframes preview-in {
  from {
    opacity: 0;
    transform: scale(0.98);
  }

  to {
    opacity: 1;
    transform: scale(1);
  }
}

@media (max-width: 520px) {
  .text-search {
    grid-template-columns: 1fr;
  }
}
</style>
