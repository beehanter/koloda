# streamlit/table/pipeline/group_stage.py
from .base import PipelineStage
import streamlit as st
import pandas as pd

class GroupStage(PipelineStage):
    def __init__(self):
        super().__init__("Группировка", "group")

    def render_ui(self, df: pd.DataFrame) -> bool:
        st.sidebar.subheader("Этап 2: Группировка")
        enabled = st.sidebar.checkbox("Включить группировку", False, key=f"{self.key}_enabled")
        if not enabled:
            return False

        # Выбираем только категориальные/текстовые колонки для группировки
        group_by_cols_options = df.select_dtypes(include=['object', 'category']).columns.tolist()
        
        self.group_by_cols = st.sidebar.multiselect(
            "Группировать по",
            options=group_by_cols_options,
            key=f"{self.key}_group_by"
        )

        if not self.group_by_cols:
            return False

        # Выбираем числовые колонки для агрегации
        numeric_cols = df.select_dtypes(include=pd.np.number).columns.tolist()
        self.agg_col = st.sidebar.selectbox(
            "Столбец для агрегации",
            options=numeric_cols,
            key=f"{self.key}_agg_col"
        )
        
        self.agg_func = st.sidebar.selectbox(
            "Функция агрегации",
            options=['sum', 'mean', 'count', 'min', 'max', 'nunique'],
            key=f"{self.key}_agg_func"
        )
        
        return True

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        if not self.group_by_cols or not self.agg_col or not self.agg_func:
            return df
        
        # Группируем и сбрасываем индекс, чтобы сгруппированные колонки снова стали столбцами
        return df.groupby(self.group_by_cols)[self.agg_col].agg(self.agg_func).reset_index()