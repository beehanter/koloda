import pandas as pd
from pathlib import Path
import logging
import numpy as np

from src.state_manager import StateManager
from src.db_manager import DBManager
from src.file_utils import find_media_files, copy_file_to_storage
from src.data_processor import (
    transform_photo_path,
    transform_coordinates,
    generate_row_hash
)

# --- Настройки ---
MEMENTO_DIR = Path("memento")
STORAGE_DIR = Path("storage")
STATE_FILE = STORAGE_DIR / "processing_state.json"

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Вспомогательная функция для конвертации типов ---

def convert_to_native_types(df: pd.DataFrame) -> list:
    """
    Конвертирует DataFrame в список кортежей с нативными типами Python.
    """
    data_for_db = []
    for row in df.itertuples(index=False, name=None):
        clean_row = []
        for val in row:
            if pd.isna(val):
                clean_row.append(None)
            elif isinstance(val, (np.integer, np.floating)):
                clean_row.append(val.item())
            elif isinstance(val, pd.Timestamp):
                clean_row.append(val.to_pydatetime())
            else:
                clean_row.append(val)
        data_for_db.append(tuple(clean_row))
    return data_for_db

# --- Функции-обработчики для каждого типа CSV ---

def process_beekeepers(df: pd.DataFrame, db: DBManager):
    df['row_hash'] = df.apply(generate_row_hash, axis=1)
    db.upsert_beekeepers(convert_to_native_types(df))

def process_koloda(df: pd.DataFrame, db: DBManager, csv_path: Path):
    df.rename(columns={'koloda': 'koloda_id'}, inplace=True)
    df['coordinates'] = df['coordinates'].apply(transform_coordinates)
    df['foto'] = df['foto'].apply(
        lambda x: transform_photo_path(x, csv_path, MEMENTO_DIR, STORAGE_DIR)
    )
    df['row_hash'] = df.apply(generate_row_hash, axis=1)
    db.upsert_koloda(convert_to_native_types(df))

def process_osmotr(df: pd.DataFrame, db: DBManager, csv_path: Path):
    df = df.rename(columns={'koloda': 'koloda_id'})
    df['foto_out'] = df['foto_out'].apply(lambda x: transform_photo_path(x, csv_path, MEMENTO_DIR, STORAGE_DIR))
    df['foto_in'] = df['foto_in'].apply(lambda x: transform_photo_path(x, csv_path, MEMENTO_DIR, STORAGE_DIR))
    df['row_hash'] = df.apply(generate_row_hash, axis=1)
    cols = ["date", "koloda_id", "status",
            "foto_out", "pro_foto_out", "foto_in", "pro_foto_in", "info",
            "plan", "date_plan", "row_hash"]
    db.upsert_osmotr(convert_to_native_types(df[cols]))
def process_place(df: pd.DataFrame, db: DBManager, csv_path: Path):
    df['row_hash'] = df.apply(generate_row_hash, axis=1)
    cols = ["place", "region", "rayon", "oopt", "image", "row_hash"]
    db.upsert_place(convert_to_native_types(df[cols]))


def process_paseki(df: pd.DataFrame, db: DBManager, csv_path: Path):
    # В колонке 'place' находится название населенного пункта (например, "Гороховец")
    # В колонке 'paseka' находится название самой пасеки (например, "Омлево")
    df['coordinates'] = df['coordinates'].apply(transform_coordinates)
    df['foto'] = df['foto'].apply(lambda x: transform_photo_path(x, csv_path, MEMENTO_DIR, STORAGE_DIR))
    df['row_hash'] = df.apply(generate_row_hash, axis=1)
    original_non_numeric = df.loc[pd.to_numeric(df['many_bees'], errors='coerce').isna() & df['many_bees'].notna(), 'many_bees']
    if not original_non_numeric.empty:
        logging.warning(f"В файле {csv_path.name} в колонке 'many_bees' найдены нечисловые значения, которые будут заменены на NULL: {original_non_numeric.tolist()}")
    df['many_bees'] = pd.to_numeric(df['many_bees'], errors='coerce')
    db_cols = ["beekeeper", "paseka", "date", "place", "coordinates", "date_start",
               "many_bees", "obrabotki", "poroda", "data_poroda", "foto", "row_hash"]
    db.upsert_paseki(convert_to_native_types(df[db_cols]))

