# stream/map/pipeline/map_config.py
import streamlit as st

class MapConfig:
    def render_ui(self):
        """
        Отображает UI для настроек карты и возвращает словарь с настройками.
        """
        st.header("⚙️ Настройки карты")
        
        settings = {}
        
        # Чекбокс для включения/отключения буфера
        show_buffer = st.checkbox("Показать буферную зону", value=False)
        
        if show_buffer:
            # Слайдер для выбора радиуса буфера
            buffer_radius = st.slider(
                "Радиус буфера (метры)",
                min_value=100,
                max_value=10000,
                value=1000,
                step=100,
                help="Выберите радиус для построения буферной зоны вокруг точек."
            )
            settings['buffer_radius'] = buffer_radius
        else:
            settings['buffer_radius'] = 0
            
        return settings