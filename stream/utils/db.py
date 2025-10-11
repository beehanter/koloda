# streamlit/utils/db.py
import psycopg2
import pandas as pd
from psycopg2 import sql
from contextlib import contextmanager

# Параметры подключения — можно вынести в config.py позже
DB_CONFIG = {
    "host": "localhost",      # так как Podman пробрасывает порт на localhost
    "port": 5432,             # стандартный порт PostgreSQL
    "database": "bee",     # имя вашей БД
    "user": "bee",    # ваш пользователь
    "password": "bee" # ваш пароль
}

@contextmanager
def get_db_connection():
    """Контекстный менеджер для безопасного подключения к БД."""
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        yield conn
    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()

def query_to_df(query: str, params: tuple = None) -> pd.DataFrame:
    """
    Выполняет SQL-запрос и возвращает результат как pandas DataFrame.
    
    Параметры:
        query (str): SQL-запрос (рекомендуется использовать %s для параметров)
        params (tuple, optional): Параметры для запроса (защита от SQL-инъекций)
    
    Пример:
        df = query_to_df("SELECT * FROM koloda WHERE beekeeper = %s", ("gse",))
    """
    with get_db_connection() as conn:
        return pd.read_sql(query, conn, params=params)