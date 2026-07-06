import { createRouter, createWebHistory } from 'vue-router'
import SearchView from '../views/SearchView.vue'

// 首屏检索页直接打包，其余页面按需懒加载，减小首屏体积、加快首屏渲染。
const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/search' },
    { path: '/search', component: SearchView },
    { path: '/gallery', component: () => import('../views/GalleryView.vue') },
    { path: '/videos', component: () => import('../views/VideoView.vue') },
    { path: '/evaluate', component: () => import('../views/EvaluateView.vue') },
    { path: '/models', component: () => import('../views/PipelineView.vue') },
    { path: '/admin', component: () => import('../views/AdminView.vue') },
    { path: '/pipeline', redirect: '/models' }
  ]
})

export default router
