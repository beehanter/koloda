@echo off
ECHO "--- FULL PROJECT RESET ---"

ECHO "Step 1: Stopping and removing all containers defined in compose..."
podman compose down --volumes || echo "Compose command failed, but continuing..."

ECHO "Step 2: Removing any remaining related containers..."
for /f "tokens=*" %%a in ('podman ps -a --filter "name=koloda" -q') do (
    podman rm -f %%a
)
echo "No remaining containers to remove."

ECHO "Step 3: Forcibly removing images..."
podman rmi -f localhost/koloda_app || echo "App image not found, skipping."
podman rmi -f localhost/koloda_db || echo "DB image not found, skipping."

ECHO "Step 4: Forcibly removing data volume..."
podman volume rm -f koloda_pg_data || echo "Volume not found, skipping."

ECHO "Step 5: Removing processing state file..."
del /f /q storage\processing_state.json || echo "State file not found, skipping."

ECHO "--- PROJECT RESET COMPLETE ---"
ECHO "You can now rebuild and restart the project from a clean state."
pause