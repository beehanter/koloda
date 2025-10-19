# stream/map/pipeline/map_renderer.py
import streamlit as st
import json
import folium
from folium.plugins import MeasureControl, Draw, TimestampedGeoJson
from streamlit_folium import st_folium
import pandas as pd
from stream.map.styles import MARKER_STYLES, BASE_LAYERS, MAP_DIMENSIONS

class MapRenderer:
    def render(self, filtered_data, map_settings):
        """
        Отрисовывает таблицы с отфильтрованными данными, а затем карту Folium.
        """
        # 1. Отображение отфильтрованных данных в таблицах
        self._render_data_tables(filtered_data)

        # 2. Отрисовка карты
        self._render_map(filtered_data)

    def _render_map(self, filtered_data):
        """Отрисовывает карту Folium."""
        st.header("Карта")
        center_lat, center_lon, zoom = self._calculate_initial_view(filtered_data)
        
        m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom, tiles=None)

        folium.TileLayer(
            tiles=BASE_LAYERS["Спутник"]['tiles'],
            attr=BASE_LAYERS["Спутник"]['attr'],
            name="Спутник",
            overlay=False,
            control=True
        ).add_to(m)
        
        for name, tile_info in BASE_LAYERS.items():
            if name == "Спутник":
                continue
            folium.TileLayer(
                tiles=tile_info['tiles'],
                attr=tile_info['attr'],
                name=name,
                overlay=False,
                control=True
            ).add_to(m)

        for table_name, df in filtered_data.items():
            if df is None or df.empty:
                continue

            style = MARKER_STYLES.get(table_name, MARKER_STYLES["default"])

            # Проверяем, есть ли поле с датой для временной визуализации
            if 'date' in df.columns and pd.to_datetime(df['date'], errors='coerce').notna().any():
                features = self._create_geojson_features(df, style)
                TimestampedGeoJson(
                    {'type': 'FeatureCollection', 'features': features},
                    period='P1D', # Период - 1 день
                    add_last_point=True,
                    auto_play=False,
                    loop=False,
                    max_speed=10,
                    loop_button=True,
                    date_options='YYYY-MM-DD',
                    time_slider_drag_update=True
                ).add_to(m)
            else:
                # Если поля date нет, используем обычные маркеры
                feature_group = folium.FeatureGroup(name=table_name, show=True)
                for _, row in df.iterrows():
                    if 'latitude' in row and 'longitude' in row and pd.notna(row['latitude']) and pd.notna(row['longitude']):
                        popup_html = self._create_popup_html(row)
                        folium.CircleMarker(
                            location=[row['latitude'], row['longitude']],
                            radius=style.get("radius", 5),
                            popup=folium.Popup(popup_html, max_width=400),
                            color=style.get("color", "gray"),
                            fill=True,
                            fill_color=style.get("fill_color", "gray"),
                            fill_opacity=style.get("fill_opacity", 0.7)
                        ).add_to(feature_group)

                        # Отрисовка буферной зоны
                        if 'buffer_geojson' in row and pd.notna(row['buffer_geojson']):
                            try:
                                geojson_data = json.loads(row['buffer_geojson'])
                                folium.GeoJson(
                                    geojson_data,
                                    style_function=lambda x, s=style: {
                                        'fillColor': s.get('buffer_fill_color', '#3186cc'),
                                        'color': s.get('buffer_fill_color', '#3186cc'),
                                        'weight': 1,
                                        'fillOpacity': s.get('buffer_fill_opacity', 0.2)
                                    }
                                ).add_to(feature_group)
                            except (json.JSONDecodeError, TypeError):
                                pass
                feature_group.add_to(m)

        folium.LayerControl(collapsed=False).add_to(m)

        # Добавляем инструменты измерения и рисования
        m.add_child(MeasureControl(primary_length_unit='meters'))
        # export=True не работает корректно со streamlit-folium,
        # поэтому мы будем обрабатывать экспорт вручную
        m.add_child(Draw())

        # Отображаем карту и получаем нарисованные объекты обратно
        output = st_folium(
            m,
            width=MAP_DIMENSIONS.get("width", "100%"),
            height=MAP_DIMENSIONS.get("height", 600),
            returned_objects=["all_drawings"]
        )

        # Обрабатываем нарисованные объекты для скачивания
        if output.get("all_drawings") and output["all_drawings"]:
            raw_drawings = output["all_drawings"]
            processed_features = self._process_drawings(raw_drawings)

            # Создаем корректный GeoJSON FeatureCollection из обработанных данных
            feature_collection = {
                "type": "FeatureCollection",
                "features": processed_features
            }
            
            # Конвертируем в строку для кнопки скачивания
            geojson_str = json.dumps(feature_collection, indent=2, ensure_ascii=False)

            st.download_button(
                label="📥 Скачать обработанные объекты (.geojson)",
                data=geojson_str,
                file_name="processed_drawn_data.geojson",
                mime="application/json",
            )

    def _process_drawings(self, drawings):
        """
        Обрабатывает 'сырые' нарисованные объекты, превращая круги в полигоны.
        """
        try:
            import geopandas as gpd
            from shapely.geometry import Point
        except ImportError:
            st.error("Для обработки геометрии необходимы библиотеки 'geopandas' и 'shapely'. Установите их: pip install geopandas shapely")
            return drawings

        processed_features = []
        for feature in drawings:
            # Проверяем, является ли объект кругом (точка с радиусом)
            if (feature.get('geometry', {}).get('type') == 'Point' and
                'radius' in feature.get('properties', {})):
                
                try:
                    lon, lat = feature['geometry']['coordinates']
                    radius_meters = feature['properties']['radius']
                    
                    # Создаем GeoDataFrame для точки
                    temp_gdf = gpd.GeoDataFrame(
                        [{'geometry': Point(lon, lat)}],
                        crs="EPSG:4326"
                    )
                    
                    # Оцениваем и переходим в локальную UTM-проекцию для точного буфера
                    utm_crs = temp_gdf.estimate_utm_crs()
                    temp_gdf_projected = temp_gdf.to_crs(utm_crs)
                    
                    # Строим буфер (полигон)
                    buffer_polygon = temp_gdf_projected.buffer(radius_meters)
                    
                    # Возвращаем полигон обратно в WGS 84
                    buffer_wgs84 = buffer_polygon.to_crs("EPSG:4326")
                    
                    # Обновляем геометрию объекта
                    # Обновляем геометрию объекта
                    json_str = gpd.GeoSeries(buffer_wgs84).to_json()
                    feature['geometry'] = json.loads(json_str)['features'][0]['geometry']
                    # Удаляем свойство radius, так как оно больше не нужно
                    del feature['properties']['radius']
                except Exception as e:
                    st.warning(f"Не удалось преобразовать нарисованный круг в полигон: {e}")
            
            processed_features.append(feature)
            
        return processed_features

    def _render_data_tables(self, filtered_data):
        """Отображает отфильтрованные данные в виде таблиц."""
        st.header("Отфильтрованные данные")
        if not any(df is not None and not df.empty for df in filtered_data.values()):
            st.info("Нет данных для отображения. Измените фильтры или выберите другие таблицы.")
            return

        for table_name, df in filtered_data.items():
            if df is not None and not df.empty:
                with st.expander(f"Таблица: {table_name} ({len(df)} записей)", expanded=False):
                    # Убираем служебные колонки для более чистого отображения
                    display_df = df.drop(columns=['geometry', 'geometry_wkt', 'latitude', 'longitude', 'coordinates'], errors='ignore')
                    st.dataframe(display_df, use_container_width=True)

    def _calculate_initial_view(self, filtered_data):
        """Вычисляет начальный вид карты на основе всех данных."""
        all_lats, all_lons = [], []
        
        for df in filtered_data.values():
            if df is not None and 'latitude' in df.columns and 'longitude' in df.columns:
                all_lats.extend(df['latitude'].dropna().tolist())
                all_lons.extend(df['longitude'].dropna().tolist())
        
        if all_lats and all_lons:
            center_lat = sum(all_lats) / len(all_lats)
            center_lon = sum(all_lons) / len(all_lons)
            lat_range = max(all_lats) - min(all_lats) if len(all_lats) > 1 else 0
            lon_range = max(all_lons) - min(all_lons) if len(all_lons) > 1 else 0
            
            if lat_range < 0.1 and lon_range < 0.1:
                zoom = 13
            elif lat_range < 1 and lon_range < 1:
                zoom = 10
            else:
                zoom = 7
        else:
            center_lat, center_lon, zoom = 55.7558, 37.6173, 10 # Москва

        return center_lat, center_lon, zoom

    def _create_popup_html(self, row):
        """Создает HTML для всплывающего окна маркера, включая изображения."""
        from urllib.parse import quote
        STATIC_SERVER_URL = "http://localhost:8001"

        def prepare_url(path):
            if not path or not isinstance(path, str):
                return None
            clean_path = path.replace("\\", "/").lstrip("/")
            if clean_path.startswith("storage/"):
                clean_path = clean_path[len("storage/"):]
            return f"{STATIC_SERVER_URL}/{quote(clean_path)}"

        html = "<div style='font-family: monospace; font-size: 12px; max-width: 350px;'>"
        html += f"<h5><b>{row.get('name', 'Объект')}</b></h5><hr style='margin: 2px 0;'>"
        
        # Сначала добавляем все текстовые поля
        for col, value in row.items():
            if col.lower().startswith("foto"):
                continue # Пропускаем фото, обработаем их отдельно
            if col.lower() not in ['geometry', 'geometry_wkt', 'latitude', 'longitude', 'coordinates', 'name', 'buffer_geojson'] and pd.notna(value):
                html += f"<b>{col}:</b> {value}<br>"
        
        # Затем добавляем изображения
        for col, value in row.items():
            if col.lower().startswith("foto") and pd.notna(value):
                img_url = prepare_url(value)
                if img_url:
                    html += f"<hr style='margin: 5px 0;'><b style='display: block; margin-bottom: 5px;'>{col}:</b>"
                    html += f"<img src='{img_url}' alt='{col}' style='width:100%; max-height: 250px; object-fit: cover; border-radius: 4px;'>"

        html += "</div>"
        return html

    def _create_geojson_features(self, df, style):
        """Создает список GeoJSON-объектов для TimestampedGeoJson."""
        features = []
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values(by='date')

        for _, row in df.iterrows():
            if 'latitude' in row and 'longitude' in row and pd.notna(row['latitude']) and pd.notna(row['longitude']):
                feature = {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [row['longitude'], row['latitude']]
                    },
                    'properties': {
                        'time': row['date'].isoformat(),
                        'popup': self._create_popup_html(row),
                        'icon': 'circle',
                        'iconstyle': {
                            'fillColor': style.get('fill_color', 'grey'),
                            'fillOpacity': 0.8,
                            'stroke': 'true',
                            'color': style.get('color', 'black'),
                            'weight': 2,
                            'radius': style.get('radius', 5)
                        }
                    }
                }
                features.append(feature)

                # Добавляем буферную зону как отдельный объект для той же временной метки
                if 'buffer_geojson' in row and pd.notna(row['buffer_geojson']):
                    try:
                        geojson_data = json.loads(row['buffer_geojson'])
                        buffer_feature = {
                            'type': 'Feature',
                            'geometry': geojson_data,
                            'properties': {
                                'time': row['date'].isoformat(),
                                'style': {
                                    'fillColor': style.get('buffer_fill_color', '#3186cc'),
                                    'color': style.get('buffer_fill_color', '#3186cc'),
                                    'weight': 1,
                                    'fillOpacity': style.get('buffer_fill_opacity', 0.2)
                                }
                            }
                        }
                        features.append(buffer_feature)
                    except (json.JSONDecodeError, TypeError):
                        pass # Игнорируем ошибки парсинга буфера

        return features
