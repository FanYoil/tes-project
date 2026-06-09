# 🤖 GitHub + Terminal + AI Telegram Bot

Bot Telegram berbasis Python lengkap dengan integrasi GitHub, terminal interaktif, dan AI (GitHub Copilot).

---

## ✨ Fitur

### 📁 GitHub
| Perintah | Fungsi |
|----------|--------|
| `/settoken <token>` | Set GitHub Personal Access Token |
| `/removetoken` | Hapus token tersimpan |
| `/profile [username]` | Lihat profil GitHub |
| `/listrepo` | Daftar semua repository |
| `/searchrepo <query>` | Cari repository di seluruh GitHub |
| `/linkrepo <owner/repo>` | Tautkan repository aktif |
| `/repoinfo` | Info detail repository |
| `/browse [path]` | Jelajahi file repository |
| `/commits` | Riwayat commit |
| `/createrepo <nama>` | Buat repository baru |
| `/clonerepo <url>` | Clone repository via terminal |
| `/downloadrepo` | Download repo sebagai ZIP |
| `/upload` | Upload file ke repository |
| `/editfile <path> <konten>` | Edit file di repository |
| `/deletefile <path>` | Hapus file dari repository |
| `/visibility <private\|public>` | Ubah visibility repository |
| `/renamerepo <nama_baru>` | Rename repository |

### 🖥️ Terminal (Admin Only)
| Perintah | Fungsi |
|----------|--------|
| `/shell <cmd>` | Jalankan perintah shell apapun |
| `/sh <cmd>` | Alias untuk /shell |
| `/cd <path>` | Pindah direktori |
| `/cwd` | Lihat direktori saat ini |
| `/env set KEY VALUE` | Set environment variable |
| `/env get KEY` | Lihat environment variable |
| `/env list` | Daftar env var custom |
| _Kirim file + caption perintah_ | Upload & jalankan script |

### 🤖 AI (GitHub Copilot)
| Perintah | Fungsi |
|----------|--------|
| `/ai <pertanyaan>` | Chat dengan AI (riwayat disimpan) |
| `/aicode <kode>` | Review & debug kode |
| `/explain <topik>` | Jelaskan kode atau konsep |
| `/generate <deskripsi>` | Generate kode baru |
| `/aiclear` | Reset riwayat percakapan |

---

## 🚀 Cara Deploy

### 1. Persiapan Token

**Telegram Bot Token:**
1. Buka [@BotFather](https://t.me/BotFather) di Telegram
2. Kirim `/newbot` dan ikuti instruksi
3. Copy token yang diberikan

**GitHub Personal Access Token:**
1. Buka https://github.com/settings/tokens
2. Klik "Generate new token (classic)"
3. Pilih scope: `repo`, `user`, `delete_repo`, `admin:org`
4. Copy token

**Admin User ID:**
1. Buka [@userinfobot](https://t.me/userinfobot)
2. Kirim `/start`
3. Copy angka User ID kamu

---

### 🐳 Deploy dengan Docker (Direkomendasikan)

```bash
# Clone / copy folder telegram-bot
cd telegram-bot

# Salin file .env
cp .env.example .env

# Edit .env dengan konfigurasi kamu
nano .env

# Build & jalankan
docker-compose up -d

# Lihat log
docker-compose logs -f
```

---

### 🖥️ Deploy di VPS / Server

```bash
# Install Python 3.10+
sudo apt update && sudo apt install -y python3 python3-pip git

# Clone atau copy folder bot
cd telegram-bot

# Install dependensi
pip3 install -r requirements.txt

# Salin & edit .env
cp .env.example .env
nano .env  # Isi TELEGRAM_BOT_TOKEN dan ADMIN_USER_IDS

# Jalankan langsung
python3 bot.py

# Atau jalankan sebagai background process dengan screen:
screen -S telebot
python3 bot.py
# Ctrl+A, D untuk detach

# Atau gunakan systemd (lebih stabil):
```

**Setup systemd service:**
```bash
sudo nano /etc/systemd/system/telegrambot.service
```
```ini
[Unit]
Description=GitHub Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/path/ke/telegram-bot
ExecStart=/usr/bin/python3 /path/ke/telegram-bot/bot.py
Restart=always
RestartSec=10
EnvironmentFile=/path/ke/telegram-bot/.env

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload
sudo systemctl enable telegrambot
sudo systemctl start telegrambot
sudo systemctl status telegrambot
```

---

### ☁️ Deploy di GitHub Codespace

```bash
# Buka terminal di Codespace
cd telegram-bot

pip install -r requirements.txt

# Buat .env
cp .env.example .env
# Edit .env menggunakan editor Codespace

python3 bot.py
```

---

### 🌩️ Deploy di Cloud (Railway, Render, dll)

1. Push folder `telegram-bot` ke GitHub repo
2. Di Railway/Render, pilih "Deploy from GitHub"
3. Set environment variables dari `.env.example`
4. Deploy!

---

## ⚙️ Konfigurasi (.env)

```env
TELEGRAM_BOT_TOKEN=   # Dari @BotFather (WAJIB)
ADMIN_USER_IDS=       # User ID admin, pisah koma (WAJIB untuk terminal)
DEFAULT_GITHUB_TOKEN= # Token GitHub default (opsional)
OPENAI_API_KEY=       # Untuk AI fallback jika Copilot tidak tersedia
COMMAND_TIMEOUT=30    # Timeout perintah terminal (detik)
```

---

## 🔒 Keamanan

- **Terminal** hanya bisa diakses oleh user yang ID-nya ada di `ADMIN_USER_IDS`
- Token GitHub disimpan lokal di `data/user_tokens.json` (tidak dikirim ke server manapun)
- Setiap user menyimpan token GitHub-nya sendiri (multi-user support)
- `COMMAND_TIMEOUT` membatasi durasi eksekusi perintah

---

## 📂 Struktur File

```
telegram-bot/
├── bot.py                    # Entry point utama
├── config.py                 # Konfigurasi dari .env
├── requirements.txt          # Dependensi Python
├── .env.example              # Template konfigurasi
├── Dockerfile                # Untuk deploy Docker
├── docker-compose.yml        # Docker Compose setup
├── handlers/
│   ├── github_handlers.py    # Semua fitur GitHub
│   ├── terminal_handlers.py  # Terminal interaktif
│   └── ai_handlers.py        # AI / GitHub Copilot
├── utils/
│   ├── auth.py               # Manajemen token & sesi user
│   └── helpers.py            # Utilitas (split pesan, format, dll)
└── data/
    └── user_tokens.json      # Token user (auto-generated)
```

---

## 🤖 Tentang AI

Bot menggunakan **GitHub Copilot API** secara default (jika token GitHub kamu memiliki akses Copilot). Jika tidak tersedia, bot akan fallback ke **OpenAI API** (isi `OPENAI_API_KEY` di .env).

Riwayat percakapan disimpan per-user (max 10 pesan terakhir) untuk konteks yang konsisten.
