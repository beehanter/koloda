import streamlit as st
from stream.map.pipeline.table_selector import TableSelector
from stream.map.pipeline.filter_stage import FilterStage
from stream.map.pipeline.map_config import MapConfig
from stream.map.pipeline.map_renderer import MapRenderer
from stream.map.utils.geo_utils import PostGISProcessor

def show():
    """
    Основная функция для отображения страницы с картой.
    Оркестрирует работу всех компонентов пайплайна.
    """
    st.title("🌍 Географическая карта данных")

    # Инициализация компонентов
    table_selector = TableSelector()
    filter_stage = FilterStage()
    map_config = MapConfig()
    map_renderer = MapRenderer()
    geo_processor = PostGISProcessor()

    with st.sidebar:
        # 1. Выбор таблиц
        selected_tables = table_selector.render_ui()
    
    if not selected_tables:
        st.info("Выберите хотя бы одну таблицу для отображения на карте.")
        return
    
    # 2. Загрузка и преобразование PostGIS данных
    data_sources = {}
    for table in selected_tables:
        # Загружаем сырые данные с PostGIS geometry
        raw_df = geo_processor.load_geo_table(table)
        if raw_df is not None and not raw_df.empty:
            # Преобразуем geometry в latitude/longitude
            processed_df = geo_processor.process_geometry(raw_df, table)
            data_sources[table] = processed_df
    
    if not data_sources:
        st.error("Не удалось загрузить геоданные из выбранных таблиц.")
        return
    
    # 3. Применение фильтров
    with st.sidebar:
        filtered_data = filter_stage.render_ui(data_sources)
    
    # 4. Настройка карты
    with st.sidebar:
        map_settings = map_config.render_ui()
    
    # 5. Отрисовка карты
    map_renderer.render(filtered_data, map_settings)

if __name__ == "__main__":
    show()