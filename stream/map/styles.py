# stream/map/styles.py

# Стили для маркеров на карте. 
# Ключ - имя таблицы, 'default' - стиль по умолчанию.
MARKER_STYLES = {
    "koloda": {
        "radius": 5,
        "color": "#FF4B4B",       # Красный для ульев
        "fill_color": "#FF4B4B",
        "fill_opacity": 0.7,
    },
    "paseki": {
        "radius": 8,
        "color": "#4B7BFF",       # Синий для пасек
        "fill_color": "#4B7BFF",
        "fill_opacity": 0.6,
    },
    "osmotr": {
        "radius": 3,
        "color": "#4BFF7B",       # Зеленый для осмотров
        "fill_color": "#4BFF7B",
        "fill_opacity": 0.8,
    },
    "default": {
        "radius": 4,
        "color": "#808080",       # Серый для всего остального
        "fill_color": "#808080",
        "fill_opacity": 0.5,
    },
}

# Базовые слои карты для Folium
BASE_LAYERS = {
    "Схема": {
        "tiles": "OpenStreetMap",
        "attr": "OpenStreetMap"
    },
    "Спутник": {
        "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "attr": "Esri"
    },
    "Топография": {
        "tiles": "CartoDB positron",
        "attr": "CartoDB"
    }
}