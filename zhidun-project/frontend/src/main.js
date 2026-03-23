import { createApp } from 'vue'
import App from './App.vue'
import { createRouter, createWebHistory } from 'vue-router'
import TrainingView from './components/TrainingView.vue'
import ReportView from './components/ReportView.vue'

// 1. 定义路由表，确保 /report 和 / 正确对应组件
const routes = [
  { path: '/', component: TrainingView }, 
  { path: '/report', component: ReportView }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

const app = createApp(App)
app.use(router) // 2. 必须激活路由插件
app.mount('#app')