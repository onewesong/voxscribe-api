import os
import tempfile
from typing import List, Optional, Annotated

import whisper
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, Header, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

app = FastAPI(
    title="VoxScribe API",
    description="语音识别和转录API，基于OpenAI的Whisper模型",
    version="0.1.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 获取环境变量中的API令牌
API_TOKEN = os.environ.get("VOXSCRIBE_API_KEY")
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

# 验证API令牌的依赖函数
async def verify_token(authorization: str = Security(api_key_header)):
    if not API_TOKEN:
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
    
    if token != API_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="认证令牌无效",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return True

# 可用的模型列表
AVAILABLE_MODELS = ["tiny", "base", "small", "medium", "large", "tiny.en", "base.en", "small.en", "medium.en", "turbo"]

# 模型缓存
models = {}


class TranscriptionResponse(BaseModel):
    text: str
    segments: Optional[List[dict]] = None
    language: str


@app.get("/")
async def root():
    return {"message": "欢迎使用VoxScribe API，基于OpenAI的Whisper模型"}


@app.get("/models", dependencies=[Depends(verify_token)])
async def list_models():
    return {"models": AVAILABLE_MODELS}


def load_model(model_name: str):
    if model_name not in AVAILABLE_MODELS:
        raise HTTPException(status_code=400, detail=f"模型 {model_name} 不可用。请选择以下模型之一: {', '.join(AVAILABLE_MODELS)}")
    
    if model_name not in models:
        try:
            models[model_name] = whisper.load_model(model_name)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"加载模型 {model_name} 时出错: {str(e)}")
    
    return models[model_name]


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
    
    - **file**: 音频文件 (支持格式: mp3, wav, m4a, flac)
    - **model**: 使用的Whisper模型名称 (默认: base)
    - **language**: 音频的语言 (可选，如不提供将自动检测)
    - **task**: 任务类型 (transcribe 或 translate，默认: transcribe)
    - **return_segments**: 是否返回详细的分段信息 (默认: False)
    """
    # 验证文件格式
    allowed_extensions = [".mp3", ".wav", ".m4a", ".flac"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式。请上传以下格式之一: {', '.join(allowed_extensions)}")
    
    # 加载模型
    model_instance = load_model(model)
    
    # 保存上传的文件到临时目录
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
        temp_file.write(await file.read())
        temp_path = temp_file.name
    
    try:
        # 转录参数
        transcribe_options = {
            "task": task
        }
        if language:
            transcribe_options["language"] = language
        
        # 执行转录
        result = model_instance.transcribe(temp_path, **transcribe_options)
        
        # 准备响应
        response = {
            "text": result["text"],
            "language": result["language"]
        }
        
        if return_segments:
            response["segments"] = result["segments"]
        
        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"转录过程中出错: {str(e)}")
    
    finally:
        # 删除临时文件
        if os.path.exists(temp_path):
            os.unlink(temp_path)
