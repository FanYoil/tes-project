"""
GitHub Actions handlers
Butuh scope: repo, workflow
"""

from github import Github, Auth
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


async def cmd_workflows(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        g = get_gh(update.effective_user.id)
        if ctx.args and "/" in ctx.args[0]:
            repo_name = ctx.args[0]
        else:
            repo_name = _get_linked(update.effective_user.id)

        repo = g.get_repo(repo_name)
        workflows = list(repo.get_workflows())

        if not workflows:
            await update.message.reply_text(f"📭 Tidak ada workflow di `{repo_name}`.", parse_mode=ParseMode.MARKDOWN)
            return

        lines = [f"⚙️ *GitHub Actions — {repo_name}*\n"]
        for wf in workflows:
            state_emoji = "✅" if wf.state == "active" else "⏸️"
            lines.append(f"{state_emoji} `{wf.id}` {wf.name}\n   📄 `{wf.path}`")

        await send_long_message(update, "\n\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_workflowruns(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        g = get_gh(update.effective_user.id)
        repo_name = _get_linked(update.effective_user.id)
        repo = g.get_repo(repo_name)

        runs = list(repo.get_workflow_runs()[:10])
        if not runs:
            await update.message.reply_text("📭 Tidak ada workflow run.")
            return

        status_emoji = {
            "completed": "✅", "in_progress": "🔄", "queued": "⏳",
            "failure": "❌", "cancelled": "🚫", "skipped": "⏭️",
            "success": "✅", "timed_out": "⏱️",
        }

        lines = [f"🏃 *Workflow Runs — {repo_name}*\n"]
        for run in runs:
            emoji = status_emoji.get(run.conclusion or run.status, "❓")
            date = run.created_at.strftime("%d/%m %H:%M") if run.created_at else "—"
            lines.append(
                f"{emoji} `#{run.run_number}` {run.name}\n"
                f"   🌿 `{run.head_branch}` | {date}\n"
                f"   Status: {run.status} / {run.conclusion or '—'}"
            )

        await send_long_message(update, "\n\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_runworkflow(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text(
            "▶️ *Jalankan Workflow*\n\n"
            "Gunakan: `/runworkflow <workflow_id_atau_nama.yml>`\n"
            "Contoh: `/runworkflow ci.yml`\n\n"
            "Lihat daftar workflow: `/workflows`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    try:
        g = get_gh(update.effective_user.id)
        repo_name = _get_linked(update.effective_user.id)
        repo = g.get_repo(repo_name)
        wf_id = ctx.args[0]
        branch = ctx.args[1] if len(ctx.args) > 1 else repo.default_branch

        try:
            wf_id_int = int(wf_id)
            wf = repo.get_workflow(wf_id_int)
        except ValueError:
            wf = repo.get_workflow(wf_id)

        result = wf.create_dispatch(ref=branch)
        if result:
            await update.message.reply_text(
                f"▶️ Workflow *{wf.name}* dijalankan di branch `{branch}`!\n"
                f"Lihat status: `/workflowruns`",
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await update.message.reply_text("⚠️ Gagal menjalankan workflow.")
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_branches(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        g = get_gh(update.effective_user.id)
        if ctx.args and "/" in ctx.args[0]:
            repo_name = ctx.args[0]
        else:
            repo_name = _get_linked(update.effective_user.id)

        repo = g.get_repo(repo_name)
        branches = list(repo.get_branches())
        default = repo.default_branch

        if not branches:
            await update.message.reply_text("📭 Tidak ada branch.")
            return

        lines = [f"🌿 *Branches — {repo_name}*\n"]
        for b in branches:
            marker = " ← *default*" if b.name == default else ""
            protected = " 🔒" if b.protected else ""
            lines.append(f"• `{b.name}`{protected}{marker}")

        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_createbranch(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text(
            "🌿 Gunakan: `/createbranch <nama_branch> [dari_branch]`\n"
            "Contoh: `/createbranch feature/login main`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    try:
        repo_name = _get_linked(update.effective_user.id)
        g = get_gh(update.effective_user.id)
        repo = g.get_repo(repo_name)

        new_branch = ctx.args[0]
        from_branch = ctx.args[1] if len(ctx.args) > 1 else repo.default_branch

        source = repo.get_branch(from_branch)
        repo.create_git_ref(ref=f"refs/heads/{new_branch}", sha=source.commit.sha)
        await update.message.reply_text(
            f"✅ Branch `{new_branch}` dibuat dari `{from_branch}`!",
            parse_mode=ParseMode.MARKDOWN,
        )
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_deletebranch(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("🗑️ Gunakan: `/deletebranch <nama_branch>`", parse_mode=ParseMode.MARKDOWN)
        return
    try:
        repo_name = _get_linked(update.effective_user.id)
        g = get_gh(update.effective_user.id)
        repo = g.get_repo(repo_name)
        branch = ctx.args[0]
        ref = repo.get_git_ref(f"heads/{branch}")
        ref.delete()
        await update.message.reply_text(f"🗑️ Branch `{branch}` dihapus.", parse_mode=ParseMode.MARKDOWN)
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
