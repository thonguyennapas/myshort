---
name: kids-trend-researcher
description: "🔍 Agent 1: Tìm trend / xu hướng YouTube Kids. Dùng khi user nói 'tìm trend', 'tìm xu hướng', 'trend youtube kids', 'xem trend'. KHÔNG phải pipeline - chỉ tìm trend thôi. CHẠY BẰNG LỆNH BASH python3."
---

# 🔍 Agent 1: Trend Researcher — Xu hướng YouTube Kids

> 🚨 **LUÔN LUÔN** chạy bằng **lệnh bash** như bên dưới.

## KHI NÀO SỬ DỤNG

Dùng agent này khi user **CHỈ** muốn xem xu hướng, KHÔNG tạo video:
- "tìm trend youtube kids", "xu hướng video trẻ em"
- "video kids nào đang hot?", "nursery rhyme trending"
- "xem trend thôi", "research trend"

> ⚠️ Nếu user muốn **TẠO VIDEO** → dùng skill `youtube-kids-pipeline` thay vì agent này.

## CÁCH THỰC HIỆN

```bash
python3 ~/.openclaw/skills/kids-trend-researcher/scripts/trend_researcher.py --max 5
```

Lọc category:
```bash
python3 ~/.openclaw/skills/kids-trend-researcher/scripts/trend_researcher.py --category music_dance
```

Test:
```bash
python3 ~/.openclaw/skills/kids-trend-researcher/scripts/trend_researcher.py --dry-run
```

## THAM SỐ

| Tham số | Giá trị |
|---------|---------|
| `--max N` | Số xu hướng mỗi category (mặc định: 5) |
| `--age-range` | 2-5, 3-8, 2-8 (mặc định: 2-8) |
| `--category` | music_dance, education, characters, general |
| `--dry-run` | Test không search |

## SAU KHI HOÀN THÀNH

1. Đọc output: `cat ~/myshort-output/trends/trend-$(date +%Y%m%d).json`
2. Tóm tắt top xu hướng cho user
3. **Hỏi user:** "Bạn muốn tạo video từ trend này không? Nếu có, tôi sẽ chạy full pipeline."
4. Nếu user đồng ý → chạy `youtube-kids-pipeline` với topic từ trend
