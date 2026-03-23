# 智盾·认知疫苗系统

基于情感计算的适老化反诈骗"数字疫苗"系统

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

### Windows 一键启动
双击根目录 `start.bat`（会打开两个命令行窗口）。
