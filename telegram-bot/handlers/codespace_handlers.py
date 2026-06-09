"""
GitHub Codespace handlers — full access via REST API
Butuh scope: codespace
"""

import aiohttp
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from utils.auth import get_github_token, get_linked_repo
from utils.helpers import send_long_message, truncate

GITHUB_API = "https://api.github.com"


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }


def _check_token(user_id: int) -> str:
    token = get_github_token(user_id)
    if not token:
        raise ValueError("❌ Token GitHub belum diset. Gunakan /settoken <token>")
    return token


def _get_linked(user_id: int) -> str:
    linked = get_linked_repo(user_id)
    if not linked:
        raise ValueError("❌ Belum ada repo yang ditautkan. Gunakan /linkrepo <owner/repo>")
    return linked


def _state_emoji(state: str) -> str:
    return {
        "Available": "🟢",
        "Shutdown": "🔴",
        "Starting": "🟡",
        "Stopping": "🟠",
        "Rebuilding": "🔄",
        "Queued": "⏳",
        "Failed": "❌",
        "Deleted": "🗑️",
    }.get(state, "❓")


# ─── LIST CODESPACES ──────────────────────────────────────────────────────────

async def cmd_codespaces(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        token = _check_token(update.effective_user.id)
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{GITHUB_API}/user/codespaces",
                headers=_headers(token),
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 401:
                    await update.message.reply_text("❌ Token tidak memiliki akses Codespace.\nPastikan scope `codespace` diaktifkan.")
                    return
                data = await resp.json()

        codespaces = data.get("codespaces", [])
        if not codespaces:
            await update.message.reply_text(
                "📭 Tidak ada codespace aktif.\n\nBuat baru dengan: `/createcodespace`",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        lines = [f"🖥️ *GitHub Codespaces* ({len(codespaces)} total)\n"]
        for cs in codespaces:
            state = cs.get("state", "Unknown")
            emoji = _state_emoji(state)
            name = cs.get("name", "—")
            display = cs.get("display_name") or name
            repo = cs.get("repository", {}).get("full_name", "—")
            branch = cs.get("git_status", {}).get("ref", "—")
            machine = cs.get("machine", {}) or {}
            machine_name = machine.get("display_name", "—")
            updated = cs.get("updated_at", "")[:10] if cs.get("updated_at") else "—"

            lines.append(
                f"{emoji} *{display}*\n"
                f"   📛 `{name}`\n"
                f"   📁 `{repo}` @ `{branch}`\n"
                f"   💻 {machine_name} | 🔄 {updated}\n"
                f"   Status: `{state}`"
            )

        text = "\n\n".join(lines) + "\n\n_Gunakan `/csstart`, `/csstop`, `/csdelete` + nama codespace_"
        await send_long_message(update, text, parse_mode=ParseMode.MARKDOWN)

    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ─── DETAIL CODESPACE ─────────────────────────────────────────────────────────

async def cmd_csinfo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text(
            "🖥️ Gunakan: `/csinfo <nama_codespace>`\nLihat nama dengan `/codespaces`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    try:
        token = _check_token(update.effective_user.id)
        name = ctx.args[0]
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{GITHUB_API}/user/codespaces/{name}",
                headers=_headers(token),
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 404:
                    await update.message.reply_text(f"❌ Codespace `{name}` tidak ditemukan.", parse_mode=ParseMode.MARKDOWN)
                    return
                cs = await resp.json()

        state = cs.get("state", "Unknown")
        machine = cs.get("machine") or {}
        git_status = cs.get("git_status") or {}
        runtime = cs.get("runtime_constraints") or {}
        prebuild = "✅" if cs.get("prebuild") else "❌"

        text = (
            f"🖥️ *Codespace Detail*\n\n"
            f"📛 Nama: `{cs.get('name')}`\n"
            f"🏷️ Display: {cs.get('display_name') or '—'}\n"
            f"📁 Repo: `{cs.get('repository', {}).get('full_name', '—')}`\n"
            f"🌿 Branch: `{git_status.get('ref', '—')}`\n"
            f"💻 Machine: {machine.get('display_name', '—')}\n"
            f"   CPU: {machine.get('cpus', '—')} cores | RAM: {machine.get('memory_in_bytes', 0) // (1024**3)} GB\n"
            f"   Storage: {machine.get('storage_in_bytes', 0) // (1024**3)} GB\n"
            f"{_state_emoji(state)} Status: `{state}`\n"
            f"🏗️ Prebuild: {prebuild}\n"
            f"📅 Dibuat: {cs.get('created_at', '—')[:10]}\n"
            f"🔄 Update: {cs.get('updated_at', '—')[:10]}\n"
            f"🔗 URL: {cs.get('web_url', '—')}"
        )
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ─── BUAT CODESPACE ───────────────────────────────────────────────────────────

async def cmd_createcodespace(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        token = _check_token(user_id)

        if ctx.args and "/" in ctx.args[0]:
            repo_name = ctx.args[0]
        else:
            repo_name = _get_linked(user_id)

        branch = ctx.args[1] if len(ctx.args) > 1 else None
        machine = ctx.args[2] if len(ctx.args) > 2 else "basicLinux32gb"

        owner, repo = repo_name.split("/", 1)

        payload: dict = {
            "repository_id": None,
            "machine": machine,
        }
        if branch:
            payload["ref"] = branch

        # Ambil repo ID dulu
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{GITHUB_API}/repos/{repo_name}",
                headers=_headers(token),
            ) as r:
                if r.status != 200:
                    await update.message.reply_text(f"❌ Repo `{repo_name}` tidak ditemukan.", parse_mode=ParseMode.MARKDOWN)
                    return
                repo_data = await r.json()
                payload["repository_id"] = repo_data["id"]
                if not branch:
                    payload["ref"] = repo_data.get("default_branch", "main")

        msg = await update.message.reply_text(
            f"⏳ Membuat codespace untuk `{repo_name}` @ `{payload['ref']}`...",
            parse_mode=ParseMode.MARKDOWN,
        )

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{GITHUB_API}/user/codespaces",
                headers=_headers(token),
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                data = await resp.json()
                if resp.status not in (200, 201):
                    err = data.get("message", str(data))
                    await msg.edit_text(f"❌ Gagal membuat codespace: {err}")
                    return

        cs = data
        await msg.edit_text(
            f"✅ *Codespace Dibuat!*\n\n"
            f"📛 Nama: `{cs.get('name')}`\n"
            f"📁 Repo: `{repo_name}`\n"
            f"🌿 Branch: `{cs.get('git_status', {}).get('ref', '—')}`\n"
            f"{_state_emoji(cs.get('state', ''))} Status: `{cs.get('state')}`\n"
            f"🔗 {cs.get('web_url', '—')}\n\n"
            f"_Gunakan `/csstart {cs.get('name')}` untuk mulai_",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )

    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ─── START CODESPACE ──────────────────────────────────────────────────────────

async def cmd_csstart(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text(
            "▶️ Gunakan: `/csstart <nama_codespace>`\nLihat daftar: `/codespaces`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    try:
        token = _check_token(update.effective_user.id)
        name = ctx.args[0]
        msg = await update.message.reply_text(f"▶️ Memulai codespace `{name}`...", parse_mode=ParseMode.MARKDOWN)

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{GITHUB_API}/user/codespaces/{name}/start",
                headers=_headers(token),
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                data = await resp.json()
                if resp.status not in (200, 202):
                    err = data.get("message", str(data))
                    await msg.edit_text(f"❌ Gagal start: {err}")
                    return

        cs = data
        await msg.edit_text(
            f"▶️ *Codespace Starting!*\n\n"
            f"📛 `{cs.get('name')}`\n"
            f"{_state_emoji(cs.get('state', ''))} Status: `{cs.get('state')}`\n"
            f"🔗 {cs.get('web_url', '—')}",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )

    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ─── STOP CODESPACE ───────────────────────────────────────────────────────────

async def cmd_csstop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text(
            "⏹️ Gunakan: `/csstop <nama_codespace>`\nLihat daftar: `/codespaces`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    try:
        token = _check_token(update.effective_user.id)
        name = ctx.args[0]
        msg = await update.message.reply_text(f"⏹️ Menghentikan codespace `{name}`...", parse_mode=ParseMode.MARKDOWN)

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{GITHUB_API}/user/codespaces/{name}/stop",
                headers=_headers(token),
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                data = await resp.json()
                if resp.status not in (200, 202):
                    err = data.get("message", str(data))
                    await msg.edit_text(f"❌ Gagal stop: {err}")
                    return

        cs = data
        await msg.edit_text(
            f"⏹️ *Codespace Stopped!*\n\n"
            f"📛 `{cs.get('name')}`\n"
            f"{_state_emoji(cs.get('state', ''))} Status: `{cs.get('state')}`",
            parse_mode=ParseMode.MARKDOWN,
        )

    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ─── DELETE CODESPACE ─────────────────────────────────────────────────────────

async def cmd_csdelete(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text(
            "🗑️ Gunakan: `/csdelete <nama_codespace>`\n⚠️ Tindakan ini tidak bisa dibatalkan!",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    try:
        token = _check_token(update.effective_user.id)
        name = ctx.args[0]
        msg = await update.message.reply_text(f"🗑️ Menghapus codespace `{name}`...", parse_mode=ParseMode.MARKDOWN)

        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f"{GITHUB_API}/user/codespaces/{name}",
                headers=_headers(token),
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status == 202:
                    await msg.edit_text(f"🗑️ Codespace `{name}` berhasil dihapus.", parse_mode=ParseMode.MARKDOWN)
                elif resp.status == 401:
                    await msg.edit_text("❌ Token tidak punya akses untuk menghapus codespace.")
                elif resp.status == 409:
                    await msg.edit_text(f"⚠️ Codespace `{name}` harus dihentikan dulu. Gunakan `/csstop {name}`", parse_mode=ParseMode.MARKDOWN)
                else:
                    data = await resp.json()
                    err = data.get("message", f"HTTP {resp.status}")
                    await msg.edit_text(f"❌ Gagal hapus: {err}")

    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ─── LIST MACHINE TYPES ───────────────────────────────────────────────────────

async def cmd_csmachines(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        token = _check_token(user_id)

        if ctx.args and "/" in ctx.args[0]:
            repo_name = ctx.args[0]
        else:
            repo_name = _get_linked(user_id)

        branch = ctx.args[1] if len(ctx.args) > 1 else None
        url = f"{GITHUB_API}/repos/{repo_name}/codespaces/machines"
        if branch:
            url += f"?ref={branch}"

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=_headers(token),
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 401:
                    await update.message.reply_text("❌ Token tidak memiliki akses Codespace.")
                    return
                data = await resp.json()

        machines = data.get("machines", [])
        if not machines:
            await update.message.reply_text(f"📭 Tidak ada machine tersedia untuk `{repo_name}`.", parse_mode=ParseMode.MARKDOWN)
            return

        lines = [f"💻 *Machine Types — {repo_name}*\n"]
        for m in machines:
            ram = m.get("memory_in_bytes", 0) // (1024 ** 3)
            storage = m.get("storage_in_bytes", 0) // (1024 ** 3)
            lines.append(
                f"🔹 `{m.get('name')}` — *{m.get('display_name')}*\n"
                f"   CPU: {m.get('cpus')} cores | RAM: {ram} GB | Storage: {storage} GB\n"
                f"   OS: {m.get('operating_system', '—')} | {m.get('storage_in_bytes', 0) // (1024**3)} GB"
            )

        lines.append(f"\n_Gunakan nama machine di `/createcodespace {repo_name} main <machine_name>`_")
        await send_long_message(update, "\n\n".join(lines), parse_mode=ParseMode.MARKDOWN)

    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ─── CODESPACE SECRETS ────────────────────────────────────────────────────────

async def cmd_cssecrets(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        token = _check_token(update.effective_user.id)
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{GITHUB_API}/user/codespaces/secrets",
                headers=_headers(token),
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 401:
                    await update.message.reply_text("❌ Token tidak memiliki akses Codespace secrets.")
                    return
                data = await resp.json()

        secrets = data.get("secrets", [])
        if not secrets:
            await update.message.reply_text(
                "📭 Tidak ada Codespace secret.\n\nTambah dengan: `/cssecretset <NAMA> <nilai>`",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        lines = [f"🔐 *Codespace Secrets* ({len(secrets)} total)\n"]
        for s in secrets:
            updated = s.get("updated_at", "")[:10] if s.get("updated_at") else "—"
            vis = s.get("visibility", "—")
            repos = s.get("selected_repositories_url", "")
            lines.append(f"🔑 `{s.get('name')}` | 👁️ {vis} | 🔄 {updated}")

        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cmd_cssecretset(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or len(ctx.args) < 2:
        await update.message.reply_text(
            "🔐 *Set Codespace Secret*\n\n"
            "Gunakan: `/cssecretset <NAMA_SECRET> <nilai>`\n"
            "Contoh: `/cssecretset DATABASE_URL postgres://...`\n\n"
            "⚠️ Secret perlu dienkripsi dengan public key GitHub.\n"
            "Untuk keamanan lebih, set langsung di: https://github.com/settings/codespaces",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
        return
    await update.message.reply_text(
        "⚠️ *Catatan Keamanan*\n\n"
        "Untuk set Codespace secret, gunakan GitHub langsung:\n"
        "🔗 https://github.com/settings/codespaces\n\n"
        "Ini lebih aman karena nilai secret perlu dienkripsi dengan public key GitHub sebelum dikirim ke API.",
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
    )


# ─── EXPORT CODESPACE TO BRANCH ──────────────────────────────────────────────

async def cmd_csexport(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text(
            "📤 *Export Codespace ke Branch*\n\n"
            "Gunakan: `/csexport <nama_codespace>`\n"
            "Ini akan push perubahan ke branch baru di GitHub.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    try:
        token = _check_token(update.effective_user.id)
        name = ctx.args[0]
        msg = await update.message.reply_text(f"📤 Mengexport codespace `{name}`...", parse_mode=ParseMode.MARKDOWN)

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{GITHUB_API}/user/codespaces/{name}/exports",
                headers=_headers(token),
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                data = await resp.json()
                if resp.status not in (200, 202):
                    err = data.get("message", f"HTTP {resp.status}")
                    await msg.edit_text(f"❌ Export gagal: {err}")
                    return

        branch = data.get("branch", "—")
        sha = data.get("sha", "—")[:7]
        html_url = data.get("html_url", "—")
        await msg.edit_text(
            f"✅ *Codespace Exported!*\n\n"
            f"📛 Codespace: `{name}`\n"
            f"🌿 Branch: `{branch}`\n"
            f"📝 Commit: `{sha}`\n"
            f"🔗 {html_url}",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )

    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ─── RENAME CODESPACE ─────────────────────────────────────────────────────────

async def cmd_csrename(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or len(ctx.args) < 2:
        await update.message.reply_text(
            "✏️ Gunakan: `/csrename <nama_lama> <display_name_baru>`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    try:
        token = _check_token(update.effective_user.id)
        name = ctx.args[0]
        new_display = " ".join(ctx.args[1:])

        async with aiohttp.ClientSession() as session:
            async with session.patch(
                f"{GITHUB_API}/user/codespaces/{name}",
                headers=_headers(token),
                json={"display_name": new_display},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                data = await resp.json()
                if resp.status != 200:
                    err = data.get("message", f"HTTP {resp.status}")
                    await update.message.reply_text(f"❌ Gagal rename: {err}")
                    return

        await update.message.reply_text(
            f"✅ Codespace `{name}` diubah nama tampilan menjadi: *{new_display}*",
            parse_mode=ParseMode.MARKDOWN,
        )

    except ValueError as e:
        await update.message.reply_text(str(e))
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
