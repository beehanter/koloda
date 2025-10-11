import unittest
from src.db_manager import DBManager
from datetime import datetime

class TestDBManager(unittest.TestCase):
    """
    Тесты для менеджера базы данных.
    """

    @classmethod
    def setUpClass(cls):
        """Подключаемся к БД один раз для всех тестов."""
        cls.db = DBManager()

    @classmethod
    def tearDownClass(cls):
        """Закрываем соединение после всех тестов."""
        cls.db.close()

    def setUp(self):
        """Очищаем таблицы перед каждым тестом."""
        with self.db.conn.cursor() as cur:
            cur.execute("TRUNCATE beekeepers, koloda, osmotr, paseki, test RESTART IDENTITY CASCADE;")
            self.db.conn.commit()
            
            # Добавляем базового пчеловода
            self.db.upsert_beekeepers([("gse", "Гуров", "123", "Адрес1", "hash1")])

    def test_upsert_beekeepers(self):
        """Тестируем вставку и обновление пчеловодов с проверкой хеша."""
        # 1. Проверяем начальную вставку (она уже есть из setUp)
        with self.db.conn.cursor() as cur:
            cur.execute("SELECT name, row_hash FROM beekeepers WHERE beekeeper = 'gse';")
            name, row_hash = cur.fetchone()
            self.assertEqual(name, "Гуров")
            self.assertEqual(row_hash, "hash1")

        # 2. Повторная вставка с тем же хешем (ничего не должно измениться)
        self.db.upsert_beekeepers([("gse", "Гуров-другоеимя", "789", "Адрес3", "hash1")])
        with self.db.conn.cursor() as cur:
            cur.execute("SELECT name FROM beekeepers WHERE beekeeper = 'gse';")
            unchanged_name = cur.fetchone()[0]
            self.assertEqual(unchanged_name, "Гуров")

        # 3. Вставка с новым хешем (данные должны обновиться)
        self.db.upsert_beekeepers([("gse", "Гуров С.Е.", "456", "Адрес2", "hash2")])
        with self.db.conn.cursor() as cur:
            cur.execute("SELECT name, contact, row_hash FROM beekeepers WHERE beekeeper = 'gse';")
            updated_name, updated_contact, updated_hash = cur.fetchone()
            self.assertEqual(updated_name, "Гуров С.Е.")
            self.assertEqual(updated_contact, "456")
            self.assertEqual(updated_hash, "hash2")

    def test_upsert_koloda_insert_and_update(self):
        """Тестируем вставку и обновление колоды с проверкой хеша."""
        # 1. Вставка новой колоды
        koloda_data = [("1", "33", "Место1", datetime.now(), "gse", "ель", "сосна", "тип1",
                        1.5, "юг", 50.0, 40.0, 100.0, "foto1.jpg", "про фото", "инфо",
                        "POINT(42.1 56.2)", "hash1")]
        
        self.db.upsert_koloda(koloda_data)

        with self.db.conn.cursor() as cur:
            cur.execute("SELECT * FROM koloda WHERE koloda_id = '1';")
            inserted_koloda = cur.fetchone()
            self.assertIsNotNone(inserted_koloda)
            self.assertEqual(inserted_koloda[-1], "hash1") # Проверяем хеш
            self.assertEqual(inserted_koloda[5], "ель") # Проверяем данные

        # 2. Повторная вставка с тем же хешем (ничего не должно измениться)
        # Меняем данные, но оставляем хеш
        koloda_data_same_hash = [("1", "33", "Место1", datetime.now(), "gse", "липа", "дуб", "тип2",
                                  2.0, "север", 60.0, 50.0, 120.0, "foto2.jpg", "про фото2", "инфо2",
                                  "POINT(43.1 57.2)", "hash1")]
        
        self.db.upsert_koloda(koloda_data_same_hash)
        
        with self.db.conn.cursor() as cur:
            cur.execute("SELECT tree FROM koloda WHERE koloda_id = '1';")
            unchanged_tree = cur.fetchone()[0]
            # Данные не должны были поменяться
            self.assertEqual(unchanged_tree, "ель")

        # 3. Вставка с новым хешем (данные должны обновиться)
        koloda_data_new_hash = [("1", "33", "Место1", datetime.now(), "gse", "береза", "осина", "тип3",
                                 2.5, "запад", 70.0, 60.0, 130.0, "foto3.jpg", "про фото3", "инфо3",
                                 "POINT(44.1 58.2)", "hash2")]

        self.db.upsert_koloda(koloda_data_new_hash)

        with self.db.conn.cursor() as cur:
            cur.execute("SELECT tree, row_hash FROM koloda WHERE koloda_id = '1';")
            updated_data = cur.fetchone()
            # Данные должны были обновиться
            self.assertEqual(updated_data[0], "береза")
            self.assertEqual(updated_data[1], "hash2")


if __name__ == '__main__':
    unittest.main()