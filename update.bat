@echo off
ECHO "--- Starting Incremental Data Update ---"

ECHO "Step 1: Stopping running application container (if any)..."
podman compose stop app

ECHO "Step 2: Removing processing state file to force re-processing..."
del /f /q storage\processing_state.json

ECHO "Step 3: Running the data processing script in the container..."
podman compose run --rm app update

ECHO "--- Incremental update complete. ---"
ECHO "You can now start the application with: podman compose up -d"
pause