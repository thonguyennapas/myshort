#!/usr/bin/env python3
"""
🎬 Agent 4: Video Maker
Đạo diễn hình ảnh — Tạo video clips qua Google Veo (Vertex AI).

Tạo prompts hình ảnh cho từng phân cảnh, gọi Veo API generate clips.

Usage:
    python3 video_maker.py --script script.json                        # Từ kịch bản
    python3 video_maker.py --script script.json --music audio.mp3      # Với nhạc
    python3 video_maker.py --dry-run                                   # Chỉ in prompts
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

MYSHORT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(MYSHORT_ROOT / "shared"))
from utils import (
    setup_logging, get_config, ensure_output_dirs, save_json, load_json,
    print_header, print_step, print_success, print_warning, print_error,
    safe_filename, get_output_dir, send_telegram
)

logger = setup_logging("VideoMaker")

# ── Constants ──
VEO_MAX_CLIP_SECONDS = 8  # Google Veo max per generation

RESOLUTION_MAP = {
    "720p": {"width": 1280, "height": 720},
    "1080p": {"width": 1920, "height": 1080},
    "4k": {"width": 3840, "height": 2160},
}

# ── Minimal sample (avoid importing from content-creator) ──
MINI_SAMPLE_SCRIPT = {
    "title": "Counting Stars with Teddy Bear",
    "duration_minutes": 1,
    "scenes": [
        {
            "id": 1, "timestamp": "0:00-0:08", "lyrics_section": "intro",
            "description": "Cute teddy bear waving hello in colorful bedroom.",
            "characters": ["Teddy Bear"], "action": "waves at camera",
            "background": "Colorful kids bedroom", "colors": "warm yellow, pink",
            "camera_movement": "slow zoom in", "mood": "gentle"
        },
        {
            "id": 2, "timestamp": "0:08-0:16", "lyrics_section": "chorus",
            "description": "Teddy flies through night sky counting golden stars.",
            "characters": ["Teddy Bear", "Golden Stars"], "action": "counts stars",
            "background": "Blue night sky", "colors": "deep blue, golden",
            "camera_movement": "pan right", "mood": "magical"
        },
    ],
    "music_direction": {"genre": "kids pop", "bpm": 120, "mood": "happy"},
}


def split_scene_to_subclips(scene):
    """
    Chia 1 scene dài thành nhiều sub-clips ≤ VEO_MAX_CLIP_SECONDS.
    VD: scene 20s → 3 sub-clips: 8s + 8s + 4s (min 4s)
    """
    timestamp = scene.get("timestamp", "0:00-0:08")
    total_duration = parse_duration(timestamp)
    start_time = parse_time(timestamp.split("-")[0].strip()) if "-" in timestamp else 0

    if total_duration <= VEO_MAX_CLIP_SECONDS:
        return [{
            **scene,
            "sub_id": 1,
            "sub_total": 1,
            "sub_duration": total_duration,
            "sub_start": start_time,
        }]

    subclips = []
    remaining = total_duration
    sub_idx = 0
    current_start = start_time

    while remaining > 0:
        sub_idx += 1
        # Ensure last clip is at least 4s (Veo minimum)
        if remaining <= VEO_MAX_CLIP_SECONDS:
            clip_dur = remaining
        elif remaining <= VEO_MAX_CLIP_SECONDS + 4:
            # Avoid creating a tiny leftover clip
            clip_dur = remaining // 2
        else:
            clip_dur = VEO_MAX_CLIP_SECONDS

        clip_dur = max(clip_dur, 4)  # Veo min ~4s
        subclips.append({
            **scene,
            "sub_id": sub_idx,
            "sub_total": -1,  # filled after loop
            "sub_duration": clip_dur,
            "sub_start": current_start,
        })
        current_start += clip_dur
        remaining -= clip_dur

    # Fill sub_total
    for sc in subclips:
        sc["sub_total"] = len(subclips)

    return subclips

def build_veo_prompts(script):
    """Tạo Google Veo prompts từ kịch bản. Tự chia scenes dài thành sub-clips."""
    prompts = []
    scenes = script.get("scenes", [])

    base_style = (
        "3D animated cartoon, Pixar-quality rendering, bright vivid colors, "
        "smooth animation, child-friendly, no text overlay, no violence, "
        "safe for kids, YouTube Kids style"
    )

    negative = (
        "violence, blood, scary, dark, horror, weapon, "
        "realistic human faces, text, watermark, logo, "
        "blurry, low quality, distorted"
    )

    global_idx = 0
    for scene in scenes:
        subclips = split_scene_to_subclips(scene)

        for sub in subclips:
            global_idx += 1
            character_desc = ", ".join(sub.get("characters", ["cute cartoon character"]))

            # Add continuity hints for sub-clips
            continuity = ""
            if sub["sub_total"] > 1:
                if sub["sub_id"] == 1:
                    continuity = "Beginning of scene, establish setting. "
                elif sub["sub_id"] == sub["sub_total"]:
                    continuity = "End of scene, conclude action. "
                else:
                    continuity = "Continuing same scene, maintain consistency. "

            prompt = (
                f"{base_style}. {continuity}"
                f"Scene: {sub.get('description', '')}. "
                f"Characters: {character_desc}. "
                f"Action: {sub.get('action', 'gentle movement')}. "
                f"Background: {sub.get('background', 'colorful fantasy setting')}. "
                f"Color palette: {sub.get('colors', 'bright rainbow colors')}. "
                f"Camera: {sub.get('camera_movement', 'static wide shot')}. "
                f"Mood: {sub.get('mood', 'happy and cheerful')}. "
                f"Lighting: bright, even, no harsh shadows."
            )

            prompts.append({
                "clip_idx": global_idx,
                "scene_id": sub["id"],
                "sub_id": sub["sub_id"],
                "sub_total": sub["sub_total"],
                "timestamp": sub.get("timestamp", ""),
                "duration_seconds": sub["sub_duration"],
                "lyrics_section": sub.get("lyrics_section", ""),
                "prompt": prompt,
                "negative_prompt": negative,
            })

    return prompts

def parse_duration(timestamp):
    """Parse duration (giây) từ timestamp string 'M:SS-M:SS'."""
    try:
        parts = timestamp.split("-")
        if len(parts) == 2:
            start = parse_time(parts[0].strip())
            end = parse_time(parts[1].strip())
            return max(end - start, 5)
    except Exception:
        pass
    return 10  # Default 10 seconds

def parse_time(time_str):
    """Parse 'M:SS' thành giây."""
    parts = time_str.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    return 0

def call_veo_api(prompt_data, config, output_path):
    """
    Gọi Google Veo API (Vertex AI) để tạo video clip.
    
    Hỗ trợ 2 cách xác thực:
    1. Service Account JSON (GOOGLE_APPLICATION_CREDENTIALS)
    2. API Key trực tiếp (GOOGLE_VEO_API_KEY)
    """
    project = config["google_project"]
    location = config["google_location"]
    api_key = config["google_veo_api_key"]
    credentials_path = config["google_credentials"]
    timeout = config["veo_timeout"]
    
    try:
        import requests
    except ImportError:
        print_error("Cần cài requests: pip install requests")
        return None
    
    prompt_text = prompt_data["prompt"]
    negative = prompt_data.get("negative_prompt", "")
    duration = prompt_data.get("duration_seconds", 10)
    
    # ── Option 1: API Key (Gemini API) ──
    if api_key:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"veo-2.0-generate-001:predictLongRunning?key={api_key}"
        )
        
        payload = {
            "instances": [{
                "prompt": prompt_text,
            }],
            "parameters": {
                "aspectRatio": "16:9",
                "durationSeconds": min(duration, VEO_MAX_CLIP_SECONDS),
            }
        }
        
        # Only add negativePrompt if present
        if negative:
            payload["parameters"]["negativePrompt"] = negative
        
        logger.info(f"Veo request: duration={min(duration, VEO_MAX_CLIP_SECONDS)}s")
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code != 200:
                print_error(f"Veo API error {response.status_code}: {response.text[:500]}")
                return None
            operation = response.json()
        except Exception as e:
            print_error(f"Veo request failed: {e}")
            return None
        
        # Poll for completion
        op_name = operation.get("name", "")
        if op_name:
            return poll_veo_operation(op_name, api_key, timeout, output_path)
        
        return operation
    
    # ── Option 2: Service Account (Vertex AI) ──
    elif credentials_path and project:
        try:
            from google.cloud import aiplatform
            from google.oauth2 import service_account
            
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path
            )
            
            aiplatform.init(
                project=project,
                location=location,
                credentials=credentials,
            )
            
            # Vertex AI video generation
            endpoint = f"projects/{project}/locations/{location}/publishers/google/models/veo-002"
            
            payload = {
                "instances": [{"prompt": prompt_text}],
                "parameters": {
                    "aspectRatio": "16:9",
                    "durationSeconds": min(duration, VEO_MAX_CLIP_SECONDS),
                    "negativePrompt": negative,
                }
            }
            
            response = requests.post(
                f"https://{location}-aiplatform.googleapis.com/v1/{endpoint}:predict",
                json=payload,
                headers={"Authorization": f"Bearer {credentials.token}"},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
            
        except ImportError:
            print_error("Cần cài google-cloud-aiplatform: pip install google-cloud-aiplatform")
            return None
    
    else:
        print_error("Cần GOOGLE_VEO_API_KEY hoặc GOOGLE_APPLICATION_CREDENTIALS + GOOGLE_CLOUD_PROJECT")
        return None

def poll_veo_operation(op_name, api_key, timeout, output_path):
    """Poll Veo operation cho đến khi hoàn tất."""
    import requests
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        time.sleep(15)
        
        url = f"https://generativelanguage.googleapis.com/v1beta/{op_name}?key={api_key}"
        response = requests.get(url, timeout=15)
        data = response.json()
        
        elapsed = int(time.time() - start_time)
        done = data.get("done", False)
        print(f"    ⏳ [{elapsed}s] Done: {done}")
        
        if done:
            result = data.get("response", {})
            videos = result.get("generatedSamples", [])
            if videos:
                video_uri = videos[0].get("video", {}).get("uri", "")
                if video_uri:
                    # Download video
                    download_response = requests.get(video_uri, timeout=120, stream=True)
                    with open(output_path, "wb") as f:
                        for chunk in download_response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    return {"video_file": str(output_path), "uri": video_uri}
            
            return result
    
    print_error(f"Veo timeout sau {timeout}s!")
    return None

def get_audio_duration(audio_path, ffmpeg_path="ffmpeg"):
    """Đo duration thật sự của file audio bằng FFprobe/FFmpeg."""
    try:
        cmd = [ffmpeg_path, "-i", str(audio_path), "-hide_banner", "-f", "null", "-"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        import re
        match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})", result.stderr)
        if match:
            h, m, s, cs = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
            return h * 3600 + m * 60 + s + cs / 100.0
    except Exception as e:
        logger.warning(f"Cannot measure audio duration: {e}")
    return None

def create_video_clips(script, music_path=None, resolution="1080p", dry_run=False, config=None):
    """Quy trình chính: tạo video clips. Tự chia scenes dài thành sub-clips ≤ 8s."""
    print_header("Agent 4: Video Maker", "🎬")

    if config is None:
        config = get_config()

    scenes = script.get("scenes", [])
    total_scenes = len(scenes)

    print(f"  🎬 Title: {script.get('title', 'N/A')}")
    print(f"  📹 Resolution: {resolution}")
    print(f"  🎞️  Scenes: {total_scenes}")

    # Measure real audio duration if available
    audio_duration = None
    if music_path and Path(music_path).exists():
        ffmpeg = config.get("ffmpeg_path", "ffmpeg")
        audio_duration = get_audio_duration(music_path, ffmpeg)
        print(f"  🎵 Music: {music_path} ({audio_duration:.1f}s)" if audio_duration else f"  🎵 Music: {music_path}")
    print()

    # Build prompts (auto-splits long scenes)
    print_step(1, 2, "Tạo Veo prompts (tự chia sub-clips ≤ 8s)...")
    veo_prompts = build_veo_prompts(script)
    total_clips = len(veo_prompts)
    total_video_duration = sum(p["duration_seconds"] for p in veo_prompts)

    print(f"  📊 {total_scenes} scenes → {total_clips} clips ({total_video_duration}s tổng)")
    if audio_duration:
        diff = abs(total_video_duration - audio_duration)
        if diff > 5:
            print_warning(f"⚠️  Video ({total_video_duration}s) vs Audio ({audio_duration:.0f}s) lệch {diff:.0f}s — sẽ xử lý ở bước ghép")
        else:
            print_success(f"Video/Audio sync OK (lệch {diff:.1f}s)")

    output_dir = ensure_output_dirs()
    clips_dir = output_dir / "clips" / datetime.now().strftime("%Y%m%d-%H%M%S")
    clips_dir.mkdir(parents=True, exist_ok=True)

    results = []

    for i, prompt_data in enumerate(veo_prompts):
        scene_id = prompt_data["scene_id"]
        sub_label = f"" if prompt_data["sub_total"] == 1 else f" (part {prompt_data['sub_id']}/{prompt_data['sub_total']})"
        print_step(i + 1, total_clips,
                  f"Scene {scene_id}{sub_label} [{prompt_data['duration_seconds']}s]")

        clip_filename = f"clip-{prompt_data['clip_idx']:03d}_scene-{scene_id}_sub-{prompt_data['sub_id']}.mp4"
        clip_path = clips_dir / clip_filename

        if dry_run:
            print_warning(f"    DRY-RUN — skip Veo API")
            results.append({
                "clip_idx": prompt_data["clip_idx"],
                "scene_id": scene_id,
                "sub_id": prompt_data["sub_id"],
                "status": "dry-run",
                "duration": prompt_data["duration_seconds"],
                "clip_path": str(clip_path),
            })
            continue

        veo_result = call_veo_api(prompt_data, config, str(clip_path))

        if veo_result:
            print_success(f"    Clip {prompt_data['clip_idx']} done!")
            results.append({
                "clip_idx": prompt_data["clip_idx"],
                "scene_id": scene_id,
                "sub_id": prompt_data["sub_id"],
                "status": "completed",
                "duration": prompt_data["duration_seconds"],
                "clip_path": str(clip_path),
            })
        else:
            print_error(f"    Clip {prompt_data['clip_idx']} FAILED!")
            results.append({
                "clip_idx": prompt_data["clip_idx"],
                "scene_id": scene_id,
                "status": "failed",
                "clip_path": None,
            })

    return {
        "clips_dir": str(clips_dir),
        "total_scenes": total_scenes,
        "total_clips": total_clips,
        "total_video_duration": total_video_duration,
        "audio_duration": audio_duration,
        "completed": sum(1 for r in results if r["status"] in ("completed", "dry-run")),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "clips": results,
    }

def main():
    parser = argparse.ArgumentParser(
        description="🎬 Agent 4: Video Maker — Tạo video clips qua Google Veo"
    )
    parser.add_argument("--script", help="File kịch bản JSON từ Agent 2")
    parser.add_argument("--music", help="File nhạc MP3 từ Agent 3 (để tính timing)")
    parser.add_argument("--resolution", default="1080p",
                       choices=["720p", "1080p", "4k"],
                       help="Độ phân giải (mặc định: 1080p)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Chỉ in Veo prompts, không gọi API")
    parser.add_argument("--no-telegram", action="store_true",
                       help="Không gửi Telegram notification")
    parser.add_argument("--output-dir", help="Thư mục lưu clips")
    parser.add_argument("--json", action="store_true",
                       help="In JSON ra stdout")
    args = parser.parse_args()
    
    # Load script
    if args.script:
        script = load_json(args.script)
    else:
        print_warning("Không có file script → dùng kịch bản mẫu (dry-run)")
        script = MINI_SAMPLE_SCRIPT
        args.dry_run = True
    
    # Create video clips
    result = create_video_clips(
        script=script,
        music_path=args.music,
        resolution=args.resolution,
        dry_run=args.dry_run,
    )
    
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # Save result
        output_dir = ensure_output_dirs()
        result_path = output_dir / "clips" / f"video-result-{datetime.now().strftime('%Y%m%d')}.json"
        save_json(result, str(result_path))
        
        print(f"\n{'━' * 50}")
        print(f"📊 KẾT QUẢ VIDEO MAKER:")
        print(f"  📂 Clips dir: {result['clips_dir']}")
        print(f"  ✅ Completed: {result['completed']}/{result['total_scenes']}")
        if result['failed'] > 0:
            print(f"  ❌ Failed: {result['failed']}")
        print(f"  📁 Result: {result_path}")
        print(f"{'━' * 50}\n")
    
    # ── Telegram Notification (chỉ gửi khi chạy standalone) ──
    if args.no_telegram or args.json:
        return
    
    msg_lines = ["🎬 *Agent 4: Video Maker*", ""]
    msg_lines.append(f"📊 *Kết quả: {result['completed']}/{result['total_clips']} clips*")
    
    if result['failed'] > 0:
        msg_lines.append(f"❌ Failed: {result['failed']} clip(s)")
        msg_lines.append("💡 Dùng prompt bên dưới để tạo thủ công trên Veo/RunwayML")
    elif result['completed'] > 0:
        msg_lines.append("✅ Tất cả clips đã tạo thành công!")
    else:
        msg_lines.append("⚠️ Dry-run mode")
    
    # Build prompts from script for notification
    veo_prompts = build_veo_prompts(script)
    prompt_map = {p['clip_idx']: p['prompt'] for p in veo_prompts}
    
    msg_lines.append("\n🎬 *Scene Prompts:*")
    clips = result.get('clips', [])
    for clip in clips:
        clip_idx = clip.get('clip_idx', '?')
        scene_id = clip.get('scene_id', '?')
        sub_id = clip.get('sub_id', 1)
        status = clip.get('status', '?')
        duration = clip.get('duration', '?')
        prompt = prompt_map.get(clip_idx, '')
        
        status_icon = '✅' if status in ('completed', 'dry-run') else '❌'
        msg_lines.append(f"\n{status_icon} *Clip {clip_idx}* (Scene {scene_id}.{sub_id}, {duration}s)")
        if prompt:
            msg_lines.append(f"{prompt[:250]}")
    
    send_telegram("\n".join(msg_lines))
    print_success("Đã gửi scene prompts qua Telegram")

if __name__ == "__main__":
    main()
