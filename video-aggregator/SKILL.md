---
name: kids-video-aggregator
description: "Agent 5: Ghép video + audio bằng FFmpeg, gửi qua Telegram. Dùng KHI user CHỈ cần ghép/export/gửi video. CHẠY BẰNG LỆNH BASH python3."
---

# 🎞️ Agent 5: Video Aggregator — Ghép + Telegram

> 🚨 **LUÔN LUÔN** chạy bằng **lệnh bash** như bên dưới.

## KHI NÀO SỬ DỤNG

Dùng agent này khi user **CHỈ** muốn ghép/gửi:
- "ghép video + nhạc", "merge clips", "export video final"
- "gửi video qua telegram", "send telegram"

> ⚠️ Nếu user muốn **TẠO VIDEO từ đầu** → dùng skill `youtube-kids-pipeline`.

## CÁCH THỰC HIỆN

Ghép + gửi Telegram:
```bash
python3 ~/.openclaw/skills/kids-video-aggregator/scripts/video_aggregator.py \
    --clips-dir ~/myshort-output/clips/ \
    --audio ~/myshort-output/audio/*.mp3 \
    --script ~/myshort-output/scripts/script-*.json \
    --send-telegram
```

Chỉ ghép (không gửi):
```bash
python3 ~/.openclaw/skills/kids-video-aggregator/scripts/video_aggregator.py \
    --clips-dir ~/myshort-output/clips/ \
    --audio ~/myshort-output/audio/*.mp3
```

Chỉ gửi file có sẵn:
```bash
python3 ~/.openclaw/skills/kids-video-aggregator/scripts/video_aggregator.py \
    --send-only ~/myshort-output/final/final.mp4
```

## THAM SỐ

| Tham số | Giá trị |
|---------|---------|
| `--clips-dir path` | Thư mục video clips |
| `--audio path` | File audio MP3 |
| `--script path` | File kịch bản (metadata) |
| `--send-telegram` | Gửi qua Telegram |
| `--send-only path` | Chỉ gửi file có sẵn |
| `--dry-run` | Test pipeline |

## SAU KHI HOÀN THÀNH

1. Xác nhận video: `ls ~/myshort-output/final/*.mp4`
2. Nếu gửi Telegram → xác nhận đã gửi thành công
3. Báo cho user: "Video đã hoàn thành và gửi qua Telegram! 🎉"
