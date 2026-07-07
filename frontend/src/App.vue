<template>
  <header class="toolbar">
    <div class="brand">
      <span class="brand-mark">C</span>
      <span>CBIR Web 系统</span>
    </div>
    <el-menu mode="horizontal" :ellipsis="false" router :default-active="$route.path">
      <el-menu-item index="/search">检索</el-menu-item>
      <el-menu-item index="/gallery">图库</el-menu-item>
      <el-menu-item index="/evaluate">评估</el-menu-item>
      <el-menu-item index="/videos">视频检索</el-menu-item>
      <el-menu-item index="/models">模型训练</el-menu-item>
    </el-menu>
    <div class="toolbar-actions">
      <el-tooltip content="在线演示二维码">
        <el-button circle :icon="Grid" @click="qrVisible = true" />
      </el-tooltip>
      <el-tooltip content="管理员配置">
        <el-button circle :icon="Setting" @click="$router.push('/admin')" />
      </el-tooltip>
      <el-tooltip :content="isDark ? '切换白天模式' : '切换夜间模式'">
        <el-button circle :icon="isDark ? Sunny : Moon" @click="toggleTheme" />
      </el-tooltip>
      <DatasetSelector />
    </div>
  </header>
  <el-dialog v-model="qrVisible" title="在线演示二维码" width="340px" class="qr-dialog" append-to-body>
    <div class="qr-card">
      <img src="/demo-qr.png" alt="在线演示网址二维码" />
      <strong>{{ demoUrl }}</strong>
      <span>手机扫码即可打开在线演示页面</span>
    </div>
  </el-dialog>
  <router-view v-slot="{ Component, route }">
    <transition name="page-slide" mode="out-in">
      <keep-alive>
        <component :is="Component" :key="route.path" />
      </keep-alive>
    </transition>
  </router-view>
</template>

<script setup>
import { Grid, Moon, Setting, Sunny } from '@element-plus/icons-vue'
import { computed, onMounted, ref, watch } from 'vue'
import DatasetSelector from './components/DatasetSelector.vue'

const theme = ref(localStorage.getItem('cbir-theme') || 'light')
const qrVisible = ref(false)
const demoUrl = 'https://cbir.sdaudw321.dpdns.org'
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
  min-width: 0;
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

.qr-card {
  display: grid;
  justify-items: center;
  gap: 10px;
  text-align: center;
}

.qr-card img {
  width: min(240px, 72vw);
  aspect-ratio: 1;
  padding: 8px;
  border: 1px solid var(--panel-border);
  border-radius: 8px;
  background: #ffffff;
}

.qr-card strong {
  color: var(--text-main);
  font-size: 15px;
  word-break: break-all;
}

.qr-card span {
  color: var(--text-muted);
  font-size: 13px;
}

@media (max-width: 720px) {
  .brand {
    width: 100%;
  }

  .toolbar-actions {
    flex-wrap: wrap;
    gap: 8px;
  }

  .toolbar-actions :deep(.dataset-selector) {
    flex: 1 1 220px;
    min-width: 0;
  }
}
</style>
