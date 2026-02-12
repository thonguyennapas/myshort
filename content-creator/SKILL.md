---
name: kids-content-creator
description: "Agent 2: Viết kịch bản video YouTube Kids. Dùng KHI user CHỈ muốn viết kịch bản/lyrics mà KHÔNG cần tạo nhạc+video. CHẠY BẰNG LỆNH BASH python3."
---

# ✍️ Agent 2: Content Creator — Kịch bản YouTube Kids

> 🚨 **LUÔN LUÔN** chạy bằng **lệnh bash** như bên dưới.

## KHI NÀO SỬ DỤNG

Dùng agent này khi user **CHỈ** muốn kịch bản/lyrics:
- "viết kịch bản video kids", "tạo lyrics trẻ em"
- "viết script cho video counting", "sáng tác lời bài hát trẻ em"

> ⚠️ Nếu user muốn **TẠO VIDEO hoàn chỉnh** → dùng skill `youtube-kids-pipeline`.

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
