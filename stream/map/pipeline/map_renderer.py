# stream/map/pipeline/map_renderer.py
import json
import folium
from folium.plugins import MeasureControl, Draw, TimestampedGeoJson
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from stream.map.styles import MARKER_STYLES, BASE_LAYERS, MAP_DIMENSIONS


class MapRenderer:
    """Отрисовка Folium-карты: все таблицы в одном слое."""

    # ------------------------------------------------------------------
    # Публичный вход
    # ------------------------------------------------------------------
    def render(self, filtered_data: dict, map_settings: dict) -> None:
        """filtered_data: {table_name: pd.DataFrame}"""
        self._render_data_tables(filtered_data)
        self._render_map(filtered_data)

    # ------------------------------------------------------------------
    # 1. Карта
    # ------------------------------------------------------------------
    def _render_map(self, filtered_data: dict) -> None:
        st.header("Карта")
        center_lat, center_lon, zoom = self._calculate_initial_view(filtered_data)

        # Базовая карта
        m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom, tiles=None)
        for name, info in BASE_LAYERS.items():
            # Делаем слой "Спутник" активным по умолчанию
            folium.TileLayer(
                tiles=info["tiles"],
                attr=info["attr"],
                name=name,
                overlay=False,
                control=True,
                # Устанавливаем "Спутник" как активный слой по умолчанию
                show=(name == "Спутник")
            ).add_to(m)

        # Единые контейнеры для объектов
        regular_fg = folium.FeatureGroup(name="Маркеры", show=True)
        time_features = []  # для TimestampedGeoJson
        has_time = False

        # Собираем объекты из всех таблиц
        for table_name, df in filtered_data.items():
            if df is None or df.empty:
                continue
            style = MARKER_STYLES.get(table_name, MARKER_STYLES["default"])

            # Проверяем, содержит ли таблица даты
            has_date = "date" in df.columns and pd.to_datetime(df["date"], errors="coerce").notna().any()
            
            # Всегда создаем обычные маркеры
            for _, row in df.iterrows():
                lat, lon = row.get("latitude"), row.get("longitude")
                if pd.isna(lat) or pd.isna(lon):
                    continue

                popup = folium.Popup(self._create_popup_html(row), max_width=400)
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=style.get("radius", 5),
                    popup=popup,
                    color=style.get("color", "gray"),
                    fill=True,
                    fill_color=style.get("fill_color", "gray"),
                    fill_opacity=style.get("fill_opacity", 0.7),
                ).add_to(regular_fg)

                # Буфер
                if "buffer_geojson" in row and pd.notna(row["buffer_geojson"]):
                    try:
                        geo = json.loads(row["buffer_geojson"])
                        folium.GeoJson(
                            geo,
                            style_function=lambda _, s=style: {
                                "fillColor": s.get("buffer_fill_color", "#3186cc"),
                                "color": s.get("buffer_fill_color", "#3186cc"),
                                "weight": 1,
                                "fillOpacity": s.get("buffer_fill_opacity", 0.2),
                            },
                        ).add_to(regular_fg)
                    except (json.JSONDecodeError, TypeError):
                        pass
            
            # Если таблица содержит даты, также создаем временные ряды
            if has_date:
                has_time = True
                # Создаем отдельные GeoJSON-фичи для временного ряда
                table_time_features = self._create_geojson_features(df, style)
                # Добавляем информацию о таблице в свойства
                for feature in table_time_features:
                    if 'properties' in feature:
                        feature['properties']['table_name'] = table_name
                time_features.extend(table_time_features)

        # Добавляем собранные слои
        # Добавляем обычные маркеры в любом случае
        regular_fg.add_to(m)
        
        # Если есть временные ряды, добавляем их отдельно
        if has_time:
            TimestampedGeoJson(
                {"type": "FeatureCollection", "features": time_features},
                period="P1D",
                add_last_point=True,
                auto_play=False,
                loop=False,
                max_speed=10,
                loop_button=True,
                date_options="YYYY-MM-DD",
                time_slider_drag_update=True,
            ).add_to(m)

        # Контролы
        folium.LayerControl(collapsed=False).add_to(m)
        m.add_child(MeasureControl(primary_length_unit="meters"))
        m.add_child(Draw(export=False))

        # Рендер в Streamlit
        output = st_folium(
            m,
            width=MAP_DIMENSIONS.get("width", "100%"),
            height=MAP_DIMENSIONS.get("height", 600),
            returned_objects=["all_drawings"],
        )

        # Кнопка скачивания нарисованного
        if output.get("all_drawings"):
            processed = self._process_drawings(output["all_drawings"])
            geojson_str = json.dumps(
                {"type": "FeatureCollection", "features": processed},
                indent=2,
                ensure_ascii=False,
            )
            st.download_button(
                label="📥 Скачать обработанные объекты (.geojson)",
                data=geojson_str,
                file_name="processed_drawn_data.geojson",
                mime="application/json",
            )

    # ------------------------------------------------------------------
    # 2. Таблицы под спойлерами
    # ------------------------------------------------------------------
    def _render_data_tables(self, filtered_data: dict) -> None:
        st.header("Отфильтрованные данные")
        if not any(df is not None and not df.empty for df in filtered_data.values()):
            st.info("Нет данных для отображения.")
            return

        for table_name, df in filtered_data.items():
            if df is None or df.empty:
                continue
            display_df = df.drop(
                columns=["geometry", "geometry_wkt", "latitude", "longitude", "coordinates", "buffer_geojson"],
                errors="ignore",
            )
            with st.expander(f"Таблица: {table_name} ({len(df)} записей)", expanded=False):
                st.dataframe(display_df, use_container_width=True)

    # ------------------------------------------------------------------
    # 3. Вспомогательные методы
    # ------------------------------------------------------------------
    def _calculate_initial_view(self, filtered_data: dict):
        lats, lons = [], []
        for df in filtered_data.values():
            if df is not None:
                lats.extend(df["latitude"].dropna().tolist())
                lons.extend(df["longitude"].dropna().tolist())
        if lats and lons:
            center_lat = sum(lats) / len(lats)
            center_lon = sum(lons) / len(lons)
            lat_r = max(lats) - min(lats)
            lon_r = max(lons) - min(lons)
            zoom = 13 if (lat_r < 0.1 and lon_r < 0.1) else 10 if (lat_r < 1 and lon_r < 1) else 7
            return center_lat, center_lon, zoom
        return 55.7558, 37.6173, 10  # Москва

    def _create_popup_html(self, row: pd.Series) -> str:
        """HTML для попапа, с картинками и пр."""
        from urllib.parse import quote

        STATIC_SERVER_URL = "http://localhost:8001"

        def clean_url(path):
            if not path or not isinstance(path, str):
                return None
            path = path.replace("\\", "/").lstrip("/")
            if path.startswith("storage/"):
                path = path[len("storage/") :]
            return f"{STATIC_SERVER_URL}/{quote(path)}"

        html = ["<div style='font-family:monospace;font-size:12px;max-width:350px;'>"]
        html.append(f"<h5><b>{row.get('name', 'Объект')}</b></h5><hr style='margin:2px 0;'>")

        # текстовые поля
        for col, val in row.items():
            if col.lower().startswith("foto") or col in {"geometry", "geometry_wkt", "latitude", "longitude", "coordinates", "buffer_geojson"}:
                continue
            if pd.notna(val):
                html.append(f"<b>{col}:</b> {val}<br>")

        # изображения
        for col, val in row.items():
            if col.lower().startswith("foto") and pd.notna(val):
                url = clean_url(val)
                if url:
                    html.append(f"<hr style='margin:5px 0;'><b style='display:block;margin-bottom:5px;'>{col}:</b>")
                    html.append(f"<img src='{url}' alt='{col}' style='width:100%;max-height:250px;object-fit:cover;border-radius:4px;'>")

        html.append("</div>")
        return "".join(html)

    def _create_geojson_features(self, df: pd.DataFrame, style: dict):
        """Список GeoJSON-фич для TimestampedGeoJson."""
        features = []
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")
        for _, row in df.iterrows():
            lat, lon = row.get("latitude"), row.get("longitude")
            if pd.isna(lat) or pd.isna(lon):
                continue
            feature = {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "time": row["date"].isoformat(),
                    "popup": self._create_popup_html(row),
                    "icon": "circle",
                    "iconstyle": {
                        "fillColor": style.get("fill_color", "grey"),
                        "fillOpacity": 0.8,
                        "stroke": "true",
                        "color": style.get("color", "black"),
                        "weight": 2,
                        "radius": style.get("radius", 5),
                    },
                },
            }
            features.append(feature)

            # буфер
            if "buffer_geojson" in row and pd.notna(row["buffer_geojson"]):
                try:
                    geo = json.loads(row["buffer_geojson"])
                    features.append(
                        {
                            "type": "Feature",
                            "geometry": geo,
                            "properties": {
                                "time": row["date"].isoformat(),
                                "style": {
                                    "fillColor": style.get("buffer_fill_color", "#3186cc"),
                                    "color": style.get("buffer_fill_color", "#3186cc"),
                                    "weight": 1,
                                    "fillOpacity": style.get("buffer_fill_opacity", 0.2),
                                },
                            },
                        }
                    )
                except (json.JSONDecodeError, TypeError):
                    pass
        return features

    def _process_drawings(self, drawings: list) -> list:
        """Превращает нарисованные круги (Point+radius) в полигоны."""
        try:
            import geopandas as gpd
            from shapely.geometry import Point
        except ImportError:
            st.error("Необходимы geopandas и shapely: pip install geopandas shapely")
            return drawings

        processed = []
        for feature in drawings:
            geom = feature.get("geometry", {})
            if geom.get("type") == "Point" and "radius" in feature.get("properties", {}):
                try:
                    lon, lat = geom["coordinates"]
                    radius = feature["properties"]["radius"]
                    gdf = gpd.GeoDataFrame({"geometry": [Point(lon, lat)]}, crs="EPSG:4326")
                    utm = gdf.estimate_utm_crs()
                    buffer = gdf.to_crs(utm).buffer(radius).to_crs("EPSG:4326")
                    # заменяем геометрию
                    feature["geometry"] = json.loads(buffer.to_json())["features"][0]["geometry"]
                    del feature["properties"]["radius"]
                except Exception as e:
                    st.warning(f"Ошибка буферизации круга: {e}")
            processed.append(feature)
        return processed
    