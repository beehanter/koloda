# %% [markdown]
# # Анализ данных о пчеловодстве
# 
# Этот ноутбук предназначен для проверки, анализа и визуализации данных, загруженных в базу данных PostgreSQL из CSV-файлов.
# 
# **Цели:**
# 1. Подключиться к базе данных.
# 2. Выполнить базовые запросы для проверки целостности данных.
# 3. Визуализировать геоданные (координаты колод и пасек) на карте.
# 4. Продемонстрировать создание интерактивных ссылок на локальные фото.

# %%
import os
from pathlib import Path
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine
from dotenv import load_dotenv
from IPython.display import display, HTML
from geodatasets import get_path

# Загружаем переменные окружения
load_dotenv()

# %% [markdown]
# ## 1. Настройка подключения к базе данных
# 
# Создаем подключение к нашей базе данных PostgreSQL с помощью SQLAlchemy.

# %%
db_user = os.getenv("POSTGRES_USER")
db_password = os.getenv("POSTGRES_PASSWORD")
db_name = os.getenv("POSTGRES_DB")
db_host = os.getenv("DB_HOST", "localhost")
db_port = os.getenv("DB_PORT", "5432")

# Строка подключения
db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

# Создаем движок SQLAlchemy
engine = create_engine(db_url)

print("Подключение к базе данных успешно настроено.")

# %% [markdown]
# ## 2. Загрузка данных из таблиц
# 
# Загрузим данные из таблиц `koloda` и `paseki`, так как они содержат координаты.

# %%
# Запрос для таблицы koloda
sql_koloda = "SELECT koloda_id, region, place, beekeeper, foto, coordinates FROM koloda;"
gdf_koloda = gpd.read_postgis(sql_koloda, engine, geom_col='coordinates')

print(f"Загружено {len(gdf_koloda)} записей из таблицы 'koloda'.")
display(gdf_koloda.head())

# %%
# Запрос для таблицы paseki
sql_paseki = "SELECT beekeeper, adres, place, foto, coordinates FROM paseki;"
gdf_paseki = gpd.read_postgis(sql_paseki, engine, geom_col='coordinates')

print(f"Загружено {len(gdf_paseki)} записей из таблицы 'paseki'.")
display(gdf_paseki.head())

# %% [markdown]
# ## 3. Визуализация координат на карте
# 
# Используем `geopandas` и `matplotlib` для отображения местоположений колод и пасек на карте.

# %%
# Для корректного отображения кириллицы в matplotlib
plt.rcParams['font.family'] = 'DeJavu Serif'
plt.rcParams['font.serif'] = ['Verdana']


world = gpd.read_file(get_path('naturalearth.land'))

fig, ax = plt.subplots(figsize=(15, 10))

# Отображаем карту мира
world.plot(ax=ax, color='lightgray')

# Отображаем пасеки (синие)
gdf_paseki.plot(ax=ax, marker='s', color='blue', markersize=50, label='Пасеки')

# Отображаем колоды (красные)
gdf_koloda.plot(ax=ax, marker='o', color='red', markersize=20, label='Колоды')

# Настройка карты
ax.set_title('Расположение пасек и колод')
ax.set_xlabel('Долгота')
ax.set_ylabel('Широта')
ax.legend()
ax.grid(True)

# Ограничиваем область показа для лучшей детализации (можно настроить)
if not gdf_koloda.empty or not gdf_paseki.empty:
    all_points = pd.concat([gdf_koloda, gdf_paseki])
    ax.set_xlim(all_points.geometry.x.min() - 1, all_points.geometry.x.max() + 1)
    ax.set_ylim(all_points.geometry.y.min() - 1, all_points.geometry.y.max() + 1)

plt.show()

# %% [markdown]
# ## 4. Просмотр фотографий
# 
# Создадим HTML-таблицу со ссылками на локальные файлы фотографий. При нажатии на ссылку фото должно открыться в новой вкладке браузера.

# %%
def create_clickable_links(df: pd.DataFrame, photo_col: str) -> pd.DataFrame:
    """Создает кликабельные HTML-ссылки для колонки с фото."""
    df_copy = df.copy()
    
    def make_link(path):
        if not path:
            return ""
        # Заменяем обратные слеши на прямые для URL-совместимости
        posix_path = Path(path).as_posix()
        # Выходим из папки notebooks/ в корень проекта, чтобы ссылка была правильной
        correct_relative_path = f"../{posix_path}"
        # Создаем относительную ссылку, которую Jupyter может разрешить
        return f'<a href="{correct_relative_path}" target="_blank">{os.path.basename(path)}</a>'

    df_copy[photo_col] = df_copy[photo_col].apply(make_link)
    return df_copy

# %% [markdown]
# ### Фотографии колод

# %%
koloda_with_links = create_clickable_links(gdf_koloda, 'foto')
display(HTML(koloda_with_links[['beekeeper', 'place', 'koloda_id', 'foto']].to_html(escape=False)))

# %% [markdown]
# ### Фотографии пасек

# %%
paseki_with_links = create_clickable_links(gdf_paseki, 'foto')
display(HTML(paseki_with_links[['beekeeper', 'place', 'adres', 'foto']].to_html(escape=False)))
