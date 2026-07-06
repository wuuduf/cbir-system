<template>
  <main class="page video-page">
    <BlockingOverlay
      :visible="busy"
      :title="busyTitle"
      message="正在处理视频关键帧、特征或检索结果"
      description="视频任务会比图片检索更耗时，完成后页面会自动刷新。"
    />

    <section class="panel header-panel">
      <div>
        <strong>视频检索</strong>
        <p class="muted">上传视频抽取关键帧，建立视频索引，再用图片检索相似视频。</p>
      </div>
      <div class="header-actions">
        <div class="mini-stat">
          <span>视频库</span>
          <strong>{{ total }}</strong>
        </div>
        <div class="mini-stat">
          <span>结果</span>
          <strong>{{ hits.length }}</strong>
        </div>
        <el-button :loading="busy" @click="loadVideos">刷新</el-button>
        <el-button text :disabled="!hasSavedState" @click="clearSavedState">清空缓存</el-button>
      </div>
    </section>

    <section class="workspace-grid">
      <section class="panel tool-panel">
        <div class="panel-head">
          <strong>视频管理</strong>
          <span class="muted">导入视频并抽取关键帧</span>
        </div>

        <div class="settings-row">
          <label class="setting-item">
            <span>关键帧间隔（秒）</span>
            <el-input-number v-model="uploadForm.intervalSeconds" :min="0.5" :max="30" :step="0.5" />
          </label>
          <label class="setting-item">
            <span>最多关键帧</span>
            <el-input-number v-model="uploadForm.maxKeyframes" :min="1" :max="500" />
          </label>
        </div>

        <el-upload
          class="video-uploader"
          drag
          :auto-upload="false"
          :show-file-list="false"
          accept="video/mp4,video/webm,video/avi,video/x-msvideo,video/quicktime"
          :on-change="handleVideoUpload"
        >
          <div class="upload-copy">
            <strong>拖入或选择视频</strong>
            <span>mp4 / webm / avi / mov</span>
          </div>
        </el-upload>

        <div class="incoming-box">
          <div>
            <strong>本地同步目录</strong>
            <code>{{ incomingDir }}</code>
          </div>
          <el-button type="primary" plain :loading="busy" @click="importIncomingVideos">
            扫描导入
          </el-button>
        </div>

        <div class="video-summary">
          <span>当前处理配置</span>
          <div>
            <span class="summary-item"><strong>{{ uploadForm.intervalSeconds }}s</strong><small>抽帧间隔</small></span>
            <span class="summary-item"><strong>{{ uploadForm.maxKeyframes }}</strong><small>最多关键帧</small></span>
            <span class="summary-item"><strong>{{ total }}</strong><small>视频库</small></span>
          </div>
        </div>
      </section>

      <section class="panel tool-panel">
        <div class="panel-head">
          <strong>索引与检索</strong>
          <span class="muted">{{ selectedFeatureTip }}</span>
        </div>

        <div class="form-row">
          <label class="setting-item">
            <span>视频特征</span>
            <el-select v-model="searchForm.feature">
              <el-option v-for="item in featureOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </label>
          <label class="setting-item">
            <span>相似度</span>
            <el-select v-model="searchForm.metric">
              <el-option label="余弦相似度" value="cosine" />
              <el-option label="直方图相交" value="intersection" />
              <el-option label="欧氏距离" value="euclidean" />
              <el-option label="加权距离" value="weighted" />
            </el-select>
          </label>
        </div>

        <el-upload
          class="query-uploader"
          drag
          :auto-upload="false"
          :show-file-list="false"
          accept="image/*"
          :on-change="handleQueryImage"
        >
          <div class="query-drop">
            <img v-if="queryPreview" class="query-preview" :src="queryPreview" alt="查询图" />
            <div v-else class="query-empty">
              <strong>拖入或选择查询图</strong>
              <span>支持 JPG / PNG / WEBP</span>
            </div>
          </div>
        </el-upload>
        <span v-if="queryPreview && !queryFile" class="preview-note">
          已恢复上次预览；重新搜索需重新选择图片。
        </span>

        <div class="action-row">
          <el-button type="primary" :loading="busy" @click="buildIndex">构建索引</el-button>
          <el-button type="primary" plain :disabled="!queryFile" :loading="busy" @click="searchVideos">
            搜视频
          </el-button>
        </div>

        <div class="feature-note">
          <strong>{{ selectedFeatureLabel }}</strong>
          <span>{{ selectedMetricText }}</span>
        </div>
      </section>
    </section>

    <section class="panel result-panel">
      <div class="section-title">
        <strong>检索结果</strong>
        <span class="muted">耗时 {{ elapsed.toFixed(2) }} ms</span>
      </div>
      <div v-if="hits.length" class="ranked-results">
        <article class="video-hit primary-hit">
          <div class="primary-info">
            <div>
              <div class="rank-badge inline">最佳匹配</div>
              <strong>{{ bestHit.name }}</strong>
              <span class="muted">匹配时间 {{ formatTime(bestHit.timestamp || 0) }}</span>
            </div>
            <span class="score-pill">{{ formatScore(bestHit.score) }}</span>
          </div>
          <div class="primary-media">
            <img v-if="bestHit.keyframe_url" :src="bestHit.keyframe_url" alt="匹配关键帧" />
            <video controls :src="bestHit.url" />
          </div>
        </article>
        <div v-if="candidateHits.length" class="candidate-block">
          <strong>候选结果</strong>
          <div class="candidate-grid">
            <article v-for="hit in candidateHits" :key="hit.video_id" class="video-hit candidate-hit">
              <div class="rank-badge subtle">候选</div>
              <img v-if="hit.keyframe_url" :src="hit.keyframe_url" alt="匹配关键帧" />
              <div class="hit-body">
                <strong>{{ hit.name }}</strong>
                <span class="score-pill compact">{{ formatScore(hit.score) }}</span>
                <span class="muted">匹配时间 {{ formatTime(hit.timestamp || 0) }}</span>
                <video controls :src="hit.url" />
              </div>
            </article>
          </div>
        </div>
      </div>
      <el-empty v-else description="选择查询图片后显示相似视频" />
    </section>

    <section class="panel library-panel">
      <div class="section-title">
        <strong>视频库</strong>
        <span class="muted">共 {{ total }} 个视频</span>
      </div>
      <div v-if="videos.length" class="library-grid">
        <article v-for="video in videos" :key="video.id" class="video-card">
          <video controls :src="video.url" />
          <div class="video-meta">
            <strong>{{ video.name }}</strong>
            <span class="muted">{{ formatTime(video.duration) }}，{{ video.keyframe_count }} 个关键帧</span>
          </div>
          <div class="keyframes">
            <img v-for="frame in video.keyframes" :key="frame.id" :src="frame.url" alt="关键帧" />
          </div>
          <el-button size="small" type="danger" plain @click="removeVideo(video)">删除</el-button>
        </article>
      </div>
      <el-empty v-else description="还没有上传视频" />
    </section>
  </main>
