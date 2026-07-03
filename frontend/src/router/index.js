import { createRouter, createWebHistory } from 'vue-router'
import SearchView from '../views/SearchView.vue'
import GalleryView from '../views/GalleryView.vue'
import EvaluateView from '../views/EvaluateView.vue'
import PipelineView from '../views/PipelineView.vue'
import VideoView from '../views/VideoView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/search' },
    { path: '/search', component: SearchView },
    { path: '/gallery', component: GalleryView },
    { path: '/videos', component: VideoView },
    { path: '/evaluate', component: EvaluateView },
    { path: '/pipeline', component: PipelineView }
  ]
})

export default router
