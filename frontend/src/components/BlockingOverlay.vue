<template>
  <el-dialog
    :model-value="visible"
    :title="title"
    width="380px"
    align-center
    append-to-body
    lock-scroll
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="false"
  >
    <div class="busy-body" role="status" aria-live="polite">
      <el-icon class="busy-icon"><Loading /></el-icon>
      <div>
        <strong>{{ message }}</strong>
        <p class="muted">{{ description }}</p>
      </div>
    </div>
    <div class="busy-line" aria-hidden="true"></div>
  </el-dialog>
</template>

<script setup>
import { Loading } from '@element-plus/icons-vue'

defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: '请稍候'
  },
  message: {
    type: String,
    default: '正在处理任务'
  },
  description: {
    type: String,
    default: '计算完成后窗口会自动关闭。'
  }
})
</script>

<style scoped>
.busy-body {
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 76px;
}

.busy-icon {
  flex: 0 0 auto;
  font-size: 34px;
  color: var(--accent);
  animation: busy-spin 1s linear infinite;
}

.busy-body strong {
  display: block;
  font-size: 16px;
}

.busy-body p {
  margin: 6px 0 0;
}

.busy-line {
  position: relative;
  overflow: hidden;
  height: 4px;
  margin-top: 4px;
  border-radius: 8px;
  background: rgba(148, 163, 184, 0.18);
}

.busy-line::after {
  position: absolute;
  inset: 0;
  width: 42%;
  content: "";
  border-radius: inherit;
  background: linear-gradient(90deg, var(--accent), var(--accent-2), var(--accent-3));
  animation: busy-run 1.15s ease-in-out infinite;
}

@keyframes busy-spin {
  from {
    transform: rotate(0deg);
  }

  to {
    transform: rotate(360deg);
  }
}

@keyframes busy-run {
  from {
    transform: translateX(-120%);
  }

  to {
    transform: translateX(260%);
  }
}
</style>
