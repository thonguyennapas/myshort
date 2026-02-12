#!/bin/bash
# ==============================================================================
# 🎬 MyShort — Setup Script
#
# Cài đặt packages, tạo .env template, tạo output dirs.
# Chạy 1 lần khi deploy lần đầu trên server.
#
# Usage:
#   bash scripts/setup.sh
# ==============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}🎬 MyShort — Setup${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# ── Step 1: Python packages ──
echo -e "${BLUE}[1/5] Cài Python packages...${NC}"

PIP_FLAGS=""
if pip install --help 2>&1 | grep -q "break-system-packages"; then
    PIP_FLAGS="--break-system-packages"
fi

for pkg in requests; do
    if python3 -c "import $pkg" 2>/dev/null; then
        echo -e "  ${GREEN}✅ $pkg (đã cài)${NC}"
    else
        pip install $PIP_FLAGS "$pkg" 2>/dev/null && \
            echo -e "  ${GREEN}✅ $pkg (vừa cài)${NC}" || \
            echo -e "  ${RED}❌ $pkg (lỗi cài)${NC}"
    fi
done

# ── Step 2: FFmpeg ──
echo ""
echo -e "${BLUE}[2/5] Kiểm tra FFmpeg...${NC}"

if command -v ffmpeg &>/dev/null; then
    FFMPEG_VER=$(ffmpeg -version 2>&1 | head -1 | awk '{print $3}')
    echo -e "  ${GREEN}✅ FFmpeg ${FFMPEG_VER}${NC}"
else
    echo -e "  ${RED}❌ FFmpeg chưa cài!${NC}"
    echo -e "  ${YELLOW}   sudo apt install ffmpeg -y${NC}"
    echo ""
    read -p "  Cài FFmpeg ngay? (y/N): " install_ffmpeg
    if [[ "$install_ffmpeg" =~ ^[Yy] ]]; then
        sudo apt install ffmpeg -y && \
            echo -e "  ${GREEN}✅ FFmpeg đã cài${NC}" || \
            echo -e "  ${RED}❌ Cài FFmpeg thất bại${NC}"
    fi
fi

# ── Step 3: .env ──
echo ""
echo -e "${BLUE}[3/5] Setup .env...${NC}"

ENV_DIR="$HOME/.openclaw"
ENV_FILE="$ENV_DIR/.env-myshort"

mkdir -p "$ENV_DIR"

if [ -f "$ENV_FILE" ]; then
    echo -e "  ${GREEN}✅ .env đã tồn tại: $ENV_FILE${NC}"
    echo -e "  ${YELLOW}   Để reset: rm $ENV_FILE && bash scripts/setup.sh${NC}"
else
    cp "$PROJECT_DIR/.env.example" "$ENV_FILE"
    echo -e "  ${GREEN}✅ Đã copy .env.example → $ENV_FILE${NC}"
    echo ""
    echo -e "  ${YELLOW}📝 Bạn cần điền API keys vào file .env:${NC}"
    echo -e "  ${CYAN}   nano $ENV_FILE${NC}"
    echo ""
    echo -e "  ${YELLOW}Các key bắt buộc:${NC}"
    echo -e "    • LLM_API_KEY        — Google AI Studio / OpenAI"
    echo -e "    • SUNO_API_KEY       — GoAPI.ai hoặc Suno"
    echo -e "    • GOOGLE_VEO_API_KEY — Google AI Studio (Veo)"
    echo -e "    • TELEGRAM_TOKEN     — Telegram Bot token"
    echo -e "    • TELEGRAM_CHAT_ID   — Chat ID nhận kết quả"
    echo -e "    • TAVILY_API_KEY     — Tavily Search (free 1000/tháng)"
fi

# ── Step 4: Output dirs ──
echo ""
echo -e "${BLUE}[4/5] Tạo output directories...${NC}"

OUTPUT_DIR="${OUTPUT_DIR:-$HOME/myshort-output}"
mkdir -p "$OUTPUT_DIR"/{trends,scripts,audio,clips,final}
echo -e "  ${GREEN}✅ $OUTPUT_DIR/{trends,scripts,audio,clips,final}${NC}"

# ── Step 5: Deploy skills ──
echo ""
echo -e "${BLUE}[5/5] Deploy skills vào ~/.openclaw/skills/...${NC}"

bash "$SCRIPT_DIR/deploy.sh"

# ── Done ──
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ SETUP HOÀN TẤT!${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "📋 ${YELLOW}Bước tiếp theo:${NC}"
echo ""
echo -e "  ${CYAN}1. Điền API keys:${NC}"
echo -e "     nano $ENV_FILE"
echo ""
echo -e "  ${CYAN}2. Start pipeline:${NC}"
echo -e "     bash scripts/start.sh --screen"
echo ""
echo -e "  ${CYAN}3. Test dry-run:${NC}"
echo -e "     bash scripts/start.sh --dry-run"
echo ""
