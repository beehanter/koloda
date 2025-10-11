# streamlit/table/pipeline/slice_stage.py
from .base import PipelineStage
import streamlit as st
import pandas as pd

class SliceStage(PipelineStage):
    def __init__(self):
        super().__init__("Срез данных", "slice")

    def render_ui(self, df: pd.DataFrame) -> bool:
        st.sidebar.subheader("Этап 4: Срез данных")
        enabled = st.sidebar.checkbox("Включить срез", False, key=f"{self.key}_enabled")
        if not enabled:
            return False

        max_rows = len(df)
        self.start_row, self.end_row = st.sidebar.slider(
            "Выберите диапазон строк",
            min_value=0,
            max_value=max_rows,
            value=(0, min(100, max_rows)), # По умолчанию показываем первые 100 строк
            key=f"{self.key}_slider"
        )
        
        return True

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        return df.iloc[self.start_row:self.end_row]