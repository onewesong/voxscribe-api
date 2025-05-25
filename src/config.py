import os
from typing import Optional


class Config:
    """应用配置类"""
    
    # API认证
    API_TOKEN: Optional[str] = os.environ.get("VOXSCRIBE_API_KEY")
    
    # 并发配置
    MAX_WORKERS: int = int(os.environ.get("MAX_WORKERS", os.cpu_count() or 4))
    
    # 文件上传配置
    MAX_FILE_SIZE: int = int(os.environ.get("MAX_FILE_SIZE", 50 * 1024 * 1024))  # 50MB
    ALLOWED_EXTENSIONS = [".mp3", ".wav", ".m4a", ".flac", ".ogg", ".webm"]
    
    # Whisper模型配置
    AVAILABLE_MODELS = [
        "tiny", "base", "small", "medium", "large", 
        "tiny.en", "base.en", "small.en", "medium.en", "turbo"
    ]
    
    # 模型缓存配置
    ENABLE_MODEL_CACHE: bool = os.environ.get("ENABLE_MODEL_CACHE", "true").lower() == "true"
    
    # 日志配置
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")
    
    # 性能优化配置
    TORCH_THREADS: int = int(os.environ.get("TORCH_THREADS", 1))  # PyTorch线程数
    
    @classmethod
    def get_whisper_device(cls) -> str:
        """获取Whisper使用的设备"""
        device = os.environ.get("WHISPER_DEVICE", "auto")
        if device == "auto":
            try:
                import torch
                return "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                return "cpu"
        return device


config = Config() 