</template>

<script setup>
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import BlockingOverlay from '../components/BlockingOverlay.vue'
import {
  buildVideoIndex,
  deleteVideo,
  fetchVideos,
  importLocalVideos,
  searchVideosByImage,
  uploadVideo
} from '../api/cbir'

const VIDEO_CACHE_KEY = 'cbir-video-state-v5'

const featureOptions = [
  { label: 'CNN 深度特征', value: 'deep_cnn', tip: '分类 CNN 更关注类别语义，适合找同类视频；排序会综合多帧降低误匹配。' },
  { label: 'Triplet 度量特征', value: 'deep_triplet', tip: 'Triplet 更适合找具体相似片段，适合当前这种鸟图定位视频。' },
  { label: 'DINOv2 自监督特征', value: 'dinov2', tip: 'DINOv2 更关注视觉结构和局部形态，适合精确视觉相似。' },
  { label: 'HSV 直方图', value: 'color_hist', tip: 'HSV 主要比较整体颜色分布。' },
  { label: '颜色矩', value: 'color_moments', tip: '颜色矩比较颜色统计量，速度快但语义较弱。' },
  { label: 'GLCM', value: 'glcm', tip: 'GLCM 比较纹理统计关系。' },
  { label: 'LBP', value: 'lbp', tip: 'LBP 比较局部纹理模式。' },
  { label: 'Hu', value: 'hu', tip: 'Hu 矩更偏形状轮廓。' },
  { label: 'EOH', value: 'eoh', tip: 'EOH 比较边缘方向分布。' }
]

