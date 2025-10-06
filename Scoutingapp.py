# =========================================================
# SCOUTINGAPP.PY — Versión completa + Login de Roles
# =========================================================
# ⚽ Mantiene toda tu estructura original y estética intacta.
# 🔐 Agrega login por roles (admin / scout / viewer) desde usuarios.csv.
# =========================================================

import os
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

from io import BytesIO
from datetime import date, datetime
from fpdf import FPDF
from st_aggrid import AgGrid, GridOptionsBuilder
import matplotlib.patches as patches

# ============================
# CONFIGURACIÓN INICIAL
# ============================
st.set_page_config(
    page_title="Carga de Informes Scouting Profesional",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================
# CARGAR ESTILOS
# ============================
try:
    from ui.style import load_custom_css
    load_custom_css()
except Exception:
    pass

# ============================
# ESTILOS VISUALES
# ============================
st.markdown("""
<style>
/* === SLIDER === */
.stSlider > div[data-baseweb="slider"] > div { background: transparent !important; }
.stSlider > div[data-baseweb="slider"] > div > div { background-color: #00c6ff !important; }
.stSlider [role="slider"] {
    background-color: #00c6ff !important;
    border: 2px solid #ffffff !important;
    box-shadow: 0 0 4px #00c6ff !important;
}
.stSlider label, .stSlider span { color: #00c6ff !important; }
/* === RADIO & CHECKBOX === */
.stRadio div[role='radiogroup'] label[data-baseweb='radio'] div:first-child,
.stCheckbox div[data-baseweb='checkbox'] div:first-child {
    background-color: #141c2e !important;
    border: 0.5px solid #141c2e !important;
}
.stRadio div[role='radiogroup'] label[data-baseweb='radio'] div:first-child > div,
.stCheckbox div[role='checkbox'] div:first-child > div {
    background-color: #00c6ff !important;
}
/* === ALERTAS === */
.stAlert.success { background-color: #003366 !important; color: #00c6ff !important; border-left: 4px solid #00c6ff !important; }
.stAlert.warning { background-color: #332b00 !important; color: #ffd700 !important; border-left: 4px solid #ffd700 !important; }
.stAlert.error   { background-color: #330000 !important; color: #ff6f61 !important; border-left: 4px solid #ff6f61 !important; }
/* === TEXTO === */
h1, h2, h3, h4, h5, h6, .stMarkdown { color: white !important; }
body, .stApp { background-color: #0e1117 !important; }
</style>
""", unsafe_allow_html=True)

# ============================
# ARCHIVOS PRINCIPALES
# ============================
FILE_USERS = "usuarios.csv"
FILE_PLAYERS = "jugadores.csv"
FILE_REPORTS = "informes.csv"
FILE_SHORTLIST = "lista_corta.csv"
CANCHA_IMG = "CANCHA.png"

# ============================
# VERIFICACIÓN DE USUARIOS
# ============================
if not os.path.exists(FILE_USERS):
    st.error("⚠️ Falta el archivo usuarios.csv con columnas: Usuario,Contraseña,Rol")
    st.stop()

df_users = pd.read_csv(FILE_USERS)
if not all(col in df_users.columns for col in ["Usuario", "Contraseña", "Rol"]):
    st.error("El archivo usuarios.csv debe tener columnas: Usuario,Contraseña,Rol")
    st.stop()

# ============================
# CREACIÓN AUTOMÁTICA DE CSVs
# ============================
if not os.path.exists(FILE_PLAYERS):
    df = pd.DataFrame(columns=[
        "ID_Jugador","Nombre","Fecha_Nac","Nacionalidad","Segunda_Nacionalidad",
        "Altura","Pie_Hábil","Posición","Caracteristica","Club","Liga","Sexo",
        "URL_Foto","URL_Perfil"
    ])
    df.to_csv(FILE_PLAYERS, index=False)

if not os.path.exists(FILE_REPORTS):
    df = pd.DataFrame(columns=[
        "ID_Informe","ID_Jugador","Scout","Fecha_Partido","Fecha_Informe",
        "Equipos_Resultados","Formación","Observaciones","Línea",
        "Controles","Perfiles","Pase_corto","Pase_largo","Pase_filtrado",
        "1v1_defensivo","Recuperacion","Intercepciones","Duelos_aereos",
        "Regate","Velocidad","Duelos_ofensivos",
        "Resiliencia","Liderazgo","Inteligencia_tactica","Inteligencia_emocional",
        "Posicionamiento","Vision_de_juego","Movimientos_sin_pelota"
    ])
    df.to_csv(FILE_REPORTS, index=False)

if not os.path.exists(FILE_SHORTLIST):
    df = pd.DataFrame(columns=[
        "ID_Jugador","Nombre","Edad","Altura","Club","Posición",
        "URL_Foto","URL_Perfil","Agregado_Por","Fecha_Agregado"
    ])
    df.to_csv(FILE_SHORTLIST, index=False)

# ============================
# FUNCIONES BASE
# ============================

from datetime import datetime, date
import pandas as pd

def calcular_edad(fecha_nac):
    """Calcula la edad a partir de una fecha en formato DD/MM/AAAA."""
    try:
        fn = datetime.strptime(str(fecha_nac), "%d/%m/%Y")
        hoy = date.today()
        return hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))
    except Exception:
        return "?"


