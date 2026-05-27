from pathlib import Path
from config import MODELS_DIR, MODEL_INFO


def is_model_ready(model_name: str) -> bool:
    """检查指定模型文件是否存在于 Models/ 目录且完整（大小 > 0）。"""
    path = get_model_path(model_name)
    return path.exists() and path.stat().st_size > 0


def get_model_path(model_name: str) -> Path:
    """返回模型文件的绝对路径。"""
    filename = MODEL_INFO[model_name]["filename"]
    return MODELS_DIR / filename


def load_model(model_name: str):
    """从 Models/ 目录加载 Whisper 模型，不使用默认缓存路径。"""
    import whisper
    model_path = get_model_path(model_name)
    if not model_path.exists():
        raise FileNotFoundError(f"模型文件不存在: {model_path}")
    return whisper.load_model(str(model_path))


def list_downloaded_models() -> list:
    """返回 Models/ 目录中已下载的模型名称列表。"""
    return [
        name for name, info in MODEL_INFO.items()
        if (MODELS_DIR / info["filename"]).exists()
    ]
