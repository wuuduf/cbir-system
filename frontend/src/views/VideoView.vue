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
        <p class="muted">上传视频抽取关键帧，复用图像特征建立视频索引，再用图片检索相似视频。</p>
      </div>
      <el-button :loading="busy" @click="loadVideos">刷新</el-button>
    </section>

    <section class="video-grid">
      <div class="panel tool-panel">
        <strong>视频管理</strong>
        <el-form label-position="top">
          <el-form-item label="关键帧间隔（秒）">
            <el-input-number v-model="uploadForm.intervalSeconds" :min="0.5" :max="30" :step="0.5" />
          </el-form-item>
          <el-form-item label="最多关键帧">
            <el-input-number v-model="uploadForm.maxKeyframes" :min="1" :max="500" />
          </el-form-item>
          <el-upload
            drag
            :auto-upload="false"
            :show-file-list="false"
            accept="video/mp4,video/webm,video/avi,video/x-msvideo,video/quicktime"
            :on-change="handleVideoUpload"
          >
            <div class="upload-copy">拖入或选择视频</div>
          </el-upload>
          <div class="incoming-box">
            <span class="muted">本地同步目录</span>
            <code>{{ incomingDir }}</code>
            <el-button type="primary" plain :loading="busy" @click="importIncomingVideos">
              扫描导入本地视频
            </el-button>
          </div>
        </el-form>
      </div>

      <div class="panel tool-panel">
        <strong>索引与检索</strong>
        <el-form label-position="top">
          <div class="form-row">
            <el-form-item label="视频特征">
              <el-select v-model="searchForm.feature">
                <el-option v-for="item in featureOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
            <el-form-item label="相似度">
              <el-select v-model="searchForm.metric">
                <el-option label="余弦相似度" value="cosine" />
                <el-option label="直方图相交" value="intersection" />
                <el-option label="欧氏距离" value="euclidean" />
                <el-option label="加权距离" value="weighted" />
              </el-select>
            </el-form-item>
          </div>
          <div class="actions">
            <el-button type="primary" :loading="busy" @click="buildIndex">构建视频索引</el-button>
            <el-upload :auto-upload="false" :show-file-list="false" accept="image/*" :on-change="handleQueryImage">
              <el-button :loading="busy">选择查询图</el-button>
            </el-upload>
            <el-button type="primary" plain :disabled="!queryFile" :loading="busy" @click="searchVideos">搜视频</el-button>
          </div>
          <img v-if="queryPreview" class="query-preview" :src="queryPreview" alt="查询图" />
        </el-form>
      </div>
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
      <el-empty v-else description="上传查询图片后显示相似视频" />
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
            <span class="muted">
              {{ formatTime(video.duration) }}，{{ video.keyframe_count }} 个关键帧
            </span>
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

const featureOptions = [
  { label: '深度特征', value: 'deep' },
  { label: 'HSV 直方图', value: 'color_hist' },
  { label: '颜色矩', value: 'color_moments' },
  { label: 'GLCM', value: 'glcm' },
  { label: 'LBP', value: 'lbp' },
  { label: 'Hu', value: 'hu' },
  { label: 'EOH', value: 'eoh' }
]

const uploadForm = reactive({
  intervalSeconds: 2,
  maxKeyframes: 60
})
const searchForm = reactive({
  feature: 'deep',
  metric: 'cosine'
})
const videos = ref([])
const total = ref(0)
const hits = ref([])
const elapsed = ref(0)
const queryFile = ref(null)
const queryPreview = ref('')
const incomingDir = 'C:\\Users\\wgq20\\Documents\\CBIR\\cbir-system\\data\\videos\\incoming'
const busy = ref(false)
const busyTitle = ref('正在处理')
const bestHit = computed(() => hits.value[0] || null)
const candidateHits = computed(() => hits.value.slice(1, 4))

watch(
  () => searchForm.feature,
  (feature) => {
    searchForm.metric = ['color_hist', 'lbp', 'eoh'].includes(feature) ? 'intersection' : 'cosine'
  }
)

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
      ElMessage.warning(`跳过 ${result.skipped.length} 个文件，请查看格式或文件是否可读`)
    }
    await loadVideos()
  })
}

function handleQueryImage(uploadFile) {
  queryFile.value = uploadFile.raw
  if (queryPreview.value) {
    URL.revokeObjectURL(queryPreview.value)
  }
  queryPreview.value = URL.createObjectURL(uploadFile.raw)
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

function formatTime(value) {
  const seconds = Math.max(Number(value) || 0, 0)
  const minute = Math.floor(seconds / 60)
  const second = Math.round(seconds % 60)
  return `${minute}:${String(second).padStart(2, '0')}`
}

function formatScore(value) {
  return `相似度 ${(Math.max(Number(value) || 0, 0) * 100).toFixed(2)}%`
}

onMounted(loadVideos)
</script>

<style scoped>
.video-page {
  display: grid;
  gap: 18px;
}

.header-panel,
.section-title,
.actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.header-panel p {
  margin: 6px 0 0;
}

.video-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.tool-panel {
  display: grid;
  gap: 14px;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.upload-copy {
  padding: 22px 0;
  color: var(--text-muted);
}

.incoming-box {
  display: grid;
  gap: 8px;
  padding: 10px;
  border: 1px solid var(--panel-border);
  border-radius: 8px;
  background: color-mix(in srgb, var(--control-bg), var(--accent) 4%);
}

.incoming-box code {
  overflow-wrap: anywhere;
  color: var(--text-main);
  font-size: 12px;
}

.query-preview {
  width: 160px;
  aspect-ratio: 4 / 3;
  object-fit: contain;
  border: 1px solid var(--panel-border);
  border-radius: 8px;
  background: var(--control-bg);
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

@media (max-width: 900px) {
  .video-grid,
  .form-row,
  .primary-media {
    grid-template-columns: 1fr;
  }

  .header-panel,
  .primary-info,
  .actions {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
