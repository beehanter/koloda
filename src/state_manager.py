# -*- coding: utf-8 -*-
"""
Модуль для управления состоянием обработки файлов.
"""
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
import logging

def calculate_file_hash(file_path: Path) -> str:
    """Вычисляет SHA-256 хеш файла."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Читаем файл по частям для экономии памяти
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

class StateManager:
    """
    Отвечает за отслеживание изменений в файлах с помощью кеша состояний.
    """
    def __init__(self, state_file: Path):
        """
        :param state_file: Путь к JSON-файлу для хранения состояний.
        """
        self.state_file = state_file
        self.state = self._load_state()

    def _load_state(self) -> dict:
        """Загружает состояние из JSON-файла."""
        if self.state_file.exists():
            with open(self.state_file, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return {}
        return {}

    def save_state(self):
        """Атомарно сохраняет текущее состояние в JSON-файл."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.state_file.with_suffix('.tmp')
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=4)
            # Атомарное переименование
            temp_path.replace(self.state_file)
        except Exception as e:
            logging.error(f"Не удалось сохранить файл состояния: {e}")
            # Попытка удалить временный файл, если он остался
            if temp_path.exists():
                temp_path.unlink()

    def has_changed(self, file_path: Path) -> bool:
        """
        Проверяет, изменился ли файл с момента последней обработки.
        
        :param file_path: Путь к проверяемому файлу.
        :return: True, если файл новый или изменился.
        """
        file_id = str(file_path)
        last_state = self.state.get(file_id)

        if not last_state:
            logging.info(f"Обнаружен новый файл: {file_path}")
            return True

        current_mtime = file_path.stat().st_mtime
        if current_mtime != last_state.get("mtime"):
            logging.info(f"Время модификации файла {file_path} изменилось. Проверяем хеш...")
            current_hash = calculate_file_hash(file_path)
            if current_hash != last_state.get("hash"):
                logging.info(f"Хеш файла {file_path} изменился. Файл будет обработан.")
                return True
            else:
                logging.info(f"Хеш файла {file_path} не изменился. Обновляем только время модификации.")
                self.update_state(file_path) # Обновляем mtime, чтобы не проверять хеш в следующий раз
        
        return False

    def update_state(self, file_path: Path):
        """
        Обновляет состояние обработанного файла.
        
        :param file_path: Путь к обработанному файлу.
        """
        file_id = str(file_path)
        current_mtime = file_path.stat().st_mtime
        current_hash = calculate_file_hash(file_path)
        
        self.state[file_id] = {
            "mtime": current_mtime,
            "hash": current_hash,
            "processed_at": datetime.now(timezone.utc).isoformat()
        }