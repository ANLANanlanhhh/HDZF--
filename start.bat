@echo off
echo 启动智盾系统...
echo.

echo [1/2] 启动后端服务...
start cmd /k "cd backend && python main.py"

timeout /t 3 /nobreak >nul

echo [2/2] 启动前端服务...
start cmd /k "cd frontend && npm run dev"

echo.
echo 系统启动中，请稍候...
echo 前端地址: http://localhost:3000
echo 后端地址: http://localhost:8000
