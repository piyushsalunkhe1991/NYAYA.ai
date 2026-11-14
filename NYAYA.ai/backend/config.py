"""Central configuration. Reads optional backend/.env without extra packages."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent


def _load_env() -> None:
    for p in (BASE_DIR / ".env", ROOT_DIR / ".env"):
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env()

# --- AI provider (OpenAI-compatible, anonymous by default) ---
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.llmfaucet.dev/v1").rstrip("/")
AI_MODEL = os.getenv("AI_MODEL", "auto")
AI_API_KEY = os.getenv("AI_API_KEY", "")  # stays on the server, never sent to the browser
AI_TIMEOUT = float(os.getenv("AI_TIMEOUT", "60"))

# --- App ---
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "database" / "nyaya.db"))
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@nyaya.ai").strip().lower()
MAX_UPLOAD_MB = 10
MAX_DOC_CHARS_TO_AI = 12000
FRONTEND_DIR = ROOT_DIR / "frontend"
DATA_DIR = BASE_DIR / "data"
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000,http://localhost:5500,http://127.0.0.1:5500",
    ).split(",")
    if o.strip()
]
