#!/usr/bin/env python3
"""
✍️ Agent 2: Content Creator
Biên kịch nội dung sáng tạo cho video YouTube Kids.

Dựa trên xu hướng từ Agent 1, tạo:
- Lời bài hát (lyrics) bắt tai, lặp lại
- Mô tả phân cảnh (scene descriptions) cho AI tạo video
- Hướng dẫn nhạc (music direction) cho Suno AI

Usage:
    python3 content_creator.py --trend trend.json              # Từ file trend
    python3 content_creator.py --topic "counting colors"       # Từ chủ đề
    python3 content_creator.py --dry-run                       # Test không gọi LLM
    python3 content_creator.py --review-prompts                # Xem prompts Agent 4
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

MYSHORT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(MYSHORT_ROOT / "shared"))
from utils import (
    setup_logging, get_config, ensure_output_dirs, save_json, load_json,
    check_content_safety, print_header, print_step, print_success,
    print_warning, print_error, safe_filename, get_output_dir,
    send_telegram
)

logger = setup_logging("ContentCreator")

# ── LLM Prompt Templates ──
SCRIPT_PROMPT = """Bạn là biên kịch chuyên nghiệp cho video YouTube Kids (trẻ em {age_range} tuổi).

NHIỆM VỤ: Tạo kịch bản video {duration} phút dựa trên chủ đề: "{topic}"

YÊU CẦU BẮT BUỘC:
1. Nội dung TUYỆT ĐỐI AN TOÀN cho trẻ em (COPPA compliant)
2. Lời bài hát bắt tai, lặp đi lặp lại, dễ nhớ
3. Màu sắc rực rỡ, nhân vật dễ thương
4. Nhịp điệu vui tươi, sôi động
5. Có yếu tố giáo dục (đếm số, màu sắc, chữ cái, v.v.)
6. ⚠️ QUAN TRỌNG: Mỗi scene TỐI ĐA 8 GIÂY (vì video AI chỉ tạo được max 8s/clip)
7. Video {duration} phút = {total_seconds} giây → cần CHÍNH XÁC {num_scenes} scenes (mỗi scene 5-8 giây)
8. Timestamps phải liên tục, không trùng, tổng = {total_seconds} giây

Trả lời CHÍNH XÁC theo format JSON sau (không thêm text ngoài JSON):

