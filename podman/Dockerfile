FROM postgres:17

# Install PostGIS
RUN apt-get update && apt-get install -y postgresql-17-postgis-3 postgresql-contrib

# Copy initialization script
COPY init.sql /docker-entrypoint-initdb.d/
