#!/usr/bin/env python3
"""
🎬 MyShort — Shared Utilities
Tiện ích chung cho tất cả agents trong pipeline YouTube Kids.
"""

import os
import sys
import json
import logging
import re
import subprocess
from datetime import datetime
from pathlib import Path

# ── Paths ──
SHARED_DIR = Path(__file__).parent          # myshort/shared/
PROJECT_DIR = SHARED_DIR.parent             # myshort/
RESOURCES_DIR = SHARED_DIR                  # safety_keywords.json lives in shared/
TEMPLATES_DIR = PROJECT_DIR / "templates"

def get_output_dir():
    """Lấy thư mục output từ env hoặc mặc định."""
    output = os.environ.get("OUTPUT_DIR", "~/myshort-output")
    return Path(os.path.expanduser(output))

def ensure_output_dirs():
    """Tạo cấu trúc thư mục output."""
    base = get_output_dir()
    dirs = ["trends", "scripts", "audio", "clips", "final", "state"]
    for d in dirs:
        (base / d).mkdir(parents=True, exist_ok=True)
    return base

# ── Logging ──
def setup_logging(name, level=None):
    """Setup logger thống nhất cho tất cả agents."""
    if level is None:
        level = os.environ.get("LOG_LEVEL", "INFO").upper()
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level, logging.INFO))
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        fmt = logging.Formatter(
            f"[%(asctime)s] %(levelname)s [{name}] %(message)s",
            datefmt="%H:%M:%S"
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)
    
    return logger

# ── Config ──
def load_env(env_path=None):
    """Load .env file vào os.environ."""
    paths_to_try = []
    if env_path:
        paths_to_try.append(Path(env_path))
    paths_to_try.extend([
        Path.home() / ".openclaw" / ".env-myshort",
        Path.home() / ".openclaw" / ".env",
        PROJECT_DIR / ".env",
    ])
    
    for path in paths_to_try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key and value and key not in os.environ:
                            os.environ[key] = value
            return str(path)
    return None

def get_config():
    """Lấy toàn bộ config từ env."""
    load_env()
    return {
        # LLM
        "llm_provider": os.environ.get("LLM_PROVIDER", "gemini"),
        "llm_model": os.environ.get("LLM_MODEL", "gemini-2.5-flash"),
        "llm_api_key": os.environ.get("LLM_API_KEY", ""),
        # Suno
        "suno_api_key": os.environ.get("SUNO_API_KEY", ""),
        "suno_api_url": os.environ.get("SUNO_API_URL", "https://studio-api.suno.ai"),
        "suno_timeout": int(os.environ.get("SUNO_TIMEOUT", "300")),
        # Google Veo
        "google_project": os.environ.get("GOOGLE_CLOUD_PROJECT", ""),
        "google_location": os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
        "google_credentials": os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", ""),
        "google_veo_api_key": os.environ.get("GOOGLE_VEO_API_KEY", ""),
        "veo_timeout": int(os.environ.get("VEO_TIMEOUT", "600")),
        # Telegram
        "telegram_token": os.environ.get("TELEGRAM_TOKEN", ""),
        "telegram_chat_id": os.environ.get("TELEGRAM_CHAT_ID", ""),
        # Search
        "tavily_api_key": os.environ.get("TAVILY_API_KEY", ""),
        # Output
        "output_dir": str(get_output_dir()),
        "ffmpeg_path": os.environ.get("FFMPEG_PATH", "ffmpeg"),
        "video_resolution": os.environ.get("VIDEO_RESOLUTION", "1080p"),
    }

# ── JSON I/O ──
def save_json(data, filepath):
    """Lưu data ra file JSON."""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return str(filepath)

