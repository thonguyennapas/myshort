---
name: kids-video-maker
description: "🎬 Agent 4: Tạo video clips qua Google Veo. Dùng khi user nói 'render clips', 'tạo video clips', 'render video'. KHÔNG phải pipeline - chỉ tạo clips thôi. CHẠY BẰNG LỆNH BASH python3."
---

# 🎬 Agent 4: Video Maker — Google Veo

> 🚨 **LUÔN LUÔN** chạy bằng **lệnh bash** như bên dưới.

## KHI NÀO SỬ DỤNG

Dùng agent này khi user **CHỈ** muốn render video clips:
- "render video clips", "tạo video từ kịch bản", "generate video veo"
- "chạy agent 4", "tạo clips video"

> ⚠️ Nếu user muốn **TẠO VIDEO hoàn chỉnh** → dùng skill `youtube-kids-pipeline`.

## CÁCH THỰC HIỆN

Từ kịch bản:
```bash
python3 ~/.openclaw/skills/kids-video-maker/scripts/video_maker.py \
    --script ~/myshort-output/scripts/script-*.json
```

Với nhạc (tính timing):
```bash
python3 ~/.openclaw/skills/kids-video-maker/scripts/video_maker.py \
    --script ~/myshort-output/scripts/script-*.json \
    --music ~/myshort-output/audio/*.mp3
```

Test (xem Veo prompts):
```bash
python3 ~/.openclaw/skills/kids-video-maker/scripts/video_maker.py \
    --script ~/myshort-output/scripts/script-*.json --dry-run
```

## THAM SỐ

| Tham số | Giá trị |
|---------|---------|
| `--script path` | File kịch bản JSON từ Agent 2 |
| `--music path` | File nhạc MP3 (tính timing) |
| `--resolution` | 720p, 1080p, 4k (mặc định: 1080p) |
| `--dry-run` | Chỉ in Veo prompts |

## SAU KHI HOÀN THÀNH

1. Xác nhận clips: `ls ~/myshort-output/clips/*.mp4`
2. Báo cho user video clips đã render xong
3. **Hỏi user:** "Video clips đã xong! Muốn ghép + gửi Telegram không?"
4. Nếu user đồng ý → chạy `youtube-kids-pipeline --from-step 5` để ghép + gửi
