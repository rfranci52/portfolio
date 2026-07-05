import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATABASE_URL = f"sqlite:///{DATA_DIR / 'portfolio.db'}"

# Load backend/.env if present (keeps secrets out of the shell / code).
load_dotenv(BASE_DIR / ".env")

# Email (Resend). Without these set, the contact form still works; it just
# saves to the DB and skips sending. See README for setup.
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
CONTACT_TO_EMAIL = os.environ.get("CONTACT_TO_EMAIL", "rakimfrancis@gmail.com")
# Until you verify your own domain in Resend, use their shared sender.
RESEND_FROM = os.environ.get("RESEND_FROM", "Portfolio <onboarding@resend.dev>")

# Origins allowed to call the API (the Vite dev server, plus same-origin prod).
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
