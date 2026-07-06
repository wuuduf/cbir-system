<template>
  <main class="page admin-page">
    <section v-if="!token" class="panel login-panel">
      <div class="admin-title">
        <strong>管理员登录</strong>
        <span>输入本地管理员口令后配置 AI 服务。</span>
      </div>
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="管理员密码">
          <el-input
            v-model="password"
            type="password"
            show-password
            placeholder="请输入管理员密码"
            @keyup.enter="login"
          />
        </el-form-item>
        <el-button type="primary" :loading="loading" @click="login">进入管理员页面</el-button>
      </el-form>
    </section>

    <section v-else class="panel config-panel">
      <div class="admin-title">
        <div>
          <strong>AI 接口配置</strong>
          <span>API Key 只保存在后端数据目录，普通评估页不会显示密钥。</span>
        </div>
        <el-button text @click="logout">退出</el-button>
      </div>

      <el-alert
        class="doc-note"
        type="info"
        show-icon
        :closable="false"
        title="DeepSeek 采用 OpenAI 兼容的 Chat Completions 接口；当前页面用于评估结果文本分析，图片特征仍由本系统 CNN、Triplet、CLIP、DINOv2 提取。"
      />

      <el-form label-position="top" class="config-form">
        <el-form-item label="启用 AI 分析">
          <el-switch v-model="form.enabled" />
        </el-form-item>
        <el-form-item label="服务商">
          <el-input v-model="form.provider" />
        </el-form-item>
        <el-form-item label="Base URL">
          <el-input v-model="form.base_url" placeholder="https://api.deepseek.com" />
        </el-form-item>
        <el-form-item label="分析模型">
          <el-input v-model="form.model" placeholder="deepseek-v4-flash" />
        </el-form-item>
        <el-form-item label="视觉模型">
          <el-input v-model="form.vision_model" placeholder="当前 DeepSeek 官方 API 未提供稳定视觉模型时可留空" />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input
            v-model="form.api_key"
            type="password"
            show-password
            placeholder="留空表示沿用已保存的 Key"
          />
          <div v-if="config?.has_api_key" class="key-hint">已保存：{{ config.api_key_hint }}</div>
        </el-form-item>
      </el-form>

      <div class="actions">
        <el-button type="primary" :loading="loading" @click="save">保存配置</el-button>
        <el-button :loading="loading" @click="loadConfig">重新读取</el-button>
      </div>
    </section>
  </main>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'
import { adminLogin, fetchAiConfig, saveAiConfig } from '../api/cbir'

const token = ref(localStorage.getItem('cbir-admin-token') || '')
const password = ref('')
const loading = ref(false)
const config = ref(null)
const form = reactive({
  enabled: false,
  provider: 'deepseek',
  base_url: 'https://api.deepseek.com',
  model: 'deepseek-v4-flash',
  vision_model: '',
  api_key: ''
})

async function login() {
  if (!password.value) {
    ElMessage.warning('请输入管理员密码')
    return
  }
  loading.value = true
  try {
    const data = await adminLogin(password.value)
    token.value = data.token
    localStorage.setItem('cbir-admin-token', token.value)
    password.value = ''
    await loadConfig()
    ElMessage.success('登录成功')
  } catch {
    ElMessage.error('管理员密码不正确')
  } finally {
    loading.value = false
  }
}

async function loadConfig() {
  if (!token.value) return
  loading.value = true
  try {
    const data = await fetchAiConfig(token.value)
    config.value = data
    form.enabled = data.enabled
    form.provider = data.provider
    form.base_url = data.base_url
    form.model = data.model
    form.vision_model = data.vision_model || ''
    form.api_key = ''
  } catch {
    logout()
  } finally {
    loading.value = false
  }
}

async function save() {
  loading.value = true
  try {
    const data = await saveAiConfig(token.value, { ...form })
    config.value = data
    form.api_key = ''
    ElMessage.success('配置已保存')
  } finally {
    loading.value = false
  }
}

function logout() {
  token.value = ''
  localStorage.removeItem('cbir-admin-token')
}

onMounted(() => {
  if (token.value) {
    loadConfig()
  }
})
</script>

<style scoped>
.admin-page {
  display: grid;
  place-items: start center;
}

.login-panel,
.config-panel {
  width: min(760px, 100%);
}

.admin-title {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.admin-title strong {
  display: block;
  font-size: 24px;
}

.admin-title span,
.key-hint {
  color: var(--text-muted);
}

.doc-note {
  margin-bottom: 18px;
}

.config-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 18px;
}

.config-form :deep(.el-form-item) {
  min-width: 0;
}

.actions {
  display: flex;
  gap: 10px;
}

@media (max-width: 760px) {
  .config-form {
    grid-template-columns: 1fr;
  }
}
</style>
