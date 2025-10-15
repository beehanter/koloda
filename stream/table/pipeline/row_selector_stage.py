# stream/table/pipeline/row_selector_stage.py
import streamlit as st
import pandas as pd
from .base import PipelineStage

class RowSelectorStage(PipelineStage):
    def __init__(self):
        super().__init__(name="🎯 Выбор строки", key="row_selector")

    def render_ui(self, df: pd.DataFrame) -> bool:
        st.sidebar.divider()
        is_active = st.sidebar.checkbox("Выбрать одну строку для анализа", key=f"{self.key}_is_active")

        # Сбрасываем выбранную строку, если этап выключен
        if not is_active:
            if 'selected_row' in st.session_state:
                del st.session_state['selected_row']
            return False

        if df.empty:
            st.sidebar.warning("Нет данных для выбора.")
            return True
        
        # Создаем текстовое представление для каждой строки, чтобы пользователь мог их различить
        # Используем первые 5 колонок для представления
        preview_cols = df.columns[:5].tolist()
        df_preview = df[preview_cols].astype(str).agg(' | '.join, axis=1)

        selected_row_preview = st.sidebar.selectbox(
            "Выберите строку:",
            options=df_preview,
            index=None,
            placeholder="Выберите запись...",
            key=f"{self.key}_selector"
        )

        if selected_row_preview:
            # Находим индекс выбранной строки и сохраняем ее в session_state
            selected_index = df_preview[df_preview == selected_row_preview].index[0]
            st.session_state['selected_row'] = df.loc[selected_index]
        elif 'selected_row' in st.session_state:
            # Очищаем, если выбор был сброшен
            del st.session_state['selected_row']
            
        return True

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        # Если строка выбрана, возвращаем DataFrame только с этой строкой
        if 'selected_row' in st.session_state:
            return pd.DataFrame([st.session_state['selected_row']])
        # Иначе возвращаем исходный DataFrame
        return df

    def show_output(self, df: pd.DataFrame):
        # Этот этап показывает свой результат в sidebar, основной вывод не нужен
        pass