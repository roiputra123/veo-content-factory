#!/usr/bin/env bash
# Veo Content Factory — Streamlit UI Launcher (WSL)
set -e

PORT=${1:-8501}
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "============================================"
echo " Veo Content Factory — Streamlit UI"
echo "============================================"
echo ""

# Kill proses lama
fuser -k "${PORT}/tcp" 2>/dev/null || true
sleep 1

# Cek Streamlit
STREAMLIT_BIN=""
for p in "$HOME/.local/bin/streamlit" "/usr/local/bin/streamlit"; do
    [ -f "$p" ] && STREAMLIT_BIN="$p" && break
done

if [ -z "$STREAMLIT_BIN" ]; then
    echo "[ERROR] Streamlit tidak ditemukan."
    echo "  Install: pip install streamlit"
    exit 1
fi

# Cek .env
if [ ! -f "$DIR/.env" ]; then
    echo "[WARN] File .env tidak ditemukan."
    echo "  Copy dari .env.example: cp .env.example .env"
    echo "  Lalu isi GEMINI_API_KEY atau GOOGLE_APPLICATION_CREDENTIALS"
    echo ""
fi

# Mulai Streamlit
echo "[INFO] Menjalankan Streamlit di port $PORT ..."
cd "$DIR"
nohup "$STREAMLIT_BIN" run interface/app.py \
    --server.headless=true \
    --server.port="$PORT" \
    > /tmp/streamlit_${PORT}.log 2>&1 &

PID=$!
echo "[OK] PID: $PID"

# Tunggu dan cek
sleep 3
if curl -s "http://localhost:${PORT}/_stcore/health" 2>/dev/null | grep -q ok; then
    echo "[OK] Streamlit siap!"
else
    echo "[WARN] Streamlit belum merespon. Cek log:"
    tail -5 "/tmp/streamlit_${PORT}.log"
fi

echo ""
echo "============================================"
echo " AKSES UI DI BROWSER:"
echo "  > http://localhost:${PORT}"
echo ""
echo " WSL2 IP: $(hostname -I 2>/dev/null | awk '{print $1}')"
echo "============================================"
echo ""
echo "Untuk stop: pkill -f \"streamlit.*${PORT}\""
echo "Log: /tmp/streamlit_${PORT}.log"
