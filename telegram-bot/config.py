import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_USER_IDS = [
    int(uid.strip())
    for uid in os.getenv("ADMIN_USER_IDS", "").split(",")
    if uid.strip().isdigit()
]
DEFAULT_GITHUB_TOKEN = os.getenv("DEFAULT_GITHUB_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
TERMINAL_WORKING_DIR = os.getenv("TERMINAL_WORKING_DIR", "/tmp/telegram-shell")
COMMAND_TIMEOUT = int(os.getenv("COMMAND_TIMEOUT", "30"))

MAX_MESSAGE_LENGTH = 4096
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

os.makedirs(TERMINAL_WORKING_DIR, exist_ok=True)
os.makedirs("data", exist_ok=True)
