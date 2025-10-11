# streamlit/table/pipeline/table_selector.py
import streamlit as st
from stream.utils.db import query_to_df

@st.cache_data(ttl=300)
def list_tables() -> list[str]:
    """Получает список таблиц из схемы public."""
    df = query_to_df("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    return df['table_name'].tolist()

def render_table_selector() -> str | None:
    """Отображает выбор таблицы в sidebar и возвращает имя выбранной таблицы."""
    st.sidebar.subheader("Источник данных")
    tables = list_tables()
    selected_table = st.sidebar.selectbox(
        "Выберите таблицу для анализа",
        tables,
        index=None,
        placeholder="Выберите таблицу..."
    )
    return selected_table