# stream/map/utils/geo_utils.py
import streamlit as st
from stream.utils.db import query_to_df
import logging

class PostGISProcessor:
    def __init__(self):
        self.geometry_column = 'coordinates'  # предполагаемое имя колонки
    
    def load_geo_table(self, table_name):
        """Загружает таблицу с PostGIS geometry"""
        try:
            # Сначала получаем метаданные таблицы
            column_info = query_to_df(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = '{table_name}'
            """)
            
            # Проверяем наличие geometry колонки
            geom_columns = column_info[column_info['data_type'] == 'USER-DEFINED']['column_name'].tolist()
            if not geom_columns:
                # Ищем по типу 'geometry' для большей совместимости
                geom_columns = column_info[column_info['data_type'] == 'geometry']['column_name'].tolist()

            if not geom_columns:
                st.error(f"В таблице {table_name} не найдены PostGIS geometry колонки")
                return None
            
            # Используем первую найденную geometry колонку
            geom_col = geom_columns[0]
            
            # Загружаем данные, преобразуя geometry в WKT и координаты
            query = f"""
            SELECT *,
                   ST_AsText({geom_col}) as geometry_wkt,
                   ST_X({geom_col}) as longitude,
                   ST_Y({geom_col}) as latitude
            FROM "{table_name}"
            WHERE {geom_col} IS NOT NULL
            """
            
            df = query_to_df(query)
            if df is not None:
                logging.info(f"Загружено {len(df)} записей из {table_name}")
            return df
            
        except Exception as e:
            st.error(f"Ошибка загрузки таблицы {table_name}: {str(e)}")
            logging.error(f"Ошибка загрузки таблицы {table_name}: {e}", exc_info=True)
            return None
    
    def process_geometry(self, df, table_name):
        """Дополнительная обработка geometry данных"""
        try:
            # Проверяем наличие координат
            if 'latitude' not in df.columns or 'longitude' not in df.columns:
                st.error(f"Не удалось извлечь координаты из {table_name}")
                return None
            
            # Фильтруем некорректные координаты
            valid_coords = (
                df['latitude'].notna() & 
                df['longitude'].notna() &
                (df['latitude'].between(-90, 90)) & 
                (df['longitude'].between(-180, 180))
            )
            
            filtered_df = df[valid_coords].copy()
            
            if len(filtered_df) < len(df):
                st.warning(f"Отфильтровано {len(df) - len(filtered_df)} записей с некорректными координатами в {table_name}")
            
            return filtered_df
            
        except Exception as e:
            st.error(f"Ошибка обработки geometry в {table_name}: {str(e)}")
            logging.error(f"Ошибка обработки geometry в {table_name}: {e}", exc_info=True)
            return None
    
    def add_buffered_geometry(self, df, radius, geom_col='coordinates'):
        """
        Добавляет в DataFrame столбец с GeoJSON буферной зоны.
        """
        if df is None or df.empty or radius <= 0:
            return df
 
        # Проверяем, есть ли уже столбец с геометрией в DataFrame.
        # Если нет, пытаемся его найти или создать.
        if geom_col not in df.columns:
            # Попробуем найти WKT столбец, если основной отсутствует
            if 'geometry_wkt' in df.columns:
                from shapely import wkt
                # Создаем геометрию из WKT
                df[geom_col] = df['geometry_wkt'].apply(wkt.loads)
            else:
                st.error(f"В данных отсутствует колонка геометрии '{geom_col}' для построения буфера.")
                return df
            
        # Создаем копию, чтобы не менять оригинальный DataFrame
        df_copy = df.copy()
 
        # Используем параметризованный запрос для безопасности
        # ST_Buffer работает с единицами проекции. Для метров нужна метрическая проекция (например, 3857).
        # 1. Трансформируем исходную геометрию в метрическую проекцию (SRID 3857).
        # 2. Строим буфер с заданным радиусом в метрах.
        # 3. Трансформируем результат обратно в WGS 84 (SRID 4326).
        # 4. Конвертируем геометрию буфера в формат GeoJSON для Folium.
        
        # Собираем WKT геометрии для передачи в запрос
        # Если geom_col это 'geometry_wkt', то там уже строки, иначе - объекты shapely
        if geom_col == 'geometry_wkt':
            wkt_geometries = df_copy[geom_col]
        else:
            wkt_geometries = df_copy[geom_col].apply(lambda geom: geom.wkt)
        
        # Формируем SQL-запрос для вычисления буферов
        # Мы используем VALUES для передачи набора WKT и их ID в одном запросе
        values_clause = ", ".join([f"({i}, ST_GeomFromText('{wkt}', 4326))" for i, wkt in enumerate(wkt_geometries)])
        
        if not values_clause:
            return df_copy # Возвращаем копию без изменений, если нет геометрии
 
        query = f"""
        WITH data (id, geom) AS (
            VALUES {values_clause}
        )
        SELECT
            id,
            ST_AsGeoJSON(
                ST_Buffer(geom::geography, {radius})::geometry
            ) as buffer_geojson
        FROM data
        ORDER BY id;
        """
        
        try:
            buffered_geometries = query_to_df(query)
            if buffered_geometries is not None and not buffered_geometries.empty:
                # Соединяем результат с исходным DataFrame
                # Устанавливаем индекс для корректного merge
                df_copy.reset_index(drop=True, inplace=True)
                buffered_geometries.set_index('id', inplace=True)
                df_copy = df_copy.join(buffered_geometries)
            else:
                df_copy['buffer_geojson'] = None
        except Exception as e:
            st.error(f"Ошибка при построении буферных зон: {e}")
            df_copy['buffer_geojson'] = None
 
        return df_copy

    def detect_geometry_type(self, df):
        """Определяет тип геометрии (Point, Polygon, etc.)"""
        if 'geometry_wkt' not in df.columns or df.empty:
            return None
        
        # Анализируем WKT для определения типа
        sample_wkt = df['geometry_wkt'].iloc[0] if len(df) > 0 else ''
        if sample_wkt.startswith('POINT'):
            return 'Point'
        elif sample_wkt.startswith('POLYGON'):
            return 'Polygon'
        elif sample_wkt.startswith('LINESTRING'):
            return 'LineString'
        else:
            return 'Unknown'