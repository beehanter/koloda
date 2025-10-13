# stream/map/pipeline/filter_stage.py
import streamlit as st

# Явная конфигурация полей для фильтрации по каждой таблице
FILTER_CONFIG = {
    "koloda": ["koloda_id", "region", "place", "beekeeper", "tree", "material", "tipe"],
    "paseki": ["beekeeper", "adres", "place", "many_bees", "obrabotki", "poroda"]
}

class FilterStage:
    def render_ui(self, data_sources: dict) -> dict:
        """
        Отображает UI для фильтрации и применяет фильтры,
        используя явную конфигурацию полей для каждой таблицы.
        """
        st.header("🔎 Фильтры")

        if not data_sources:
            st.warning("Нет данных для фильтрации.")
            return {}

        # Создаем копию для мутабельных операций
        filtered_data = data_sources.copy()

        with st.expander("Панель фильтров", expanded=True):
            # 1. Глобальный текстовый поиск
            search_query = st.text_input("Поиск по тексту", help="Поиск по всем текстовым полям во всех выбранных таблицах.")

            # Применяем текстовый поиск, если он есть
            if search_query:
                for table_name, df in filtered_data.items():
                    if df is None or df.empty:
                        continue
                    
                    text_cols = df.select_dtypes(include=['object', 'string']).columns
                    if not text_cols.empty:
                        mask = df[text_cols].apply(lambda col: col.str.contains(search_query, case=False, na=False)).any(axis=1)
                        filtered_data[table_name] = df[mask]

            # 2. Создание и применение фильтров по колонкам для каждой таблицы
            for table_name, df in data_sources.items():
                # Работаем с уже отфильтрованным (поиском) датафреймом
                df_to_filter = filtered_data.get(table_name)

                if df_to_filter is None or df_to_filter.empty:
                    continue

                filter_cols = FILTER_CONFIG.get(table_name, [])
                
                st.subheader(f"Фильтры для '{table_name}'")
                
                for col in filter_cols:
                    if col in df.columns: # Проверяем наличие колонки в оригинальном DF
                        # Используем оригинальный DF для получения всех возможных опций
                        options = sorted(df[col].dropna().unique())
                        
                        if len(options) >= 1:
                            filter_key = f"filter_{table_name}_{col}"
                            selected = st.multiselect(
                                f"по '{col}'",
                                options=options,
                                key=filter_key
                            )
                            if selected:
                                # Применяем фильтр к текущему состоянию filtered_data
                                df_to_filter = filtered_data[table_name]
                                filtered_data[table_name] = df_to_filter[df_to_filter[col].isin(selected)]

        return filtered_data
