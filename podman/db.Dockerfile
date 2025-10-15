FROM postgres:17

# Install PostGIS
RUN apt-get update && \
    apt-get install -y --no-install-recommends postgresql-17-postgis-3 postgresql-contrib && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy initialization script
COPY podman/init.sql /docker-entrypoint-initdb.d/
