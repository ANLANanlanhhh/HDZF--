import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: { port: 3000 },
  /** GitHub Pages 项目页示例：构建前设置环境变量 VITE_BASE=/仓库名/ */
  base: process.env.VITE_BASE || '/'
})
