#!/bin/bash
# Setup otomatis untuk Telegram Bot
# Jalankan: bash setup.sh

set -e

echo "=================================="
echo "  GitHub + Terminal + AI Bot"
echo "       Setup Script"
echo "=================================="
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "❌ Python3 tidak ditemukan. Install Python 3.10+ terlebih dahulu."
    exit 1
fi

PYTHON_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✅ Python $PYTHON_VER ditemukan"

# Install pip jika belum ada
if ! command -v pip3 &>/dev/null; then
    echo "📦 Menginstall pip..."
    curl https://bootstrap.pypa.io/get-pip.py | python3
fi

# Install dependensi
echo ""
echo "📦 Menginstall dependensi..."
pip3 install -r requirements.txt
echo "✅ Dependensi terinstall"

# Buat .env jika belum ada
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "📝 File .env dibuat dari .env.example"
fi

# Buat direktori yang dibutuhkan
mkdir -p data /tmp/telegram-shell
echo "✅ Direktori siap"

echo ""
echo "=================================="
echo "  Konfigurasi Diperlukan"
echo "=================================="
echo ""
echo "Edit file .env dan isi:"
echo ""
echo "  1. TELEGRAM_BOT_TOKEN"
echo "     Dapatkan dari @BotFather di Telegram"
echo ""
echo "  2. ADMIN_USER_IDS"
echo "     Dapatkan ID kamu dari @userinfobot"
echo ""
echo "  3. (Opsional) DEFAULT_GITHUB_TOKEN"
echo "     Buat di: https://github.com/settings/tokens"
echo ""
echo "Setelah .env diisi, jalankan:"
echo "  python3 bot.py"
echo ""
echo "Atau dengan Docker:"
echo "  docker-compose up -d"
echo ""
echo "=================================="

# Tanya apakah ingin edit .env sekarang
read -p "Buka .env sekarang? (y/n): " choice
if [[ "$choice" == "y" || "$choice" == "Y" ]]; then
    if command -v nano &>/dev/null; then
        nano .env
    elif command -v vim &>/dev/null; then
        vim .env
    else
        cat .env
        echo ""
        echo "Edit .env secara manual dengan text editor."
    fi
fi

echo ""
echo "✅ Setup selesai! Jalankan: python3 bot.py"
