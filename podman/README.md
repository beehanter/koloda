# Podman - Конфигурация базы данных

Эта директория содержит файлы для настройки, инициализации и управления базой данных PostgreSQL с поддержкой геопространственных данных и векторного поиска.

---

## 📁 Содержимое

### Основные файлы

- **`Dockerfile`**: Инструкции для сборки кастомного образа PostgreSQL 17, который включает:
  - **PostGIS 3.6+** — геопространственные функции для работы с координатами
  - **pgvector 0.7.4** — векторный поиск и semantic embeddings
  - **pg_trgm** — нечёткий текстовый поиск (fuzzy matching)
  - **pgcrypto** — криптографические функции для row_hash

- **`init.sql`**: SQL-скрипт инициализации базы данных (Phase 1). Выполняется автоматически при первом запуске контейнера. Создаёт:
  - **Таблицы**: `beekeepers`, `place`, `koloda`, `osmotr`, `paseki`, `test`, `kg_edges`, `schema_version`
  - **Индексы**: Full-text search (GIN), геопространственные (GIST), foreign keys
  - **Триггеры**: Автоматическое обновление `content_tsv` для полнотекстового поиска
  - **Функции**: `vector_search_koloda()` для базового векторного поиска
  - **Структуру для AI**: Колонка `embedding vector(1536)` готова для Phase 2A

### Дополнительные директории

- **`patches/`**: SQL-патчи для пошагового расширения функциональности (Phase 2+)
  - `002_add_hnsw.sql` — HNSW индекс для векторного поиска
  - `003_add_hybrid_search.sql` — гибридный поиск с RRF (Reciprocal Rank Fusion)
  - `004_add_osmotr_vectors.sql` — расширение векторного поиска на таблицу `osmotr`
  - `README.md` — документация по применению патчей

- **`scripts/`**: Утилиты для управления схемой БД
  - `apply_patch.sh` — безопасное применение SQL-патчей
  - `check_schema.sql` — диагностика состояния схемы БД

---

## 🚀 Использование

### Запуск базы данных

Конфигурация управляется через файл `docker-compose.yml` в корне проекта:

Сборка образа (только при первом запуске или после изменения Dockerfile)
podman-compose build

Запуск контейнера
podman-compose up -d

Просмотр логов
podman logs -f koloda-postgres

Остановка
podman-compose down

Полная пересборка (удаляет данные!)
podman-compose down -v
podman-compose build --no-cache
podman-compose up -d

text

### Подключение к базе данных

Интерактивная консоль PostgreSQL
podman exec -it koloda-postgres psql -U bee -d bee

Выполнение SQL-команды
podman exec koloda-postgres psql -U bee -d bee -c "SELECT * FROM schema_version;"

Выполнение SQL-файла
podman exec -i koloda-postgres psql -U bee -d bee < script.sql

text

### Проверка состояния

Список таблиц
podman exec koloda-postgres psql -U bee -d bee -c "\dt"

Установленные расширения
podman exec koloda-postgres psql -U bee -d bee -c "\dx"

Версия схемы
podman exec koloda-postgres psql -U bee -d bee -c "SELECT * FROM schema_version;"

Полная диагностика
podman exec -i koloda-postgres psql -U bee -d bee < podman/scripts/check_schema.sql

text

---

## 📊 Структура базы данных

### Основные таблицы

| Таблица | Описание | Ключевые поля |
|---------|----------|---------------|
| **beekeepers** | Пчеловоды | `beekeeper` (PK), `name`, `contact` |
| **place** | Места размещения | `place` (PK), `region`, `rayon`, `oopt` |
| **koloda** | Колоды | `koloda_id` (PK), `place` (FK), `beekeeper` (FK), `coordinates`, `embedding`, `content_tsv` |
| **osmotr** | Осмотры колод | `(date, koloda_id)` (PK), `status`, `info`, `content_tsv` |
| **paseki** | Пасеки | `(beekeeper, paseka)` (PK), `place` (FK), `coordinates` |
| **test** | Тесты на варроа | `(date, koloda_id)` (PK), `varroa_test` |
| **kg_edges** | Knowledge Graph | `from_table`, `from_id`, `to_table`, `to_id`, `relationship_type` |
| **schema_version** | Журнал версий схемы | `version` (PK), `patch_name`, `applied_at` |

### AI-готовые возможности (Phase 1)

✅ **Full-Text Search** (работает из коробки):
- Колонка `content_tsv` (tsvector) в таблицах `koloda` и `osmotr`
- Автоматическое обновление через триггеры
- GIN индексы для быстрого поиска
- Поддержка русского языка (russian stemming)

