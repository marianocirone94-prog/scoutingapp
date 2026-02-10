# =========================================================
# BLOQUE 1 / 5 — Conexión + Configuración inicial + Login
# =========================================================
# ⚽ ScoutingApp Profesional v2 — Conectada a Google Sheets
# =========================================================
# - Carga directa desde "Scouting_DB" (Jugadores / Informes / Lista corta)
# - Login por roles (admin / scout / viewer)
# - Diseño oscuro #0e1117 + acento #00c6ff
# =========================================================

# ----------------------
# 📦 IMPORTS GENERALES
# ----------------------
import os
import base64
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import plotly.express as px

from io import BytesIO
from datetime import date, datetime, timedelta
from fpdf import FPDF
from st_aggrid import AgGrid, GridOptionsBuilder
import matplotlib.patches as patches
import gspread
from google.oauth2.service_account import Credentials

# =========================================================
# 🎨 HELPER VISUAL — PLOTLY GLASS (ANTI FONDO NEGRO)
# =========================================================
def apply_glass_plotly(fig):
    """
    Aplica un layout transparente y coherente con el diseño
    glass/futurista de la app.
    Elimina el fondo negro/blanco por defecto de Plotly.
    """
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            color="white",
            size=12
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
            font=dict(color="white")
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.08)",
            zeroline=False
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.08)",
            zeroline=False
        ),
        margin=dict(l=20, r=20, t=40, b=20)
    )
    return fig


# =========================================================
# BLOQUE DE CONEXIÓN A GOOGLE SHEETS (FINAL - SEGURO Y MULTIUSUARIO)
# =========================================================

import os, json, time
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
from datetime import datetime, timedelta

# --- CONFIGURACIÓN GENERAL ---
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
SHEET_ID = "1IInJ87xaaEwJfaz96mUlLLiX9_tk0HvqzoBoZGhrBi8"
CREDS_PATH = os.path.join("credentials", "credentials.json")

# Control de lectura para evitar exceso de requests
if "ultima_lectura" not in st.session_state:
    st.session_state["ultima_lectura"] = datetime.now() - timedelta(seconds=5)


# =========================================================
# CONEXIÓN
# =========================================================
def conectar_sheets():
    try:
        if "GOOGLE_SERVICE_ACCOUNT_JSON" in st.secrets:
            creds_dict = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"])
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
        else:
            if not os.path.exists(CREDS_PATH):
                st.error("❌ Falta credentials.json o secreto en Streamlit Cloud.")
                st.stop()
            creds = Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPE)

        client = gspread.authorize(creds)
        return client.open_by_key(SHEET_ID)
    except Exception as e:
        st.error(f"⚠️ No se pudo conectar con Google Sheets: {e}")
        st.stop()


# =========================================================
# OBTENER O CREAR HOJA
# =========================================================
def obtener_hoja(nombre_hoja: str, columnas_base: list = None):
    try:
        book = conectar_sheets()
        hojas = [ws.title for ws in book.worksheets()]
        if nombre_hoja not in hojas:
            ws = book.add_worksheet(title=nombre_hoja, rows=500, cols=20)
            if columnas_base:
                ws.append_row(columnas_base)
            st.warning(f"⚠️ Hoja '{nombre_hoja}' creada automáticamente.")
            return ws
        return book.worksheet(nombre_hoja)
    except Exception as e:
        st.error(f"⚠️ Error al obtener hoja '{nombre_hoja}': {e}")
        st.stop()


# =========================================================
# CARGAR DATOS (con control de tiempo)
# =========================================================
@st.cache_data(ttl=30)
def _leer_datos(nombre_hoja: str):
    ws = obtener_hoja(nombre_hoja)
    return ws.get_all_records()


def cargar_datos_sheets(nombre_hoja: str, columnas_base: list = None) -> pd.DataFrame:
    try:
        ahora = datetime.now()
        if ahora - st.session_state["ultima_lectura"] < timedelta(seconds=2):
            time.sleep(1)
        st.session_state["ultima_lectura"] = ahora

        data = _leer_datos(nombre_hoja)
        df = pd.DataFrame(data)
        if df.empty and columnas_base:
            df = pd.DataFrame(columns=columnas_base)
        return df
    except Exception as e:
        st.error(f"⚠️ Error al cargar '{nombre_hoja}': {e}")
        return pd.DataFrame(columns=columnas_base or [])


# =========================================================
# ACTUALIZAR HOJA (BLINDADA - SIN BORRAR)
# =========================================================
def actualizar_hoja(nombre_hoja: str, df: pd.DataFrame):
    """
    Actualiza sin borrar datos previos.
    Si existe el ID, actualiza esa fila. Si no, la agrega.
    Nunca borra toda la hoja.
    """
    try:
        ws = obtener_hoja(nombre_hoja, list(df.columns))
        data_actual = ws.get_all_records()
        df_actual = pd.DataFrame(data_actual)

        # Si la hoja está vacía, crea desde cero
        if df_actual.empty:
            ws.update([df.columns.values.tolist()] + df.values.tolist())
            st.toast(f"✅ Hoja '{nombre_hoja}' creada y actualizada.", icon="💾")
            return

        # Detectar columna de ID
        id_col = None
        for posible in ["ID_Jugador", "ID_Informe"]:
            if posible in df.columns:
                id_col = posible
                break

        # Fusión segura sin borrar
        if id_col:
            df_actual[id_col] = df_actual[id_col].astype(str)
            df[id_col] = df[id_col].astype(str)
            df_fusion = pd.concat([df_actual, df]).drop_duplicates(subset=[id_col], keep="last")
        else:
            df_fusion = pd.concat([df_actual, df]).drop_duplicates(keep="last")

        # Subir a Sheets
        ws.update([df_fusion.columns.values.tolist()] + df_fusion.values.tolist())
        st.toast(f"💾 '{nombre_hoja}' actualizada correctamente (sin borrar datos).", icon="✅")

    except Exception as e:
        st.error(f"⚠️ Error al actualizar '{nombre_hoja}': {e}")


# =========================================================
# ELIMINAR FILA SEGURA (CONTROLADO)
# =========================================================
def eliminar_por_id(nombre_hoja: str, id_col: str, id_valor):
    """
    Elimina una fila específica por ID, sin tocar el resto.
    """
    try:
        ws = obtener_hoja(nombre_hoja)
        data_actual = ws.get_all_records()
        df = pd.DataFrame(data_actual)
        if id_col not in df.columns:
            st.error(f"⚠️ La hoja '{nombre_hoja}' no tiene la columna '{id_col}'.")
            return
        df = df[df[id_col].astype(str) != str(id_valor)]
        ws.update([df.columns.values.tolist()] + df.values.tolist())
        st.success(f"🗑️ Registro con {id_col}={id_valor} eliminado correctamente.")
    except Exception as e:
        st.error(f"⚠️ Error al eliminar en '{nombre_hoja}': {e}")


# =========================================================
# AGREGAR FILA NUEVA (SEGURA)
# =========================================================
def agregar_fila(nombre_hoja: str, fila: list):
    """Agrega una nueva fila sin tocar el resto."""
    try:
        ws = obtener_hoja(nombre_hoja)
        ws.append_row(fila, value_input_option="USER_ENTERED")
        st.toast(f"🟢 Nueva fila agregada en '{nombre_hoja}'.", icon="🟢")
        st.cache_data.clear()
    except Exception as e:
        st.error(f"⚠️ Error al agregar fila en '{nombre_hoja}': {e}")


# =========================================================
# BOTÓN MANUAL DE REFRESCO
# =========================================================
def boton_refrescar_datos():
    st.markdown("---")
    if st.button("🔄 Actualizar datos (refrescar desde Google Sheets)"):
        st.cache_data.clear()
        st.rerun()

# =========================================================
# CONFIGURACIÓN INICIAL DE LA APP
# =========================================================
st.set_page_config(
    page_title="ScoutingApp Profesional",
    layout="wide",
    initial_sidebar_state="collapsed"
)


