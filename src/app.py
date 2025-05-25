import os
import tempfile
import asyncio
import threading
import logging
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Annotated

import whisper
import torch
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, Header, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from .config import config

# 设置PyTorch线程数以优化性能
torch.set_num_threads(config.TORCH_THREADS)

# 配置日志
logging.basicConfig(level=getattr(logging, config.LOG_LEVEL))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时的初始化
    logger.info(f"VoxScribe API 启动")
    logger.info(f"设备: {WHISPER_DEVICE}")
    logger.info(f"最大工作线程数: {config.MAX_WORKERS}")
    logger.info(f"PyTorch线程数: {config.TORCH_THREADS}")
    logger.info(f"模型缓存: {'启用' if config.ENABLE_MODEL_CACHE else '禁用'}")
    
    yield
    
    # 关闭时清理线程池
    logger.info("正在关闭VoxScribe API...")
    executor.shutdown(wait=True)
    logger.info("线程池已清理，应用已关闭")


app = FastAPI(
    title="VoxScribe API",
    description="语音识别和转录API，基于OpenAI的Whisper模型",
    version="0.1.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API令牌验证
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

# 线程池执行器，用于并发处理转录任务
executor = ThreadPoolExecutor(max_workers=config.MAX_WORKERS)

# 线程锁，用于保护模型加载过程
models_lock = threading.Lock()

# 模型缓存
models = {}

# Whisper设备配置
WHISPER_DEVICE = config.get_whisper_device()
logger.info(f"使用设备: {WHISPER_DEVICE}")


# 验证API令牌的依赖函数
async def verify_token(authorization: str = Security(api_key_header)):
    if not config.API_TOKEN:
        # 如果环境变量中没有设置令牌，则不进行验证
        return True
    
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="缺少认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 检查令牌格式
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        # 尝试直接使用整个头作为令牌
        token = authorization
    
    if token != config.API_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="认证令牌无效",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return True


class TranscriptionResponse(BaseModel):
    text: str
    segments: Optional[List[dict]] = None
    language: str


class ModelInfo(BaseModel):
    name: str
    loaded: bool
    device: str


@app.get("/")
async def root():
    return {
        "message": "欢迎使用VoxScribe API，基于OpenAI的Whisper模型",
        "version": "0.1.0",
        "device": WHISPER_DEVICE,
        "max_workers": config.MAX_WORKERS
    }


@app.get("/models", dependencies=[Depends(verify_token)])
async def list_models():
    model_info = []
    for model_name in config.AVAILABLE_MODELS:
        model_info.append({
            "name": model_name,
            "loaded": model_name in models,
            "device": WHISPER_DEVICE
        })
    return {"models": model_info}


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "loaded_models": list(models.keys()),
        "worker_threads": config.MAX_WORKERS,
        "device": WHISPER_DEVICE
    }


def _load_model_sync(model_name: str):
    """同步加载模型的内部函数"""
    if model_name not in config.AVAILABLE_MODELS:
        raise HTTPException(
            status_code=400, 
            detail=f"模型 {model_name} 不可用。请选择以下模型之一: {', '.join(config.AVAILABLE_MODELS)}"
        )
    
    # 使用线程锁确保模型加载的线程安全
    with models_lock:
        if model_name not in models:
            try:
                logger.info(f"正在加载模型: {model_name}")
                model = whisper.load_model(model_name, device=WHISPER_DEVICE)
                if config.ENABLE_MODEL_CACHE:
                    models[model_name] = model
                    logger.info(f"模型 {model_name} 已加载并缓存")
                else:
                    logger.info(f"模型 {model_name} 已加载（未缓存）")
                return model
            except Exception as e:
                logger.error(f"加载模型 {model_name} 时出错: {str(e)}")
                raise HTTPException(status_code=500, detail=f"加载模型 {model_name} 时出错: {str(e)}")
    
    return models[model_name]


async def load_model_async(model_name: str):
    """异步加载模型"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, _load_model_sync, model_name)


def _transcribe_sync(model_instance, temp_path: str, transcribe_options: dict):
    """同步执行转录的内部函数"""
    try:
        logger.info(f"开始转录音频文件: {temp_path}")
        result = model_instance.transcribe(temp_path, **transcribe_options)
        logger.info(f"转录完成，识别语言: {result.get('language', 'unknown')}")
        return result
    except Exception as e:
        logger.error(f"转录过程中出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"转录过程中出错: {str(e)}")


async def transcribe_async(model_instance, temp_path: str, transcribe_options: dict):
    """异步执行转录"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, _transcribe_sync, model_instance, temp_path, transcribe_options)


def _save_temp_file(file_content: bytes, file_ext: str) -> str:
    """保存临时文件的同步函数"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
        temp_file.write(file_content)
        return temp_file.name


def _cleanup_temp_file(temp_path: str):
    """清理临时文件的同步函数"""
    try:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
            logger.debug(f"已删除临时文件: {temp_path}")
    except Exception as e:
        logger.warning(f"删除临时文件失败: {temp_path}, 错误: {str(e)}")


@app.post("/transcribe", response_model=TranscriptionResponse, dependencies=[Depends(verify_token)])
async def transcribe_audio(
    file: UploadFile = File(...),
    model: str = Form("base"),
    language: Optional[str] = Form(None),
    task: str = Form("transcribe"),
    return_segments: bool = Form(False)
):
    """
    转录上传的音频文件
    
    - **file**: 音频文件 (支持格式: mp3, wav, m4a, flac, ogg, webm)
    - **model**: 使用的Whisper模型名称 (默认: base)
    - **language**: 音频的语言 (可选，如不提供将自动检测)
    - **task**: 任务类型 (transcribe 或 translate，默认: transcribe)
    - **return_segments**: 是否返回详细的分段信息 (默认: False)
    """
    # 验证文件格式
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in config.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的文件格式。请上传以下格式之一: {', '.join(config.ALLOWED_EXTENSIONS)}"
        )
    
    # 检查文件大小
    file_content = await file.read()
    if len(file_content) > config.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"文件过大。最大允许大小: {config.MAX_FILE_SIZE / (1024*1024):.1f}MB"
        )
    
    # 验证任务类型
    if task not in ["transcribe", "translate"]:
        raise HTTPException(status_code=400, detail="任务类型必须是 'transcribe' 或 'translate'")
    
    logger.info(f"收到转录请求 - 模型: {model}, 语言: {language}, 任务: {task}, 文件大小: {len(file_content)/1024:.1f}KB")
    
    # 异步加载模型
    model_instance = await load_model_async(model)
    
    # 在线程池中处理文件IO，避免阻塞主线程
    loop = asyncio.get_event_loop()
    temp_path = await loop.run_in_executor(
        executor, 
        _save_temp_file, 
        file_content, 
        file_ext
    )
    
    try:
        # 转录参数
        transcribe_options = {
            "task": task,
            "verbose": False  # 减少日志输出
        }
        if language:
            transcribe_options["language"] = language
        
        # 异步执行转录
        result = await transcribe_async(model_instance, temp_path, transcribe_options)
        
        # 准备响应
        response = {
            "text": result["text"],
            "language": result["language"]
        }
        
        if return_segments:
            response["segments"] = result["segments"]
        
        logger.info(f"转录完成 - 语言: {result['language']}, 文本长度: {len(result['text'])}")
        return response
    
    finally:
        # 异步删除临时文件
        await loop.run_in_executor(executor, _cleanup_temp_file, temp_path)