const uploadForm = reactive({ intervalSeconds: 2, maxKeyframes: 60 })
const searchForm = reactive({ feature: 'deep_triplet', metric: 'cosine' })
const videos = ref([])
const total = ref(0)
const hits = ref([])
const elapsed = ref(0)
const queryFile = ref(null)
const queryPreview = ref('')
const hasSavedState = ref(false)
const incomingDir = 'C:\\Users\\wgq20\\Documents\\CBIR\\cbir-system\\data\\videos\\incoming'
const busy = ref(false)
const busyTitle = ref('正在处理')
const bestHit = computed(() => hits.value[0] || null)
const candidateHits = computed(() => hits.value.slice(1, 4))
const selectedFeature = computed(() => featureOptions.find((item) => item.value === searchForm.feature) || featureOptions[0])
const selectedFeatureLabel = computed(() => selectedFeature.value.label)
const selectedFeatureTip = computed(() => selectedFeature.value.tip)
const selectedMetricText = computed(() => `当前使用 ${metricName(searchForm.metric)}，Top-K 返回 4 个视频。`)

watch(
  () => searchForm.feature,
  (feature) => {
    searchForm.metric = ['color_hist', 'lbp', 'eoh'].includes(feature) ? 'intersection' : 'cosine'
    saveState()
  }
)

watch(() => [uploadForm.intervalSeconds, uploadForm.maxKeyframes, searchForm.metric], saveState)

async function runBusy(title, action) {
  busyTitle.value = title
  busy.value = true
  try {
    return await action()
  } finally {
    busy.value = false
  }
}

async function loadVideos() {
  const result = await fetchVideos({ page: 1, size: 50 })
  videos.value = result.items
  total.value = result.total
  saveState()
}

async function handleVideoUpload(uploadFile) {
  await runBusy('正在上传并抽取关键帧', async () => {
    await uploadVideo({
      file: uploadFile.raw,
      intervalSeconds: uploadForm.intervalSeconds,
      maxKeyframes: uploadForm.maxKeyframes
    })
    ElMessage.success('视频上传完成')
    await loadVideos()
  })
}

async function importIncomingVideos() {
  await runBusy('正在扫描本地视频目录', async () => {
    const result = await importLocalVideos({
      intervalSeconds: uploadForm.intervalSeconds,
      maxKeyframes: uploadForm.maxKeyframes
    })
    if (result.imported.length) {
      ElMessage.success(`已导入 ${result.imported.length} 个视频`)
    } else {
      ElMessage.info('没有发现可导入的视频')
    }
    if (result.skipped.length) {
      ElMessage.warning(`跳过 ${result.skipped.length} 个文件，请检查格式或文件是否可读`)
    }
    await loadVideos()
  })
}

async function handleQueryImage(uploadFile) {
  queryFile.value = uploadFile.raw
  queryPreview.value = await fileToDataUrl(uploadFile.raw)
  saveState()
}

async function buildIndex() {
  await runBusy('正在构建视频索引', async () => {
    const result = await buildVideoIndex({ feature: searchForm.feature })
    ElMessage.success(`已构建 ${result.count} 个关键帧索引`)
  })
}

async function searchVideos() {
  if (!queryFile.value) return
  await runBusy('正在检索相似视频', async () => {
    const result = await searchVideosByImage({
      file: queryFile.value,
      feature: searchForm.feature,
      metric: searchForm.metric,
      topK: 4
    })
    hits.value = result.hits
    elapsed.value = result.elapsed_ms
    saveState()
  })
}

async function removeVideo(video) {
  try {
    await ElMessageBox.confirm('删除视频会同时删除关键帧，并清空旧视频索引。', '删除视频', {
      confirmButtonText: '删除',
      cancelButtonText: '返回',
      type: 'warning'
    })
  } catch {
    return
  }
  await deleteVideo(video.id)
  ElMessage.success('已删除视频')
  await loadVideos()
}

