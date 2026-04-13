/**
 * 后端 API 根地址。构建前可在 frontend/.env 里设置：
 *   VITE_API_BASE=https://你的服务.onrender.com
 * 不设则使用下列默认（与项目示例部署一致）。
 */
export const API_BASE =
  (import.meta.env.VITE_API_BASE && String(import.meta.env.VITE_API_BASE).replace(/\/$/, '')) ||
  (import.meta.env.DEV ? 'http://127.0.0.1:8000' : 'https://zhidun.onrender.com')
