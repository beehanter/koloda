# streamlit/table/pipeline/base.py
from abc import ABC, abstractmethod
import streamlit as st
import pandas as pd

class PipelineStage(ABC):
    def __init__(self, name: str, key: str):
        self.name = name
        self.key = key  # уникальный ключ для st.sidebar

    @abstractmethod
    def render_ui(self, df: pd.DataFrame) -> bool:
        """Отображает UI в sidebar. Возвращает True, если этап активен."""
        pass

    @abstractmethod
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Применяет преобразование к DataFrame."""
        pass

    def show_output(self, df: pd.DataFrame):
        """Опционально: показывает результат этапа."""
        with st.expander(f"Результат: {self.name}", expanded=False):
            st.dataframe(df, use_container_width=True)