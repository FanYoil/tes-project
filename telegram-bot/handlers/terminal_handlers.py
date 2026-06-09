import os
import asyncio
import subprocess
import tempfile
import shlex
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from config import COMMAND_TIMEOUT, TERMINAL_WORKING_DIR
from utils.auth import is_admin, get_terminal_cwd, set_terminal_cwd
from utils.helpers import send_long_message, truncate


_user_sessions: dict[int, dict] = {}


def _get_session(user_id: int) -> dict:
    if user_id not in _user_sessions:
        cwd = get_terminal_cwd(user_id)
        os.makedirs(cwd, exist_ok=True)
        _user_sessions[user_id] = {"cwd": cwd, "env": dict(os.environ)}
    return _user_sessions[user_id]


async def _run_shell_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE, command: str):
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text(
            "⛔ Akses ditolak. Hanya admin yang dapat menggunakan terminal.\n"
            "Hubungi administrator bot untuk akses."
        )
        return

    if not command.strip():
        await update.message.reply_text("⚠️ Perintah tidak boleh kosong.")
        return

    session = _get_session(user_id)
    cwd = session["cwd"]

    os.makedirs(cwd, exist_ok=True)

    msg = await update.message.reply_text(
        f"⏳ Menjalankan: `{truncate(command, 100)}`",
        parse_mode=ParseMode.MARKDOWN,
    )

    if command.strip().startswith("cd "):
        new_dir = command.strip()[3:].strip()
        if new_dir == "~":
            new_dir = os.path.expanduser("~")
        elif not os.path.isabs(new_dir):
            new_dir = os.path.join(cwd, new_dir)
        new_dir = os.path.normpath(new_dir)
        if os.path.isdir(new_dir):
            session["cwd"] = new_dir
            set_terminal_cwd(user_id, new_dir)
            await msg.edit_text(f"📂 Direktori diubah ke: `{new_dir}`", parse_mode=ParseMode.MARKDOWN)
        else:
            await msg.edit_text(f"❌ Direktori tidak ditemukan: `{new_dir}`", parse_mode=ParseMode.MARKDOWN)
        return

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=cwd,
            env=session["env"],
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=COMMAND_TIMEOUT)
        except asyncio.TimeoutError:
            proc.kill()
            await msg.edit_text(
                f"⏱️ Timeout! Perintah melebihi {COMMAND_TIMEOUT} detik.\n"
                f"Command: `{truncate(command, 100)}`",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        output = stdout.decode("utf-8", errors="replace") if stdout else ""
        return_code = proc.returncode

        header = f"{'✅' if return_code == 0 else '❌'} `{truncate(command, 80)}`\n📂 `{cwd}`\n"

        if output.strip():
            formatted = f"{header}\n```\n{truncate(output, 3500)}\n```"
        else:
            formatted = f"{header}\n_(tidak ada output)_"

        await msg.delete()
        await send_long_message(update, formatted, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        await msg.edit_text(f"❌ Error menjalankan perintah: {e}")


async def cmd_shell(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        user_id = update.effective_user.id
        session = _get_session(user_id)
        await update.message.reply_text(
            "🖥️ *Terminal Aktif*\n\n"
            f"📂 CWD: `{session['cwd']}`\n\n"
            "Gunakan: `/shell <perintah>`\n"
            "Contoh:\n"
            "`/shell ls -la`\n"
            "`/shell python3 script.py`\n"
            "`/shell git status`\n\n"
            "Perintah lain:\n"
            "• `/cwd` — lihat direktori saat ini\n"
            "• `/cd <path>` — ganti direktori\n"
            "• `/upload_script` — upload & jalankan script",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    command = " ".join(ctx.args)
    await _run_shell_cmd(update, ctx, command)


async def cmd_shell_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text or ""
    if not is_admin(user_id):
        return
    command = text.strip()
    if command:
        await _run_shell_cmd(update, ctx, command)


async def cmd_cd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Akses ditolak.")
        return
    if not ctx.args:
        session = _get_session(user_id)
        await update.message.reply_text(f"📂 CWD: `{session['cwd']}`", parse_mode=ParseMode.MARKDOWN)
        return
    path = " ".join(ctx.args)
    ctx.args = [f"cd {path}"]
    session = _get_session(user_id)
    cwd = session["cwd"]
    if path == "~":
        new_dir = os.path.expanduser("~")
    elif not os.path.isabs(path):
        new_dir = os.path.join(cwd, path)
    else:
        new_dir = path
    new_dir = os.path.normpath(new_dir)
    if os.path.isdir(new_dir):
        session["cwd"] = new_dir
        set_terminal_cwd(user_id, new_dir)
        await update.message.reply_text(f"📂 Direktori: `{new_dir}`", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(f"❌ Tidak ditemukan: `{new_dir}`", parse_mode=ParseMode.MARKDOWN)


async def cmd_cwd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Akses ditolak.")
        return
    session = _get_session(user_id)
    await update.message.reply_text(f"📂 Direktori saat ini: `{session['cwd']}`", parse_mode=ParseMode.MARKDOWN)


async def cmd_upload_and_run(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Akses ditolak.")
        return
    if not update.message.document:
        await update.message.reply_text(
            "📤 *Upload & Jalankan Script*\n\n"
            "Kirim file script (.py, .sh, .js, dll) dengan caption perintah untuk menjalankannya.\n"
            "Contoh caption: `python3 script.py` atau `bash run.sh`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    session = _get_session(user_id)
    cwd = session["cwd"]
    doc = update.message.document
    caption = update.message.caption or ""

    file = await doc.get_file()
    filename = doc.file_name or "script"
    filepath = os.path.join(cwd, filename)

    await file.download_to_drive(filepath)
    await update.message.reply_text(f"✅ File `{filename}` tersimpan di `{cwd}`", parse_mode=ParseMode.MARKDOWN)

    if caption.strip():
        run_cmd = caption.strip()
        await _run_shell_cmd(update, ctx, run_cmd)


async def cmd_kill(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    await update.message.reply_text("⚠️ Tidak ada proses aktif yang bisa dihentikan saat ini.")


async def cmd_env(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Akses ditolak.")
        return

    if not ctx.args:
        await update.message.reply_text(
            "🔧 *Environment Variables*\n\n"
            "• `/env set KEY VALUE` — set variabel\n"
            "• `/env get KEY` — lihat variabel\n"
            "• `/env list` — list semua variabel custom",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    session = _get_session(user_id)
    subcmd = ctx.args[0].lower()

    if subcmd == "set" and len(ctx.args) >= 3:
        key, val = ctx.args[1], " ".join(ctx.args[2:])
        session["env"][key] = val
        await update.message.reply_text(f"✅ Set `{key}` = `{val}`", parse_mode=ParseMode.MARKDOWN)
    elif subcmd == "get" and len(ctx.args) >= 2:
        key = ctx.args[1]
        val = session["env"].get(key, "(tidak ada)")
        await update.message.reply_text(f"`{key}` = `{val}`", parse_mode=ParseMode.MARKDOWN)
    elif subcmd == "list":
        custom = {k: v for k, v in session["env"].items() if k not in os.environ}
        if custom:
            lines = [f"`{k}` = `{v}`" for k, v in list(custom.items())[:20]]
            await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("_(Tidak ada variabel custom)_", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("❌ Subperintah tidak dikenal.")
