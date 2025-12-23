-- =============================================================================
-- ПАТЧ 003: Гибридный поиск (RRF fusion)
-- =============================================================================
-- Применять: после 002 (когда HNSW работает)
-- Требует: заполненные embeddings + content_tsv в koloda
-- Использование в приложении:
--   SELECT * FROM hybrid_search_koloda('высокая ель пчеловод gse', embedding_vector, 5);
-- =============================================================================
-- Удаляем старую версию функции (если была)
DROP FUNCTION IF EXISTS hybrid_search_koloda(TEXT, vector, INTEGER, INTEGER);
-- Создаём гибридный поиск с RRF fusion
CREATE OR REPLACE FUNCTION hybrid_search_koloda(
        query_text TEXT,
        query_vector vector(1536),
        search_limit INTEGER DEFAULT 10,
        rrf_k INTEGER DEFAULT 60
    ) RETURNS TABLE (
        koloda_id VARCHAR,
        place VARCHAR,
        beekeeper VARCHAR,
        info TEXT,
        rrf_score REAL
    ) AS $$ BEGIN RETURN QUERY WITH -- Векторный поиск (семантический)
    vector_search AS (
        SELECT k.koloda_id,
            ROW_NUMBER() OVER (
                ORDER BY k.embedding <=> query_vector
            ) AS rank
        FROM koloda k
        WHERE k.embedding IS NOT NULL
        ORDER BY k.embedding <=> query_vector
        LIMIT search_limit * 5 -- Oversampling критичен для RRF
    ), -- Полнотекстовый поиск (точные термины)
    fulltext_search AS (
        SELECT k.koloda_id,
            ROW_NUMBER() OVER (
                ORDER BY ts_rank_cd(k.content_tsv, query) DESC
            ) AS rank
        FROM koloda k,
            websearch_to_tsquery('russian', query_text) query
        WHERE k.content_tsv @@ query
        ORDER BY ts_rank_cd(k.content_tsv, query) DESC
        LIMIT search_limit * 5 -- Oversampling
    ), -- Reciprocal Rank Fusion
    rrf_scores AS (
        SELECT koloda_id,
            1.0 / (rrf_k + rank) AS score
        FROM vector_search
        UNION ALL
        SELECT koloda_id,
            1.0 / (rrf_k + rank) AS score
        FROM fulltext_search
    ) -- Финальные результаты
SELECT k.koloda_id,
    k.place,
    k.beekeeper,
    k.info,
    SUM(r.score)::REAL AS rrf_score
FROM rrf_scores r
    JOIN koloda k ON k.koloda_id = r.koloda_id
GROUP BY k.koloda_id,
    k.place,
    k.beekeeper,
    k.info
ORDER BY rrf_score DESC
LIMIT search_limit;
END;
$$ LANGUAGE plpgsql;
-- Комментарии для документации
COMMENT ON FUNCTION hybrid_search_koloda IS 'Гибридный поиск: векторный + полнотекстовый с RRF (Reciprocal Rank Fusion).

ПАРАМЕТРЫ:
- query_text (TEXT): текстовый запрос для полнотекстового поиска
- query_vector (vector): embedding вектор для векторного поиска
- search_limit (INT): количество результатов (по умолчанию 10)
- rrf_k (INT): константа RRF (по умолчанию 60, меньше = больше вес топам)

ИСПОЛЬЗОВАНИЕ:
  SELECT * FROM hybrid_search_koloda(
    ''высокая колода из ели пчеловода gse'',
    embedding_vector,
    5
  );';
-- Записываем в журнал
INSERT INTO schema_version (version, patch_name, description)
VALUES (
        3,
        '003_add_hybrid_search.sql',
        'Hybrid search function (RRF fusion)'
    ) ON CONFLICT (version) DO NOTHING;