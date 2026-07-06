<template>
  <el-popover
    trigger="hover"
    placement="top"
    :width="300"
    :show-after="120"
    popper-class="param-popover"
  >
    <template #reference>
      <button type="button" class="param-info-button" aria-label="查看参数说明" @click.stop="$emit('open')">
        i
      </button>
    </template>
    <div class="param-popover-card">
      <strong>{{ info.title }}</strong>
      <p>{{ info.short }}</p>
      <span>{{ info.impact }}</span>
      <em>点击 i 查看详细说明</em>
    </div>
  </el-popover>
</template>

<script setup>
defineProps({
  info: {
    type: Object,
    required: true
  }
})

defineEmits(['open'])
</script>

<style scoped>
.param-info-button {
  display: inline-grid;
  place-items: center;
  width: 16px;
  height: 16px;
  margin-left: 6px;
  padding: 0;
  color: var(--accent);
  border: 1px solid color-mix(in srgb, var(--accent), transparent 42%);
  border-radius: 50%;
  background: color-mix(in srgb, var(--control-bg), var(--accent) 8%);
  cursor: pointer;
  font-size: 11px;
  font-weight: 900;
  line-height: 1;
}

.param-info-button:hover,
.param-info-button:focus-visible {
  color: #ffffff;
  outline: none;
  background: var(--accent);
}

:global(.param-popover) {
  border-color: var(--panel-border) !important;
  background: var(--panel-solid) !important;
  color: var(--text-main) !important;
}

.param-popover-card {
  display: grid;
  gap: 7px;
}

.param-popover-card strong {
  color: var(--text-main);
  font-size: 14px;
}

.param-popover-card p,
.param-popover-card span {
  margin: 0;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.5;
}

.param-popover-card span {
  color: var(--accent-2);
}

.param-popover-card em {
  color: var(--accent);
  font-size: 12px;
  font-style: normal;
  font-weight: 700;
}
</style>
