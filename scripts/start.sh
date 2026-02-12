#!/bin/bash
# ==============================================================================
# 🎬 MyShort — Start Pipeline
#
# Load .env, validate keys, chạy orchestrator trong screen session.
# Chạy song song với myclaw (screen riêng: "myshort").
#
# Usage:
#   bash scripts/start.sh                    # Full pipeline trong screen
#   bash scripts/start.sh --screen           # Giống trên (mặc định)
#   bash scripts/start.sh --topic "animals"  # Chỉ định topic
#   bash scripts/start.sh --dry-run          # Test không gọi API
#   bash scripts/start.sh --agent 1          # Chạy 1 agent cụ thể
#   bash scripts/start.sh --foreground       # Chạy foreground (debug)
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

SCREEN_NAME="myshort"
TOPIC=""
DRY_RUN=""
AGENT=""
FOREGROUND=false
ENV_FILE=""

# ── Parse Arguments ──
while [[ $# -gt 0 ]]; do
    case $1 in
        --screen)       shift ;;
        --screen-name)  SCREEN_NAME="$2"; shift 2 ;;
        --topic)        TOPIC="$2"; shift 2 ;;
        --dry-run)      DRY_RUN="--dry-run"; shift ;;
        --agent)        AGENT="$2"; shift 2 ;;
        --foreground)   FOREGROUND=true; shift ;;
        --env)          ENV_FILE="$2"; shift 2 ;;
        --help|-h)
            echo "Usage: bash scripts/start.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --topic TEXT      Chủ đề video (mặc định: auto từ trends)"
            echo "  --agent N         Chạy 1 agent cụ thể (1-5)"
            echo "  --dry-run         Test không gọi API"
            echo "  --screen-name     Tên screen (mặc định: myshort)"
            echo "  --foreground      Chạy foreground thay vì screen"
            echo "  --env FILE        Đường dẫn file .env"
            echo "  -h, --help        Hiện help"
            echo ""
            echo "Examples:"
            echo "  bash scripts/start.sh --topic 'counting animals'"
            echo "  bash scripts/start.sh --dry-run"
            echo "  bash scripts/start.sh --agent 1 --dry-run"
            exit 0
            ;;
        *) echo -e "${RED}❌ Unknown: $1${NC}"; exit 1 ;;
    esac
done

