import json
import os
import subprocess
import tempfile
from pathlib import Path

from model_manager import load_model
from utils import get_ffmpeg, get_ffmpeg_dir


def _ensure_ffmpeg_in_path():
    """把 ffmpeg 目录加入当前进程 PATH，Whisper 内部调用 ffmpeg 时能找到。"""
    ffmpeg_dir = get_ffmpeg_dir()
    current = os.environ.get("PATH", "")
    if ffmpeg_dir not in current:
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + current


def get_audio_duration(audio_path: Path) -> float:
    """用 ffmpeg 获取音频时长（秒），兼容无 ffprobe 环境。"""
    ffmpeg = get_ffmpeg()
    result = subprocess.run(
        [ffmpeg, "-i", str(audio_path)],
        capture_output=True, text=True, errors="replace",
    )
    # ffmpeg -i 输出在 stderr，格式: "Duration: HH:MM:SS.ss"
    for line in result.stderr.splitlines():
        if "Duration:" in line:
            parts = line.strip().split("Duration:")[1].split(",")[0].strip()
            h, m, s = parts.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    raise RuntimeError(f"无法解析音频时长，ffmpeg 输出:\n{result.stderr[:500]}")


def clip_audio(audio_path: Path, start: float, end: float) -> Path:
    """用 ffmpeg 裁剪音频片段到临时文件，返回临时文件路径。"""
    ffmpeg = get_ffmpeg()
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    cmd = [
        ffmpeg, "-y",
        "-i", str(audio_path),
        "-ss", str(start),
        "-to", str(end),
        "-ar", "16000", "-ac", "1",
        "-c:a", "pcm_s16le",
        tmp.name,
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg 裁剪失败: {result.stderr.decode(errors='replace')}"
        )
    return Path(tmp.name)


def write_srt(segments: list, stem: str, out_dir: Path) -> Path:
    """将 Whisper segments 写成标准 SRT 文件。"""
    srt_path = out_dir / f"{stem}.srt"
    lines = []
    for i, seg in enumerate(segments, 1):
        start = _fmt_timestamp(seg["start"])
        end   = _fmt_timestamp(seg["end"])
        text  = seg["text"].strip()
        lines.append(f"{i}\n{start} --> {end}\n{text}\n")
    srt_path.write_text("\n".join(lines), encoding="utf-8")
    return srt_path


def write_txt(text: str, stem: str, out_dir: Path) -> Path:
    """将完整转录文本写入 TXT 文件。"""
    txt_path = out_dir / f"{stem}.txt"
    txt_path.write_text(text.strip(), encoding="utf-8")
    return txt_path


def transcribe(
    audio_path: Path,
    model_name: str = "base",
    language: str = "zh",
    progress_cb=None,
) -> tuple:
    """
    分片转录音频，每 30 秒 emit 一次进度。
    返回 (srt_path, txt_path)。
    """
    _ensure_ffmpeg_in_path()   # Whisper 内部也需要 ffmpeg
    model    = load_model(model_name)
    duration = get_audio_duration(audio_path)
    out_dir  = audio_path.parent

    CHUNK        = 30.0
    all_segments = []
    offset       = 0.0

    while offset < duration:
        end        = min(offset + CHUNK, duration)
        chunk_path = clip_audio(audio_path, offset, end)
        try:
            transcribe_kwargs = dict(language=language, verbose=False)
            if language == "zh":
                # Bias Whisper toward Simplified Chinese characters
                transcribe_kwargs["initial_prompt"] = "以下是普通话的句子，请使用简体中文。"
            result = model.transcribe(str(chunk_path), **transcribe_kwargs)
        finally:
            chunk_path.unlink(missing_ok=True)

        for seg in result["segments"]:
            seg["start"] += offset
            seg["end"]   += offset
        all_segments.extend(result["segments"])

        offset = end
        if progress_cb:
            progress_cb(int(min(offset / duration * 100, 99)))

    full_text = " ".join(s["text"].strip() for s in all_segments)
    srt_path  = write_srt(all_segments, audio_path.stem, out_dir)
    txt_path  = write_txt(full_text, audio_path.stem, out_dir)

    if progress_cb:
        progress_cb(100)

    return srt_path, txt_path


def _fmt_timestamp(seconds: float) -> str:
    """转为 SRT 时间戳格式 HH:MM:SS,mmm。"""
    ms  = int(seconds * 1000)
    s   = ms // 1000
    ms  = ms % 1000
    m   = s // 60
    s   = s % 60
    h   = m // 60
    m   = m % 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
