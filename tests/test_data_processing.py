import unittest
import pandas as pd
from src.data_processor import (
    parse_composite_key, 
    transform_coordinates, 
    generate_row_hash,
    transform_photo_path
)
from pathlib import Path

class TestDataProcessing(unittest.TestCase):
    """
    Тесты для функций обработки данных.
    """

    def test_parse_composite_key(self):
        """
        Тестирует функцию парсинга составного ключа 'koloda'.
        """
        self.assertEqual(
            parse_composite_key("1 _33 _Лухский _gse"), 
            ('1', '33', 'Лухский', 'gse')
        )
        self.assertEqual(parse_composite_key("некорректная_строка"), (None, None, None, None))
        self.assertEqual(parse_composite_key("1 _2 _3"), (None, None, None, None)) # Не хватает части
        self.assertEqual(parse_composite_key(None), (None, None, None, None))
        self.assertEqual(parse_composite_key(""), (None, None, None, None))

    def test_transform_photo_path(self):
        """
        Тестирует функцию преобразования пути к фото.
        На данном этапе она является заглушкой.
        """
        original_path = "file:///.../sergeyomlevo 2025-09-23 00.04.55.jpg"
        csv_path = Path("memento/gse/koloda/koloda.csv")
        memento_dir = Path("memento")
        storage_dir = Path("storage")
        
        expected = str(storage_dir / "gse/koloda/sergeyomlevo 2025-09-23 00.04.55.jpg")
        
        self.assertEqual(transform_photo_path(original_path, csv_path, memento_dir, storage_dir), expected)
        self.assertIsNone(transform_photo_path(None, csv_path, memento_dir, storage_dir))
        self.assertIsNone(transform_photo_path("", csv_path, memento_dir, storage_dir))

    def test_transform_coordinates(self):
        """
        Тестирует функцию преобразования координат в формат PostGIS.
        """
        self.assertEqual(
            transform_coordinates("56.1959878,42.7476128"), 
            "POINT(42.7476128 56.1959878)"
        )
        self.assertEqual(
            transform_coordinates("  56.1,  42.7  "), 
            "POINT(42.7 56.1)"
        )
        self.assertIsNone(transform_coordinates("некорректная строка"))
        self.assertIsNone(transform_coordinates("56.1959878 42.7476128")) # без запятой
        self.assertIsNone(transform_coordinates(None))

    def test_generate_row_hash(self):
        """
        Тестирует функцию генерации хеша для строки данных.
        """
        data1 = {'col1': 'a', 'col2': 1, 'col3': None}
        data2 = {'col1': 'a', 'col2': 1, 'col3': None}
        data3 = {'col1': 'b', 'col2': 2, 'col3': 'c'}
        
        row1 = pd.Series(data1)
        row2 = pd.Series(data2)
        row3 = pd.Series(data3)
        
        hash1 = generate_row_hash(row1)
        hash2 = generate_row_hash(row2)
        hash3 = generate_row_hash(row3)
        
        # Хеши для идентичных строк должны совпадать
        self.assertEqual(hash1, hash2)
        
        # Хеши для разных строк должны отличаться
        self.assertNotEqual(hash1, hash3)
        
        # Проверяем формат хеша
        self.assertEqual(len(hash1), 64)
        self.assertTrue(all(c in '0123456789abcdef' for c in hash1))

if __name__ == '__main__':
    unittest.main()