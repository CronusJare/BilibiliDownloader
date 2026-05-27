import threading
from pathlib import Path

import requests


class DownloadThread:
    def __init__(self, url: str, output_dir: Path, cookies: str = "",
                 on_meta=None, on_thumbnail=None, on_progress=None,
                 on_finished=None, on_error=None):
        self.url        = url
        self.output_dir = output_dir
        self.cookies    = cookies
        self.on_meta      = on_meta
        self.on_thumbnail = on_thumbnail
        self.on_progress  = on_progress
        self.on_finished  = on_finished
        self.on_error     = on_error
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def is_alive(self) -> bool:
        return self._thread.is_alive()

    def _run(self):
        from downloader import get_metadata, download_video, download_cover
        try:
            meta = get_metadata(self.url, self.cookies)
            if self.on_meta:
                self.on_meta(meta)

            thumb_url = meta.get("thumbnail", "")
            if thumb_url:
                try:
                    r = requests.get(thumb_url, timeout=10)
                    if r.ok and self.on_thumbnail:
                        self.on_thumbnail(r.content)
                except Exception:
                    pass

            video_path = download_video(
                meta, self.output_dir,
                progress_cb=self.on_progress,
                cookies=self.cookies,
            )
            download_cover(meta, self.output_dir, stem=video_path.stem)

            if self.on_finished:
                self.on_finished(video_path)

        except Exception as e:
            if self.on_error:
                self.on_error(str(e))
