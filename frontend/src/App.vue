<template>
  <header class="toolbar">
    <div class="brand">
      <span class="brand-mark">C</span>
      <span>CBIR Web 系统</span>
    </div>
    <el-menu mode="horizontal" :ellipsis="false" router :default-active="$route.path">
      <el-menu-item index="/search">检索</el-menu-item>
      <el-menu-item index="/gallery">图库</el-menu-item>
      <el-menu-item index="/videos">视频检索</el-menu-item>
      <el-menu-item index="/evaluate">评估</el-menu-item>
      <el-menu-item index="/pipeline">实验流水线</el-menu-item>
    </el-menu>
    <div class="toolbar-actions">
      <el-tooltip :content="isDark ? '切换白天模式' : '切换夜间模式'">
        <el-button circle :icon="isDark ? Sunny : Moon" @click="toggleTheme" />
      </el-tooltip>
      <DatasetSelector />
    </div>
  </header>
  <router-view v-slot="{ Component, route }">
    <transition name="page-slide" mode="out-in">
      <component :is="Component" :key="route.path" />
    </transition>
  </router-view>
</template>

<script setup>
import { Moon, Sunny } from '@element-plus/icons-vue'
import { computed, onMounted, ref, watch } from 'vue'
import DatasetSelector from './components/DatasetSelector.vue'

const theme = ref(localStorage.getItem('cbir-theme') || 'light')
const isDark = computed(() => theme.value === 'dark')

function applyTheme(value) {
  document.documentElement.classList.toggle('dark', value === 'dark')
  localStorage.setItem('cbir-theme', value)
}

function toggleTheme() {
  theme.value = isDark.value ? 'light' : 'dark'
}

watch(theme, applyTheme)

onMounted(() => {
  applyTheme(theme.value)
})
</script>

<style scoped>
.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  color: #ffffff;
  font-size: 15px;
  font-weight: 800;
  border-radius: 8px;
  background: linear-gradient(135deg, #2563eb, #0f766e 55%, #f59e0b);
  box-shadow: 0 8px 18px rgba(37, 99, 235, 0.24);
}
</style>
