#!/usr/bin/env python3
"""
🎞️ Agent 5: Video Aggregator & Extractor
Kỹ thuật viên hậu kỳ — Ghép video + audio, gửi qua Telegram.

Sử dụng FFmpeg để:
- Ghép video clips theo thứ tự
- Overlay audio lên video
- Thêm transitions
- Export MP4 1080p
- Gửi qua Telegram Bot API

Usage:
    python3 video_aggregator.py --audio audio.mp3 --clips-dir clips/    # Ghép + gửi TG
    python3 video_aggregator.py --clips-dir clips/ --dry-run            # Test FFmpeg
    python3 video_aggregator.py --send-only final.mp4                   # Chỉ gửi TG
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

MYSHORT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(MYSHORT_ROOT / "shared"))
from utils import (
    setup_logging, get_config, ensure_output_dirs, save_json, load_json,
    print_header, print_step, print_success, print_warning, print_error,
    safe_filename, get_output_dir
)

logger = setup_logging("VideoAggregator")

def find_clips(clips_dir):
    """Tìm tất cả video clips trong thư mục, sắp xếp theo tên."""
    clips_path = Path(clips_dir)
    if not clips_path.exists():
        return []
    
    extensions = {".mp4", ".webm", ".avi", ".mov", ".mkv"}
    clips = sorted([
        f for f in clips_path.iterdir()
        if f.is_file() and f.suffix.lower() in extensions
    ])
    return clips

def create_concat_file(clips, output_dir):
    """Tạo file concat list cho FFmpeg."""
    concat_file = Path(output_dir) / "concat-list.txt"
    with open(concat_file, "w", encoding="utf-8") as f:
        for clip in clips:
            # FFmpeg cần escape single quotes
            escaped = str(clip.absolute()).replace("'", "'\\''")
            f.write(f"file '{escaped}'\n")
    return str(concat_file)

def get_media_duration(file_path, ffmpeg_path="ffmpeg"):
    """Đo duration (giây) của file media bằng FFmpeg."""
    try:
        cmd = [ffmpeg_path, "-i", str(file_path), "-hide_banner", "-f", "null", "-"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})", result.stderr)
        if match:
            h, m, s, cs = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
            return h * 3600 + m * 60 + s + cs / 100.0
    except Exception as e:
        logger.warning(f"Cannot measure duration: {e}")
    return None

def normalize_clips(clips, output_dir, ffmpeg_path="ffmpeg", target_fps=30, target_res="1920:1080"):
    """
    Normalize tất cả clips về cùng codec/fps/resolution trước khi concat.
    Tránh lỗi FFmpeg khi concat clips khác format.
    """
    normalized = []
    norm_dir = Path(output_dir) / "normalized"
    norm_dir.mkdir(parents=True, exist_ok=True)

    for i, clip in enumerate(clips):
        out_path = norm_dir / f"norm-{i:03d}.mp4"
        cmd = [
            ffmpeg_path, "-y",
            "-i", str(clip),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-r", str(target_fps),
            "-vf", f"scale={target_res}:force_original_aspect_ratio=decrease,pad={target_res}:(ow-iw)/2:(oh-ih)/2:color=black",
            "-pix_fmt", "yuv420p",
            "-an",  # Remove any existing audio
            "-movflags", "+faststart",
            str(out_path)
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                normalized.append(out_path)
            else:
                logger.warning(f"Normalize failed for {clip}: {result.stderr[:200]}")
                normalized.append(clip)  # fallback to original
        except Exception as e:
            logger.warning(f"Normalize error: {e}")
            normalized.append(clip)

    return normalized

def merge_clips(clips, output_path, ffmpeg_path="ffmpeg"):
    """Ghép tất cả clips thành 1 video."""
    if not clips:
        print_error("Không có clips để ghép!")
        return False
    
    output_dir = Path(output_path).parent
    concat_file = create_concat_file(clips, output_dir)
    
    cmd = [
        ffmpeg_path,
        "-y",                           # Overwrite output
        "-f", "concat",
        "-safe", "0",
        "-i", concat_file,
        "-c:v", "libx264",             # H.264 encoding
        "-preset", "medium",
        "-crf", "23",                   # Quality (lower = better)
        "-pix_fmt", "yuv420p",          # Compatible pixel format
        "-movflags", "+faststart",      # Enable streaming
        output_path
    ]
    
    logger.info(f"FFmpeg concat: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300
        )
        if result.returncode != 0:
            print_error(f"FFmpeg concat failed: {result.stderr[:500]}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print_error("FFmpeg timeout (300s)!")
        return False
    except FileNotFoundError:
        print_error(f"FFmpeg không tìm thấy: {ffmpeg_path}. Cài: sudo apt install ffmpeg")
        return False

def overlay_audio(video_path, audio_path, output_path, ffmpeg_path="ffmpeg"):
    """
    Overlay audio lên video với xử lý mismatch thông minh:
    - Nếu video ngắn hơn audio: pad video bằng frame cuối
    - Nếu audio ngắn hơn video: fade out audio, giữ nguyên video
    - Nếu khớp: merge bình thường
    """
    video_dur = get_media_duration(video_path, ffmpeg_path)
    audio_dur = get_media_duration(audio_path, ffmpeg_path)

    if video_dur and audio_dur:
        diff = video_dur - audio_dur
        print(f"    📏 Video: {video_dur:.1f}s | Audio: {audio_dur:.1f}s | Diff: {diff:+.1f}s")

        if abs(diff) <= 2:
            # Close enough: use -shortest
            strategy = "shortest"
        elif diff < -2:
            # Video shorter: pad video with last frame
            strategy = "pad_video"
        else:
            # Audio shorter: fade out audio, keep full video
            strategy = "fade_audio"
    else:
        strategy = "shortest"

    if strategy == "pad_video" and video_dur and audio_dur:
        # Pad video to match audio duration
        print(f"    🔧 Strategy: pad video ({video_dur:.0f}s → {audio_dur:.0f}s)")
        cmd = [
            ffmpeg_path, "-y",
            "-i", video_path,
            "-i", audio_path,
            "-filter_complex",
            f"[0:v]tpad=stop_mode=clone:stop_duration={audio_dur - video_dur}[v]",
            "-map", "[v]", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            output_path
        ]
    elif strategy == "fade_audio" and audio_dur:
        # Fade out audio at the end, keep full video silent after audio ends
        fade_start = max(audio_dur - 3, 0)  # 3 second fade
        print(f"    🔧 Strategy: fade audio out at {fade_start:.0f}s")
        cmd = [
            ffmpeg_path, "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-af", f"afade=t=out:st={fade_start}:d=3",
            "-c:a", "aac", "-b:a", "192k",
            "-map", "0:v:0", "-map", "1:a:0",
            "-movflags", "+faststart",
            output_path
        ]
    else:
        # Standard merge with -shortest
        print(f"    🔧 Strategy: standard merge")
        cmd = [
            ffmpeg_path, "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-map", "0:v:0", "-map", "1:a:0",
            "-shortest",
            "-movflags", "+faststart",
            output_path
        ]

    logger.info(f"FFmpeg overlay: {' '.join(cmd[:10])}...")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            print_error(f"FFmpeg overlay failed: {result.stderr[:500]}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print_error("FFmpeg timeout (300s)!")
        return False
    except FileNotFoundError:
        print_error(f"FFmpeg không tìm thấy: {ffmpeg_path}")
        return False

def add_transitions(video_path, output_path, transition_type="fade", duration_sec=0.5, ffmpeg_path="ffmpeg"):
    """Thêm hiệu ứng fade in/out."""
    # Get video duration
    probe_cmd = [
        ffmpeg_path, "-i", video_path,
        "-hide_banner", "-f", "null", "-"
    ]
    
    try:
        probe = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=30)
        # Extract duration from stderr
        import re
        match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2})\.\d{2}", probe.stderr)
        if match:
            total_seconds = int(match.group(1)) * 3600 + int(match.group(2)) * 60 + int(match.group(3))
        else:
            total_seconds = 180  # Default 3 min
    except Exception:
        total_seconds = 180
    
    fade_out_start = max(total_seconds - duration_sec, 0)
    
    cmd = [
        ffmpeg_path,
        "-y",
        "-i", video_path,
        "-vf", f"fade=t=in:st=0:d={duration_sec},fade=t=out:st={fade_out_start}:d={duration_sec}",
        "-c:a", "copy",
        output_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return result.returncode == 0
    except Exception as e:
        print_warning(f"Transition failed (non-critical): {e}")
        return False

def send_telegram(video_path, title, description, config):
    """Gửi video qua Telegram Bot API."""
    token = config["telegram_token"]
    chat_id = config["telegram_chat_id"]
    
    if not token or not chat_id:
        print_error("TELEGRAM_TOKEN hoặc TELEGRAM_CHAT_ID chưa cấu hình!")
        return False
    
    try:
        import requests
    except ImportError:
        print_error("Cần cài requests: pip install requests")
        return False
    
    # Check file size (Telegram limit: 50MB for bot API)
    file_size = Path(video_path).stat().st_size
    file_size_mb = file_size / (1024 * 1024)
    
    if file_size_mb > 50:
        print_warning(f"File quá lớn ({file_size_mb:.1f}MB > 50MB limit). Gửi link thay vì file.")
        # Send text message with file path
        text_url = f"https://api.telegram.org/bot{token}/sendMessage"
        text_payload = {
            "chat_id": chat_id,
            "text": f"🎬 *{title}*\n\n{description}\n\n📁 File: `{video_path}`\n⚠️ File quá lớn để gửi qua Telegram.",
            "parse_mode": "Markdown"
        }
        response = requests.post(text_url, json=text_payload, timeout=15)
        return response.status_code == 200
    
    # Send video
    url = f"https://api.telegram.org/bot{token}/sendVideo"
    
    caption = f"🎬 *{title}*\n\n{description}"
    if len(caption) > 1024:
        caption = caption[:1021] + "..."
    
    with open(video_path, "rb") as f:
        files = {"video": f}
        data = {
            "chat_id": chat_id,
            "caption": caption,
            "parse_mode": "Markdown",
            "supports_streaming": True,
        }
        
        print(f"    📤 Uploading {file_size_mb:.1f}MB...")
        response = requests.post(url, files=files, data=data, timeout=120)
    
    if response.status_code == 200:
        return True
    else:
        print_error(f"Telegram API error: {response.status_code} — {response.text[:200]}")
        return False

def aggregate_video(clips_dir, audio_path=None, script=None,
                    send_telegram_flag=False, dry_run=False, config=None):
    """Quy trình chính: ghép video + audio → gửi Telegram."""
    print_header("Agent 5: Video Aggregator", "🎞️")
    
    if config is None:
        config = get_config()
    
    ffmpeg = config.get("ffmpeg_path", "ffmpeg")
    output_dir = ensure_output_dirs()
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    
    # Find clips
    clips = find_clips(clips_dir) if clips_dir else []
    print(f"  📹 Clips found: {len(clips)}")
    if audio_path:
        print(f"  🎵 Audio: {audio_path}")
    
    if not clips and not dry_run:
        print_error("Không tìm thấy clips!")
        return None
    
    title = "Kids Video"
    description = ""
    if script:
        title = script.get("title", title)
        seo = script.get("seo", {})
        description = seo.get("description", "")
        tags = " ".join(f"#{t}" for t in seo.get("tags", []))
        description += f"\n\n{tags}" if tags else ""
    
    result = {
        "title": title,
        "clips_count": len(clips),
        "steps": [],
    }
    
    if dry_run:
        print_warning("DRY-RUN MODE")
        print(f"\n  📋 Pipeline sẽ thực hiện:")
        print(f"    1. Ghép {len(clips) if clips else 'N'} clips → merged.mp4")
        if audio_path:
            print(f"    2. Overlay audio → with-audio.mp4")
        print(f"    3. Thêm fade in/out → final.mp4")
        if send_telegram_flag:
            print(f"    4. Gửi qua Telegram")
        
        result["status"] = "dry-run"
        result["final_video"] = None
        return result
    
    # Step 0.5: Normalize clips (same resolution/fps/codec)
    print_step(1, 5, f"Normalize {len(clips)} clips (cùng format/fps/resolution)...")
    clips = normalize_clips(clips, str(output_dir / "final"), ffmpeg)
    print_success(f"Normalized {len(clips)} clips")

    # Step 1: Merge clips
    merged_path = str(output_dir / "final" / f"merged-{timestamp}.mp4")
    print_step(2, 5, f"Ghép {len(clips)} clips...")
    
    if merge_clips(clips, merged_path, ffmpeg):
        print_success(f"Merged → {merged_path}")
        result["steps"].append({"step": "merge", "status": "ok", "file": merged_path})
        current_video = merged_path
    else:
        print_error("Merge failed!")
        result["status"] = "failed"
        return result
    
    # Step 2: Overlay audio
    if audio_path and Path(audio_path).exists():
        audio_video_path = str(output_dir / "final" / f"with-audio-{timestamp}.mp4")
        print_step(2, 4, "Overlay audio lên video...")
        
        if overlay_audio(current_video, audio_path, audio_video_path, ffmpeg):
            print_success(f"Audio overlay → {audio_video_path}")
            result["steps"].append({"step": "audio", "status": "ok", "file": audio_video_path})
            current_video = audio_video_path
        else:
            print_warning("Audio overlay failed — giữ video không nhạc")
    else:
        print_step(2, 4, "Bỏ qua audio overlay (không có file audio)")
    
    # Step 3: Add transitions
    final_path = str(output_dir / "final" / f"final-{timestamp}.mp4")
    print_step(3, 4, "Thêm fade in/out transitions...")
    
    if add_transitions(current_video, final_path, ffmpeg_path=ffmpeg):
        print_success(f"Transitions → {final_path}")
        result["steps"].append({"step": "transitions", "status": "ok", "file": final_path})
    else:
        print_warning("Transitions failed — sử dụng video không transition")
        final_path = current_video
    
    result["final_video"] = final_path
    
    # Step 4: Send Telegram
    if send_telegram_flag:
        print_step(4, 4, "Gửi video qua Telegram...")
        
        if send_telegram(final_path, title, description, config):
            print_success("Đã gửi qua Telegram!")
            result["steps"].append({"step": "telegram", "status": "ok"})
        else:
            print_error("Gửi Telegram thất bại!")
            result["steps"].append({"step": "telegram", "status": "failed"})
    
    result["status"] = "completed"
    
    # Get file size
    if Path(final_path).exists():
        size_mb = Path(final_path).stat().st_size / (1024 * 1024)
        result["file_size_mb"] = round(size_mb, 2)
    
    return result

def main():
    parser = argparse.ArgumentParser(
        description="🎞️ Agent 5: Video Aggregator — Ghép video + gửi Telegram"
    )
    parser.add_argument("--clips-dir", help="Thư mục chứa video clips")
    parser.add_argument("--audio", help="File audio MP3 từ Agent 3")
    parser.add_argument("--script", help="File kịch bản JSON (lấy metadata)")
    parser.add_argument("--send-telegram", action="store_true",
                       help="Gửi video qua Telegram")
    parser.add_argument("--send-only", help="Chỉ gửi file video có sẵn qua Telegram")
    parser.add_argument("--dry-run", action="store_true",
                       help="Test pipeline không thực hiện")
    parser.add_argument("--no-telegram", action="store_true",
                       help="Không gửi Telegram notification (dùng bởi orchestrator)")
    parser.add_argument("--output", help="Đường dẫn video output")
    parser.add_argument("--json", action="store_true",
                       help="In JSON ra stdout")
    args = parser.parse_args()
    
    config = get_config()
    
    # Send-only mode
    if args.send_only:
        print_header("Gửi Video qua Telegram", "📨")
        script = load_json(args.script) if args.script else {}
        title = script.get("title", "Kids Video")
        desc = script.get("seo", {}).get("description", "")
        
        if send_telegram(args.send_only, title, desc, config):
            print_success("Đã gửi!")
        else:
            print_error("Gửi thất bại!")
        return
    
    # Load script if available
    script = load_json(args.script) if args.script else None
    
    # Run aggregation
    result = aggregate_video(
        clips_dir=args.clips_dir,
        audio_path=args.audio,
        script=script,
        send_telegram_flag=args.send_telegram,
        dry_run=args.dry_run,
        config=config,
    )
    
    if result is None:
        print_error("Aggregation failed!")
        sys.exit(1)
    
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # Save result
        output_dir = ensure_output_dirs()
        result_path = output_dir / "final" / f"aggregation-result-{datetime.now().strftime('%Y%m%d')}.json"
        save_json(result, str(result_path))
        
        print(f"\n{'━' * 50}")
        print(f"📊 KẾT QUẢ AGGREGATION:")
        print(f"  🎬 Title: {result.get('title', 'N/A')}")
        if result.get("final_video"):
            print(f"  📁 Final video: {result['final_video']}")
        if result.get("file_size_mb"):
            print(f"  📦 Size: {result['file_size_mb']} MB")
        print(f"  📋 Status: {result.get('status', 'unknown')}")
        print(f"{'━' * 50}\n")

if __name__ == "__main__":
    main()
