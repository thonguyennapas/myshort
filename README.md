# 🎬 MyShort — YouTube Kids Content Pipeline

## Tổng quan

5 Agent Skills trên OpenClaw, tự phối hợp sản xuất video YouTube Kids (2-8 tuổi).

## ⚡ Cách hoạt động

### User hỏi chung → Agents TỰ ĐỘNG phối hợp

```
User: "tạo video kids về counting animals"
  ↓
AI đọc SKILL.md (youtube-kids-pipeline) → chạy orchestrator.py
  ↓
orchestrator.py TỰ ĐỘNG chain 5 agents:
  Agent 1 (Trend) → Agent 2 (Script) → Agent 3 (Music) → Agent 4 (Video) → Agent 5 (Ghép+TG)
  ↓
Video hoàn chỉnh → gửi Telegram
```

### User hỏi riêng → Agent hoạt động ĐỘC LẬP

```
User: "tìm trend youtube kids"     → chỉ chạy Agent 1
User: "viết kịch bản counting"     → chỉ chạy Agent 2
User: "tạo nhạc thiếu nhi"         → chỉ chạy Agent 3
User: "ghép video gửi telegram"    → chỉ chạy Agent 5
```

Sau khi xong, agent hỏi: *"Muốn tiếp tục pipeline không?"* → user đồng ý → chạy tiếp.

## Cấu trúc

```
myshort/
├── SKILL.md                     ← 🎯 Pipeline chính (orchestrator)
├── trend-researcher/SKILL.md    ← 🔍 Agent 1 (độc lập)
├── content-creator/SKILL.md     ← ✍️ Agent 2 (độc lập)
├── music-maker/SKILL.md         ← 🎵 Agent 3 (độc lập)
├── video-maker/SKILL.md         ← 🎬 Agent 4 (độc lập)
├── video-aggregator/SKILL.md    ← 🎞️ Agent 5 (độc lập)
├── shared/                      ← Utils chung
└── scripts/                     ← Orchestrator + Deploy
```

## Quick Start

```bash
# Deploy
bash scripts/deploy.sh --setup-env

# Full pipeline (agents tự phối hợp)
python3 scripts/orchestrator.py --topic "counting colors" --send-telegram

# Chạy riêng 1 agent
python3 trend-researcher/scripts/trend_researcher.py --dry-run
```

## Giao tiếp Agent ↔ Agent

Qua file JSON trong `~/myshort-output/`:

| Agent | Input | Output |
|-------|-------|--------|
| 1. Trend | — | `trends/trend-*.json` |
| 2. Script | trend.json | `scripts/script-*.json` |
| 3. Music | script.json | `audio/*.mp3` |
| 4. Video | script.json | `clips/*.mp4` |
| 5. Aggregate | audio + clips | `final/*.mp4` → Telegram |
