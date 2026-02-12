---
name: youtube-kids-pipeline
description: "🎬 Pipeline TỰ ĐỘNG sản xuất video YouTube Kids. Khi user muốn TẠO VIDEO, LÀM VIDEO, XUẤT VIDEO KIDS → LUÔN chạy orchestrator.py. Pipeline 5 agents tự phối hợp. CHẠY BẰNG LỆNH BASH python3."
---

# 🎬 YouTube Kids Pipeline — Orchestrator Tự Động

> ⚡ **ĐÂY LÀ SKILL CHÍNH.** Khi user yêu cầu **tạo video** → LUÔN dùng skill này.
> 🚨 **LUÔN LUÔN** chạy bằng **lệnh bash** như bên dưới.

## KHI NÀO SỬ DỤNG — ƯU TIÊN CAO NHẤT

Dùng skill này khi user nhắn BẤT KỲ câu nào sau:

- "tạo video kids", "làm video trẻ em", "xuất video youtube kids"
- "tạo video về counting", "video nhạc trẻ em", "sản xuất video kids"
- "chạy pipeline", "start pipeline", "full pipeline"
- "tạo video", "làm video", "render video" (khi ngữ cảnh là trẻ em)
- Bất kỳ yêu cầu nào cần **nhiều hơn 1 agent** hoạt động

> ⚠️ **KHÔNG** dùng skill này khi user chỉ hỏi 1 việc cụ thể (ví dụ: "tìm trend thôi", "viết kịch bản thôi"). Khi đó dùng agent riêng lẻ.

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