{{
    "title": "Tên video hấp dẫn bằng tiếng Anh",
    "title_vi": "Tên video tiếng Việt",
    "duration_minutes": {duration},
    "target_age": "{age_range}",
    "theme": "{topic}",
    "lyrics": {{
        "intro": "4-8 dòng mở đầu (friendly, inviting)",
        "verse1": "4-8 dòng verse 1 (giới thiệu chủ đề)",
        "chorus": "4-6 dòng chorus (bắt tai nhất, lặp lại được)",
        "verse2": "4-8 dòng verse 2 (phát triển chủ đề)",
        "chorus_repeat": "Lặp lại chorus",
        "bridge": "4 dòng bridge (chuyển tiếp thú vị)",
        "outro": "4 dòng kết thúc (vui vẻ, goodbye)"
    }},
    "scenes": [
        {{
            "id": 1,
            "timestamp": "0:00-0:08",
            "lyrics_section": "intro",
            "description": "Mô tả chi tiết cảnh (nhân vật, hành động, bối cảnh) — CHỈ 1 hành động đơn giản cho 8 giây",
            "characters": ["tên nhân vật dễ thương"],
            "action": "1 hành động cụ thể, đơn giản",
            "background": "mô tả nền",
            "colors": "bảng màu chủ đạo",
            "camera_movement": "zoom in/out/pan/static",
            "mood": "happy/exciting/calm"
        }}
    ],
    "music_direction": {{
        "genre": "Cocomelon-style kids pop / Synth-pop kids / etc.",
        "bpm": 120,
        "key": "C major",
        "mood": "happy, cheerful, energetic",
        "instruments": ["ukulele", "xylophone", "claps", "tambourine"],
        "vocal_style": "cheerful child-like voice, clear pronunciation",
        "reference_songs": ["Baby Shark", "Wheels on the Bus"]
    }},
    "seo": {{
        "tags": ["tag1", "tag2", "tag3"],
        "description": "Mô tả video cho YouTube (150 ký tự)"
    }}
}}
"""

# ── Dry-run Sample (max 8s per scene) ──
SAMPLE_SCRIPT = {
    "title": "Counting Stars with Teddy Bear",
    "title_vi": "Đếm Sao cùng Gấu Bông",
    "duration_minutes": 1,
    "target_age": "2-5",
    "theme": "counting",
    "lyrics": {
        "intro": "Hello hello little friends!\nCome and play with Teddy Bear!\nLet's count the stars tonight!\nOne by one, shining bright!",
        "verse1": "One little star up in the sky,\nTwinkling, twinkling way up high!\nTwo little stars say hello,\nWatch them sparkle, watch them glow!",
        "chorus": "Count with me! One, two, three!\nStars are shining, can you see?\nFour and five, up so high!\nCounting stars across the sky!",
        "outro": "Great job counting! You're a star!\nTeddy Bear says you've come far!\nGoodnight friends, sleep so tight,\nSee you next time! Bye bye! Night night!"
    },
    "scenes": [
        {
            "id": 1, "timestamp": "0:00-0:08", "lyrics_section": "intro",
            "description": "Cute 3D teddy bear waking up in a cozy colorful bedroom, yawning and stretching.",
            "characters": ["Teddy Bear (brown, fluffy, big eyes)"],
            "action": "Teddy stretches and yawns cutely",
            "background": "Colorful kids bedroom with star-patterned wallpaper",
            "colors": "warm yellow, soft blue, pink",
            "camera_movement": "slow zoom in to Teddy",
            "mood": "gentle, inviting"
        },
        {
            "id": 2, "timestamp": "0:08-0:16", "lyrics_section": "intro",
            "description": "Teddy waves hello at the camera, musical notes float around him.",
            "characters": ["Teddy Bear"],
            "action": "Waves at camera, smiles big",
            "background": "Colorful bedroom, window showing night sky",
            "colors": "warm yellow, pink, purple",
            "camera_movement": "static wide shot",
            "mood": "happy, welcoming"
        },
        {
            "id": 3, "timestamp": "0:16-0:24", "lyrics_section": "verse1",
            "description": "Teddy flies out the window into the night sky. One golden star appears twinkling.",
            "characters": ["Teddy Bear", "Star 1 (golden, smiling)"],
            "action": "Teddy floats up, points at the star",
            "background": "Deep blue night sky",
            "colors": "deep blue, golden, white sparkles",
            "camera_movement": "pan upward following Teddy",
            "mood": "magical, wonder"
        },
        {
            "id": 4, "timestamp": "0:24-0:32", "lyrics_section": "verse1",
            "description": "Second silver star appears. Teddy counts 'one, two!' with fingers.",
            "characters": ["Teddy Bear", "Star 1", "Star 2 (silver, winking)"],
            "action": "Teddy holds up two fingers, stars twinkle",
            "background": "Night sky with scattered clouds",
            "colors": "deep blue, golden, silver",
            "camera_movement": "slight zoom in on Teddy counting",
            "mood": "playful, educational"
        },
        {
            "id": 5, "timestamp": "0:32-0:40", "lyrics_section": "chorus",
            "description": "Stars 1-3 line up in a row. Big colorful numbers 1,2,3 appear bouncing.",
            "characters": ["Teddy Bear", "3 Stars"],
            "action": "Teddy dances and jumps, numbers bounce",
            "background": "Night sky with rainbow aurora",
            "colors": "rainbow spectrum, golden numbers",
            "camera_movement": "dynamic, slight zoom on numbers",
            "mood": "energetic, exciting"
        },
        {
            "id": 6, "timestamp": "0:40-0:48", "lyrics_section": "chorus",
            "description": "Numbers 4 and 5 appear with firework effects. All 5 stars celebrate.",
            "characters": ["Teddy Bear", "5 Stars"],
            "action": "Stars spin and dance in formation",
            "background": "Night sky filled with stardust",
            "colors": "full rainbow, gold sparkles",
            "camera_movement": "pull back to wide shot",
            "mood": "jubilant, peak energy"
        },
        {
            "id": 7, "timestamp": "0:48-0:56", "lyrics_section": "outro",
            "description": "Teddy back in bedroom, stars wave goodbye through the window.",
            "characters": ["Teddy Bear", "Stars peeking through window"],
            "action": "Teddy waves goodbye, blows a kiss",
            "background": "Cozy bedroom, warm lamp light",
            "colors": "warm amber, soft blue moonlight",
            "camera_movement": "slow zoom out",
            "mood": "warm, gentle"
        },
        {
            "id": 8, "timestamp": "0:56-1:00", "lyrics_section": "outro",
            "description": "Teddy tucks into bed, pulls blanket up. Moon smiles through window.",
            "characters": ["Teddy Bear"],
            "action": "Pulls blanket up, closes eyes, smiles",
            "background": "Dim bedroom with moonlight",
            "colors": "soft blue, cozy pink, warm amber",
            "camera_movement": "fade to stars",
            "mood": "sleepy, peaceful"
        }
    ],
    "music_direction": {
        "genre": "Cocomelon-style kids pop",
        "bpm": 115,
        "key": "C major",
        "mood": "happy, cheerful, gentle at ending",
        "instruments": ["ukulele", "glockenspiel", "soft drums", "claps", "wind chimes"],
        "vocal_style": "cheerful child-like voice, clear pronunciation, slight echo",
        "reference_songs": ["Twinkle Twinkle Little Star (modern remix)", "Baby Shark"]
    },
    "seo": {
        "tags": ["counting", "numbers", "stars", "teddy bear", "kids song", "nursery rhyme", "educational", "toddler"],
        "description": "Count to 5 with Teddy Bear! Fun educational counting song for toddlers with colorful stars and catchy music."
    }
}

def extract_json_from_text(text):
    """Trích xuất JSON từ LLM response (xử lý markdown fences, trailing commas)."""
    import re
    
    # Strip markdown code fences
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Remove ```json ... ``` or ``` ... ```
        cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned)
        cleaned = re.sub(r'\n?```\s*$', '', cleaned)
    
    # Remove trailing commas before } or ]
    cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    
    # Fallback: find first { ... } block
    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if match:
        try:
            block = match.group(0)
            block = re.sub(r',\s*([}\]])', r'\1', block)
            return json.loads(block)
        except json.JSONDecodeError:
            pass
    
    return None

def call_llm(prompt, config):
    """Gọi LLM API để tạo kịch bản."""
    provider = config["llm_provider"]
    api_key = config["llm_api_key"]
    model = config["llm_model"]
    
    if not api_key:
        print_error("LLM_API_KEY chưa được cấu hình! Dùng --dry-run để test.")
        return None
    
    try:
        import requests
    except ImportError:
        print_error("Cần cài requests: pip install requests")
        return None
    
    if provider == "gemini":
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.8,
                "maxOutputTokens": 16384,
                "responseMimeType": "application/json"
            }
        }
        
        response = requests.post(url, json=payload, timeout=1200)
        response.raise_for_status()
        data = response.json()
        
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        result = extract_json_from_text(text)
        if result is None:
            print_error(f"Không parse được JSON từ Gemini. Raw text (500 chars):\n{text[:500]}")
        return result
    
    elif provider == "openai":
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.8,
            "response_format": {"type": "json_object"}
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=1200)
        response.raise_for_status()
        data = response.json()
        
        text = data["choices"][0]["message"]["content"]
        result = extract_json_from_text(text)
        if result is None:
            print_error(f"Không parse được JSON từ OpenAI. Raw text (500 chars):\n{text[:500]}")
        return result
    
    else:
        print_error(f"LLM provider '{provider}' chưa được hỗ trợ. Dùng gemini hoặc openai.")
        return None

def create_script(topic, age_range="2-5", duration=3, style="cocomelon", dry_run=False, config=None):
    """Tạo kịch bản video."""
    print_header("Agent 2: Content Creator", "✍️")
    print(f"  🎯 Chủ đề: {topic}")
    print(f"  👶 Độ tuổi: {age_range}")
    print(f"  ⏱️  Thời lượng: {duration} phút")
    print(f"  🎨 Phong cách: {style}\n")
    
    if dry_run:
        print_warning("DRY-RUN MODE — Sử dụng kịch bản mẫu")
        script = SAMPLE_SCRIPT.copy()
        script["theme"] = topic
        script["target_age"] = age_range
        script["duration_minutes"] = duration
        return script
    
    if config is None:
        config = get_config()
    
    # Build prompt
    total_seconds = duration * 60
    num_scenes = total_seconds // 8  # ~22-23 scenes for 3 min
    
    prompt = SCRIPT_PROMPT.format(
        age_range=age_range,
        duration=duration,
        topic=topic,
        total_seconds=total_seconds,
        num_scenes=num_scenes,
    )
    
    print_step(1, 3, "Gọi LLM tạo kịch bản...")
    script = call_llm(prompt, config)
    
    if script is None:
        print_error("Không thể tạo kịch bản từ LLM")
        return None
    
    # Safety check
    print_step(2, 3, "Kiểm tra an toàn nội dung...")
    lyrics_text = " ".join(script.get("lyrics", {}).values())
    scenes_text = " ".join(s.get("description", "") for s in script.get("scenes", []))
    full_text = f"{lyrics_text} {scenes_text}"
    
    is_safe, violations = check_content_safety(full_text)
    if not is_safe:
        print_error(f"Nội dung KHÔNG AN TOÀN! Vi phạm: {violations}")
        print_warning("Đang yêu cầu LLM viết lại...")
        # Retry with stronger safety prompt
        prompt += "\n\n⚠️ LƯU Ý: Nội dung PHẢI tuyệt đối an toàn. KHÔNG ĐƯỢC chứa: " + ", ".join(violations)
        script = call_llm(prompt, config)
        if script is None:
            return None
    
    print_step(3, 3, "Hoàn thiện kịch bản...")
    print_success("Kịch bản đã tạo thành công!")
    
    return script

def generate_veo_prompts(script):
    """Tạo prompts cho Google Veo từ kịch bản (để Agent 2 review trước)."""
    veo_prompts = []
    
    for scene in script.get("scenes", []):
        prompt = (
            f"A 3D animated cartoon scene for children's YouTube video. "
            f"Style: bright, colorful, Pixar-quality, child-friendly. "
            f"Scene: {scene['description']} "
            f"Characters: {', '.join(scene.get('characters', ['cute cartoon character']))}. "
            f"Action: {scene.get('action', 'gentle movement')}. "
            f"Background: {scene.get('background', 'colorful setting')}. "
            f"Color palette: {scene.get('colors', 'bright, vibrant')}. "
            f"Camera: {scene.get('camera_movement', 'static')}. "
            f"Mood: {scene.get('mood', 'happy')}. "
            f"Resolution: 1080p, smooth animation, no text overlays."
        )
        veo_prompts.append({
            "scene_id": scene["id"],
            "timestamp": scene.get("timestamp", ""),
            "prompt": prompt,
        })
    
    return veo_prompts

def main():
    parser = argparse.ArgumentParser(
        description="✍️ Agent 2: Content Creator — Tạo kịch bản YouTube Kids"
    )
    parser.add_argument("--trend", help="File trend JSON từ Agent 1")
    parser.add_argument("--topic", help="Chủ đề trực tiếp (thay vì từ file trend)")
    parser.add_argument("--duration", type=int, default=3,
                       help="Thời lượng video (phút, mặc định: 3)")
    parser.add_argument("--age-range", default="2-5",
                       help="Độ tuổi mục tiêu (mặc định: 2-5)")
    parser.add_argument("--style", default="cocomelon",
                       choices=["cocomelon", "disney", "educational", "lullaby"],
                       help="Phong cách (mặc định: cocomelon)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Test không gọi LLM thật")
    parser.add_argument("--no-telegram", action="store_true",
                       help="Không gửi Telegram notification")
    parser.add_argument("--review-prompts", action="store_true",
                       help="Hiển thị Veo prompts để review")
    parser.add_argument("--output", help="Đường dẫn output")
    parser.add_argument("--json", action="store_true",
                       help="In JSON ra stdout")
    args = parser.parse_args()
    
    # Determine topic
    topic = args.topic
    if args.trend:
        trend_data = load_json(args.trend)
        rec = trend_data.get("recommended_topic", {})
        topic = topic or rec.get("name", "counting and colors for kids")
        logger.info(f"Lấy topic từ trend: {topic}")
    
    if not topic:
        topic = "counting and colors for kids"
        print_warning(f"Không có topic → dùng mặc định: {topic}")
    
    # Create script
    script = create_script(
        topic=topic,
        age_range=args.age_range,
        duration=args.duration,
        style=args.style,
        dry_run=args.dry_run,
    )
    
    if script is None:
        print_error("Không tạo được kịch bản!")
        # Gửi Telegram thông báo lỗi để user biết
        if not (hasattr(args, 'no_telegram') and args.no_telegram):
            fail_msg = [
                "✍️ *Agent 2: Content Creator*", "",
                "❌ *Tạo kịch bản THẤT BẠI!*",
                f"🎯 Chủ đề: {topic}",
                f"⏱ Thời lượng: {args.duration} phút",
                "",
                "💡 Có thể do LLM API lỗi/timeout.",
                "Thử lại: viết kịch bản counting",
            ]
            send_telegram("\n".join(fail_msg))
            print_success("Đã gửi thông báo lỗi qua Telegram")
        sys.exit(1)
    
    # Review Veo prompts
    if args.review_prompts:
        veo_prompts = generate_veo_prompts(script)
        print(f"\n{'━' * 50}")
        print("🎬 VEO PROMPTS (Review trước khi gửi Agent 4):")
        print(f"{'━' * 50}")
        for vp in veo_prompts:
            print(f"\n  Scene {vp['scene_id']} [{vp['timestamp']}]:")
            print(f"  {vp['prompt'][:200]}...")
        print()
    
    # Output
    if args.json:
        print(json.dumps(script, ensure_ascii=False, indent=2))
    else:
        # Save
        output_dir = ensure_output_dirs()
        output_path = args.output or str(
            output_dir / "scripts" / f"script-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        )
        save_json(script, output_path)
        
        # Summary
        print(f"\n{'━' * 50}")
        print(f"✅ Kịch bản đã tạo!")
        print(f"📁 File: {output_path}")
        print(f"🎬 Title: {script.get('title', 'N/A')}")
        print(f"⏱️  Duration: {script.get('duration_minutes', 'N/A')} phút")
        print(f"🎵 Genre: {script.get('music_direction', {}).get('genre', 'N/A')}")
        print(f"🎬 Scenes: {len(script.get('scenes', []))}")
        
        # Lyrics preview
        lyrics = script.get("lyrics", {})
        if lyrics.get("chorus"):
            print(f"\n🎤 Chorus preview:")
            for line in lyrics["chorus"].split("\n")[:4]:
                print(f"   ♪ {line}")
        
        print(f"{'━' * 50}\n")
    
    # ── Telegram Notification (chỉ gửi khi chạy standalone, không qua orchestrator) ──
    if args.no_telegram:
        return
    msg_lines = ["✍️ *Agent 2: Content Creator*", ""]
    msg_lines.append(f"🎬 *{script.get('title', 'N/A')}*")
    msg_lines.append(f"🎯 Chủ đề: {script.get('theme', topic)}")
    msg_lines.append(f"⏱ Thời lượng: {script.get('duration_minutes', 'N/A')} phút")
    msg_lines.append(f"👶 Độ tuổi: {script.get('target_age', 'N/A')}")
    
    # Scenes summary
    scenes = script.get('scenes', [])
    msg_lines.append(f"\n🎬 *{len(scenes)} Scene(s):*")
    for s in scenes:
        sid = s.get('id', '?')
        ts = s.get('timestamp', '?')
        desc = s.get('description', '')[:60]
        msg_lines.append(f"  {sid}. [{ts}] {desc}")
    
    # Lyrics
    if lyrics:
        msg_lines.append("\n🎤 *Lyrics:*")
        for section, text in lyrics.items():
            msg_lines.append(f"\n_{section}_:")
            msg_lines.append(text[:200])
    
    # Music direction
    music = script.get('music_direction', {})
    if music:
        msg_lines.append(f"\n🎵 *Music Direction:*")
        msg_lines.append(f"  Genre: {music.get('genre', 'N/A')}")
        msg_lines.append(f"  BPM: {music.get('bpm', 'N/A')}")
        msg_lines.append(f"  Mood: {music.get('mood', 'N/A')}")
    
    send_telegram("\n".join(msg_lines))
    print_success("Đã gửi kịch bản qua Telegram")

if __name__ == "__main__":
    main()
