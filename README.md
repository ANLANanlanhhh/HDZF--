# 智盾·认知疫苗系统

基于情感计算的适老化反诈骗"数字疫苗"系统2026.5.14

**完整交接说明请见：[交接说明.md](./交接说明.md)**（启动、配置、接口、常见问题）。

## 项目结构
- `frontend/` - Vue 3 前端（适老化极简UI）
- `backend/` - Python FastAPI 后端

## 快速启动

### 后端
```bash
cd backend
pip install -r requirements.txt
python main.py
```

### 前端
```bash
cd frontend
npm install
npm run dev
```

开发服务器默认 **http://localhost:3000**（见 `frontend/vite.config.js`）。

### 生产构建
建议使用 Node.js 22 LTS。当前项目会在构建前检查 Node 版本，避免部分 Windows Node 24 早期版本导致 Vite/Rollup 原生崩溃。

```bash
cd frontend
npm ci
npm run build
```

线上前后端同域部署时，前端默认请求同源 `/api` 和 `/chat`；如果前后端分开部署，请在构建前设置 `VITE_API_BASE=https://你的后端域名`。

后端可用环境变量 `CORS_ORIGINS` 限制允许访问的前端域名，多个域名用英文逗号分隔；不设置时默认允许所有来源。

### Windows 一键启动
双击根目录 `start.bat`（会打开两个命令行窗口）。
