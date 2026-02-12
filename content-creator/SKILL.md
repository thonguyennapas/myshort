---
name: kids-content-creator
description: "✍️ Agent 2: Viết kịch bản / script / lyrics. Dùng khi user nói 'viết kịch bản', 'tạo script', 'viết lyrics', 'sáng tác', 'kịch bản đếm số', 'kịch bản counting'. KHÔNG phải pipeline - chỉ viết kịch bản thôi. CHẠY BẰNG LỆNH BASH python3."
---

# ✍️ Agent 2: Content Creator — Kịch bản YouTube Kids

> 🚨 **LUÔN LUÔN** chạy bằng **lệnh bash** như bên dưới.
> ⚡ **KHÔNG PHẢI PIPELINE** — skill này CHỈ viết kịch bản, KHÔNG tạo video.

## KHI NÀO SỬ DỤNG

Dùng agent này khi user muốn **viết kịch bản / script / lyrics**:
- "viết kịch bản", "viết kịch bản đếm số", "viết kịch bản counting"
- "tạo script", "tạo kịch bản", "viết script cho video"
- "viết lyrics", "sáng tác lời bài hát trẻ em", "tạo lyrics"
- "kịch bản về...", "script về..."

> ⚠️ Nếu user muốn **TẠO VIDEO hoàn chỉnh** (nói "tạo video", "làm video") → dùng skill `youtube-kids-pipeline`.

## CÁCH THỰC HIỆN

Từ topic:
```bash
python3 ~/.openclaw/skills/kids-content-creator/scripts/content_creator.py \
    --topic "counting colors with teddy bear" --duration 3 --style cocomelon
```

Từ trend Agent 1:
```bash
python3 ~/.openclaw/skills/kids-content-creator/scripts/content_creator.py \
    --trend ~/myshort-output/trends/trend-$(date +%Y%m%d).json
```

Review Veo prompts:
```bash
python3 ~/.openclaw/skills/kids-content-creator/scripts/content_creator.py \
    --topic "learning animals" --review-prompts
```

Test:
```bash
python3 ~/.openclaw/skills/kids-content-creator/scripts/content_creator.py --dry-run
```

## THAM SỐ

| Tham số | Giá trị |
|---------|---------|
| `--topic` | Chủ đề video |
| `--trend path` | File trend JSON từ Agent 1 |
| `--duration N` | Thời lượng phút (2-5, mặc định: 3) |
| `--style` | cocomelon, disney, educational, lullaby |
| `--review-prompts` | Xem Veo prompts trước khi render |
| `--dry-run` | Test không gọi LLM |

## SAU KHI HOÀN THÀNH

1. Đọc output: `cat ~/myshort-output/scripts/script-*.json`
2. Hiển thị lyrics + scene descriptions cho user
3. **Hỏi user:** "Kịch bản OK chưa? Muốn tạo nhạc + video từ kịch bản này không?"
4. Nếu user đồng ý → chạy `youtube-kids-pipeline --from-step 3` để tiếp tục pipeline
