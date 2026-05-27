import os
import sys
import importlib
from importlib import metadata

_MIN_PYWEBVIEW = (4, 4, 0)
_REQUIRED_MODULES = [
    ("webview", "pywebview"),
    ("yt_dlp", "yt-dlp"),
    ("whisper", "openai-whisper"),
    ("requests", "requests"),
]


def _show_startup_error(message: str):
    title = "启动失败"
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, message, title, 0x10)
            return
        except Exception:
            pass
    print(f"[错误] {message}", file=sys.stderr)


def _parse_version(version: str) -> tuple[int, int, int]:
    parts = []
    for raw in version.split("."):
        digits = "".join(ch for ch in raw if ch.isdigit())
        parts.append(int(digits) if digits else 0)
        if len(parts) == 3:
            break
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def _collect_missing_components() -> list[str]:
    missing = []
    for module_name, package_name in _REQUIRED_MODULES:
        try:
            importlib.import_module(module_name)
        except Exception as e:
            missing.append(f"{package_name}（导入失败: {e}）")

    try:
        ver_str = metadata.version("pywebview")
        if _parse_version(ver_str) < _MIN_PYWEBVIEW:
            need = ".".join(str(x) for x in _MIN_PYWEBVIEW)
            missing.append(f"pywebview>= {need}（当前版本: {ver_str}）")
    except metadata.PackageNotFoundError:
        missing.append("pywebview（未检测到已安装发行版）")
    except Exception as e:
        missing.append(f"pywebview（版本检测失败: {e}）")

    try:
        from utils import get_ffmpeg
        get_ffmpeg()
    except Exception as e:
        missing.append(f"ffmpeg / imageio-ffmpeg（{e}）")

    return missing


def _check_startup_components() -> bool:
    missing = _collect_missing_components()
    if not missing:
        return True

    message = (
        "检测到缺少或不满足要求的组件，程序将退出。\n\n"
        "请先安装/修复以下组件：\n"
        + "\n".join(f"- {item}" for item in missing)
        + "\n\n建议先执行:\n"
        "pip install -r requirements.txt"
    )
    _show_startup_error(message)
    return False


def main():
    if not _check_startup_components():
        sys.exit(1)

    import webview
    from api import API
    api = API()

    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "index.html")

    window = webview.create_window(
        title="bilibili-dl",
        url=html_path,
        js_api=api,
        width=1100,
        height=700,
        min_size=(960, 640),
        background_color="#020617",
    )
    api.attach_window(window)

    webview.start()


if __name__ == "__main__":
    main()
