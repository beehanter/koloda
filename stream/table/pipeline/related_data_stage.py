# stream/table/pipeline/related_data_stage.py
import streamlit as st
import pandas as pd
from .base import PipelineStage
from stream.utils.db import query_to_df
from collections import defaultdict

@st.cache_data(ttl=3600)
def get_db_schema_relations():
    """
    Извлекает реальные FOREIGN KEY связи, корректно обрабатывая составные ключи.
    Возвращает два словаря со списками кортежей:
    1. 'references_to': {table: [([fk_cols], ref_table, [ref_cols]), ...]}
    2. 'referenced_by': {table: [(fk_table, [fk_cols], [ref_cols]), ...]}
    """
    # Этот запрос корректно соединяет столбцы внешнего ключа с соответствующими столбцами первичного ключа,
    # избегая проблемы декартова произведения путем сопоставления их порядковых позиций.
    query = """
    SELECT
        fk.constraint_name,
        fk.table_name AS foreign_table,
        fk_col.column_name AS foreign_column,
        pk.table_name AS primary_table,
        pk_col.column_name AS primary_column
    FROM
        information_schema.referential_constraints AS rc
    JOIN information_schema.table_constraints AS fk
        ON rc.constraint_name = fk.constraint_name AND rc.constraint_schema = fk.table_schema
    JOIN information_schema.table_constraints AS pk
        ON rc.unique_constraint_name = pk.constraint_name AND rc.unique_constraint_schema = pk.table_schema
    JOIN information_schema.key_column_usage AS fk_col
        ON fk.constraint_name = fk_col.constraint_name AND fk.table_schema = fk_col.table_schema
    JOIN information_schema.key_column_usage AS pk_col
        ON pk.constraint_name = pk_col.constraint_name AND pk.table_schema = pk_col.table_schema
        AND fk_col.ordinal_position = pk_col.ordinal_position
    WHERE
        fk.constraint_type = 'FOREIGN KEY'
    ORDER BY
        fk.constraint_name,
        fk_col.ordinal_position;
    """
    fk_df = query_to_df(query)

    # Группировка столбцов по имени ограничения для обработки составных ключей
    constraints = {}
    for _, row in fk_df.iterrows():
        cn = row['constraint_name']
        if cn not in constraints:
            constraints[cn] = {
                'foreign_table': row['foreign_table'],
                'primary_table': row['primary_table'],
                'foreign_columns': [],
                'primary_columns': []
            }
        constraints[cn]['foreign_columns'].append(row['foreign_column'])
        constraints[cn]['primary_columns'].append(row['primary_column'])

    # Построение итоговых карт связей
    references_to = defaultdict(list)
    referenced_by = defaultdict(list)
    for _, c in constraints.items():
        # Таблица "ссылается на" (references_to) другую таблицу
        references_to[c['foreign_table']].append(
            (c['foreign_columns'], c['primary_table'], c['primary_columns'])
        )
        # На таблицу "ссылаются из" (referenced_by) другой таблицы
        referenced_by[c['primary_table']].append(
            (c['foreign_table'], c['foreign_columns'], c['primary_columns'])
        )
        
    return dict(references_to), dict(referenced_by)

class RelatedDataStage(PipelineStage):
    def __init__(self):
        super().__init__(name="🔗 Связанные данные", key="related_data")

    def render_ui(self, df: pd.DataFrame) -> bool:
        st.sidebar.divider()
        is_active = st.sidebar.checkbox("Показать связанные данные", key=f"{self.key}_is_active")

        # Этот этап активен только если выбрана строка на предыдущем этапе
        if is_active and 'selected_row' in st.session_state:
            st.session_state['hide_final_dataframe'] = True
            self.show_related_data_for_row(st.session_state['selected_row'])
            return True
        
        return False

    def show_related_data_for_row(self, selected_row: pd.Series):
        st.subheader(self.name)
        st.write(f"**Анализ для записи из таблицы `{st.session_state.get('selected_table', '...')}`:**")
        st.write(pd.DataFrame([selected_row]))
        st.write("---")
        st.write("**Найденные связанные данные:**")
        
        references_to, referenced_by = get_db_schema_relations()
        current_table = st.session_state.get('selected_table')
        found_anything = False

        # А. Ищем, НА КОГО ссылается текущая таблица
        if current_table in references_to:
            st.write("#### ⬆️ Записи, на которые ссылается эта строка:")
            for fk_cols, ref_table, ref_cols in references_to[current_table]:
                where_clauses, params, all_keys_present = [], [], True
                for fk_col, ref_col in zip(fk_cols, ref_cols):
                    if fk_col in selected_row and pd.notna(selected_row[fk_col]):
                        where_clauses.append(f'"{ref_col}" = %s')
                        params.append(selected_row[fk_col])
                    else:
                        all_keys_present = False
                        break
                
                if all_keys_present and where_clauses:
                    query = f'SELECT * FROM "{ref_table}" WHERE {" AND ".join(where_clauses)}'
                    
                    with st.spinner(f"Загружаем родительскую запись из '{ref_table}'..."):
                        try:
                            related_df = query_to_df(query, tuple(params))
                            if not related_df.empty:
                                found_anything = True
                                st.write(f"**Родительская таблица: `{ref_table}`**")
                                st.dataframe(related_df, use_container_width=True)
                        except Exception as e:
                            st.error(f"Ошибка при запросе к таблице {ref_table}: {e}")

        # Б. Ищем, КТО ссылается на текущую таблицу
        if current_table in referenced_by:
            st.write("#### ⬇️ Записи, которые ссылаются на эту строку:")
            for fk_table, fk_cols, ref_cols in referenced_by[current_table]:
                where_clauses, params, all_keys_present = [], [], True
                for ref_col, fk_col in zip(ref_cols, fk_cols):
                    if ref_col in selected_row and pd.notna(selected_row[ref_col]):
                        where_clauses.append(f'"{fk_col}" = %s')
                        params.append(selected_row[ref_col])
                    else:
                        all_keys_present = False
                        break
                
                if all_keys_present and where_clauses:
                    query = f'SELECT * FROM "{fk_table}" WHERE {" AND ".join(where_clauses)}'

                    with st.spinner(f"Ищем дочерние записи в '{fk_table}'..."):
                        try:
                            related_df = query_to_df(query, tuple(params))
                            if not related_df.empty:
                                found_anything = True
                                st.write(f"**Дочерняя таблица: `{fk_table}`**")
                                st.dataframe(related_df, use_container_width=True)
                        except Exception as e:
                            st.error(f"Ошибка при запросе к таблице {fk_table}: {e}")

        if not found_anything:
            st.info("Связанных записей в других таблицах не найдено.")


    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        # Этот этап не меняет данные, только отображает дополнительную информацию
        return df

    def show_output(self, df: pd.DataFrame):
        pass # Управляем выводом самостоятельно