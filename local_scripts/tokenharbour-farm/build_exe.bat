@echo off
rem ==========================================================
rem  TokenHarbour Farm - build EXE standalone (PyInstaller)
rem  Hasil: dist\TokenHarbourFarm\TokenHarbourFarm.exe
rem  Taruh/copy folder hasil itu ke mana saja DI DALAM folder
rem  proyek token-harbor-main, lalu jalankan exe-nya.
rem ==========================================================
cd /d "%~dp0"

set PY=%~dp0.venv\Scripts\python.exe
if not exist "%PY%" set PY=%~dp0..\.venv\Scripts\python.exe
if not exist "%PY%" set PY=python

echo [1/2] Memastikan PyInstaller terpasang...
"%PY%" -m pip install --upgrade pyinstaller || goto :err

echo [2/2] Membangun EXE (butuh beberapa menit)...
"%PY%" -m PyInstaller --noconfirm --clean --onedir --console ^
  --name TokenHarbourFarm ^
  --paths . ^
  --collect-all playwright ^
  --collect-all camoufox ^
  --collect-all curl_cffi ^
  farm.py || goto :err

echo.
echo ================================================
echo  SELESAI! Hasil build ada di:
echo    dist\TokenHarbourFarm\TokenHarbourFarm.exe
echo  Catatan komputer target:
echo   - Tidak perlu install Python
echo   - Tetap butuh Google Chrome terinstall
echo   - Camoufox browser otomatis diunduh saat
echo     pertama kali dipakai (±100MB, sekali saja)
echo   - Bisa kena false-positive antivirus;
echo     tambahkan pengecualian bila perlu
echo ================================================
pause
exit /b 0

:err
echo.
echo [!!] Build gagal. Periksa pesan error di atas.
pause
exit /b 1