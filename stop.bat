@echo off
ECHO "Stopping all application processes..."

ECHO "Stopping and removing Podman containers..."
uv run python -m podman_compose down
timeout /t 5 >nul

ECHO "Stopping service windows..."
:: Используем PowerShell для поиска и завершения процессов по заголовку окна
powershell -Command "Get-Process | Where-Object { $_.MainWindowTitle -match 'DataProcessing|StaticServer|StreamlitApp' } | Stop-Process -Force"

ECHO "All processes have been terminated."
pause
