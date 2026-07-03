<template>
  <section class="results">
    <div v-if="hits.length === 0" class="panel empty muted">等待检索结果</div>
    <div v-else class="result-grid">
      <article v-for="hit in hits" :key="hit.image_id" class="result-card" @click="$emit('select', hit)">
        <div class="image-frame" :class="{ 'low-res-image': isLowResolution(hit) }">
          <img :src="hit.url" :alt="hit.name" />
        </div>
        <div class="meta">
          <strong>{{ hit.name }}</strong>
          <span>{{ hit.score.toFixed(4) }}</span>
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