# ── Banner ──
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}🎬 MyShort — YouTube Kids Pipeline${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# ── Find .env ──
if [ -z "$ENV_FILE" ]; then
    ENV_SEARCH_PATHS=(
        "$HOME/.openclaw/.env-myshort"
        "$PROJECT_DIR/.env"
        "$HOME/.openclaw/.env"
    )
    for path in "${ENV_SEARCH_PATHS[@]}"; do
        if [ -f "$path" ]; then
            ENV_FILE="$path"
            break
        fi
    done
fi

if [ -z "$ENV_FILE" ] || [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}❌ Không tìm thấy file .env!${NC}"
    echo ""
    echo -e "${YELLOW}Chạy setup trước:${NC}"
    echo -e "  bash scripts/setup.sh"
    exit 1
fi

echo -e "${BLUE}📂 Loading: ${ENV_FILE}${NC}"

# ── Load .env ──
set -a
while IFS='=' read -r key value; do
    [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
    key=$(echo "$key" | xargs)
    value=$(echo "$value" | xargs)
    value="${value%\"}"
    value="${value#\"}"
    value="${value%\'}"
    value="${value#\'}"
    export "$key=$value"
done < "$ENV_FILE"
set +a

# ── Validate Keys ──
echo -e "${BLUE}🔍 Checking API keys...${NC}"

MISSING=0
check_var() {
    local var_name=$1
    local var_label=$2
    local required=$3
    local var_value="${!var_name}"

    if [ -z "$var_value" ] || [[ "$var_value" == *"your_"* ]] || [[ "$var_value" == *"_here"* ]]; then
        if [ "$required" = "required" ]; then
            echo -e "  ${RED}❌ ${var_label} (${var_name})${NC}"
            MISSING=$((MISSING + 1))
        else
            echo -e "  ${YELLOW}⚠️  ${var_label} (optional)${NC}"
        fi
    else
        local masked="${var_value:0:6}...${var_value: -4}"
        echo -e "  ${GREEN}✅ ${var_label}: ${masked}${NC}"
    fi
}

check_var "LLM_API_KEY"        "LLM API Key"     "required"
check_var "TELEGRAM_TOKEN"     "Telegram Token"   "required"
check_var "TELEGRAM_CHAT_ID"   "Telegram Chat ID" "required"
check_var "TAVILY_API_KEY"     "Tavily Search"    "required"
check_var "SUNO_API_KEY"       "Suno AI"          "optional"
check_var "GOOGLE_VEO_API_KEY" "Google Veo"       "optional"

echo ""

if [ $MISSING -gt 0 ]; then
    echo -e "${RED}❌ Thiếu ${MISSING} key bắt buộc!${NC}"
    echo -e "  nano $ENV_FILE"
    exit 1
fi

# ── Build Command ──
if [ -n "$AGENT" ]; then
    # Run single agent
    case $AGENT in
        1) CMD="python3 $PROJECT_DIR/trend-researcher/scripts/trend_researcher.py $DRY_RUN --json" ;;
        2) CMD="python3 $PROJECT_DIR/content-creator/scripts/content_creator.py $DRY_RUN --json" ;;
        3) CMD="python3 $PROJECT_DIR/music-maker/scripts/music_maker.py $DRY_RUN --json" ;;
        4) CMD="python3 $PROJECT_DIR/video-maker/scripts/video_maker.py $DRY_RUN --json" ;;
        5) CMD="python3 $PROJECT_DIR/video-aggregator/scripts/video_aggregator.py $DRY_RUN --json" ;;
        *) echo -e "${RED}❌ Agent phải từ 1-5${NC}"; exit 1 ;;
    esac
    echo -e "${BLUE}🎯 Chạy Agent $AGENT${NC}"
else
    # Full pipeline
    CMD="python3 $PROJECT_DIR/scripts/orchestrator.py --send-telegram $DRY_RUN"
    if [ -n "$TOPIC" ]; then
        CMD="$CMD --topic \"$TOPIC\""
    fi
    echo -e "${BLUE}🔄 Full pipeline${NC}"
fi

if [ -n "$TOPIC" ]; then
    echo -e "${BLUE}📝 Topic: ${TOPIC}${NC}"
fi
if [ -n "$DRY_RUN" ]; then
    echo -e "${YELLOW}🔸 Dry-run mode (không gọi API)${NC}"
fi
echo ""

# ── Run ──
if [ "$FOREGROUND" = true ]; then
    echo -e "${GREEN}🚀 Running in foreground...${NC}"
    echo ""
    eval $CMD
else
    echo -e "${YELLOW}📺 Screen session: ${SCREEN_NAME}${NC}"
    echo -e "${YELLOW}   Detach: Ctrl+A → D${NC}"
    echo -e "${YELLOW}   Attach: screen -r ${SCREEN_NAME}${NC}"
    echo -e "${YELLOW}   Kill:   screen -X -S ${SCREEN_NAME} quit${NC}"
    echo ""

    # Kill existing session if exists
    screen -X -S "$SCREEN_NAME" quit 2>/dev/null || true

    # Start new screen session
    screen -dmS "$SCREEN_NAME" bash -c "
        set -a
        source $ENV_FILE
        set +a
        cd $PROJECT_DIR
        $CMD
        echo ''
        echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
        echo '✅ Pipeline hoàn tất!'
        echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
        echo 'Nhấn Enter để đóng screen...'
        read
    "

    sleep 1
    echo -e "${GREEN}✅ Pipeline đang chạy trong background!${NC}"
    echo ""
    echo -e "📋 Commands:"
    echo -e "  screen -r ${SCREEN_NAME}             # Xem logs"
    echo -e "  screen -X -S ${SCREEN_NAME} quit     # Dừng pipeline"
    echo ""
fi
