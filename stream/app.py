# stream/app.py
import sys
import os
import streamlit as st

# Добавляем корневую директорию проекта в sys.path
# Это нужно, чтобы работали абсолютные импорты из любой точки проекта
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Настройка основного заголовка и иконки (опционально)
st.set_page_config(
    page_title="Пчёлы: Анализ данных",
    page_icon="🐝",
    layout="wide"
)

# Создание навигации по страницам
pages = [
    st.Page("table/table.py", title="Таблицы", icon="📊"),
    st.Page("map/map.py", title="Карта", icon="🌍"),
]

# Запуск навигации
pg = st.navigation(pages)
pg.run()