def cargar_datos():
    """Carga los archivos CSV principales de la app y normaliza los ID."""
    try:
        df_players = pd.read_csv(FILE_PLAYERS)
        df_reports = pd.read_csv(
            FILE_REPORTS,
            sep=",",
            engine="python",
            quotechar='"',
            on_bad_lines="skip"
        )
        df_short = pd.read_csv(FILE_SHORTLIST)

        # === Forzar que los ID sean texto (para evitar errores al comparar) ===
        df_players["ID_Jugador"] = df_players["ID_Jugador"].astype(str)
        df_reports["ID_Jugador"] = df_reports["ID_Jugador"].astype(str)

        return df_players, df_reports, df_short

    except Exception as e:
        st.error(f"⚠️ Error al cargar datos: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


def guardar_csv(df, path):
    """Guarda un DataFrame como CSV sin índice."""
    try:
        df.to_csv(path, index=False)
    except Exception as e:
        st.error(f"⚠️ Error al guardar CSV: {e}")

# ============================
# LOGIN CON ROLES
# ============================
def login_ui():
    st.sidebar.title("🔐 Acceso de usuario")
    if "user" not in st.session_state:
        st.session_state["user"] = None
        st.session_state["role"] = None

    if st.session_state["user"]:
        st.sidebar.success(f"Conectado: {st.session_state['user']} ({st.session_state['role']})")
        if st.sidebar.button("Cerrar sesión"):
            st.session_state["user"] = None
            st.session_state["role"] = None
            st.rerun()
        return True

    with st.sidebar.form("login_form"):
        usuario = st.text_input("Usuario")
        clave = st.text_input("Contraseña", type="password")
        enviar = st.form_submit_button("Ingresar")

    if enviar:
        match = df_users[(df_users["Usuario"] == usuario) & (df_users["Contraseña"] == clave)]
        if not match.empty:
            rol = match.iloc[0]["Rol"]
            st.session_state["user"] = usuario
            st.session_state["role"] = rol
            st.success(f"Bienvenido {usuario} ({rol})")
            st.rerun()
        else:
            st.sidebar.error("Usuario o contraseña incorrectos")
    return False

if not login_ui():
    st.stop()

CURRENT_USER = st.session_state["user"]
CURRENT_ROLE = st.session_state["role"]
st.markdown(f"###  {CURRENT_USER} ({CURRENT_ROLE})")
st.markdown("---")
# =========================================================
# BLOQUE 2 / 4 — Funciones + Sección Jugadores
# =========================================================

# ============================
# FUNCIONES DE CÁLCULO
# ============================

def calcular_promedios_jugador(df_reports, id_jugador):
    # Forzar que los IDs sean strings para evitar errores de coincidencia
    df_reports["ID_Jugador"] = df_reports["ID_Jugador"].astype(str)
    id_jugador = str(id_jugador)

    informes = df_reports[df_reports["ID_Jugador"] == id_jugador]
    if informes.empty:
        return None

    columnas = [
        "Controles", "Perfiles", "Pase_corto", "Pase_largo", "Pase_filtrado",
        "1v1_defensivo", "Recuperacion", "Intercepciones", "Duelos_aereos",
        "Regate", "Velocidad", "Duelos_ofensivos", "Resiliencia", "Liderazgo",
        "Inteligencia_tactica", "Inteligencia_emocional", "Posicionamiento",
        "Vision_de_juego", "Movimientos_sin_pelota"
    ]
    return {col: informes[col].mean() for col in columnas if col in informes.columns}


def calcular_promedios_posicion(df_reports, df_players, posicion):
    df_players["ID_Jugador"] = df_players["ID_Jugador"].astype(str)
    df_reports["ID_Jugador"] = df_reports["ID_Jugador"].astype(str)

    jugadores_pos = df_players[df_players["Posición"] == posicion]
    ids = jugadores_pos["ID_Jugador"].values.astype(str)
    informes = df_reports[df_reports["ID_Jugador"].isin(ids)]

    if informes.empty:
        return None

    columnas = [
        "Controles", "Perfiles", "Pase_corto", "Pase_largo", "Pase_filtrado",
        "1v1_defensivo", "Recuperacion", "Intercepciones", "Duelos_aereos",
        "Regate", "Velocidad", "Duelos_ofensivos", "Resiliencia", "Liderazgo",
        "Inteligencia_tactica", "Inteligencia_emocional", "Posicionamiento",
        "Vision_de_juego", "Movimientos_sin_pelota"
    ]
    return {col: informes[col].mean() for col in columnas if col in informes.columns}


def mostrar_kpis(prom_jugador, prom_posicion):
    for bloque, promedio in prom_jugador.items():
        prom_pos = prom_posicion[bloque] if prom_posicion and bloque in prom_posicion else 0
        diff = promedio - prom_pos
        if diff > 0.2:
            delta = f"✅ {diff:.2f} arriba"
        elif diff < -0.2:
            delta = f"⚠️ {abs(diff):.2f} abajo"
        else:
            delta = "⚪ En promedio"
        st.metric(label=bloque, value=f"{promedio:.2f}", delta=delta)


def radar_chart(prom_jugador, prom_posicion):
    categorias = list(prom_jugador.keys())
    valores_jug = [prom_jugador.get(c, 0) for c in categorias]
    valores_pos = [prom_posicion.get(c, 0) for c in categorias] if prom_posicion else [0] * len(categorias)
    valores_jug += valores_jug[:1]
    valores_pos += valores_pos[:1]

    angles = np.linspace(0, 2 * np.pi, len(categorias), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor("#0e1117")
    ax.set_facecolor("#0e1117")

    ax.plot(angles, valores_jug, linewidth=2, color="cyan", label="Jugador")
    ax.fill(angles, valores_jug, color="cyan", alpha=0.25)
    ax.plot(angles, valores_pos, linewidth=2, color="orange", label="Promedio Posición")
    ax.fill(angles, valores_pos, color="orange", alpha=0.25)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categorias, color="white")
    ax.tick_params(colors="white")
    ax.legend(loc="upper right", bbox_to_anchor=(1.2, 1.1), facecolor="#0e1117", labelcolor="white")
    st.pyplot(fig)


def generar_pdf_ficha(jugador, informes):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(30, 60, 114)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 15, "Informe de Scouting", ln=True, align="C", fill=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"{jugador['Nombre']}", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 8, f"Edad: {jugador.get('Edad', '?')} años", ln=True)
    pdf.cell(0, 8, f"Posición: {jugador.get('Posición', '')}", ln=True)
    pdf.cell(0, 8, f"Club: {jugador.get('Club', '')}", ln=True)
    pdf.ln(5)

    pdf.set_font("Arial", "B", 12)
    pdf.set_fill_color(42, 82, 152)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 10, "Informes", ln=True, fill=True)
    pdf.set_text_color(0, 0, 0)

    for _, inf in informes.iterrows():
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, f"{inf['Fecha_Partido']} - Scout: {inf['Scout']} | Línea: {inf['Línea']}", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 6, str(inf["Observaciones"]))
        pdf.ln(3)

    buffer = BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer


