FROM postgres:17

# Install PostGIS
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-17-postgis-3 \
    postgresql-contrib \
 && rm -rf /var/lib/apt/lists/*

# Add healthcheck to wait for DB readiness
HEALTHCHECK CMD pg_isready -U bee -d bee || exit 1

# Copy initialization script
COPY podman/init.sql /docker-entrypoint-initdb.d/
