import re
import shutil
import sys
from pathlib import Path

# ── ffmpeg 路径缓存 ───────────────────────────────────
_ffmpeg_exe: str | None = None
_ffmpeg_dir: str | None = None


def _resolve_ffmpeg() -> tuple[str, str]:
    """
    返回 (ffmpeg可执行文件路径, 所在目录)。
    优先用系统 PATH；回退到 imageio-ffmpeg，
    并在同目录创建 ffmpeg.exe 别名（yt-dlp 按名称查找）。
    """
    global _ffmpeg_exe, _ffmpeg_dir
    if _ffmpeg_exe:
        return _ffmpeg_exe, _ffmpeg_dir

    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        _ffmpeg_exe = sys_ffmpeg
        _ffmpeg_dir = str(Path(sys_ffmpeg).parent)
        return _ffmpeg_exe, _ffmpeg_dir

    try:
        import imageio_ffmpeg
        src = Path(imageio_ffmpeg.get_ffmpeg_exe())
        # 在同目录创建 ffmpeg.exe 别名，供 yt-dlp 按名称发现
        alias = src.parent / ("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
        if not alias.exists():
            shutil.copy2(src, alias)
        _ffmpeg_exe = str(alias)
        _ffmpeg_dir = str(alias.parent)
        return _ffmpeg_exe, _ffmpeg_dir
    except ImportError:
        raise RuntimeError(
            "未找到 ffmpeg，请安装 ffmpeg 或运行: pip install imageio-ffmpeg"
        )


def get_ffmpeg() -> str:
    """返回 ffmpeg 可执行文件路径。"""
    exe, _ = _resolve_ffmpeg()
    return exe


def get_ffmpeg_dir() -> str:
    """返回包含 ffmpeg 的目录路径（供 yt-dlp ffmpeg_location 使用）。"""
    _, d = _resolve_ffmpeg()
    return d


def sanitize_filename(name: str, max_len: int = 80) -> str:
    """去除文件名中的非法字符，截断到 max_len 个字符。"""
    name = re.sub(r'[\\/:*?"<>|]', "_", name)
    name = name.strip(". ")
    return name[:max_len]


def format_duration(seconds: int) -> str:
    """将秒数格式化为 HH:MM:SS。"""
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def ensure_dirs(output_dir: Path) -> None:
    """确保输出目录存在。"""
    output_dir.mkdir(parents=True, exist_ok=True)