✅ **Геопространственные запросы** (PostGIS):
- Колонка `coordinates` типа `GEOMETRY(Point, 4326)`
- GIST индексы для эффективного поиска
- Функции расстояния, радиус, пересечения

✅ **Векторная структура** (готова для Phase 2A):
- Колонка `embedding vector(1536)` в таблице `koloda`
- Функция `vector_search_koloda()` для базового поиска
- Готова к применению HNSW индекса (патч 002)

✅ **Knowledge Graph** (структура готова):
- Таблица `kg_edges` для связей между сущностями
- Индексы для быстрого обхода графа
- Поддержка весов и метаданных связей

---

## 🔧 Применение патчей (Phase 2+)

### Когда применять патчи?

Патчи применяются **постепенно**, когда появляется необходимость:

- **002_add_hnsw.sql**: Когда embeddings заполнены для > 100 записей
- **003_add_hybrid_search.sql**: После применения патча 002
- **004_add_osmotr_vectors.sql**: Если нужен семантический поиск по осмотрам

### Как применить патч?

**Способ 1 (рекомендуется):** Через утилиту
cd podman/scripts
./apply_patch.sh 002_add_hnsw.sql

text

**Способ 2:** Вручную
Windows PowerShell
Get-Content podman\patches\002_add_hnsw.sql | podman exec -i koloda-postgres psql -U bee -d bee

Linux/Mac
podman exec -i koloda-postgres psql -U bee -d bee < podman/patches/002_add_hnsw.sql

text

**Проверка:**
podman exec koloda-postgres psql -U bee -d bee -c "SELECT * FROM schema_version ORDER BY version;"

text

Подробнее см. `patches/README.md`

---

## 🛠️ Разработка

### Добавление новой таблицы

1. Добавь CREATE TABLE в `init.sql` (для новых установок)
2. Создай патч в `patches/` (для обновления существующих БД)
3. Обнови `schema_version`
4. Протестируй на чистой БД

### Изменение существующей таблицы

**Не меняй `init.sql` для существующих таблиц!** Вместо этого:

1. Создай новый патч `00X_description.sql` в `patches/`
2. Используй `ALTER TABLE` для изменений
3. Примени патч через `apply_patch.sh`

Пример:
-- patches/005_add_koloda_height_index.sql
CREATE INDEX IF NOT EXISTS idx_koloda_height
ON koloda(height_koloda)
WHERE height_koloda IS NOT NULL;

INSERT INTO schema_version (version, patch_name, description)
VALUES (5, '005_add_koloda_height_index.sql', 'Index on koloda height')
ON CONFLICT (version) DO NOTHING;

text

### Откат изменений

Откат патча вручную (пример для 002)
podman exec koloda-postgres psql -U bee -d bee -c "
DROP INDEX IF EXISTS idx_koloda_embedding_hnsw;
DELETE FROM schema_version WHERE version = 2;
"

text

---

## 📚 Полезные ссылки

- [PostgreSQL 17 Documentation](https://www.postgresql.org/docs/17/)
- [PostGIS Documentation](https://postgis.net/documentation/)
- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [Podman Documentation](https://docs.podman.io/)

---

## 🆘 Troubleshooting

### Проблема: Контейнер не запускается

Проверь логи
podman logs koloda-postgres

Проверь что порт 5432 свободен
podman ps -a

text

### Проблема: Расширения не установлены

Пересобери образ
podman-compose down -v
podman-compose build --no-cache
podman-compose up -d

text

### Проблема: Таблицы не создались

Проверь что init.sql выполнился
podman logs koloda-postgres | grep "init.sql"

Примени init.sql вручную
podman exec -i koloda-postgres psql -U bee -d bee < podman/init.sql

text

### Проблема: Потерял данные после down -v

Флаг `-v` удаляет тома! Для сохранения данных:
Остановка БЕЗ удаления данных
podman-compose down

Резервная копия перед удалением
podman exec koloda-postgres pg_dump -U bee bee > backup.sql

text

---

## 📋 Версии

- **PostgreSQL**: 17.7
- **PostGIS**: 3.6+
- **pgvector**: 0.7.4
- **Schema Version**: 1 (Phase 1)

Для обновления версий измени `Dockerfile` и пересобери образ.

---

**Версия документа**: 1.0  
**Дата**: 2025-12-23  
**Статус**: Phase 1 Complete
