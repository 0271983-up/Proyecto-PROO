import streamlit as st
import pandas as pd
import pydeck as pdk
import time
import numpy as np


st.set_page_config(layout="wide", page_title="Mapa de Calor Tráfico")


st.title(" Visualización de Tráfico (Optimizado)")


# 1. Cargar datos con optimización de memoria
@st.cache_data(show_spinner=False)
def load_and_process_data():
    status_bar = st.progress(0, text="Leyendo archivo masivo...")
   
    cols_to_use = ["Coordx", "Coordy", "timestamp", "linear_color_weighting"]
   
    try:
        # Intentamos leer solo columnas necesarias
        df = pd.read_csv("data_sorted.csv", usecols=cols_to_use)
    except ValueError:
        # Fallback si los nombres no coinciden exacto
        st.warning("Aviso: Nombres de columnas variaron, leyendo archivo completo...")
        df = pd.read_csv("data_sorted.csv")


    status_bar.progress(30, text="Limpiando coordenadas...")
   
    # CORRECCIÓN CRÍTICA: Forzar a números. Si hay texto "basura", se convierte en NaN
    df["Coordx"] = pd.to_numeric(df["Coordx"], errors='coerce')
    df["Coordy"] = pd.to_numeric(df["Coordy"], errors='coerce')
   
    # Eliminar filas que no tengan coordenadas válidas
    df = df.dropna(subset=["Coordx", "Coordy"])


    status_bar.progress(50, text="Procesando fechas...")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["hour_bucket"] = df["timestamp"].dt.floor("h")
   
    status_bar.progress(80, text="Calculando colores...")
   
    # Asegurar que el peso sea numérico y llenar vacíos con 0
    df["linear_color_weighting"] = pd.to_numeric(df["linear_color_weighting"], errors='coerce').fillna(0)
    weights = df["linear_color_weighting"].to_numpy()
   
    # Vectorización rápida para colores
    # R se basa en el peso. Si el peso es > 1, lo limitamos a 1 (clip)
    weights = np.clip(weights, 0, 1)
   
    # Creamos lista de colores. Usamos int() para asegurar formato entero para PyDeck
    # Formato: [R, G, B, A] -> Rojo variable, Transparencia fija (150)
    df["formatted_color"] = [
        [int(w * 255), 0, 0, 150] for w in weights
    ]
   
    status_bar.progress(100, text="¡Datos listos!")
    time.sleep(0.5)
    status_bar.empty()
   
    return df


try:
    df = load_and_process_data()
except FileNotFoundError:
    st.error("❌ Archivo 'data_sorted.csv' no encontrado.")
    st.stop()


# --- DIAGNÓSTICO (Oculto por defecto) ---
with st.expander("🔍 Ver datos cargados (Debug)"):
    st.write(f"Filas totales cargadas: {len(df)}")
    st.write(df.head())
    st.write("Tipos de datos:", df.dtypes)


if df.empty:
    st.error("El archivo se cargó pero no tiene datos válidos después de la limpieza.")
    st.stop()


# Configuración del mapa
center_lat = df["Coordy"].mean()
center_lon = df["Coordx"].mean()


col1, col2, col3 = st.columns([1, 1, 3])


with col1:
    run_animation = st.checkbox("▶️ Activar Animación")


with col2:
    speed = st.slider("Velocidad (seg/hora)", 0.1, 2.0, 0.5)


with col3:
    status_text = st.empty()


map_placeholder = st.empty()


# Función helper para dibujar mapa
def render_map(data, pitch=40):
    if data.empty:
        st.warning("⚠️ No hay datos para este periodo.")
        return


    layer = pdk.Layer(
        "ScatterplotLayer",
        data=data,
        get_position=["Coordx", "Coordy"],
        get_radius=80,          # Radio visible
        get_fill_color="formatted_color",
        pickable=True,
        opacity=0.8,
        filled=True,
        stroked=False
    )
   
    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=11,
        pitch=pitch,
    )
   
    # CORRECCIÓN: Usamos el URL directo para evitar el error de atributo
    map_style_url = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
   
    map_placeholder.pydeck_chart(
        pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            map_style=map_style_url
        )
    )


# Renderizado Inicial
if not run_animation:
    first_hour = df["hour_bucket"].min()
    status_text.info(f"Vista previa: {first_hour}")
    initial_data = df[df["hour_bucket"] == first_hour]
    render_map(initial_data)


# Bucle de Animación
# Bucle de Animación - 1 ms = 1 hora
if run_animation:
    groups = df.groupby("hour_bucket")

    for current_hour, batch in groups:
        if not run_animation:
            break

        status_text.markdown(f"### 🕒 Hora: {current_hour}")
        render_map(batch)

        # Cada milisegundo representa 1 hora
        time.sleep(0.001)

    st.success("Fin de los datos.")
