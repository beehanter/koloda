# streamlit/table/pipeline/filter_stage.py
from .base import PipelineStage
import streamlit as st
import pandas as pd

class FilterStage(PipelineStage):
    def __init__(self):
        super().__init__("Фильтрация", "filter")

    def render_ui(self, df: pd.DataFrame) -> bool:
        st.sidebar.subheader("Этап 1: Фильтрация")
        enabled = st.sidebar.checkbox("Включить фильтрацию", True, key=f"{self.key}_enabled")
        if not enabled:
            return False

        self.filters = {}
        # Показываем фильтр только для столбцов с небольшим числом уникальных значений
        for col in df.select_dtypes(include=['object', 'category']).columns:
            if 1 < df[col].nunique() <= 50:
                values = st.sidebar.multiselect(
                    f"Фильтр по `{col}`",
                    options=df[col].dropna().unique(),
                    key=f"{self.key}_{col}"
                )
                if values:
                    self.filters[col] = values
        
        # Возвращаем True, если этап включен и есть хотя бы один активный фильтр
        return enabled and bool(self.filters)

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        if not self.filters:
            return df
        
        # Создаем копию, чтобы не изменять оригинальный DataFrame на предыдущих этапах
        filtered_df = df.copy()
        for col, vals in self.filters.items():
            if vals: # Убедимся, что список значений не пуст
                filtered_df = filtered_df[filtered_df[col].isin(vals)]
        return filtered_df