function saveState() {
  const payload = {
    uploadForm: { ...uploadForm },
    searchForm: { ...searchForm },
    videos: videos.value,
    total: total.value,
    hits: hits.value,
    elapsed: elapsed.value,
    queryPreview: queryPreview.value,
    savedAt: new Date().toISOString()
  }
  localStorage.setItem(VIDEO_CACHE_KEY, JSON.stringify(payload))
  hasSavedState.value = true
}

function restoreState() {
  const raw = localStorage.getItem(VIDEO_CACHE_KEY)
  hasSavedState.value = Boolean(raw)
  if (!raw) return
  try {
    const payload = JSON.parse(raw)
    Object.assign(uploadForm, payload.uploadForm || {})
    Object.assign(searchForm, payload.searchForm || {})
    videos.value = Array.isArray(payload.videos) ? payload.videos : []
    total.value = Number(payload.total || 0)
    hits.value = Array.isArray(payload.hits) ? payload.hits : []
    elapsed.value = Number(payload.elapsed || 0)
    queryPreview.value = payload.queryPreview || ''
  } catch {
    localStorage.removeItem(VIDEO_CACHE_KEY)
    hasSavedState.value = false
  }
}

function clearSavedState() {
  localStorage.removeItem(VIDEO_CACHE_KEY)
  hasSavedState.value = false
  hits.value = []
  elapsed.value = 0
  queryFile.value = null
  queryPreview.value = ''
  ElMessage.success('视频检索缓存已清空')
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

function metricName(value) {
  return {
    cosine: '余弦相似度',
    intersection: '直方图相交',
    euclidean: '欧氏距离',
    weighted: '加权距离'
  }[value] || value
}

function formatTime(value) {
  const seconds = Math.max(Number(value) || 0, 0)
  const minute = Math.floor(seconds / 60)
  const second = Math.round(seconds % 60)
  return `${minute}:${String(second).padStart(2, '0')}`
}

function formatScore(value) {
  return `相似度 ${(Math.max(Number(value) || 0, 0) * 100).toFixed(2)}%`
}

onMounted(async () => {
  restoreState()
  await loadVideos()
})
</script>

<style scoped>
.video-page {
  display: grid;
  gap: 18px;
}

.header-panel,
.section-title,
.header-actions,
.action-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.header-panel p {
  margin: 6px 0 0;
}

.header-actions,
.action-row {
  flex-wrap: wrap;
}

.mini-stat {
  display: grid;
  min-width: 68px;
  padding: 7px 10px;
  border: 1px solid var(--panel-border);
  border-radius: 8px;
  background: var(--control-bg);
}

.mini-stat span {
  color: var(--text-muted);
  font-size: 12px;
}

.mini-stat strong {
  color: var(--text-main);
  font-size: 20px;
  line-height: 1.1;
}

.workspace-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  align-items: stretch;
}

.tool-panel {
  display: grid;
  gap: 14px;
  align-content: start;
  padding: 18px;
}

.panel-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}

.panel-head strong {
  flex: 0 0 auto;
  white-space: nowrap;
}

.panel-head .muted {
  min-width: 0;
  overflow-wrap: anywhere;
}

.settings-row,
.form-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.setting-item {
  display: grid;
  gap: 7px;
  min-width: 0;
}

.setting-item span {
  color: var(--text-muted);
  font-size: 14px;
}

.setting-item :deep(.el-input-number),
.setting-item :deep(.el-select) {
  width: 100%;
}

.upload-copy {
  display: grid;
  place-items: center;
  gap: 5px;
  min-height: 108px;
  color: var(--text-muted);
}

.upload-copy strong {
  color: var(--text-main);
}

:deep(.el-upload-dragger) {
  padding: 12px;
  border-radius: 8px;
  background:
    linear-gradient(135deg, rgba(37, 99, 235, 0.08), rgba(15, 118, 110, 0.07)),
    var(--panel-solid);
}

.incoming-box {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--panel-border);
  border-radius: 8px;
  background: color-mix(in srgb, var(--control-bg), var(--accent) 4%);
}

.incoming-box div {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.incoming-box code {
  overflow: hidden;
  color: var(--text-main);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.video-summary {
  display: grid;
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid color-mix(in srgb, var(--accent-2), transparent 70%);
  border-radius: 8px;
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--accent), transparent 92%), transparent),
    var(--control-bg);
}

