@echo off
echo Building DB image...
podman build -f podman/db.Dockerfile -t localhost/koloda_db:latest .

echo Building App image...
podman build -f podman/app.Dockerfile -t localhost/koloda_app:latest .

echo Build complete.