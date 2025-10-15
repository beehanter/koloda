# streamlit/table/table.py
import streamlit as st
from stream.utils.db import query_to_df
from stream.table.pipeline.table_selector import render_table_selector
from stream.table.pipeline.filter_stage import FilterStage
from stream.table.pipeline.group_stage import GroupStage
from stream.table.pipeline.sort_stage import SortStage
from stream.table.pipeline.slice_stage import SliceStage
from stream.table.pipeline.search_stage import SearchStage
from stream.table.pipeline.row_selector_stage import RowSelectorStage
from stream.table.pipeline.related_data_stage import RelatedDataStage

st.title("📊 Гибкий конвейер анализа данных")

# 1. Выбор таблицы
selected_table = render_table_selector()

if not selected_table:
    st.info("Пожалуйста, выберите таблицу в боковой панели, чтобы начать анализ.")
    st.stop()

# Сохраняем выбранную таблицу в состояние сессии, чтобы другие модули имели к ней доступ
st.session_state['selected_table'] = selected_table

# 2. Загрузка данных
try:
    df_original = query_to_df(f'SELECT * FROM "{selected_table}"')
    
    df_current = df_original.copy()
    st.sidebar.divider()
except Exception as e:
    st.error(f"Не удалось загрузить таблицу `{selected_table}`.")
    st.error(f"Ошибка: {e}")
    st.stop()

# 3. Инициализация этапов конвейера
stages = [
    SearchStage(),
    FilterStage(),
    GroupStage(),
    SortStage(),
    SliceStage(),
    RowSelectorStage(),
    RelatedDataStage(),
]

# 4. Применение активных этапов
# Сбрасываем флаг перед циклом
st.session_state['hide_final_dataframe'] = False
for stage in stages:
    is_active = stage.render_ui(df_current)
    if is_active:
        df_current = stage.transform(df_current)
        stage.show_output(df_current)

# 5. Финальный вывод
if not st.session_state.get('hide_final_dataframe', False):
    st.subheader("Итоговый результат")
    
    # --- Логика для отображения фото-ссылок по умолчанию ---
    df_display = df_current.copy()
    column_config = {}
    STATIC_SERVER_URL = "http://localhost:8001"
    from urllib.parse import quote

    def prepare_url(path):
        if not path or not isinstance(path, str):
            return None
        clean_path = path.replace("\\", "/").lstrip("/")
        if clean_path.startswith("storage/"):
            clean_path = clean_path[len("storage/"):]
        return f"{STATIC_SERVER_URL}/{quote(clean_path)}"

    for col in df_display.columns:
        if col.lower().startswith("foto"):
            df_display[col] = df_display[col].apply(prepare_url)
            column_config[col] = st.column_config.LinkColumn(
                label=col,
                display_text="🖼️"
            )
    # --- Конец логики ---

    st.dataframe(
        df_display,
        use_container_width=True,
        column_config=column_config
    )

# 6. Экспорт
st.sidebar.divider()
st.sidebar.download_button(
    "📥 Скачать результат (CSV)",
    df_current.to_csv(index=False).encode("utf-8"),
    f"{selected_table}_processed.csv",
    "text/csv",
    key="download-csv"
)
