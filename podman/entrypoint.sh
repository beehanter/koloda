#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Wait for the database to be ready
echo "Waiting for PostgreSQL to be ready..."
# Используем pg_isready для проверки доступности базы данных.
# 'db' - это имя сервиса из docker-compose.yml.
until pg_isready -h db -U bee -d bee; do
  echo "Waiting for PostgreSQL..."
  sleep 2
done
echo "PostgreSQL is ready."

# Run the data processing script
echo "Running data processing..."
python main.py
echo "Data processing finished."

# Start the static file server in the background
echo "Starting static file server in background..."
python src/serve_static.py &

# Start the Streamlit application as the main process
echo "Starting Streamlit app..."
exec streamlit run stream/app.py --server.port=8501 --server.address=0.0.0.0