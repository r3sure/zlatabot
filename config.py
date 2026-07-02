import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

_token_path = BASE_DIR / "bot_token.txt"
if _token_path.exists():
    TELEGRAM_BOT_TOKEN = _token_path.read_text().strip()
else:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

PROXY = os.getenv("PROXY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")  # groq | deepseek
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()} or {799895805, 453933675}

DATABASE_PATH = BASE_DIR / "data" / "zlatabot.db"
