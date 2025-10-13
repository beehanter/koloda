# stream/map/pipeline/table_selector.py
import streamlit as st

class TableSelector:
    def __init__(self):
        self.available_tables = ["koloda", "paseki"]
    
    def render_ui(self):
        st.sidebar.header("📋 Выбор таблиц")
        
        selected_tables = []
        for table in self.available_tables:
            if st.sidebar.checkbox(
                f"Показать {table}", 
                value=True, 
                key=f"show_{table}",
                help=f"Отобразить данные из таблицы {table} на карте"
            ):
                selected_tables.append(table)
        
        if "selected_geo_tables" not in st.session_state:
            st.session_state.selected_geo_tables = []
            
        st.session_state.selected_geo_tables = selected_tables
        return selected_tables