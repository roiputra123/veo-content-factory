#!/usr/bin/env bash
# Diagnostik lingkungan untuk Veo Content Factory
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

MERAH='\033[0;31m'
HIJAU='\033[0;32m'
KUNING='\033[1;33m'
BIRU='\033[0;34m'
NC='\033[0m'

ok_msg()  { echo -e "  ${HIJAU}[OK]${NC} $1"; }
fail_msg(){ echo -e "  ${MERAH}[FAIL]${NC} $1"; }
warn_msg(){ echo -e "  ${KUNING}[WARN]${NC} $1"; }
info_msg(){ echo -e "  ${BIRU}[INFO]${NC} $1"; }

echo "============================================"
echo " Diagnostik Lingkungan — Veo Content Factory"
echo "============================================"
echo ""

# 1. Python
echo "--- Python ---"
python3 --version 2>&1 && ok_msg "Python $(python3 --version 2>&1 | awk '{print $2}')" || fail_msg "Python tidak ditemukan"

# 2. Dependensi
echo ""
echo "--- Dependensi ---"
for pkg in streamlit pyyaml google-genai pillow; do
    if python3 -c "import ${pkg}" 2>/dev/null; then
        ok_msg "$pkg terinstall"
    else
        fail_msg "$pkg belum terinstall"
    fi
done

# 3. Impor project
echo ""
echo "--- Impor Module ---"
python3 -c "
import sys
sys.path.insert(0, '.')
sys.path.insert(0, './app')
from prompt_engine.niche_loader import NicheLoader
from prompt_engine.refiner import PromptRefiner
from prompt_engine.builder import PromptBuilder
from core.logger import ProductionLogger
n = len(NicheLoader().list_niches())
print(f'OK: {n} profil niche tersedia')
" 2>&1 && ok_msg "Semua module project bisa diimpor" || fail_msg "Ada module yang gagal diimpor"

# 4. Port
echo ""
echo "--- Port ---"
for port in 8501 8502 8503; do
    if ss -tlnp 2>/dev/null | grep -q ":$port "; then
        warn_msg "Port $port sedang dipakai"
    else
        ok_msg "Port $port tersedia"
    fi
done

# 5. Jaringan
echo ""
echo "--- Jaringan ---"
echo "  Hostname : $(hostname)"
WSL_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
echo "  WSL IP   : $WSL_IP"
if grep -qi microsoft /proc/version 2>/dev/null; then
    echo "  Platform : WSL2 (Windows Subsystem for Linux)"
    echo ""
    echo "  Cara akses dari Windows browser:"
    echo "    http://localhost:<port>"
    echo ""
    echo "  Jika tidak bisa, jalankan di Windows PowerShell (Admin):"
    echo "    netsh interface portproxy add v4tov4 listenport=8501 listenaddress=0.0.0.0 connectport=8501 connectaddress=$WSL_IP"
    echo ""
    echo "  Cek portproxy:"
    echo "    netsh interface portproxy show all"
    echo ""
    echo "  Hapus portproxy (kalau ingin reset):"
    echo "    netsh interface portproxy delete v4tov4 listenport=8501"
else
    echo "  Platform : Linux Native"
fi

# 6. .env
echo ""
echo "--- Konfigurasi ---"
if [ -f .env ]; then
    ok_msg "File .env ditemukan"
    grep -v "^#" .env | grep -v "^$" | while read line; do
        key=$(echo "$line" | cut -d= -f1)
        val=$(echo "$line" | cut -d= -f2-)
        if [ -z "$val" ]; then
            warn_msg "  $key = (kosong)"
        else
            masked="${val:0:4}****${val: -4}"
            [ ${#val} -le 8 ] && masked="$val"
            info_msg "  $key = $masked"
        fi
    done
else
    fail_msg "File .env tidak ada — copy dari .env.example dan isi API key"
fi

# 7. Git
echo ""
echo "--- Git ---"
if [ -d .git ]; then
    branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
    commit=$(git log --oneline -1 2>/dev/null)
    ok_msg "Repo git aktif — branch: $branch"
    info_msg "  $commit"
else
    info_msg "Belum diinisialisasi git"
fi

echo ""
echo "============================================"
echo " Selesai. Gunakan start_ui.sh untuk menjalankan UI."
echo "============================================"
