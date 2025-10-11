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

load_dotenv()

class DBManager:
    """
    Класс для инкапсуляции работы с базой данных.
    """
    def __init__(self):
        try:
            self.conn = psycopg2.connect(
                dbname=os.getenv("POSTGRES_DB"),
                user=os.getenv("POSTGRES_USER"),
                password=os.getenv("POSTGRES_PASSWORD"),
                host=os.getenv("DB_HOST", "localhost"),
                port=os.getenv("DB_PORT", "5432")
            )
            self.cur = self.conn.cursor()
        except psycopg2.OperationalError as e:
            logging.critical(f"Критическая ошибка подключения к БД: {e}")
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
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()

    def _execute_upsert(self, table_name: str, columns: List[str], pk_columns: List[str], data: List[Tuple]):
        """
        Универсальный метод для выполнения UPSERT. НЕ КОММИТИТ ТРАНЗАКЦИЮ.
        """
        if not data:
            return

        temp_table_name = f"temp_{table_name}"
        self.cur.execute(f"CREATE TEMP TABLE IF NOT EXISTS {temp_table_name} (LIKE {table_name} INCLUDING DEFAULTS) ON COMMIT DROP;")
        # Очищаем временную таблицу на случай, если она уже существовала
        self.cur.execute(f"TRUNCATE TABLE {temp_table_name};")

        cols_str = ", ".join(columns)
        execute_values(self.cur, f"INSERT INTO {temp_table_name} ({cols_str}) VALUES %s", data)

        update_set_str = ", ".join([f"{col} = s.{col}" for col in columns if col not in pk_columns])
        pk_join_str = " AND ".join([f"t.{pk} = s.{pk}" for pk in pk_columns])
        
        update_query = f"""
            UPDATE {table_name} t
            SET {update_set_str}
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

    def upsert_beekeepers(self, data: List[Tuple]):
        cols = ["beekeeper", "name", "contact", "adres", "row_hash"]
        pk_cols = ["beekeeper"]
        self._execute_upsert("beekeepers", cols, pk_cols, data)

    def upsert_koloda(self, data: List[Tuple]):
        cols = ["koloda_id", "region", "place", "date", "beekeeper", "tree", "material", "tipe", 
                "height_loc", "letok_orient", "diametr_out", "diametr_in", "height_koloda", 
                "foto", "pro_foto", "info", "coordinates", "row_hash"]
        pk_cols = ["koloda_id", "region", "place", "beekeeper"]
        self._execute_upsert("koloda", cols, pk_cols, data)

    def upsert_osmotr(self, data: List[Tuple]):
        cols = ["date", "koloda_id", "region_id", "place_id", "beekeeper_id", "status", 
                "foto_out", "pro_foto_out", "foto_in", "pro_foto_in", "info", 
                "plan", "date_plan", "row_hash"]
        pk_cols = ["date", "koloda_id", "region_id", "place_id", "beekeeper_id"]
        self._execute_upsert("osmotr", cols, pk_cols, data)

    def upsert_paseki(self, data: List[Tuple]):
        cols = ["beekeeper", "adres", "date", "place", "coordinates", "date_start", 
                "many_bees", "obrabotki", "poroda", "data_poroda", "foto", "row_hash"]
        pk_cols = ["beekeeper", "adres"]
        self._execute_upsert("paseki", cols, pk_cols, data)

    def upsert_test(self, data: List[Tuple]):
        cols = ["date", "koloda_id", "region_id", "place_id", "beekeeper_id", "poroda", 
                "data_poroda", "foto_varroa", "varroa_test", "row_hash"]
        pk_cols = ["date", "koloda_id", "region_id", "place_id", "beekeeper_id"]
        self._execute_upsert("test", cols, pk_cols, data)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