def process_test(df: pd.DataFrame, db: DBManager, csv_path: Path):
    df = df.rename(columns={'koloda': 'koloda_id'})
    df['foto_varroa'] = df['foto_varroa'].apply(lambda x: transform_photo_path(x, csv_path, MEMENTO_DIR, STORAGE_DIR))
    df['row_hash'] = df.apply(generate_row_hash, axis=1)
    cols = ["date", "koloda_id", "poroda",
            "data_poroda", "foto_varroa", "varroa_test", "row_hash"]
    db.upsert_test(convert_to_native_types(df[cols]))

# --- Главный оркестратор ---

def preprocess_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Выполняет общую предварительную обработку DataFrame."""
    df.replace({np.nan: None}, inplace=True)
    for col in ['date', 'date_plan', 'date_start']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce').replace({pd.NaT: None})
    return df

def dispatch_processor(file_path: Path, df: pd.DataFrame, db: DBManager):
    """Определяет и вызывает нужный обработчик для DataFrame."""
    processors = {
        "beekeepers.csv": process_beekeepers,
        "koloda.csv": process_koloda,
        "osmotr.csv": process_osmotr,
        "paseki.csv": process_paseki,
        "place.csv": process_place,
        "test.csv": process_test,
    }
    processor = processors.get(file_path.name)
    
    if not processor:
        logging.warning(f"Не найден обработчик для файла {file_path.name}. Пропускаем.")
        return

    if file_path.name == 'beekeepers.csv':
        processor(df, db)
    else:
        processor(df, db, csv_path=file_path)


def process_csv_file(file_path: Path, db: DBManager, state: StateManager):
    """Обрабатывает один CSV-файл: читает, преобразует и загружает в БД."""
    if not state.has_changed(file_path):
        return

    logging.info(f"Обнаружены изменения в {file_path}. Начинаем обработку...")
    
    db.begin()
    try:
        df = pd.read_csv(file_path)
        df = preprocess_dataframe(df)
        dispatch_processor(file_path, df, db)
        
        db.commit()
        state.update_state(file_path)
        logging.info(f"Файл {file_path} успешно обработан и закоммичен.")
    except Exception as e:
        db.rollback()
        logging.error(f"Ошибка при обработке файла {file_path}. Транзакция отменена. Ошибка: {e}", exc_info=True)


def sync_media_files():
    logging.info("Начинаем синхронизацию медиафайлов...")
    media_files = find_media_files(MEMENTO_DIR)
    if not media_files:
        logging.info("Новых медиафайлов не найдено.")
        return
        
    copied_count = 0
    for file in media_files:
        relative_path = file.relative_to(MEMENTO_DIR)
        destination_path = STORAGE_DIR / relative_path
        if not destination_path.exists():
            copy_file_to_storage(file, MEMENTO_DIR, STORAGE_DIR)
            copied_count += 1
            
    logging.info(f"Синхронизация медиафайлов завершена. Скопировано новых файлов: {copied_count}.")


def main():
    logging.info("--- Запуск приложения синхронизации ---")
    state_manager = StateManager(STATE_FILE)
    sync_media_files()

    all_csv_files = list(MEMENTO_DIR.rglob('*.csv'))
    beekeepers_files = [p for p in all_csv_files if p.name == 'beekeepers.csv']
    place_files = [p for p in all_csv_files if p.name == 'place.csv']
    other_files = [p for p in all_csv_files if p.name not in ['beekeepers.csv', 'place.csv']]
    sorted_csv_files = beekeepers_files + place_files + other_files

    try:
        with DBManager() as db_manager:
            for csv_file in sorted_csv_files:
                process_csv_file(csv_file, db_manager, state_manager)
    except Exception as e:
        logging.critical(f"Критическая ошибка работы приложения: {e}", exc_info=True)
    finally:
        state_manager.save_state()
        logging.info("Состояние обработки файлов сохранено.")
    
    logging.info("--- Работа приложения завершена ---")


if __name__ == "__main__":
    main()
