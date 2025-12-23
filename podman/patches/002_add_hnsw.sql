-- =============================================================================
-- ПАТЧ 002: HNSW индекс для векторного поиска
-- =============================================================================
-- Применять: когда embeddings реально заполнены (> 100 записей)
-- Проверка готовности:
--   SELECT COUNT(*) as total, COUNT(embedding) as with_embedding FROM koloda;
-- =============================================================================
DO $$
DECLARE records_with_embeddings INTEGER;
BEGIN -- Проверяем, есть ли embeddings
SELECT COUNT(*) INTO records_with_embeddings
FROM koloda
WHERE embedding IS NOT NULL;
IF records_with_embeddings < 10 THEN RAISE NOTICE 'ВНИМАНИЕ: Всего % записей с embeddings. HNSW индекс НЕ создан (нужно минимум 10).',
records_with_embeddings;
ELSE -- Создаём HNSW индекс (идемпотентно)
CREATE INDEX IF NOT EXISTS idx_koloda_embedding_hnsw ON koloda USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
RAISE NOTICE 'HNSW индекс успешно создан для % записей',
records_with_embeddings;
-- Записываем в журнал
INSERT INTO schema_version (version, patch_name, description)
VALUES (
        2,
        '002_add_hnsw.sql',
        'HNSW index for koloda.embedding'
    ) ON CONFLICT (version) DO NOTHING;
RAISE NOTICE 'Версия 2 записана в schema_version';
END IF;
END;
$$;
-- Проверка результата
SELECT schemaname,
    tablename,
    indexname,
    CASE
        WHEN indexdef LIKE '%m = 16%' THEN 'HNSW(m=16, ef_construction=64)'
        ELSE 'Unknown config'
    END as config
FROM pg_indexes
WHERE indexname = 'idx_koloda_embedding_hnsw';