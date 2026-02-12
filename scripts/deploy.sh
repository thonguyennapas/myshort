#!/bin/bash
# ==============================================================================
# 🎬 MyShort — Deploy YouTube Kids Pipeline (Multi-Skill Architecture)
#
# Deploy 5 agent skills + shared + orchestrator vào ~/.openclaw/skills/
# ==============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

SKILLS_DIR="$HOME/.openclaw/skills"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SETUP_ENV=false

# Skills to deploy (mapping: source_folder → skill_name)
declare -A SKILL_MAP=(
    ["trend-researcher"]="kids-trend-researcher"
    ["content-creator"]="kids-content-creator"
    ["music-maker"]="kids-music-maker"
    ["video-maker"]="kids-video-maker"
    ["video-aggregator"]="kids-video-aggregator"
)

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --setup-env) SETUP_ENV=true; shift ;;
        --help|-h)
            echo "Usage: bash deploy.sh [--setup-env]"
            exit 0
            ;;
        *) echo -e "${RED}❌ Unknown: $1${NC}"; exit 1 ;;
    esac
done

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}🎬 MyShort — Multi-Skill Pipeline Deploy${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# ── Step 1: Deploy each agent skill ──
echo -e "${BLUE}[1/5] Deploy 5 agent skills...${NC}"

for source_folder in "${!SKILL_MAP[@]}"; do
    skill_name="${SKILL_MAP[$source_folder]}"
    target="$SKILLS_DIR/$skill_name"
    source="$PROJECT_DIR/$source_folder"
    
    if [ -d "$source" ]; then
        mkdir -p "$target"
        cp -r "$source/SKILL.md" "$target/"
        cp -r "$source/scripts" "$target/"
        echo -e "  ${GREEN}✅ $skill_name${NC}"
    else
        echo -e "  ${YELLOW}⚠️  $source_folder — không tìm thấy${NC}"
    fi
done

# ── Step 2: Deploy shared + orchestrator ──
echo ""
echo -e "${BLUE}[2/5] Deploy shared utilities + orchestrator...${NC}"

# Pipeline overview skill
PIPELINE_TARGET="$SKILLS_DIR/youtube-kids-pipeline"
mkdir -p "$PIPELINE_TARGET/scripts"
mkdir -p "$PIPELINE_TARGET/shared"

cp "$PROJECT_DIR/SKILL.md" "$PIPELINE_TARGET/"
cp "$PROJECT_DIR/scripts/orchestrator.py" "$PIPELINE_TARGET/scripts/"
cp -r "$PROJECT_DIR/shared/"* "$PIPELINE_TARGET/shared/"

# Also copy shared to each skill's parent for imports
for skill_name in "${SKILL_MAP[@]}"; do
    cp -r "$PROJECT_DIR/shared" "$SKILLS_DIR/$skill_name/../shared" 2>/dev/null || true
done

# Ensure shared is accessible from skills dir
cp -r "$PROJECT_DIR/shared" "$SKILLS_DIR/myshort-shared" 2>/dev/null || true

echo -e "  ${GREEN}✅ youtube-kids-pipeline (orchestrator)${NC}"
echo -e "  ${GREEN}✅ shared utilities${NC}"

# ── Step 3: Fix permissions ──
echo ""
echo -e "${BLUE}[3/5] Fix permissions...${NC}"

if command -v dos2unix &>/dev/null; then
    find "$SKILLS_DIR/kids-"* "$PIPELINE_TARGET" -type f \( -name "*.md" -o -name "*.py" -o -name "*.sh" -o -name "*.json" \) -exec dos2unix {} \; 2>/dev/null
    echo -e "  ${GREEN}✅ Line endings fixed${NC}"
fi

find "$SKILLS_DIR/kids-"* "$PIPELINE_TARGET" -name "*.py" -exec chmod +x {} \;
find "$SKILLS_DIR/kids-"* "$PIPELINE_TARGET" -name "*.sh" -exec chmod +x {} \;
echo -e "  ${GREEN}✅ Permissions set${NC}"

# ── Step 4: Dependencies ──
echo ""
echo -e "${BLUE}[4/5] Dependencies...${NC}"

PIP_FLAGS=""
if pip install --help 2>&1 | grep -q "break-system-packages"; then
    PIP_FLAGS="--break-system-packages"
fi

for pkg in requests ddgs; do
    pip install $PIP_FLAGS "$pkg" 2>/dev/null && echo -e "  ${GREEN}✅ $pkg${NC}" || true
done

if command -v ffmpeg &>/dev/null; then
    echo -e "  ${GREEN}✅ FFmpeg installed${NC}"
else
    echo -e "  ${RED}❌ FFmpeg missing! sudo apt install ffmpeg${NC}"
fi

# ── Step 5: .env ──
echo ""
echo -e "${BLUE}[5/5] .env...${NC}"

ENV_TARGET="$HOME/.openclaw/.env-myshort"
if [ -f "$ENV_TARGET" ]; then
    echo -e "  ${GREEN}✅ .env exists: $ENV_TARGET${NC}"
elif [ "$SETUP_ENV" = true ]; then
    cp "$PROJECT_DIR/.env.example" "$ENV_TARGET"
    read -p "  SUNO_API_KEY: " v; [ -n "$v" ] && sed -i "s|SUNO_API_KEY=.*|SUNO_API_KEY=$v|" "$ENV_TARGET"
    read -p "  GOOGLE_VEO_API_KEY: " v; [ -n "$v" ] && sed -i "s|GOOGLE_VEO_API_KEY=.*|GOOGLE_VEO_API_KEY=$v|" "$ENV_TARGET"
    read -p "  TELEGRAM_TOKEN: " v; [ -n "$v" ] && sed -i "s|TELEGRAM_TOKEN=.*|TELEGRAM_TOKEN=$v|" "$ENV_TARGET"
    read -p "  TELEGRAM_CHAT_ID: " v; [ -n "$v" ] && sed -i "s|TELEGRAM_CHAT_ID=.*|TELEGRAM_CHAT_ID=$v|" "$ENV_TARGET"
    read -p "  LLM_API_KEY: " v; [ -n "$v" ] && sed -i "s|LLM_API_KEY=.*|LLM_API_KEY=$v|" "$ENV_TARGET"
    echo -e "  ${GREEN}✅ .env created${NC}"
else
    echo -e "  ${YELLOW}⚠️  Run: bash deploy.sh --setup-env${NC}"
fi

# ── Done ──
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ DEPLOY HOÀN TẤT!${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "📋 Skills đã cài:"
for skill_name in "${SKILL_MAP[@]}"; do
    echo "  ✅ $skill_name"
done
echo "  ✅ youtube-kids-pipeline (orchestrator)"
echo ""
echo -e "📌 Test: python3 $PIPELINE_TARGET/scripts/orchestrator.py --dry-run"
echo ""
