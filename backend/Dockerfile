# 1. 指定现代的 Python 3.11 运行环境
FROM python:3.10-slim

# 2. 设置容器内的工作目录
WORKDIR /app

# 3. 先复制依赖文件，利用 Docker 缓存加速构建
COPY requirements.txt .

# 4. 安装你的 FastAPI 等所有依赖
RUN pip install --no-cache-dir -r requirements.txt

# 5. 把 backend 目录下的所有代码复制到容器中
COPY . .

# 6. 暴露 80 端口（这和你截图中配置的端口保持一致）
EXPOSE 80

# 7. 启动 FastAPI 服务
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]