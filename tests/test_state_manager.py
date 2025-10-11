import unittest
import shutil
import time
from pathlib import Path
from src.state_manager import StateManager

class TestStateManager(unittest.TestCase):
    """
    Тесты для менеджера состояний.
    """

    def setUp(self):
        self.test_dir = Path("temp_state_test_dir")
        self.test_dir.mkdir()
        self.state_file = self.test_dir / "state.json"
        self.test_file = self.test_dir / "test_data.csv"
        
        with open(self.test_file, "w") as f:
            f.write("initial content")

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_new_file_has_changed(self):
        """Проверяем, что новый файл определяется как измененный."""
        sm = StateManager(self.state_file)
        self.assertTrue(sm.has_changed(self.test_file))

    def test_unchanged_file(self):
        """Проверяем, что неизмененный файл не определяется как измененный."""
        sm = StateManager(self.state_file)
        # 1. "Обрабатываем" файл в первый раз
        sm.update_state(self.test_file)
        sm.save_state()
        
        # 2. Создаем новый экземпляр менеджера, который загрузит состояние
        sm2 = StateManager(self.state_file)
        self.assertFalse(sm2.has_changed(self.test_file))
        
    def test_changed_file_content(self):
        """Проверяем, что файл с измененным контентом определяется как измененный."""
        sm = StateManager(self.state_file)
        sm.update_state(self.test_file)
        sm.save_state()
        
        # Ждем немного, чтобы время модификации гарантированно отличалось
        time.sleep(0.01)
        
        # Меняем контент
        with open(self.test_file, "w") as f:
            f.write("updated content")
            
        sm2 = StateManager(self.state_file)
        self.assertTrue(sm2.has_changed(self.test_file))

    def test_state_save_and_load(self):
        """Проверяем корректность сохранения и загрузки состояния."""
        sm = StateManager(self.state_file)
        sm.update_state(self.test_file)
        sm.save_state()
        
        # Проверяем, что файл state.json был создан
        self.assertTrue(self.state_file.exists())
        
        # Создаем новый менеджер и проверяем, что он загрузил состояние
        sm2 = StateManager(self.state_file)
        self.assertIn(str(self.test_file), sm2.state)
        self.assertIsNotNone(sm2.state[str(self.test_file)].get("hash"))

if __name__ == '__main__':
    unittest.main()