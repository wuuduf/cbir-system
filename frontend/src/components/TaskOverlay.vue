<template>
  <el-dialog
    :model-value="visible"
    width="min(640px, calc(100vw - 32px))"
    align-center
    append-to-body
    lock-scroll
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="false"
    class="task-overlay-dialog"
  >
    <div class="task-overlay">
      <div class="task-top">
        <div>
          <span class="eyebrow">{{ eyebrow }}</span>
          <h3 :title="task?.name || title">{{ task?.name || title }}</h3>
          <p>{{ messageText }}</p>
        </div>
        <div class="percent-ring">
          <span>{{ percentage }}%</span>
        </div>
      </div>

      <el-progress :percentage="percentage" :status="progressStatus" :stroke-width="12" striped striped-flow />

      <div class="task-stats">
        <span>{{ progressLabel }}</span>
        <span>{{ statusText }}</span>
      </div>

      <pre class="task-log">{{ latestLog }}</pre>

      <div class="task-actions">
        <el-button :disabled="!canCancel" type="danger" plain @click="$emit('cancel')">取消任务</el-button>
        <el-button v-if="isTerminal" type="primary" @click="$emit('close')">关闭</el-button>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  task: {
    type: Object,
    default: null
  },
  title: {
    type: String,
    default: '正在执行任务'
  },
  eyebrow: {
    type: String,
    default: '后台任务'
  }
})

defineEmits(['cancel', 'close'])

const isTerminal = computed(() => ['succeeded', 'failed', 'cancelled'].includes(props.task?.status))
const canCancel = computed(() => ['queued', 'running'].includes(props.task?.status))
const percentage = computed(() => {
  if (!props.task) return 0
  if (props.task.status === 'succeeded') return 100
  if (props.task.status === 'failed' || props.task.status === 'cancelled') return 100
  if (props.task.progress?.percent !== undefined) {
    return Math.max(0, Math.min(99, Number(props.task.progress.percent) || 0))
  }
  if (props.task.progress?.epoch && props.task.progress?.total_epochs) {
    return Math.min(99, Math.round((props.task.progress.epoch / props.task.progress.total_epochs) * 100))
  }
  return props.task.status === 'running' ? 8 : 0
})

const progressStatus = computed(() => {
  if (props.task?.status === 'succeeded') return 'success'
  if (props.task?.status === 'failed') return 'exception'
  if (props.task?.status === 'cancelled') return 'warning'
  return ''
})

const statusText = computed(() => {
  return {
    queued: '排队中',
    running: '运行中',
    cancelling: '取消中',
    cancelled: '已取消',
    succeeded: '已完成',
    failed: '失败'
  }[props.task?.status] || '等待任务'
})

const progressLabel = computed(() => {
  const progress = props.task?.progress || {}
  if (progress.current && progress.total) {
    return `${progress.label || '处理'} ${progress.current}/${progress.total}`
  }
  if (progress.epoch) {
    return `epoch ${progress.epoch}/${progress.total_epochs || '?'}`
  }
  return '正在准备任务'
})

const messageText = computed(() => {
  if (props.task?.status === 'succeeded') return '任务已经完成，可以查看结果或继续下一步。'
  if (props.task?.status === 'failed') return props.task?.error || '任务执行失败。'
  if (props.task?.status === 'cancelled') return '任务已取消。'
  if (props.task?.status === 'cancelling') return '正在停止后台进程，请稍候。'
  if (props.task?.kind === 'train') return '正在训练 CNN 分类模型，期间请不要重复启动训练任务。'
  if (props.task?.kind === 'train_metric') return '正在训练 Triplet 度量学习模型，期间请不要重复启动训练任务。'
  if (props.task?.kind === 'index') return '正在提取特征并写入索引，期间请不要重复启动同类任务。'
  if (props.task?.kind === 'evaluate') return '正在计算评估指标，期间请等待任务完成。'
  return '后台任务正在运行，期间请不要重复启动同类任务。'
})

const latestLog = computed(() => {
  const logs = props.task?.logs || []
  return logs.slice(-6).join('\n') || '等待日志输出...'
})
</script>

<style scoped>
.task-overlay {
  display: grid;
  gap: 16px;
  min-width: 0;
  overflow: hidden;
}

.task-top {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 76px;
  gap: 14px;
  align-items: center;
}

.task-top > div:first-child {
  min-width: 0;
}

.eyebrow {
  color: var(--accent);
  font-size: 12px;
  font-weight: 800;
}

h3 {
  margin: 5px 0 6px;
  overflow: hidden;
  color: var(--text-main);
  font-size: 20px;
  line-height: 1.28;
  overflow-wrap: anywhere;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

p {
  margin: 0;
  color: var(--text-muted);
  line-height: 1.5;
}

.percent-ring {
  display: grid;
  place-items: center;
  width: 72px;
  height: 72px;
  border: 1px solid color-mix(in srgb, var(--accent), transparent 55%);
  border-radius: 50%;
  background: linear-gradient(135deg, color-mix(in srgb, var(--accent), transparent 82%), var(--panel-solid));
  box-shadow: 0 16px 34px rgba(37, 99, 235, 0.12);
}

.percent-ring span {
  font-size: 19px;
  font-weight: 900;
}

.task-overlay :deep(.el-progress__text) {
  display: none;
}

.task-stats {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: var(--text-muted);
  font-size: 13px;
}

.task-log {
  min-height: 96px;
  max-height: 150px;
  margin: 0;
  overflow: auto;
  padding: 12px;
  color: var(--log-text);
  white-space: pre-wrap;
  word-break: break-word;
  border: 1px solid var(--code-border);
  border-radius: 8px;
  background: var(--log-bg);
  font-size: 12px;
  line-height: 1.5;
}

.task-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

@media (max-width: 560px) {
  .task-top {
    grid-template-columns: 1fr;
  }
}
</style>