# ============================
# CARGAR DATA
# ============================
df_players, df_reports, df_short = cargar_datos()

# ============================
# MENÚ
# ============================
menu = st.sidebar.radio("Menú", ["Jugadores", "Ver informes", "Lista corta"])

# ============================
# JUGADORES
# ============================

# --- Función auxiliar para generar un ID único ---
def generar_id_unico(df, columna="ID_Jugador"):
    """Genera un ID numérico incremental único basado en la columna especificada."""
    if columna not in df.columns or df.empty:
        return 1
    ids_existentes = df[columna].dropna().astype(str).tolist()
    numeros = [int(i) for i in ids_existentes if i.isdigit()]
    return max(numeros) + 1 if numeros else 1


if menu == "Jugadores":
    st.subheader("Buscador de Jugadores y Creación de Informes")

    # --- Opciones del buscador ---
    if not df_players.empty:
        opciones = {f"{row['Nombre']} - {row['Club']}": row["ID_Jugador"] for _, row in df_players.iterrows()}
    else:
        opciones = {}

    # --- Selector de jugador ---
    seleccion = st.selectbox("Seleccioná un jugador", [""] + list(opciones.keys()))

    # --- Mostrar botón para agregar jugador solo si no hay selección ---
    if not seleccion:
        st.markdown("#### ¿No encontrás al jugador?")
        if st.button("➕ Agregar nuevo jugador"):
            st.markdown("### Crear nuevo jugador")
            with st.form("nuevo_jugador_form"):
                nuevo_nombre = st.text_input("Nombre completo")
                nueva_fecha = st.text_input("Fecha de nacimiento (dd/mm/aaaa)")
                nueva_altura = st.number_input("Altura (cm)", min_value=140, max_value=210, value=175)
                nuevo_pie = st.selectbox("Pie hábil", ["Derecho", "Izquierdo", "Ambidiestro"])
                nueva_posicion = st.text_input("Posición")
                nuevo_club = st.text_input("Club actual")
                nueva_liga = st.text_input("Liga o país")
                nueva_nacionalidad = st.text_input("Nacionalidad")
                nueva_url_foto = st.text_input("URL de foto (opcional)")
                nueva_url_perfil = st.text_input("URL de enlace externo (opcional)")

                guardar_nuevo = st.form_submit_button("Guardar jugador")

                if guardar_nuevo:
                    try:
                        nuevo_id = generar_id_unico(df_players, "ID_Jugador")
                        nuevo_registro = pd.DataFrame([{
                            "ID_Jugador": nuevo_id,
                            "Nombre": nuevo_nombre,
                            "Fecha_Nac": nueva_fecha,
                            "Altura": nueva_altura,
                            "Pie_Hábil": nuevo_pie,
                            "Posición": nueva_posicion,
                            "Club": nuevo_club,
                            "Liga": nueva_liga,
                            "Nacionalidad": nueva_nacionalidad,
                            "URL_Foto": nueva_url_foto,
                            "URL_Perfil": nueva_url_perfil
                        }])
                        df_players = pd.concat([df_players, nuevo_registro], ignore_index=True)
                        guardar_csv(df_players, FILE_PLAYERS)
                        st.success(f"Jugador '{nuevo_nombre}' agregado correctamente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ocurrió un error al agregar el jugador: {e}")

    # --- Mostrar datos del jugador seleccionado ---
    if seleccion:
        id_jugador = opciones[seleccion]
        jugador = df_players[df_players["ID_Jugador"] == id_jugador].iloc[0]

        # === Ficha del jugador ===
        col1, col2, col3, col4 = st.columns([1.5, 1, 1, 1.5])

        with col1:
            st.markdown(f"### {jugador['Nombre']}")
            if pd.notna(jugador["URL_Foto"]) and str(jugador["URL_Foto"]).startswith("http"):
                st.image(jugador["URL_Foto"], width=150)

            st.write(f"📅 {jugador['Fecha_Nac']} ({calcular_edad(jugador['Fecha_Nac'])} años)")
            st.write(f"🌍 Nacionalidad: {jugador['Nacionalidad']}")
            st.write(f"📏 Altura: {jugador['Altura']} cm")
            st.write(f"👟 Pie hábil: {jugador['Pie_Hábil']}")
            st.write(f"🎯 Posición: {jugador['Posición']}")
            st.write(f"🏟️ Club: {jugador['Club']} ({jugador['Liga']})")

            if pd.notna(jugador["URL_Perfil"]) and str(jugador["URL_Perfil"]).startswith("http"):
                st.markdown(f"[Enlace externo]({jugador['URL_Perfil']})", unsafe_allow_html=True)

            # --- Agregar a lista corta ---
            if CURRENT_ROLE in ["admin", "scout"]:
                if st.button("Agregar a lista corta"):
                    df_short = pd.read_csv(FILE_SHORTLIST)
                    columnas_short = [
                        "ID_Jugador", "Nombre", "Edad", "Altura", "Club",
                        "Posición", "URL_Foto", "URL_Perfil", "Agregado_Por", "Fecha_Agregado"
                    ]
                    edad = calcular_edad(jugador["Fecha_Nac"])
                    nuevo = pd.DataFrame([[
                        jugador.get("ID_Jugador", ""), jugador.get("Nombre", ""), edad,
                        jugador.get("Altura", "-"), jugador.get("Club", "-"),
                        jugador.get("Posición", ""), jugador.get("URL_Foto", ""),
                        jugador.get("URL_Perfil", ""), CURRENT_USER, date.today().strftime("%d/%m/%Y")
                    ]], columns=columnas_short)

                    if jugador["ID_Jugador"] not in df_short["ID_Jugador"].values:
                        df_short = pd.concat([df_short, nuevo], ignore_index=True)
                        guardar_csv(df_short, FILE_SHORTLIST)
                        st.success("Jugador agregado a la lista corta.")
                    else:
                        st.info("Ya está en la lista corta.")

            # --- Eliminar jugador (solo admin) ---
            if CURRENT_ROLE == "admin":
                st.markdown("---")
                st.markdown("#### ⚠️ Eliminar jugador")

                eliminar_confirm = st.checkbox("Confirmar eliminación")

                eliminar_css = """
                <style>
                div[data-testid="stButton"] button[kind="primary"] {
                    background-color: #ff4b4b !important;
                    color: white !important;
                }
                </style>
                """
                st.markdown(eliminar_css, unsafe_allow_html=True)

                if st.button("🗑️ Eliminar jugador permanentemente"):
                    if eliminar_confirm:
                        try:
                            df_players = df_players[df_players["ID_Jugador"] != id_jugador]
                            guardar_csv(df_players, FILE_PLAYERS)

                            df_short = pd.read_csv(FILE_SHORTLIST)
                            df_short = df_short[df_short["ID_Jugador"] != id_jugador]
                            guardar_csv(df_short, FILE_SHORTLIST)

                            st.success(f"Jugador '{jugador['Nombre']}' eliminado correctamente.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Ocurrió un error al eliminar: {e}")
                    else:
                        st.warning("Debes confirmar la eliminación antes de continuar.")

        # === KPIs ===
        prom_jug = calcular_promedios_jugador(df_reports, id_jugador)
        prom_pos = calcular_promedios_posicion(df_reports, df_players, jugador["Posición"])

        with col2, col3:
            if prom_jug and prom_pos:
                tecnica_j = np.mean([
                    prom_jug["Controles"], prom_jug["Perfiles"],
                    prom_jug["Pase_corto"], prom_jug["Pase_largo"], prom_jug["Pase_filtrado"]
                ])
                defensivos_j = np.mean([
                    prom_jug["1v1_defensivo"], prom_jug["Recuperacion"],
                    prom_jug["Intercepciones"], prom_jug["Duelos_aereos"]
                ])
                ofensivos_j = np.mean([
                    prom_jug["Regate"], prom_jug["Velocidad"], prom_jug["Duelos_ofensivos"]
                ])
                tacticos_j = np.mean([
                    prom_jug["Posicionamiento"], prom_jug["Vision_de_juego"], prom_jug["Movimientos_sin_pelota"]
                ])
                psicologicos_j = np.mean([
                    prom_jug["Resiliencia"], prom_jug["Liderazgo"],
                    prom_jug["Inteligencia_tactica"], prom_jug["Inteligencia_emocional"]
                ])

                kpis_j = {
                    "Técnica": tecnica_j, "Defensivos": defensivos_j,
                    "Ofensivos": ofensivos_j, "Tácticos": tacticos_j,
                    "Psicológicos": psicologicos_j
                }

                tecnica_p = np.mean([
                    prom_pos["Controles"], prom_pos["Perfiles"],
                    prom_pos["Pase_corto"], prom_pos["Pase_largo"], prom_pos["Pase_filtrado"]
                ])
                defensivos_p = np.mean([
                    prom_pos["1v1_defensivo"], prom_pos["Recuperacion"],
                    prom_pos["Intercepciones"], prom_pos["Duelos_aereos"]
                ])
                ofensivos_p = np.mean([
                    prom_pos["Regate"], prom_pos["Velocidad"], prom_pos["Duelos_ofensivos"]
                ])
                tacticos_p = np.mean([
                    prom_pos["Posicionamiento"], prom_pos["Vision_de_juego"], prom_pos["Movimientos_sin_pelota"]
                ])
                psicologicos_p = np.mean([
                    prom_pos["Resiliencia"], prom_pos["Liderazgo"],
                    prom_pos["Inteligencia_tactica"], prom_pos["Inteligencia_emocional"]
                ])

                kpis_p = {
                    "Técnica": tecnica_p, "Defensivos": defensivos_p,
                    "Ofensivos": ofensivos_p, "Tácticos": tacticos_p,
                    "Psicológicos": psicologicos_p
                }

                for idx, (bloque, valor) in enumerate(kpis_j.items()):
                    col_target = col2 if idx % 2 == 0 else col3
                    with col_target:
                        diff = valor - kpis_p[bloque]
                        if diff > 0.2:
                            delta = f"✅ {diff:.2f} arriba"
                        elif diff < -0.2:
                            delta = f"⚠️ {abs(diff):.2f} abajo"
                        else:
                            delta = "⚪ En el promedio"
                        st.metric(bloque, f"{valor:.2f}", delta)

        # === RADAR ===
        with col4:
            if prom_jug:
                categorias = [
                    "Pase_largo", "Pase_filtrado", "Regate", "Velocidad",
                    "Liderazgo", "Inteligencia_tactica", "Posicionamiento", "Duelos_aereos"
                ]
                valores_jug = [prom_jug.get(c, 0) for c in categorias] + [prom_jug.get(categorias[0], 0)]
                valores_pos = [prom_pos.get(c, 0) for c in categorias] + [prom_pos.get(categorias[0], 0)]
                angles = np.linspace(0, 2 * np.pi, len(categorias), endpoint=False).tolist()
                angles += angles[:1]

                fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
                fig.patch.set_facecolor("#0e1117")
                ax.set_facecolor("#0e1117")
                ax.plot(angles, valores_jug, linewidth=2, color="cyan", label="Jugador")
                ax.fill(angles, valores_jug, color="cyan", alpha=0.25)
                ax.plot(angles, valores_pos, linewidth=2, color="orange", label="Promedio Posición")
                ax.fill(angles, valores_pos, color="orange", alpha=0.25)
                ax.set_xticks(angles[:-1])
                ax.set_xticklabels(categorias, color="white")
                ax.tick_params(colors="white")
                ax.legend(loc="upper right", bbox_to_anchor=(1.2, 1.1),
                          facecolor="#0e1117", labelcolor="white")
                st.pyplot(fig)

        # === FORMULARIO DE INFORME ===
        st.subheader(f"Cargar informe para {jugador['Nombre']}")

        if CURRENT_ROLE in ["admin", "scout"]:
            scout = CURRENT_USER
            fecha_partido = st.date_input("Fecha del partido", format="DD/MM/YYYY")
            equipos_resultados = st.text_input("Equipos y resultado")
            formacion = st.selectbox("Formación", ["4-2-3-1","4-3-1-2","4-4-2","4-3-3","3-5-2","3-4-3","5-3-2"])
            observaciones = st.text_area("Observaciones")
            linea = st.selectbox("Línea", [
                "1ra (Fichar)", "2da (Seguir)",
                "3ra (Ver más adelante)", "4ta (Descartar)", "Joven Promesa"
            ])

            st.write("### Evaluación del jugador (0 a 5)")
            with st.expander("Técnica"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    controles = st.slider("Controles", 0.0, 5.0, 0.0, 0.5)
                    perfiles = st.slider("Perfiles", 0.0, 5.0, 0.0, 0.5)
                with col2:
                    pase_corto = st.slider("Pase corto", 0.0, 5.0, 0.0, 0.5)
                    pase_largo = st.slider("Pase largo", 0.0, 5.0, 0.0, 0.5)
                with col3:
                    pase_filtrado = st.slider("Pase filtrado", 0.0, 5.0, 0.0, 0.5)

            with st.expander("Defensivos"):
                col1, col2 = st.columns(2)
                with col1:
                    v1_def = st.slider("1v1 Defensivo", 0.0, 5.0, 0.0, 0.5)
                    recuperacion = st.slider("Recuperación", 0.0, 5.0, 0.0, 0.5)
                with col2:
                    intercepciones = st.slider("Intercepciones", 0.0, 5.0, 0.0, 0.5)
                    duelos_aereos = st.slider("Duelos aéreos", 0.0, 5.0, 0.0, 0.5)

            with st.expander("Ofensivos"):
                col1, col2 = st.columns(2)
                with col1:
                    regate = st.slider("Regate", 0.0, 5.0, 0.0, 0.5)
                    velocidad = st.slider("Velocidad", 0.0, 5.0, 0.0, 0.5)
                with col2:
                    duelos_of = st.slider("Duelos ofensivos", 0.0, 5.0, 0.0, 0.5)

            with st.expander("Psicológicos"):
                col1, col2 = st.columns(2)
                with col1:
                    resiliencia = st.slider("Resiliencia", 0.0, 5.0, 0.0, 0.5)
                    liderazgo = st.slider("Liderazgo", 0.0, 5.0, 0.0, 0.5)
                with col2:
                    int_tactica = st.slider("Inteligencia táctica", 0.0, 5.0, 0.0, 0.5)
                    int_emocional = st.slider("Inteligencia emocional", 0.0, 5.0, 0.0, 0.5)

            with st.expander("Tácticos"):
                col1, col2 = st.columns(2)
                with col1:
                    posicionamiento = st.slider("Posicionamiento", 0.0, 5.0, 0.0, 0.5)
                    vision = st.slider("Visión de juego", 0.0, 5.0, 0.0, 0.5)
                with col2:
                    movimientos = st.slider("Movimientos sin pelota", 0.0, 5.0, 0.0, 0.5)

            if st.button("Guardar informe"):
                nuevo = [
                    len(df_reports)+1, id_jugador, scout, fecha_partido.strftime("%d/%m/%Y"),
                    date.today().strftime("%d/%m/%Y"), equipos_resultados, formacion,
                    observaciones, linea,
                    controles, perfiles, pase_corto, pase_largo, pase_filtrado,
                    v1_def, recuperacion, intercepciones, duelos_aereos,
                    regate, velocidad, duelos_of,
                    resiliencia, liderazgo, int_tactica, int_emocional,
                    posicionamiento, vision, movimientos
                ]
                df_reports.loc[len(df_reports)] = nuevo
                guardar_csv(df_reports, FILE_REPORTS)
                st.success("Informe guardado correctamente.")

# =========================================================
# VER INFORMES
# =========================================================
if menu == "Ver informes":
    st.subheader("📝 Informes cargados")

    # ============================
    # MERGE ENTRE INFORMES Y JUGADORES (fix tipo de ID)
    # ============================
    if "ID_Jugador" in df_reports.columns and "ID_Jugador" in df_players.columns:
        df_reports["ID_Jugador"] = pd.to_numeric(df_reports["ID_Jugador"], errors="coerce")
        df_players["ID_Jugador"] = pd.to_numeric(df_players["ID_Jugador"], errors="coerce")
        df_merged = df_reports.merge(df_players, on="ID_Jugador", how="left")
    else:
        st.error("❌ No se encuentra la columna 'ID_Jugador' en alguno de los archivos.")
        st.stop()

    # --- Filtro por rol ---
    if CURRENT_ROLE == "scout":
        df_merged = df_merged[df_merged["Scout"] == CURRENT_USER]
    elif CURRENT_ROLE == "viewer":
        st.info("Modo visualización: no puede editar ni eliminar informes.")

    # === Filtros ===
    st.sidebar.markdown("### 🔎 Filtros")
    filtro_scout = st.sidebar.multiselect("Scout", sorted(df_merged["Scout"].dropna().unique()))
    filtro_jugador = st.sidebar.multiselect("Jugador", sorted(df_merged["Nombre"].dropna().unique()))
    filtro_club = st.sidebar.multiselect("Club", sorted(df_merged["Club"].dropna().unique()))
    filtro_nacionalidad = st.sidebar.multiselect("Nacionalidad", sorted(df_merged["Nacionalidad"].dropna().unique()))
    filtro_posicion = st.sidebar.multiselect("Posición", sorted(df_merged["Posición"].dropna().unique()))
    filtro_linea = st.sidebar.multiselect("Línea", sorted(df_merged["Línea"].dropna().unique()))
    filtro_caracteristica = st.sidebar.multiselect("Característica", sorted(df_merged["Caracteristica"].dropna().unique()))
    filtro_edad = st.sidebar.slider("Edad", 15, 40, (15, 40))

    # Copia filtrada
    df_filtrado = df_merged.copy()

    if filtro_scout:
        df_filtrado = df_filtrado[df_filtrado["Scout"].isin(filtro_scout)]
    if filtro_jugador:
        df_filtrado = df_filtrado[df_filtrado["Nombre"].isin(filtro_jugador)]
    if filtro_club:
        df_filtrado = df_filtrado[df_filtrado["Club"].isin(filtro_club)]
    if filtro_nacionalidad:
        df_filtrado = df_filtrado[df_filtrado["Nacionalidad"].isin(filtro_nacionalidad)]
    if filtro_posicion:
        df_filtrado = df_filtrado[df_filtrado["Posición"].isin(filtro_posicion)]
    if filtro_linea:
        df_filtrado = df_filtrado[df_filtrado["Línea"].isin(filtro_linea)]
    if filtro_caracteristica:
        df_filtrado = df_filtrado[df_filtrado["Caracteristica"].isin(filtro_caracteristica)]

    # Calcular edad si existe la fecha
    if "Fecha_Nac" in df_filtrado.columns:
        try:
            df_filtrado["Edad"] = df_filtrado["Fecha_Nac"].apply(calcular_edad)
            df_filtrado = df_filtrado[
                (df_filtrado["Edad"] >= filtro_edad[0]) & (df_filtrado["Edad"] <= filtro_edad[1])
            ]
        except Exception as e:
            st.warning(f"⚠️ No se pudo calcular la edad correctamente: {e}")

    # Mostrar tabla principal
    if not df_filtrado.empty:
        st.markdown("### 📋 Tabla de informes")

        columnas_validas = [col for col in ["Fecha_Partido", "Nombre", "Observaciones", "Línea", "Scout", "Equipos_Resultados"] if col in df_filtrado.columns]
        df_tabla = df_filtrado[columnas_validas].copy()

        gb = GridOptionsBuilder.from_dataframe(df_tabla)
        gb.configure_column("Observaciones", wrapText=True, autoHeight=True)
        gb.configure_pagination(paginationAutoPageSize=True)
        gb.configure_grid_options(domLayout='normal')
        gridOptions = gb.build()

        AgGrid(
            df_tabla,
            gridOptions=gridOptions,
            fit_columns_on_grid_load=True,
            theme="blue",
            height=700,
            custom_css={
                ".ag-header": {"background-color": "#1e3c72", "color": "white", "font-weight": "bold"},
                ".ag-row-even": {"background-color": "#2a5298 !important", "color": "white !important"},
                ".ag-row-odd": {"background-color": "#3b6bbf !important", "color": "white !important"},
                ".ag-cell": {"white-space": "normal !important", "line-height": "1.3", "padding": "6px"},
            }
        )

        # === Selección de jugador ===
        seleccion = st.selectbox("👤 Seleccioná un jugador", [""] + list(df_filtrado["Nombre"].unique()))
        if seleccion:
            jugador_sel = df_players[df_players["Nombre"] == seleccion].iloc[0]
            st.markdown(f"### 📋 Informes de {jugador_sel['Nombre']}")
            informes_sel = df_reports[df_reports["ID_Jugador"] == jugador_sel["ID_Jugador"]]

            # === Exportar PDF ===
            if CURRENT_ROLE in ["admin", "scout"] and not informes_sel.empty:
                if st.button("📥 Exportar informes en PDF"):
                    pdf = FPDF(orientation="P", unit="mm", format="A4")
                    pdf.add_page()
                    pdf.set_font("Arial", "B", 16)
                    pdf.cell(0, 10, f"Informes de {jugador_sel['Nombre']}", ln=True, align="C")
                    pdf.ln(5)
                    pdf.set_font("Arial", "", 12)
                    pdf.cell(0, 8, f"Club: {jugador_sel['Club']}", ln=True)
                    pdf.cell(0, 8, f"Posición: {jugador_sel['Posición']}", ln=True)
                    pdf.ln(10)

                    for _, inf in informes_sel.iterrows():
                        pdf.set_font("Arial", "B", 12)
                        pdf.cell(0, 8, f"Partido: {inf.get('Fecha_Partido','')} | Scout: {inf.get('Scout','')} | Línea: {inf.get('Línea','')}", ln=True)
                        pdf.set_font("Arial", "I", 11)
                        pdf.cell(0, 8, f"Equipos: {inf.get('Equipos_Resultados','')}", ln=True)
                        pdf.set_font("Arial", "", 11)
                        pdf.multi_cell(0, 8, f"Observaciones:\n{inf.get('Observaciones','')}")
                        pdf.ln(5)
                        pdf.set_draw_color(0, 0, 128)
                        pdf.set_line_width(0.3)
                        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                        pdf.ln(5)

                    buffer = BytesIO()
                    pdf.output(buffer)
                    buffer.seek(0)
                    st.download_button(
                        "📥 Descargar PDF",
                        data=buffer,
                        file_name=f"informes_{jugador_sel['Nombre']}.pdf",
                        mime="application/pdf"
                    )

            # === Mostrar informes individuales ===
            for _, inf in informes_sel.iterrows():
                with st.expander(f"{inf.get('Fecha_Partido','')} | Scout: {inf.get('Scout','')} | Línea: {inf.get('Línea','')}"):
                    if CURRENT_ROLE == "viewer":
                        st.write(f"**Scout:** {inf.get('Scout','')}")
                        st.write(f"**Fecha:** {inf.get('Fecha_Partido','')}")
                        st.write(f"**Equipos:** {inf.get('Equipos_Resultados','')}")
                        st.write(f"**Línea:** {inf.get('Línea','')}")
                        st.write(f"**Observaciones:** {inf.get('Observaciones','')}")
                    else:
                        with st.form(f"edit_inf_{inf['ID_Informe']}"):
                            nuevo_scout = st.text_input("Scout", inf.get("Scout",""))
                            nueva_fecha = st.text_input("Fecha del partido", inf.get("Fecha_Partido",""))
                            nuevos_equipos = st.text_input("Equipos y resultado", inf.get("Equipos_Resultados",""))
                            nueva_linea = st.selectbox(
                                "Línea",
                                ["1ra (Fichar)", "2da (Seguir)", "3ra (Ver más adelante)", "4ta (Descartar)", "Joven Promesa"],
                                index=["1ra (Fichar)", "2da (Seguir)", "3ra (Ver más adelante)", "4ta (Descartar)", "Joven Promesa"].index(
                                    inf.get("Línea","3ra (Ver más adelante)")
                                )
                            )
                            nuevas_obs = st.text_area("Observaciones", inf.get("Observaciones",""), height=120)
                            guardar = st.form_submit_button("💾 Guardar cambios")
                            if guardar:
                                df_reports.loc[df_reports["ID_Informe"] == inf["ID_Informe"],
                                    ["Scout","Fecha_Partido","Equipos_Resultados","Línea","Observaciones"]] = [
                                        nuevo_scout, nueva_fecha, nuevos_equipos, nueva_linea, nuevas_obs
                                    ]
                                guardar_csv(df_reports, FILE_REPORTS)
                                st.success("✅ Informe actualizado")
                                st.rerun()
    else:
        st.info("No se encontraron informes con los filtros seleccionados.")


# =========================================================
# LISTA CORTA — versión corregida completa
# =========================================================
if menu == "Lista corta":
    st.subheader("⭐ Lista corta de jugadores")

    # === Filtrado por rol ===
    if CURRENT_ROLE == "scout":
        df_short = df_short[df_short["Agregado_Por"] == CURRENT_USER]

    if df_short.empty:
        st.info("No hay jugadores en la lista corta todavía.")
    else:
        # --- Filtros ---
        st.sidebar.markdown("### Filtros lista corta")
        filtro_posicion = st.sidebar.multiselect("Posición", sorted(df_short["Posición"].dropna().unique()))
        filtro_club = st.sidebar.multiselect("Club", sorted(df_short["Club"].dropna().unique()))
        filtro_nacionalidad = st.sidebar.multiselect("Nacionalidad", sorted(df_players["Nacionalidad"].dropna().unique()))

        df_filtrado = df_short.copy()
        if filtro_posicion:
            df_filtrado = df_filtrado[df_filtrado["Posición"].isin(filtro_posicion)]
        if filtro_club:
            df_filtrado = df_filtrado[df_filtrado["Club"].isin(filtro_club)]
        if filtro_nacionalidad:
            ids_filtrados = df_players[df_players["Nacionalidad"].isin(filtro_nacionalidad)]["ID_Jugador"].tolist()
            df_filtrado = df_filtrado[df_filtrado["ID_Jugador"].isin(ids_filtrados)]

        # --- Subpestañas ---
        tabs = st.tabs(["📋 Listado", "📊 Tabla", "⚽ Cancha"])

        # === LISTADO ===
        with tabs[0]:
            st.markdown("### Jugadores (vista de cartas)")
            df_filtrado = df_filtrado.sort_values("Posición")
            cols = st.columns(3)

            for i, row in df_filtrado.iterrows():
                with cols[i % 3]:
                    st.markdown(f"""
                    <div style="background: linear-gradient(90deg, #1e3c72, #2a5298);
                        padding: 0.5em; border-radius: 5px; margin-bottom: 10px;
                        color: white; text-align: center; font-family: Arial, sans-serif; max-width: 200px;">
                        <img src="{row['URL_Foto'] if pd.notna(row['URL_Foto']) and str(row['URL_Foto']).startswith('http') else 'https://via.placeholder.com/120'}"
                             style="width:80px; border-radius:6px; margin-bottom:5px;" />
                        <h5 style="font-size:16px; margin:4px 0;">{row['Nombre']}</h5>
                        <p style="font-size:14px; margin:2px 0;">Edad: {row['Edad']} años</p>
                        <p style="font-size:14px; margin:2px 0;">{row['Posición']}</p>
                        <p style="font-size:14px; margin:2px 0;">{row['Club']}</p>
                    </div>
                    """, unsafe_allow_html=True)

                    # Botón eliminar jugador (solo admin o scout)
                    if CURRENT_ROLE in ["admin", "scout"]:
                        if st.button(f"Borrar {row['Nombre']}", key=f"del_{i}"):
                            df_short = df_short[df_short["ID_Jugador"] != row["ID_Jugador"]]
                            guardar_csv(df_short, FILE_SHORTLIST)
                            st.success(f"Jugador {row['Nombre']} eliminado")
                            st.rerun()

        # === TABLA ===
        with tabs[1]:
            st.markdown("### Vista en tabla")
            st.dataframe(df_filtrado[["Nombre","Edad","Posición","Club","Agregado_Por","Fecha_Agregado"]],
                         use_container_width=True)

        # === CANCHA ===
        with tabs[2]:
            st.markdown("### Distribución en cancha")

            posiciones_cancha = {
                "Arquero": (265, 630),
                "Defensa central derecho": (340, 560),
                "Defensa central izquierdo": (187, 560),
                "Lateral derecho": (470, 470),
                "Lateral izquierdo": (60, 470),
                "Mediocampista defensivo": (265, 430),
                "Mediocampista mixto": (195, 280),
                "Mediocampista ofensivo": (320, 200),
                "Extremo derecho": (470, 130),
                "Extremo izquierdo": (60, 130),
                "Delantero centro": (265, 60)
            }

            if "alineacion" not in st.session_state:
                st.session_state["alineacion"] = {pos: [] for pos in posiciones_cancha.keys()}

            col1, col2 = st.columns([1, 2])
            with col1:
                if CURRENT_ROLE in ["admin", "scout"]:
                    st.markdown("#### Asignar jugador a una posición")
                    jugador_opt = st.selectbox("Seleccionar jugador", [""] + list(df_short["Nombre"]))
                    pos_opt = st.selectbox("Posición en cancha", list(posiciones_cancha.keys()))
                    if st.button("Asignar"):
                        if jugador_opt:
                            jugador_data = df_short[df_short["Nombre"] == jugador_opt].iloc[0]
                            jugador_info = {
                                "Nombre": jugador_data["Nombre"],
                                "Edad": jugador_data["Edad"],
                                "Altura": jugador_data["Altura"],
                                "Club": jugador_data["Club"]
                            }
                            if not isinstance(st.session_state["alineacion"][pos_opt], list):
                                st.session_state["alineacion"][pos_opt] = []
                            st.session_state["alineacion"][pos_opt].append(jugador_info)
                            st.success(f"✅ {jugador_opt} agregado a {pos_opt}")

            with col2:
                st.markdown("#### Vista en cancha")
                try:
                    cancha = plt.imread(CANCHA_IMG)
                    fig, ax = plt.subplots(figsize=(6, 9))
                    ax.imshow(cancha)
                except:
                    st.warning("⚠️ No se encontró la imagen CANCHA.png en la carpeta del proyecto.")
                    fig, ax = plt.subplots(figsize=(6, 9))
                    ax.set_facecolor("#003366")

                for pos, coords in posiciones_cancha.items():
                    jugadores = st.session_state["alineacion"].get(pos, [])
                    # ✅ Evitar error: filtrar solo diccionarios válidos
                    jugadores = [j for j in jugadores if isinstance(j, dict) and "Nombre" in j]
                    if jugadores:
                        for idx, jugador in enumerate(jugadores):
                            partes = jugador["Nombre"].split()
                            nombre_fmt = f"{partes[0]} {partes[-1]}" if len(partes) >= 2 else jugador["Nombre"]
                            edad = jugador.get("Edad", "-")
                            club = jugador.get("Club", "-")
                            texto = f"{nombre_fmt} ({edad})\n{club}"
                            x, y = coords[0], coords[1] + idx * 32
                            ax.add_patch(patches.Rectangle((x-60, y-15), 122, 32,
                                                           linewidth=1, edgecolor="white",
                                                           facecolor="blue", alpha=0.6))
                            ax.text(x, y, texto, ha="center", va="center",
                                    fontsize=6, color="white", linespacing=1.1)
                ax.axis("off")
                st.pyplot(fig)

            if CURRENT_ROLE in ["admin", "scout"]:
                st.markdown("### ❌ Eliminar jugadores de la alineación")
                for pos, jugadores in st.session_state["alineacion"].items():
                    # Evitar errores con tipos no válidos
                    jugadores = [j for j in jugadores if isinstance(j, dict) and "Nombre" in j]
                    for idx, jugador in enumerate(jugadores):
                        col_del1, col_del2 = st.columns([4,1])
                        with col_del1:
                            st.write(f"{pos}: {jugador['Nombre']} ({jugador['Club']})")
                        with col_del2:
                            if st.button("❌", key=f"del_{pos}_{idx}"):
                                st.session_state["alineacion"][pos].pop(idx)
                                st.rerun()
# =========================================================
# BLOQUE FINAL — Cierre profesional
# =========================================================

st.markdown("---")
st.markdown(
    f"""
    <div style="text-align:center; color:#00c6ff; margin-top:30px;">
        <h4>ScoutingApp Profesional v1.0</h4>
        <p>Usuario activo: <strong>{CURRENT_USER}</strong> ({CURRENT_ROLE})</p>
        <p style="color:gray; font-size:13px;">
            Desarrollada por Mariano Cirone · Área de Scouting Profesional
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# Limpieza opcional del estado de alineación
if "user" in st.session_state:
    if "alineacion" in st.session_state and CURRENT_ROLE != "admin":
        if st.button("Limpiar alineación temporal"):
            st.session_state["alineacion"] = {pos: [] for pos in [
                "Arquero","Defensa central derecho","Defensa central izquierdo",
                "Lateral derecho","Lateral izquierdo","Mediocampista defensivo",
                "Mediocampista mixto","Mediocampista ofensivo",
                "Extremo derecho","Extremo izquierdo","Delantero centro"
            ]}
            st.success("Alineación limpia para la próxima sesión.")
            st.rerun()

st.markdown(
    "<p style='text-align:center; color:gray; font-size:12px;'>© 2025 · Mariano Cirone · ScoutingApp</p>",
    unsafe_allow_html=True
)
