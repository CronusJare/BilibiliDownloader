import json
from pathlib import Path

# ── 路径常量 ──────────────────────────────────────────
MODELS_DIR  = Path(__file__).parent / "Models"
CONFIG_FILE = Path(__file__).parent / "config.json"

# ── 默认配置 ──────────────────────────────────────────
_DEFAULTS = {
    "model":           "base",
    "language":        "zh",
    "output_dir":      str(Path.home() / "Downloads"),
    "auto_transcribe": True,
    "cookies":         "",
}

# ── 静态常量 ──────────────────────────────────────────
WHISPER_MODELS = ["tiny", "base", "small", "medium", "large"]

MODEL_INFO = {
    "tiny": {
        "size": "~75MB", "vram": "~1GB", "speed": "极快", "accuracy": "较低",
        "filename": "tiny.pt",
        "url": "https://openaipublic.azureedge.net/main/whisper/models/"
               "65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt",
    },
    "base": {
        "size": "~150MB", "vram": "~1GB", "speed": "快", "accuracy": "一般",
        "filename": "base.pt",
        "url": "https://openaipublic.azureedge.net/main/whisper/models/"
               "ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e/base.pt",
    },
    "small": {
        "size": "~490MB", "vram": "~2GB", "speed": "中等", "accuracy": "良好",
        "filename": "small.pt",
        "url": "https://openaipublic.azureedge.net/main/whisper/models/"
               "9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794/small.pt",
    },
    "medium": {
        "size": "~1.5GB", "vram": "~5GB", "speed": "慢", "accuracy": "高",
        "filename": "medium.pt",
        "url": "https://openaipublic.azureedge.net/main/whisper/models/"
               "345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1/medium.pt",
    },
    "large": {
        "size": "~3GB", "vram": "~10GB", "speed": "很慢", "accuracy": "最高",
        "filename": "large-v3.pt",
        "url": "https://openaipublic.azureedge.net/main/whisper/models/"
               "e5b1a55b89c1367dacf97e3e19bfd829a01529dbfdeefa8caeb59b3f1b81dadb/large-v3.pt",
    },
}

VIDEO_FORMAT = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"


# ── 读写接口 ──────────────────────────────────────────
def load_config() -> dict:
    """读取 config.json，缺失字段用默认值填充，文件不存在时返回全默认值。"""
    cfg = dict(_DEFAULTS)
    if CONFIG_FILE.exists():
        try:
            saved = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            cfg.update({k: saved[k] for k in _DEFAULTS if k in saved})
        except (json.JSONDecodeError, OSError):
            pass
    return cfg


def save_config(cfg: dict) -> None:
    """将配置字典写入 config.json（只保存 schema 定义的键）。"""
    to_save = {k: cfg[k] for k in _DEFAULTS if k in cfg}
    CONFIG_FILE.write_text(
        json.dumps(to_save, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