.video-summary > span {
  color: var(--text-muted);
  font-size: 13px;
}

.video-summary > div {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.video-summary .summary-item {
  display: grid;
  gap: 3px;
  justify-items: center;
  min-width: 0;
}

.video-summary .summary-item strong,
.video-summary .summary-item small {
  display: block;
  min-width: 0;
  text-align: center;
}

.video-summary .summary-item strong {
  color: var(--text-main);
  font-size: 17px;
  line-height: 1.15;
  overflow-wrap: anywhere;
}

.video-summary .summary-item small {
  color: var(--text-muted);
  font-size: 12px;
}

.query-uploader {
  width: 100%;
}

.query-drop {
  display: grid;
  place-items: center;
  min-height: 176px;
}

.query-preview {
  width: 100%;
  max-height: 176px;
  object-fit: contain;
}

.query-empty {
  display: grid;
  place-items: center;
  gap: 5px;
  color: var(--text-muted);
}

.query-empty strong {
  color: var(--text-main);
}

.preview-note {
  margin-top: -6px;
  color: var(--text-muted);
  font-size: 12px;
}

.feature-note {
  display: grid;
  gap: 4px;
  padding: 10px 12px;
  border: 1px solid color-mix(in srgb, var(--accent), transparent 70%);
  border-radius: 8px;
  background: color-mix(in srgb, var(--control-bg), var(--accent) 5%);
}

.feature-note strong {
  font-size: 14px;
}

.feature-note span {
  color: var(--text-muted);
  font-size: 13px;
}

.result-panel,
.library-panel {
  display: grid;
  gap: 14px;
}

.candidate-grid,
.library-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 14px;
}

.ranked-results {
  display: grid;
  gap: 16px;
}

.candidate-block {
  display: grid;
  gap: 10px;
}

.video-hit,
.video-card {
  position: relative;
  display: grid;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--panel-border);
  border-radius: 8px;
  background: var(--panel-solid);
}

.primary-hit {
  gap: 14px;
  border-color: color-mix(in srgb, var(--accent), transparent 45%);
  box-shadow: 0 16px 34px rgba(37, 99, 235, 0.16);
}

.primary-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.primary-info > div {
  display: grid;
  gap: 5px;
}

.primary-info strong {
  font-size: 22px;
}

.primary-media {
  display: grid;
  grid-template-columns: minmax(260px, 0.78fr) minmax(320px, 1fr);
  gap: 14px;
  align-items: start;
}

.primary-media img,
.primary-media video {
  width: 100%;
  max-height: 380px;
  object-fit: contain;
  border-radius: 6px;
  background: var(--control-bg);
}

.candidate-hit {
  opacity: 0.92;
}

.rank-badge {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 1;
  padding: 4px 8px;
  color: #ffffff;
  font-size: 12px;
  border-radius: 7px;
  background: var(--accent);
}

.rank-badge.inline {
  position: static;
  width: fit-content;
}

.rank-badge.subtle {
  background: rgba(100, 116, 139, 0.88);
}

.score-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: fit-content;
  padding: 7px 11px;
  color: #ffffff;
  font-weight: 800;
  border-radius: 8px;
  background: linear-gradient(135deg, #16a34a, #0f766e);
  box-shadow: 0 10px 22px rgba(15, 118, 110, 0.2);
}

.score-pill.compact {
  padding: 5px 8px;
  font-size: 13px;
}

.video-hit > img {
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: contain;
  border-radius: 6px;
  background: var(--control-bg);
}

.hit-body,
.video-meta {
  display: grid;
  gap: 4px;
}

video {
  width: 100%;
  aspect-ratio: 16 / 9;
  border-radius: 6px;
  background: #000000;
}

.keyframes {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 6px;
}

.keyframes img {
  width: 100%;
  aspect-ratio: 1;
  object-fit: cover;
  border-radius: 5px;
  background: var(--control-bg);
}

@media (max-width: 1050px) {
  .workspace-grid,
  .primary-media {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .header-panel,
  .header-actions,
  .primary-info,
  .action-row,
  .incoming-box,
  .settings-row,
  .form-row {
    align-items: stretch;
    grid-template-columns: 1fr;
    flex-direction: column;
  }
}
</style>