st.markdown("""
<style>

/* =====================================================
🌌 FONDO GLOBAL — FUTURISTA / TECH CON MOVIMIENTO
===================================================== */
.stApp {
    background:
        radial-gradient(circle at 20% 15%, rgba(0,198,255,0.22), transparent 38%),
        radial-gradient(circle at 80% 35%, rgba(30,60,114,0.40), transparent 42%),
        linear-gradient(120deg, #1e3c72, #16213e, #0e1117);
    background-size: 220% 220%;
    animation: fondoVivo 15s ease-in-out infinite;
}

@keyframes fondoVivo {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

/* =====================================================
✍️ TEXTO GLOBAL
===================================================== */
h1, h2, h3, h4, h5, h6, .stMarkdown, label {
    color: #ffffff !important;
}

/* =====================================================
🧊 CONTENEDORES GENERALES — GLASS
===================================================== */
div[data-testid="stContainer"] {
    background: linear-gradient(
        145deg,
        rgba(30,60,114,0.78),
        rgba(14,17,23,0.92)
    );
    border-radius: 18px;
    padding: 18px;
    margin-bottom: 18px;
    box-shadow:
        0 14px 36px rgba(0,0,0,0.55),
        inset 0 0 24px rgba(0,198,255,0.06);
    animation: fadeUp 0.35s ease;
}

@keyframes fadeUp {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* =====================================================
📊 KPI — TARJETAS (COMO ANTES + MEJOR)
===================================================== */
.kpi-container {
    display:flex;
    justify-content:center;
    gap:22px;
    margin:25px 0 35px 0;
    flex-wrap:wrap;
}

.kpi-card {
    background: linear-gradient(135deg, #0e1117, #1e3c72);
    border-radius:16px;
    padding:18px 22px;
    min-width:220px;
    text-align:center;
    box-shadow:
        0 10px 26px rgba(0,0,0,0.55),
        inset 0 0 18px rgba(0,198,255,0.06);
    transition: all 0.25s ease;
}

.kpi-card:hover {
    transform: translateY(-4px);
    box-shadow:
        0 16px 40px rgba(0,0,0,0.65),
        0 0 24px rgba(0,198,255,0.45);
}

.kpi-title {
    color:#00c6ff;
    font-size:14px;
    font-weight:700;
}

.kpi-value {
    font-size:30px;
    font-weight:800;
    color:white;
}

/* =====================================================
🏆 RANKINGS — TARJETAS (FIX DEFINITIVO)
===================================================== */
.panel-title {
    color:#00c6ff;
    font-weight:700;
    font-size:16px;
    margin:14px 0 8px 0;
    text-align:center;
}

.rank-card {
    background: linear-gradient(90deg, #0e1117, #1e3c72);
    border-radius:12px;
    padding:10px 14px;
    margin-bottom:8px;
    display:flex;
    justify-content:space-between;
    align-items:center;
    box-shadow:0 0 10px rgba(0,0,0,0.45);
    transition: all 0.25s ease;
}

.rank-card:hover {
    transform: translateX(4px);
    box-shadow:
        0 0 18px rgba(0,198,255,0.45),
        0 0 30px rgba(0,0,0,0.6);
}

.rank-left {
    display:flex;
    gap:12px;
    align-items:center;
}

.rank-num {
    color:#ffd700;
    font-weight:800;
    width:26px;
    text-align:center;
}

.rank-name {
    font-size:13px;
    font-weight:700;
    color:white;
}

.rank-score {
    color:#00c6ff;
    font-weight:800;
}

/* =====================================================
🎚️ SLIDERS — FIX TOTAL DEFINITIVO (ROJO ELIMINADO)
===================================================== */

/* -----------------------------------------------------
   TRACK INACTIVO (lado derecho / fondo)
----------------------------------------------------- */
.stSlider div[data-baseweb="slider"] > div {
    background-color: rgba(12, 22, 38, 0.85) !important;  /* azul oscuro / negro */
    border-radius: 8px;
}

/* -----------------------------------------------------
   TRACK ACTIVO (lado izquierdo — ERA ROJO)
----------------------------------------------------- */
.stSlider div[data-baseweb="slider"] > div > div {
    background: linear-gradient(
        90deg,
        #00c6ff,
        #1e3c72
    ) !important;
    border-radius: 8px;
}

/* -----------------------------------------------------
   THUMB / HANDLE (bolita)
----------------------------------------------------- */
.stSlider [role="slider"] {
    background-color: #00c6ff !important;
    border: 2px solid #ffffff !important;
    box-shadow:
        0 0 10px rgba(0,198,255,0.9),
        0 0 18px rgba(0,198,255,0.45) !important;
}

/* -----------------------------------------------------
   VALORES NUMÉRICOS (min / max / valor actual)
----------------------------------------------------- */
.stSlider span,
.stSlider [data-testid="stSliderThumbValue"] {
    color: #00c6ff !important;
    font-weight: 700;
}

/* -----------------------------------------------------
   FIX EXTRA — COLOR PRIMARIO STREAMLIT (ANTI ROJO GLOBAL)
----------------------------------------------------- */
:root {
    --primary-color: #00c6ff !important;
    --primary-color-hover: #00c6ff !important;
}

.stApp,
[data-testid="stAppViewContainer"],
section[data-testid="stSidebar"] {
    --primary-color: #00c6ff !important;
    --primary-color-hover: #00c6ff !important;
}


/* =====================================================
📂 SIDEBAR — MENU + RADIO (SIN ROJO)
===================================================== */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0e1117, #16213e);
    border-right:1px solid rgba(255,255,255,0.06);
}

section[data-testid="stSidebar"]
div[role="radiogroup"] > label[data-selected="true"] {
    background: linear-gradient(90deg, rgba(0,198,255,0.30), rgba(0,198,255,0.05));
    border-left:4px solid #00c6ff;
    border-radius:6px;
}

/* Radio button interno (punto) */
div[role="radiogroup"] label span div {
    background-color:#00c6ff !important;
}

/* Borde radio */
div[role="radiogroup"] label span[aria-hidden="true"] {
    border-color:#00c6ff !important;
}

/* =====================================================
📊 TABLAS — GLASS + HOVER
===================================================== */
div[data-testid="stDataFrame"] {
    background: linear-gradient(145deg, rgba(30,60,114,0.45), rgba(14,17,23,0.70));
    border-radius:16px;
    padding:8px;
    box-shadow:
        0 12px 30px rgba(0,0,0,0.40),
        inset 0 0 18px rgba(0,198,255,0.05);
}

div[data-testid="stDataFrame"] table {
    background-color:transparent !important;
    color:white !important;
}

div[data-testid="stDataFrame"] thead th {
    background:rgba(0,0,0,0.20) !important;
    color:#00c6ff !important;
    font-weight:700;
}

div[data-testid="stDataFrame"] tbody tr:hover td {
    background:rgba(0,198,255,0.15) !important;
}

/* =====================================================
🛠️ FIX DEFINITIVO — ROJOS / FOCUS / INVALID
===================================================== */
*:focus,
*:focus-visible {
    outline:none !important;
}

input, textarea {
    caret-color:#00c6ff !important;
}

div[data-baseweb="input"] > div,
div[data-baseweb="select"] > div,
div[data-baseweb="textarea"] > div {
    border:1px solid rgba(0,198,255,0.45) !important;
    background-color:rgba(14,17,23,0.85) !important;
    box-shadow:none !important;
}

div[data-baseweb="input"] > div:focus-within,
div[data-baseweb="select"] > div:focus-within,
div[data-baseweb="textarea"] > div:focus-within {
    border-color:#00c6ff !important;
    box-shadow:0 0 10px rgba(0,198,255,0.45) !important;
}

div[aria-invalid="true"],
div[aria-invalid="true"] * {
    border-color:#00c6ff !important;
    box-shadow:0 0 10px rgba(0,198,255,0.45) !important;
}

/* =====================================================
🚨 ALERTAS
===================================================== */
.stAlert.success {
    background-color:rgba(0,51,102,0.97) !important;
    color:#00c6ff !important;
    border-left:4px solid #00c6ff !important;
}
.stAlert.warning {
    background-color:rgba(51,43,0,0.97) !important;
    color:#ffd700 !important;
    border-left:4px solid #ffd700 !important;
}
.stAlert.error {
    background-color:rgba(51,0,0,0.97) !important;
    color:#ff6f61 !important;
    border-left:4px solid #ff6f61 !important;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# ARCHIVOS LOCALES (usuarios y cancha)
# =========================================================
FILE_USERS = "usuarios.csv"
CANCHA_IMG = "CANCHA.png"

if not os.path.exists(FILE_USERS):
    st.error("⚠️ Falta el archivo usuarios.csv con columnas: Usuario,Contraseña,Rol")
    st.stop()

df_users = pd.read_csv(FILE_USERS)
if not all(col in df_users.columns for col in ["Usuario", "Contraseña", "Rol"]):
    st.error("El archivo usuarios.csv debe tener columnas: Usuario,Contraseña,Rol")
    st.stop()

# =========================================================
# BLOQUE DE LOGIN CON ROLES
# =========================================================
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

st.markdown(f"### 👤 {CURRENT_USER} ({CURRENT_ROLE})")
st.markdown("---")

# =========================================================
# BLOQUE 2 / 5 — Funciones base + carga de datos + menú
# =========================================================

# ---------------------------------------------------------
# FUNCIONES AUXILIARES
# ---------------------------------------------------------

def calcular_edad(fecha_nac):
    try:
        fn = datetime.strptime(str(fecha_nac), "%d/%m/%Y")
        hoy = date.today()
        return hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))
    except Exception:
        return "?"


def generar_id_unico(df, columna="ID_Jugador"):
    if columna not in df.columns or df.empty:
        return 1
    ids = df[columna].dropna().astype(str)
    nums = [int(i) for i in ids if i.isdigit()]
    return max(nums) + 1 if nums else 1


# ---------------------------------------------------------
# FUNCIONES DE PROMEDIOS (OBLIGATORIAS PARA BLOQUE 3)
# ---------------------------------------------------------

def calcular_promedios_jugador(df_reports, id_jugador):
    if df_reports.empty:
        return None

    df = df_reports.copy()
    df["ID_Jugador"] = df["ID_Jugador"].astype(str)
    informes = df[df["ID_Jugador"] == str(id_jugador)]

    if informes.empty:
        return None

    metricas = [
        "Controles","Perfiles","Pase_corto","Pase_largo","Pase_filtrado",
        "1v1_defensivo","Recuperacion","Intercepciones","Duelos_aereos",
        "Regate","Velocidad","Duelos_ofensivos",
        "Resiliencia","Liderazgo","Inteligencia_tactica",
        "Inteligencia_emocional","Posicionamiento",
        "Vision_de_juego","Movimientos_sin_pelota"
    ]

    promedios = {}
    for m in metricas:
        if m in informes.columns:
            try:
                valores = (
                    informes[m]
                    .astype(str)
                    .str.replace(",", ".", regex=False)
                    .replace(["", "nan", "None", "-", "—"], 0)
                    .astype(float)
                )
                promedios[m] = round(valores.mean(), 2)
            except Exception:
                promedios[m] = 0.0
        else:
            promedios[m] = 0.0

    return promedios


def calcular_promedios_posicion(df_reports, df_players, posicion):
    if not posicion or df_reports.empty or df_players.empty:
        return None

    df_r = df_reports.copy()
    df_p = df_players.copy()

    df_r["ID_Jugador"] = df_r["ID_Jugador"].astype(str)
    df_p["ID_Jugador"] = df_p["ID_Jugador"].astype(str)

    ids = df_p[df_p["Posición"] == posicion]["ID_Jugador"].tolist()
    informes = df_r[df_r["ID_Jugador"].isin(ids)]

    if informes.empty:
        return None

    metricas = [
        "Controles","Perfiles","Pase_corto","Pase_largo","Pase_filtrado",
        "1v1_defensivo","Recuperacion","Intercepciones","Duelos_aereos",
        "Regate","Velocidad","Duelos_ofensivos",
        "Resiliencia","Liderazgo","Inteligencia_tactica",
        "Inteligencia_emocional","Posicionamiento",
        "Vision_de_juego","Movimientos_sin_pelota"
    ]

    promedios = {}
    for m in metricas:
        if m in informes.columns:
            try:
                valores = (
                    informes[m]
                    .astype(str)
                    .str.replace(",", ".", regex=False)
                    .replace(["", "nan", "None", "-", "—"], 0)
                    .astype(float)
                )
                promedios[m] = round(valores.mean(), 2)
            except Exception:
                promedios[m] = 0.0
        else:
            promedios[m] = 0.0

    return promedios


# ---------------------------------------------------------
# RADAR
# ---------------------------------------------------------

def radar_chart(prom_jugador, prom_posicion):
    if not prom_jugador:
        return

    categorias = list(prom_jugador.keys())
    valores_j = [float(prom_jugador.get(c, 0)) for c in categorias]
    valores_p = [float(prom_posicion.get(c, 0)) for c in categorias] if prom_posicion else [0]*len(categorias)

    valores_j += valores_j[:1]
    valores_p += valores_p[:1]

    angles = np.linspace(0, 2*np.pi, len(categorias), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor("#0e1117")
    ax.set_facecolor("#0e1117")

    ax.plot(angles, valores_j, color="cyan", linewidth=2)
    ax.fill(angles, valores_j, color="cyan", alpha=0.25)

    ax.plot(angles, valores_p, color="orange", linewidth=2)
    ax.fill(angles, valores_p, color="orange", alpha=0.25)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categorias, color="white", fontsize=9)
    ax.tick_params(colors="white")

    st.pyplot(fig)


# ---------------------------------------------------------
# CARGA DE DATOS
# ---------------------------------------------------------

@st.cache_data(ttl=120)
def cargar_datos():

    columnas_jug = ["ID_Jugador","Nombre","Fecha_Nac","Nacionalidad","Segunda_Nacionalidad",
                    "Altura","Pie_Hábil","Posición","Caracteristica","Club","Liga",
                    "Sexo","URL_Foto","URL_Perfil","Instagram","Fecha_Fin_Contrato"]

    columnas_inf = ["ID_Informe","ID_Jugador","Scout","Fecha_Partido","Fecha_Informe",
                    "Equipos_Resultados","Formación","Observaciones","Línea",
                    "Controles","Perfiles","Pase_corto","Pase_largo","Pase_filtrado",
                    "1v1_defensivo","Recuperacion","Intercepciones","Duelos_aereos",
                    "Regate","Velocidad","Duelos_ofensivos",
                    "Resiliencia","Liderazgo","Inteligencia_tactica",
                    "Inteligencia_emocional","Posicionamiento",
                    "Vision_de_juego","Movimientos_sin_pelota"]

    columnas_short = ["ID_Jugador","Nombre","Edad","Altura","Club","Posición",
                      "URL_Foto","URL_Perfil","Agregado_Por","Fecha_Agregado"]

    df_players = cargar_datos_sheets("Jugadores", columnas_jug)
    df_reports = cargar_datos_sheets("Informes", columnas_inf)
    df_short   = cargar_datos_sheets("Lista corta", columnas_short)

    # Normalización de IDs
    for df in (df_players, df_reports, df_short):
        if not df.empty and "ID_Jugador" in df.columns:
            df["ID_Jugador"] = df["ID_Jugador"].astype(str)

    return df_players, df_reports, df_short

# ---------------------------------------------------------
# INICIALIZACIÓN
# ---------------------------------------------------------

# 1️⃣ Carga base desde Sheets (SIN filtros)
df_players, df_reports, df_short = cargar_datos()

# 2️⃣ Guardar como fuente única en session_state
st.session_state["df_players"] = df_players.copy()
st.session_state["df_reports"] = df_reports.copy()
st.session_state["df_short"]   = df_short.copy()

# =========================================================
# 🔐 FILTRADO GLOBAL DE DATOS POR USUARIO (ÚNICO)
# =========================================================

# Fuente completa (ALL)
df_players_all = st.session_state["df_players"].copy()
df_reports_all = st.session_state["df_reports"].copy()
df_short_all   = st.session_state["df_short"].copy()

if CURRENT_ROLE != "admin":
    # Informes: solo los del scout
    df_reports_user = df_reports_all[
        df_reports_all["Scout"] == CURRENT_USER
    ].copy()

    # Lista corta: solo lo agregado por el scout
    df_short_user = df_short_all[
        df_short_all["Agregado_Por"] == CURRENT_USER
    ].copy()

    # Jugadores relacionados (informes + lista corta)
    ids = (
        set(df_reports_user["ID_Jugador"].astype(str)) |
        set(df_short_user["ID_Jugador"].astype(str))
    )

    df_players_user = df_players_all[
        df_players_all["ID_Jugador"].astype(str).isin(ids)
    ].copy()

else:
    # Admin ve todo
    df_reports_user = df_reports_all.copy()
    df_short_user   = df_short_all.copy()
    df_players_user = df_players_all.copy()

# -----------------------------
# Menú principal
# -----------------------------
menu = st.sidebar.radio(
    "📋 Menú principal",
    [
        "Panel General",
        "Agenda",
        "Jugadores",
        "Ver informes",
        "Lista corta",
        "Panel Scouts",
        "Área Préstamos"   # ← NUEVO
    ]
)


# =========================================================
# BLOQUE 3 / 5 — Sección Jugadores
# =========================================================

if menu == "Jugadores":

    st.subheader("Gestión de jugadores e informes individuales")

    # ---------------------------------------------------------
    # DATASETS
    # ---------------------------------------------------------
    df_players = df_players_all.copy()      # 🔓 todos los jugadores
    df_reports = df_reports_user.copy()     # 🔐 solo informes del scout

    # ---------------------------------------------------------
    # OPCIONES PREDEFINIDAS
    # ---------------------------------------------------------
    opciones_pies = ["Derecho", "Izquierdo", "Ambidiestro"]

    opciones_posiciones = [
        "Arquero", "Lateral derecho", "Defensa central derecho",
        "Defensa central izquierdo", "Lateral izquierdo",
        "Mediocampista defensivo", "Mediocampista mixto",
        "Mediocampista ofensivo", "Extremo derecho",
        "Extremo izquierdo", "Delantero centro"
    ]

    opciones_ligas = [
        "Argentina - LPF", "Argentina - Primera Nacional", "Argentina - Federal A",
        "Brasil - Serie A (Brasileirão)", "Brasil - Serie B",
        "Chile - Primera División", "Uruguay - Primera División",
        "Uruguay - Segunda División Profesional", "Paraguay - División Profesional",
        "Colombia - Categoría Primera A", "Ecuador - LigaPro Serie A",
        "Perú - Liga 1", "Venezuela - Liga FUTVE", "México - Liga MX",
        "España - LaLiga", "España - LaLiga 2", "Italia - Serie A", "Italia - Serie B",
        "Inglaterra - Premier League", "Inglaterra - Championship",
        "Francia - Ligue 1", "Alemania - Bundesliga", "Portugal - Primeira Liga",
        "Países Bajos - Eredivisie", "Suiza - Super League",
        "Polonia - Liga Polaca", "Bélgica - Pro League",
        "Grecia - Super League", "Turquía - Süper Lig",
        "Arabia Saudita - Saudi Pro League", "Estados Unidos - MLS",
        "Otro / Sin especificar"
    ]

    opciones_paises = [
        "Argentina", "Brasil", "Chile", "Uruguay", "Paraguay", "Colombia", "México",
        "Ecuador", "Perú", "Venezuela", "España", "Italia", "Francia", "Inglaterra",
        "Alemania", "Portugal", "Estados Unidos", "Canadá", "Bolivia",
        "Honduras", "Costa Rica", "El Salvador", "Panamá",
        "República Dominicana", "Guatemala", "Haití", "Jamaica", "Otro"
    ]

    opciones_caracteristicas = [
        "agresivo", "completo", "tiempista", "dinámico", "velocista", "goleador",
        "juego de espalda", "líder defensivo", "versátil", "posicional",
        "habilidoso", "táctico", "aguerrido", "resolutivo", "creativo",
        "preciso", "criterioso", "aplomado", "temperamental",
        "técnico", "conductor", "proyección"
    ]

    # ---------------------------------------------------------
    # BUSCADOR DE JUGADORES
    # ---------------------------------------------------------
    opciones = {
        f"{row['Nombre']} - {row['Club']}": row["ID_Jugador"]
        for _, row in df_players.iterrows()
    }

    seleccion_jug = st.selectbox(
        "🔍 Buscar jugador",
        [""] + list(opciones.keys())
    )

    # ---------------------------------------------------------
    # CREAR NUEVO JUGADOR
    # ---------------------------------------------------------
    if not seleccion_jug:

        with st.expander("➕ Agregar nuevo jugador", expanded=False):
            with st.form("nuevo_jugador_form", clear_on_submit=True):

                col1, col2 = st.columns(2)

                with col1:
                    nuevo_nombre = st.text_input("Nombre completo")
                    nueva_fecha = st.text_input("Fecha de nacimiento (dd/mm/aaaa)")
                    nueva_altura = st.number_input("Altura (cm)", 140, 210, 175)
                    nuevo_pie = st.selectbox("Pie hábil", opciones_pies)
                    nueva_posicion = st.selectbox("Posición principal", opciones_posiciones)
                    nueva_fecha_fin_contrato = st.text_input("Fin de contrato (dd/mm/aaaa)")

                with col2:
                    nuevo_club = st.text_input("Club actual")
                    nueva_liga = st.selectbox("Liga", opciones_ligas)
                    nueva_nacionalidad = st.selectbox("Nacionalidad", opciones_paises)
                    nueva_seg_nac = st.selectbox("Segunda nacionalidad", [""] + opciones_paises)
                    nueva_caracteristica = st.multiselect("Características", opciones_caracteristicas)
                    nueva_url_foto = st.text_input("URL Foto")
                    nueva_url_perfil = st.text_input("URL Perfil")
                    nueva_instagram = st.text_input("Instagram")

                guardar = st.form_submit_button("💾 Guardar jugador")

                if guardar and nuevo_nombre:
                    try:
                        nuevo_id = generar_id_unico(df_players_all, "ID_Jugador")
                        car_str = ", ".join(nueva_caracteristica)

                        fila = [
                            nuevo_id, nuevo_nombre, nueva_fecha,
                            nueva_nacionalidad, nueva_seg_nac,
                            nueva_altura, nuevo_pie, nueva_posicion,
                            car_str, nuevo_club, nueva_liga, "",
                            nueva_url_foto, nueva_url_perfil, nueva_instagram,
                            nueva_fecha_fin_contrato
                        ]

                        ws = obtener_hoja("Jugadores")
                        ws.append_row(fila, value_input_option="USER_ENTERED")

                        st.cache_data.clear()
                        st.experimental_rerun()

                    except Exception as e:
                        st.error(f"Error al guardar jugador: {e}")

    # ---------------------------------------------------------
    # MOSTRAR JUGADOR SELECCIONADO
    # ---------------------------------------------------------
    if seleccion_jug:

        id_jugador = opciones[seleccion_jug]
        jugador = df_players[df_players["ID_Jugador"] == id_jugador].iloc[0]

        col1, col2, col3 = st.columns([1.2, 1.2, 1.6])

        with col1:
            st.markdown(f"### {jugador['Nombre']}")

            if str(jugador.get("URL_Foto", "")).startswith("http"):
                st.image(jugador["URL_Foto"], width=160)

            edad = calcular_edad(jugador.get("Fecha_Nac"))

            nac1 = jugador.get("Nacionalidad", "-")
            nac2 = jugador.get("Segunda_Nacionalidad", "")
            st.write(f"📅 Nacimiento: {jugador.get('Fecha_Nac', '')} ({edad} años)")
            st.write(f"🌍 Nacionalidad: {nac1 if not nac2 else f'{nac1}, {nac2}'}")
            st.write(f"📏 Altura: {jugador.get('Altura', '-')} cm")
            st.write(f"👟 Pie hábil: {jugador.get('Pie_Hábil', '-')}")
            st.write(f"🎯 Posición: {jugador.get('Posición', '-')}")
            st.write(f"🏟️ Club: {jugador.get('Club', '-')} ({jugador.get('Liga', '-')})")

            if jugador.get("Fecha_Fin_Contrato"):
                st.write(f"📄 Fin de contrato: {jugador['Fecha_Fin_Contrato']}")

            if str(jugador.get("URL_Perfil", "")).startswith("http"):
                st.markdown(f"[🌐 Perfil externo]({jugador['URL_Perfil']})")

            if str(jugador.get("Instagram", "")).startswith("http"):
                st.markdown(f"[📸 Instagram]({jugador['Instagram']})")

            # ⭐ AGREGAR A LISTA CORTA (POR SEMESTRE)
            if CURRENT_ROLE in ["admin", "scout"]:
                if st.button("⭐ Agregar a lista corta"):
                    try:
                        ws_short = obtener_hoja("Lista corta")
                        data_short = ws_short.get_all_records()
                        df_short_local = pd.DataFrame(data_short)

                        from datetime import date
                        hoy = date.today()
                        ANIO_ACTUAL = hoy.year
                        SEMESTRE_ACTUAL = 1 if hoy.month <= 6 else 2

                        if not df_short_local.empty:
                            df_short_local["Fecha_Agregado_dt"] = pd.to_datetime(
                                df_short_local["Fecha_Agregado"],
                                format="%d/%m/%Y",
                                errors="coerce"
                            )

                            df_short_local["Año"] = df_short_local["Fecha_Agregado_dt"].dt.year
                            df_short_local["Semestre"] = df_short_local["Fecha_Agregado_dt"].dt.month.apply(
                                lambda m: 1 if m <= 6 else 2
                            )

                            existe = df_short_local[
                                (df_short_local["ID_Jugador"].astype(str) == str(jugador["ID_Jugador"])) &
                                (df_short_local["Agregado_Por"] == CURRENT_USER) &
                                (df_short_local["Año"] == ANIO_ACTUAL) &
                                (df_short_local["Semestre"] == SEMESTRE_ACTUAL)
                            ]
                        else:
                            existe = pd.DataFrame()

                        if not existe.empty:
                            st.info("⚠️ Ya agregaste este jugador a tu lista corta en este semestre")
                        else:
                            nueva_fila = [
                                jugador["ID_Jugador"],
                                jugador["Nombre"],
                                edad,
                                jugador.get("Altura", "-"),
                                jugador.get("Club", "-"),
                                jugador.get("Posición", "-"),
                                jugador.get("URL_Foto", ""),
                                jugador.get("URL_Perfil", ""),
                                CURRENT_USER,
                                hoy.strftime("%d/%m/%Y")
                            ]

                            ws_short.append_row(nueva_fila, value_input_option="USER_ENTERED")
                            st.toast("⭐ Jugador agregado a Lista Corta", icon="⭐")
                            st.cache_data.clear()

                    except Exception as e:
                        st.error(f"Error al agregar a lista corta: {e}")

            
        # ---------------------------------------------------------
        # EDITAR DATOS DEL JUGADOR
        # ---------------------------------------------------------
        with st.expander("✏️ Editar información del jugador", expanded=False):

            with st.form(f"editar_jugador_form_{jugador['ID_Jugador']}"):

                col1, col2 = st.columns(2)

                with col1:
                    e_nombre = st.text_input("Nombre completo", value=jugador.get("Nombre", ""))
                    e_fecha = st.text_input("Fecha de nacimiento (dd/mm/aaaa)", value=jugador.get("Fecha_Nac", ""))
                    e_altura = st.number_input(
                        "Altura (cm)", 140, 210,
                        int(float(jugador.get("Altura", 175))) if str(jugador.get("Altura", "")).strip() else 175
                    )
                    e_pie = st.selectbox(
                        "Pie hábil", opciones_pies,
                        index=opciones_pies.index(jugador["Pie_Hábil"]) if jugador["Pie_Hábil"] in opciones_pies else 0
                    )
                    e_pos = st.selectbox(
                        "Posición", opciones_posiciones,
                        index=opciones_posiciones.index(jugador["Posición"]) if jugador["Posición"] in opciones_posiciones else 0
                    )
                    e_fin_contrato = st.text_input(
                        "Fin de contrato (dd/mm/aaaa)",
                        value=str(jugador.get("Fecha_Fin_Contrato", ""))
                    )

                with col2:
                    e_club = st.text_input("Club actual", value=jugador.get("Club", ""))
                    e_liga = st.selectbox(
                        "Liga", opciones_ligas,
                        index=opciones_ligas.index(jugador["Liga"]) if jugador["Liga"] in opciones_ligas else 0
                    )
                    e_nac = st.selectbox(
                        "Nacionalidad principal", opciones_paises,
                        index=opciones_paises.index(jugador["Nacionalidad"]) if jugador["Nacionalidad"] in opciones_paises else 0
                    )

                    e_seg_opciones = [""] + opciones_paises
                    e_seg = st.selectbox(
                        "Segunda nacionalidad (opcional)",
                        e_seg_opciones,
                        index=e_seg_opciones.index(jugador.get("Segunda_Nacionalidad", "")) 
                        if jugador.get("Segunda_Nacionalidad", "") in e_seg_opciones else 0
                    )

                    e_car = st.multiselect(
                        "Características",
                        opciones_caracteristicas,
                        default=[
                            c.strip().lower()
                            for c in str(jugador.get("Caracteristica", "")).split(",")
                            if c.strip().lower() in [o.lower() for o in opciones_caracteristicas]
                        ]
                    )

                    e_foto = st.text_input("URL de foto", value=str(jugador.get("URL_Foto", "")))
                    e_link = st.text_input("URL perfil externo", value=str(jugador.get("URL_Perfil", "")))
                    e_instagram = st.text_input("URL Instagram", value=str(jugador.get("Instagram", "")))

                guardar_ed = st.form_submit_button("💾 Guardar cambios")

                if guardar_ed:
                    try:
                        ws = obtener_hoja("Jugadores")
                        data = ws.get_all_records()
                        df_actual = pd.DataFrame(data)

                        index_row = df_actual.index[
                            df_actual["ID_Jugador"].astype(str) == str(id_jugador)
                        ]

                        if not index_row.empty:
                            row_number = index_row[0] + 2
                            e_car_str = ", ".join(e_car) if e_car else ""

                            valores = [
                                id_jugador,
                                e_nombre,
                                e_fecha,
                                e_nac,
                                e_seg,
                                e_altura,
                                e_pie,
                                e_pos,
                                e_car_str,
                                e_club,
                                e_liga,
                                "",
                                e_foto,
                                e_link,
                                e_instagram,
                                e_fin_contrato
                            ]

                            ws.update(f"A{row_number}:P{row_number}", [valores])

                            st.cache_data.clear()
                            st.toast("✅ Datos actualizados correctamente.", icon="✅")
                            st.experimental_rerun()
                        else:
                            st.warning("⚠️ No se encontró el jugador en la hoja.")

                    except Exception as e:
                        st.error(f"⚠️ Error al guardar: {e}")


        # ---------------------------------------------------------
        # CARGAR NUEVO INFORME
        # ---------------------------------------------------------
        if CURRENT_ROLE in ["admin", "scout"]:

            st.markdown("---")
            st.subheader(f"📝 Cargar nuevo informe para {jugador['Nombre']}")

            with st.form(f"nuevo_informe_form_{jugador['ID_Jugador']}", clear_on_submit=True):

                scout = CURRENT_USER
                fecha_partido = st.date_input("Fecha del partido", format="DD/MM/YYYY")
                equipos_resultados = st.text_input("Equipos y resultado")
                formacion = st.selectbox(
                    "Formación",
                    ["4-2-3-1", "4-3-1-2", "4-4-2", "4-3-3", "3-5-2", "3-4-3", "5-3-2"]
                )

                observaciones = st.text_area("Observaciones generales", height=100)

                linea = st.selectbox(
                    "Línea de seguimiento",
                    [
                        "1ra (Fichar)",
                        "2da (Seguir)",
                        "3ra (Ver más adelante)",
                        "4ta (Descartar)",
                        "Joven Promesa"
                    ]
                )

                st.markdown("### Evaluación técnica (1 a 10)")

                with st.expander("🎯 Habilidades técnicas"):
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        controles = st.slider("Controles", 1, 10, 5, 1)
                        perfiles = st.slider("Perfiles", 1, 10, 5, 1)

                    with col2:
                        pase_corto = st.slider("Pase corto", 1, 10, 5, 1)
                        pase_largo = st.slider("Pase largo", 1, 10, 5, 1)

                    with col3:
                        pase_filtrado = st.slider("Pase filtrado", 1, 10, 5, 1)

                with st.expander("Aspectos defensivos"):
                    col1, col2 = st.columns(2)

                    with col1:
                        v1_def = st.slider("1v1 defensivo", 1, 10, 5, 1)
                        recuperacion = st.slider("Recuperación", 1, 10, 5, 1)

                    with col2:
                        intercepciones = st.slider("Intercepciones", 1, 10, 5, 1)
                        duelos_aereos = st.slider("Duelos aéreos", 1, 10, 5, 1)

                with st.expander("Aspectos ofensivos"):
                    col1, col2 = st.columns(2)

                    with col1:
                        regate = st.slider("Regate", 1, 10, 5, 1)
                        velocidad = st.slider("Velocidad", 1, 10, 5, 1)

                    with col2:
                        duelos_of = st.slider("Duelos ofensivos", 1, 10, 5, 1)

                with st.expander("Aspectos mentales / psicológicos"):
                    col1, col2 = st.columns(2)

                    with col1:
                        resiliencia = st.slider("Resiliencia", 1, 10, 5, 1)
                        liderazgo = st.slider("Liderazgo", 1, 10, 5, 1)

                    with col2:
                        int_tactica = st.slider("Inteligencia táctica", 1, 10, 5, 1)
                        int_emocional = st.slider("Inteligencia emocional", 1, 10, 5, 1)

                with st.expander("Aspectos tácticos"):
                    col1, col2 = st.columns(2)

                    with col1:
                        posicionamiento = st.slider("Posicionamiento", 1, 10, 5, 1)
                        vision = st.slider("Visión de juego", 1, 10, 5, 1)

                    with col2:
                        movimientos = st.slider("Movimientos sin pelota", 1, 10, 5, 1)

                guardar_informe = st.form_submit_button("Guardar informe")

                if guardar_informe:
                    try:

                        def to_float_safe(v):
                            try:
                                if isinstance(v, str):
                                    v = v.replace(",", ".")
                                return round(float(v), 2)
                            except Exception:
                                return 0.0

                        nuevo = [
                            len(df_reports) + 1,
                            jugador["ID_Jugador"],
                            CURRENT_USER,
                            fecha_partido.strftime("%d/%m/%Y"),
                            date.today().strftime("%d/%m/%Y"),
                            equipos_resultados,
                            formacion,
                            observaciones,
                            linea,
                            to_float_safe(controles),
                            to_float_safe(perfiles),
                            to_float_safe(pase_corto),
                            to_float_safe(pase_largo),
                            to_float_safe(pase_filtrado),
                            to_float_safe(v1_def),
                            to_float_safe(recuperacion),
                            to_float_safe(intercepciones),
                            to_float_safe(duelos_aereos),
                            to_float_safe(regate),
                            to_float_safe(velocidad),
                            to_float_safe(duelos_of),
                            to_float_safe(resiliencia),
                            to_float_safe(liderazgo),
                            to_float_safe(int_tactica),
                            to_float_safe(int_emocional),
                            to_float_safe(posicionamiento),
                            to_float_safe(vision),
                            to_float_safe(movimientos)
                        ]

                        ws_inf = obtener_hoja("Informes")
                        ws_inf.append_row(nuevo, value_input_option="USER_ENTERED")

                        st.cache_data.clear()
                        df_reports = df_reports_usercargar_datos_sheets("Informes")

                        st.toast(
                            f"✅ Informe guardado correctamente para {jugador['Nombre']}",
                            icon="✅"
                        )
                        st.experimental_rerun()

                    except Exception as e:
                        st.error(f"⚠️ Error al guardar el informe: {e}")



# =========================================================
# BLOQUE 4 / 5 — Ver Informes (optimizado y con ficha completa)
# =========================================================

if menu == "Ver informes":
    st.subheader("📝 Informes cargados")

    # ---------------------------------------------------------
    # DATASETS SEGÚN ROL
    # ---------------------------------------------------------
    df_players = df_players_all.copy()     # 🔓 todos los jugadores

    if CURRENT_ROLE == "admin":
        df_reports = df_reports_all.copy()     # admin ve todo
    else:
        df_reports = df_reports_user.copy()    # scout ve solo sus informes

    # ---------------------------------------------------------
    # UNIFICACIÓN SEGURA
    # ---------------------------------------------------------
    try:
        df_reports["ID_Jugador"] = df_reports["ID_Jugador"].astype(str)
        df_players["ID_Jugador"] = df_players["ID_Jugador"].astype(str)
        df_merged = df_reports.merge(df_players, on="ID_Jugador", how="left")
    except Exception as e:
        st.error(f"❌ Error al unir datos: {e}")
        st.stop()

    # =========================================================
    # FILTROS SUPERIORES
    # =========================================================
    st.markdown("### 🔎 Filtros")

    f1, f2, f3, f4, f5, f6 = st.columns(6)

    with f1:
        filtro_scout = st.multiselect(
            "Scout",
            sorted(df_merged["Scout"].dropna().unique())
        )

    with f2:
        filtro_jugador = st.multiselect(
            "Jugador",
            sorted(df_merged["Nombre"].dropna().unique())
        )

    with f3:
        filtro_club = st.multiselect(
            "Club",
            sorted(df_merged["Club"].dropna().unique())
        )

    with f4:
        filtro_pos = st.multiselect(
            "Posición",
            sorted(df_merged["Posición"].dropna().unique())
        )

    with f5:
        filtro_linea = st.multiselect(
            "Línea",
            sorted(df_merged["Línea"].dropna().unique())
        )

    with f6:
        filtro_nac = st.multiselect(
            "Nacionalidad",
            sorted(df_merged["Nacionalidad"].dropna().unique())
        )

    # ---------------------------------------------------------
    # APLICAR FILTROS
    # ---------------------------------------------------------
    df_filtrado = df_merged.copy()

    if filtro_scout:
        df_filtrado = df_filtrado[df_filtrado["Scout"].isin(filtro_scout)]
    if filtro_jugador:
        df_filtrado = df_filtrado[df_filtrado["Nombre"].isin(filtro_jugador)]
    if filtro_club:
        df_filtrado = df_filtrado[df_filtrado["Club"].isin(filtro_club)]
    if filtro_pos:
        df_filtrado = df_filtrado[df_filtrado["Posición"].isin(filtro_pos)]
    if filtro_linea:
        df_filtrado = df_filtrado[df_filtrado["Línea"].isin(filtro_linea)]
    if filtro_nac:
        df_filtrado = df_filtrado[df_filtrado["Nacionalidad"].isin(filtro_nac)]

    # =========================================================
    # TABLA PRINCIPAL (AgGrid) — DISEÑO ORIGINAL
    # =========================================================
    if not df_filtrado.empty:
        st.markdown("### 📋 Informes disponibles")

        columnas = [
            "Fecha_Informe", "Nombre", "Club",
            "Línea", "Scout", "Equipos_Resultados", "Observaciones"
        ]

        df_tabla = df_filtrado[[c for c in columnas if c in df_filtrado.columns]].copy()

        try:
            df_tabla["Fecha_dt"] = pd.to_datetime(
                df_tabla["Fecha_Informe"],
                format="%d/%m/%Y",
                errors="coerce"
            )
            df_tabla = (
                df_tabla
                .sort_values("Fecha_dt", ascending=False)
                .drop(columns="Fecha_dt")
            )
        except Exception:
            pass

        gb = GridOptionsBuilder.from_dataframe(df_tabla)
        gb.configure_selection("single", use_checkbox=False)
        gb.configure_pagination(enabled=True, paginationAutoPageSize=True)
        gb.configure_grid_options(domLayout="normal")

        widths = {
            "Fecha_Informe": 100,
            "Nombre": 150,
            "Club": 130,
            "Línea": 120,
            "Scout": 120,
            "Equipos_Resultados": 150,
            "Observaciones": 420
        }

        for c in df_tabla.columns:
            if c == "Observaciones":
                gb.configure_column(c, wrapText=True, autoHeight=True, width=widths[c])
            else:
                gb.configure_column(c, width=widths.get(c, 120))

        grid_response = AgGrid(
            df_tabla,
            gridOptions=gb.build(),
            fit_columns_on_grid_load=True,
            theme="blue",
            height=580,
            allow_unsafe_jscode=True,
            update_mode="MODEL_CHANGED",
            custom_css={
                ".ag-header": {
                    "background-color": "#1e3c72",
                    "color": "white",
                    "font-weight": "bold",
                    "font-size": "13px"
                },
                ".ag-row-even": {
                    "background-color": "#2a5298 !important",
                    "color": "white !important"
                },
                ".ag-row-odd": {
                    "background-color": "#3b6bbf !important",
                    "color": "white !important"
                },
                ".ag-cell": {
                    "white-space": "normal !important",
                    "line-height": "1.25",
                    "padding": "5px",
                    "font-size": "12.5px"
                },
            },
        )

        # =========================================================
        # SELECCIÓN ULTRA SEGURA (AgGrid FIX DEFINITIVO)
        # =========================================================
        selected_data = grid_response.get("selected_rows")

        # Normalización TOTAL
        if selected_data is None:
            selected_data = []
        elif isinstance(selected_data, pd.DataFrame):
            selected_data = selected_data.to_dict("records")
        elif isinstance(selected_data, dict):
            selected_data = [selected_data]
        elif not isinstance(selected_data, list):
            selected_data = []

        # A PARTIR DE ACÁ SIEMPRE ES list[dict]
        if len(selected_data) > 0:
            jugador_sel = selected_data[0]
            nombre_jug = jugador_sel.get("Nombre", "")


        # =========================================================
        # FICHA DEL JUGADOR
        # =========================================================
        if len(selected_data) > 0:

            jugador_sel = selected_data[0]
            nombre_jug = jugador_sel.get("Nombre", "")
            jugador_data = df_players[df_players["Nombre"] == nombre_jug]

            if not jugador_data.empty:
                j = jugador_data.iloc[0]

                st.markdown("---")
                st.markdown(f"### 🧾 Ficha del jugador: **{j['Nombre']}**")

                col1, col2, col3 = st.columns([1, 1, 1])

                with col1:
                    if pd.notna(j.get("URL_Foto")) and str(j["URL_Foto"]).startswith("http"):
                        st.image(j["URL_Foto"], width=150)

                    st.markdown(f"**📍 Club:** {j.get('Club','-')}")
                    st.markdown(f"**🎯 Posición:** {j.get('Posición','-')}")
                    st.markdown(f"**📏 Altura:** {j.get('Altura','-')} cm")
                    st.markdown(f"**📅 Edad:** {calcular_edad(j.get('Fecha_Nac'))}")

                with col2:
                    st.markdown(f"**👟 Pie hábil:** {j.get('Pie_Hábil','-')}")
                    st.markdown(f"**🌍 Nacionalidad:** {j.get('Nacionalidad','-')}")
                    st.markdown(f"**🏆 Liga:** {j.get('Liga','-')}")

                with col3:
                    st.markdown(f"**🧠 Característica:** {j.get('Caracteristica','-')}")

                    if pd.notna(j.get("Instagram")) and str(j["Instagram"]).startswith("http"):
                        st.markdown(f"[📸 Instagram]({j['Instagram']})")

                    if pd.notna(j.get("URL_Perfil")) and str(j["URL_Perfil"]).startswith("http"):
                        st.markdown(f"[🌐 Perfil externo]({j['URL_Perfil']})")

                # =========================================================
                # EXPORTAR PDF SIMPLE
                # =========================================================
                if st.button("📥 Exportar informe simple", key=f"pdf_{j['ID_Jugador']}"):
                    try:
                        from fpdf import FPDF
                        from io import BytesIO

                        pdf = FPDF()
                        pdf.add_page()
                        pdf.set_font("Arial", "B", 14)
                        pdf.cell(0, 10, "SCOUTING REPORT", ln=True)

                        pdf.set_font("Arial", "", 11)
                        pdf.ln(5)
                        pdf.cell(0, 8, f"Jugador: {j['Nombre']}", ln=True)
                        pdf.cell(0, 8, f"Club: {j.get('Club','-')}", ln=True)
                        pdf.cell(0, 8, f"Posición: {j.get('Posición','-')}", ln=True)
                        pdf.ln(4)

                        informes_pdf = df_reports[df_reports["ID_Jugador"] == j["ID_Jugador"]]

                        for _, inf in informes_pdf.iterrows():
                            pdf.multi_cell(
                                0, 6,
                                f"- {inf['Fecha_Partido']} | {inf['Scout']} | {inf['Línea']}\n"
                                f"{inf['Observaciones'][:300]}"
                            )
                            pdf.ln(2)

                        buffer = BytesIO()
                        pdf.output(buffer)
                        buffer.seek(0)

                        st.download_button(
                            "📄 Descargar PDF",
                            buffer,
                            file_name=f"Informe_{j['Nombre']}.pdf",
                            mime="application/pdf"
                        )

                    except Exception as e:
                        st.error(f"⚠️ Error PDF: {e}")

                # =========================================================
                # EXPANDER — EDITAR / ELIMINAR INFORMES
                # =========================================================
                informes_sel = df_reports[df_reports["ID_Jugador"] == j["ID_Jugador"]]

                for idx, inf in enumerate(informes_sel.itertuples()):
                    titulo = f"{inf.Fecha_Partido} | Scout: {inf.Scout} | Línea: {inf.Línea}"

                    with st.expander(titulo):
                        with st.form(f"form_edit_{inf.ID_Informe}_{idx}"):

                            nuevo_scout = st.text_input("Scout", inf.Scout)
                            nueva_fecha = st.text_input("Fecha del partido", inf.Fecha_Partido)
                            nuevos_equipos = st.text_input("Equipos y resultado", inf.Equipos_Resultados)

                            opciones_linea = [
                                "1ra (Fichar)", "2da (Seguir)",
                                "3ra (Ver más adelante)", "4ta (Descartar)",
                                "Joven Promesa"
                            ]

                            nueva_linea = st.selectbox(
                                "Línea",
                                opciones_linea,
                                index=opciones_linea.index(inf.Línea)
                                if inf.Línea in opciones_linea else 2
                            )

                            nuevas_obs = st.text_area(
                                "Observaciones",
                                inf.Observaciones,
                                height=120
                            )

                            guardar = st.form_submit_button("💾 Guardar cambios")

                            if guardar:
                                try:
                                    df_all = df_reports_all.copy()

                                    df_all.loc[
                                        df_all["ID_Informe"] == inf.ID_Informe,
                                        ["Scout","Fecha_Partido","Equipos_Resultados","Línea","Observaciones"]
                                    ] = [
                                        nuevo_scout,
                                        nueva_fecha,
                                        nuevos_equipos,
                                        nueva_linea,
                                        nuevas_obs
                                    ]

                                    ws_inf = obtener_hoja("Informes")
                                    ws_inf.update(
                                        [df_all.columns.values.tolist()] +
                                        df_all.values.tolist()
                                    )

                                    st.cache_data.clear()
                                    st.toast("✓ Informe actualizado correctamente", icon="✅")
                                    st.rerun()

                                except Exception as e:
                                    st.error(f"⚠️ Error al actualizar el informe: {e}")

                            st.markdown("---")

                            confirmar = st.checkbox(
                                "Confirmar eliminación del informe",
                                key=f"del_chk_{inf.ID_Informe}"
                            )

                            eliminar = st.form_submit_button(
                                "🗑️ Eliminar informe",
                                disabled=not confirmar
                            )

                            if eliminar:
                                try:
                                    eliminar_por_id(
                                        nombre_hoja="Informes",
                                        id_col="ID_Informe",
                                        id_valor=inf.ID_Informe
                                    )

                                    st.cache_data.clear()
                                    st.toast("🗑️ Informe eliminado correctamente", icon="🗑️")
                                    st.rerun()

                                except Exception as e:
                                    st.error(f"⚠️ Error al eliminar el informe: {e}")

    else:
        st.info("📍 Seleccioná un registro para ver la ficha del jugador.")


# =========================================================
# BLOQUE 5 / 5 — Lista corta táctica
# =========================================================

if menu == "Lista corta":
    st.subheader("Lista corta de jugadores")

    # -----------------------------------------------------
    # DATASETS
    # -----------------------------------------------------
    df_short = df_short_user.copy()          # decisiones (todas; privacidad luego)
    df_players = df_players_all.copy()       # base completa de jugadores

    if df_short.empty:
        st.info("No hay jugadores cargados en la lista corta actualmente.")
        st.stop()

    # =========================================================
    # FILTRO DE PRIVACIDAD POR USUARIO
    # =========================================================
    if CURRENT_ROLE not in ["admin"]:
        df_short = df_short[df_short["Agregado_Por"] == CURRENT_USER]

    # Cortar referencia (evita SettingWithCopyWarning)
    df_short = df_short.copy()

    # =========================================================
    # NORMALIZAR FECHA / AÑO / SEMESTRE (LISTA CORTA)
    # =========================================================
    if "Fecha_Agregado" not in df_short.columns:
        df_short["Fecha_Agregado"] = None

    df_short["Fecha_dt"] = pd.to_datetime(
        df_short["Fecha_Agregado"],
        errors="coerce",
        dayfirst=True
    )

    df_short["Año"] = df_short["Fecha_dt"].dt.year.astype("Int64")

    df_short["Semestre"] = df_short["Fecha_dt"].dt.month.apply(
        lambda m: "1º" if m <= 6 else "2º" if pd.notna(m) else ""
    )

    # =========================================================
    # 🔧 AGREGADO 1 / 2 — DEFAULT AÑO + SEMESTRE ACTUAL
    # =========================================================
    hoy = datetime.today()
    anio_actual = hoy.year
    semestre_actual = "1º" if hoy.month <= 6 else "2º"

    opciones_anio = (
        df_short["Año"]
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    if anio_actual in opciones_anio:
        default_anio = anio_actual
    else:
        default_anio = max(opciones_anio) if opciones_anio else ""

    default_semestre = semestre_actual

    # =========================================================
    # FILTROS
    # =========================================================
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        filtro_scout = st.selectbox(
            "Scout",
            [""] + sorted(df_short["Agregado_Por"].dropna().unique())
        )

    with col2:
        filtro_liga = st.selectbox(
            "Liga",
            [""] + sorted(df_players["Liga"].dropna().unique())
        )

    with col3:
        filtro_nac = st.selectbox(
            "Nacionalidad",
            [""] + sorted(df_players["Nacionalidad"].dropna().unique())
        )

    with col4:
        filtro_anio = st.selectbox(
            "Año",
            [""] + sorted(opciones_anio, reverse=True),
            index=(
                sorted(opciones_anio, reverse=True).index(default_anio) + 1
                if default_anio in opciones_anio else 0
            )
        )

    with col5:
        filtro_sem = st.selectbox(
            "Semestre",
            ["", "1º", "2º"],
            index=1 if default_semestre == "1º" else 2
        )

    with col6:
        filtro_promesa = st.selectbox(
            "Promesa",
            ["", "Sí", "No"]
        )

    # =========================================================
    # APLICAR FILTROS
    # =========================================================
    df_filtrado = df_short.copy()

    if filtro_scout:
        df_filtrado = df_filtrado[df_filtrado["Agregado_Por"] == filtro_scout]

    if filtro_liga:
        ids_liga = (
            df_players[df_players["Liga"] == filtro_liga]["ID_Jugador"]
            .astype(str)
        )
        df_filtrado = df_filtrado[
            df_filtrado["ID_Jugador"].astype(str).isin(ids_liga)
        ]

    if filtro_nac:
        ids_nac = (
            df_players[df_players["Nacionalidad"] == filtro_nac]["ID_Jugador"]
            .astype(str)
        )
        df_filtrado = df_filtrado[
            df_filtrado["ID_Jugador"].astype(str).isin(ids_nac)
        ]

    if filtro_anio:
        df_filtrado = df_filtrado[df_filtrado["Año"] == int(filtro_anio)]

    if filtro_sem:
        df_filtrado = df_filtrado[df_filtrado["Semestre"] == filtro_sem]

    if filtro_promesa == "Sí":
        df_filtrado = df_filtrado[
            df_filtrado["Posición"].str.contains("Promesa", case=False, na=False)
        ]
    elif filtro_promesa == "No":
        df_filtrado = df_filtrado[
            ~df_filtrado["Posición"].str.contains("Promesa", case=False, na=False)
        ]

    total_jugadores = len(df_filtrado)

    st.markdown(
        f"### Vista táctica (sistema 4-2-3-1) — "
        f"<span style='color:#00c6ff;'>Total jugadores: {total_jugadores}</span>",
        unsafe_allow_html=True
    )

    # =========================================================
    # CSS TARJETAS
    # =========================================================
    st.markdown(
        """
        <style>
        .player-card {
            display:flex;align-items:center;justify-content:flex-start;
            background:linear-gradient(90deg,#0e1117,#1e3c72);
            padding:0.6em 0.8em;border-radius:12px;color:white;
            font-family:Arial, sans-serif;box-shadow:0 0 6px rgba(0,0,0,0.4);
            width:230px;min-height:75px;margin:6px auto;transition:0.2s;
        }
        .player-card:hover {transform:scale(1.05);box-shadow:0 0 12px #00c6ff;}
        .player-photo {
            width:55px;height:55px;border-radius:50%;object-fit:cover;
            border:2px solid #00c6ff;margin-right:10px;
        }
        .player-info h5 {font-size:13px;margin:0;color:#00c6ff;font-weight:bold;}
        .player-info p {font-size:11.5px;margin:1px 0;color:#ccc;}
        .player-link a {color:#00c6ff;font-size:10.5px;text-decoration:none;}
        .player-link a:hover{text-decoration:underline;}
        .line-title {
            color:#00c6ff;font-weight:bold;font-size:16px;
            margin:10px 0 5px;text-align:center;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # =========================================================
    # SISTEMA 4-2-3-1
    # =========================================================
    sistema = {
        "Arqueros": ["Arquero"],
        "Defensas": [
            "Lateral derecho",
            "Defensa central derecho",
            "Defensa central izquierdo",
            "Lateral izquierdo",
        ],
        "Mediocampistas defensivos": [
            "Mediocampista mixto",
            "Mediocampista defensivo",
        ],
        "Mediocampistas ofensivos": [
            "Extremo derecho",
            "Mediocampista ofensivo",
            "Extremo izquierdo",
        ],
        "Delanteros": ["Delantero centro"],
    }

    # =========================================================
    # RENDER DE JUGADORES
    # =========================================================
    for linea, posiciones in sistema.items():
        jugadores_linea = df_filtrado[df_filtrado["Posición"].isin(posiciones)]
        if jugadores_linea.empty:
            continue

        cantidad = len(jugadores_linea)
        with st.expander(f"{linea} ({cantidad})", expanded=True):

            if linea in ["Arqueros", "Delanteros"]:
                jugadores_lista = list(jugadores_linea.iterrows())
                for fila in range(0, len(jugadores_lista), 5):
                    fila_jugadores = jugadores_lista[fila:fila + 5]
                    fila_cols = st.columns(len(fila_jugadores))
                    for fcol, (_, row) in zip(fila_cols, fila_jugadores):
                        with fcol:
                            url_foto = str(row.get("URL_Foto", "")).strip()
                            if not url_foto.startswith("http"):
                                url_foto = "https://via.placeholder.com/60"

                            partes = str(row.get("Nombre", "")).split()
                            nombre = partes[0] if partes else "Sin nombre"
                            apellido = partes[-1] if len(partes) > 1 else ""

                            edad = row.get("Edad", "-")
                            altura = row.get("Altura", "-")
                            club = row.get("Club", "-")
                            url_perfil = str(row.get("URL_Perfil", ""))

                            link_html = (
                                f"<div class='player-link'><a href='{url_perfil}' target='_blank'>Ver perfil</a></div>"
                                if url_perfil.startswith("http") else ""
                            )

                            st.markdown(
                                f"""
                                <div class="player-card">
                                    <img src="{url_foto}" class="player-photo"/>
                                    <div class="player-info">
                                        <h5>{nombre} {apellido}</h5>
                                        <p>{club}</p>
                                        <p>Edad: {edad} | Altura: {altura} cm</p>
                                        {link_html}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

            else:
                cols = st.columns(len(posiciones))
                for i, pos in enumerate(posiciones):
                    jugadores_pos = jugadores_linea[jugadores_linea["Posición"] == pos]
                    with cols[i]:
                        st.markdown(
                            f"<div class='line-title'>{pos}</div>",
                            unsafe_allow_html=True
                        )

                        if jugadores_pos.empty:
                            st.markdown(
                                "<p style='color:gray;font-size:11px;text-align:center;'>— Vacante —</p>",
                                unsafe_allow_html=True
                            )
                            continue

                        jugadores_lista = list(jugadores_pos.iterrows())
                        salto = 2 if "Mediocampista" in pos else 1

                        for fila in range(0, len(jugadores_lista), salto):
                            fila_jugadores = jugadores_lista[fila:fila + salto]
                            fila_cols = st.columns(len(fila_jugadores))
                            for fcol, (_, row) in zip(fila_cols, fila_jugadores):
                                with fcol:
                                    url_foto = str(row.get("URL_Foto", "")).strip()
                                    if not url_foto.startswith("http"):
                                        url_foto = "https://via.placeholder.com/60"

                                    partes = str(row.get("Nombre", "")).split()
                                    nombre = partes[0] if partes else "Sin nombre"
                                    apellido = partes[-1] if len(partes) > 1 else ""

                                    edad = row.get("Edad", "-")
                                    altura = row.get("Altura", "-")
                                    club = row.get("Club", "-")
                                    url_perfil = str(row.get("URL_Perfil", ""))

                                    link_html = (
                                        f"<div class='player-link'><a href='{url_perfil}' target='_blank'>Ver perfil</a></div>"
                                        if url_perfil.startswith("http") else ""
                                    )

                                    st.markdown(
                                        f"""
                                        <div class="player-card">
                                            <img src="{url_foto}" class="player-photo"/>
                                            <div class="player-info">
                                                <h5>{nombre} {apellido}</h5>
                                                <p>{club}</p>
                                                <p>Edad: {edad} | Altura: {altura} cm</p>
                                                {link_html}
                                            </div>
                                        </div>
                                        """,
                                        unsafe_allow_html=True
                                    )

    # =========================================================
    # GESTOR DE LISTA CORTA — Eliminación
    # =========================================================
    st.markdown("---")
    st.markdown("### 🗑️ Gestor de Lista Corta (Eliminar jugadores)")

    busqueda = st.text_input("Buscar jugador para eliminar (por nombre o club)")

    if busqueda:
        df_busqueda = df_filtrado[
            df_filtrado["Nombre"].str.contains(busqueda, case=False, na=False) |
            df_filtrado["Club"].str.contains(busqueda, case=False, na=False)
        ]
    else:
        df_busqueda = df_filtrado.copy()

    if df_busqueda.empty:
        st.info("No se encontraron jugadores que coincidan con la búsqueda.")
    else:
        st.dataframe(
            df_busqueda[["Nombre", "Posición", "Club", "Agregado_Por"]],
            use_container_width=True,
            hide_index=True
        )

        jugador_sel = st.selectbox(
            "Seleccionar jugador a eliminar",
            [""] + sorted(df_busqueda["Nombre"].unique())
        )

        if jugador_sel:
            jugador_row = df_busqueda[df_busqueda["Nombre"] == jugador_sel].iloc[0]
            st.warning(f"⚠️ Vas a eliminar a **{jugador_sel}** de TU lista corta.")
            confirmar = st.checkbox("Confirmar eliminación")

            if st.button("🗑️ Eliminar jugador", type="primary", disabled=not confirmar):
                try:
                    ws_short = obtener_hoja("Lista corta")
                    data_short = ws_short.get_all_records()
                    df_short_local = pd.DataFrame(data_short)

                    fila = df_short_local.index[
                        (df_short_local["ID_Jugador"].astype(str) == str(jugador_row["ID_Jugador"])) &
                        (df_short_local["Agregado_Por"] == CURRENT_USER)
                    ]

                    if not fila.empty:
                        df_short_local = df_short_local.drop(fila[0])
                        ws_short.clear()
                        ws_short.update(
                            [df_short_local.columns.values.tolist()] +
                            df_short_local.values.tolist()
                        )
                        st.toast(
                            f"🗑️ Jugador {jugador_sel} eliminado correctamente de TU lista.",
                            icon="🗑️"
                        )
                        st.cache_data.clear()
                        st.experimental_rerun()
                    else:
                        st.warning("⚠️ No se encontró el jugador en tu lista corta.")
                except Exception as e:
                    st.error(f"⚠️ Error al eliminar: {e}")


# =========================================================
# 🕐 BLOQUE 6 / 6 — Agenda de Seguimientos — ScoutingApp PRO
# =========================================================
# - Versión FINAL BLINDADA (2025)
# - Sin errores JSON, sin borrado de hojas, con backup automático
# - Cards en filas de 5 columnas, con etiquetas dinámicas y hover
# =========================================================

if menu == "Agenda":
    import os
    import pandas as pd
    from datetime import datetime, timedelta

    st.markdown("<h2 style='text-align:center;color:#00c6ff;'>📅 Agenda de Seguimiento — ScoutingApp PRO</h2>", unsafe_allow_html=True)

    # =========================================================
    # CSS PERSONALIZADO
    # =========================================================
    st.markdown("""
    <style>
    body, .stApp { background-color:#0e1117 !important; color:white !important; font-family:'Segoe UI',sans-serif; }
    h1,h2,h3,h4,h5,h6 { color:white !important; }
    .card-container { display:flex; flex-wrap:wrap; justify-content:center; gap:14px; margin-bottom:1em; }
    .card {
        background:linear-gradient(90deg,#0e1117,#1e3c72);
        border-radius:10px; padding:0.7em 1em; color:white;
        box-shadow:0 0 8px rgba(0,0,0,0.5); transition:0.2s ease-in-out;
        width:220px; min-height:135px;
    }
    .card:hover { transform:scale(1.04); box-shadow:0 0 10px #00c6ff; }
    .card h5 { color:#00c6ff; font-size:14px; margin:0 0 3px 0; text-align:left; }
    .card p { font-size:12px; color:#b0b0b0; margin:2px 0; }
    .card.visto { opacity:0.7; background:linear-gradient(90deg,#1a1f2e,#2a3a5a); }
    .label {
        display:inline-block; font-size:11px; padding:2px 6px; border-radius:5px;
        font-weight:bold; margin-bottom:5px;
    }
    .vencido { background-color:#8b0000; color:white; }
    .hoy { background-color:#ffd700; color:black; }
    .proximo { background-color:#006400; color:white; }
    .futuro { background-color:#004488; color:white; }
    </style>
    """, unsafe_allow_html=True)

    # =========================================================
    # CARGA / CREACIÓN DE HOJA "Agenda"
    # =========================================================
    columnas = ["ID_Jugador", "Nombre", "Scout", "Fecha_Revisar", "Motivo", "Visto"]

    try:
        ws = obtener_hoja("Agenda", columnas)
        data = ws.get_all_records()
        df_agenda = pd.DataFrame(data)
    except Exception as e:
        st.warning("⚠️ No existía la hoja 'Agenda'. Se creará automáticamente en la base de datos.")
        try:
            ws = obtener_hoja("Agenda", columnas)
            ws.append_row(columnas)
            df_agenda = pd.DataFrame(columns=columnas)
        except Exception as err:
            st.error(f"❌ No se pudo crear la hoja Agenda: {err}")
            st.stop()

    if df_agenda.empty:
        df_agenda = pd.DataFrame(columns=columnas)

    df_agenda["Fecha_Revisar"] = pd.to_datetime(df_agenda["Fecha_Revisar"], errors="coerce")
    df_agenda["Visto"] = df_agenda["Visto"].astype(str).str.lower().isin(["si", "sí", "true", "1"])

    hoy = pd.Timestamp(datetime.now().date())
    pendientes = df_agenda[df_agenda["Visto"] == False]
    vistos = df_agenda[df_agenda["Visto"] == True]

    # =========================================================
    # FUNCIÓN DE BACKUP LOCAL
    # =========================================================
    def backup_local(df):
        try:
            df.to_csv("agenda_backup.csv", index=False, encoding="utf-8")
        except Exception:
            pass

    # =========================================================
    # FUNCIÓN: MARCAR VISTO (segura y serializable)
    # =========================================================
    def marcar_visto(nombre):
        df_agenda.loc[df_agenda["Nombre"] == nombre, "Visto"] = "Sí"

        # Convertir fechas a texto antes de enviar
        df_tmp = df_agenda.copy()
        if "Fecha_Revisar" in df_tmp.columns:
            df_tmp["Fecha_Revisar"] = df_tmp["Fecha_Revisar"].astype(str)

        backup_local(df_tmp)

        try:
            ws.update([df_tmp.columns.values.tolist()] + df_tmp.fillna("").values.tolist())
            st.toast(f"✅ {nombre} marcado como visto.", icon="✅")
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"⚠️ Error al actualizar seguimiento: {e}")

    # =========================================================
    # FUNCIÓN: GUARDAR NUEVO (con backup)
    # =========================================================
    def guardar_nuevo(id_jugador, nombre, scout, fecha, motivo):
        nueva = [id_jugador, nombre, scout, fecha.strftime("%Y-%m-%d"), motivo, "Pendiente"]
        try:
            ws.append_row(nueva)
            df_local = pd.concat([df_agenda, pd.DataFrame([{
                "ID_Jugador": id_jugador,
                "Nombre": nombre,
                "Scout": scout,
                "Fecha_Revisar": fecha.strftime("%Y-%m-%d"),
                "Motivo": motivo,
                "Visto": "Pendiente"
            }])], ignore_index=True)
            backup_local(df_local)
            st.success(f"✅ Seguimiento agendado para {nombre} el {fecha.strftime('%d/%m/%Y')}")
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"⚠️ Error al guardar seguimiento: {e}")

    # =========================================================
    # BLOQUE PENDIENTES (máx 5 columnas por fila)
    # =========================================================
    with st.expander("🕐 Seguimientos pendientes", expanded=True):
        if pendientes.empty:
            st.info("No hay seguimientos pendientes.")
        else:
            jugadores_lista = list(pendientes.sort_values("Fecha_Revisar").iterrows())
            for i in range(0, len(jugadores_lista), 5):
                fila = jugadores_lista[i:i+5]
                cols = st.columns(len(fila))
                for col, (_, row) in zip(cols, fila):
                    nombre, scout, fecha, motivo = row["Nombre"], row["Scout"], row["Fecha_Revisar"], row["Motivo"]
                    if pd.isnull(fecha): continue
                    dias = (fecha - hoy).days
                    if dias < 0: label = "<span class='label vencido'>Vencido</span>"
                    elif dias == 0: label = "<span class='label hoy'>Hoy</span>"
                    elif dias <= 7: label = f"<span class='label proximo'>En {dias} días</span>"
                    else: label = f"<span class='label futuro'>En {dias} días</span>"

                    with col:
                        st.markdown(f"""
                        <div class='card'>
                            {label}
                            <h5>{nombre}</h5>
                            <p>Scout: {scout}</p>
                            <p>📅 {fecha.strftime('%d/%m/%Y')}</p>
                            <p><i>{motivo}</i></p>
                        </div>
                        """, unsafe_allow_html=True)
                        st.button("👁 Marcar visto", key=f"mark_{nombre}_{i}", on_click=marcar_visto, args=(nombre,))

    # =========================================================
    # BLOQUE YA VISTOS (máx 5 columnas por fila)
    # =========================================================
    with st.expander("👁 Seguimientos ya vistos", expanded=False):
        if vistos.empty:
            st.info("No hay jugadores vistos aún.")
        else:
            jugadores_lista = list(vistos.sort_values("Fecha_Revisar").iterrows())
            for i in range(0, len(jugadores_lista), 5):
                fila = jugadores_lista[i:i+5]
                cols = st.columns(len(fila))
                for col, (_, row) in zip(cols, fila):
                    nombre, scout, fecha, motivo = row["Nombre"], row["Scout"], row["Fecha_Revisar"], row["Motivo"]
                    if pd.isnull(fecha): continue
                    with col:
                        st.markdown(f"""
                        <div class='card visto'>
                            <span class='label futuro'>Visto</span>
                            <h5>{nombre}</h5>
                            <p>Scout: {scout}</p>
                            <p>📅 {fecha.strftime('%d/%m/%Y')}</p>
                            <p><i>{motivo}</i></p>
                        </div>
                        """, unsafe_allow_html=True)

    # =========================================================
    # FORMULARIO NUEVO SEGUIMIENTO
    # =========================================================
    st.markdown("---")
    with st.expander("➕ Agendar nuevo seguimiento", expanded=False):
        jugadores_dict = {row["Nombre"]: row["ID_Jugador"] for _, row in df_players.iterrows()}
        col1, col2 = st.columns(2)
        with col1:
            jugador_sel = st.selectbox("Seleccioná un jugador", [""] + list(jugadores_dict.keys()))
            scout = st.text_input("Scout responsable", value=CURRENT_USER)
        with col2:
            fecha_rev = st.date_input("Fecha de revisión", value=datetime.now().date() + timedelta(days=7))
            motivo = st.text_area("Motivo del seguimiento", height=70)

        if jugador_sel and st.button("💾 Guardar seguimiento"):
            id_jugador = jugadores_dict[jugador_sel]
            guardar_nuevo(id_jugador, jugador_sel, scout, fecha_rev, motivo)

# =========================================================
# 🏠 PANEL GENERAL — ScoutingApp PRO (FINAL + CONSENSO)
# =========================================================
if menu == "Panel General":

    st.markdown(
        "<h2 style='text-align:center;color:#00c6ff;'>📊 Panel General — ScoutingApp PRO</h2>",
        unsafe_allow_html=True
    )

    # =========================
    # DATA BASE
    # =========================
    df_players = df_players_user.copy()
    df_reports = df_reports_user.copy()
    df_short = df_short_user.copy()

    df_players["ID_Jugador"] = df_players["ID_Jugador"].astype(str)
    df_reports["ID_Jugador"] = df_reports["ID_Jugador"].astype(str)
    df_short["ID_Jugador"] = df_short["ID_Jugador"].astype(str)

    # =========================
    # FECHAS
    # =========================
    df_reports["Fecha_Informe_dt"] = pd.to_datetime(
        df_reports["Fecha_Informe"], errors="coerce", dayfirst=True
    )

    hoy = datetime.today()
    hace_30 = hoy - timedelta(days=30)

    # =========================
    # EDAD SEGURA
    # =========================
    def edad_segura(fecha):
        try:
            f = datetime.strptime(str(fecha), "%d/%m/%Y")
            return int((hoy - f).days / 365.25)
        except:
            return None

    df_players["Edad"] = df_players["Fecha_Nac"].apply(edad_segura)

    # =========================
    # MÉTRICAS LIMPIAS
    # =========================
    metricas = [
        "Controles","Perfiles","Pase_corto","Pase_largo","Pase_filtrado",
        "1v1_defensivo","Recuperacion","Intercepciones","Duelos_aereos",
        "Regate","Velocidad","Duelos_ofensivos",
        "Resiliencia","Liderazgo","Inteligencia_tactica",
        "Inteligencia_emocional","Posicionamiento","Vision_de_juego",
        "Movimientos_sin_pelota"
    ]

    for m in metricas:
        if m in df_reports.columns:
            df_reports[m] = (
                df_reports[m]
                .astype(str)
                .str.replace(",", ".", regex=False)
                .replace(["", "nan", "None", "-", "—"], 0)
                .astype(float)
            )
        else:
            df_reports[m] = 0.0

    # =========================
    # KPIs
    # =========================
    inicio_semestre = datetime(hoy.year, 1, 1) if hoy.month <= 6 else datetime(hoy.year, 7, 1)
    jugadores_sem = df_reports[df_reports["Fecha_Informe_dt"] >= inicio_semestre]["ID_Jugador"].nunique()
    informes_30 = df_reports[df_reports["Fecha_Informe_dt"] >= hace_30].shape[0]

    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-card"><div class="kpi-title">Jugadores evaluados</div><div class="kpi-value">{df_players["ID_Jugador"].nunique()}</div></div>
        <div class="kpi-card"><div class="kpi-title">Informes cargados</div><div class="kpi-value">{len(df_reports)}</div></div>
        <div class="kpi-card"><div class="kpi-title">Jugadores este semestre</div><div class="kpi-value">{jugadores_sem}</div></div>
        <div class="kpi-card"><div class="kpi-title">Informes últimos 30 días</div><div class="kpi-value">{informes_30}</div></div>
    </div>
    """, unsafe_allow_html=True)

    # =====================================================
    # ⭐ CONSENSO — LISTA CORTA
    # =====================================================
    st.markdown("<div class='panel-title'>⭐ Consenso en Lista Corta</div>", unsafe_allow_html=True)

    df_short["Fecha_Agregado_dt"] = pd.to_datetime(
        df_short["Fecha_Agregado"], errors="coerce", dayfirst=True
    )

    col_c1, col_c2 = st.columns(2)

    with col_c1:
        filtro_anio = st.selectbox(
            "Año",
            ["Todos"] + sorted(df_short["Fecha_Agregado_dt"].dt.year.dropna().unique().tolist())
        )

    with col_c2:
        filtro_sem = st.selectbox(
            "Semestre",
            ["Todos", "1° semestre", "2° semestre"]
        )

    df_consenso = df_short.copy()

    if filtro_anio != "Todos":
        df_consenso = df_consenso[df_consenso["Fecha_Agregado_dt"].dt.year == filtro_anio]

    if filtro_sem != "Todos":
        if filtro_sem == "1° semestre":
            df_consenso = df_consenso[df_consenso["Fecha_Agregado_dt"].dt.month <= 6]
        else:
            df_consenso = df_consenso[df_consenso["Fecha_Agregado_dt"].dt.month >= 7]

    df_consenso = (
        df_consenso
        .groupby(["ID_Jugador","Nombre","Club","Posición"], as_index=False)
        .agg(Cantidad_Scouts=("Agregado_Por","nunique"))
    )

    df_consenso = df_consenso[df_consenso["Cantidad_Scouts"] > 1]

    if df_consenso.empty:
        st.info("No hay jugadores con consenso entre scouts.")
    else:
        st.dataframe(
            df_consenso.sort_values("Cantidad_Scouts", ascending=False),
            use_container_width=True,
            hide_index=True
        )

    # =====================================================
    # ⏰ SEGUIMIENTOS PRIORITARIOS VENCIDOS
    # =====================================================
    st.markdown("<div class='panel-title'>⏰ Seguimientos prioritarios vencidos</div>", unsafe_allow_html=True)

    lineas_prioritarias = ["1ra (Fichar)", "2da (Seguir)", "Joven Promesa"]

    df_last = (
        df_reports
        .sort_values("Fecha_Informe_dt")
        .groupby("ID_Jugador")
        .last()
        .reset_index()
    )

    df_last = df_last[df_last["Línea"].isin(lineas_prioritarias)]
    df_last["Dias_sin_evaluar"] = (hoy - df_last["Fecha_Informe_dt"]).dt.days

    df_last = df_last[
        (df_last["Dias_sin_evaluar"] > 46) &
        (df_last["Dias_sin_evaluar"] <= 100)
    ]

    if CURRENT_ROLE != "admin":
        df_last = df_last[df_last["Scout"] == CURRENT_USER]

    df_alertas = df_last.merge(
        df_players[["ID_Jugador","Nombre","Club","Posición"]],
        on="ID_Jugador",
        how="left"
    )

    col_f1, col_f2, col_f3 = st.columns(3)

    with col_f1:
        filtro_pos = st.multiselect(
            "Posición",
            sorted(df_alertas["Posición"].dropna().unique().tolist())
        )

    with col_f2:
        filtro_linea = st.multiselect(
            "Línea",
            sorted(df_alertas["Línea"].dropna().unique().tolist())
        )

    with col_f3:
        filtro_dias = st.selectbox(
            "Días sin evaluar",
            ["Todos", "47–60", "61–80", "81–100"]
        )

    if filtro_pos:
        df_alertas = df_alertas[df_alertas["Posición"].isin(filtro_pos)]

    if filtro_linea:
        df_alertas = df_alertas[df_alertas["Línea"].isin(filtro_linea)]

    if filtro_dias != "Todos":
        rangos = {
            "47–60": (47, 60),
            "61–80": (61, 80),
            "81–100": (81, 100)
        }
        r = rangos[filtro_dias]
        df_alertas = df_alertas[
            (df_alertas["Dias_sin_evaluar"] >= r[0]) &
            (df_alertas["Dias_sin_evaluar"] <= r[1])
        ]

    if df_alertas.empty:
        st.success("No hay seguimientos prioritarios vencidos.")
    else:
        st.dataframe(
            df_alertas[["Nombre","Club","Posición","Línea","Fecha_Informe","Dias_sin_evaluar"]],
            use_container_width=True,
            hide_index=True
        )

    # =========================
    # CONTRATOS POR VENCER
    # =========================
    if "Fecha_Fin_Contrato" in df_players.columns:

        df_c = df_players.copy()
        df_c["Fecha_Fin_dt"] = pd.to_datetime(df_c["Fecha_Fin_Contrato"], errors="coerce", dayfirst=True)
        df_c = df_c.dropna(subset=["Fecha_Fin_dt"])

        lim6 = hoy + timedelta(days=180)
        lim12 = hoy + timedelta(days=365)

        df6 = df_c[df_c["Fecha_Fin_dt"] <= lim6]
        df12 = df_c[(df_c["Fecha_Fin_dt"] > lim6) & (df_c["Fecha_Fin_dt"] <= lim12)]

        st.markdown("<div class='panel-title'>📄 Contratos por vencer</div>", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1: st.metric("🔴 ≤ 6 meses", len(df6))
        with c2: st.metric("🟡 ≤ 12 meses", len(df12))

        if not df6.empty or not df12.empty:
            st.dataframe(
                pd.concat([df6, df12]).sort_values("Fecha_Fin_dt")[
                    ["Nombre","Club","Posición","Fecha_Fin_Contrato"]
                ],
                use_container_width=True,
                hide_index=True
            )

    # =========================
    # TOPS POR POSICIÓN
    # =========================
    df_scores = (
        df_reports
        .groupby("ID_Jugador")[metricas]
        .mean()
        .mean(axis=1)
        .reset_index(name="Score")
        .merge(
            df_players[["ID_Jugador","Nombre","Posición"]],
            on="ID_Jugador",
            how="left"
        )
        .sort_values("Score", ascending=False)
    )

    def render_top(df, titulo):
        st.markdown(f"<div class='panel-title'>{titulo}</div>", unsafe_allow_html=True)
        if df.empty:
            st.info("Sin datos")
            return
        for i, r in enumerate(df.head(10).itertuples(), 1):
            st.markdown(f"""
            <div class='rank-card'>
                <div class='rank-left'>
                    <div class='rank-num'>#{i}</div>
                    <div class='rank-name'>{r.Nombre}</div>
                </div>
                <div class='rank-score'>{round(r.Score,2)}</div>
            </div>
            """, unsafe_allow_html=True)

    posiciones = [
        ("Arquero","🧤 Arqueros"),
        ("Lateral derecho","➡️ Laterales derechos"),
        ("Defensa central derecho","🛡️ Centrales derechos"),
        ("Defensa central izquierdo","🛡️ Centrales izquierdos"),
        ("Lateral izquierdo","⬅️ Laterales izquierdos"),
        ("Mediocampista defensivo","🔒 Volantes defensivos"),
        ("Mediocampista mixto","🔄 Volantes mixtos"),
        ("Mediocampista ofensivo","🎯 Volantes ofensivos"),
        ("Extremo derecho","⚡ Extremos derechos"),
        ("Extremo izquierdo","⚡ Extremos izquierdos"),
        ("Delantero centro","🎯 Delanteros centro"),
    ]

    cols = st.columns(4)
    for i, (pos, titulo) in enumerate(posiciones):
        with cols[i % 4]:
            render_top(df_scores[df_scores["Posición"] == pos], titulo)

    # =========================
    # COMPARADOR DE JUGADORES
    # =========================
    st.markdown("<div class='panel-title'>🆚 Comparador de jugadores</div>", unsafe_allow_html=True)

    col_f1, col_f2, col_f3 = st.columns(3)

    opciones_pos = sorted(df_players["Posición"].dropna().astype(str).unique().tolist())
    opciones_pie = sorted(df_players["Pie_Hábil"].dropna().astype(str).unique().tolist())

    with col_f1:
        filtro_pos = st.selectbox("Posición", ["Todas"] + opciones_pos)
    with col_f2:
        filtro_pie = st.selectbox("Pie hábil", ["Todos"] + opciones_pie)
    with col_f3:
        edad_min, edad_max = st.slider("Edad", 15, 45, (18, 35))

    df_base = df_players.copy()
    if filtro_pos != "Todas":
        df_base = df_base[df_base["Posición"] == filtro_pos]
    if filtro_pie != "Todos":
        df_base = df_base[df_base["Pie_Hábil"] == filtro_pie]

    df_base = df_base[(df_base["Edad"] >= edad_min) & (df_base["Edad"] <= edad_max)]

    opciones_cmp = {f"{r.Nombre} ({r.Club})": r.ID_Jugador for r in df_base.itertuples()}

    seleccionados = st.multiselect(
        "Seleccioná de 2 a 6 jugadores",
        list(opciones_cmp.keys()),
        max_selections=6
    )

    if 2 <= len(seleccionados) <= 6:
        ids = [opciones_cmp[n] for n in seleccionados]

        df_cmp = (
            df_reports[df_reports["ID_Jugador"].isin(ids)]
            .groupby("ID_Jugador")[metricas]
            .mean()
            .reset_index()
            .merge(
                df_players[["ID_Jugador","Nombre","Posición","Edad","Club","Pie_Hábil"]],
                on="ID_Jugador",
                how="left"
            )
        )

        st.dataframe(
            df_cmp[["Nombre","Club","Posición","Pie_Hábil","Edad"] + metricas],
            use_container_width=True,
            hide_index=True
        )

# =========================================================
# 🧭 PANEL SCOUTS — BLOQUE ESTABLE Y COHERENTE
# =========================================================
if menu == "Panel Scouts":

    # -----------------------------------------------------
    # 🔐 CONTROL DE ACCESO
    # -----------------------------------------------------
    if CURRENT_ROLE not in ["admin", "scout"]:
        st.warning("⛔ No tenés permisos para acceder a este panel.")
        st.stop()

    st.markdown(
        "<h2 style='text-align:center;color:#00c6ff;'>Panel de Control de Scouts</h2>",
        unsafe_allow_html=True
    )

    # -----------------------------------------------------
    # 📦 DATA BASE (YA FILTRADA POR USUARIO)
    # -----------------------------------------------------
    df_reports = df_reports_user.copy()
    df_players = df_players_user.copy()

    if df_reports.empty:
        st.info("No hay informes disponibles.")
        st.stop()

    # -----------------------------------------------------
    # 🧹 NORMALIZACIÓN BÁSICA
    # -----------------------------------------------------
    df_reports["Scout"] = df_reports["Scout"].astype(str).str.strip()
    df_reports["ID_Jugador"] = df_reports["ID_Jugador"].astype(str)
    df_players["ID_Jugador"] = df_players["ID_Jugador"].astype(str)

    # -----------------------------------------------------
    # 🕒 FECHAS
    # -----------------------------------------------------
    df_reports["Fecha_dt"] = pd.to_datetime(
        df_reports["Fecha_Informe"],
        errors="coerce",
        dayfirst=True
    )

    df_reports["Año"] = df_reports["Fecha_Informe"].astype(str).str[-4:]
    df_reports["Mes_num"] = df_reports["Fecha_dt"].dt.month
    df_reports["Semestre"] = df_reports["Mes_num"].apply(
        lambda m: "1º" if m and m <= 6 else "2º"
    )
    df_reports["Mes"] = df_reports["Fecha_dt"].dt.strftime("%Y-%m")

    # -----------------------------------------------------
    # 🔗 MERGE CON JUGADORES
    # -----------------------------------------------------
    df = df_reports.merge(
        df_players[["ID_Jugador", "Posición", "Liga"]],
        on="ID_Jugador",
        how="left"
    )

    # -----------------------------------------------------
    # 🔎 FILTROS
    # -----------------------------------------------------
    st.markdown("### 🔎 Filtros")

    f1, f2, f3 = st.columns(3)

    with f1:
        filtro_anio = st.multiselect(
            "Año",
            sorted(df["Año"].dropna().unique(), reverse=True)
        )

    with f2:
        filtro_sem = st.multiselect("Semestre", ["1º", "2º"])

    with f3:
        if CURRENT_ROLE == "admin":
            filtro_scout = st.multiselect(
                "Scout",
                sorted(df["Scout"].dropna().unique())
            )
        else:
            filtro_scout = []

    # -----------------------------------------------------
    # 🎯 DATAFRAME FINAL
    # -----------------------------------------------------
    df_f = df.copy()

    if filtro_anio:
        df_f = df_f[df_f["Año"].isin(filtro_anio)]
    if filtro_sem:
        df_f = df_f[df_f["Semestre"].isin(filtro_sem)]
    if filtro_scout:
        df_f = df_f[df_f["Scout"].isin(filtro_scout)]

    # -----------------------------------------------------
    # 📊 KPIs
    # -----------------------------------------------------
    st.markdown("### 📌 Actividad del período")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("📝 Informes", len(df_f))
    k2.metric("👤 Scouts activos", df_f["Scout"].nunique())
    k3.metric("🎯 Jugadores", df_f["ID_Jugador"].nunique())
    k4.metric("🏟️ Ligas", df_f["Liga"].nunique())

    # -----------------------------------------------------
    # 🏆 RANKING
    # -----------------------------------------------------
    pesos = {
        "1ra (Fichar)": 3,
        "2da (Seguir)": 2,
        "3ra (Ver más adelante)": 1
    }

    df_rank = df_f.copy()
    df_rank["Peso"] = df_rank["Línea"].map(pesos).fillna(0.5)

    ranking = (
        df_rank.groupby("Scout")
        .agg(
            Informes=("ID_Jugador", "count"),
            Jugadores=("ID_Jugador", "nunique"),
            Calidad=("Peso", "sum")
        )
        .reset_index()
    )

    ranking["Score"] = (ranking["Calidad"] / ranking["Informes"]).round(2)
    ranking = ranking.sort_values(["Score", "Informes"], ascending=False)

    st.markdown("### 🏆 Ranking de scouts")
    st.dataframe(ranking, use_container_width=True)

    # -----------------------------------------------------
    # 📈 GRÁFICOS
    # -----------------------------------------------------
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📈 Evolución mensual total")

        total_mes = (
            df_f.groupby("Mes")
            .size()
            .reset_index(name="Informes")
            .sort_values("Mes")
        )

        fig = px.line(total_mes, x="Mes", y="Informes", markers=True)
        fig = apply_glass_plotly(fig)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 🧭 Observaciones por posición")

        pos_df = df_f["Posición"].value_counts().reset_index()
        pos_df.columns = ["Posición", "Cantidad"]

        fig = px.pie(pos_df, names="Posición", values="Cantidad", hole=0.45)
        fig = apply_glass_plotly(fig)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### 📊 Evolución mensual por scout")

        scout_mes = (
            df_f.groupby(["Mes", "Scout"])
            .size()
            .reset_index(name="Informes")
            .sort_values("Mes")
        )

        fig = px.line(
            scout_mes,
            x="Mes",
            y="Informes",
            color="Scout",
            markers=True
        )
        fig = apply_glass_plotly(fig)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 📊 Informes por scout")

        bar_df = (
            df_f.groupby("Scout")
            .size()
            .reset_index(name="Informes")
        )

        fig = px.bar(bar_df, x="Scout", y="Informes", text="Informes")
        fig = apply_glass_plotly(fig)
        st.plotly_chart(fig, use_container_width=True)

    # -----------------------------------------------------
    # 🎯 DISTRIBUCIÓN DE DECISIONES
    # -----------------------------------------------------
    st.markdown("### 🎯 Distribución de decisiones por scout")

    tabla_lineas = (
        df_f.groupby(["Scout", "Línea"])
        .size()
        .reset_index(name="Cantidad")
        .pivot(index="Scout", columns="Línea", values="Cantidad")
        .fillna(0)
        .astype(int)
    )

    st.dataframe(tabla_lineas, use_container_width=True)

# =========================================================
# BLOQUE — ÁREA PRÉSTAMOS (Power BI)
# =========================================================

if menu == "Área Préstamos":

    st.markdown("## 🔄 Área Préstamos — Seguimiento de jugadores cedidos")
    st.markdown(
        """
        <p style="color:#b0b0b0;font-size:14px;">
        Panel de control para monitorear jugadores a préstamo: minutos, continuidad,
        rendimiento competitivo y situación contractual.
        </p>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")

    powerbi_url = "https://app.powerbi.com/view?r=eyJrIjoiODg0NjhjMjMtZmRlNy00MGNhLWFmMGEtNDJjZThiZjQwODY4IiwidCI6ImVjYTkwN2Y1LTYwNmMtNDJmNS04NTM2LTUwYjY4ZTRhMGM4MyJ9"

    st.components.v1.iframe(
        src=powerbi_url,
        height=900,
        scrolling=True
    )


# =========================================================
# CIERRE PROFESIONAL (footer)
# =========================================================
st.markdown("---")
st.markdown(f"""
<div style="text-align:center;color:#00c6ff;margin-top:30px;">
    <h4>ScoutingApp Profesional v2.3</h4>
    <p>Usuario activo: <strong>{CURRENT_USER}</strong> ({CURRENT_ROLE})</p>
    <p style="color:gray;font-size:13px;">
        Desarrollada por Mariano Cirone · Área de Scouting Profesional
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown(
    "<p style='text-align:center;color:gray;font-size:12px;'>© 2025 · Mariano Cirone · ScoutingApp Profesional</p>",
    unsafe_allow_html=True
)


