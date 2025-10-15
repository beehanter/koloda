@echo off
ECHO "Building container images..."

ECHO "Building database image (koloda_db)..."
podman build --no-cache -f podman/db.Dockerfile -t localhost/koloda_db .

ECHO "Forcibly removing old application image (koloda_app)..."
podman rmi -f localhost/koloda_app || true

ECHO "Building application image (koloda_app)..."
podman build --no-cache -f podman/app.Dockerfile -t localhost/koloda_app .

ECHO "Build complete."
pause