@echo off
ECHO "Stopping all application processes..."

ECHO "Stopping and removing Podman containers..."
podman-compose down

ECHO "Stopping Python and Streamlit processes..."
taskkill /IM streamlit.exe /F
taskkill /IM python.exe /F /FI "WINDOWTITLE eq DataProcessing"
taskkill /IM python.exe /F /FI "WINDOWTITLE eq StaticServer"

ECHO "All processes have been terminated."
pause