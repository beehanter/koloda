# streamlit/table/pipeline/sort_stage.py
from .base import PipelineStage
import streamlit as st
import pandas as pd

class SortStage(PipelineStage):
    def __init__(self):
        super().__init__("Сортировка", "sort")

    def render_ui(self, df: pd.DataFrame) -> bool:
        st.sidebar.subheader("Этап 3: Сортировка")
        enabled = st.sidebar.checkbox("Включить сортировку", False, key=f"{self.key}_enabled")
        if not enabled:
            return False

        # Предлагаем для сортировки все колонки, доступные на данном этапе
        self.sort_col = st.sidebar.selectbox(
            "Сортировать по столбцу",
            options=["(нет)"] + df.columns.tolist(),
            key=f"{self.key}_col"
        )
        
        if self.sort_col == "(нет)":
            return False

        self.ascending = st.sidebar.checkbox("По возрастанию", True, key=f"{self.key}_asc")
        return True

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.sort_col and self.sort_col != "(нет)" and self.sort_col in df.columns:
            return df.sort_values(by=self.sort_col, ascending=self.ascending)
        return df