# ============================================
# 织梦绮谭 - Backend Dockerfile
# Python 3.12 + FastAPI + Uvicorn
# ============================================

FROM python:3.12

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8

# 安装 MySQL 客户端开发库（python:3.12 完整镜像已有 gcc 等构建工具）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        default-libmysqlclient-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先复制依赖文件（利用 Docker 缓存层）
COPY requirements.txt .

# 使用清华 pip 镜像源加速下载
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --trusted-host pypi.tuna.tsinghua.edu.cn \
    -r requirements.txt

# 复制应用代码
COPY . .

# 将 .env.prod 复制为 .env（容器内 fallback，docker-compose env_file 优先级更高）
RUN if [ -f .env.prod ]; then cp .env.prod .env; fi

# 创建数据目录
RUN mkdir -p data/chroma data/saves

# 预下载 ChromaDB ONNX 嵌入模型（避免运行时从外网下载）
RUN python -c "from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2; ONNXMiniLM_L6_V2()" 2>/dev/null || true

# 暴露端口
EXPOSE 8000

# 启动命令：生产模式不使用 reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
