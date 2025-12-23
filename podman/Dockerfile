FROM postgres:17

# Устанавливаем PostGIS и зависимости для pgvector
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgis \
    postgresql-17-postgis-3 \
    build-essential \
    git \
    postgresql-server-dev-17 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем pgvector
RUN cd /tmp \
    && git clone --branch v0.7.4 https://github.com/pgvector/pgvector.git \
    && cd pgvector \
    && make clean \
    && make OPTFLAGS="" \
    && make install \
    && cd / \
    && rm -rf /tmp/pgvector

# Удаляем build dependencies (экономим место)
RUN apt-get remove -y build-essential git postgresql-server-dev-17 \
    && apt-get autoremove -y \
    && apt-get clean
