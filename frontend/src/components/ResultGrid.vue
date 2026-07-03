<template>
  <section class="results">
    <div v-if="hits.length === 0" class="panel empty muted">等待检索结果</div>
    <div v-else class="result-grid">
      <article
        v-for="(hit, index) in hits"
        :key="hit.image_id"
        class="result-card"
        @click="$emit('select', hit)"
      >
        <div class="image-frame" :class="{ 'low-res-image': isLowResolution(hit) }">
          <span class="rank-badge" :class="{ 'rank-top': index < 3 }">#{{ index + 1 }}</span>
          <img :src="hit.url" :alt="hit.name" />
        </div>
        <div class="meta">
          <strong>{{ hit.name }}</strong>
          <span>{{ hit.score.toFixed(4) }}</span>
        </div>
        <div class="score-bar" :title="`相似度 ${hit.score.toFixed(4)}`">
          <i :style="{ width: `${scorePercent(hit.score)}%` }" />
        </div>
        <el-tag v-if="hit.category" size="small">{{ hit.category }}</el-tag>
      </article>
    </div>
  </section>
</template>

<script setup>
defineProps({
  hits: {
    type: Array,
    default: () => []
  }
})

defineEmits(['select'])

function isLowResolution(hit) {
  return Number(hit.width || 0) <= 64 && Number(hit.height || 0) <= 64
}

// 相似度分数（0~1）转百分比宽度，直观展示每个结果与查询图的接近程度。
function scorePercent(score) {
  const value = Number(score) || 0
  return Math.max(0, Math.min(100, value * 100))
}
</script>

<style scoped>
.results {
  min-width: 0;
}

.empty {
  min-height: 220px;
  display: grid;
  place-items: center;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.result-card {
  min-width: 0;
  padding: 10px;
  background: var(--panel-solid);
  border: 1px solid var(--panel-border);
  border-radius: 8px;
  cursor: pointer;
}

.image-frame {
  position: relative;
  display: grid;
  place-items: center;
  overflow: hidden;
  width: 100%;
  aspect-ratio: 1;
  border-radius: 8px;
  background: color-mix(in srgb, var(--control-bg), var(--accent) 5%);
}

.image-frame::after {
  position: absolute;
  inset: auto 0 0;
  height: 38%;
  pointer-events: none;
  content: "";
  background: linear-gradient(to top, rgba(15, 23, 42, 0.18), transparent);
  opacity: 0;
  transition: opacity 180ms ease;
}

.rank-badge {
  position: absolute;
  top: 6px;
  left: 6px;
  z-index: 2;
  min-width: 24px;
  padding: 2px 6px;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.4;
  text-align: center;
  color: #ffffff;
  border-radius: 6px;
  background: rgba(15, 23, 42, 0.62);
  backdrop-filter: blur(4px);
}

.rank-badge.rank-top {
  background: linear-gradient(135deg, var(--accent), var(--accent-2));
  box-shadow: 0 4px 10px rgba(37, 99, 235, 0.32);
}

.score-bar {
  height: 5px;
  margin: 0 0 8px;
  overflow: hidden;
  border-radius: 999px;
  background: color-mix(in srgb, var(--control-bg), var(--accent) 8%);
}

.score-bar i {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--accent), var(--accent-2));
  transition: width 320ms ease;
}

.result-card img {
  display: block;
  width: 100%;
  aspect-ratio: 1;
  object-fit: cover;
  transition: transform 220ms ease;
}

.low-res-image img {
  width: auto;
  height: auto;
  max-width: 64px;
  max-height: 64px;
  aspect-ratio: auto;
  object-fit: contain;
  image-rendering: auto;
}

.result-card:hover img {
  transform: scale(1.06);
}

.result-card:hover .image-frame::after {
  opacity: 1;
}

.meta {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 8px;
  align-items: center;
  margin: 8px 0;
  font-size: 13px;
}

.meta span {
  color: var(--accent-2);
  font-weight: 700;
}

.meta strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 1080px) {
  .result-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .result-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
