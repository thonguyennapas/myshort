# 🎬 MyShort — YouTube Kids Content Pipeline

## Tổng quan

5 Agent Skills trên OpenClaw, tự phối hợp sản xuất video YouTube Kids (2-8 tuổi).
Mỗi agent hoạt động độc lập hoặc chạy chuỗi qua orchestrator.

## ⚡ Quick Start (3 bước)

```bash
# 1. Clone & Setup (cài packages + tạo .env)
git clone https://github.com/thonguyennapas/myshort.git
cd myshort
bash scripts/setup.sh

# 2. Điền API keys
nano ~/.openclaw/.env-myshort

# 3. Start pipeline (chạy trong screen)
bash scripts/start.sh --screen
```

## 🖥️ Deploy lên Server (Linux)

### Bước 1: Clone + Setup tự động

```bash
cd ~/napas/openclaw
git clone https://github.com/thonguyennapas/myshort.git
cd myshort
bash scripts/setup.sh
```

Setup tự động:
- ✅ Cài `requests`
- ✅ Kiểm tra FFmpeg (hỏi cài nếu chưa có)
- ✅ Copy `.env.example` → `~/.openclaw/.env-myshort`
- ✅ Tạo output dirs (`~/myshort-output/`)
- ✅ Deploy skills vào `~/.openclaw/skills/`

### Bước 2: Điền API keys

```bash
nano ~/.openclaw/.env-myshort
```

### Bước 3: Start pipeline

```bash
# Full pipeline (screen nền, song song với myclaw)
bash scripts/start.sh

# Hoặc chỉ định topic
bash scripts/start.sh --topic "counting animals"

# Dry-run test
bash scripts/start.sh --dry-run

# Chạy 1 agent riêng
bash scripts/start.sh --agent 1 --dry-run

# Xem logs
screen -r myshort

# Dừng
screen -X -S myshort quit
```

### (Optional) Cron Job — Tự động hàng ngày

```bash
crontab -e
# Thêm:
0 8 * * * cd ~/napas/openclaw/myshort && bash scripts/start.sh --topic "kids trends today" >> ~/myshort-output/cron.log 2>&1
```

## Cách hoạt động

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

## 📨 Telegram Notification

### Chạy full pipeline (orchestrator)
Orchestrator gửi **1 tin nhắn tổng hợp duy nhất** ở cuối pipeline — không spam từng agent riêng lẻ.

### Chạy agent riêng lẻ (standalone)
Mỗi agent tự động gửi kết quả chi tiết về Telegram, **kể cả khi API fail**:

| Agent | Thành công | Thất bại (gửi để tạo tay) |
|-------|-----------|---------------------------|
| 1: Trend | Trends + 🔗 URL + 📝 snippet | "Không tìm được" |
| 2: Content | Script + scenes + lyrics | Error message |
| 3: Music | Audio file + prompt | **Lyrics + Suno prompt** |
| 4: Video | Clip results + prompts | **Timestamps + Veo prompts** |

## Cấu trúc

```
myshort/
├── SKILL.md                     ← 🎯 Pipeline chính (orchestrator)
├── .env.example                 ← 🔑 Template biến môi trường
├── scripts/
│   ├── setup.sh                 ← 📦 Cài đặt 1 lần (packages + .env + deploy)
│   ├── start.sh                 ← 🚀 Chạy pipeline (screen nền)
│   ├── deploy.sh                ← 📦 Deploy skills vào ~/.openclaw/skills/
│   └── orchestrator.py          ← 🔄 Điều phối 5 agents
├── shared/
│   ├── utils.py                 ← 🛠️ Telegram, logging, config
│   └── safety_keywords.json     ← 🔒 Bộ lọc nội dung
├── trend-researcher/            ← 🔍 Agent 1
│   ├── SKILL.md
│   └── scripts/trend_researcher.py
├── content-creator/             ← ✍️ Agent 2
│   ├── SKILL.md
│   └── scripts/content_creator.py
├── music-maker/                 ← 🎵 Agent 3
│   ├── SKILL.md
│   └── scripts/music_maker.py
├── video-maker/                 ← 🎬 Agent 4
│   ├── SKILL.md
│   └── scripts/video_maker.py
└── video-aggregator/            ← 🎞️ Agent 5
    ├── SKILL.md
    └── scripts/video_aggregator.py
```

