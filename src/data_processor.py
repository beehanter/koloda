# -*- coding: utf-8 -*-
"""
Модуль для обработки и преобразования данных перед загрузкой в БД.
"""
import hashlib
import pandas as pd
from pathlib import Path
import logging

def transform_photo_path(original_path: str, csv_file_path: Path, memento_dir: Path, storage_dir: Path) -> str | None:
    """
    Преобразует исходный путь к фото из формата Memento 
    в относительный путь для папки storage.

    :param original_path: Исходная строка пути (e.g., "file:///.../photo.jpg").
    :param csv_file_path: Путь к CSV файлу, в котором найдена эта запись.
    :param memento_dir: Корневая папка-источник.
    :param storage_dir: Корневая папка-приемник.
    :return: Новый относительный путь (e.g., "gse/koloda/photo.jpg").
    """
    if not isinstance(original_path, str) or not original_path:
        return None
    
    # Извлекаем только имя файла
    file_name = Path(original_path).name
    
    # Путь к фото должен быть в той же папке, что и CSV
    # Например, фото для `memento/gse/koloda/koloda.csv` лежит в `memento/gse/koloda/`
    photo_path_in_memento = csv_file_path.parent / file_name

    if not photo_path_in_memento.exists():
        logging.warning(f"Файл фото не найден по пути: {photo_path_in_memento}")
        return None

    # Вычисляем относительный путь от корня `memento`
    relative_path = photo_path_in_memento.relative_to(memento_dir)

    # Возвращаем путь в виде строки для записи в БД
    return str(relative_path)


def transform_coordinates(coord_string: str) -> str | None:
    """
    Преобразует строку с координатами "lat,lon" в PostGIS-совместимый
    формат "POINT(lon lat)".

    :param coord_string: Строка с координатами (e.g., "56.1959878,42.7476128").
    :return: Строка для PostGIS или None.
    """
    if not isinstance(coord_string, str) or ',' not in coord_string:
        return None
    
    try:
        lat_str, lon_str = map(str.strip, coord_string.split(','))
        # Проверяем, что координаты являются числами
        lat, lon = float(lat_str), float(lon_str)
        return f"POINT({lon} {lat})"
    except (ValueError, IndexError):
        logging.warning(f"Некорректные координаты: '{coord_string}'")
        return None

def generate_row_hash(row: pd.Series) -> str:
    """
    Генерирует SHA-256 хеш для строки данных (pandas Series).
    Все значения приводятся к строке и конкатенируются.

    :param row: Строка данных из DataFrame.
    :return: 64-символьный hex-хеш.
    """
    # Собираем все значения строки в одну строку, заменяя NaN на пустую строку
    # Собираем все значения строки в одну строку, заменяя NaN на пустую строку
    combined_string = "".join("" if pd.isna(v) else str(v) for v in row.values)
    
    return hashlib.sha256(combined_string.encode('utf-8')).hexdigest()
