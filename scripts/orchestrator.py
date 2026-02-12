#!/usr/bin/env python3
"""
🎬 MyShort Orchestrator — Pipeline điều phối 5 Agent Skills
Chạy tuần tự: Trend Research → Content Create → Music → Video → Aggregate

Mỗi agent là 1 skill riêng (SKILL.md riêng), giao tiếp qua file JSON.

Usage:
    python3 orchestrator.py                                    # Full pipeline
    python3 orchestrator.py --dry-run                          # Test toàn bộ
    python3 orchestrator.py --from-step 3                      # Resume từ step 3
    python3 orchestrator.py --topic "counting animals"         # Chỉ định topic
"""

import argparse
import json
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

# Add shared/ to path
MYSHORT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(MYSHORT_ROOT / "shared"))

from utils import (
    setup_logging, get_config, ensure_output_dirs, save_json, load_json,
    PipelineState, print_header, print_step, print_success,
    print_warning, print_error, check_dependencies, get_output_dir
)

logger = setup_logging("Orchestrator")

# ── Skill Paths (khi deploy trên VPS) ──
SKILLS_BASE = Path.home() / ".openclaw" / "skills"

# Fallback: khi chạy từ source tree trực tiếp
SOURCE_BASE = MYSHORT_ROOT

AGENTS = {
    1: {
        "name": "Trend Researcher",
        "emoji": "🔍",
        "skill": "kids-trend-researcher",
        "script": "scripts/trend_researcher.py",
    },
    2: {
        "name": "Content Creator",
        "emoji": "✍️",
        "skill": "kids-content-creator",
        "script": "scripts/content_creator.py",
    },
    3: {
        "name": "Music Maker",
        "emoji": "🎵",
        "skill": "kids-music-maker",
        "script": "scripts/music_maker.py",
    },
    4: {
        "name": "Video Maker",
        "emoji": "🎬",
        "skill": "kids-video-maker",
        "script": "scripts/video_maker.py",
    },
    5: {
        "name": "Video Aggregator",
        "emoji": "🎞️",
        "skill": "kids-video-aggregator",
        "script": "scripts/video_aggregator.py",
    },
}

# Mapping skill_name → source folder name
SKILL_TO_SOURCE = {
    "kids-trend-researcher": "trend-researcher",
    "kids-content-creator": "content-creator",
    "kids-music-maker": "music-maker",
    "kids-video-maker": "video-maker",
    "kids-video-aggregator": "video-aggregator",
}

def find_agent_script(agent_info):
    """Tìm script của agent — deployed skill trước, source tree sau."""
    skill = agent_info["skill"]
    script = agent_info["script"]
    
    # 1. Deployed path
    deployed = SKILLS_BASE / skill / script
    if deployed.exists():
        return str(deployed)
    
    # 2. Source tree path
    source_folder = SKILL_TO_SOURCE.get(skill, skill)
    source = SOURCE_BASE / source_folder / script
    if source.exists():
        return str(source)
    
    return None

def run_agent(step_num, agent_args, state, dry_run=False):
    """Chạy 1 agent bằng subprocess."""
    agent = AGENTS[step_num]
    script_path = find_agent_script(agent)
    
    if not script_path:
        print_error(f"Không tìm thấy script cho {agent['name']}!")
        state.set_step(step_num, "failed")
        return None
    
    cmd = [sys.executable, script_path] + agent_args
    if dry_run:
        cmd.append("--dry-run")
    cmd.extend(["--json", "--no-telegram"])
    
    print(f"  🔧 CMD: {' '.join(cmd[:5])}...")
    
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=900  # 15 min max
        )
        
        if result.returncode != 0:
            print_error(f"Agent failed: {result.stderr[:300]}")
            state.set_step(step_num, "failed")
            return None
        
        # Parse JSON output
        try:
            data = json.loads(result.stdout)
            state.set_step(step_num, "completed")
            return data
        except json.JSONDecodeError:
            # Non-JSON output is OK for some agents
            print_success(f"Agent completed (non-JSON output)")
            state.set_step(step_num, "completed")
            return {"raw_output": result.stdout[:500]}
    
    except subprocess.TimeoutExpired:
        print_error(f"Agent timeout (900s)!")
        state.set_step(step_num, "failed")
        return None
    except Exception as e:
        print_error(f"Agent error: {e}")
        state.set_step(step_num, "failed")
        return None

