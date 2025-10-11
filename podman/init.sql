-- Включаем необходимые расширения
CREATE EXTENSION IF NOT EXISTS postgis; -- Для работы с геоданными (координаты)
CREATE EXTENSION IF NOT EXISTS pg_trgm; -- Для эффективного текстового поиска (пока не используется, но полезно на будущее)

-- Удаляем таблицы в обратном порядке зависимостей, если они существуют, для чистого перезапуска
DROP TABLE IF EXISTS test CASCADE;
DROP TABLE IF EXISTS osmotr CASCADE;
DROP TABLE IF EXISTS paseki CASCADE;
DROP TABLE IF EXISTS koloda CASCADE;
DROP TABLE IF EXISTS beekeepers CASCADE;

-- 1. Таблица пчеловодов (справочник)
CREATE TABLE beekeepers (
    beekeeper VARCHAR(10) PRIMARY KEY, -- Уникальный идентификатор пчеловода (например, "gse")
    name VARCHAR(255),                 -- Полное имя пчеловода
    contact VARCHAR(20),               -- Контактный телефон
    adres VARCHAR(255),                -- Адрес проживания
    row_hash VARCHAR(64) UNIQUE        -- Хеш строки для отслеживания изменений
);

-- 2. Таблица колод (основная сущность)
CREATE TABLE koloda (
    koloda_id VARCHAR(10) NOT NULL,    -- Идентификатор колоды, уникален в рамках пасеки
    region VARCHAR(10) NOT NULL,       -- Код региона
    place VARCHAR(255) NOT NULL,       -- Название места (пасеки)
    date TIMESTAMP,                    -- Дата создания записи о колоде
    beekeeper VARCHAR(10) NOT NULL REFERENCES beekeepers(beekeeper), -- Внешний ключ к таблице пчеловодов
    tree VARCHAR(255),                 -- Порода дерева, из которого сделана колода
    material VARCHAR(255),             -- Материал (если не дерево)
    tipe VARCHAR(255),                 -- Тип колоды (естественное дупло, искусственная)
    height_loc REAL,                   -- Высота расположения над землей
    letok_orient VARCHAR(50),          -- Ориентация летка по сторонам света
    diametr_out REAL,                  -- Внешний диаметр колоды
    diametr_in REAL,                   -- Внутренний диаметр
    height_koloda REAL,                -- Высота колоды
    foto VARCHAR(512),                 -- Путь к файлу с фотографией колоды (в `storage`)
    pro_foto TEXT,                     -- Описание фотографии
    info TEXT,                         -- Дополнительная информация
    coordinates GEOMETRY(Point, 4326), -- Географические координаты (точка в системе WGS 84)
    row_hash VARCHAR(64),              -- Хеш строки для отслеживания изменений
    PRIMARY KEY (koloda_id, region, place, beekeeper) -- Составной первичный ключ для уникальности колоды
);

-- 3. Таблица осмотров
CREATE TABLE osmotr (
    date TIMESTAMP NOT NULL,           -- Дата и время осмотра (часть составного ключа)
    koloda_id VARCHAR(10) NOT NULL,    -- Идентификатор колоды (часть ключа)
    region_id VARCHAR(10) NOT NULL,    -- Код региона (часть ключа)
    place_id VARCHAR(255) NOT NULL,    -- Название места (часть ключа)
    beekeeper_id VARCHAR(10) NOT NULL, -- Идентификатор пчеловода (часть ключа)
    status VARCHAR(255),               -- Статус колоды по результатам осмотра (пчелы, пусто и т.д.)
    foto_out VARCHAR(512),             -- Фотография снаружи
    pro_foto_out TEXT,                 -- Описание фото снаружи
    foto_in VARCHAR(512),              -- Фотография внутри
    pro_foto_in TEXT,                  -- Описание фото внутри
    info TEXT,                         -- Дополнительная информация об осмотре
    plan TEXT,                         -- План дальнейших работ
    date_plan DATE,                    -- Дата планируемых работ
    row_hash VARCHAR(64),              -- Хеш строки для отслеживания изменений
    PRIMARY KEY (date, koloda_id, region_id, place_id, beekeeper_id), -- Составной ключ для уникальности осмотра
    FOREIGN KEY (koloda_id, region_id, place_id, beekeeper_id) REFERENCES koloda(koloda_id, region, place, beekeeper) -- Связь с таблицей колод
);

-- 4. Таблица пасек
CREATE TABLE paseki (
    beekeeper VARCHAR(10) NOT NULL REFERENCES beekeepers(beekeeper), -- Идентификатор пчеловода (часть ключа)
    adres VARCHAR(255) NOT NULL,       -- Адрес пасеки (часть ключа)
    date TIMESTAMP,                    -- Дата создания записи
    place VARCHAR(255),                -- Название места (дублирует `koloda.place` для удобства)
    coordinates GEOMETRY(Point, 4326), -- Координаты пасеки
    date_start DATE,                   -- Дата основания пасеки
    many_bees INTEGER,                 -- Примерное количество пчел на пасеке
    obrabotki TEXT,                    -- Информация о проведенных обработках
    poroda VARCHAR(255),               -- Основная порода пчел на пасеке
    data_poroda VARCHAR(512),          -- Ссылка на документ с данными о породе (Яндекс.Диск)
    foto VARCHAR(512),                 -- Фотография пасеки
    row_hash VARCHAR(64),              -- Хеш строки для отслеживания изменений
    PRIMARY KEY (beekeeper, adres)     -- Составной ключ для уникальности пасеки
);

-- 5. Таблица тестов (например, на варроатоз)
CREATE TABLE test (
    date TIMESTAMP NOT NULL,           -- Дата и время теста (часть составного ключа)
    koloda_id VARCHAR(10) NOT NULL,    -- Идентификатор колоды (часть ключа)
    region_id VARCHAR(10) NOT NULL,    -- Код региона (часть ключа)
    place_id VARCHAR(255) NOT NULL,    -- Название места (часть ключа)
    beekeeper_id VARCHAR(10) NOT NULL, -- Идентификатор пчеловода (часть ключа)
    poroda VARCHAR(255),               -- Порода пчел в колоде на момент теста
    data_poroda VARCHAR(512),          -- Ссылка на данные о породе
    foto_varroa VARCHAR(512),          -- Фотография, относящаяся к тесту
    varroa_test VARCHAR(50),           -- Результат теста на варроатоз
    row_hash VARCHAR(64),              -- Хеш строки для отслеживания изменений
    PRIMARY KEY (date, koloda_id, region_id, place_id, beekeeper_id), -- Составной ключ для уникальности теста
    FOREIGN KEY (koloda_id, region_id, place_id, beekeeper_id) REFERENCES koloda(koloda_id, region, place, beekeeper) -- Связь с таблицей колод
);

-- Индексы для ускорения выборок по внешним ключам и часто используемым полям
CREATE INDEX idx_koloda_beekeeper ON koloda(beekeeper);
CREATE INDEX idx_osmotr_keys ON osmotr(koloda_id, region_id, place_id, beekeeper_id);
CREATE INDEX idx_test_keys ON test(koloda_id, region_id, place_id, beekeeper_id);
CREATE INDEX idx_paseki_beekeeper ON paseki(beekeeper);