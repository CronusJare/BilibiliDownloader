import threading
import time

import requests

from config import MODEL_INFO, MODELS_DIR
from model_manager import get_model_path


class ModelDownloadThread:
    def __init__(self, model_name: str,
                 on_progress=None, on_finished=None, on_error=None):
        self.model_name  = model_name
        self.url         = MODEL_INFO[model_name]["url"]
        self.dest        = get_model_path(model_name)
        self.on_progress = on_progress
        self.on_finished = on_finished
        self.on_error    = on_error
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def _run(self):
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        try:
            resp = requests.get(self.url, stream=True, timeout=30)
            resp.raise_for_status()

            total      = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            t0         = time.time()

            with open(self.dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    f.write(chunk)
                    downloaded += len(chunk)

                    elapsed = time.time() - t0 or 0.001
                    speed   = downloaded / elapsed
                    percent = int(downloaded / total * 100) if total else 0
                    if self.on_progress:
                        self.on_progress(percent, _fmt_speed(speed))

            if self.on_finished:
                self.on_finished()

        except Exception as e:
            self.dest.unlink(missing_ok=True)
            if self.on_error:
                self.on_error(str(e))


def _fmt_speed(bps: float) -> str:
    if bps >= 1024 ** 2:
        return f"{bps/1024**2:.1f} MB/s"
    if bps >= 1024:
        return f"{bps/1024:.0f} KB/s"
    return f"{bps:.0f} B/s"