def run_pipeline(args):
    """Chạy toàn bộ pipeline."""
    print_header("MyShort — YouTube Kids Content Pipeline", "🎬")
    
    config = get_config()
    state = PipelineState(args.session_id if hasattr(args, 'session_id') else None)
    output_dir = ensure_output_dirs()
    
    print(f"  📋 Session: {state.session_id}")
    print(f"  🔄 Mode: {'DRY-RUN' if args.dry_run else 'PRODUCTION'}")
    print(f"  ▶️  Bắt đầu từ Step: {args.from_step}")
    print()
    
    # Pre-flight
    if not args.dry_run:
        issues = check_dependencies()
        for issue in issues:
            print_warning(issue)
    
    results = {}
    
    # ── Step 1: Trend Research ──
    if args.from_step <= 1:
        print(f"\n{'═' * 50}")
        print(f"  🔍 STEP 1/5: Trend Researcher")
        print(f"{'═' * 50}\n")
        
        step_args = ["--max", "5"]
        if args.age_range:
            step_args.extend(["--age-range", args.age_range])
        if hasattr(args, 'category') and args.category:
            step_args.extend(["--category", args.category])
        
        results[1] = run_agent(1, step_args, state, args.dry_run)
        
        # Extract trend file from output or find latest
        trend_path = None
        if results[1] and results[1].get("output_file"):
            trend_path = results[1]["output_file"]
        else:
            trend_files = sorted((output_dir / "trends").glob("trend-*.json"), reverse=True)
            if trend_files:
                trend_path = str(trend_files[0])
        if trend_path:
            state.set_file("trend", trend_path)
            print(f"  📎 Trend: {trend_path}")
    
    # ── Step 2: Content Creator ──
    if args.from_step <= 2:
        print(f"\n{'═' * 50}")
        print(f"  ✍️ STEP 2/5: Content Creator")
        print(f"{'═' * 50}\n")
        
        step_args = ["--duration", str(args.duration), "--style", args.style]
        if args.topic:
            step_args.extend(["--topic", args.topic])
        else:
            trend_path = state.get_file("trend")
            if trend_path:
                step_args.extend(["--trend", trend_path])
        if not args.skip_review:
            step_args.append("--review-prompts")
        
        results[2] = run_agent(2, step_args, state, args.dry_run)
        
        # Find latest script file
        script_files = sorted((output_dir / "scripts").glob("script-*.json"), reverse=True)
        if script_files:
            state.set_file("script", str(script_files[0]))
            print(f"  📎 Script: {script_files[0]}")
    
    # ── Step 3: Music Maker ──
    if args.from_step <= 3:
        print(f"\n{'═' * 50}")
        print(f"  🎵 STEP 3/5: Music Maker")
        print(f"{'═' * 50}\n")
        
        step_args = []
        script_path = state.get_file("script")
        if script_path:
            step_args.extend(["--script", script_path])
        
        results[3] = run_agent(3, step_args, state, args.dry_run)
        
        # Extract actual audio path from agent output
        if results[3]:
            audio_file = results[3].get("audio_file")
            if audio_file:
                state.set_file("audio", audio_file)
                print(f"  📎 Audio: {audio_file}")
            # Store actual duration for Agent 4
            actual_dur = results[3].get("actual_duration")
            if actual_dur:
                state.set_file("audio_duration", str(actual_dur))
        
        # Fallback: find latest audio file
        if not state.get_file("audio"):
            audio_files = sorted((output_dir / "audio").glob("*.mp3"), reverse=True)
            if audio_files:
                state.set_file("audio", str(audio_files[0]))
                print(f"  📎 Audio (fallback): {audio_files[0]}")
    
    # ── Step 4: Video Maker ──
    if args.from_step <= 4:
        print(f"\n{'═' * 50}")
        print(f"  🎬 STEP 4/5: Video Maker")
        print(f"{'═' * 50}\n")
        
        step_args = []
        script_path = state.get_file("script")
        if script_path:
            step_args.extend(["--script", script_path])
        
        audio_path = state.get_file("audio")
        if audio_path:
            step_args.extend(["--music", audio_path])
        
        results[4] = run_agent(4, step_args, state, args.dry_run)
        
        # Extract clips_dir from agent output
        if results[4]:
            clips_dir = results[4].get("clips_dir")
            if clips_dir:
                state.set_file("clips_dir", clips_dir)
                print(f"  📎 Clips: {clips_dir}")
    
    # ── Step 5: Video Aggregator ──
    if args.from_step <= 5:
        print(f"\n{'═' * 50}")
        print(f"  🎞️ STEP 5/5: Video Aggregator")
        print(f"{'═' * 50}\n")
        
        step_args = []
        
        # Use actual clips_dir from Agent 4, or find latest
        clips_dir = state.get_file("clips_dir")
        if not clips_dir:
            # Find latest clips subdirectory
            clips_base = output_dir / "clips"
            clip_dirs = sorted([d for d in clips_base.iterdir() if d.is_dir()], reverse=True) if clips_base.exists() else []
            clips_dir = str(clip_dirs[0]) if clip_dirs else str(clips_base)
        step_args.extend(["--clips-dir", clips_dir])
        
        audio_path = state.get_file("audio")
        if audio_path:
            step_args.extend(["--audio", audio_path])
        
        script_path = state.get_file("script")
        if script_path:
            step_args.extend(["--script", script_path])
        
        if args.send_telegram:
            step_args.append("--send-telegram")
        
        results[5] = run_agent(5, step_args, state, args.dry_run)
    
    # ── Summary ──
    print(f"\n{'━' * 50}")
    print(f"📊 PIPELINE SUMMARY")
    print(f"{'━' * 50}")
    print(f"  Session: {state.session_id}")
    
    for step_num in range(1, 6):
        agent = AGENTS[step_num]
        step_state = state.get_step(step_num)
        status = step_state.get("status", "skipped")
        icon = "✅" if status == "completed" else "❌" if status == "failed" else "⏭️"
        print(f"  {icon} Step {step_num}: {agent['name']} — {status}")
    
    print(f"\n  📁 Output: {output_dir}")
    print(f"  📁 State: {state.state_file}")
    print(f"{'━' * 50}\n")
    
    # ── Telegram: Gửi 1 tin nhắn tổng hợp DUY NHẤT ──
    if args.send_telegram:
        try:
            from utils import send_telegram as tg_send
            msg_lines = ["🎬 *MyShort Pipeline - Kết quả tổng hợp*", ""]
            msg_lines.append(f"📝 Session: `{state.session_id}`")
            msg_lines.append(f"🔄 Mode: {'DRY-RUN' if args.dry_run else 'PRODUCTION'}")
            msg_lines.append("")
            
            for step_num in range(1, 6):
                agent = AGENTS[step_num]
                step_state = state.get_step(step_num)
                status = step_state.get("status", "skipped")
                icon = "✅" if status == "completed" else "❌" if status == "failed" else "⏭️"
                msg_lines.append(f"{icon} Step {step_num}: {agent['emoji']} {agent['name']} — {status}")
            
            # Thêm chi tiết từ kết quả từng agent
            if results.get(1) and results[1].get('trends'):
                msg_lines.append(f"\n🔍 *Trend Researcher:*")
                for i, t in enumerate(results[1].get('trends', [])[:5]):
                    name = t.get('name', '?')[:60]
                    url = t.get('url', '')
                    msg_lines.append(f"  {i+1}. {name}")
                    if url:
                        msg_lines.append(f"     🔗 {url}")
            
            msg_lines.append(f"\n📁 Output: `{output_dir}`")
            
            tg_send("\n".join(msg_lines))
            print_success("Đã gửi kết quả tổng hợp qua Telegram")
        except Exception as e:
            print_warning(f"Không gửi được Telegram: {e}")
    
    return results

def main():
    parser = argparse.ArgumentParser(
        description="🎬 MyShort Orchestrator — YouTube Kids Content Pipeline"
    )
    parser.add_argument("--from-step", type=int, default=1, choices=[1, 2, 3, 4, 5])
    parser.add_argument("--session", dest="session_id")
    parser.add_argument("--topic", help="Chỉ định topic")
    parser.add_argument("--age-range", default="2-5")
    parser.add_argument("--duration", type=int, default=3)
    parser.add_argument("--style", default="cocomelon",
                       choices=["cocomelon", "disney", "educational", "lullaby"])
    parser.add_argument("--category", choices=["music_dance", "education", "characters", "general"])
    parser.add_argument("--skip-review", action="store_true")
    parser.add_argument("--send-telegram", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    
    run_pipeline(args)

if __name__ == "__main__":
    main()
