import json
import aiohttp
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from config import OPENAI_API_KEY
from utils.auth import get_github_token
from utils.helpers import send_long_message, truncate


_chat_histories: dict[int, list] = {}


async def _call_github_copilot(token: str, messages: list) -> str:
    url = "https://api.githubcopilot.com/chat/completions"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Editor-Version": "vscode/1.85.0",
        "Editor-Plugin-Version": "copilot-chat/0.11.1",
        "Openai-Intent": "conversation-panel",
    }
    payload = {
        "model": "gpt-4o",
        "messages": messages,
        "stream": False,
        "temperature": 0.7,
        "max_tokens": 2048,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
            elif resp.status == 401:
                raise ValueError("❌ Token tidak memiliki akses GitHub Copilot.")
            else:
                text = await resp.text()
                raise ValueError(f"Copilot API error {resp.status}: {text[:200]}")


async def _call_openai(messages: list) -> str:
    if not OPENAI_API_KEY:
        raise ValueError("❌ OPENAI_API_KEY belum diset di .env")
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2048,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
            else:
                text = await resp.text()
                raise ValueError(f"OpenAI error {resp.status}: {text[:200]}")


async def cmd_ai(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not ctx.args:
        await update.message.reply_text(
            "🤖 *AI Assistant (GitHub Copilot)*\n\n"
            "Gunakan: `/ai <pertanyaan>`\n\n"
            "Contoh:\n"
            "`/ai Bagaimana cara membuat REST API dengan Flask?`\n"
            "`/ai Perbaiki bug di kode ini: ...`\n\n"
            "Perintah lain:\n"
            "• `/aiclear` — hapus riwayat chat\n"
            "• `/aicode <kode>` — review kode\n\n"
            "_Menggunakan GitHub Copilot (butuh token dengan akses Copilot)_",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    question = " ".join(ctx.args)
    await _process_ai(update, user_id, question)


async def _process_ai(update: Update, user_id: int, question: str):
    if user_id not in _chat_histories:
        _chat_histories[user_id] = [
            {
                "role": "system",
                "content": (
                    "Kamu adalah asisten AI yang helpful, berpengetahuan luas tentang programming, "
                    "GitHub, dan teknologi. Jawab dalam bahasa yang sama dengan pertanyaan pengguna. "
                    "Untuk kode, selalu gunakan markdown code blocks."
                ),
            }
        ]

    _chat_histories[user_id].append({"role": "user", "content": question})

    if len(_chat_histories[user_id]) > 21:
        system_msg = _chat_histories[user_id][0]
        _chat_histories[user_id] = [system_msg] + _chat_histories[user_id][-20:]

    msg = await update.message.reply_text("🤖 Sedang berpikir...")

    try:
        token = get_github_token(user_id)
        if token:
            try:
                answer = await _call_github_copilot(token, _chat_histories[user_id])
            except Exception:
                answer = await _call_openai(_chat_histories[user_id])
        else:
            answer = await _call_openai(_chat_histories[user_id])

        _chat_histories[user_id].append({"role": "assistant", "content": answer})

        await msg.delete()
        await send_long_message(update, f"🤖 *AI:*\n\n{answer}", parse_mode=ParseMode.MARKDOWN)

    except ValueError as e:
        _chat_histories[user_id].pop()
        await msg.edit_text(str(e))
    except Exception as e:
        _chat_histories[user_id].pop()
        await msg.edit_text(f"❌ Error AI: {e}")


async def cmd_aiclear(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    _chat_histories.pop(user_id, None)
    await update.message.reply_text("🗑️ Riwayat chat AI dihapus.")


async def cmd_aicode(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text(
            "💻 *Review Kode*\n\nGunakan: `/aicode <kode>`\n\n"
            "Atau kirim kode langsung setelah `/aicode`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    code = " ".join(ctx.args)
    question = (
        f"Tolong review kode berikut, temukan bug, dan berikan saran perbaikan:\n\n```\n{code}\n```"
    )
    await _process_ai(update, update.effective_user.id, question)


async def cmd_explain(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("❓ Gunakan: `/explain <kode atau konsep>`")
        return
    topic = " ".join(ctx.args)
    question = f"Tolong jelaskan dengan mudah: {topic}"
    await _process_ai(update, update.effective_user.id, question)


async def cmd_generate(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("✨ Gunakan: `/generate <deskripsi kode yang diinginkan>`")
        return
    desc = " ".join(ctx.args)
    question = f"Buatkan kode untuk: {desc}. Berikan kode lengkap yang siap dipakai."
    await _process_ai(update, update.effective_user.id, question)
