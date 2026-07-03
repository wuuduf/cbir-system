import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const currentDataset = ref('cifar10')
  return { currentDataset }
})
