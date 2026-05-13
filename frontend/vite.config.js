import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: { port: 3000 },
  /** GitHub Pages 项目页示例：构建前设置环境变量 VITE_BASE=/仓库名/ */
  base: process.env.VITE_BASE || '/',
  build: {
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined
          if (id.includes('echarts') || id.includes('zrender')) return 'vendor-echarts'
          if (
            id.includes('html2pdf.js') ||
            id.includes('html2canvas') ||
            id.includes('jspdf') ||
            id.includes('canvg')
          ) {
            return 'vendor-pdf'
          }
          if (id.includes('vue')) return 'vendor-vue'
          return 'vendor'
        }
      }
    }
  }
})
