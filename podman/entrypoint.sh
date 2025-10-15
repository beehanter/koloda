#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Wait for the database to be ready
echo "Waiting for DB to be ready..."
sleep 10

# Run the data processing script
echo "Running data processing..."
python main.py
echo "Data processing finished."

# Check if the first argument is 'update'
if [ "$1" = "update" ]; then
  echo "Update command detected. Exiting without starting servers."
  exit 0
fi

# Start the static file server in the background
echo "Starting static file server in background..."
python src/serve_static.py &

# Start the Streamlit application as the main process
echo "Starting Streamlit app..."
exec streamlit run stream/app.py --server.port=8501 --server.address=0.0.0.0