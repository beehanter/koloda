# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /app

# Install PostgreSQL client for pg_isready
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy the dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv pip install --system --no-cache .

# Copy the rest of the application's source code from the host to the container
COPY . .

# Explicitly copy the entrypoint script from the podman subfolder in the build context
COPY podman/entrypoint.sh /app/entrypoint.sh

# Make entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Make port 8501 available to the world outside this container (for Streamlit)
EXPOSE 8501

# Make port 8001 available for the static file server
EXPOSE 8001

# Use the entrypoint script to start the services
ENTRYPOINT ["/app/entrypoint.sh"]
