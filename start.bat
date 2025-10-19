@echo off
ECHO "Starting the application..."

ECHO "Starting Podman containers for the database..."
start "Podman" cmd /c "uv run python -m podman_compose up"
ECHO "Waiting for the database to be ready..."
timeout /t 10

ECHO "Starting services in new windows..."

ECHO " - Starting DataProcessing (main.py)..."
start "DataProcessing" cmd /c "title DataProcessing && uv run python main.py"

ECHO " - Starting Static File Server (serve_static.py)..."
start "StaticServer" cmd /c "title StaticServer && uv run python src/serve_static.py"

ECHO " - Starting Streamlit..."
start "StreamlitApp" cmd /c "title StreamlitApp && uv run python -m streamlit run stream/app.py"

ECHO "All services launched in separate windows."