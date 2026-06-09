#!/usr/bin/env python3
"""
Telegram Bot: GitHub + Terminal + AI
Dibuat dengan python-telegram-bot v20+
"""

import logging
import sys
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode

from config import TELEGRAM_BOT_TOKEN, ADMIN_USER_IDS
from handlers.github_handlers import (
    cmd_settoken,
    cmd_removetoken,
    cmd_profile,
    cmd_listrepo,
    cmd_searchrepo,
    cmd_createrepo,
    cmd_linkrepo,
    cmd_browse,
    cmd_commits,
    cmd_downloadrepo,
    cmd_uploadfile,
    cmd_editfile,
    cmd_deletefile,
    cmd_changevisibility,
    cmd_renamerepo,
    cmd_repoinfo,
    cmd_clonerepo,
    cmd_pullrepo,
)
from handlers.terminal_handlers import (
    cmd_shell,
    cmd_cd,
    cmd_cwd,
    cmd_upload_and_run,
    cmd_kill,
    cmd_env,
)
from handlers.ai_handlers import (
    cmd_ai,
    cmd_aiclear,
    cmd_aicode,
    cmd_explain,
    cmd_generate,
)
from handlers.git_handlers import (
    cmd_gitstatus,
    cmd_gitlog,
    cmd_gitinit,
    cmd_gitpush,
    cmd_gitpull,
    cmd_gitclone,
)
from handlers.issues_handlers import (
    cmd_issues,
    cmd_createissue,
    cmd_closeissue,
    cmd_commentissue,
    cmd_prs,
    cmd_createpr,
    cmd_mergepr,
)
from handlers.actions_handlers import (
    cmd_workflows,
    cmd_workflowruns,
    cmd_runworkflow,
    cmd_branches,
    cmd_createbranch,
    cmd_deletebranch,
)
from handlers.extra_handlers import (
    cmd_releases,
    cmd_createrelease,
    cmd_gists,
    cmd_creategist,
    cmd_notifications,
    cmd_markread,
    cmd_star,
    cmd_unstar,
    cmd_starred,
    cmd_follow,
    cmd_unfollow,
    cmd_sshkeys,
    cmd_addsshkey,
    cmd_deletesshkey,
    cmd_contributors,
    cmd_fork,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_admin = user.id in ADMIN_USER_IDS
    admin_badge = " 👑 Admin" if is_admin else ""

    text = (
        f"👋 Halo, *{user.first_name}*{admin_badge}!\n\n"
        "🤖 *GitHub + Terminal + AI Bot*\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🔑 *Mulai:*\n"
        "• `/settoken <github_token>` — set token GitHub\n\n"
        "📁 *GitHub:*\n"
        "• `/profile` — profil GitHub\n"
        "• `/listrepo` — daftar repository\n"
        "• `/searchrepo <query>` — cari repo\n"
        "• `/linkrepo <owner/repo>` — tautkan repo\n"
        "• `/repoinfo` — info repo aktif\n"
        "• `/browse [path]` — jelajahi file\n"
        "• `/commits` — riwayat commit\n"
        "• `/createrepo <nama>` — buat repo baru\n"
        "• `/clonerepo <url>` — clone repo\n"
        "• `/downloadrepo` — download ZIP\n"
        "• `/upload` — upload file ke repo\n"
        "• `/editfile` — edit file repo\n"
        "• `/deletefile` — hapus file\n"
        "• `/visibility` — ubah visibility\n"
        "• `/renamerepo` — rename repo\n\n"
        "🐛 *Issues & PRs:*\n"
        "• `/issues` — lihat issues\n"
        "• `/createissue <judul>` — buat issue\n"
        "• `/prs` — lihat pull requests\n"
        "• `/createpr` — buat PR\n"
        "• `/mergepr <nomor>` — merge PR\n\n"
        "⚙️ *Actions & Branches:*\n"
        "• `/workflows` — daftar workflow\n"
        "• `/workflowruns` — status run\n"
        "• `/branches` — daftar branch\n"
        "• `/createbranch <nama>` — buat branch\n\n"
        "🎁 *Releases, Gists & Lainnya:*\n"
        "• `/releases` — daftar release\n"
        "• `/createrelease` — buat release\n"
        "• `/gists` — lihat gist\n"
        "• `/notifications` — notifikasi\n"
        "• `/star` / `/unstar` — bintang repo\n"
        "• `/fork <owner/repo>` — fork repo\n"
        "• `/follow` / `/unfollow` — ikuti user\n"
        "• `/sshkeys` — daftar SSH key\n\n"
    )

    if is_admin:
        text += (
            "🖥️ *Terminal (Admin Only):*\n"
            "• `/shell <cmd>` — jalankan perintah\n"
            "• `/cd <path>` — pindah direktori\n"
            "• `/cwd` — direktori saat ini\n"
            "• `/env` — kelola env variables\n\n"
            "⬆️ *Git Push/Pull (Admin Only):*\n"
            "• `/gitpush [pesan]` — push project ke GitHub\n"
            "• `/gitpull` — pull dari remote\n"
            "• `/gitclone <url|owner/repo>` — clone repo\n"
            "• `/gitinit <owner/repo>` — init & push project baru\n"
            "• `/gitstatus` — lihat status git\n"
            "• `/gitlog` — riwayat commit\n\n"
        )

    text += (
        "🤖 *AI (GitHub Copilot):*\n"
        "• `/ai <pertanyaan>` — tanya AI\n"
        "• `/aicode <kode>` — review kode\n"
        "• `/explain <topik>` — penjelasan\n"
        "• `/generate <deskripsi>` — buat kode\n"
        "• `/aiclear` — reset riwayat AI\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📖 `/help` — bantuan lengkap"
    )

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_admin = user_id in ADMIN_USER_IDS

    text = (
        "📖 *Panduan Lengkap Bot*\n\n"
        "━━━ 🔑 AUTENTIKASI ━━━\n"
        "`/settoken <token>` — Set GitHub PAT\n"
        "`/removetoken` — Hapus token tersimpan\n\n"
        "━━━ 👤 PROFIL & REPO ━━━\n"
        "`/profile [username]` — Profil GitHub\n"
        "`/listrepo` — Daftar repo milikmu\n"
        "`/searchrepo <query>` — Cari repo di GitHub\n"
        "`/linkrepo <owner/repo>` — Tautkan repo aktif\n"
        "`/repoinfo [owner/repo]` — Detail repo\n\n"
        "━━━ 📁 MANAJEMEN FILE ━━━\n"
        "`/browse [path]` — Jelajahi file repo\n"
        "`/commits [repo]` — Lihat commit\n"
        "`/upload` — Upload file ke repo (kirim file dgn caption)\n"
        "`/editfile <path> <konten>` — Edit file\n"
        "`/deletefile <path>` — Hapus file\n\n"
        "━━━ 🏗️ MANAJEMEN REPO ━━━\n"
        "`/createrepo <nama> [desc] [private]` — Buat repo\n"
        "`/clonerepo <url>` — Clone repo via terminal\n"
        "`/downloadrepo [owner/repo]` — Download ZIP\n"
        "`/visibility <private|public>` — Ubah visibility\n"
        "`/renamerepo <nama_baru>` — Rename repo\n"
        "`/fork <owner/repo>` — Fork repo\n"
        "`/contributors` — Kontributor repo\n\n"
        "━━━ 🐛 ISSUES ━━━\n"
        "`/issues [closed]` — Daftar issues\n"
        "`/createissue <judul> | <body>` — Buat issue\n"
        "`/closeissue <nomor>` — Tutup issue\n"
        "`/commentissue <nomor> <komentar>` — Komentar issue\n\n"
        "━━━ 🔀 PULL REQUESTS ━━━\n"
        "`/prs [closed]` — Daftar pull requests\n"
        "`/createpr <head> <base> <judul>` — Buat PR\n"
        "`/mergepr <nomor>` — Merge PR\n\n"
        "━━━ ⚙️ ACTIONS & BRANCHES ━━━\n"
        "`/workflows` — Daftar GitHub Actions workflow\n"
        "`/workflowruns` — Status run terbaru\n"
        "`/runworkflow <file.yml>` — Jalankan workflow\n"
        "`/branches` — Daftar branch\n"
        "`/createbranch <nama> [dari]` — Buat branch\n"
        "`/deletebranch <nama>` — Hapus branch\n\n"
        "━━━ 🏷️ RELEASES ━━━\n"
        "`/releases` — Daftar release\n"
        "`/createrelease <tag> <judul>` — Buat release\n\n"
        "━━━ 📋 GISTS ━━━\n"
        "`/gists` — Daftar gist\n"
        "`/creategist <file> <konten>` — Buat gist\n\n"
        "━━━ 🔔 LAINNYA ━━━\n"
        "`/notifications` — Notifikasi GitHub\n"
        "`/markread` — Tandai semua dibaca\n"
        "`/star [owner/repo]` — Star repo\n"
        "`/unstar [owner/repo]` — Hapus star\n"
        "`/starred [username]` — Repo yang di-star\n"
        "`/follow <username>` — Follow user\n"
        "`/unfollow <username>` — Unfollow user\n"
        "`/sshkeys` — Daftar SSH key\n"
        "`/addsshkey <judul> <key>` — Tambah SSH key\n"
        "`/deletesshkey <id>` — Hapus SSH key\n\n"
    )

    if is_admin:
        text += (
            "━━━ 🖥️ TERMINAL ━━━\n"
            "`/shell <cmd>` — Jalankan perintah shell\n"
            "`/cd <path>` — Pindah direktori\n"
            "`/cwd` — Tampilkan direktori saat ini\n"
            "`/env set KEY VALUE` — Set env var\n"
            "`/env get KEY` — Lihat env var\n"
            "`/env list` — Daftar env var custom\n"
            "_Kirim file dgn caption perintah untuk upload & run_\n\n"
            "━━━ ⬆️ GIT PUSH/PULL ━━━\n"
            "`/gitpush [pesan commit]` — Push project ke GitHub\n"
            "`/gitpull` — Pull dari remote origin\n"
            "`/gitclone <url|owner/repo>` — Clone dengan token otomatis\n"
            "`/gitinit <owner/repo>` — Init & push project baru ke repo\n"
            "`/gitstatus` — Git status di direktori aktif\n"
            "`/gitlog [n]` — Lihat n commit terakhir\n\n"
            "💡 _Token GitHub otomatis di-inject, tidak perlu setup credential!_\n\n"
        )

    text += (
        "━━━ 🤖 AI ASSISTANT ━━━\n"
        "`/ai <pertanyaan>` — Chat dengan AI\n"
        "`/aicode <kode>` — Review & debug kode\n"
        "`/explain <topik>` — Jelaskan konsep\n"
        "`/generate <deskripsi>` — Generate kode\n"
        "`/aiclear` — Reset riwayat percakapan AI\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🔗 Buat token: https://github.com/settings/tokens\n"
        "📋 Scope: `repo`, `user`, `delete_repo`"
    )

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def handle_document(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    caption = (update.message.caption or "").strip()
    user_id = update.effective_user.id

    if caption.startswith("/upload"):
        await cmd_uploadfile(update, ctx)
    elif caption and user_id in ADMIN_USER_IDS:
        await cmd_upload_and_run(update, ctx)
    else:
        await cmd_uploadfile(update, ctx)


async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    pass


async def error_handler(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Exception: {ctx.error}", exc_info=ctx.error)
    if isinstance(update, Update) and update.message:
        await update.message.reply_text(
            f"⚠️ Terjadi kesalahan: `{str(ctx.error)[:200]}`",
            parse_mode=ParseMode.MARKDOWN,
        )


async def post_init(app: Application):
    commands = [
        BotCommand("start", "Mulai bot"),
        BotCommand("help", "Bantuan lengkap"),
        BotCommand("settoken", "Set GitHub token"),
        BotCommand("profile", "Profil GitHub"),
        BotCommand("listrepo", "Daftar repository"),
        BotCommand("searchrepo", "Cari repository"),
        BotCommand("linkrepo", "Tautkan repository"),
        BotCommand("repoinfo", "Info repository"),
        BotCommand("browse", "Jelajahi file repo"),
        BotCommand("commits", "Riwayat commit"),
        BotCommand("createrepo", "Buat repository baru"),
        BotCommand("downloadrepo", "Download repo sebagai ZIP"),
        BotCommand("upload", "Upload file ke repo"),
        BotCommand("editfile", "Edit file di repo"),
        BotCommand("deletefile", "Hapus file di repo"),
        BotCommand("visibility", "Ubah visibility repo"),
        BotCommand("renamerepo", "Rename repository"),
        BotCommand("clonerepo", "Clone repository"),
        BotCommand("gitpush", "Push project terminal ke GitHub"),
        BotCommand("gitpull", "Pull dari remote GitHub"),
        BotCommand("gitclone", "Clone repo dengan token otomatis"),
        BotCommand("gitinit", "Init & push project baru ke GitHub"),
        BotCommand("gitstatus", "Git status direktori aktif"),
        BotCommand("gitlog", "Riwayat commit git"),
        BotCommand("issues", "Daftar issues"),
        BotCommand("createissue", "Buat issue baru"),
        BotCommand("closeissue", "Tutup issue"),
        BotCommand("commentissue", "Komentar di issue"),
        BotCommand("prs", "Daftar pull requests"),
        BotCommand("createpr", "Buat pull request"),
        BotCommand("mergepr", "Merge pull request"),
        BotCommand("workflows", "Daftar GitHub Actions"),
        BotCommand("workflowruns", "Status workflow run"),
        BotCommand("runworkflow", "Jalankan workflow"),
        BotCommand("branches", "Daftar branch"),
        BotCommand("createbranch", "Buat branch baru"),
        BotCommand("deletebranch", "Hapus branch"),
        BotCommand("releases", "Daftar release"),
        BotCommand("createrelease", "Buat release baru"),
        BotCommand("gists", "Daftar gist"),
        BotCommand("creategist", "Buat gist baru"),
        BotCommand("notifications", "Notifikasi GitHub"),
        BotCommand("markread", "Tandai notifikasi dibaca"),
        BotCommand("star", "Star repository"),
        BotCommand("unstar", "Hapus star repository"),
        BotCommand("starred", "Repo yang di-star"),
        BotCommand("fork", "Fork repository"),
        BotCommand("contributors", "Kontributor repo"),
        BotCommand("follow", "Follow user GitHub"),
        BotCommand("unfollow", "Unfollow user GitHub"),
        BotCommand("sshkeys", "Daftar SSH key"),
        BotCommand("addsshkey", "Tambah SSH key"),
        BotCommand("deletesshkey", "Hapus SSH key"),
        BotCommand("shell", "Jalankan perintah terminal"),
        BotCommand("cd", "Pindah direktori terminal"),
        BotCommand("cwd", "Lihat direktori terminal saat ini"),
        BotCommand("env", "Kelola environment variables"),
        BotCommand("ai", "Tanya AI / GitHub Copilot"),
        BotCommand("aicode", "Review kode dengan AI"),
        BotCommand("explain", "Jelaskan kode atau konsep"),
        BotCommand("generate", "Generate kode dengan AI"),
        BotCommand("aiclear", "Reset riwayat chat AI"),
        BotCommand("removetoken", "Hapus GitHub token"),
    ]
    await app.bot.set_my_commands(commands)
    logger.info("✅ Bot berhasil diinisialisasi!")
    logger.info(f"👑 Admin IDs: {ADMIN_USER_IDS}")


def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN belum diset! Salin .env.example ke .env dan isi token.")
        sys.exit(1)

    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))

    app.add_handler(CommandHandler("settoken", cmd_settoken))
    app.add_handler(CommandHandler("removetoken", cmd_removetoken))

    app.add_handler(CommandHandler("profile", cmd_profile))
    app.add_handler(CommandHandler("listrepo", cmd_listrepo))
    app.add_handler(CommandHandler("searchrepo", cmd_searchrepo))
    app.add_handler(CommandHandler("createrepo", cmd_createrepo))
    app.add_handler(CommandHandler("linkrepo", cmd_linkrepo))
    app.add_handler(CommandHandler("browse", cmd_browse))
    app.add_handler(CommandHandler("commits", cmd_commits))
    app.add_handler(CommandHandler("downloadrepo", cmd_downloadrepo))
    app.add_handler(CommandHandler("clonerepo", cmd_clonerepo))
    app.add_handler(CommandHandler("pullrepo", cmd_pullrepo))
    app.add_handler(CommandHandler("upload", cmd_uploadfile))
    app.add_handler(CommandHandler("editfile", cmd_editfile))
    app.add_handler(CommandHandler("deletefile", cmd_deletefile))
    app.add_handler(CommandHandler("visibility", cmd_changevisibility))
    app.add_handler(CommandHandler("renamerepo", cmd_renamerepo))
    app.add_handler(CommandHandler("repoinfo", cmd_repoinfo))

    app.add_handler(CommandHandler("gitpush", cmd_gitpush))
    app.add_handler(CommandHandler("gitpull", cmd_gitpull))
    app.add_handler(CommandHandler("gitclone", cmd_gitclone))
    app.add_handler(CommandHandler("gitinit", cmd_gitinit))
    app.add_handler(CommandHandler("gitstatus", cmd_gitstatus))
    app.add_handler(CommandHandler("gitlog", cmd_gitlog))

    app.add_handler(CommandHandler("issues", cmd_issues))
    app.add_handler(CommandHandler("createissue", cmd_createissue))
    app.add_handler(CommandHandler("closeissue", cmd_closeissue))
    app.add_handler(CommandHandler("commentissue", cmd_commentissue))
    app.add_handler(CommandHandler("prs", cmd_prs))
    app.add_handler(CommandHandler("createpr", cmd_createpr))
    app.add_handler(CommandHandler("mergepr", cmd_mergepr))

    app.add_handler(CommandHandler("workflows", cmd_workflows))
    app.add_handler(CommandHandler("workflowruns", cmd_workflowruns))
    app.add_handler(CommandHandler("runworkflow", cmd_runworkflow))
    app.add_handler(CommandHandler("branches", cmd_branches))
    app.add_handler(CommandHandler("createbranch", cmd_createbranch))
    app.add_handler(CommandHandler("deletebranch", cmd_deletebranch))

    app.add_handler(CommandHandler("releases", cmd_releases))
    app.add_handler(CommandHandler("createrelease", cmd_createrelease))
    app.add_handler(CommandHandler("gists", cmd_gists))
    app.add_handler(CommandHandler("creategist", cmd_creategist))
    app.add_handler(CommandHandler("notifications", cmd_notifications))
    app.add_handler(CommandHandler("markread", cmd_markread))
    app.add_handler(CommandHandler("star", cmd_star))
    app.add_handler(CommandHandler("unstar", cmd_unstar))
    app.add_handler(CommandHandler("starred", cmd_starred))
    app.add_handler(CommandHandler("fork", cmd_fork))
    app.add_handler(CommandHandler("contributors", cmd_contributors))
    app.add_handler(CommandHandler("follow", cmd_follow))
    app.add_handler(CommandHandler("unfollow", cmd_unfollow))
    app.add_handler(CommandHandler("sshkeys", cmd_sshkeys))
    app.add_handler(CommandHandler("addsshkey", cmd_addsshkey))
    app.add_handler(CommandHandler("deletesshkey", cmd_deletesshkey))

    app.add_handler(CommandHandler("shell", cmd_shell))
    app.add_handler(CommandHandler("sh", cmd_shell))
    app.add_handler(CommandHandler("cd", cmd_cd))
    app.add_handler(CommandHandler("cwd", cmd_cwd))
    app.add_handler(CommandHandler("env", cmd_env))
    app.add_handler(CommandHandler("kill", cmd_kill))

    app.add_handler(CommandHandler("ai", cmd_ai))
    app.add_handler(CommandHandler("aiclear", cmd_aiclear))
    app.add_handler(CommandHandler("aicode", cmd_aicode))
    app.add_handler(CommandHandler("explain", cmd_explain))
    app.add_handler(CommandHandler("generate", cmd_generate))

    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.PHOTO, cmd_uploadfile))

    app.add_error_handler(error_handler)

    logger.info("🚀 Bot sedang berjalan...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
