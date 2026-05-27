"""
bilibili-dl CLI 测试工具
用法:
    python test_cli.py --test fetch
    python test_cli.py --test transcribe --model tiny
    python test_cli.py --test all
"""
import argparse
import shutil
import sys
import tempfile
import time
from pathlib import Path

# Windows 终端强制 UTF-8 输出
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

TEST_URL = "https://www.bilibili.com/video/BV1taPszGEuL?spm_id_from=333.1387.favlist.content.click"

SEP  = "=" * 50
SEP2 = "-" * 50


# ─────────────────────────────────────────────────────
#  T-01  视频信息获取
# ─────────────────────────────────────────────────────
def test_fetch(url: str) -> bool:
    from downloader import get_metadata
    import requests as req

    print(f"\n{SEP}")
    print("[T-01] 视频信息获取测试")
    print(f"URL: {url}")
    print(SEP)

    t0 = time.time()
    try:
        meta = get_metadata(url)
    except Exception as e:
        print(f"[✗] 获取元数据失败: {e}")
        return False

    elapsed = time.time() - t0
    required = ["id", "title", "thumbnail", "webpage_url", "duration", "uploader"]
    passed = True

    for key in required:
        val = meta.get(key, "")
        ok  = bool(val)
        mark = "✓" if ok else "✗"
        print(f"[{mark}] {key:<12}: {str(val)[:80]}")
        if not ok:
            passed = False

    # 封面图可访问性
    thumb = meta.get("thumbnail", "")
    if thumb:
        try:
            r = req.get(thumb, timeout=10)
            ok = r.ok
        except Exception:
            ok = False
        mark = "✓" if ok else "✗"
        print(f"[{mark}] thumbnail HTTP : {r.status_code if ok else '无法访问'}")
        if not ok:
            passed = False

    from utils import format_duration
    print(f"\n      时长: {format_duration(meta.get('duration', 0))}")
    print(f"      简介: {str(meta.get('description',''))[:100]}...")
    print(SEP2)
    print(f"[T-01] 结果: {'通过 ✓' if passed else '失败 ✗'}   耗时: {elapsed:.1f}s")
    print(SEP)
    return passed


# ─────────────────────────────────────────────────────
#  T-02  端到端语音转文字
# ─────────────────────────────────────────────────────
def test_transcribe(url: str, model_name: str) -> bool:
    from downloader import get_metadata, download_video, download_cover, extract_audio
    from transcribe import transcribe
    from model_manager import is_model_ready
    from utils import sanitize_filename

    print(f"\n{SEP}")
    print("[T-02] 语音转文字端到端测试")
    print(f"URL  : {url}")
    print(f"模型 : {model_name}")

    if not is_model_ready(model_name):
        print(f"[✗] 模型 '{model_name}' 不存在于 Models/ 目录，请先下载模型")
        return False

    tmp_dir = Path(tempfile.mkdtemp(prefix="bilibili_test_"))
    print(f"临时目录: {tmp_dir}  (测试后自动删除)")
    print(SEP)

    t_total = time.time()
    passed  = False

    try:
        # Step 1: 元数据
        print("[Step 1/4] 获取元数据...", end=" ", flush=True)
        t = time.time()
        meta = get_metadata(url)
        print(f"✓ ({time.time()-t:.1f}s)  {meta['title']}")

        # Step 2: 下载视频
        print("[Step 2/4] 下载视频...")
        t = time.time()

        def _progress(pct, speed):
            bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
            print(f"\r  [{bar}] {pct:3d}%  {speed}", end="", flush=True)

        video_path = download_video(meta, tmp_dir, progress_cb=_progress)
        print(f"\n  ✓ 保存至 {video_path}  ({time.time()-t:.1f}s)")
        expected_base = sanitize_filename(meta["title"]) or "未命名视频"
        video_name_ok = (
            video_path.stem == expected_base
            or video_path.stem.startswith(f"{expected_base}_")
        )
        print(f"[{'✓' if video_name_ok else '✗'}] 视频命名: {video_path.name}")
        if not video_name_ok:
            passed = False
        cover_path = download_cover(meta, tmp_dir, stem=video_path.stem)
        cover_name_ok = cover_path.stem == video_path.stem and cover_path.exists()
        print(f"[{'✓' if cover_name_ok else '✗'}] 封面命名: {cover_path.name}")
        if not cover_name_ok:
            passed = False

        # Step 3: 提取音频
        print("[Step 3/4] 提取音频 (ffmpeg)...", end=" ", flush=True)
        t = time.time()
        audio_path = extract_audio(video_path, tmp_dir)
        print(f"✓ ({time.time()-t:.1f}s)")

        # Step 4: 转录
        print("[Step 4/4] Whisper 转录...")
        t = time.time()

        def _trans_progress(pct):
            bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
            print(f"\r  [{bar}] {pct:3d}%", end="", flush=True)

        srt_path, txt_path = transcribe(
            audio_path, model_name=model_name, language="zh",
            progress_cb=_trans_progress,
        )
        print(f"\n  ✓ 转录完成 ({time.time()-t:.1f}s)")

        # 结果展示
        print(SEP2)
        text = txt_path.read_text(encoding="utf-8")
        print(f"转录预览（前200字）:\n{text[:200]}")
        print()
        srt_lines = srt_path.read_text(encoding="utf-8").splitlines()
        preview   = "\n".join(srt_lines[:20])
        print(f"SRT 前5条:\n{preview}")
        print(SEP2)

        txt_ok = txt_path.exists() and txt_path.stat().st_size > 0
        srt_ok = srt_path.exists() and srt_path.stat().st_size > 0
        print(f"[{'✓' if txt_ok else '✗'}] TXT: {txt_path}  ({txt_path.stat().st_size} 字节)")
        print(f"[{'✓' if srt_ok else '✗'}] SRT: {srt_path}  ({srt_path.stat().st_size} 字节)")

        passed = txt_ok and srt_ok

    except Exception as e:
        import traceback
        print(f"\n[✗] 异常: {e}")
        traceback.print_exc()
        passed = False

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        print("[清理] 临时目录已删除")

    total = time.time() - t_total
    m, s = divmod(int(total), 60)
    print(f"[T-02] 结果: {'通过 ✓' if passed else '失败 ✗'}   总耗时: {m}m {s}s")
    print(SEP)
    return passed


# ─────────────────────────────────────────────────────
#  入口
# ─────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="bilibili-dl CLI 测试工具")
    parser.add_argument("--test",  choices=["fetch", "transcribe", "all"],
                        default="all")
    parser.add_argument("--url",   default=TEST_URL)
    parser.add_argument("--model", default="tiny",
                        choices=["tiny", "base", "small", "medium", "large"])
    args = parser.parse_args()

    results = {}
    if args.test in ("fetch", "all"):
        results["T-01 视频信息获取"] = test_fetch(args.url)
    if args.test in ("transcribe", "all"):
        results["T-02 语音转文字"] = test_transcribe(args.url, args.model)

    print(f"\n{SEP}")
    print("测试汇总")
    print(SEP)
    for name, ok in results.items():
        print(f"  {name}: {'通过 ✓' if ok else '失败 ✗'}")
    print(SEP)
    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()
