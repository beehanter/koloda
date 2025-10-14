# stream/map/pipeline/map_renderer.py
import streamlit as st
import folium
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

            feature_group = folium.FeatureGroup(name=table_name, show=True)
            style = MARKER_STYLES.get(table_name, MARKER_STYLES["default"])

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

                    # Отрисовка буферной зоны, если она есть
                    if 'buffer_geojson' in row and pd.notna(row['buffer_geojson']):
                        import json
                        try:
                            geojson_data = json.loads(row['buffer_geojson'])
                            folium.GeoJson(
                                geojson_data,
                                style_function=lambda x, style=style: {
                                    'fillColor': style.get('buffer_fill_color', '#3186cc'),
                                    'color': style.get('buffer_fill_color', '#3186cc'),
                                    'weight': 1,
                                    'fillOpacity': style.get('buffer_fill_opacity', 0.2)
                                }
                            ).add_to(feature_group)
                        except (json.JSONDecodeError, TypeError):
                            # Игнорируем ошибки, если GeoJSON некорректен
                            pass
            
            feature_group.add_to(m)

        folium.LayerControl(collapsed=False).add_to(m)
        st_folium(
            m,
            width=MAP_DIMENSIONS.get("width", "100%"),
            height=MAP_DIMENSIONS.get("height", 600),
            returned_objects=[]
        )

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
        """Создает HTML для всплывающего окна маркера."""
        html = "<div style='font-family: monospace; font-size: 12px;'>"
        html += f"<h5><b>{row.get('name', 'Объект')}</b></h5><hr style='margin: 2px 0;'>"
        for col, value in row.items():
            if col.lower() not in ['geometry', 'geometry_wkt', 'latitude', 'longitude', 'coordinates', 'name'] and pd.notna(value):
                html += f"<b>{col}:</b> {value}<br>"
        html += "</div>"
        return html
