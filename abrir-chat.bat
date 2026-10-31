@echo off
rem Opens Tom in a browser chat window. The server runs on this computer only (127.0.0.1:8000).
rem Close this window to stop it.
cd /d "%~dp0"
where /q uv || (echo uv nao encontrado. Instale: https://docs.astral.sh/uv/ & pause & exit /b 1)
uv run python -m emporio.web
pause
