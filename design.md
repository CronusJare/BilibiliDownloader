# Bilibili Video Downloader & Speech-to-Text Tool — Design Document

**Project Name**: bilibili-dl  
**Document Version**: v1.4  
**Date**: 2026-04-02  
**Status**: Design Phase

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Functional Requirements](#2-functional-requirements)
3. [UI/UX Design](#3-uiux-design)
4. [Technology Stack](#4-technology-stack)
5. [System Architecture](#5-system-architecture)
6. [Module Design](#6-module-design)
7. [Data Flow](#7-data-flow)
8. [Directory Structure](#8-directory-structure)
9. [Output Specifications](#9-output-specifications)
10. [Error Handling](#10-error-handling)
11. [Dependencies & Environment](#11-dependencies--environment)
12. [Notes & Limitations](#12-notes--limitations)
13. [CLI Test Module](#13-cli-test-module)
14. [Model Management](#14-model-management)

---

## 1. Project Overview

`bilibili-dl` is a Python desktop application with a graphical interface. Given a Bilibili video URL, it automatically performs three tasks:

- Downloads the highest-quality video file (MP4) and cover image (JPG/WebP)
- After a **successful** download, automatically triggers audio extraction and calls a local Whisper model for speech recognition
- Outputs subtitle files (SRT) and plain-text transcripts (TXT)

The entire pipeline **requires no cloud API keys** — speech recognition runs entirely locally, making it suitable for privacy-sensitive scenarios.

### Design Principles

- **GUI-first**: Visual desktop interface with a left sidebar + main content area dual-panel layout
- **Serial pipeline**: Speech-to-text is triggered automatically only after the download completes, avoiding concurrent resource contention
- **Local-first**: Whisper model inference runs locally; no audio data is uploaded
- **Structured output**: All files are organized into subdirectories by type for easy management
- **Decoupled modules**: Download, extraction, and transcription are independent modules that can be invoked or extended individually

---

## 2. Functional Requirements

### Core Features

| ID | Feature | Description |
|----|---------|-------------|
| F-01 | Video download | Uses yt-dlp to fetch Bilibili CDN links and download the highest-quality MP4 |
| F-02 | Cover download | Extracts the thumbnail URL from video metadata and downloads the cover image |
| F-03 | Audio extraction | Extracts the audio track from the downloaded video file and converts it to WAV |
| F-04 | Speech-to-text | Runs the local Whisper model on the audio and outputs SRT and TXT |
| F-05 | Video info display | Shows video title, cover image, description, and original URL in the Download panel in real time |
| F-06 | Transcript display | Shows recognition progress and the full transcript text in the Speech-to-Text panel |
| F-07 | Left navigation menu | Searchable sidebar navigation with "Download" and "Settings" page entries |

### Optional Features

| ID | Feature | Description |
|----|---------|-------------|
| O-01 | Skip transcription | Auto-transcription toggle can be disabled in the Settings page |
| O-02 | Model selection | Settings page supports selecting tiny / base / small / medium / large |
| O-03 | Language selection | Defaults to `zh` in Settings; can be changed |
| O-04 | Cookie support | Settings page allows configuring a cookies file path for premium-member videos |
| O-05 | Custom output directory | Settings page allows configuring the output root directory (default: system Downloads folder, `~/Downloads`) |

---

## 3. UI/UX Design

### 3.1 Overall Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  bilibili-dl                                              [─][□][×] │
├──────────────┬──────────────────────────────────────────────────────┤
│              │                                                      │
│  🔍 Search   │               Main Content Area                      │
│  ──────────  │                                                      │
│  ▶ Download  │                                                      │
│    Settings  │                                                      │
│              │                                                      │
│              │                                                      │
│              │                                                      │
└──────────────┴──────────────────────────────────────────────────────┘
```

- **Left navigation bar** (~180px wide): search box at the top, menu items listed below, "Download" highlighted by default
- **Main content area**: renders the corresponding page based on the selected menu item

---

### 3.2 Left Navigation Bar

```
┌──────────────┐
│ 🔍 [Search…] │  ← Real-time filtering of menu items (instant filter on input)
│ ──────────── │
│ ▶ Download   │  ← Selected by default; icon + label
│   Settings   │
└──────────────┘
```

**Menu items** (2 total):

| Order | Icon | Name | Default |
|-------|------|------|---------|
| 1 | ⬇ | Download | Yes |
| 2 | ⚙ | Settings | No |

**Search behavior**: The input box filters menu item labels in real time using partial, case-insensitive matching — matching items are shown, non-matching items are hidden. Clearing the input restores all items.

---

### 3.3 Download Page (Dual-Panel Layout)

The Download page is split horizontally into two equally-wide panels that are always visible simultaneously:

```
┌──────────────┬───────────────────────┬───────────────────────────┐
│  Left Nav    │     Download Panel     │  Speech-to-Text Panel     │
│              │ ─────────────────────  │ ──────────────────────── │
│ ▶ Download   │ URL input  [Download]  │  [Status] Waiting…        │
│   Settings   │                        │                           │
│              │ ┌──────────────────┐  │                           │
│              │ │   Cover image    │  │                           │
│              │ └──────────────────┘  │                           │
│              │ Title: xxx             │  (Starts automatically    │
│              │ Uploader: xxx          │   after download)         │
│              │ Duration: HH:MM:SS     │                           │
│              │ Description: xxxxxx    │                           │
│              │ URL: [original link]   │                           │
│              │                        │                           │
│              │ ── Download Progress ──│  ── Transcript Progress ──│
│              │ [██████████  80%]      │  [████░░░░░░  40%]        │
│              │ Status: Downloading…   │  Whisper recognizing…     │
│              │                        │                           │
│              │                        │  ── Transcript Result ── │
│              │                        │  Hello, welcome to…       │
│              │                        │  Today we'll cover…       │
└──────────────┴───────────────────────┴───────────────────────────┘
```

#### Download Panel (left)

| Area | Content |
|------|---------|
| URL input | Paste or type a Bilibili video link |
| Download button | Fetches metadata first, then starts the download |
| Cover image | Thumbnail rendered immediately after metadata is retrieved |
| Video info | Title, uploader, duration, description (collapsible; expandable when overflow), original URL (clickable) |
| Download progress bar | Shows download percentage and speed in real time |
| Status label | Fetching info / Downloading / Download complete / Download failed |

#### Speech-to-Text Panel (right)

| Area | Content |
|------|---------|
| Waiting state | Shows "Waiting for download to complete…" placeholder before download finishes |
| Transcript progress bar | Starts automatically after download; shows Whisper recognition progress in real time |
| Status label | Extracting audio / Whisper recognizing / Transcript complete / Transcript failed |
| Transcript result | Displays the full recognized text in segments with scrolling support |
| Export buttons | "Copy all", "Save TXT", "Save SRT" actions |

---

### 3.4 Settings Page

```
┌──────────────┬──────────────────────────────────────────────────┐
│  Left Nav    │  ⚙ Settings                                      │
│              │ ──────────────────────────────────────────────── │
│   Download   │  Whisper Model    [base          ▼]              │
│ ▶ Settings   │  Language         [zh             ▼]              │
│              │  Output Dir       [C:\Users\xxx\Downloads] [Browse…]│
│              │  Auto Transcribe  [ ✓ Enabled ]                  │
│              │  Cookies File     [            ] [Browse…]        │
│              │                                                   │
│              │                              [Save Settings]      │
└──────────────┴──────────────────────────────────────────────────┘
```

---

## 4. Technology Stack

| Component | Library/Tool | Version | Rationale |
|-----------|-------------|---------|-----------|
| GUI framework | `PyQt6` | >= 6.4 | Native cross-platform desktop UI with custom styling; QSplitter naturally supports dual-panel layout |
| Video download | `yt-dlp` | >= 2024.1 | Bilibili support, actively maintained, handles CDN authentication automatically |
| Speech recognition | `openai-whisper` | >= 20231117 | Local model, good Chinese support, multiple model sizes |
| Audio processing | `ffmpeg` (system) | >= 4.4 | Already required by yt-dlp; reused directly |
| Async tasks | `QThread` / `QRunnable` | PyQt6 built-in | Download and transcription run in worker threads to keep the UI responsive |
| HTTP requests | `requests` | >= 2.28 | Downloading cover images |
| Progress signals | Qt Signal/Slot | PyQt6 built-in | Worker threads push progress data to the main thread |
| Python version | CPython | >= 3.9 | Minimum required by Whisper |

---

## 5. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       PyQt6 Main Window                          │
│  ┌─────────────┐   ┌──────────────────┬────────────────────┐   │
│  │  Sidebar    │   │  Download Panel   │ Transcribe Panel   │   │
│  │  SearchBar  │   │  (DownloadWidget) │ (TranscribeWidget) │   │
│  │  NavList    │   │                  │                    │   │
│  └─────────────┘   └──────────────────┴────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────┘
                               │ Signal/Slot
           ┌───────────────────┴──────────────────┐
           │         Task Scheduler (main thread)  │
           └──────┬──────────────────┬────────────┘
                  │                  │  download_finished signal triggers
                  ▼                  ▼
      ┌──────────────────┐  ┌──────────────────────┐
      │  DownloadThread  │  │  TranscribeThread     │
      │  (QThread)       │  │  (QThread)            │
      │                  │  │                       │
      │  yt-dlp download │  │  ffmpeg audio extract │
      │  requests cover  │  │  Whisper recognition  │
      └──────────────────┘  └──────────────────────┘
                  │                  │
                  ▼                  ▼
           output/videos/     output/transcripts/
           output/covers/     (SRT + TXT)
```

---

## 6. Module Design

### 6.1 `main.py` — Application Entry Point

**Responsibility**: Initializes `QApplication`, **checks for the model on startup**, and creates the main window if ready.

```python
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Check whether the currently configured model exists in Models/ at startup
    cfg = load_config()
    if not is_model_ready(cfg["model"]):
        dialog = ModelDownloadDialog(model_name=cfg["model"])
        if dialog.exec() != QDialog.Accepted:
            sys.exit(0)          # User chose to exit; don't enter main UI

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
```

**Startup flow**:

```
QApplication initialization
  │
  ├─ load_config()  →  Read config.json (use defaults if missing)
  │
  ├─ is_model_ready(model)
  │     ├─ True  → Show main window directly
  │     └─ False → Show ModelDownloadDialog
  │                   ├─ User downloads (Accepted) → Show main window
  │                   └─ User exits    (Rejected) → sys.exit(0)
  │
  └─ MainWindow.show()
```

---

### 6.2 `ui/main_window.py` — Main Window

**Responsibility**: Assembles the sidebar + main content area and manages page switching.

**Layout**: `QHBoxLayout`
- Left: `SidebarWidget` (fixed width 180px)
- Right: `QStackedWidget` (Download page / Settings page)

**Size constraints**:

```python
self.setMinimumSize(900, 600)   # Minimum usable size for dual-panel
self.resize(1280, 800)          # Default startup size
```

The `QSplitter` inside the dual-panel sets a minimum width of 320px on each side to prevent panels from collapsing fully when dragged:

```python
splitter.setCollapsible(0, False)   # Left panel not collapsible
splitter.setCollapsible(1, False)   # Right panel not collapsible
splitter.setSizes([480, 480])       # Equal width on startup
```

**Signal connections**:
- `SidebarWidget.page_changed` → `QStackedWidget.setCurrentIndex`

---

### 6.3 `ui/sidebar.py` — Left Navigation Bar

**Responsibility**: Renders the searchable menu and emits page-switch signals.

```python
class SidebarWidget(QWidget):
    page_changed = Signal(int)   # 0=Download, 1=Settings

    def __init__(self):
        # Top search box: QLineEdit
        # Menu list: QListWidget
        # textChanged on search box → real-time filtering
        # Item click → emit page_changed signal
```

**Menu item definitions**:

```python
MENU_ITEMS = [
    {"icon": "⬇", "label": "Download", "index": 0},
    {"icon": "⚙", "label": "Settings", "index": 1},
]
```

**Search filter logic**: Iterates all `QListWidgetItem` entries, performs a case-insensitive substring match between each item's `label` and the search box text — matched items call `setHidden(False)`, non-matched items call `setHidden(True)`.

---

### 6.4 `ui/download_page.py` — Download Page

**Responsibility**: Horizontal dual-panel layout; coordinates the download and transcription sub-components.

**Layout**: `QSplitter(Qt.Horizontal)`
- Left: `DownloadPanel`
- Right: `TranscribePanel`

**Core orchestration logic** (serial trigger):

```python
def on_start_download(self):
    url = self.download_panel.get_url()
    self.download_thread = DownloadThread(url, config)
    self.download_thread.meta_ready.connect(self.download_panel.show_video_info)
    self.download_thread.progress.connect(self.download_panel.update_progress)
    self.download_thread.finished.connect(self.on_download_finished)  # Triggers transcription on completion
    self.download_thread.start()

def on_download_finished(self, video_path):
    # Download succeeded → start transcription automatically
    self.transcribe_panel.set_status("Extracting audio…")
    self.transcribe_thread = TranscribeThread(video_path, config)
    self.transcribe_thread.progress.connect(self.transcribe_panel.update_progress)
    self.transcribe_thread.result_ready.connect(self.transcribe_panel.show_result)
    self.transcribe_thread.start()
```

---

### 6.5 `ui/download_panel.py` — Download Panel

**Responsibility**: URL input, video info display, download progress.

**Widgets**:

| Widget | Type | Notes |
|--------|------|-------|
| URL input | `QLineEdit` | Supports paste; triggers on Enter or button click |
| Download button | `QPushButton` | Triggers the download flow |
| Cover image | `QLabel` (pixmap) | Loaded asynchronously after metadata is retrieved |
| Title/Uploader/Duration | `QLabel` | Populated once metadata is ready |
| Description | `QTextEdit` (read-only) | Scrollable when content exceeds 3 lines |
| Original URL | `QLabel` | `setOpenExternalLinks(True)` — clickable |
| Progress bar | `QProgressBar` | 0–100 with percentage text |
| Status label | `QLabel` | Download status description |

**Signals (exposed externally)**:
- `start_requested(url: str)` — emitted when the user clicks Start

**Slots (receiving external updates)**:
- `show_video_info(meta: dict)` — populates the video info area
- `update_progress(percent: int, speed: str)` — updates the progress bar
- `set_status(msg: str)` — updates the status label

---

### 6.6 `ui/transcribe_panel.py` — Speech-to-Text Panel

**Responsibility**: Displays the transcription waiting state, progress, and final result text.

**Widgets**:

| Widget | Type | Notes |
|--------|------|-------|
| Status label | `QLabel` | Initial value: "Waiting for download to complete…" |
| Progress bar | `QProgressBar` | Hidden before download completes; visible during transcription |
| Transcript text box | `QTextEdit` (read-only) | Scrollable segmented display of recognition results |
| Copy button | `QPushButton` | Copies full text to clipboard |
| Save TXT button | `QPushButton` | Save as .txt |
| Save SRT button | `QPushButton` | Save as .srt |

**Slots (receiving external updates)**:
- `update_progress(percent: int)` — updates transcription progress
- `show_result(text: str, srt_path: Path)` — populates transcript text and enables export buttons
- `set_status(msg: str)` — updates the status label

---

### 6.7 `ui/settings_page.py` — Settings Page

**Responsibility**: Provides a configuration form for the Whisper model, language, output directory, auto-transcription toggle, and cookies path; saves to local `config.json`.

---

### 6.8 `downloader.py` — Download Core

**Responsibility**: Wraps yt-dlp calls; provides four functions: metadata extraction, video download, cover download, and audio extraction. (Same design as v1.0, with an additional `progress_callback` parameter for `DownloadThread` to emit signals.)

#### `get_metadata(url, cookies=None) -> dict`

```python
{
    "id": "BV1xx411c7mD",
    "title": "Video title",
    "description": "Video description text",
    "thumbnail": "https://i0.hdslb.com/bfs/archive/xxx.jpg",
    "webpage_url": "https://www.bilibili.com/video/BV1xx411c7mD",
    "duration": 372,
    "uploader": "Uploader nickname",
}
```

#### `download_video(meta, output_dir, progress_cb) -> Path`

yt-dlp parameters are the same as v1.0. The `progress_hooks` callback calls `progress_cb(percent, speed)` to push progress to the UI.

#### `download_cover(meta, output_dir) -> Path`

Downloads from `meta["thumbnail"]` and saves to the `covers/` directory.

#### `extract_audio(video_path, output_dir) -> Path`

```bash
ffmpeg -i input.mp4 -ar 16000 -ac 1 -c:a pcm_s16le output.wav
```

---

### 6.9 `transcribe.py` — Speech Recognition

**Responsibility**: Loads the local Whisper model, transcribes audio, and outputs SRT and TXT.

**Whisper progress callback implementation**:

`whisper.model.transcribe()` does not natively provide incremental progress callbacks. The following approach is used for percentage estimation:

1. Use ffmpeg to probe the total audio duration (in seconds) before transcription
2. Call `transcribe()` with `verbose=False` and collect `result["segments"]`
3. Since Whisper is a synchronous blocking call, progress cannot be pushed in real time during transcription
4. **Solution**: Split the audio into fixed-length chunks (30s), call `transcribe()` on each chunk, and emit a progress update after each chunk

```python
import subprocess, json
from pathlib import Path
from model_manager import load_model

def get_audio_duration(audio_path: Path) -> float:
    """Get audio duration in seconds using ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", audio_path],
        capture_output=True, text=True
    )
    info = json.loads(result.stdout)
    return float(info["format"]["duration"])

def transcribe(audio_path: Path, model_name: str, language: str,
               progress_cb=None) -> tuple[Path, Path]:
    model = load_model(model_name)
    duration = get_audio_duration(audio_path)
    CHUNK = 30.0          # 30 seconds per chunk

    all_segments = []
    offset = 0.0

    while offset < duration:
        end = min(offset + CHUNK, duration)
        # clip_audio() uses ffmpeg to extract the [offset, end] segment to a temp file
        chunk_path = clip_audio(audio_path, offset, end)
        result = model.transcribe(str(chunk_path), language=language)

        # Correct timestamp offsets
        for seg in result["segments"]:
            seg["start"] += offset
            seg["end"]   += offset
        all_segments.extend(result["segments"])
        chunk_path.unlink()   # Delete the temporary chunk

        offset = end
        if progress_cb:
            progress_cb(int(offset / duration * 100))

    srt_path = write_srt(all_segments, audio_path.stem, audio_path.parent)
    txt_path = write_txt(
        " ".join(s["text"] for s in all_segments),
        audio_path.stem, audio_path.parent
    )
    if progress_cb:
        progress_cb(100)
    return srt_path, txt_path
```

> **Trade-off**: 30-second chunking adds ~5–10% extra inference overhead (model warm-up per chunk), but enables genuine incremental progress feedback — a much better user experience than the performance cost. For very short videos (< 30s), the behavior degrades to a single call and progress jumps directly from 0% to 100%.

---

### 6.10 `workers/download_thread.py` — Download Worker Thread

**Cover image display timing**: When `meta_ready` fires, only the cover URL is available — the local file does not yet exist. To display the cover image in the UI as quickly as possible, the thread **immediately fetches the thumbnail bytes from the URL via `requests`** after receiving the metadata, and sends them to `DownloadPanel` for rendering via a dedicated `thumbnail_ready` signal, in parallel with the main video download. `download_cover()` is still responsible for saving the full-size cover to the local `covers/` directory — the two operations do not block each other.

```python
class DownloadThread(QThread):
    meta_ready      = Signal(dict)      # Metadata ready (title, duration, description, etc.)
    thumbnail_ready = Signal(bytes)     # Raw cover image bytes for direct QPixmap rendering in UI
    progress        = Signal(int, str)  # (percent, speed_str)
    finished        = Signal(Path)      # Download complete; returns local video path
    error           = Signal(str)       # Emitted on failure at any step

    def run(self):
        try:
            # Step 1: Fetch metadata
            meta = get_metadata(self.url, self.cookies)
            self.meta_ready.emit(meta)

            # Step 2: Fetch cover thumbnail bytes for UI display (lightweight, usually < 100KB)
            thumb_resp = requests.get(meta["thumbnail"], timeout=10)
            if thumb_resp.ok:
                self.thumbnail_ready.emit(thumb_resp.content)

            # Step 3: Download the main video
            video_path = download_video(meta, self.output_dir, self._on_progress)

            # Step 4: Save cover to local covers/ directory (full size)
            download_cover(meta, self.output_dir)

            self.finished.emit(video_path)

        except Exception as e:
            self.error.emit(str(e))

    def _on_progress(self, percent: int, speed: str):
        self.progress.emit(percent, speed)
```

**Corresponding `DownloadPanel` slot**:

```python
# After thumbnail_ready signal fires, convert bytes to QPixmap and display
def on_thumbnail_ready(self, data: bytes):
    pixmap = QPixmap()
    pixmap.loadFromData(data)
    self.cover_label.setPixmap(
        pixmap.scaled(240, 135, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    )
```

---

### 6.11 `workers/transcribe_thread.py` — Transcription Worker Thread

```python
class TranscribeThread(QThread):
    progress     = Signal(int)          # Transcription progress percentage (estimated from audio duration)
    result_ready = Signal(str, Path)    # (full text, srt_path)
    error        = Signal(str)

    def run(self):
        audio_path = extract_audio(self.video_path, self.output_dir)
        srt_path, txt_path = transcribe(
            audio_path, self.model, self.language, self._on_progress
        )
        text = txt_path.read_text(encoding="utf-8")
        self.result_ready.emit(text, srt_path)
```

---

### 6.12 `config.py` — Configuration Management

**Responsibility**: Holds all default values and static constants, and provides read/write interfaces for `config.json`. `config.json` lives in the project root and stores runtime configuration changed by the user in the Settings page.

#### `config.json` full schema

```json
{
  "model":          "base",
  "language":       "zh",
  "output_dir":     "C:/Users/<username>/Downloads",
  "auto_transcribe": true,
  "cookies":        ""
}
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `model` | str | `"base"` | Whisper model name; must match a key in `MODEL_INFO` |
| `language` | str | `"zh"` | Whisper recognition language |
| `output_dir` | str | `str(Path.home()/"Downloads")` | Absolute path to output root directory (stored as string in JSON) |
| `auto_transcribe` | bool | `true` | Whether to trigger transcription automatically after download completes |
| `cookies` | str | `""` | Absolute path to cookies file; empty string means unused |

#### Constants and read/write interface

```python
import json
from pathlib import Path

# ── Path constants ────────────────────────────────────
MODELS_DIR  = Path(__file__).parent / "Models"
CONFIG_FILE = Path(__file__).parent / "config.json"

# ── Default config (used on first run or for missing fields in config.json) ─
_DEFAULTS = {
    "model":           "base",
    "language":        "zh",
    "output_dir":      str(Path.home() / "Downloads"),
    "auto_transcribe": True,
    "cookies":         "",
}

# ── Static constants ──────────────────────────────────
WHISPER_MODELS = ["tiny", "base", "small", "medium", "large"]

MODEL_INFO = {
    "tiny":   {"size": "~75MB",  "vram": "~1GB",  "speed": "Very fast", "accuracy": "Low",
               "filename": "tiny.pt",    "url": "https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt"},
    "base":   {"size": "~150MB", "vram": "~1GB",  "speed": "Fast",      "accuracy": "Moderate",
               "filename": "base.pt",    "url": "https://openaipublic.azureedge.net/main/whisper/models/ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e/base.pt"},
    "small":  {"size": "~490MB", "vram": "~2GB",  "speed": "Medium",    "accuracy": "Good",
               "filename": "small.pt",   "url": "https://openaipublic.azureedge.net/main/whisper/models/9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794/small.pt"},
    "medium": {"size": "~1.5GB", "vram": "~5GB",  "speed": "Slow",      "accuracy": "High",
               "filename": "medium.pt",  "url": "https://openaipublic.azureedge.net/main/whisper/models/345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1/medium.pt"},
    "large":  {"size": "~3GB",   "vram": "~10GB", "speed": "Very slow", "accuracy": "Highest",
               "filename": "large-v3.pt","url": "https://openaipublic.azureedge.net/main/whisper/models/e5b1a55b89c1367dacf97e3e19bfd829a01529dbfdeefa8caeb59b3f1b81dadb/large-v3.pt"},
}

VIDEO_FORMAT = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"

# ── Read/write interface ──────────────────────────────
def load_config() -> dict:
    """Read config.json, filling missing fields with defaults. Returns all defaults if the file doesn't exist."""
    cfg = dict(_DEFAULTS)
    if CONFIG_FILE.exists():
        try:
            saved = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            cfg.update({k: saved[k] for k in _DEFAULTS if k in saved})
        except (json.JSONDecodeError, OSError):
            pass   # Silently fall back to defaults on corrupt file
    return cfg

def save_config(cfg: dict) -> None:
    """Write the config dict to config.json (only saves keys defined in the schema)."""
    to_save = {k: cfg[k] for k in _DEFAULTS if k in cfg}
    CONFIG_FILE.write_text(
        json.dumps(to_save, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
```

> **Calling convention**: All modules obtain runtime config via `load_config()`. Only `settings_page.py` calls `save_config()` when the user clicks "Save Settings". Config is never read at module level to avoid startup-ordering issues.

---

## 7. Data Flow

```
User inputs URL → clicks "Download"
  │
  ├─ [Step 1] DownloadThread.run()
  │     ├─ get_metadata()  →  meta dict
  │     │     └─ meta_ready.emit(meta)  →  DownloadPanel.show_video_info()
  │     │                                  (Immediately renders cover, title, description, link)
  │     │
  │     ├─ download_video()  →  output/videos/BVxxx_title.mp4
  │     │     └─ progress.emit(%, speed)  →  DownloadPanel.update_progress()
  │     │
  │     └─ download_cover()  →  output/covers/BVxxx_title.jpg
  │           └─ finished.emit(video_path)
  │                 │
  │                 ▼ (Only triggered on success; stops on failure)
  ├─ [Step 2] TranscribeThread.run()   ← Started automatically by on_download_finished
  │     │     TranscribePanel.set_status("Extracting audio…")
  │     │
  │     ├─ extract_audio()  →  output/transcripts/BVxxx_title.wav
  │     │
  │     ├─ transcribe()
  │     │     ├─ progress.emit(%)  →  TranscribePanel.update_progress()
  │     │     ├─  →  output/transcripts/BVxxx_title.srt
  │     │     └─  →  output/transcripts/BVxxx_title.txt
  │     │
  │     └─ result_ready.emit(text, srt_path)
  │           └─  TranscribePanel.show_result()
  │                 (Populates transcript text; enables copy/save buttons)
  │
  └─ [Done] Both panels show final state; user can export results
```

> **Key constraint**: `TranscribeThread` only starts after `DownloadThread.finished` is emitted. If the download fails (via the `error` signal), the transcription panel shows "Download failed — cannot transcribe" and the transcription thread is not started.

---

## 8. Directory Structure

### Project Source Directory

```
bilibili-dl/
├── main.py                     # App entry point (includes startup model check)
├── config.py                   # Global config and config.json read/write interface
├── downloader.py               # Download module (yt-dlp wrapper)
├── transcribe.py               # Speech recognition module (Whisper + chunked progress)
├── model_manager.py            # Model management (check / download / load)
├── utils.py                    # Utility functions (sanitize_filename / format_duration)
├── ui/
│   ├── __init__.py             # Empty file; makes ui/ a Python package
│   ├── main_window.py          # Main window (sidebar + content area)
│   ├── sidebar.py              # Searchable left navigation
│   ├── download_page.py        # Download page (dual-panel orchestration)
│   ├── download_panel.py       # Download panel (info display + progress)
│   ├── transcribe_panel.py     # Speech-to-text panel (result display)
│   ├── settings_page.py        # Settings page
│   └── model_download_dialog.py  # Model-missing prompt and download progress dialog
├── workers/
│   ├── __init__.py             # Empty file; makes workers/ a Python package
│   ├── download_thread.py      # Download worker thread (QThread)
│   ├── transcribe_thread.py    # Transcription worker thread (QThread)
│   └── model_download_thread.py  # Model download worker thread (QThread)
├── Models/                     # Whisper model file storage directory
│   ├── .gitkeep                # Keeps the directory tracked by git; model files are not committed
│   ├── tiny.pt                 # (Present after user downloads)
│   ├── base.pt
│   ├── small.pt
│   ├── medium.pt
│   └── large-v3.pt
├── assets/
│   └── icons/                  # Static assets such as menu icons
├── config.json                 # Runtime user config (auto-created by load_config on first run)
├── .gitignore
├── requirements.txt
└── README.md
```

### Runtime Output Directory

The default root is the system user's Downloads folder (`Path.home() / "Downloads"`), which maps to:

| Platform | Default path |
|----------|-------------|
| Windows | `C:\Users\<username>\Downloads` |
| macOS | `/Users/<username>/Downloads` |
| Linux | `/home/<username>/Downloads` |

```
~/Downloads/
├── videos/
│   └── BV1xx411c7mD_video_title.mp4
├── covers/
│   └── BV1xx411c7mD_video_title.jpg
└── transcripts/
    ├── BV1xx411c7mD_video_title.wav   # Intermediate file
    ├── BV1xx411c7mD_video_title.srt   # Timestamped subtitles
    └── BV1xx411c7mD_video_title.txt   # Plain-text transcript
```

Users can change the output root directory via the "Browse…" button in the Settings page; the setting is saved to `config.json` and loaded automatically on the next startup.

---

## 9. Output Specifications

### Transcript Panel Text Format

After transcription completes, the panel displays text in paragraphs of roughly 50–80 characters each, with a blank line between paragraphs. Supports scrolling and full-text copy.

### SRT Format

Follows the standard SRT format. Each subtitle line is at most 80 characters; paragraphs are separated by blank lines:

```
1
00:00:01,240 --> 00:00:04,560
Hello, welcome to this video.

2
00:00:04,800 --> 00:00:08,120
Today we'll cover…
```

---

## 10. Error Handling

| Error type | Trigger condition | Handling strategy |
|------------|------------------|-------------------|
| `URLError` | Invalid URL or parse failure | Download panel status bar shows a red message |
| `DownloadError` | Network interruption or video unavailable | Retry up to 3 times; on failure, Download panel shows error and Transcribe panel shows "Download failed — cannot transcribe" |
| `PermissionError` | Premium video with no cookies configured | Pop-up dialog guiding the user to configure cookies in Settings |
| `FFmpegNotFound` | ffmpeg not installed on the system | Pop-up dialog with installation instructions |
| `WhisperModelError` | Whisper model download failed | Transcribe panel shows error with a manual download path hint |
| `DiskFullError` | Insufficient disk space | Estimate required space before downloading; warn the user upfront if insufficient |
| `KeyboardInterrupt` | Window closed while tasks are running | Confirmation dialog; on confirm, terminate worker threads and clean up temporary files |

---

## 11. Dependencies & Environment

### Python Dependencies

```
# requirements.txt
PyQt6>=6.4.0
yt-dlp>=2024.1.0
openai-whisper>=20231117
requests>=2.28.0
```

### System Dependencies

```bash
# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt install ffmpeg

# Windows (recommended: winget)
winget install ffmpeg
```

### Installation Steps

```bash
# 1. Clone the project
git clone https://github.com/yourname/bilibili-dl
cd bilibili-dl

# 2. Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch the app
python main.py
```

---

## 12. Notes & Limitations

### Whisper Model Selection Guide

| Device | Recommended model | Estimated transcription time for a 12-min video |
|--------|------------------|------------------------------------------------|
| CPU only | `tiny` / `base` | 5–15 minutes |
| Entry-level GPU (4GB VRAM) | `small` | 2–4 minutes |
| Mid-range GPU (8GB VRAM) | `medium` | 1–2 minutes |
| High-end GPU (16GB+ VRAM) | `large` | < 1 minute |

### Bilibili Access Restrictions

- **Premium videos**: A cookies file path must be configured in Settings.
- **Download throttling**: Bilibili throttles unauthenticated users; configuring cookies is recommended.
- **Regional restrictions**: Some videos are mainland-China-only; overseas users need a proxy.

### Serial Task Behavior

Transcription is triggered automatically after download completes — no manual action is required. If the download fails, transcription will not start. To skip auto-transcription, disable the "Auto Transcribe" toggle in Settings.

### Temporary Files

The WAV audio file is retained by default after transcription completes. A future version may add an option to automatically delete temporary audio files after transcription.

### Copyright Notice

This tool is intended for personal study, research, and backup only. When downloading others' content, comply with Bilibili's user agreement and applicable laws. Do not use for commercial purposes or redistribution.

---

---

## 13. CLI Test Module

### 13.1 Goals

Validate two core capabilities via the command line without launching the GUI:

1. **Video info fetch**: Can the tool successfully parse metadata from a Bilibili URL (title, cover, description, direct links, etc.)?
2. **Speech-to-text**: Can the tool complete the full end-to-end pipeline — download → audio extraction → Whisper transcription?

Fixed test URL: `https://www.bilibili.com/video/BV1G29EBGE8b/`

---

### 13.2 Test Script: `test_cli.py`

**Location**: Project root `test_cli.py`

**Usage**:

```bash
# Test video info fetch only (fast; no download required)
python test_cli.py --test fetch

# Test speech-to-text only (slow; includes download + Whisper inference)
python test_cli.py --test transcribe

# Run all tests (sequential)
python test_cli.py --test all

# Use a custom URL (overrides default test URL)
python test_cli.py --test all --url "https://www.bilibili.com/video/BV1G29EBGE8b/"

# Specify Whisper model (default: tiny, for faster testing)
python test_cli.py --test transcribe --model tiny
```

---

### 13.3 Test Case Details

#### T-01 Video Info Fetch (`--test fetch`)

**Purpose**: Verify that yt-dlp can successfully parse Bilibili video metadata and extract direct links.

**Steps**:

1. Call `get_metadata(url)` to extract metadata
2. Print and validate that the following fields are non-empty:

| Field | Description | Pass condition |
|-------|-------------|---------------|
| `id` | Video BV number | Non-empty string |
| `title` | Video title | Non-empty string |
| `thumbnail` | Cover image URL | Starts with `http` |
| `webpage_url` | Video page link | Contains `bilibili.com` |
| `duration` | Video duration (seconds) | Positive integer |
| `uploader` | Uploader nickname | Non-empty string |
| `description` | Video description | Key exists (may be empty) |

3. Access the `thumbnail` URL to verify the cover image can be downloaded (HTTP 200)
4. Call yt-dlp `extract_info` with `listformats=True`, print all available formats, and confirm MP4 is present

**Expected terminal output**:

```
========================================
[T-01] Video Info Fetch Test
URL: https://www.bilibili.com/video/BV1G29EBGE8b/
========================================
[✓] id          : BV1G29EBGE8b
[✓] title       : <video title>
[✓] uploader    : <uploader>
[✓] duration    : <duration>s  (HH:MM:SS)
[✓] thumbnail   : https://i0.hdslb.com/...  (HTTP 200)
[✓] webpage_url : https://www.bilibili.com/video/BV1G29EBGE8b/
[✓] description : <first 100 chars>...
[✓] Available formats:
      id    ext   resolution  notes
      ----  ----  ----------  -----
      80    mp4   1080p       HD 1080P
      64    mp4   720p        HD 720P
      ...
----------------------------------------
[T-01] Result: PASSED ✓   Time: 2.3s
========================================
```

---

#### T-02 End-to-End Speech-to-Text (`--test transcribe`)

**Purpose**: Verify that the full pipeline — download → ffmpeg audio extraction → Whisper transcription — runs correctly.

**Steps**:

1. Create an isolated working directory in the system temp folder (`tempfile.mkdtemp()`); clean up automatically after the test
2. Call `get_metadata(url)` (reuses T-01)
3. Call `download_video(meta, tmp_dir)` and print progress
4. After download, call `extract_audio(video_path, tmp_dir)` to extract WAV
5. Call `transcribe(audio_path, model="tiny", language="zh")` to run Whisper
6. Print the first 200 characters of the transcript and the first 5 SRT entries
7. Verify that SRT and TXT files were created and are non-empty
8. Clean up the temp directory

**Expected terminal output**:

```
========================================
[T-02] End-to-End Speech-to-Text Test
URL    : https://www.bilibili.com/video/BV1G29EBGE8b/
Model  : tiny
Output : /tmp/bilibili_test_xxxx/  (auto-deleted after test)
========================================
[Step 1/4] Fetch metadata…           ✓ (1.8s)
[Step 2/4] Download video…
  Downloading: ████████████████████ 100%  12.3 MB/s
               ✓ Saved to /tmp/bilibili_test_xxxx/videos/BV1G29EBGE8b_xxx.mp4  (2m 14s)
[Step 3/4] Extract audio (ffmpeg)…   ✓ (4.2s)
[Step 4/4] Whisper transcription (tiny)…
  Transcribing: ████████░░░░░░░░░░░░  40%
                ✓ Transcription complete  (38.7s)
----------------------------------------
Transcript preview (first 200 chars):
Hello, welcome to this video. Today we'll cover…

SRT first 5 entries:
1
00:00:01,240 --> 00:00:04,560
Hello, welcome to this video.

2
00:00:04,800 --> 00:00:08,120
Today we'll cover…
...
----------------------------------------
[✓] TXT file: /tmp/.../transcripts/BV1G29EBGE8b_xxx.txt  (1,024 bytes)
[✓] SRT file: /tmp/.../transcripts/BV1G29EBGE8b_xxx.srt  (2,048 bytes)
[T-02] Result: PASSED ✓   Total time: 3m 01s
[Cleanup] Temp directory deleted
========================================
```

---

### 13.4 Test Script Structure

```python
# test_cli.py

import argparse
import sys
import time
import tempfile
import shutil
from pathlib import Path

TEST_URL = "https://www.bilibili.com/video/BV1G29EBGE8b/"

def test_fetch(url: str) -> bool:
    """T-01: Verify video metadata fetch and direct-link resolution."""
    from downloader import get_metadata
    ...

def test_transcribe(url: str, model: str) -> bool:
    """T-02: End-to-end download + audio extraction + Whisper transcription."""
    from downloader import get_metadata, download_video, extract_audio
    from transcribe import transcribe
    tmp_dir = Path(tempfile.mkdtemp(prefix="bilibili_test_"))
    try:
        ...
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        print(f"[Cleanup] Temp directory deleted")

def main():
    parser = argparse.ArgumentParser(description="bilibili-dl CLI test tool")
    parser.add_argument("--test", choices=["fetch", "transcribe", "all"],
                        default="all", help="Select test(s) to run")
    parser.add_argument("--url", default=TEST_URL, help="Bilibili video URL for testing")
    parser.add_argument("--model", default="tiny",
                        choices=["tiny", "base", "small", "medium", "large"],
                        help="Whisper model for transcription test (default: tiny for speed)")
    args = parser.parse_args()

    results = {}
    if args.test in ("fetch", "all"):
        results["T-01 Video Info Fetch"] = test_fetch(args.url)
    if args.test in ("transcribe", "all"):
        results["T-02 Speech-to-Text"]   = test_transcribe(args.url, args.model)

    # Summary output
    print("\n" + "=" * 40)
    print("Test Summary")
    print("=" * 40)
    for name, passed in results.items():
        status = "PASSED ✓" if passed else "FAILED ✗"
        print(f"  {name}: {status}")
    print("=" * 40)
    sys.exit(0 if all(results.values()) else 1)

if __name__ == "__main__":
    main()
```

---

### 13.5 Testing Notes

| Item | Notes |
|------|-------|
| Network | Requires access to Bilibili; overseas environments need a proxy |
| Disk space | T-02 downloads video and needs ~500MB of temp space; cleaned up automatically |
| Transcription speed | Defaults to `tiny` model for faster tests; use `--model base` for accuracy validation |
| Cookies | If the target video is premium content, append `--cookies <path>` (`test_cli.py` supports this too) |
| Exit code | Returns `0` if all tests pass, `1` on any failure — suitable for CI integration |

---

---

## 14. Model Management

### 14.1 Design Principles

- Whisper model files are stored in the `Models/` directory at the project root, not in Whisper's default cache path (`~/.cache/whisper`)
- **On every startup**, the app checks whether the currently configured model exists in `Models/`; if not, a prompt dialog is shown
- After the user confirms, the dialog shows real-time download progress; the dialog closes automatically on completion and the main window opens
- Model files are large (75MB–3GB) and are excluded from git (`.gitignore` excludes `Models/*.pt`)

---

### 14.2 Startup Detection Flow

```
App starts (main.py)
  │
  ├─ Read currently selected model from config.json (default: "base")
  │
  ├─ model_manager.is_model_ready(model_name)?
  │     Check whether Models/<filename>.pt exists and has size > 0
  │
  ├─ [Exists] → Start main window normally
  │
  └─ [Missing] → Show ModelDownloadDialog
                  │
                  ├─ User clicks "Download" → Start ModelDownloadThread
                  │                           Download complete → Close dialog → Start main window
                  │
                  └─ User clicks "Exit" → App exits
```

---

### 14.3 `model_manager.py` — Model Management Module

**Responsibility**: Provides three interfaces — model check, path resolution, and load — as the sole intermediary between `transcribe.py` and model files.

```python
from pathlib import Path
from config import MODELS_DIR, MODEL_INFO

def is_model_ready(model_name: str) -> bool:
    """Check whether the specified model file exists in Models/ and is complete (size > 0)."""
    model_path = get_model_path(model_name)
    return model_path.exists() and model_path.stat().st_size > 0

def get_model_path(model_name: str) -> Path:
    """Return the absolute path of the model file."""
    filename = MODEL_INFO[model_name]["filename"]
    return MODELS_DIR / filename

def load_model(model_name: str):
    """Load the model, forcing it to be read from Models/ instead of Whisper's default cache."""
    import whisper
    model_path = get_model_path(model_name)
    # whisper.load_model supports passing a file path directly
    return whisper.load_model(str(model_path))

def list_downloaded_models() -> list[str]:
    """Return a list of model names that have been downloaded to Models/."""
    downloaded = []
    for name, info in MODEL_INFO.items():
        if (MODELS_DIR / info["filename"]).exists():
            downloaded.append(name)
    return downloaded
```

---

### 14.4 `workers/model_download_thread.py` — Model Download Thread

```python
class ModelDownloadThread(QThread):
    progress = Signal(int, str)   # (percent, speed_str)  e.g. (42, "3.2 MB/s")
    finished = Signal()
    error    = Signal(str)

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.url      = MODEL_INFO[model_name]["url"]
        self.dest     = get_model_path(model_name)

    def run(self):
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        try:
            # Streaming download; report progress every 1MB
            response = requests.get(self.url, stream=True, timeout=30)
            response.raise_for_status()
            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            with open(self.dest, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    f.write(chunk)
                    downloaded += len(chunk)
                    percent = int(downloaded / total * 100) if total else 0
                    speed = ...   # Calculated from elapsed time
                    self.progress.emit(percent, speed)
            self.finished.emit()
        except Exception as e:
            self.dest.unlink(missing_ok=True)   # Clean up incomplete file
            self.error.emit(str(e))
```

---

### 14.5 `ui/model_download_dialog.py` — Model Download Dialog

**Trigger**: Shown by `main.py` before creating the main window when `is_model_ready()` returns `False`.

**UI sketch**:

```
┌─────────────────────────────────────────────┐
│  ⚠  Whisper Model Not Found                 │
│─────────────────────────────────────────────│
│  Configured model: base (~150MB)            │
│  Model directory: /path/to/bilibili-dl/Models/│
│                                             │
│  The speech-to-text feature requires a     │
│  local Whisper model to run.                │
│  Download now?                              │
│                                             │
│  [████████████░░░░░░░░]  60%  3.2 MB/s     │
│  Downloading base.pt…  90MB / 150MB         │
│                                             │
│            [Download]      [Exit App]       │
└─────────────────────────────────────────────┘
```

**State machine**:

| State | "Download" button | Progress bar | Notes |
|-------|------------------|--------------|-------|
| Initial | Enabled | Hidden | Waiting for user confirmation |
| Downloading | Disabled (grey) | Visible | Prevents duplicate clicks |
| Complete | — | — | Dialog auto-closes; main window starts |
| Failed | Changes to "Retry" | Shows error text | Allows re-download |

**Core logic**:

```python
class ModelDownloadDialog(QDialog):
    def __init__(self, model_name: str, parent=None):
        ...

    def on_download_clicked(self):
        self.btn_download.setEnabled(False)
        self.thread = ModelDownloadThread(self.model_name)
        self.thread.progress.connect(self.update_progress)
        self.thread.finished.connect(self.on_finished)
        self.thread.error.connect(self.on_error)
        self.thread.start()

    def on_finished(self):
        self.accept()   # Close dialog; main.py receives Accepted and starts the main window

    def on_error(self, msg: str):
        self.btn_download.setText("Retry")
        self.btn_download.setEnabled(True)
        self.label_status.setText(f"Download failed: {msg}")
```

---

### 14.6 `transcribe.py` Adjustment

The `transcribe()` function now loads the model via `model_manager.load_model()` instead of calling `whisper.load_model(model_name)` directly:

```python
# Before
model = whisper.load_model(model_name)

# After
from model_manager import load_model
model = load_model(model_name)   # Loads from Models/ directory
```

---

### 14.7 `.gitignore` Rules

```gitignore
# Whisper model files (too large to commit)
Models/*.pt
Models/*.bin

# Keep the directory itself
!Models/.gitkeep
```

---

*End of document — bilibili-dl v1.4 Design Document*
