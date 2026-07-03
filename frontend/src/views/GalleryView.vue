<template>
  <main class="page">
    <BlockingOverlay
      :visible="busy"
      title="正在同步图库"
      :message="busyMessage"
      description="操作期间已锁定页面，索引同步完成后会自动恢复。"
    />
    <section class="panel gallery-tools">
      <div>
        <strong>图库管理</strong>
        <p class="muted">当前数据集：{{ store.currentDataset }}，共 {{ total }} 张</p>
      </div>
      <el-select
        v-model="category"
        clearable
        placeholder="类别"
        style="width: 180px"
        :disabled="busy"
        @change="loadImages"
      >
        <el-option v-for="item in categories" :key="item" :label="item" :value="item" />
      </el-select>
      <el-segmented v-model="displayMode" :options="displayModeOptions" />
      <el-upload :auto-upload="false" :show-file-list="false" :disabled="busy" :on-change="uploadSelected">
        <el-button type="primary" :disabled="busy">上传图片</el-button>
      </el-upload>
      <el-button :loading="building" :disabled="busy" @click="rebuild">重建索引</el-button>
    </section>

    <section v-loading="loading" class="gallery-grid">
      <article v-for="image in images" :key="image.id" class="gallery-card">
        <div class="gallery-image" :class="{ 'low-res-image': shouldUseOriginalSize(image) }">
          <img :src="image.url" :alt="image.name" />
        </div>
        <div class="card-meta">
          <strong>{{ image.name }}</strong>
          <el-tag v-if="image.category" size="small">{{ image.category }}</el-tag>
        </div>
        <el-button type="danger" plain size="small" :disabled="busy" @click="remove(image)">删除</el-button>
      </article>
      <el-empty v-if="!loading && images.length === 0" description="暂无图片" />
    </section>

    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        :page-size="size"
        layout="prev, pager, next"
        :total="total"
        :disabled="busy"
        @current-change="loadImages"
      />
    </div>
  </main>
</template>

<script setup>
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, ref, watch } from 'vue'
import { buildIndex, deleteImage, fetchCategories, fetchImages, uploadImage } from '../api/cbir'
import BlockingOverlay from '../components/BlockingOverlay.vue'
import { useAppStore } from '../store/useAppStore'

const store = useAppStore()
const images = ref([])
const categories = ref([])
const category = ref('')
const page = ref(1)
const size = 24
const total = ref(0)
const loading = ref(false)
const building = ref(false)
const mutating = ref(false)
const displayMode = ref(localStorage.getItem('cbir-gallery-display-mode') || 'original')
const displayModeOptions = [
  { label: '原始尺寸', value: 'original' },
  { label: '平滑放大', value: 'smooth' }
]
const allFeatures = ['color_hist', 'color_moments', 'glcm', 'lbp', 'hu', 'eoh', 'deep', 'clip']
const busy = computed(() => building.value || mutating.value)
const busyMessage = computed(() => {
  if (building.value) {
    return '正在重建 CIFAR-10 全量索引'
  }
  return '正在保存图库变更并同步索引'
})

async function loadImages() {
  loading.value = true
  try {
    const result = await fetchImages({
      dataset: store.currentDataset,
      page: page.value,
      size,
      category: category.value
    })
    images.value = result.items
    total.value = result.total
  } finally {
    loading.value = false
  }
}

async function loadCategories() {
  categories.value = await fetchCategories(store.currentDataset)
}

async function uploadSelected(uploadFile) {
  mutating.value = true
  try {
    await uploadImage({
      dataset: store.currentDataset,
      file: uploadFile.raw,
      category: category.value
    })
    ElMessage.success('上传完成，索引已同步')
    await loadCategories()
    await loadImages()
  } finally {
    mutating.value = false
  }
}

async function remove(image) {
  await ElMessageBox.confirm(`删除 ${image.name}？`, '确认删除', { type: 'warning' })
  mutating.value = true
  try {
    await deleteImage(image.id)
    ElMessage.success('已删除，索引已同步')
    await loadCategories()
    await loadImages()
  } finally {
    mutating.value = false
  }
}

async function rebuild() {
  building.value = true
  try {
    await buildIndex({ dataset: store.currentDataset, features: allFeatures })
    ElMessage.success('索引已重建')
  } finally {
    building.value = false
  }
}

function isLowResolution(image) {
  return Number(image.width || 0) <= 64 && Number(image.height || 0) <= 64
}

function shouldUseOriginalSize(image) {
  return displayMode.value === 'original' && isLowResolution(image)
}

watch(
  () => store.currentDataset,
  async () => {
    page.value = 1
    category.value = ''
    await loadCategories()
    await loadImages()
  }
)

watch(displayMode, (value) => {
  localStorage.setItem('cbir-gallery-display-mode', value)
})

onMounted(async () => {
  await loadCategories()
  await loadImages()
})
</script>

<style scoped>
.gallery-tools {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.gallery-tools p {
  margin: 6px 0 0;
}

.gallery-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 14px;
  min-height: 220px;
}

.gallery-card {
  padding: 10px;
  background: var(--panel-solid);
  border: 1px solid var(--panel-border);
  border-radius: 8px;
}

.gallery-image {
  display: grid;
  place-items: center;
  overflow: hidden;
  width: 100%;
  aspect-ratio: 1;
  border-radius: 8px;
  background: color-mix(in srgb, var(--control-bg), var(--accent-2) 5%);
}

.gallery-card img {
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

.gallery-card:hover img {
  transform: scale(1.06);
}

.card-meta {
  display: grid;
  gap: 6px;
  margin: 8px 0;
  min-height: 54px;
}

.card-meta strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.pager {
  display: flex;
  justify-content: center;
  padding: 22px 0;
}

@media (max-width: 1080px) {
  .gallery-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 680px) {
  .gallery-tools {
    align-items: stretch;
    flex-direction: column;
  }

  .gallery-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
