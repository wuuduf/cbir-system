<template>
  <main class="page pipeline-page">
    <section class="panel header-panel">
      <div>
        <strong>实验流水线</strong>
        <p class="muted">数据导入、预处理、模型训练、索引构建和评估统一在这里启动。</p>
      </div>
      <el-select v-model="form.dataset" style="width: 180px" @change="useDatasetDefaults">
        <el-option label="CIFAR-10" value="cifar10" />
        <el-option label="CIFAR-100" value="cifar100" />
      </el-select>
    </section>

    <section class="pipeline-grid">
      <div class="panel stage-panel">
        <strong>1. 数据集导入</strong>
        <el-form label-position="top">
          <el-form-item label="官方下载地址">
            <el-input v-model="form.downloadUrl" />
          </el-form-item>
          <el-form-item label="保存文件名">
            <el-input v-model="form.downloadName" />
          </el-form-item>
          <div class="actions">
            <el-button :loading="starting" @click="downloadDataset">开始下载</el-button>
            <el-upload :auto-upload="false" :show-file-list="false" :on-change="uploadArchive">
              <el-button :loading="uploading" type="primary">上传压缩包</el-button>
            </el-upload>
          </div>
          <el-form-item label="解压后的数据目录">
            <el-input v-model="form.src" />
          </el-form-item>
        </el-form>
      </div>

      <div class="panel stage-panel">
        <strong>2. 数据预处理</strong>
        <el-form label-position="top">
          <div class="form-row">
            <el-form-item label="划分">
              <el-select v-model="form.split">
                <el-option label="全部 train + test" value="all" />
                <el-option label="仅 train" value="train" />
                <el-option label="仅 test" value="test" />
              </el-select>
            </el-form-item>
            <el-form-item label="每类数量">
              <el-input-number v-model="form.perClass" :min="0" :max="6000" controls-position="right" />
            </el-form-item>
          </div>
          <el-form-item v-if="form.dataset === 'cifar100'" label="CIFAR-100 标签">
            <el-segmented v-model="form.labelLevel" :options="labelOptions" />
          </el-form-item>
          <el-button type="primary" :loading="starting" @click="prepareDataset">开始预处理</el-button>
        </el-form>
      </div>

      <div class="panel stage-panel">
        <strong>3. 训练 CNN / Triplet 模型</strong>
        <el-form label-position="top">
          <el-form-item label="训练目标">
            <el-segmented v-model="form.trainObjective" :options="trainOptions" />
          </el-form-item>
          <div class="form-row">
            <el-form-item label="Epoch">
              <el-input-number v-model="form.epochs" :min="1" :max="500" controls-position="right" />
            </el-form-item>
            <el-form-item label="Batch Size">
              <el-input-number v-model="form.batchSize" :min="16" :max="1024" :step="16" controls-position="right" />
            </el-form-item>
          </div>
          <div class="form-row">
            <el-form-item label="学习率">
              <el-input-number v-model="form.lr" :min="0.0001" :max="1" :step="0.01" controls-position="right" />
            </el-form-item>
            <el-form-item label="Workers">
              <el-input-number v-model="form.workers" :min="0" :max="16" controls-position="right" />
            </el-form-item>
          </div>
          <div v-if="form.trainObjective === 'metric'" class="form-row">
            <el-form-item label="Triplet Margin">
              <el-input-number v-model="form.margin" :min="0.05" :max="2" :step="0.05" controls-position="right" />
            </el-form-item>
            <el-form-item label="Eval K">
              <el-input-number v-model="form.evalK" :min="1" :max="100" controls-position="right" />
            </el-form-item>
          </div>
          <div v-if="form.trainObjective === 'metric'" class="form-row">
            <el-form-item label="Triplet 权重">
              <el-input-number v-model="form.tripletWeight" :min="0" :max="10" :step="0.1" controls-position="right" />
            </el-form-item>
            <el-form-item label="分类权重">
              <el-input-number v-model="form.ceWeight" :min="0" :max="10" :step="0.1" controls-position="right" />
            </el-form-item>
          </div>
          <el-checkbox v-model="form.amp">使用 AMP 混合精度</el-checkbox>
          <el-button type="primary" :loading="starting" @click="trainSelectedModel">
            {{ form.trainObjective === 'metric' ? '开始 Triplet 训练' : '开始分类训练' }}
          </el-button>
        </el-form>
      </div>

      <div class="panel stage-panel">
        <strong>4. 索引与评估</strong>
        <el-form label-position="top">
          <el-form-item label="重建特征">
            <el-checkbox-group v-model="form.features">
              <el-checkbox-button label="deep">深度</el-checkbox-button>
              <el-checkbox-button label="clip">CLIP</el-checkbox-button>
              <el-checkbox-button label="color_hist">HSV</el-checkbox-button>
              <el-checkbox-button label="color_moments">颜色矩</el-checkbox-button>
              <el-checkbox-button label="glcm">GLCM</el-checkbox-button>
              <el-checkbox-button label="lbp">LBP</el-checkbox-button>
              <el-checkbox-button label="hu">Hu</el-checkbox-button>
              <el-checkbox-button label="eoh">EOH</el-checkbox-button>
            </el-checkbox-group>
          </el-form-item>
          <div class="actions">
            <el-button type="primary" :loading="starting" @click="buildIndexes">重建索引</el-button>
            <el-button :loading="starting" @click="evaluateCurrent">评估 deep</el-button>
          </div>
        </el-form>
      </div>
    </section>

    <section class="panel task-panel">
      <div class="task-header">
        <strong>任务中心</strong>
        <div class="task-actions">
          <el-button size="small" @click="loadTasks">刷新</el-button>
          <el-button size="small" :disabled="!hasFinishedTasks" @click="clearTasks('finished')">清空已结束</el-button>
          <el-button size="small" type="danger" plain :disabled="tasks.length === 0" @click="clearTasks('all')">
            清空全部
          </el-button>
        </div>
      </div>
      <el-table :data="tasks" height="260" @row-click="selectTask">
        <el-table-column prop="name" label="任务" min-width="220" />
        <el-table-column prop="kind" label="类型" width="90" />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" min-width="260">
          <template #default="{ row }">
            <div class="progress-cell">
              <el-progress :percentage="taskPercent(row)" :status="progressStatus(row.status)" :stroke-width="8" />
              <span v-if="row.progress?.epoch" class="muted">
                epoch {{ row.progress.epoch }}/{{ row.progress.total_epochs || '?' }}，
                val_acc {{ Number(row.progress.val_acc || 0).toFixed(4) }}
                <template v-if="row.progress?.p_at_k">，P@K {{ Number(row.progress.p_at_k).toFixed(4) }}</template>
              </span>
              <span v-else-if="row.result?.map" class="muted">
                mAP {{ Number(row.result.map).toFixed(4) }}，P@K {{ Number(row.result.p_at_k).toFixed(4) }}
              </span>
              <span v-else class="muted">{{ progressHint(row.status) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="110" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="danger" plain :disabled="!canCancel(row)" @click.stop="cancelTask(row)">
              取消
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="log-view">
        <div class="log-title">
          <strong>{{ selectedTask?.name || '未选择任务' }}</strong>
          <span v-if="selectedTask" class="muted">{{ selectedTask.id }}</span>
        </div>
        <pre>{{ selectedLogs }}</pre>
      </div>
    </section>
  </main>
</template>

<script setup>
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import {
  cancelPipelineTask,
  clearPipelineTasks,
  fetchPipelineTasks,
  startDatasetDownload,
  startDatasetPrepare,
  startMetricTraining,
  startModelTraining,
  startPipelineEvaluate,
  startPipelineIndex,
  uploadDatasetArchive
} from '../api/cbir'

const urls = {
  cifar10: {
    url: 'https://www.cs.toronto.edu/~kriz/cifar-10-python.tar.gz',
    name: 'cifar-10-python.tar.gz',
    src: '..\\data\\raw\\cifar-10-batches-py'
  },
  cifar100: {
    url: 'https://www.cs.toronto.edu/~kriz/cifar-100-python.tar.gz',
    name: 'cifar-100-python.tar.gz',
    src: '..\\data\\raw\\cifar-100-python'
  }
}

const labelOptions = [
  { label: 'fine 100 类', value: 'fine' },
  { label: 'coarse 20 类', value: 'coarse' }
]

const trainOptions = [
  { label: '分类训练', value: 'classification' },
  { label: 'Triplet 度量学习', value: 'metric' }
]

const form = reactive({
  dataset: 'cifar10',
  downloadUrl: urls.cifar10.url,
  downloadName: urls.cifar10.name,
  src: urls.cifar10.src,
  split: 'all',
  perClass: 0,
  labelLevel: 'fine',
  epochs: 80,
  batchSize: 128,
  lr: 0.1,
  workers: 2,
  amp: true,
  trainObjective: 'metric',
  margin: 0.2,
  tripletWeight: 1.0,
  ceWeight: 0.5,
  evalK: 12,
  features: ['deep', 'clip']
})
const tasks = ref([])
const selectedTask = ref(null)
const starting = ref(false)
const uploading = ref(false)
let timer = null

const selectedLogs = computed(() => {
  if (!selectedTask.value) {
    return '选择一个任务后显示日志。'
  }
  return selectedTask.value.logs?.join('\n') || '暂无日志。'
})
const hasFinishedTasks = computed(() =>
  tasks.value.some((task) => ['succeeded', 'failed', 'cancelled'].includes(task.status))
)

function useDatasetDefaults() {
  const item = urls[form.dataset]
  form.downloadUrl = item.url
  form.downloadName = item.name
  form.src = item.src
  form.labelLevel = 'fine'
  form.perClass = 0
}

async function runStarter(action) {
  starting.value = true
  try {
    const task = await action()
    selectedTask.value = task
    ElMessage.success('任务已启动')
    await loadTasks()
  } finally {
    starting.value = false
  }
}

async function downloadDataset() {
  await runStarter(() => startDatasetDownload({ url: form.downloadUrl, filename: form.downloadName }))
}

async function uploadArchive(uploadFile) {
  uploading.value = true
  try {
    const result = await uploadDatasetArchive({ file: uploadFile.raw, extract: true })
    if (result.extract_dir) {
      form.src = result.extract_dir
    }
    ElMessage.success('上传完成')
  } finally {
    uploading.value = false
  }
}

async function prepareDataset() {
  await runStarter(() =>
    startDatasetPrepare({
      dataset: form.dataset,
      src: form.src,
      split: form.split,
      per_class: form.perClass > 0 ? form.perClass : null,
      label_level: form.labelLevel
    })
  )
}

function trainingPayload() {
  return {
    dataset: form.dataset,
    src: form.src,
    epochs: form.epochs,
    batch_size: form.batchSize,
    lr: form.lr,
    workers: form.workers,
    amp: form.amp,
    label_level: form.labelLevel
  }
}

async function trainSelectedModel() {
  if (form.trainObjective === 'metric') {
    await trainMetricModel()
    return
  }
  await trainModel()
}

async function trainModel() {
  await runStarter(() =>
    startModelTraining(trainingPayload())
  )
}

async function trainMetricModel() {
  await runStarter(() =>
    startMetricTraining({
      ...trainingPayload(),
      margin: form.margin,
      triplet_weight: form.tripletWeight,
      ce_weight: form.ceWeight,
      eval_k: form.evalK
    })
  )
}

async function buildIndexes() {
  await runStarter(() =>
    startPipelineIndex({
      dataset: form.dataset,
      features: form.features.length > 0 ? form.features : ['deep']
    })
  )
}

async function evaluateCurrent() {
  await runStarter(() =>
    startPipelineEvaluate({
      dataset: form.dataset,
      feature: 'deep',
      metric: 'cosine',
      k: 12,
      sample: 100
    })
  )
}

async function loadTasks() {
  tasks.value = await fetchPipelineTasks()
  if (selectedTask.value) {
    selectedTask.value = tasks.value.find((task) => task.id === selectedTask.value.id) || tasks.value[0] || null
  } else if (tasks.value.length > 0) {
    selectedTask.value = tasks.value[0]
  } else {
    selectedTask.value = null
  }
}

async function clearTasks(mode) {
  if (mode === 'all') {
    try {
      await ElMessageBox.confirm('这会取消正在运行的任务，并清空任务中心记录。', '清空全部任务', {
        confirmButtonText: '清空',
        cancelButtonText: '返回',
        type: 'warning'
      })
    } catch {
      return
    }
  }
  tasks.value = await clearPipelineTasks(mode)
  selectedTask.value = tasks.value.find((task) => task.id === selectedTask.value?.id) || tasks.value[0] || null
  ElMessage.success(mode === 'all' ? '任务中心已清空' : '已清空结束任务')
}

function selectTask(row) {
  selectedTask.value = row
}

function statusType(status) {
  if (status === 'succeeded') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'cancelled') return 'info'
  if (status === 'cancelling') return 'warning'
  if (status === 'running') return 'warning'
  return 'info'
}

function statusText(status) {
  return {
    queued: '排队中',
    running: '运行中',
    cancelling: '取消中',
    cancelled: '已取消',
    succeeded: '已完成',
    failed: '失败'
  }[status] || status
}

function taskPercent(task) {
  if (task.status === 'succeeded') return 100
  if (task.status === 'failed' || task.status === 'cancelled') return 100
  if (task.progress?.epoch && task.progress?.total_epochs) {
    return Math.min(99, Math.round((task.progress.epoch / task.progress.total_epochs) * 100))
  }
  if (task.status === 'running' || task.status === 'cancelling') return 15
  return 0
}

function progressStatus(status) {
  if (status === 'succeeded') return 'success'
  if (status === 'failed') return 'exception'
  if (status === 'cancelled') return 'warning'
  return ''
}

function progressHint(status) {
  if (status === 'running') return '运行中，等待日志'
  if (status === 'cancelling') return '正在取消'
  if (status === 'cancelled') return '已取消'
  if (status === 'succeeded') return '已完成'
  if (status === 'failed') return '失败'
  return '等待开始'
}

function canCancel(task) {
  return task.status === 'queued' || task.status === 'running'
}

async function cancelTask(task) {
  try {
    await cancelPipelineTask(task.id)
    ElMessage.success('已发送取消请求')
  } catch (error) {
    if (error.response?.status === 404) {
      tasks.value = tasks.value.filter((item) => item.id !== task.id)
      selectedTask.value = tasks.value.find((item) => item.id === selectedTask.value?.id) || tasks.value[0] || null
      ElMessage.warning('这个任务已经不在后端任务中心，已从页面移除')
    } else {
      ElMessage.error(error.response?.data?.detail || error.message || '取消失败')
    }
  } finally {
    await loadTasks()
  }
}

onMounted(async () => {
  await loadTasks()
  timer = window.setInterval(loadTasks, 2000)
})

onUnmounted(() => {
  if (timer) {
    window.clearInterval(timer)
  }
})
</script>

<style scoped>
.pipeline-page {
  display: grid;
  gap: 18px;
}

.header-panel,
.task-header,
.actions,
.log-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.header-panel p {
  margin: 6px 0 0;
}

.pipeline-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.stage-panel {
  display: grid;
  gap: 14px;
}

.stage-panel :deep(.el-form-item) {
  margin-bottom: 12px;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.task-panel {
  display: grid;
  gap: 14px;
}

.task-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-cell {
  display: grid;
  gap: 4px;
}

.log-view {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #111827;
  color: #d1d5db;
  overflow: hidden;
}

.log-title {
  padding: 10px 12px;
  border-bottom: 1px solid #374151;
  color: #f9fafb;
}

.log-view pre {
  margin: 0;
  min-height: 180px;
  max-height: 320px;
  overflow: auto;
  padding: 12px;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
  line-height: 1.55;
}

@media (max-width: 980px) {
  .pipeline-grid,
  .form-row {
    grid-template-columns: 1fr;
  }

  .header-panel,
  .task-header,
  .actions {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
