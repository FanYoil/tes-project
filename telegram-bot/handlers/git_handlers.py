"""
Git handlers — push/pull/status/init project dari terminal ke GitHub
Token GitHub otomatis di-inject ke remote URL supaya tidak perlu setup credential.
"""

import asyncio
import os
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from config import COMMAND_TIMEOUT
from utils.auth import is_admin, get_github_token, get_terminal_cwd, set_terminal_cwd, get_linked_repo, set_linked_repo
from utils.helpers import send_long_message, truncate


def _inject_token(url: str, token: str) -> str:
    """Sisipkan token ke HTTPS URL GitHub agar tidak perlu login."""
    if token and "github.com" in url and "@" not in url:
        url = url.replace("https://", f"https://{token}@")
    return url


async def _git_run(cwd: str, args: list[str], token: str = "", timeout: int = COMMAND_TIMEOUT) -> tuple[int, str]:
    """Jalankan perintah git dan return (returncode, output)."""
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    if token:
        env["GIT_ASKPASS"] = "echo"

    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=cwd,
        env=env,
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return -1, f"⏱️ Timeout setelah {timeout} detik."

    output = stdout.decode("utf-8", errors="replace").strip()
    return proc.returncode, output


def _check_admin(update: Update) -> bool:
    return is_admin(update.effective_user.id)


