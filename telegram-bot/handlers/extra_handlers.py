"""
Extra GitHub features:
- Releases (scope: repo)
- Gists (scope: gist)
- Notifications (scope: notifications)
- Stars (scope: public_repo / repo)
- Follow/Unfollow (scope: user:follow)
- SSH Keys (scope: admin:public_key)
- User Emails (scope: user:email)
- Repository Contributors & Stats
"""

import io
import aiohttp
from github import Github, Auth
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from utils.auth import get_github_token, get_linked_repo
from utils.helpers import send_long_message, truncate, size_human


def get_gh(user_id: int) -> Github:
    token = get_github_token(user_id)
    if not token:
        raise ValueError("❌ Token GitHub belum diset. Gunakan /settoken <token>")
    return Github(auth=Auth.Token(token))


def _get_linked(user_id: int) -> str:
    linked = get_linked_repo(user_id)
    if not linked:
        raise ValueError("❌ Belum ada repo yang ditautkan. Gunakan /linkrepo <owner/repo>")
    return linked


# ─── RELEASES ────────────────────────────────────────────────────────────────

async def cmd_releases(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        g = get_gh(update.effective_user.id)
        if ctx.args and "/" in ctx.args[0]:
            repo_name = ctx.args[0]
        else:
            repo_name = _get_linked(update.effective_user.id)

        repo = g.get_repo(repo_name)
        releases = list(repo.get_releases()[:10])

        if not releases:
            await update.message.reply_text(f"📭 Tidak ada release di `{repo_name}`.", parse_mode=ParseMode.MARKDOWN)
            return

        lines = [f"🏷️ *Releases — {repo_name}*\n"]
        for r in releases:
            pre = " 🔧 pre-release" if r.prerelease else ""
            draft = " 📝 draft" if r.draft else ""
            date = r.created_at.strftime("%d %b %Y") if r.created_at else "—"
            assets = r.get_assets().totalCount
            lines.append(
                f"🏷️ `{r.tag_name}` *{r.title or r.tag_name}*{pre}{draft}\n"
                f"   📅 {date} | 📦 {assets} asset\n"
                f"   🔗 {r.html_url}"
            )

        await send_long_message(update, "\n\n".join(lines), parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_createrelease(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or len(ctx.args) < 2:
        await update.message.reply_text(
            "🏷️ *Buat Release*\n\n"
            "Gunakan: `/createrelease <tag> <judul> [body]`\n"
            "Contoh: `/createrelease v1.0.0 'Rilis Perdana' 'Ini versi pertama!'`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    try:
        repo_name = _get_linked(update.effective_user.id)
        g = get_gh(update.effective_user.id)
        repo = g.get_repo(repo_name)
        tag = ctx.args[0]
        title = ctx.args[1]
        body = " ".join(ctx.args[2:]) if len(ctx.args) > 2 else ""
        release = repo.create_git_release(tag=tag, name=title, message=body)
        await update.message.reply_text(
            f"✅ *Release Dibuat!*\n\n"
            f"🏷️ Tag: `{tag}`\n"
            f"📛 Judul: {title}\n"
            f"🔗 {release.html_url}",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ─── GISTS ───────────────────────────────────────────────────────────────────

async def cmd_gists(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        g = get_gh(update.effective_user.id)
        u = g.get_user()
        gists = list(u.get_gists()[:15])

        if not gists:
            await update.message.reply_text("📭 Tidak ada gist.")
            return

        lines = [f"📋 *Gists milik {u.login}*\n"]
        for gi in gists:
            desc = (gi.description or "—")[:50]
            pub = "🌐" if gi.public else "🔒"
            files = ", ".join(list(gi.files.keys())[:3])
            updated = gi.updated_at.strftime("%d/%m/%y") if gi.updated_at else "—"
            lines.append(f"{pub} `{gi.id[:8]}...` _{desc}_\n   📄 {files}\n   🔄 {updated}")

        await send_long_message(update, "\n\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_creategist(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or len(ctx.args) < 2:
        await update.message.reply_text(
            "📋 *Buat Gist*\n\n"
            "Gunakan: `/creategist <nama_file> <konten>`\n"
            "Contoh: `/creategist hello.py print('Hello World')`\n\n"
            "Atau kirim file dengan caption `/creategist`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    try:
        g = get_gh(update.effective_user.id)
        u = g.get_user()
        filename = ctx.args[0]
        content = " ".join(ctx.args[1:]).replace("\\n", "\n")
        from github import InputFileContent
        gist = u.create_gist(
            public=True,
            files={filename: InputFileContent(content)},
            description=f"Created via Telegram Bot",
        )
        await update.message.reply_text(
            f"✅ *Gist Dibuat!*\n\n"
            f"📄 File: `{filename}`\n"
            f"🔗 {gist.html_url}",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ─── NOTIFICATIONS ────────────────────────────────────────────────────────────

async def cmd_notifications(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        g = get_gh(update.effective_user.id)
        u = g.get_user()
        notifs = list(u.get_notifications()[:15])

        if not notifs:
            await update.message.reply_text("✅ Tidak ada notifikasi baru!")
            return

        type_emoji = {
            "Issue": "🐛", "PullRequest": "🔀", "Release": "🏷️",
            "RepositoryVulnerabilityAlert": "⚠️", "CheckSuite": "⚙️",
            "Commit": "📝", "Discussion": "💬",
        }
        lines = [f"🔔 *Notifikasi GitHub* ({len(notifs)})\n"]
        for n in notifs:
            emoji = type_emoji.get(n.subject.type, "📌")
            repo = n.repository.full_name if n.repository else "—"
            lines.append(f"{emoji} *{n.subject.type}* — `{repo}`\n   _{n.subject.title[:60]}_")

        await send_long_message(update, "\n\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_markread(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        g = get_gh(update.effective_user.id)
        u = g.get_user()
        u.mark_notifications_as_read()
        await update.message.reply_text("✅ Semua notifikasi ditandai sudah dibaca.")
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ─── STARS ───────────────────────────────────────────────────────────────────

async def cmd_star(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        g = get_gh(update.effective_user.id)
        if ctx.args and "/" in ctx.args[0]:
            repo_name = ctx.args[0]
        else:
            repo_name = _get_linked(update.effective_user.id)

        u = g.get_user()
        repo = g.get_repo(repo_name)
        u.add_to_starred(repo)
        await update.message.reply_text(f"⭐ Repository `{repo_name}` di-star!", parse_mode=ParseMode.MARKDOWN)
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_unstar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        g = get_gh(update.effective_user.id)
        if ctx.args and "/" in ctx.args[0]:
            repo_name = ctx.args[0]
        else:
            repo_name = _get_linked(update.effective_user.id)

        u = g.get_user()
        repo = g.get_repo(repo_name)
        u.remove_from_starred(repo)
        await update.message.reply_text(f"💫 Star dihapus dari `{repo_name}`.", parse_mode=ParseMode.MARKDOWN)
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_starred(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        g = get_gh(update.effective_user.id)
        if ctx.args:
            u = g.get_user(ctx.args[0])
        else:
            u = g.get_user()

        repos = list(u.get_starred()[:20])
        if not repos:
            await update.message.reply_text("📭 Tidak ada repo yang di-star.")
            return

        lines = [f"⭐ *Repo yang di-star oleh {u.login}*\n"]
        for r in repos:
            lang = r.language or "—"
            lines.append(f"• [{r.full_name}](https://github.com/{r.full_name}) [{lang}] ⭐{r.stargazers_count}")

        await send_long_message(update, "\n".join(lines), parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ─── FOLLOW / UNFOLLOW ───────────────────────────────────────────────────────

async def cmd_follow(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("👥 Gunakan: `/follow <username>`", parse_mode=ParseMode.MARKDOWN)
        return
    try:
        g = get_gh(update.effective_user.id)
        me = g.get_user()
        target = g.get_user(ctx.args[0])
        me.add_to_following(target)
        await update.message.reply_text(f"✅ Kamu sekarang mengikuti `{target.login}`.", parse_mode=ParseMode.MARKDOWN)
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_unfollow(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("👥 Gunakan: `/unfollow <username>`", parse_mode=ParseMode.MARKDOWN)
        return
    try:
        g = get_gh(update.effective_user.id)
        me = g.get_user()
        target = g.get_user(ctx.args[0])
        me.remove_from_following(target)
        await update.message.reply_text(f"✅ Kamu berhenti mengikuti `{target.login}`.", parse_mode=ParseMode.MARKDOWN)
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ─── SSH KEYS ────────────────────────────────────────────────────────────────

async def cmd_sshkeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        g = get_gh(update.effective_user.id)
        u = g.get_user()
        keys = list(u.get_keys())

        if not keys:
            await update.message.reply_text("🔑 Belum ada SSH key terdaftar.")
            return

        lines = [f"🔑 *SSH Keys — {u.login}* ({len(keys)} key)\n"]
        for k in keys:
            short = k.key.split()[-1][:20] if k.key else "—"
            key_type = k.key.split()[0] if k.key else "—"
            lines.append(f"• `{k.id}` *{k.title}*\n   `{key_type} ...{short}`")

        await update.message.reply_text("\n\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_addsshkey(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or len(ctx.args) < 2:
        await update.message.reply_text(
            "🔑 *Tambah SSH Key*\n\n"
            "Gunakan: `/addsshkey <judul> <public_key>`\n"
            "Contoh: `/addsshkey MyServer ssh-rsa AAAA...`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    try:
        g = get_gh(update.effective_user.id)
        u = g.get_user()
        title = ctx.args[0]
        key = " ".join(ctx.args[1:])
        u.create_key(title=title, key=key)
        await update.message.reply_text(f"✅ SSH Key `{title}` berhasil ditambahkan!", parse_mode=ParseMode.MARKDOWN)
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_deletesshkey(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or not ctx.args[0].isdigit():
        await update.message.reply_text("🗑️ Gunakan: `/deletesshkey <id>`\nLihat ID dengan `/sshkeys`", parse_mode=ParseMode.MARKDOWN)
        return
    try:
        g = get_gh(update.effective_user.id)
        u = g.get_user()
        key = u.get_key(int(ctx.args[0]))
        title = key.title
        key.delete()
        await update.message.reply_text(f"🗑️ SSH Key `{title}` dihapus.", parse_mode=ParseMode.MARKDOWN)
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ─── CONTRIBUTORS & STATS ────────────────────────────────────────────────────

async def cmd_contributors(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        g = get_gh(update.effective_user.id)
        if ctx.args and "/" in ctx.args[0]:
            repo_name = ctx.args[0]
        else:
            repo_name = _get_linked(update.effective_user.id)

        repo = g.get_repo(repo_name)
        contributors = list(repo.get_contributors()[:15])

        if not contributors:
            await update.message.reply_text("📭 Tidak ada kontributor.")
            return

        lines = [f"👥 *Kontributor — {repo_name}*\n"]
        for i, c in enumerate(contributors, 1):
            lines.append(f"{i}. `{c.login}` — {c.contributions} commit")

        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ─── FORK ────────────────────────────────────────────────────────────────────

async def cmd_fork(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or "/" not in ctx.args[0]:
        await update.message.reply_text("🍴 Gunakan: `/fork <owner/repo>`", parse_mode=ParseMode.MARKDOWN)
        return
    try:
        g = get_gh(update.effective_user.id)
        repo = g.get_repo(ctx.args[0])
        fork = repo.create_fork()
        await update.message.reply_text(
            f"🍴 *Fork berhasil!*\n\n"
            f"Dari: `{repo.full_name}`\n"
            f"Fork: `{fork.full_name}`\n"
            f"🔗 {fork.html_url}",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
