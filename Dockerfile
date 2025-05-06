FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY src/ .

# 暴露端口
EXPOSE 8000

# 启动应用
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"] 