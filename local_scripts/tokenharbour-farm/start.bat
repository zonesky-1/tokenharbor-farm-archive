@echo off
rem ============================================
rem  TokenHarbour Farm - launcher CLI interaktif
rem ============================================
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

rem Cari venv di beberapa lokasi umum; fallback ke python sistem
set PYEXE=%~dp0.venv\Scripts\python.exe
if not exist "%PYEXE%" set PYEXE=%~dp0..\.venv\Scripts\python.exe
if not exist "%PYEXE%" set PYEXE=%~dp0..\..\.venv\Scripts\python.exe
if not exist "%PYEXE%" set PYEXE=python

"%PYEXE%" -X utf8 farm.py
pause
