import base64
import json
import shutil
import sys
from pathlib import Path

import webview

from config import load_config, save_config, MODEL_INFO, WHISPER_MODELS
from model_manager import is_model_ready, list_downloaded_models
# Workers are imported lazily inside methods to avoid blocking startup with
# heavy top-level imports (yt_dlp, torch/whisper).


class API:
    def __init__(self):
        self._window: webview.Window | None = None
        self._download_thread  = None
        self._transcribe_thread = None
        self._model_dl_thread  = None
        self._last_video_path: Path | None = None
        self._last_srt_path:   Path | None = None

    def attach_window(self, window: webview.Window):
        self._window = window

    # ── Internal ──────────────────────────────────────────
    def _js(self, code: str):
        if self._window:
            try:
                self._window.evaluate_js(code)
            except Exception:
                pass

    # ── Startup ───────────────────────────────────────────
    def check_startup(self) -> dict:
        cfg = load_config()
        return {
            "model_ready": is_model_ready(cfg["model"]),
            "model_name":  cfg["model"],
            "config":      cfg,
        }

    # ── Config ────────────────────────────────────────────
    def load_config(self) -> dict:
        return load_config()

    def save_config(self, cfg: dict) -> bool:
        save_config(cfg)
        return True

    def get_models_info(self) -> dict:
        downloaded = list_downloaded_models()
        return {
            name: {**MODEL_INFO[name], "downloaded": name in downloaded}
            for name in WHISPER_MODELS
        }

    # ── Model download ────────────────────────────────────
    def start_model_download(self, model_name: str) -> bool:
        from workers.model_download_thread import ModelDownloadThread

        def on_progress(percent: int, speed: str):
            self._js(f"onModelProgress({percent}, {json.dumps(speed)})")

        def on_finished():
            self._js("onModelDownloadDone()")

        def on_error(msg: str):
            self._js(f"onModelError({json.dumps(msg)})")

        self._model_dl_thread = ModelDownloadThread(
            model_name,
            on_progress=on_progress,
            on_finished=on_finished,
            on_error=on_error,
        )
        self._model_dl_thread.start()
        return True

    # ── Video download ────────────────────────────────────
    def start_download(self, url: str) -> bool:
        from workers.download_thread import DownloadThread

        if self._download_thread and self._download_thread.is_alive():
            return False

        cfg = load_config()

        def on_meta(meta: dict):
            filtered = {
                "title":       meta.get("title", ""),
                "uploader":    meta.get("uploader", ""),
                "duration":    meta.get("duration", 0),
                "description": meta.get("description", ""),
                "webpage_url": meta.get("webpage_url", ""),
            }
            self._js(f"onMeta({json.dumps(filtered, ensure_ascii=False)})")

        def on_thumbnail(data: bytes):
            b64 = base64.b64encode(data).decode()
            self._js(f"onThumbnail('data:image/jpeg;base64,{b64}')")

        def on_progress(percent: int, speed: str):
            self._js(f"onDownloadProgress({percent}, {json.dumps(speed)})")

        def on_finished(video_path: Path):
            self._last_video_path = video_path
            self._js(f"onDownloadFinished({json.dumps(str(video_path))})")
            cfg2 = load_config()
            if cfg2.get("auto_transcribe", True):
                self._js("onAutoTranscribeBegin()")
                self._run_transcribe(video_path)

        def on_error(msg: str):
            self._js(f"onDownloadError({json.dumps(msg)})")

        self._download_thread = DownloadThread(
            url=url,
            output_dir=Path(cfg["output_dir"]),
            cookies=cfg.get("cookies", ""),
            on_meta=on_meta,
            on_thumbnail=on_thumbnail,
            on_progress=on_progress,
            on_finished=on_finished,
            on_error=on_error,
        )
        self._download_thread.start()
        return True

    # ── Transcription ─────────────────────────────────────
    def _run_transcribe(self, video_path: Path):
        from workers.transcribe_thread import TranscribeThread

        cfg = load_config()

        def on_progress(percent: int):
            self._js(f"onTranscribeProgress({percent})")

        def on_result(text: str, srt_path: Path):
            self._last_srt_path = srt_path
            self._js(
                f"onTranscribeResult({json.dumps(text, ensure_ascii=False)},"
                f" {json.dumps(str(srt_path))})"
            )

        def on_error(msg: str):
            self._js(f"onTranscribeError({json.dumps(msg)})")

        self._transcribe_thread = TranscribeThread(
            video_path=video_path,
            output_dir=Path(cfg["output_dir"]),
            model_name=cfg["model"],
            language=cfg["language"],
            on_progress=on_progress,
            on_result=on_result,
            on_error=on_error,
        )
        self._transcribe_thread.start()

    # ── File dialogs ──────────────────────────────────────
    def browse_directory(self) -> str | None:
        if not self._window:
            return None
        result = self._window.create_folder_dialog()
        if result:
            return result[0] if isinstance(result, (list, tuple)) else result
        return None

    def browse_file(self) -> str | None:
        if not self._window:
            return None
        result = self._window.create_file_dialog(
            webview.OPEN_DIALOG,
            file_types=("Text Files (*.txt)", "All Files (*.*)"),
        )
        if result:
            return result[0]
        return None

    def save_txt_dialog(self, text: str) -> bool:
        if not self._window:
            return False
        result = self._window.create_file_dialog(
            webview.SAVE_DIALOG,
            save_filename="transcript.txt",
            file_types=("Text Files (*.txt)",),
        )
        if result:
            path = result[0] if isinstance(result, (list, tuple)) else result
            Path(path).write_text(text, encoding="utf-8")
            return True
        return False

    def save_srt_dialog(self) -> bool:
        if not self._last_srt_path:
            return False
        if not self._window:
            return False
        result = self._window.create_file_dialog(
            webview.SAVE_DIALOG,
            save_filename="transcript.srt",
            file_types=("SRT Files (*.srt)",),
        )
        if result:
            path = result[0] if isinstance(result, (list, tuple)) else result
            shutil.copy2(self._last_srt_path, path)
            return True
        return False

    # ── App control ───────────────────────────────────────
    def quit(self):
        sys.exit(0)
