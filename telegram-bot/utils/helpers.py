import io
import textwrap
from config import MAX_MESSAGE_LENGTH


def split_message(text: str, max_len: int = MAX_MESSAGE_LENGTH) -> list[str]:
    if len(text) <= max_len:
        return [text]
    parts = []
    while text:
        if len(text) <= max_len:
            parts.append(text)
            break
        split_at = text.rfind("\n", 0, max_len)
        if split_at == -1:
            split_at = max_len
        parts.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return parts


def format_code(text: str, lang: str = "") -> str:
    return f"```{lang}\n{text}\n```"


def truncate(text: str, max_len: int = 3500) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + f"\n\n... [terpotong, total {len(text)} karakter]"


def size_human(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def escape_md(text: str) -> str:
    chars = r"\_*[]()~`>#+-=|{}.!"
    for c in chars:
        text = text.replace(c, f"\\{c}")
    return text


async def send_long_message(update, text: str, parse_mode=None):
    parts = split_message(text)
    for part in parts:
        await update.message.reply_text(part, parse_mode=parse_mode)
