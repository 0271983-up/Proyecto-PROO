import streamlit as st
import pandas as pd
import pydeck as pdk
import time
import numpy as np

st.set_page_config(layout="wide", page_title="Mapa de Calor Tráfico")
st.title("Visualización de Tráfico Guadalajara, Jalisco")

#Carga datos
@st.cache_data(show_spinner=False)
def load_and_process_data():
    cols_to_use = ["Coordx", "Coordy", "timestamp", "linear_color_weighting"]
    df = pd.read_csv("data_sorted.csv", usecols=cols_to_use)

    df["Coordx"] = pd.to_numeric(df["Coordx"], errors='coerce')
    df["Coordy"] = pd.to_numeric(df["Coordy"], errors='coerce')
    df = df.dropna(subset=["Coordx", "Coordy"])

    df["timestamp_utc"] = pd.to_datetime(df["timestamp"], utc=True)
    df["hour_bucket"] = df["timestamp_utc"].dt.floor("h")


    df["linear_color_weighting"] = (
        pd.to_numeric(df["linear_color_weighting"], errors="coerce")
        .fillna(0)
        .clip(0, 1)
    )

    return df

df = load_and_process_data()

center_lat = df["Coordy"].mean()
center_lon = df["Coordx"].mean()

col1, col2, col3 = st.columns([1, 1, 3])
with col1:
    run_animation = st.checkbox("Activar/pausar Animación")
with col2:
    speed = st.slider("Velocidad", 0.01, 3.0, 1.0)
with col3:
    status_text = st.empty()

map_placeholder = st.empty()

#Renderizado
def render_map(data):
    if data.empty:
        st.warning("No hay datos para esta hora.")
        return

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=data,
        get_position=["Coordx", "Coordy"],
        get_radius=80,
        get_fill_color="formatted_color",
        pickable=True,
        opacity=0.8,
        filled=True,
        stroked=False)

    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=11,
        pitch=40,)

    map_placeholder.pydeck_chart(
        pdk.Deck(layers=[layer], initial_view_state=view_state,
                 map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"))

#Animación
if "current_hour_index" not in st.session_state:
    st.session_state.current_hour_index = 0

# Vista fija si no está animando
if not run_animation:
    first_hour = df["hour_bucket"].min()
    subset = df[df["hour_bucket"] == first_hour]
    subset["formatted_color"] = [[255, 100, 0, 150]] * len(subset)
    status_text.info(f"Vista inicial: {first_hour}")
    render_map(subset)

if run_animation:
    groups = list(df.groupby("hour_bucket"))
    start_index = st.session_state.current_hour_index
    for idx in range(start_index, len(groups)):
        current_hour, batch = groups[idx]
# Guardar avance
        st.session_state.current_hour_index = idx

        w = batch["linear_color_weighting"].to_numpy()
        batch["formatted_color"] = [
            [int(255 * wi), int(255 * (1 - wi)), 0, 180]
            for wi in w]

        # Tiempo
        frame_utc = batch["timestamp_utc"].iloc[0]
        status_text.markdown(
        f"### Hora UTC: **{frame_utc.strftime('%Y-%m-%d %H:%M:%S%z')[:-2] + ':' + frame_utc.strftime('%z')[-2:]}**")
        render_map(batch)

        time.sleep(0.001 / speed)

    st.success("Fin de los datos.")