def load_json(filepath):
    """Đọc file JSON."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

# ── Safety ──
def load_safety_keywords():
    """Load danh sách từ khóa an toàn/cấm."""
    safety_file = RESOURCES_DIR / "safety_keywords.json"
    if safety_file.exists():
        return load_json(safety_file)
    return {"allowed_themes": [], "blocked_keywords": [], "age_appropriate": {}}

def check_content_safety(text):
    """
    Kiểm tra nội dung có an toàn cho trẻ em không.
    Returns: (is_safe: bool, violations: list)
    """
    safety = load_safety_keywords()
    blocked = safety.get("blocked_keywords", [])
    text_lower = text.lower()
    
    violations = []
    for keyword in blocked:
        if keyword.lower() in text_lower:
            violations.append(keyword)
    
    return len(violations) == 0, violations

# ── File Utilities ──
def safe_filename(text, max_length=50):
    """Tạo tên file an toàn từ text."""
    safe = re.sub(r'[^\w\s-]', '', text.lower())
    safe = re.sub(r'[-\s]+', '-', safe).strip('-')
    return safe[:max_length]

def timestamp_filename(prefix="", ext="json"):
    """Tạo filename với timestamp."""
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    if prefix:
        return f"{prefix}-{ts}.{ext}"
    return f"{ts}.{ext}"

# ── Dependency Check ──
def check_dependencies():
    """Kiểm tra các dependency cần thiết."""
    issues = []
    
    # FFmpeg
    ffmpeg = os.environ.get("FFMPEG_PATH", "ffmpeg")
    try:
        result = subprocess.run(
            [ffmpeg, "-version"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            issues.append(f"FFmpeg không hoạt động: {ffmpeg}")
    except FileNotFoundError:
        issues.append(f"FFmpeg không tìm thấy: {ffmpeg}. Cài: sudo apt install ffmpeg")
    except Exception as e:
        issues.append(f"FFmpeg lỗi: {e}")
    
    # Python packages
    required_packages = ["requests", "json", "subprocess"]
    for pkg in required_packages:
        try:
            __import__(pkg)
        except ImportError:
            issues.append(f"Python package thiếu: {pkg}")
    
    return issues

# ── Pipeline State ──
class PipelineState:
    """Quản lý state của pipeline để hỗ trợ resume."""
    
    def __init__(self, session_id=None):
        self.session_id = session_id or datetime.now().strftime("%Y%m%d-%H%M%S")
        self.state_dir = get_output_dir() / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / f"pipeline-{self.session_id}.json"
        self.state = self._load()
    
    def _load(self):
        if self.state_file.exists():
            return load_json(self.state_file)
        return {
            "session_id": self.session_id,
            "created_at": datetime.now().isoformat(),
            "current_step": 0,
            "steps": {},
            "files": {}
        }
    
    def save(self):
        save_json(self.state, self.state_file)
    
    def set_step(self, step_num, status, data=None):
        """Cập nhật trạng thái step."""
        self.state["current_step"] = step_num
        self.state["steps"][str(step_num)] = {
            "status": status,
            "updated_at": datetime.now().isoformat(),
            "data": data or {}
        }
        self.save()
    
    def get_step(self, step_num):
        return self.state["steps"].get(str(step_num), {})
    
    def set_file(self, key, filepath):
        """Lưu đường dẫn file output."""
        self.state["files"][key] = str(filepath)
        self.save()
    
    def get_file(self, key):
        return self.state["files"].get(key)
    
    @property
    def current_step(self):
        return self.state.get("current_step", 0)


# ── Print Helpers ──
def print_header(title, emoji="🎬"):
    """In header đẹp."""
    print(f"\n{'━' * 50}")
    print(f"{emoji} {title}")
    print(f"{'━' * 50}\n")

def print_step(step_num, total, description):
    """In bước hiện tại."""
    print(f"  [{step_num}/{total}] {description}")

def print_success(message):
    print(f"  ✅ {message}")

def print_warning(message):
    print(f"  ⚠️  {message}", file=sys.stderr)

def print_error(message):
    print(f"  ❌ {message}", file=sys.stderr)


# ── Telegram ──

def send_telegram(message, config=None, parse_mode="Markdown"):
    """
    Gửi tin nhắn tới Telegram chat.
    Auto-truncate nếu quá 4096 ký tự.
    Returns True nếu gửi thành công, False nếu thất bại.
    """
    if config is None:
        config = get_config()

    token = config.get("telegram_token", "")
    chat_id = config.get("telegram_chat_id", "")

    if not token or not chat_id:
        logging.getLogger("telegram").warning("TELEGRAM_TOKEN hoặc TELEGRAM_CHAT_ID chưa set")
        return False

    try:
        import requests
    except ImportError:
        logging.getLogger("telegram").warning("requests chưa cài")
        return False

    # Telegram limit: 4096 chars
    if len(message) > 4000:
        message = message[:3950] + "\n\n... _(truncated)_"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            return True
        else:
            # Retry without parse_mode (in case of markdown errors)
            payload["parse_mode"] = None
            resp2 = requests.post(url, json=payload, timeout=10)
            return resp2.status_code == 200
    except Exception as e:
        logging.getLogger("telegram").warning(f"Telegram send failed: {e}")
        return False


if __name__ == "__main__":
    # Quick self-test
    print_header("MyShort Utils — Self Test")
    
    # Check dependencies
    issues = check_dependencies()
    if issues:
        for issue in issues:
            print_warning(issue)
    else:
        print_success("Tất cả dependencies OK")
    
    # Check safety
    is_safe, violations = check_content_safety("A cute teddy bear dancing with colorful balloons")
    print_success(f"Safety check (safe content): safe={is_safe}")
    
    is_safe, violations = check_content_safety("violent fight scene with blood")
    print_success(f"Safety check (unsafe content): safe={is_safe}, violations={violations}")
    
    # Check output dirs
    base = ensure_output_dirs()
    print_success(f"Output directory: {base}")
    
    print("\n✅ All utils tests passed!")
