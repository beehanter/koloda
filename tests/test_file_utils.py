import unittest
import shutil
from pathlib import Path
from src.file_utils import find_media_files, copy_file_to_storage

class TestFileUtils(unittest.TestCase):
    """
    Тесты для утилит по работе с файлами.
    """

    def setUp(self):
        """
        Создаем временные директории и файлы для тестов.
        """
        self.test_dir = Path("temp_test_dir")
        self.memento_dir = self.test_dir / "memento"
        self.storage_dir = self.test_dir / "storage"

        # Создаем структуру папок и тестовые файлы
        (self.memento_dir / "gse" / "koloda").mkdir(parents=True, exist_ok=True)
        (self.memento_dir / "gse" / "osmotr").mkdir(parents=True, exist_ok=True)

        (self.memento_dir / "gse" / "koloda" / "photo1.jpg").touch()
        (self.memento_dir / "gse" / "koloda" / "photo2.jpeg").touch()
        (self.memento_dir / "gse" / "osmotr" / "photo3.jpg").touch()
        (self.memento_dir / "gse" / "koloda" / "data.csv").touch() # Этот файл должен игнорироваться

    def tearDown(self):
        """
        Удаляем временные директории после тестов.
        """
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_find_media_files(self):
        """
        Проверяем, что функция поиска находит только нужные файлы.
        """
        media_files = find_media_files(self.memento_dir)
        self.assertEqual(len(media_files), 3)
        
        # Проверяем, что найдены файлы с нужными расширениями
        extensions = {file.suffix.lower() for file in media_files}
        self.assertTrue(".jpg" in extensions)
        self.assertTrue(".jpeg" in extensions)
        self.assertFalse(".csv" in extensions)

    def test_copy_file_to_storage(self):
        """
        Проверяем корректность копирования файла с сохранением структуры.
        """
        source_file = self.memento_dir / "gse" / "koloda" / "photo1.jpg"
        
        # 1. Первое копирование
        destination_path = copy_file_to_storage(source_file, self.memento_dir, self.storage_dir)
        
        # Проверяем, что путь назначения корректный
        expected_path = self.storage_dir / "gse" / "koloda" / "photo1.jpg"
        self.assertEqual(destination_path, expected_path)
        
        # Проверяем, что файл физически существует
        self.assertTrue(destination_path.exists())
        
        # 2. Повторное копирование (не должно ничего делать, но должно вернуть путь)
        # Сохраняем время модификации
        first_copy_mtime = destination_path.stat().st_mtime
        
        # Повторный вызов
        destination_path_again = copy_file_to_storage(source_file, self.memento_dir, self.storage_dir)
        second_copy_mtime = destination_path_again.stat().st_mtime

        # Время модификации не должно измениться, так как shutil.copy2 не вызывался
        self.assertEqual(first_copy_mtime, second_copy_mtime)


if __name__ == '__main__':
    unittest.main()