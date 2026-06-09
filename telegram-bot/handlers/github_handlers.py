import os
import io
import zipfile
import base64
import tempfile
import aiohttp
import aiofiles
from github import Github, GithubException, Auth
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from utils.auth import get_github_token, set_linked_repo, get_linked_repo
from utils.helpers import send_long_message, size_human, truncate, format_code


def get_gh(user_id: int) -> Github:
    token = get_github_token(user_id)
    if not token:
        raise ValueError("❌ Token GitHub belum diset. Gunakan /settoken <token>")
    return Github(auth=Auth.Token(token))


async def cmd_settoken(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not ctx.args:
        await update.message.reply_text(
            "🔑 *Set GitHub Token*\n\n"
            "Gunakan: `/settoken <personal_access_token>`\n\n"
            "Buat token di: https://github.com/settings/tokens\n"
            "Scope yang dibutuhkan: `repo`, `user`, `delete_repo`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    token = ctx.args[0].strip()
    try:
        g = Github(auth=Auth.Token(token))
        user = g.get_user()
        _ = user.login
        from utils.auth import set_github_token
        set_github_token(user_id, token)
        await update.message.reply_text(
            f"✅ Token berhasil disimpan!\n👤 Login sebagai: `{user.login}`",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Token tidak valid: {e}")


async def cmd_removetoken(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    from utils.auth import remove_github_token
    remove_github_token(update.effective_user.id)
    await update.message.reply_text("✅ Token GitHub telah dihapus.")


async def cmd_profile(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        g = get_gh(update.effective_user.id)
        if ctx.args:
            u = g.get_user(ctx.args[0])
        else:
            u = g.get_user()

        repos = u.public_repos
        followers = u.followers
        following = u.following
        bio = u.bio or "—"
        company = u.company or "—"
        location = u.location or "—"
        blog = u.blog or "—"
        created = u.created_at.strftime("%d %b %Y") if u.created_at else "—"

        text = (
            f"👤 *Profil GitHub*\n\n"
            f"🔗 Login: `{u.login}`\n"
            f"📛 Nama: {u.name or '—'}\n"
            f"📝 Bio: {bio}\n"
            f"🏢 Perusahaan: {company}\n"
            f"📍 Lokasi: {location}\n"
            f"🌐 Blog: {blog}\n"
            f"📁 Repo Publik: {repos}\n"
            f"👥 Followers: {followers} | Following: {following}\n"
            f"📅 Bergabung: {created}\n"
            f"🔗 URL: https://github.com/{u.login}"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_listrepo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        g = get_gh(update.effective_user.id)
        u = g.get_user()
        repos = list(u.get_repos(sort="updated"))
        if not repos:
            await update.message.reply_text("📭 Tidak ada repository.")
            return

        lines = []
        for i, r in enumerate(repos[:30], 1):
            visibility = "🔒" if r.private else "🌐"
            lang = r.language or "—"
            lines.append(
                f"{i}. {visibility} `{r.name}` [{lang}] ⭐{r.stargazers_count}"
            )

        total = u.public_repos + (u.owned_private_repos or 0)
        text = f"📁 *Repository milik {u.login}* (total: {total})\n\n" + "\n".join(lines)
        if len(repos) > 30:
            text += f"\n\n_...dan {len(repos)-30} repo lainnya_"
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_searchrepo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("🔍 Gunakan: `/searchrepo <kata kunci>`", parse_mode=ParseMode.MARKDOWN)
        return
    query = " ".join(ctx.args)
    try:
        g = get_gh(update.effective_user.id)
        results = g.search_repositories(query=query, sort="stars", order="desc")
        repos = list(results[:15])
        if not repos:
            await update.message.reply_text("🔍 Tidak ada hasil ditemukan.")
            return
        lines = [f"🔍 *Hasil pencarian: `{query}`*\n"]
        for i, r in enumerate(repos, 1):
            visibility = "🔒" if r.private else "🌐"
            lang = r.language or "—"
            desc = (r.description or "")[:60]
            lines.append(
                f"{i}. {visibility} [{r.full_name}](https://github.com/{r.full_name})\n"
                f"   ⭐{r.stargazers_count} 🍴{r.forks_count} [{lang}]\n"
                f"   _{desc}_"
            )
        await update.message.reply_text(
            "\n\n".join(lines),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_createrepo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text(
            "🆕 *Buat Repository Baru*\n\n"
            "Gunakan: `/createrepo <nama> [deskripsi] [private/public]`\n"
            "Contoh: `/createrepo my-project 'Proyek keren' private`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    try:
        g = get_gh(update.effective_user.id)
        u = g.get_user()
        name = ctx.args[0]
        desc = ctx.args[1] if len(ctx.args) > 1 else ""
        is_private = ctx.args[-1].lower() == "private" if len(ctx.args) > 2 else False
        repo = u.create_repo(name=name, description=desc, private=is_private)
        visibility = "🔒 Private" if is_private else "🌐 Public"
        await update.message.reply_text(
            f"✅ *Repository Berhasil Dibuat!*\n\n"
            f"📁 Nama: `{repo.name}`\n"
            f"👁️ Visibility: {visibility}\n"
            f"🔗 URL: {repo.html_url}\n"
            f"📋 Clone: `git clone {repo.clone_url}`",
            parse_mode=ParseMode.MARKDOWN,
        )
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_linkrepo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        linked = get_linked_repo(update.effective_user.id)
        if linked:
            await update.message.reply_text(f"🔗 Repo aktif: `{linked}`\nGunakan `/linkrepo <owner/repo>` untuk ganti.", parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("🔗 Gunakan: `/linkrepo <owner/repo>`\nContoh: `/linkrepo octocat/Hello-World`", parse_mode=ParseMode.MARKDOWN)
        return
    repo_name = ctx.args[0]
    try:
        g = get_gh(update.effective_user.id)
        repo = g.get_repo(repo_name)
        set_linked_repo(update.effective_user.id, repo.full_name)
        await update.message.reply_text(
            f"✅ Repository ditautkan!\n🔗 `{repo.full_name}`\n⭐ {repo.stargazers_count} | 🍴 {repo.forks_count}",
            parse_mode=ParseMode.MARKDOWN,
        )
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


def _get_linked(user_id: int) -> str:
    linked = get_linked_repo(user_id)
    if not linked:
        raise ValueError("❌ Belum ada repo yang ditautkan. Gunakan /linkrepo <owner/repo>")
    return linked


async def cmd_browse(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        g = get_gh(update.effective_user.id)
        if ctx.args and "/" in ctx.args[0]:
            repo_name = ctx.args[0]
            path = " ".join(ctx.args[1:]) if len(ctx.args) > 1 else ""
        else:
            repo_name = _get_linked(update.effective_user.id)
            path = " ".join(ctx.args) if ctx.args else ""

        repo = g.get_repo(repo_name)
        contents = repo.get_contents(path)

        if isinstance(contents, list):
            dirs, files = [], []
            for c in contents:
                if c.type == "dir":
                    dirs.append(f"📁 `{c.name}/`")
                else:
                    size = size_human(c.size)
                    files.append(f"📄 `{c.name}` ({size})")
            lines = [f"📂 *{repo_name}/{path or ''}*\n"] + dirs + files
            await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
        else:
            if contents.encoding == "base64" and contents.size < 100_000:
                content = base64.b64decode(contents.content).decode("utf-8", errors="replace")
                text = f"📄 *{contents.name}* ({size_human(contents.size)})\n\n{format_code(truncate(content))}"
                await send_long_message(update, text, parse_mode=ParseMode.MARKDOWN)
            else:
                await update.message.reply_text(
                    f"📄 `{contents.name}` ({size_human(contents.size)})\n🔗 {contents.html_url}",
                    parse_mode=ParseMode.MARKDOWN,
                )
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_commits(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        g = get_gh(update.effective_user.id)
        if ctx.args and "/" in ctx.args[0]:
            repo_name = ctx.args[0]
        else:
            repo_name = _get_linked(update.effective_user.id)

        repo = g.get_repo(repo_name)
        commits = list(repo.get_commits()[:15])

        lines = [f"📝 *Commits: {repo_name}*\n"]
        for c in commits:
            sha = c.sha[:7]
            msg = c.commit.message.split("\n")[0][:60]
            author = c.commit.author.name[:20] if c.commit.author else "—"
            date = c.commit.author.date.strftime("%d/%m/%y") if c.commit.author else "—"
            lines.append(f"`{sha}` [{date}] *{author}*\n   _{msg}_")

        await update.message.reply_text(
            "\n\n".join(lines),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_pullrepo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⬇️ *Pull / Clone Repository*\n\n"
        "Gunakan perintah terminal `/shell` untuk clone:\n"
        "`git clone https://github.com/owner/repo.git`\n\n"
        "Atau gunakan /downloadrepo untuk download sebagai ZIP.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_downloadrepo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        g = get_gh(update.effective_user.id)
        if ctx.args and "/" in ctx.args[0]:
            repo_name = ctx.args[0]
        else:
            repo_name = _get_linked(update.effective_user.id)

        repo = g.get_repo(repo_name)
        branch = repo.default_branch
        zip_url = f"https://github.com/{repo.full_name}/archive/refs/heads/{branch}.zip"
        token = get_github_token(update.effective_user.id)

        msg = await update.message.reply_text(f"⬇️ Mengunduh `{repo_name}`...", parse_mode=ParseMode.MARKDOWN)

        headers = {"Authorization": f"token {token}"} if token else {}
        async with aiohttp.ClientSession() as session:
            async with session.get(zip_url, headers=headers, allow_redirects=True) as resp:
                if resp.status != 200:
                    await msg.edit_text(f"❌ Gagal download: HTTP {resp.status}")
                    return
                data = await resp.read()

        if len(data) > 50 * 1024 * 1024:
            await msg.edit_text(
                f"⚠️ File terlalu besar ({size_human(len(data))}) untuk dikirim via Telegram.\n"
                f"🔗 Download langsung: {zip_url}"
            )
            return

        bio = io.BytesIO(data)
        bio.name = f"{repo.name}-{branch}.zip"
        await msg.delete()
        await update.message.reply_document(
            document=bio,
            caption=f"✅ `{repo.full_name}` @ {branch}\n📦 {size_human(len(data))}",
            parse_mode=ParseMode.MARKDOWN,
        )
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_uploadfile(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message.document and not update.message.photo:
        await update.message.reply_text(
            "📤 *Upload File ke Repository*\n\n"
            "Kirim file dengan caption:\n"
            "`/upload <path_di_repo>`\n\n"
            "Contoh caption saat kirim file:\n"
            "`/upload src/main.py`\n\n"
            "Pastikan repo sudah ditautkan dengan /linkrepo",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    caption = update.message.caption or ""
    path_in_repo = caption.replace("/upload", "").strip() or "uploaded_file"

    try:
        repo_name = _get_linked(update.effective_user.id)
        g = get_gh(update.effective_user.id)
        repo = g.get_repo(repo_name)

        if update.message.document:
            file = await update.message.document.get_file()
            filename = update.message.document.file_name or "file"
        else:
            file = await update.message.photo[-1].get_file()
            filename = "photo.jpg"

        if not path_in_repo or path_in_repo == "uploaded_file":
            path_in_repo = filename

        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
            await file.download_to_drive(tmp.name)
            with open(tmp.name, "rb") as f:
                content = f.read()
            os.unlink(tmp.name)

        msg = await update.message.reply_text(f"📤 Mengupload ke `{repo_name}/{path_in_repo}`...", parse_mode=ParseMode.MARKDOWN)

        try:
            existing = repo.get_contents(path_in_repo)
            repo.update_file(
                path=path_in_repo,
                message=f"Update {path_in_repo} via Telegram Bot",
                content=content,
                sha=existing.sha,
            )
            action = "diperbarui"
        except GithubException:
            repo.create_file(
                path=path_in_repo,
                message=f"Add {path_in_repo} via Telegram Bot",
                content=content,
            )
            action = "ditambahkan"

        await msg.edit_text(
            f"✅ File berhasil {action}!\n📄 `{repo_name}/{path_in_repo}`",
            parse_mode=ParseMode.MARKDOWN,
        )
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_editfile(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or len(ctx.args) < 2:
        await update.message.reply_text(
            "✏️ *Edit File Repository*\n\n"
            "Gunakan: `/editfile <path> <konten baru>`\n\n"
            "Contoh:\n`/editfile README.md # Hello World\\nIni konten baru`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    try:
        repo_name = _get_linked(update.effective_user.id)
        g = get_gh(update.effective_user.id)
        repo = g.get_repo(repo_name)

        path = ctx.args[0]
        new_content = " ".join(ctx.args[1:]).replace("\\n", "\n")

        existing = repo.get_contents(path)
        repo.update_file(
            path=path,
            message=f"Edit {path} via Telegram Bot",
            content=new_content,
            sha=existing.sha,
        )
        await update.message.reply_text(
            f"✅ File berhasil diedit!\n📄 `{repo_name}/{path}`",
            parse_mode=ParseMode.MARKDOWN,
        )
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_deletefile(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text(
            "🗑️ Gunakan: `/deletefile <path>`\nContoh: `/deletefile old-file.txt`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    try:
        repo_name = _get_linked(update.effective_user.id)
        g = get_gh(update.effective_user.id)
        repo = g.get_repo(repo_name)
        path = ctx.args[0]
        existing = repo.get_contents(path)
        repo.delete_file(
            path=path,
            message=f"Delete {path} via Telegram Bot",
            sha=existing.sha,
        )
        await update.message.reply_text(
            f"🗑️ File `{path}` berhasil dihapus dari `{repo_name}`.",
            parse_mode=ParseMode.MARKDOWN,
        )
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_changevisibility(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text(
            "👁️ Gunakan: `/visibility <private|public>`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    try:
        repo_name = _get_linked(update.effective_user.id)
        g = get_gh(update.effective_user.id)
        repo = g.get_repo(repo_name)
        vis = ctx.args[0].lower()
        if vis not in ("private", "public"):
            await update.message.reply_text("❌ Gunakan `private` atau `public`.", parse_mode=ParseMode.MARKDOWN)
            return
        repo.edit(private=(vis == "private"))
        emoji = "🔒" if vis == "private" else "🌐"
        await update.message.reply_text(
            f"✅ `{repo_name}` sekarang {emoji} *{vis.capitalize()}*",
            parse_mode=ParseMode.MARKDOWN,
        )
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_renamerepo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text(
            "✏️ Gunakan: `/renamerepo <nama_baru>`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    try:
        repo_name = _get_linked(update.effective_user.id)
        g = get_gh(update.effective_user.id)
        repo = g.get_repo(repo_name)
        new_name = ctx.args[0]
        old_name = repo.name
        repo.edit(name=new_name)
        set_linked_repo(update.effective_user.id, f"{repo.owner.login}/{new_name}")
        await update.message.reply_text(
            f"✅ Repository berhasil diubah nama!\n`{old_name}` → `{new_name}`",
            parse_mode=ParseMode.MARKDOWN,
        )
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_repoinfo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        g = get_gh(update.effective_user.id)
        if ctx.args and "/" in ctx.args[0]:
            repo_name = ctx.args[0]
        else:
            repo_name = _get_linked(update.effective_user.id)

        repo = g.get_repo(repo_name)
        topics = ", ".join(repo.get_topics()) or "—"
        visibility = "🔒 Private" if repo.private else "🌐 Public"
        updated = repo.updated_at.strftime("%d %b %Y %H:%M") if repo.updated_at else "—"
        created = repo.created_at.strftime("%d %b %Y") if repo.created_at else "—"

        text = (
            f"📁 *{repo.full_name}*\n\n"
            f"📝 {repo.description or '—'}\n"
            f"👁️ Visibility: {visibility}\n"
            f"💻 Bahasa: {repo.language or '—'}\n"
            f"⭐ Stars: {repo.stargazers_count}\n"
            f"🍴 Forks: {repo.forks_count}\n"
            f"👀 Watchers: {repo.watchers_count}\n"
            f"🐛 Issues: {repo.open_issues_count}\n"
            f"🌿 Branch default: `{repo.default_branch}`\n"
            f"🏷️ Topics: {topics}\n"
            f"📅 Dibuat: {created}\n"
            f"🔄 Update: {updated}\n"
            f"🔗 {repo.html_url}"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_clonerepo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text(
            "🔄 *Clone Repository*\n\n"
            "Gunakan perintah di terminal:\n"
            "`/shell git clone https://github.com/owner/repo.git`\n\n"
            "Atau kirim langsung:\n"
            "`git clone <url>`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    repo_url = ctx.args[0]
    dest = ctx.args[1] if len(ctx.args) > 1 else ""
    cmd = f"git clone {repo_url} {dest}".strip()
    ctx.args = [cmd]
    from handlers.terminal_handlers import _run_shell_cmd
    await _run_shell_cmd(update, ctx, cmd)
