"""
Issues & Pull Requests handlers
Butuh scope: repo
"""

from github import Github, GithubException, Auth
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from utils.auth import get_github_token, get_linked_repo
from utils.helpers import send_long_message, truncate


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


# ─── ISSUES ──────────────────────────────────────────────────────────────────

async def cmd_issues(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        g = get_gh(update.effective_user.id)
        if ctx.args and "/" in ctx.args[0]:
            repo_name = ctx.args[0]
        else:
            repo_name = _get_linked(update.effective_user.id)

        state = "open"
        if ctx.args and ctx.args[-1].lower() in ("closed", "all"):
            state = ctx.args[-1].lower()

        repo = g.get_repo(repo_name)
        issues = [i for i in repo.get_issues(state=state) if i.pull_request is None][:20]

        if not issues:
            await update.message.reply_text(f"📭 Tidak ada issue {state} di `{repo_name}`.", parse_mode=ParseMode.MARKDOWN)
            return

        emoji = {"open": "🟢", "closed": "🔴", "all": "📋"}
        lines = [f"{emoji.get(state, '📋')} *Issues ({state}) — {repo_name}*\n"]
        for i in issues:
            labels = ", ".join(l.name for l in i.labels) if i.labels else ""
            label_str = f" [{labels}]" if labels else ""
            lines.append(f"#{i.number} {i.title}{label_str}\n   👤 {i.user.login} | 💬 {i.comments}")

        await send_long_message(update, "\n\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_createissue(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text(
            "🐛 *Buat Issue Baru*\n\n"
            "Gunakan: `/createissue <judul> | <body>`\n"
            "Contoh: `/createissue Bug login | Tidak bisa login dengan email`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    try:
        repo_name = _get_linked(update.effective_user.id)
        g = get_gh(update.effective_user.id)
        repo = g.get_repo(repo_name)

        full = " ".join(ctx.args)
        if "|" in full:
            title, body = [x.strip() for x in full.split("|", 1)]
        else:
            title, body = full, ""

        issue = repo.create_issue(title=title, body=body)
        await update.message.reply_text(
            f"✅ *Issue dibuat!*\n\n"
            f"#{issue.number} {issue.title}\n"
            f"🔗 {issue.html_url}",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_closeissue(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or not ctx.args[0].isdigit():
        await update.message.reply_text("🔒 Gunakan: `/closeissue <nomor>`\nContoh: `/closeissue 5`", parse_mode=ParseMode.MARKDOWN)
        return
    try:
        repo_name = _get_linked(update.effective_user.id)
        g = get_gh(update.effective_user.id)
        repo = g.get_repo(repo_name)
        issue = repo.get_issue(int(ctx.args[0]))
        issue.edit(state="closed")
        await update.message.reply_text(f"🔒 Issue #{issue.number} *{issue.title}* ditutup.", parse_mode=ParseMode.MARKDOWN)
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_commentissue(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or len(ctx.args) < 2:
        await update.message.reply_text("💬 Gunakan: `/commentissue <nomor> <komentar>`", parse_mode=ParseMode.MARKDOWN)
        return
    try:
        repo_name = _get_linked(update.effective_user.id)
        g = get_gh(update.effective_user.id)
        repo = g.get_repo(repo_name)
        number = int(ctx.args[0])
        comment = " ".join(ctx.args[1:])
        issue = repo.get_issue(number)
        c = issue.create_comment(comment)
        await update.message.reply_text(
            f"💬 Komentar ditambahkan ke Issue #{number}!\n🔗 {c.html_url}",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ─── PULL REQUESTS ────────────────────────────────────────────────────────────

async def cmd_prs(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        g = get_gh(update.effective_user.id)
        if ctx.args and "/" in ctx.args[0]:
            repo_name = ctx.args[0]
        else:
            repo_name = _get_linked(update.effective_user.id)

        state = "open"
        if ctx.args and ctx.args[-1].lower() in ("closed", "all"):
            state = ctx.args[-1].lower()

        repo = g.get_repo(repo_name)
        prs = list(repo.get_pulls(state=state))[:15]

        if not prs:
            await update.message.reply_text(f"📭 Tidak ada PR {state} di `{repo_name}`.", parse_mode=ParseMode.MARKDOWN)
            return

        lines = [f"🔀 *Pull Requests ({state}) — {repo_name}*\n"]
        for pr in prs:
            mergeable = "✅" if pr.mergeable else "⚠️" if pr.mergeable is False else "❓"
            lines.append(
                f"#{pr.number} {pr.title}\n"
                f"   🌿 `{pr.head.ref}` → `{pr.base.ref}` {mergeable}\n"
                f"   👤 {pr.user.login} | 💬 {pr.comments}"
            )

        await send_long_message(update, "\n\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_createpr(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or len(ctx.args) < 3:
        await update.message.reply_text(
            "🔀 *Buat Pull Request*\n\n"
            "Gunakan: `/createpr <head_branch> <base_branch> <judul>`\n"
            "Contoh: `/createpr feature/login main Tambah fitur login`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    try:
        repo_name = _get_linked(update.effective_user.id)
        g = get_gh(update.effective_user.id)
        repo = g.get_repo(repo_name)
        head = ctx.args[0]
        base = ctx.args[1]
        title = " ".join(ctx.args[2:])
        pr = repo.create_pull(title=title, body="", head=head, base=base)
        await update.message.reply_text(
            f"✅ *PR dibuat!*\n\n"
            f"#{pr.number} {pr.title}\n"
            f"🌿 `{head}` → `{base}`\n"
            f"🔗 {pr.html_url}",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_mergepr(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or not ctx.args[0].isdigit():
        await update.message.reply_text("🔀 Gunakan: `/mergepr <nomor_pr>`\nContoh: `/mergepr 3`", parse_mode=ParseMode.MARKDOWN)
        return
    try:
        repo_name = _get_linked(update.effective_user.id)
        g = get_gh(update.effective_user.id)
        repo = g.get_repo(repo_name)
        pr = repo.get_pull(int(ctx.args[0]))
        if not pr.mergeable:
            await update.message.reply_text(f"⚠️ PR #{pr.number} tidak bisa di-merge (conflict atau belum siap).")
            return
        merge_msg = " ".join(ctx.args[1:]) if len(ctx.args) > 1 else f"Merge PR #{pr.number}"
        result = pr.merge(commit_message=merge_msg)
        await update.message.reply_text(
            f"{'✅' if result.merged else '❌'} PR #{pr.number} *{pr.title}*\n"
            f"Status: {result.message}",
            parse_mode=ParseMode.MARKDOWN,
        )
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