## 🔑 Biến Môi Trường

**KHÔNG BAO GIỜ** commit `.env` lên Git!

```bash
# Setup
cp .env.example ~/.openclaw/.env-myshort
nano ~/.openclaw/.env-myshort
```

| Nhóm | Biến | Bắt buộc | Mô tả |
|-|-|-|-|
| **LLM** | `LLM_PROVIDER` | ✅ | gemini, openai |
| | `LLM_MODEL` | ✅ | gemini-2.5-flash, gpt-4o |
| | `LLM_API_KEY` | ✅ | API key |
| **Suno AI** | `SUNO_API_KEY` | ✅ | GoAPI.ai hoặc Suno key |
| | `SUNO_API_URL` | ✅ | `https://api.goapi.ai/suno` |
| | `SUNO_TIMEOUT` | | Timeout (mặc định: 300s) |
| **Google Veo** | `GOOGLE_VEO_API_KEY` | ✅ | Google AI Studio key |
| | `GOOGLE_CLOUD_PROJECT` | 🔸 | Cho Vertex AI |
| | `VEO_TIMEOUT` | | Timeout (mặc định: 600s) |
| **Telegram** | `TELEGRAM_TOKEN` | ✅ | Bot token |
| | `TELEGRAM_CHAT_ID` | ✅ | Chat ID nhận kết quả |
| **Search** | `TAVILY_API_KEY` | ✅ | Free 1000 req/tháng |
| **Tools** | `FFMPEG_PATH` | | Mặc định: `ffmpeg` |
| | `OUTPUT_DIR` | | Mặc định: `~/myshort-output` |

## Giao tiếp Agent ↔ Agent

Qua file JSON trong `~/myshort-output/`:

| Agent | Input | Output |
|-------|-------|--------|
| 1. Trend | — | `trends/trend-*.json` |
| 2. Script | trend.json | `scripts/script-*.json` |
| 3. Music | script.json | `audio/*.mp3` |
| 4. Video | script.json | `clips/*.mp4` |
| 5. Aggregate | audio + clips | `final/*.mp4` → Telegram |

## 🔄 Cập nhật & Khởi động lại (trên VPS)

Khi có thay đổi code mới, chạy 3 lệnh sau trên VPS:

```bash
# 1. Dừng pipeline đang chạy
screen -X -S myshort quit

# 2. Pull code mới từ git
cd ~/napas/openclaw/myshort
git pull origin main

# 3. (Tùy chọn) Deploy lại skills nếu có thay đổi SKILL.md
bash scripts/deploy.sh

# 4. Chạy lại pipeline
bash scripts/start.sh
```

### Quick 1-liner (copy-paste):

```bash
screen -X -S myshort quit 2>/dev/null; cd ~/napas/openclaw/myshort && git pull origin main && bash scripts/deploy.sh && bash scripts/start.sh
```

### Kiểm tra trạng thái:

```bash
# Xem pipeline có đang chạy không
screen -ls

# Xem logs pipeline đang chạy
screen -r myshort

# Detach khỏi screen (giữ pipeline chạy nền)
# Nhấn: Ctrl+A → D

# Dừng pipeline
screen -X -S myshort quit
```

## Thêm Agent Mới

```bash
# 1. Tạo folder
mkdir -p myshort/ten-agent-moi/scripts

# 2. Tạo SKILL.md (< 100 dòng)
# 3. Thêm scripts/tool.py
# 4. Thêm vào SKILL_MAP trong scripts/deploy.sh
# 5. Deploy
git push origin main
bash scripts/deploy.sh
```

---

📅 Cập nhật: 12/02/2026
🔧 Version: 1.1 — 5 agents, consolidated Telegram notifications, GoAPI.ai Suno + Gemini Veo
