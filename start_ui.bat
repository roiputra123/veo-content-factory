@echo off
chcp 65001 >nul
title Veo Content Factory - Streamlit UI
echo ============================================
echo  Veo Content Factory - Streamlit UI Launcher
echo ============================================
echo.

:: Cari WSL IP
for /f "tokens=1" %%i in ('wsl hostname -I 2^>nul') do set WSL_IP=%%i
if "%WSL_IP%"=="" (
    echo [ERROR] Tidak bisa deteksi IP WSL.
    echo Pastikan WSL sudah jalan: wsl --list --verbose
    pause
    exit /b 1
)

echo [INFO] WSL IP: %WSL_IP%
echo.

:: Setup portproxy (hapus dulu yang lama)
echo [INFO] Setup port forwarding localhost:8501 ^=^> %WSL_IP%:8501
netsh interface portproxy delete v4tov4 listenport=8501 >nul 2>&1
netsh interface portproxy add v4tov4 listenport=8501 listenaddress=0.0.0.0 connectport=8501 connectaddress=%WSL_IP%
if %errorlevel% neq 0 (
    echo [WARN] Gagal setup portproxy. Coba jalankan sebagai Administrator.
    echo.
    echo    Klik kanan ^> "Run as Administrator"
    pause
    exit /b 1
)

:: Verifikasi portproxy
echo [INFO] Portproxy aktif:
netsh interface portproxy show v4tov4 | findstr "8501"
echo.

:: Cek apakah Streamlit sudah jalan di WSL
wsl pgrep -f "streamlit.*8501" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Streamlit belum jalan. Menjalankan...
    start "Streamlit" wsl bash -c "cd /mnt/c/gemini-proyek/veo-content-factory && nohup ~/.local/bin/streamlit run interface/app.py --server.headless=true --server.port=8501 > /tmp/streamlit_8501.log 2>&1 &"
    echo [INFO] Tunggu 5 detik...
    timeout /t 5 /nobreak >nul
) else (
    echo [INFO] Streamlit sudah berjalan.
)

:: Test akses
echo [INFO] Testing akses ke http://localhost:8501 ...
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:8501/_stcore/health' -TimeoutSec 5; if ($r.Content -eq 'ok') { Write-Host '[OK] Streamlit siap!' -ForegroundColor Green } else { Write-Host '[ERROR] Respon tidak valid: ' $r.Content -ForegroundColor Red } } catch { Write-Host '[ERROR] Tidak bisa akses Streamlit. Cek firewall atau jalankan ulang.' -ForegroundColor Red }"

echo.
echo ============================================
echo  AKSES UI DI BROWSER:
echo  ^> http://localhost:8501
echo ============================================
echo.
echo  Untuk stop: tekan Ctrl+C di terminal ini,
echo  lalu jalankan: wsl pkill -f streamlit
echo.

:: Buka browser
start http://localhost:8501

pause
