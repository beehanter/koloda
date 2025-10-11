# stream/table/pipeline/search_stage.py
import streamlit as st
import pandas as pd
from .base import PipelineStage

class SearchStage(PipelineStage):
    def __init__(self):
        super().__init__(name="🔍 Поиск", key="search")
        self.search_query = ""

    def render_ui(self, df: pd.DataFrame) -> bool:
        """Отображает UI в sidebar."""
        st.sidebar.divider()
        st.sidebar.subheader(self.name)
        
        self.search_query = st.sidebar.text_input(
            "Введите текст для поиска по всей таблице",
            key=f"{self.key}_query"
        )
        
        # Этап считается активным, если в поле поиска есть текст
        return bool(self.search_query.strip())

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Фильтрует DataFrame по поисковому запросу."""
        if not self.search_query or not self.search_query.strip():
            return df

        # Приводим все данные к строковому типу для универсального поиска
        df_str = df.astype(str)
        
        # Ищем совпадения в любой ячейке строки (без учета регистра)
        mask = df_str.apply(
            lambda row: row.str.contains(self.search_query, case=False, na=False).any(),
            axis=1
        )
        
        return df[mask]