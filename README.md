# VoxScribe API

基于OpenAI Whisper模型的高性能语音识别和转录API，支持并发处理。

## 功能特性

- 🎙️ 支持多种音频格式：MP3, WAV, M4A, FLAC, OGG, WebM
- 🚀 **高并发处理**：支持多个请求同时处理
- 🔄 智能模型缓存和线程安全
- 🔐 可选的API令牌认证
- 📊 详细的健康检查和监控
- 🐳 Docker容器化部署
- ⚡ GPU/CPU自适应加速

## 并发优化

### 核心特性
- **异步处理**：所有I/O操作都是异步的，避免阻塞
- **线程池执行**：Whisper转录在独立线程池中执行
- **模型缓存**：智能模型缓存机制，支持线程安全访问
- **资源优化**：可配置的工作线程数和PyTorch线程数

### 环境变量配置
```bash
# 并发配置
MAX_WORKERS=8                    # 最大工作线程数（默认：CPU核心数）
TORCH_THREADS=1                  # PyTorch线程数（建议设为1以避免过度订阅）

# 性能配置
WHISPER_DEVICE=auto              # 设备选择：auto, cpu, cuda
ENABLE_MODEL_CACHE=true          # 是否启用模型缓存

# 文件限制
MAX_FILE_SIZE=52428800           # 最大文件大小（字节，默认50MB）

# 日志配置
LOG_LEVEL=INFO                   # 日志级别：DEBUG, INFO, WARNING, ERROR
```

## 安装和运行

### 1. 环境准备
```bash
# 克隆项目
git clone <repository-url>
cd voxscribe-api

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 运行API服务
```bash
# 开发模式（支持热重载）
make dev

# 生产模式
make run

# 或直接使用uvicorn
uvicorn src.app:app --host 0.0.0.0 --port 8000 --workers 4
```

### 3. Docker部署
```bash
# 构建并运行
make docker-up

# 或手动构建
docker build -t voxscribe-api .
docker run -p 8000:8000 voxscribe-api
```

## API端点

### 健康检查
```bash
curl http://localhost:8000/health
```

### 获取可用模型
```bash
curl http://localhost:8000/models
```

### 音频转录
```bash
curl -X POST http://localhost:8000/transcribe \
  -H "Content-Type: multipart/form-data" \
  -F "file=@audio.mp3" \
  -F "model=base" \
  -F "language=zh" \
  -F "return_segments=true"
```

## 并发性能测试

项目包含并发测试脚本，用于验证API的并发处理能力：

```bash
# 安装测试依赖
pip install aiohttp

# 运行并发测试
python test_concurrency.py --requests 10 --model tiny

# 指定音频文件和更多参数
python test_concurrency.py \
  --file sample.mp3 \
  --requests 5 \
  --model base \
  --url http://localhost:8000 \
  --token your_api_token
```

### 测试参数
- `--requests`: 并发请求数量（默认：5）
- `--file`: 测试音频文件路径
- `--model`: 使用的Whisper模型（默认：tiny）
- `--url`: API基础URL（默认：http://localhost:8000）
- `--token`: API认证令牌（如果需要）

## 性能优化建议

### 1. 硬件配置
- **CPU**: 多核心处理器，建议8核以上
- **内存**: 至少8GB，大模型需要更多内存
- **GPU**: 支持CUDA的NVIDIA GPU可显著提升性能

### 2. 环境变量优化
```bash
# 针对4核CPU的推荐配置
export MAX_WORKERS=4
export TORCH_THREADS=1
export WHISPER_DEVICE=auto

# 针对GPU的推荐配置
export MAX_WORKERS=2
export TORCH_THREADS=1
export WHISPER_DEVICE=cuda
```

### 3. 模型选择
- **tiny**: 最快，适合实时处理，准确度较低
- **base**: 平衡速度和准确度
- **small**: 更好的准确度，处理时间适中
- **medium/large**: 最高准确度，处理时间较长

### 4. 并发策略
- 小文件 + tiny模型：可以设置较高的并发数
- 大文件 + 大模型：建议降低并发数以避免内存不足
- GPU加速：可以增加并发数，但注意GPU内存限制

## 故障排除

### 常见问题

1. **内存不足**
   ```bash
   # 减少工作线程数
   export MAX_WORKERS=2
   # 禁用模型缓存
   export ENABLE_MODEL_CACHE=false
   ```

2. **GPU内存不足**
   ```bash
   # 切换到CPU
   export WHISPER_DEVICE=cpu
   # 或减少并发数
   export MAX_WORKERS=1
   ```

3. **文件上传失败**
   ```bash
   # 增加文件大小限制
   export MAX_FILE_SIZE=104857600  # 100MB
   ```

### 日志分析
```bash
# 启用详细日志
export LOG_LEVEL=DEBUG

# 查看API日志
tail -f app.log
```

## 部署建议

### 生产环境
```bash
# 使用Gunicorn + Uvicorn
gunicorn src.app:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# 或使用Docker Compose
docker-compose up -d
```

### 负载均衡
如果需要处理大量并发请求，建议：
1. 使用Nginx进行负载均衡
2. 部署多个API实例
3. 使用Redis进行任务队列管理

## 许可证

[MIT License](LICENSE)

## 贡献

欢迎提交问题和改进建议！
