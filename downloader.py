import subprocess
from pathlib import Path

import requests
import yt_dlp

from config import VIDEO_FORMAT
from utils import sanitize_filename, ensure_dirs, get_ffmpeg, get_ffmpeg_dir


def get_metadata(url: str, cookies: str = "") -> dict:
    """调用 yt-dlp 提取视频元数据，不实际下载。"""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
    }
    if cookies:
        ydl_opts["cookiefile"] = cookies

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    return {
        "id":          info.get("id", ""),
        "title":       info.get("title", "未知标题"),
        "description": info.get("description", ""),
        "thumbnail":   info.get("thumbnail", ""),
        "webpage_url": info.get("webpage_url", url),
        "duration":    info.get("duration", 0),
        "uploader":    info.get("uploader", "未知UP主"),
    }


def download_video(meta: dict, output_dir: Path,
                   progress_cb=None, cookies: str = "") -> Path:
    """下载最高画质 MP4，返回本地文件路径。"""
    ensure_dirs(output_dir)
    safe_title = sanitize_filename(meta["title"]) or "未命名视频"
    stem = _next_available_stem(output_dir, safe_title)
    outtmpl = str(output_dir / f"{stem}.%(ext)s")

    def _hook(d):
        if d["status"] == "downloading" and progress_cb:
            total   = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            current = d.get("downloaded_bytes", 0)
            speed   = d.get("speed") or 0
            percent = int(current / total * 100) if total else 0
            speed_str = _fmt_speed(speed)
            progress_cb(percent, speed_str)
        elif d["status"] == "finished" and progress_cb:
            progress_cb(100, "")

    ydl_opts = {
        "format":               VIDEO_FORMAT,
        "merge_output_format":  "mp4",
        "outtmpl":              outtmpl,
        "progress_hooks":       [_hook],
        "quiet":                True,
        "no_warnings":          True,
        "ffmpeg_location":      get_ffmpeg_dir(),
    }
    if cookies:
        ydl_opts["cookiefile"] = cookies

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([meta["webpage_url"]])

    video_path = output_dir / f"{stem}.mp4"
    if not video_path.exists():
        raise FileNotFoundError("视频下载完成但找不到输出文件")
    return video_path


def download_cover(meta: dict, output_dir: Path, stem: str | None = None) -> Path:
    """下载视频封面图到输出目录，返回本地路径。"""
    ensure_dirs(output_dir)
    safe_title = sanitize_filename(meta["title"]) or "未命名视频"
    final_stem = stem or _next_available_stem(output_dir, safe_title)
    dest = output_dir / f"{final_stem}.jpg"

    if not meta.get("thumbnail"):
        return dest

    resp = requests.get(meta["thumbnail"], timeout=15)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    return dest


def extract_audio(video_path: Path, output_dir: Path) -> Path:
    """用 ffmpeg 从视频中提取 16kHz 单声道 WAV，返回音频路径。"""
    ensure_dirs(output_dir)
    audio_path = output_dir / (video_path.stem + ".wav")
    cmd = [
        get_ffmpeg(), "-y",
        "-i", str(video_path),
        "-ar", "16000",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        str(audio_path),
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg 提取音频失败:\n{result.stderr.decode(errors='replace')}"
        )
    return audio_path


# ── 内部工具 ──────────────────────────────────────────
def _fmt_speed(bps: float) -> str:
    if bps <= 0:
        return ""
    if bps >= 1024 ** 2:
        return f"{bps/1024**2:.1f} MB/s"
    if bps >= 1024:
        return f"{bps/1024:.0f} KB/s"
    return f"{bps:.0f} B/s"


def _next_available_stem(output_dir: Path, base_stem: str) -> str:
    candidate = base_stem
    idx = 2
    while (output_dir / f"{candidate}.mp4").exists() or (output_dir / f"{candidate}.jpg").exists():
        candidate = f"{base_stem}_{idx}"
        idx += 1
    return candidate
