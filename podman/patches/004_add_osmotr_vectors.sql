-- =============================================================================
-- ПАТЧ 004: Расширение векторного поиска на таблицу osmotr (ОПЦИОНАЛЬНО)
-- =============================================================================
-- Применять: если нужен семантический поиск по осмотрам
-- Этот патч независимый и может быть применён в любой момент
-- =============================================================================
DO $$ BEGIN -- Добавляем колонку embedding (если её ещё нет)
IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name = 'osmotr'
        AND column_name = 'embedding'
) THEN
ALTER TABLE osmotr
ADD COLUMN embedding vector(1536);
RAISE NOTICE 'Колонка embedding добавлена в osmotr';
ELSE RAISE NOTICE 'Колонка embedding уже существует в osmotr';
END IF;
END;
$$;
-- Создаём HNSW индекс (будет пустым пока не заполним embeddings)
CREATE INDEX IF NOT EXISTS idx_osmotr_embedding_hnsw ON osmotr USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
-- Функция векторного поиска по осмотрам
CREATE OR REPLACE FUNCTION vector_search_osmotr(
        query_vector vector(1536),
        search_limit INTEGER DEFAULT 10
    ) RETURNS TABLE (
        date TIMESTAMP,
        koloda_id VARCHAR,
        status VARCHAR,
        info TEXT,
        similarity REAL
    ) AS $$ BEGIN RETURN QUERY
SELECT o.date,
    o.koloda_id,
    o.status,
    o.info,
    (1 - (o.embedding <=> query_vector))::REAL AS similarity
FROM osmotr o
WHERE o.embedding IS NOT NULL
ORDER BY o.embedding <=> query_vector
LIMIT search_limit;
END;
$$ LANGUAGE plpgsql;
COMMENT ON FUNCTION vector_search_osmotr IS 'Векторный поиск по осмотрам колод.
Использует косинусное расстояние в пространстве embeddings.
Примеры: поиск похожих проблем, состояний, планов действий.';
-- Записываем в журнал
INSERT INTO schema_version (version, patch_name, description)
VALUES (
        4,
        '004_add_osmotr_vectors.sql',
        'Vector search for osmotr table'
    ) ON CONFLICT (version) DO NOTHING;
-- Проверка
SELECT COUNT(*) as total_osmotr,
    COUNT(embedding) as with_embedding
FROM osmotr;