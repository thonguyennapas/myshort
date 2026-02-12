---
name: youtube-kids-pipeline
description: "🎬 Pipeline TỰ ĐỘNG sản xuất video YouTube Kids HOÀN CHỈNH (5 bước). CHỈ dùng khi user nói RÕ RÀNG 'tạo video', 'làm video', 'xuất video', 'chạy pipeline'. KHÔNG dùng khi user chỉ muốn 1 việc (viết kịch bản, tìm trend, tạo nhạc). CHẠY BẰNG LỆNH BASH python3."
---

# 🎬 YouTube Kids Pipeline — Orchestrator Tự Động

> ⚡ **ĐÂY LÀ SKILL PIPELINE** — chạy TẤT CẢ 5 agents liên tiếp.
> 🚨 **LUÔN LUÔN** chạy bằng **lệnh bash** như bên dưới.

## KHI NÀO SỬ DỤNG — CHỈ KHI USER MUỐN LÀM VIDEO

Dùng skill này **CHỈ KHI** user nói rõ muốn **TẠO VIDEO / LÀM VIDEO**:

- "tạo video kids", "làm video trẻ em", "xuất video youtube kids"
- "chạy pipeline", "start pipeline", "full pipeline"
- "tạo video", "làm video", "render video"
- "tạo video về counting", "làm video đếm số"

## ⛔ KHÔNG DÙNG PIPELINE KHI:

**Nếu user chỉ muốn 1 việc cụ thể → DÙNG AGENT RIÊNG LẺ, KHÔNG chạy pipeline!**

| User nói | Dùng skill nào | KHÔNG phải pipeline |
|----------|---------------|---------------------|
| "viết kịch bản", "tạo script", "viết lyrics" | `kids-content-creator` | ✅ Agent 2 riêng |
| "tìm trend", "tìm xu hướng" | `kids-trend-researcher` | ✅ Agent 1 riêng |
| "tạo nhạc", "generate music" | `kids-music-maker` | ✅ Agent 3 riêng |
| "render clips", "tạo video clips" | `kids-video-maker` | ✅ Agent 4 riêng |
| "ghép video", "gửi telegram" | `kids-video-aggregator` | ✅ Agent 5 riêng |

> 🔑 **QUY TẮC VÀNG:** Nếu user KHÔNG nói "tạo video" hoặc "làm video" → KHÔNG chạy pipeline.

## CÁCH THỰC HIỆN — 1 LỆNH DUY NHẤT

### 🚀 Chạy full pipeline (5 agents tự phối hợp):
```bash
python3 ~/.openclaw/skills/youtube-kids-pipeline/scripts/orchestrator.py \
    --topic "counting animals" --duration 3 --style cocomelon --send-telegram
```

### User KHÔNG chỉ định topic → pipeline tự tìm trend:
```bash
python3 ~/.openclaw/skills/youtube-kids-pipeline/scripts/orchestrator.py \
    --duration 3 --send-telegram
```

### Dry-run test (không gọi API):
```bash
python3 ~/.openclaw/skills/youtube-kids-pipeline/scripts/orchestrator.py --dry-run
```

### Resume nếu bị gián đoạn:
```bash
python3 ~/.openclaw/skills/youtube-kids-pipeline/scripts/orchestrator.py \
    --from-step 3 --session SESSION_ID
```

## TỰ ĐỘNG XỬ LÝ

Orchestrator **TỰ ĐỘNG** chạy 5 bước tuần tự, KHÔNG cần trigger thủ công:

```
Step 1: 🔍 Trend Researcher  → Tìm xu hướng → trend.json
           ↓ tự động
Step 2: ✍️ Content Creator   → Viết kịch bản → script.json
           ↓ tự động
Step 3: 🎵 Music Maker       → Tạo nhạc Suno → audio.mp3
           ↓ tự động
Step 4: 🎬 Video Maker       → Render video Veo → clips/*.mp4
           ↓ tự động
Step 5: 🎞️ Video Aggregator  → Ghép + gửi Telegram → final.mp4
```

## THAM SỐ

| Tham số | Giá trị | Mặc định |
|---------|---------|----------|
| `--topic` | Chủ đề video | Tự tìm từ trend |
| `--duration` | Thời lượng (phút) | 3 |
| `--style` | cocomelon, disney, educational, lullaby | cocomelon |
| `--age-range` | 2-5, 3-8, 2-8 | 2-5 |
| `--send-telegram` | Gửi video qua Telegram | Không gửi |
| `--from-step N` | Resume từ step N | 1 |
| `--dry-run` | Test không gọi API | — |

## SAU KHI HOÀN THÀNH

Đọc kết quả pipeline và báo cho user:
- Số step thành công/thất bại
- Đường dẫn video cuối: `~/myshort-output/final/*.mp4`
- Nếu `--send-telegram`: xác nhận đã gửi
