# -*- coding: utf-8 -*-
"""
Модуль для утилит по работе с файлами.
Включает функции для поиска, копирования и обработки файлов проекта.
"""

import os
import shutil
from pathlib import Path
import logging

def find_media_files(source_dir: Path, extensions: list[str] = None) -> list[Path]:
    """
    Рекурсивно находит все медиафайлы в указанной директории.

    :param source_dir: Исходная директория для поиска (например, 'memento').
    :param extensions: Список расширений для поиска (например, ['.jpg', '.png']).
                       По умолчанию ['.jpg', '.jpeg'].
    :return: Список путей к найденным файлам.
    """
    if extensions is None:
        extensions = ['.jpg', '.jpeg']
    
    found_files = []
    for root, _, files in os.walk(source_dir):
        for file in files:
            if Path(file).suffix.lower() in extensions:
                found_files.append(Path(root) / file)
    return found_files

def copy_file_to_storage(source_path: Path, memento_dir: Path, storage_dir: Path) -> Path:
    """
    Копирует файл из директории memento в storage, сохраняя структуру.

    Пример:
    source_path = 'memento/gse/koloda/photo.jpg'
    memento_dir = 'memento'
    storage_dir = 'storage'
    Результат: файл будет скопирован в 'storage/gse/koloda/photo.jpg'

    :param source_path: Полный путь к исходному файлу.
    :param memento_dir: Корневая папка-источник.
    :param storage_dir: Корневая папка-приемник.
    :return: Путь к скопированному файлу.
    """
    # Вычисляем относительный путь файла внутри memento
    relative_path = source_path.relative_to(memento_dir)
    
    # Создаем целевой путь в storage
    destination_path = storage_dir / relative_path
    
    # Создаем родительские директории, если их нет
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Копируем, если файл не существует или его размер отличается
    copy = True
    if destination_path.exists():
        try:
            if destination_path.stat().st_size == source_path.stat().st_size:
                copy = False
        except FileNotFoundError:
            # Файл мог быть удален между проверкой exists() и stat()
            pass

    if copy:
        try:
            shutil.copy2(source_path, destination_path)
            logging.getLogger('my_app').info(f"Скопирован файл: {source_path} -> {destination_path}")
        except OSError as e:
            logging.getLogger('my_app').error(f"Ошибка копирования файла {source_path} в {destination_path}: {e}")
            return None
            
    return destination_path
