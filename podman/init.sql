-- ============================================================
-- KOLODA DATABASE - SCHEMA (Phase 1: AI-Ready Base)
-- PostgreSQL 17 + PostGIS + pgvector + Full-Text Search
-- ============================================================
-- БАЗОВЫЕ РАСШИРЕНИЯ (запускаются сразу)
CREATE EXTENSION IF NOT EXISTS postgis;
-- Координаты (уже используете)
CREATE EXTENSION IF NOT EXISTS vector;
-- Векторный поиск (базовый функционал)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
-- Для fuzzy text search
CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- Для row_hash
-- ОТЛОЖЕННЫЕ РАСШИРЕНИЯ (раскомментировать позже, если понадобится)
-- CREATE EXTENSION IF NOT EXISTS vectorscale CASCADE;  -- Только если > 500K векторов
-- ============================================================
-- ОЧИСТКА (для development)
-- ============================================================
DROP TABLE IF EXISTS kg_edges CASCADE;
DROP TABLE IF EXISTS test CASCADE;
DROP TABLE IF EXISTS osmotr CASCADE;
DROP TABLE IF EXISTS paseki CASCADE;
DROP TABLE IF EXISTS koloda CASCADE;
DROP TABLE IF EXISTS place CASCADE;
DROP TABLE IF EXISTS beekeepers CASCADE;
-- ============================================================
-- СПРАВОЧНИКИ (без изменений от исходной схемы)
-- ============================================================
CREATE TABLE beekeepers (
    beekeeper VARCHAR(10) PRIMARY KEY,
    name VARCHAR(255),
    contact VARCHAR(20),
    adres VARCHAR(255),
    row_hash VARCHAR(64) UNIQUE,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE place (
    place VARCHAR(255) PRIMARY KEY,
    region VARCHAR(255),
    rayon VARCHAR(255),
    oopt VARCHAR(255),
    image TEXT,
    row_hash VARCHAR(64),
    created_at TIMESTAMP DEFAULT NOW()
);
-- ============================================================
-- ОСНОВНЫЕ ТАБЛИЦЫ
-- AI-поля: ТОЛЬКО где реально нужно (koloda + osmotr опционально)
-- ============================================================
CREATE TABLE koloda (
    koloda_id VARCHAR(10) NOT NULL PRIMARY KEY,
    date TIMESTAMP,
    place VARCHAR(255) NOT NULL REFERENCES place(place),
    beekeeper VARCHAR(10) NOT NULL REFERENCES beekeepers(beekeeper),
    tree VARCHAR(255),
    material VARCHAR(255),
    tipe VARCHAR(255),
    height_loc REAL,
    letok_orient VARCHAR(50),
    diametr_out REAL,
    diametr_in REAL,
    height_koloda REAL,
    foto VARCHAR(512),
    pro_foto TEXT,
    info TEXT,
    coordinates GEOMETRY(Point, 4326),
    row_hash VARCHAR(64),
    -- AI-поля (ТОЛЬКО здесь - основная сущность для поиска!)
    embedding vector(1536),
    -- Семантический поиск (заполняется через Python)
    content_tsv tsvector,
    -- Full-text search (автоматический через триггер)
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE osmotr (
    date TIMESTAMP NOT NULL,
    koloda_id VARCHAR(10) NOT NULL,
    status VARCHAR(255),
    foto_out VARCHAR(512),
    pro_foto_out TEXT,
    foto_in VARCHAR(512),
    pro_foto_in TEXT,
    info TEXT,
    plan TEXT,
    date_plan DATE,
    row_hash VARCHAR(64),
    -- AI-поля (FTS добавляем сразу, embeddings - опционально позже)
    content_tsv tsvector,
    -- Дешёвый полнотекстовый поиск
    -- embedding vector(1536),        -- Раскомментировать в патче 004
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (date, koloda_id),
    FOREIGN KEY (koloda_id) REFERENCES koloda(koloda_id)
);
CREATE TABLE paseki (
    beekeeper VARCHAR(10) NOT NULL REFERENCES beekeepers(beekeeper),
    paseka VARCHAR(255) NOT NULL,
    date TIMESTAMP,
    place VARCHAR(255) NOT NULL REFERENCES place(place),
    coordinates GEOMETRY(Point, 4326),
    date_start DATE,
    many_bees INTEGER,
    obrabotki TEXT,
    poroda VARCHAR(255),
    data_poroda VARCHAR(512),
    foto VARCHAR(512),
    row_hash VARCHAR(64),
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (beekeeper, paseka)
);
CREATE TABLE test (
    date TIMESTAMP NOT NULL,
    koloda_id VARCHAR(10) NOT NULL,
    poroda VARCHAR(255),
    data_poroda VARCHAR(512),
    foto_varroa VARCHAR(512),
    varroa_test VARCHAR(50),
    row_hash VARCHAR(64),
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (date, koloda_id),
    FOREIGN KEY (koloda_id) REFERENCES koloda(koloda_id)
);
-- ============================================================
-- KNOWLEDGE GRAPH (ЗАДЕЛ, НЕ БАЗОВАЯ ФУНКЦИОНАЛЬНОСТЬ)
-- Создаём структуру, заполняется приложением через Python скрипты
-- ============================================================
CREATE TABLE kg_edges (
    id BIGSERIAL PRIMARY KEY,
    from_table TEXT NOT NULL,
    from_id TEXT NOT NULL,
    to_table TEXT NOT NULL,
    to_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    properties JSONB,
    -- Метаданные связи (расстояние, вес, скор сходства)
    weight REAL DEFAULT 1.0,
    -- Сила связи для взвешивания при обходе
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT unique_edge UNIQUE (
        from_table,
        from_id,
        to_table,
        to_id,
        relationship_type
    )
);
COMMENT ON TABLE kg_edges IS 'Knowledge Graph edges - таблица связей между сущностями.
Заполняется приложением через Python скрипты (scripts/build_knowledge_graph.py).
Используется для обогащения контекста при поиске и обходе графа.';
-- ============================================================
-- ТРИГГЕРЫ: ТОЛЬКО ДЛЯ TSVECTOR
-- Векторы (embeddings) заполняются через Python API, не триггеры!
-- ============================================================
CREATE OR REPLACE FUNCTION update_koloda_tsv() RETURNS TRIGGER AS $$ BEGIN NEW.content_tsv := to_tsvector(
        'russian',
        COALESCE(NEW.koloda_id, '') || ' ' || COALESCE(NEW.place, '') || ' ' || COALESCE(NEW.tree, '') || ' ' || COALESCE(NEW.material, '') || ' ' || COALESCE(NEW.tipe, '') || ' ' || COALESCE(NEW.info, '')
    );
NEW.updated_at := NOW();
RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER tsvector_update_koloda BEFORE
INSERT
    OR
UPDATE ON koloda FOR EACH ROW EXECUTE FUNCTION update_koloda_tsv();
CREATE OR REPLACE FUNCTION update_osmotr_tsv() RETURNS TRIGGER AS $$ BEGIN NEW.content_tsv := to_tsvector(
        'russian',
        COALESCE(NEW.status, '') || ' ' || COALESCE(NEW.info, '') || ' ' || COALESCE(NEW.plan, '')
    );
RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER tsvector_update_osmotr BEFORE
INSERT
    OR
UPDATE ON osmotr FOR EACH ROW EXECUTE FUNCTION update_osmotr_tsv();
-- ============================================================
-- ИНДЕКСЫ: МИНИМУМ (остальное - по метрикам при необходимости)
-- ============================================================
-- Foreign keys (обязательно для производительности)
CREATE INDEX idx_koloda_beekeeper ON koloda(beekeeper);
CREATE INDEX idx_koloda_place ON koloda(place);
CREATE INDEX idx_osmotr_koloda_id ON osmotr(koloda_id);
CREATE INDEX idx_test_koloda_id ON test(koloda_id);
CREATE INDEX idx_paseki_beekeeper ON paseki(beekeeper);
CREATE INDEX idx_paseki_place ON paseki(place);
-- Геопространственные (используются в приложении)
CREATE INDEX idx_koloda_coordinates ON koloda USING GIST(coordinates);
CREATE INDEX idx_paseki_coordinates ON paseki USING GIST(coordinates);
-- Full-text search (дешёвый, полезный)
CREATE INDEX idx_koloda_fts ON koloda USING GIN(content_tsv);
CREATE INDEX idx_osmotr_fts ON osmotr USING GIN(content_tsv);
-- Векторный индекс (HNSW) создаётся патчем 002, когда embeddings заполнены
-- CREATE INDEX idx_koloda_embedding ON koloda 
-- USING hnsw (embedding vector_cosine_ops) 
-- WITH (m = 16, ef_construction = 64);
-- Knowledge graph индексы (задел)
CREATE INDEX idx_kg_edges_from ON kg_edges(from_table, from_id);
CREATE INDEX idx_kg_edges_to ON kg_edges(to_table, to_id);
-- ============================================================
-- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (задел на будущее)
-- ============================================================
-- Простой векторный поиск (без RRF пока)
-- Используется для базовой проверки работы embeddings
CREATE OR REPLACE FUNCTION vector_search_koloda(
        query_vector vector(1536),
        search_limit INTEGER DEFAULT 10
    ) RETURNS TABLE (
        koloda_id VARCHAR,
        place VARCHAR,
        similarity REAL
    ) AS $$ BEGIN RETURN QUERY
SELECT k.koloda_id,
    k.place,
    (1 - (k.embedding <=> query_vector))::REAL AS similarity
FROM koloda k
WHERE k.embedding IS NOT NULL
ORDER BY k.embedding <=> query_vector
LIMIT search_limit;
END;
$$ LANGUAGE plpgsql;
COMMENT ON FUNCTION vector_search_koloda IS 'Базовый векторный поиск по колодам.
Использует косинусное расстояние в пространстве embeddings.
Hybrid search (RRF) добавить в патче 003.';
-- ============================================================
-- ВЕРСИОНИРОВАНИЕ СХЕМЫ (журнал изменений, не Alembic)
-- ============================================================
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    patch_name TEXT,
    -- Имя файла патча для трассировки
    applied_at TIMESTAMP DEFAULT NOW(),
    description TEXT
);
-- Базовая версия (init.sql)
INSERT INTO schema_version (version, patch_name, description)
VALUES (
        1,
        'init.sql',
        'Initial schema: PostgreSQL 17 + PostGIS + pgvector + FTS (koloda only)'
    ) ON CONFLICT DO NOTHING;
COMMENT ON TABLE schema_version IS 'Журнал изменений схемы БД (простая альтернатива Alembic).
patch_name помогает найти файл, который внёс изменение.
Для добавления новой версии: INSERT INTO schema_version VALUES (N, ''FILENAME.sql'', ''Description'');';
-- ============================================================
-- СЛУЖЕБНАЯ ИНФОРМАЦИЯ
-- ============================================================
COMMENT ON DATABASE bee IS 'Koloda - Beekeeping Data Analysis.
Schema Version: 1 (Phase 1 - Minimal AI-Ready Base)
Next steps: Run patches in podman/patches/ when ready for Phase 2+';