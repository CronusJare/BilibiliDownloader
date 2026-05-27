# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Install dependencies:**
```bash
pip install -r requirements.txt
```

**Run the application:**
```bash
python main.py
```

**Run CLI tests:**
```bash
python test_cli.py --test fetch        # T-01: metadata fetch
python test_cli.py --test transcribe --model tiny  # T-02: end-to-end transcription
python test_cli.py --test all          # Run all test cases
```

## Architecture

This is a **pywebview desktop application** with a **Tailwind CSS** (dark blue theme) frontend that downloads Bilibili videos and performs local speech-to-text transcription via OpenAI Whisper. No cloud APIs are used for transcription.

### Three-Phase Workflow
1. **Download** — yt-dlp fetches video metadata, cover, and MP4
2. **Audio extraction** — FFmpeg converts video to 16kHz mono WAV
3. **Transcription** — Whisper processes audio in 30-second chunks, outputs SRT + TXT

### Layer Structure

| Layer | Files | Responsibility |
|---|---|---|
| Frontend | `web/index.html` | Tailwind CSS UI, JS event handlers |
| Python-JS bridge | `api.py` | `API` class exposed to JS via `js_api` |
| Workers | `workers/` | `threading.Thread` subclasses for async ops |
| Business logic | `downloader.py`, `transcribe.py` | Core pipeline logic |
| Config/utilities | `config.py`, `model_manager.py`, `utils.py` | Settings, model lifecycle, helpers |

### Threading Model
All long-running operations run in `threading.Thread` workers. Workers call Python callbacks, which call `window.evaluate_js(...)` to push updates to the UI:
- `workers/download_thread.py` — callbacks: `on_meta`, `on_thumbnail`, `on_progress`, `on_finished`, `on_error`
- `workers/transcribe_thread.py` — callbacks: `on_progress`, `on_result`, `on_error`
- `workers/model_download_thread.py` — model file download with resume support

Worker classes are imported lazily inside `api.py` methods (not at module top level) to avoid blocking startup with heavy imports (`yt_dlp`, `torch`/`whisper`).

`api.py` owns all three threads. When download finishes it checks `auto_transcribe` config and starts transcription automatically — calling `onAutoTranscribeBegin()` and then `onTranscribeProgress/Result` JS callbacks.

### Python ↔ JS Communication
- **JS → Python**: `await window.pywebview.api.methodName(args)` — returns a Promise; all `API` methods run in a worker thread inside pywebview.
- **Python → JS**: `window.evaluate_js("jsFunctionName(arg)")` — callable from any thread; used by worker callbacks to push progress/results.
- File dialogs (`browse_directory`, `browse_file`, `save_txt_dialog`, `save_srt_dialog`) use pywebview's built-in `create_folder_dialog` / `create_file_dialog`.

### Configuration
`config.json` (git-ignored) stores: selected Whisper model, language, output directory, auto-transcribe toggle, cookies path. Managed by `config.py` with defaults fallback. Whisper model metadata (size, VRAM requirements) is also defined in `config.py` as `MODEL_INFO`.

### Output Structure
All files are written directly into the user-configured output directory (no subdirectories):
```
output_dir/{sanitized_title}.mp4   ← video
output_dir/{sanitized_title}.jpg   ← cover thumbnail
output_dir/{sanitized_title}.wav   ← intermediate audio (16kHz mono)
output_dir/{sanitized_title}.srt   ← subtitle file
output_dir/{sanitized_title}.txt   ← plain transcript
```
`_next_available_stem` in `downloader.py` appends `_2`, `_3`, etc. on filename collision.

### FFmpeg Resolution
`utils.get_ffmpeg()` first checks system PATH via `shutil.which`, then falls back to `imageio-ffmpeg`. When using `imageio-ffmpeg`, a `ffmpeg.exe` alias is created in the same directory so yt-dlp can find it by name.

### Whisper Models
Models are stored as `.pt` files in `Models/`. At startup, `main.py` calls `model_manager.is_model_ready()` and prompts the user to download the model via `api.start_model_download()` if missing. Models can also be managed from the Settings page. The `large` model maps to `large-v3.pt`.
