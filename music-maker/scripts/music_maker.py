#!/usr/bin/env python3
"""
🎵 Agent 3: Music Maker
Kỹ sư âm thanh — Tạo nhạc qua Suno AI.

Nhận lyrics + music direction từ Agent 2, soạn prompt Suno tối ưu,
gọi API tạo bài hát, download file audio.

Usage:
    python3 music_maker.py --script script.json              # Từ kịch bản
    python3 music_maker.py --script script.json --dry-run    # Chỉ in Suno prompt
    python3 music_maker.py --custom-lyrics "lyrics.txt"      # Từ file lyrics
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
    safe_filename, get_output_dir, send_telegram
)

logger = setup_logging("MusicMaker")

# ── Minimal sample (avoid broken cross-skill import) ──
MINI_SAMPLE_SCRIPT = {
    "title": "Counting Stars",
    "duration_minutes": 1,
    "lyrics": {
        "intro": "Hello hello little friends!\nLet's count the stars tonight!",
        "chorus": "One, two, three!\nStars are shining, can you see?",
    },
    "music_direction": {
        "genre": "kids pop", "bpm": 120, "mood": "happy",
        "instruments": ["ukulele", "xylophone"],
        "vocal_style": "cheerful child-like voice",
    },
}

# ── Suno Style Mapping ──
STYLE_MAP = {
    "cocomelon": "cheerful kids pop, nursery rhyme, bright synth, xylophone, claps, childlike vocals",
    "disney": "orchestral kids song, magical, whimsical, gentle strings, piano, choir",
    "educational": "upbeat educational song, rhythmic, catchy, marimba, percussion, spoken word elements",
    "lullaby": "gentle lullaby, soft piano, music box, soothing, slow tempo, whispered vocals",
}

def build_suno_prompt(script):
    """Xây dựng prompt tối ưu cho Suno AI từ kịch bản."""
    music = script.get("music_direction", {})
    lyrics = script.get("lyrics", {})
    
    # Genre/Style
    genre = music.get("genre", "kids pop")
    instruments = ", ".join(music.get("instruments", ["ukulele", "xylophone"]))
    mood = music.get("mood", "happy, cheerful")
    vocal = music.get("vocal_style", "cheerful child-like voice")
    bpm = music.get("bpm", 120)
    key = music.get("key", "C major")
    
    # Style prompt
    style_prompt = (
        f"{genre}, {mood}, {instruments}, "
        f"{vocal}, {bpm} BPM, key of {key}, "
        f"children's music, YouTube Kids style, bright and colorful sound, "
        f"catchy melody, singalong, educational"
    )
    
    # Format lyrics with sections
    formatted_lyrics = ""
    section_order = ["intro", "verse1", "chorus", "verse2", "chorus_repeat", "bridge", "outro"]
    
    section_labels = {
        "intro": "[Intro]",
        "verse1": "[Verse 1]",
        "chorus": "[Chorus]",
        "verse2": "[Verse 2]",
        "chorus_repeat": "[Chorus]",
        "bridge": "[Bridge]",
        "outro": "[Outro]",
    }
    
    for section in section_order:
        if section in lyrics and lyrics[section]:
            label = section_labels.get(section, f"[{section.title()}]")
            formatted_lyrics += f"\n{label}\n{lyrics[section]}\n"
    
    return {
        "style_prompt": style_prompt,
        "lyrics": formatted_lyrics.strip(),
        "title": script.get("title", "Kids Song"),
        "duration_seconds": script.get("duration_minutes", 3) * 60,
    }

def call_suno_api(suno_prompt, config):
    """
    Gọi Suno AI API để tạo nhạc.
    Hỗ trợ: goapi.ai proxy / self-hosted / Suno official.
    """
    api_key = config["suno_api_key"]
    api_url = config["suno_api_url"].rstrip("/")
    timeout = config["suno_timeout"]
    
    if not api_key:
        print_error("SUNO_API_KEY chưa được cấu hình!")
        return None
    
    try:
        import requests
    except ImportError:
        print_error("Cần cài requests: pip install requests")
        return None
    
    # ── GoAPI.ai proxy ──
    if "goapi" in api_url.lower():
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        }
        
        payload = {
            "custom_mode": True,
            "input": {
                "gpt_description_prompt": suno_prompt["style_prompt"],
                "lyrics": suno_prompt["lyrics"],
                "title": suno_prompt["title"],
                "make_instrumental": False,
            }
        }
        
        generate_url = f"{api_url}/api/suno/v1/music"
        print_step(2, 4, f"Gửi request tới GoAPI.ai Suno ({generate_url})...")
        
        try:
            response = requests.post(generate_url, json=payload, headers=headers, timeout=30)
            logger.info(f"GoAPI response status: {response.status_code}")
            if response.status_code != 200:
                print_error(f"GoAPI error {response.status_code}: {response.text[:500]}")
                return None
            task_data = response.json()
        except Exception as e:
            print_error(f"GoAPI request failed: {e}")
            return None
        
        task_id = task_data.get("data", {}).get("task_id") or task_data.get("task_id")
        
        if not task_id:
            print_error(f"Không nhận được task_id: {json.dumps(task_data)[:500]}")
            return None
        
        # Poll for completion
        print_step(3, 4, f"Chờ Suno generate (timeout: {timeout}s)...")
        start_time = time.time()
        poll_url = f"{api_url}/api/suno/v1/music/{task_id}"
        
        while time.time() - start_time < timeout:
            time.sleep(10)
            try:
                status_resp = requests.get(poll_url, headers=headers, timeout=15)
                status_data = status_resp.json()
            except Exception as e:
                logger.warning(f"Poll error: {e}")
                continue
            
            status = status_data.get("data", {}).get("status", "")
            
            elapsed = int(time.time() - start_time)
            print(f"    ⏳ [{elapsed}s] Status: {status}")
            
            if status == "completed":
                songs = status_data.get("data", {}).get("output", [])
                if songs:
                    return {
                        "audio_url": songs[0].get("audio_url", ""),
                        "duration": songs[0].get("duration", 0),
                        "title": suno_prompt["title"],
                        "task_id": task_id,
                    }
            elif status in ("failed", "error"):
                print_error(f"Suno generation failed: {json.dumps(status_data)[:500]}")
                return None
        
        print_error(f"Timeout sau {timeout}s!")
        return None
    
    # ── Suno official API / self-hosted ──
    else:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "prompt": suno_prompt["style_prompt"],
            "lyrics": suno_prompt["lyrics"],
            "title": suno_prompt["title"],
            "custom_mode": True,
            "make_instrumental": False,
        }
        
        generate_url = f"{api_url}/api/generate/v2"
        print_step(2, 4, f"Gửi request tới Suno API ({generate_url})...")
        
        try:
            response = requests.post(generate_url, json=payload, headers=headers, timeout=30)
            logger.info(f"Suno response status: {response.status_code}")
            if response.status_code != 200:
                print_error(f"Suno error {response.status_code}: {response.text[:500]}")
                return None
            result = response.json()
        except Exception as e:
            print_error(f"Suno request failed: {e}")
            return None
        
        # Extract audio info
        clips = result.get("clips", result.get("data", []))
        if clips:
            clip = clips[0] if isinstance(clips, list) else clips
            return {
                "audio_url": clip.get("audio_url", ""),
                "duration": clip.get("duration", 0),
                "title": suno_prompt["title"],
                "clip_id": clip.get("id", ""),
            }
        
        return result

def download_audio(audio_url, output_path):
    """Download file audio từ URL."""
    try:
        import requests
        response = requests.get(audio_url, timeout=60, stream=True)
        response.raise_for_status()

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return True
    except Exception as e:
        print_error(f"Download failed: {e}")
        return False

def get_audio_duration(audio_path, ffmpeg_path="ffmpeg"):
    """Đo duration thật sự của file audio bằng FFmpeg."""
    try:
        cmd = [ffmpeg_path, "-i", str(audio_path), "-hide_banner", "-f", "null", "-"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})", result.stderr)
        if match:
            h, m, s, cs = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
            return h * 3600 + m * 60 + s + cs / 100.0
    except Exception as e:
        logger.warning(f"Cannot measure audio duration: {e}")
    return None

def create_music(script, dry_run=False, config=None):
    """Quy trình chính: tạo nhạc từ kịch bản."""
    print_header("Agent 3: Music Maker", "🎵")

    if config is None:
        config = get_config()

    # Build Suno prompt
    print_step(1, 4, "Soạn Suno AI prompt...")
    suno_prompt = build_suno_prompt(script)

    target_duration = suno_prompt['duration_seconds']
    print(f"\n  🎼 Title: {suno_prompt['title']}")
    print(f"  🎨 Style: {suno_prompt['style_prompt'][:100]}...")
    print(f"  ⏱️  Target: {target_duration}s")
    print(f"\n  📝 SUNO PROMPT:")
    print(f"  {'─' * 40}")
    print(f"  Style: {suno_prompt['style_prompt']}")
    print(f"  {'─' * 40}")
    lyrics_lines = suno_prompt['lyrics'].split('\n')[:10]
    for line in lyrics_lines:
        print(f"  {line}")
    if len(suno_prompt['lyrics'].split('\n')) > 10:
        print(f"  ... ({len(suno_prompt['lyrics'].split(chr(10)))} dòng)")
    print(f"  {'─' * 40}\n")

    if dry_run:
        print_warning("DRY-RUN MODE — Không gọi Suno API")
        return {
            "status": "dry-run",
            "suno_prompt": suno_prompt,
            "audio_file": None,
            "target_duration": target_duration,
            "actual_duration": None,
        }

    # Call Suno API
    result = call_suno_api(suno_prompt, config)

    if result is None:
        print_error("Không tạo được nhạc từ Suno!")
        return None

    # Download audio
    audio_url = result.get("audio_url", "")
    if audio_url:
        output_dir = ensure_output_dirs()
        audio_filename = safe_filename(suno_prompt["title"]) + ".mp3"
        audio_path = output_dir / "audio" / audio_filename

        print_step(4, 4, f"Download audio → {audio_path}")
        if download_audio(audio_url, str(audio_path)):
            print_success(f"Audio saved: {audio_path}")
            result["audio_file"] = str(audio_path)

            # Measure actual duration
            ffmpeg = config.get("ffmpeg_path", "ffmpeg")
            actual_dur = get_audio_duration(str(audio_path), ffmpeg)
            result["actual_duration"] = actual_dur
            result["target_duration"] = target_duration

            if actual_dur:
                diff = abs(actual_dur - target_duration)
                print(f"  📏 Actual duration: {actual_dur:.1f}s (target: {target_duration}s, diff: {diff:.1f}s)")
                if diff > 15:
                    print_warning(f"Duration lệch nhiều ({diff:.0f}s) — Agent 5 sẽ xử lý pad/trim khi ghép")
        else:
            result["audio_file"] = None
            result["actual_duration"] = None

    return result

def main():
    parser = argparse.ArgumentParser(
        description="🎵 Agent 3: Music Maker — Tạo nhạc qua Suno AI"
    )
    parser.add_argument("--script", required=False,
                       help="File kịch bản JSON từ Agent 2")
    parser.add_argument("--custom-lyrics", help="File lyrics text tùy chỉnh")
    parser.add_argument("--suno-style", help="Override Suno style prompt")
    parser.add_argument("--wait-timeout", type=int, default=300,
                       help="Timeout chờ Suno (giây, mặc định: 300)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Chỉ in prompt, không gọi API")
    parser.add_argument("--output", help="Đường dẫn output MP3")
    parser.add_argument("--json", action="store_true",
                       help="In JSON ra stdout")
    args = parser.parse_args()
    
    # Load script
    if args.script:
        script = load_json(args.script)
    elif args.custom_lyrics:
        # Build minimal script from custom lyrics
        with open(args.custom_lyrics, "r", encoding="utf-8") as f:
            lyrics_text = f.read()
        script = {
            "title": "Custom Kids Song",
            "duration_minutes": 3,
            "lyrics": {"verse1": lyrics_text},
            "music_direction": {
                "genre": args.suno_style or "cheerful kids pop",
                "bpm": 120,
                "mood": "happy, cheerful",
            }
        }
    else:
        # Use sample from content_creator
        print_warning("Không có file script → dùng kịch bản mẫu (dry-run)")
        script = MINI_SAMPLE_SCRIPT
        args.dry_run = True
    
    # Override timeout
    os.environ.setdefault("SUNO_TIMEOUT", str(args.wait_timeout))
    
    # Create music
    result = create_music(script, dry_run=args.dry_run)
    
    if result is None:
        print_error("Music creation failed!")
        # Still send Telegram with lyrics/prompt so user can create manually
        msg_lines = ["🎵 *Agent 3: Music Maker*", ""]
        msg_lines.append("❌ *Tạo nhạc thất bại* - Bạn có thể tạo thủ công:")
        
        # Extract lyrics from script
        lyrics = script.get('lyrics', {})
        if lyrics:
            msg_lines.append("\n🎤 *Lyrics:*")
            for section, text in lyrics.items():
                msg_lines.append(f"\n_{section}_:")
                msg_lines.append(str(text)[:300])
        
        # Music direction for manual creation
        music = script.get('music_direction', {})
        if music:
            msg_lines.append(f"\n🎵 *Hướng dẫn tạo nhạc:*")
            msg_lines.append(f"  Genre: {music.get('genre', 'N/A')}")
            msg_lines.append(f"  BPM: {music.get('bpm', 'N/A')}")
            msg_lines.append(f"  Mood: {music.get('mood', 'N/A')}")
            msg_lines.append(f"  Instruments: {music.get('instruments', 'N/A')}")
        
        msg_lines.append("\n💡 Dán lyrics vào Suno/Udio để tạo nhạc thủ công")
        send_telegram("\n".join(msg_lines))
        print_success("Đã gửi lyrics + prompt qua Telegram")
        sys.exit(1)
    
    if args.json:
        # Clean for JSON output
        output = {
            "status": result.get("status", "completed"),
            "audio_file": result.get("audio_file"),
            "title": result.get("title"),
            "suno_prompt": result.get("suno_prompt"),
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"\n{'━' * 50}")
        if result.get("audio_file"):
            print_success(f"Audio: {result['audio_file']}")
        elif result.get("status") == "dry-run":
            print_success("Dry-run hoàn tất — prompt đã sẵn sàng")
        print(f"{'━' * 50}\n")
    
    # ── Telegram Notification (success) ──
    msg_lines = ["🎵 *Agent 3: Music Maker*", ""]
    
    if result.get("audio_file"):
        msg_lines.append(f"✅ *Nhạc đã tạo thành công!*")
        msg_lines.append(f"🎧 File: `{result['audio_file']}`")
        if result.get('actual_duration'):
            msg_lines.append(f"⏱ Duration: {result['actual_duration']:.1f}s")
    else:
        msg_lines.append("⚠️ Dry-run mode - chưa tạo nhạc thật")
    
    # Always include lyrics + prompt
    suno_prompt = result.get('suno_prompt', {})
    if suno_prompt:
        msg_lines.append(f"\n🎤 *Suno Prompt:*")
        msg_lines.append(f"Title: {suno_prompt.get('title', 'N/A')}")
        msg_lines.append(f"Style: {suno_prompt.get('style_prompt', 'N/A')[:200]}")
        msg_lines.append(f"\n🎶 *Lyrics:*")
        msg_lines.append(suno_prompt.get('lyrics', 'N/A')[:500])
    
    send_telegram("\n".join(msg_lines))
    print_success("Đã gửi kết quả qua Telegram")

if __name__ == "__main__":
    main()

