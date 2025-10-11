import unittest
import os
import psycopg2
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

class TestDatabaseSchema(unittest.TestCase):
    """
    Тесты для проверки корректности схемы базы данных PostgreSQL.
    """
    
    @classmethod
    def setUpClass(cls):
        """
        Устанавливаем соединение с базой данных перед выполнением всех тестов.
        """
        try:
            cls.conn = psycopg2.connect(
                dbname=os.getenv("POSTGRES_DB"),
                user=os.getenv("POSTGRES_USER"),
                password=os.getenv("POSTGRES_PASSWORD"),
                host=os.getenv("DB_HOST", "localhost"),
                port=os.getenv("DB_PORT", "5432")
            )
            cls.cur = cls.conn.cursor()
        except psycopg2.OperationalError as e:
            raise ConnectionError("Не удалось подключиться к базе данных. Убедитесь, что контейнер запущен и переменные окружения заданы верно.") from e

    @classmethod
    def tearDownClass(cls):
        """
        Закрываем соединение с базой данных после выполнения всех тестов.
        """
        cls.cur.close()
        cls.conn.close()

    def test_tables_exist(self):
        """
        Проверяет, что все ожидаемые таблицы были созданы.
        """
        expected_tables = {'beekeepers', 'koloda', 'osmotr', 'paseki', 'test'}
        self.cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables_in_db = {row[0] for row in self.cur.fetchall()}
        
        missing_tables = expected_tables - tables_in_db
        self.assertEqual(len(missing_tables), 0, f"В базе данных отсутствуют таблицы: {', '.join(missing_tables)}")

    def test_postgis_extension_enabled(self):
        """
        Проверяет, что расширение PostGIS включено.
        """
        self.cur.execute("SELECT extname FROM pg_extension WHERE extname = 'postgis'")
        self.assertIsNotNone(self.cur.fetchone(), "Расширение PostGIS не было найдено в базе данных.")

if __name__ == '__main__':
    unittest.main()