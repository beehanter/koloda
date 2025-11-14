# -*- coding: utf-8 -*-
"""
Модуль для управления взаимодействием с базой данных PostgreSQL.
"""
import os
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from typing import List, Tuple
import logging
import time

load_dotenv()

class DBManager:
    """
    Класс для инкапсуляции работы с базой данных.
    """
    def __init__(self, retries=3, delay=5):
        self.conn = None
        self.cur = None
        for attempt in range(retries):
            try:
                self.conn = psycopg2.connect(
                    dbname=os.getenv("POSTGRES_DB"),
                    user=os.getenv("POSTGRES_USER"),
                    password=os.getenv("POSTGRES_PASSWORD"),
                    host=os.getenv("POSTGRES_HOST", "localhost"),
                    port=os.getenv("POSTGRES_PORT", "5432")
                )
                self.cur = self.conn.cursor()
                logging.info("Успешное подключение к базе данных.")
                break
            except psycopg2.OperationalError as e:
                logging.warning(f"Попытка {attempt + 1} из {retries}: не удалось подключиться к БД. Ошибка: {e}")
                if attempt < retries - 1:
                    time.sleep(delay)
                else:
                    logging.critical("Критическая ошибка: не удалось подключиться к базе данных после нескольких попыток.")
                    raise

    def begin(self):
        """Начинает новую транзакцию."""
        self.cur.execute("BEGIN;")

    def commit(self):
        """Фиксирует текущую транзакцию."""
        self.conn.commit()

    def rollback(self):
        """Откатывает текущую транзакцию."""
        self.conn.rollback()

    def close(self):
        if getattr(self, "cur", None):
            self.cur.close()
        if getattr(self, "conn", None):
            self.conn.close()

    def _execute_upsert(self, table_name: str, columns: List[str], pk_columns: List[str], data: List[Tuple]):
        """
        Универсальный метод для выполнения UPSERT. НЕ КОММИТИТ ТРАНЗАКЦИЮ.
        В случае ошибки выполняет откат.
        """
        if not data:
            return
        
        try:
            temp_table_name = f"temp_{table_name}_{os.getpid()}"
            self.cur.execute(f"CREATE TEMP TABLE IF NOT EXISTS {temp_table_name} (LIKE {table_name} INCLUDING DEFAULTS) ON COMMIT DROP;")
            self.cur.execute(f"TRUNCATE TABLE {temp_table_name};")

            cols_str = ", ".join(columns)
            execute_values(self.cur, f"INSERT INTO {temp_table_name} ({cols_str}) VALUES %s", data)

            # Список столбцов для обновления, исключая первичные ключи и row_hash
            update_cols = [col for col in columns if col not in pk_columns and col != 'row_hash']
            update_set_str = ", ".join([f"{col} = s.{col}" for col in update_cols])
            pk_join_str = " AND ".join([f"t.{pk} = s.{pk}" for pk in pk_columns])
            
            # Обновляем запись, только если row_hash изменился
            update_query = f"""
                UPDATE {table_name} t
                SET {update_set_str}, row_hash = s.row_hash
                FROM {temp_table_name} s
                WHERE {pk_join_str} AND t.row_hash IS DISTINCT FROM s.row_hash;
            """
            self.cur.execute(update_query)

            insert_query = f"""
                INSERT INTO {table_name} ({cols_str})
                SELECT {cols_str}
                FROM {temp_table_name} s
                WHERE NOT EXISTS (
                    SELECT 1 FROM {table_name} t WHERE {pk_join_str}
                );
            """
            self.cur.execute(insert_query)
            logging.getLogger('my_app').info(f"Таблица {table_name} обновлена: обработано {len(data)} записей.")
        except Exception:
            self.rollback()
            logging.getLogger('my_app').error(f"Ошибка во время операции UPSERT для таблицы {table_name}. Транзакция отменена.")
            raise

    def upsert_beekeepers(self, data: List[Tuple]):
        cols = ["beekeeper", "name", "contact", "adres", "row_hash"]
        pk_cols = ["beekeeper"]
        self._execute_upsert("beekeepers", cols, pk_cols, data)

    def upsert_koloda(self, data: List[Tuple]):
        cols = ["koloda_id", "date", "place", "beekeeper", "tree", "material", "tipe",
                "height_loc", "letok_orient", "diametr_out", "diametr_in", "height_koloda",
                "foto", "pro_foto", "info", "coordinates", "row_hash"]
        pk_cols = ["koloda_id"]
        self._execute_upsert("koloda", cols, pk_cols, data)

    def upsert_osmotr(self, data: List[Tuple]):
        cols = ["date", "koloda_id", "status",
                "foto_out", "pro_foto_out", "foto_in", "pro_foto_in", "info",
                "plan", "date_plan", "row_hash"]
        pk_cols = ["date", "koloda_id"]
        self._execute_upsert("osmotr", cols, pk_cols, data)

    def upsert_paseki(self, data: List[Tuple]):
        cols = ["beekeeper", "paseka", "date", "place", "coordinates", "date_start",
                "many_bees", "obrabotki", "poroda", "data_poroda", "foto", "row_hash"]
        pk_cols = ["beekeeper", "paseka"]
        self._execute_upsert("paseki", cols, pk_cols, data)

    def upsert_test(self, data: List[Tuple]):
        cols = ["date", "koloda_id", "poroda",
                "data_poroda", "foto_varroa", "varroa_test", "row_hash"]
        pk_cols = ["date", "koloda_id"]
        self._execute_upsert("test", cols, pk_cols, data)

    def upsert_place(self, data: List[Tuple]):
        cols = ["place", "region", "rayon", "oopt", "image", "row_hash"]
        pk_cols = ["place"]
        self._execute_upsert("place", cols, pk_cols, data)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
