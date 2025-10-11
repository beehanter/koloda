FROM postgres:17

# Install PostGIS
RUN apt-get update && apt-get install -y postgis

# Copy initialization script
COPY init.sql /docker-entrypoint-initdb.d/
