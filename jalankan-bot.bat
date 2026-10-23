@echo off
cd /d "%~dp0"
echo Menyalakan Minhub... (tutup jendela ini untuk mematikan bot)
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" bot.py
) else (
    python bot.py
)
pause