async def cmd_gitstatus(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _check_admin(update):
        await update.message.reply_text("⛔ Hanya admin yang bisa menggunakan fitur ini.")
        return

    user_id = update.effective_user.id
    cwd = get_terminal_cwd(user_id)

    rc, out = await _git_run(cwd, ["status"])
    if rc != 0 and "not a git repository" in out:
        await update.message.reply_text(
            f"❌ `{cwd}` bukan git repository.\n\nGunakan `/gitinit` untuk inisialisasi.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    text = f"📊 *Git Status* — `{cwd}`\n\n```\n{truncate(out, 3000)}\n```"
    await send_long_message(update, text, parse_mode=ParseMode.MARKDOWN)


async def cmd_gitlog(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _check_admin(update):
        await update.message.reply_text("⛔ Hanya admin yang bisa menggunakan fitur ini.")
        return

    user_id = update.effective_user.id
    cwd = get_terminal_cwd(user_id)
    n = ctx.args[0] if ctx.args and ctx.args[0].isdigit() else "10"

    rc, out = await _git_run(cwd, ["log", f"-{n}", "--oneline", "--decorate"])
    if rc != 0:
        await update.message.reply_text(f"❌ {truncate(out, 500)}", parse_mode=ParseMode.MARKDOWN)
        return

    text = f"📜 *Git Log* (terakhir {n}) — `{cwd}`\n\n```\n{truncate(out, 3000)}\n```"
    await send_long_message(update, text, parse_mode=ParseMode.MARKDOWN)


async def cmd_gitinit(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    /gitinit [owner/repo] — init git, set remote dengan token, lalu push.
    Jika owner/repo tidak diberikan, gunakan repo yang sedang ditautkan.
    """
    if not _check_admin(update):
        await update.message.reply_text("⛔ Hanya admin yang bisa menggunakan fitur ini.")
        return

    user_id = update.effective_user.id
    cwd = get_terminal_cwd(user_id)
    token = get_github_token(user_id)

    repo_arg = ctx.args[0] if ctx.args else None
    if not repo_arg:
        repo_arg = get_linked_repo(user_id)

    if not repo_arg:
        await update.message.reply_text(
            "📋 *Init & Push Project*\n\n"
            "Gunakan: `/gitinit <owner/repo>`\n"
            "Contoh: `/gitinit myuser/my-project`\n\n"
            "Perintah ini akan:\n"
            "1. `git init` di direktori terminal saat ini\n"
            "2. Set remote origin dengan token\n"
            "3. `git add .` → `git commit` → `git push`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if not token:
        await update.message.reply_text("❌ Token GitHub belum diset. Gunakan /settoken <token>")
        return

    remote_url = _inject_token(f"https://github.com/{repo_arg}.git", token)
    msg = await update.message.reply_text(
        f"🔧 Menginisialisasi git di `{cwd}`...",
        parse_mode=ParseMode.MARKDOWN,
    )

    steps = [
        (["init"], "git init"),
        (["config", "user.email", "bot@telegram.bot"], "config email"),
        (["config", "user.name", "Telegram Bot"], "config name"),
        (["remote", "remove", "origin"], None),
        (["remote", "add", "origin", remote_url], "set remote"),
        (["add", "."], "git add ."),
        (["commit", "-m", "Push via Telegram Bot"], "git commit"),
        (["branch", "-M", "main"], "set branch main"),
        (["push", "-u", "origin", "main", "--force"], "git push"),
    ]

    log_lines = []
    for git_args, label in steps:
        if label is None:
            await _git_run(cwd, git_args)
            continue
        rc, out = await _git_run(cwd, git_args, token=token)
        status = "✅" if rc == 0 else "⚠️"
        if out:
            log_lines.append(f"{status} {label}:\n{truncate(out, 300)}")
        else:
            log_lines.append(f"{status} {label}")
        if rc != 0 and label == "git push":
            log_lines.append("❌ Push gagal. Cek apakah repo sudah ada di GitHub.\nBuat dulu dengan /createrepo")
            break

    set_linked_repo(user_id, repo_arg)

    result_text = (
        f"🚀 *Git Init & Push* — `{cwd}`\n"
        f"📁 Repo: `{repo_arg}`\n\n"
        + "\n\n".join(log_lines)
    )
    await msg.delete()
    await send_long_message(update, result_text, parse_mode=ParseMode.MARKDOWN)


async def cmd_gitpush(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    /gitpush [pesan commit] — git add all, commit, push ke remote origin.
    Token otomatis di-inject ke URL jika diperlukan.
    """
    if not _check_admin(update):
        await update.message.reply_text("⛔ Hanya admin yang bisa menggunakan fitur ini.")
        return

    user_id = update.effective_user.id
    cwd = get_terminal_cwd(user_id)
    token = get_github_token(user_id)
    commit_msg = " ".join(ctx.args) if ctx.args else "Update via Telegram Bot"

    msg = await update.message.reply_text(
        f"⬆️ Mempersiapkan push dari `{cwd}`...",
        parse_mode=ParseMode.MARKDOWN,
    )

    # Cek apakah ini git repo
    rc, _ = await _git_run(cwd, ["rev-parse", "--git-dir"])
    if rc != 0:
        await msg.edit_text(
            f"❌ `{cwd}` bukan git repository.\n\n"
            "Gunakan `/gitinit <owner/repo>` untuk inisialisasi dan push pertama kali.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Inject token ke remote URL jika ada
    if token:
        rc_r, remote_url = await _git_run(cwd, ["remote", "get-url", "origin"])
        if rc_r == 0 and remote_url and "@" not in remote_url:
            new_url = _inject_token(remote_url.strip(), token)
            await _git_run(cwd, ["remote", "set-url", "origin", new_url])

    # Set git identity jika belum
    await _git_run(cwd, ["config", "user.email", "bot@telegram.bot"])
    await _git_run(cwd, ["config", "user.name", "Telegram Bot"])

    log_lines = []

    # git add .
    rc, out = await _git_run(cwd, ["add", "."])
    log_lines.append(f"{'✅' if rc == 0 else '❌'} git add .\n{truncate(out, 200) if out else ''}")

    # git commit
    rc, out = await _git_run(cwd, ["commit", "-m", commit_msg])
    if rc != 0:
        if "nothing to commit" in out or "nothing added" in out:
            await msg.edit_text(
                f"ℹ️ Tidak ada perubahan untuk di-commit.\n📂 `{cwd}`",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        log_lines.append(f"⚠️ git commit:\n{truncate(out, 300)}")
    else:
        log_lines.append(f"✅ git commit:\n{truncate(out, 300)}")

    # git push
    rc, out = await _git_run(cwd, ["push"], token=token, timeout=60)
    if rc != 0:
        # Coba push dengan set-upstream
        rc, out2 = await _git_run(
            cwd,
            ["push", "--set-upstream", "origin", "HEAD"],
            token=token,
            timeout=60,
        )
        if rc == 0:
            log_lines.append(f"✅ git push (upstream):\n{truncate(out2, 300)}")
        else:
            log_lines.append(f"❌ git push gagal:\n{truncate(out, 400)}")
    else:
        log_lines.append(f"✅ git push:\n{truncate(out, 300)}")

    # Ambil info repo dari remote
    _, remote_info = await _git_run(cwd, ["remote", "get-url", "origin"])
    repo_display = remote_info.strip().split("github.com/")[-1].replace(".git", "") if "github.com" in (remote_info or "") else cwd

    result = (
        f"{'✅' if rc == 0 else '❌'} *Git Push*\n"
        f"📁 `{cwd}`\n"
        f"📦 Repo: `{repo_display}`\n"
        f"💬 Commit: _{commit_msg}_\n\n"
        + "\n\n".join(l for l in log_lines if l.strip())
    )

    await msg.delete()
    await send_long_message(update, result, parse_mode=ParseMode.MARKDOWN)


async def cmd_gitpull(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    /gitpull — git pull dari remote origin dengan token otomatis.
    """
    if not _check_admin(update):
        await update.message.reply_text("⛔ Hanya admin yang bisa menggunakan fitur ini.")
        return

    user_id = update.effective_user.id
    cwd = get_terminal_cwd(user_id)
    token = get_github_token(user_id)

    # Inject token
    if token:
        rc_r, remote_url = await _git_run(cwd, ["remote", "get-url", "origin"])
        if rc_r == 0 and remote_url and "@" not in remote_url:
            await _git_run(cwd, ["remote", "set-url", "origin", _inject_token(remote_url.strip(), token)])

    msg = await update.message.reply_text(f"⬇️ Pulling dari origin...", parse_mode=ParseMode.MARKDOWN)
    rc, out = await _git_run(cwd, ["pull"], token=token, timeout=60)

    status = "✅" if rc == 0 else "❌"
    text = f"{status} *Git Pull* — `{cwd}`\n\n```\n{truncate(out, 2000)}\n```"
    await msg.delete()
    await send_long_message(update, text, parse_mode=ParseMode.MARKDOWN)


async def cmd_gitclone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    /gitclone <url_atau_owner/repo> [folder] — clone dengan token otomatis.
    """
    if not _check_admin(update):
        await update.message.reply_text("⛔ Hanya admin yang bisa menggunakan fitur ini.")
        return

    if not ctx.args:
        await update.message.reply_text(
            "🔄 *Git Clone*\n\n"
            "Gunakan:\n"
            "`/gitclone <url>` — clone dari URL\n"
            "`/gitclone owner/repo` — clone repo GitHub\n"
            "`/gitclone owner/repo folder` — clone ke folder tertentu",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    user_id = update.effective_user.id
    cwd = get_terminal_cwd(user_id)
    token = get_github_token(user_id)

    raw = ctx.args[0]
    # Kalau format owner/repo, jadikan URL lengkap
    if "/" in raw and not raw.startswith("http") and not raw.startswith("git@"):
        raw = f"https://github.com/{raw}.git"

    url = _inject_token(raw, token) if token else raw
    dest = ctx.args[1] if len(ctx.args) > 1 else ""

    git_args = ["clone", url] + ([dest] if dest else [])
    msg = await update.message.reply_text(
        f"🔄 Cloning `{ctx.args[0]}`...", parse_mode=ParseMode.MARKDOWN
    )

    rc, out = await _git_run(cwd, git_args, token=token, timeout=120)

    status = "✅" if rc == 0 else "❌"
    if rc == 0:
        cloned_dir = dest or ctx.args[0].split("/")[-1].replace(".git", "")
        new_cwd = os.path.join(cwd, cloned_dir)
        if os.path.isdir(new_cwd):
            set_terminal_cwd(user_id, new_cwd)
            text = (
                f"✅ Clone berhasil!\n"
                f"📂 Direktori pindah ke: `{new_cwd}`\n\n"
                f"```\n{truncate(out, 1000)}\n```"
            )
        else:
            text = f"✅ Clone berhasil!\n\n```\n{truncate(out, 1000)}\n```"
    else:
        text = f"❌ Clone gagal:\n\n```\n{truncate(out, 2000)}\n```"

    await msg.delete()
    await send_long_message(update, text, parse_mode=ParseMode.MARKDOWN)
