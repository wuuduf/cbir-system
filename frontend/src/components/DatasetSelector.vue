<template>
  <el-select v-model="store.currentDataset" class="dataset-selector" placeholder="数据集">
    <el-option
      v-for="dataset in datasets"
      :key="dataset.key"
      :label="`${dataset.display_name} (${dataset.count})`"
      :value="dataset.key"
    />
  </el-select>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { fetchDatasets } from '../api/cbir'
import { useAppStore } from '../store/useAppStore'

const store = useAppStore()
const datasets = ref([])

onMounted(async () => {
  datasets.value = await fetchDatasets()
  if (datasets.value.length > 0 && !datasets.value.some((item) => item.key === store.currentDataset)) {
    store.currentDataset = datasets.value[0].key
  }
})
</script>

<style scoped>
.dataset-selector {
  width: 180px;
}

@media (max-width: 720px) {
  .dataset-selector {
    width: 100%;
  }
}
</style>
