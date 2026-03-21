import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import LiveView from '../views/LiveView.vue'

const routes = [
  { path: '/', name: 'home', component: HomeView },
  { path: '/live', name: 'live', component: LiveView },
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
