# streamlit/table/pipeline/filter_stage.py
from .base import PipelineStage
import streamlit as st

class FilterStage(PipelineStage):
    def __init__(self):
        super().__init__("Фильтрация", "filter")

    def render_ui(self, data) -> bool:
        st.sidebar.subheader("Этап 1: Фильтрация")
        enabled = st.sidebar.checkbox("Включить фильтрацию", True, key=f"{self.key}_enabled")
        if not enabled:
            # Если фильтрация выключена, сбрасываем все фильтры из состояния
            # Это важно, чтобы transform() не использовал старые значения
            self.filters = {}
            return False

        is_dict_input = isinstance(data, dict)
        self.filters = {}

        if is_dict_input:
            # РЕЖИМ КАРТЫ: отдельные фильтры для каждой таблицы
            for table_name, df in data.items():
                if df.empty:
                    continue
                st.sidebar.markdown("---")
                st.sidebar.subheader(f"Фильтры для: `{table_name}`")
                
                table_filters = {}
                cascade_df = df.copy()
                
                filterable_cols = [
                    col for col in df.select_dtypes(include=['object', 'category']).columns
                    if 1 < df[col].nunique() <= 50
                ]
                if 'koloda_id' in filterable_cols:
                    filterable_cols.remove('koloda_id')
                    filterable_cols.append('koloda_id')

                for col in filterable_cols:
                    options = cascade_df[col].dropna().unique()
                    if len(options) <= 1 and len(table_filters) > 0:
                        continue
                    
                    values = st.sidebar.multiselect(
                        f"Фильтр по `{col}`",
                        options=sorted(options),
                        key=f"{self.key}_{table_name}_{col}"
                    )
                    if values:
                        table_filters[col] = values
                        cascade_df = cascade_df[cascade_df[col].isin(values)]
                
                if table_filters:
                    self.filters[table_name] = table_filters
                    if st.sidebar.button(f"Сбросить фильтры для `{table_name}`", key=f"{self.key}_{table_name}_reset"):
                        for col in filterable_cols:
                            if f"{self.key}_{table_name}_{col}" in st.session_state:
                                del st.session_state[f"{self.key}_{table_name}_{col}"]
                        st.rerun()

        else:
            # РЕЖИМ ТАБЛИЦЫ: общие фильтры
            df = data
            if df.empty:
                return enabled and bool(self.filters)
            
            cascade_df = df.copy()
            filterable_cols = [
                col for col in df.select_dtypes(include=['object', 'category']).columns
                if 1 < df[col].nunique() <= 50
            ]
            if 'koloda_id' in filterable_cols:
                filterable_cols.remove('koloda_id')
                filterable_cols.append('koloda_id')

            single_table_filters = {}
            for col in filterable_cols:
                options = cascade_df[col].dropna().unique()
                if len(options) <= 1 and len(single_table_filters) > 0:
                    continue

                values = st.sidebar.multiselect(
                    f"Фильтр по `{col}`",
                    options=sorted(options),
                    key=f"{self.key}_{col}"
                )
                if values:
                    single_table_filters[col] = values
                    cascade_df = cascade_df[cascade_df[col].isin(values)]
            
            if single_table_filters:
                self.filters = single_table_filters
                if st.sidebar.button("Сбросить все фильтры", key=f"{self.key}_reset"):
                    for col in filterable_cols:
                        if f"{self.key}_{col}" in st.session_state:
                            del st.session_state[f"{self.key}_{col}"]
                    st.rerun()

        return enabled and bool(self.filters)

    def transform(self, data):
        if not self.filters:
            return data

        is_dict_input = isinstance(data, dict)

        if is_dict_input:
            # РЕЖИМ КАРТЫ: применяем фильтры для каждой таблицы
            transformed_data = {}
            for table_name, df in data.items():
                # Получаем фильтры для конкретной таблицы
                table_filters = self.filters.get(table_name, {})
                if not table_filters:
                    transformed_data[table_name] = df
                    continue
                
                filtered_df = df.copy()
                for col, vals in table_filters.items():
                    if vals and col in filtered_df.columns:
                        filtered_df = filtered_df[filtered_df[col].isin(vals)]
                transformed_data[table_name] = filtered_df
            return transformed_data
        else:
            # РЕЖИМ ТАБЛИЦЫ: применяем общие фильтры
            filtered_df = data.copy()
            for col, vals in self.filters.items():
                if vals and col in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df[col].isin(vals)]
            return filtered_df