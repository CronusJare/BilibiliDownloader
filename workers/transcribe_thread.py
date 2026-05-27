import threading
from pathlib import Path


class TranscribeThread:
    def __init__(self, video_path: Path, output_dir: Path,
                 model_name: str = "base", language: str = "zh",
                 on_progress=None, on_result=None, on_error=None):
        self.video_path = video_path
        self.output_dir = output_dir
        self.model_name = model_name
        self.language   = language
        self.on_progress = on_progress
        self.on_result   = on_result
        self.on_error    = on_error
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def _run(self):
        from downloader import extract_audio
        from transcribe import transcribe
        try:
            audio_path = extract_audio(self.video_path, self.output_dir)
            srt_path, txt_path = transcribe(
                audio_path,
                model_name=self.model_name,
                language=self.language,
                progress_cb=self.on_progress,
            )
            text = txt_path.read_text(encoding="utf-8")
            if self.on_result:
                self.on_result(text, srt_path)

        except Exception as e:
            if self.on_error:
                self.on_error(str(e))
