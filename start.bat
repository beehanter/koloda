@echo off
ECHO "Starting the application..."

ECHO "Starting Podman containers for the database..."
start "Podman" cmd /c "podman-compose up"

ECHO "Waiting for the database to be ready..."
timeout /t 10

ECHO "Running the data processing script (main.py)..."
start "DataProcessing" cmd /c "uv run python main.py"

ECHO "Starting the static file server (serve_static.py)..."
start "StaticServer" cmd /c "uv run python src/serve_static.py"

ECHO "Starting the Streamlit application..."
uv run streamlit run stream/app.py