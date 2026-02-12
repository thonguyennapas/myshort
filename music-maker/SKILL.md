---
name: kids-music-maker
description: "🎵 Agent 3: Tạo nhạc thiếu nhi qua Suno AI. Dùng khi user nói 'tạo nhạc', 'generate music', 'làm nhạc', 'nhạc trẻ em'. KHÔNG phải pipeline - chỉ tạo nhạc thôi. CHẠY BẰNG LỆNH BASH python3."
---

# 🎵 Agent 3: Music Maker — Nhạc Suno AI

> 🚨 **LUÔN LUÔN** chạy bằng **lệnh bash** như bên dưới.

## KHI NÀO SỬ DỤNG

Dùng agent này khi user **CHỈ** muốn tạo nhạc:
- "tạo nhạc trẻ em", "generate music kids", "làm bài hát thiếu nhi"
- "suno tạo nhạc", "nhạc cho video kids"

> ⚠️ Nếu user muốn **TẠO VIDEO hoàn chỉnh** → dùng skill `youtube-kids-pipeline`.

## CÁCH THỰC HIỆN

Từ kịch bản có sẵn:
```bash
python3 ~/.openclaw/skills/kids-music-maker/scripts/music_maker.py \
    --script ~/myshort-output/scripts/script-*.json
```

Test (xem Suno prompt):
```bash
python3 ~/.openclaw/skills/kids-music-maker/scripts/music_maker.py \
    --script ~/myshort-output/scripts/script-*.json --dry-run
```

## THAM SỐ

| Tham số | Giá trị |
|---------|---------|
| `--script path` | File kịch bản JSON từ Agent 2 |
| `--wait-timeout N` | Timeout chờ Suno (giây, mặc định: 300) |
| `--dry-run` | Chỉ in prompt, không gọi API |

## SAU KHI HOÀN THÀNH

1. Xác nhận file nhạc: `ls ~/myshort-output/audio/*.mp3`
2. Báo cho user nhạc đã tạo xong
3. **Hỏi user:** "Nhạc đã xong! Muốn tạo video + ghép luôn không?"
4. Nếu user đồng ý → chạy `youtube-kids-pipeline --from-step 4` để render video + ghép
