# =========================================================
# BLOQUE 1 / 5 — Conexión + Configuración inicial + Login
# =========================================================
# ⚽ ScoutingApp Profesional v2 — Conectada a Google Sheets
# =========================================================
# - Carga directa desde "Scouting_DB" (Jugadores / Informes / Lista corta)
# - Login por roles (admin / scout / viewer)
# - Diseño oscuro #0e1117 + acento #00c6ff
# =========================================================

import os
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

from io import BytesIO
from datetime import date, datetime, timedelta
from fpdf import FPDF
from st_aggrid import AgGrid, GridOptionsBuilder
import matplotlib.patches as patches
import gspread
from google.oauth2.service_account import Credentials

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

# =========================================================
# CARGAR ESTILOS Y CSS PERSONALIZADO
# =========================================================
try:
    from ui.style import load_custom_css
    load_custom_css()
except Exception:
    pass

st.markdown("""
<style>
.stSlider > div[data-baseweb="slider"] > div { background: transparent !important; }
.stSlider > div[data-baseweb="slider"] > div > div { background-color: #00c6ff !important; }
.stSlider [role="slider"] {
    background-color: #00c6ff !important;
    border: 2px solid #ffffff !important;
    box-shadow: 0 0 4px #00c6ff !important;
}
.stAlert.success { background-color: #003366 !important; color: #00c6ff !important; border-left: 4px solid #00c6ff !important; }
.stAlert.warning { background-color: #332b00 !important; color: #ffd700 !important; border-left: 4px solid #ffd700 !important; }
.stAlert.error   { background-color: #330000 !important; color: #ff6f61 !important; border-left: 4px solid #ff6f61 !important; }
h1, h2, h3, h4, h5, h6, .stMarkdown { color: white !important; }
body, .stApp { background-color: #0e1117 !important; }
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
# BLOQUE 2 / 5 — Funciones base + carga de datos + menú (OPTIMIZADO)
# =========================================================
# - Misma estructura y lógica original
# - Se agregan controles de cache granular y sincronización inmediata
# =========================================================

# =========================================================
# FUNCIONES AUXILIARES Y DE CÁLCULO (versión estable y segura)
# =========================================================

def calcular_edad(fecha_nac):
    """Calcula edad a partir de una fecha DD/MM/AAAA; devuelve '?' si es inválida."""
    try:
        fn = datetime.strptime(str(fecha_nac), "%d/%m/%Y")
        hoy = date.today()
        return hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))
    except Exception:
        return "?"


def generar_id_unico(df, columna="ID_Jugador"):
    """Genera ID incremental único basado en la columna dada."""
    if columna not in df.columns or df.empty:
        return 1
    ids_existentes = df[columna].dropna().astype(str).tolist()
    numeros = [int(i) for i in ids_existentes if i.isdigit()]
    return max(numeros) + 1 if numeros else 1


def calcular_promedios_jugador(df_reports, id_jugador):
    """Calcula promedios reales (0-5) del jugador, corrigiendo valores no numéricos."""
    if df_reports.empty:
        return None

    df_reports["ID_Jugador"] = df_reports["ID_Jugador"].astype(str)
    informes = df_reports[df_reports["ID_Jugador"] == str(id_jugador)]
    if informes.empty:
        return None

    columnas = [
        "Controles","Perfiles","Pase_corto","Pase_largo","Pase_filtrado",
        "1v1_defensivo","Recuperacion","Intercepciones","Duelos_aereos",
        "Regate","Velocidad","Duelos_ofensivos","Resiliencia","Liderazgo",
        "Inteligencia_tactica","Inteligencia_emocional","Posicionamiento",
        "Vision_de_juego","Movimientos_sin_pelota"
    ]

    promedios = {}
    for col in columnas:
        if col in informes.columns:
            try:
                valores = (
                    informes[col]
                    .astype(str)
                    .str.replace(",", ".", regex=False)
                    .replace(["", "nan", "None", "-", "—"], 0)
                    .astype(float)
                )
                prom = np.mean(valores)
                if prom > 5:
                    prom = prom / 10
                promedios[col] = round(float(prom), 2)
            except Exception:
                promedios[col] = 0.0
        else:
            promedios[col] = 0.0
    return promedios


def calcular_promedios_posicion(df_reports, df_players, posicion):
    """Promedio global de la posición, limpiando valores no numéricos."""
    if df_players.empty or df_reports.empty:
        return None

    df_players["ID_Jugador"] = df_players["ID_Jugador"].astype(str)
    df_reports["ID_Jugador"] = df_reports["ID_Jugador"].astype(str)

    jugadores_pos = df_players[df_players["Posición"] == posicion]
    ids = jugadores_pos["ID_Jugador"].astype(str).tolist()
    informes = df_reports[df_reports["ID_Jugador"].isin(ids)]
    if informes.empty:
        return None

    columnas = [
        "Controles","Perfiles","Pase_corto","Pase_largo","Pase_filtrado",
        "1v1_defensivo","Recuperacion","Intercepciones","Duelos_aereos",
        "Regate","Velocidad","Duelos_ofensivos","Resiliencia","Liderazgo",
        "Inteligencia_tactica","Inteligencia_emocional","Posicionamiento",
        "Vision_de_juego","Movimientos_sin_pelota"
    ]

    promedios = {}
    for col in columnas:
        if col in informes.columns:
            try:
                valores = (
                    informes[col]
                    .astype(str)
                    .str.replace(",", ".", regex=False)
                    .replace(["", "nan", "None", "-", "—"], 0)
                    .astype(float)
                )
                prom = np.mean(valores)
                if prom > 5:
                    prom = prom / 10
                promedios[col] = round(float(prom), 2)
            except Exception:
                promedios[col] = 0.0
        else:
            promedios[col] = 0.0
    return promedios


def radar_chart(prom_jugador, prom_posicion):
    """Radar comparativo jugador vs promedio de posición."""
    if not prom_jugador:
        return

    categorias = list(prom_jugador.keys())
    valores_jug = [float(prom_jugador.get(c, 0) or 0) for c in categorias]
    valores_pos = [float(prom_posicion.get(c, 0) or 0) for c in categorias] if prom_posicion else [0]*len(categorias)
    valores_jug += valores_jug[:1]
    valores_pos += valores_pos[:1]

    angles = np.linspace(0, 2 * np.pi, len(categorias), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6,6), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor("#0e1117")
    ax.set_facecolor("#0e1117")

    ax.plot(angles, valores_jug, linewidth=2, color="cyan", label="Jugador")
    ax.fill(angles, valores_jug, color="cyan", alpha=0.25)
    ax.plot(angles, valores_pos, linewidth=2, color="orange", label="Promedio Posición")
    ax.fill(angles, valores_pos, color="orange", alpha=0.25)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categorias, color="white", fontsize=9)
    ax.tick_params(colors="white")
    ax.legend(
        loc="upper right",
        bbox_to_anchor=(1.2, 1.1),
        facecolor="#0e1117",
        labelcolor="white"
    )
    st.pyplot(fig)


def generar_pdf_ficha(jugador, informes):
    """Genera PDF con la ficha e informes del jugador."""
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


# =========================================================
# REFRESCO AUTOMÁTICO DE DATAFRAMES (nuevo, mejorado)
# =========================================================
def actualizar_dataframe(nombre_hoja, df_local):
    """🔧 Recarga solo la hoja indicada sin limpiar toda la cache."""
    try:
        df_nuevo = leer_hoja(nombre_hoja)  # usa la cache granular
        if df_nuevo.empty:
            return df_local
        if nombre_hoja == "Jugadores":
            st.session_state["df_players"] = df_nuevo
        elif nombre_hoja == "Informes":
            st.session_state["df_reports"] = df_nuevo
        elif nombre_hoja == "Lista corta":
            st.session_state["df_short"] = df_nuevo
        st.session_state["last_update"] = time.time()
        return df_nuevo
    except Exception as e:
        st.warning(f"⚠️ No se pudo refrescar '{nombre_hoja}': {e}")
        return df_local

# =========================================================
# CARGA DE DATOS DESDE GOOGLE SHEETS (memoria sincronizada)
# =========================================================
@st.cache_data(ttl=120)
def cargar_datos():
    """Carga los tres datasets principales desde Google Sheets (optimizada)."""
    columnas_jug = [
        "ID_Jugador","Nombre","Fecha_Nac","Nacionalidad","Segunda_Nacionalidad",
        "Altura","Pie_Hábil","Posición","Caracteristica","Club","Liga","Sexo",
        "URL_Foto","URL_Perfil"
    ]
    columnas_inf = [
        "ID_Informe","ID_Jugador","Scout","Fecha_Partido","Fecha_Informe",
        "Equipos_Resultados","Formación","Observaciones","Línea",
        "Controles","Perfiles","Pase_corto","Pase_largo","Pase_filtrado",
        "1v1_defensivo","Recuperacion","Intercepciones","Duelos_aereos",
        "Regate","Velocidad","Duelos_ofensivos",
        "Resiliencia","Liderazgo","Inteligencia_tactica","Inteligencia_emocional",
        "Posicionamiento","Vision_de_juego","Movimientos_sin_pelota"
    ]
    columnas_short = [
        "ID_Jugador","Nombre","Edad","Altura","Club","Posición",
        "URL_Foto","URL_Perfil","Agregado_Por","Fecha_Agregado"
    ]

    df_players = cargar_datos_sheets("Jugadores", columnas_jug)
    df_reports = cargar_datos_sheets("Informes", columnas_inf)
    df_short = cargar_datos_sheets("Lista corta", columnas_short)

    for df in [df_players, df_reports, df_short]:
        if "ID_Jugador" in df.columns:
            df["ID_Jugador"] = df["ID_Jugador"].astype(str)

    return df_players, df_reports, df_short


# =========================================================
# SINCRONIZACIÓN DE MEMORIA LOCAL CON CACHE
# =========================================================
def sincronizar_memoria():
    """Mantiene la memoria (session_state) sincronizada con cache cada 60s."""
    if "last_sync" not in st.session_state:
        st.session_state["last_sync"] = time.time()

    if time.time() - st.session_state["last_sync"] > 60:
        st.session_state["df_players"], st.session_state["df_reports"], st.session_state["df_short"] = cargar_datos()
        st.session_state["last_sync"] = time.time()
        st.toast("♻️ Datos sincronizados automáticamente.", icon="🔁")

# =========================================================
# MENÚ PRINCIPAL + FILTRO POR ROL Y USUARIO (versión final optimizada)
# =========================================================
st.session_state["df_players"], st.session_state["df_reports"], st.session_state["df_short"] = cargar_datos()
df_players = st.session_state["df_players"]
df_reports = st.session_state["df_reports"]
df_short = st.session_state["df_short"]

# 🔄 Mantiene sincronía automática
sincronizar_memoria()

# Normalizamos texto (sin cambios)
if "Scout" in df_reports.columns:
    df_reports["Scout"] = df_reports["Scout"].astype(str).str.strip()

# --- Lógica de acceso ---
if CURRENT_ROLE == "admin":
    if CURRENT_USER in ["Mariano Cirone", "Dario Marra"]:
        pass  # sin filtro
    else:
        df_reports = df_reports[df_reports["Scout"] == CURRENT_USER]
elif CURRENT_ROLE == "scout":
    df_reports = df_reports[df_reports["Scout"] == CURRENT_USER]
elif CURRENT_ROLE == "viewer":
    st.info("👀 Estás en modo visualización: solo podés ver los datos.")

# --- Menú lateral principal ---
menu = st.sidebar.radio(
    "📋 Menú principal",
    ["Panel General", "Agenda", "Jugadores", "Ver informes", "Lista corta"]
)


# =========================================================
# BLOQUE 3 / 5 — Sección Jugadores (editable + eliminar para todos)
# =========================================================

if menu == "Jugadores":
    st.subheader("Gestión de jugadores e informes individuales")

    # --- OPCIONES PREDEFINIDAS ---
    opciones_pies = ["Derecho", "Izquierdo", "Ambidiestro"]

    opciones_posiciones = [
        "Arquero", "Lateral derecho", "Defensa central derecho", "Defensa central izquierdo",
        "Lateral izquierdo", "Mediocampista defensivo", "Mediocampista mixto",
        "Mediocampista ofensivo", "Extremo derecho", "Extremo izquierdo", "Delantero centro"
    ]

    opciones_ligas = [
        "Argentina - LPF", "Argentina - Primera Nacional", "Argentina - Federal A",
        "Brasil - Serie A (Brasileirão)", "Brasil - Serie B", "Chile - Primera División",
        "Uruguay - Primera División", "Uruguay - Segunda División Profesional",
        "Paraguay - División Profesional", "Colombia - Categoría Primera A",
        "Ecuador - LigaPro Serie A", "Perú - Liga 1", "Venezuela - Liga FUTVE",
        "México - Liga MX", "España - LaLiga", "España - LaLiga 2", "Italia - Serie A",
        "Italia - Serie B", "Inglaterra - Premier League", "Inglaterra - Championship",
        "Francia - Ligue 1", "Alemania - Bundesliga", "Portugal - Primeira Liga",
        "Países Bajos - Eredivisie", "Suiza - Super League", "Polonia - Liga Polaca", "Bélgica - Pro League",
        "Grecia - Super League", "Turquía - Süper Lig", "Arabia Saudita - Saudi Pro League",
        "Estados Unidos - MLS", "Otro / Sin especificar"
    ]

    opciones_paises = [
        "Argentina", "Brasil", "Chile", "Uruguay", "Paraguay", "Colombia", "México",
        "Ecuador", "Perú", "Venezuela", "España", "Italia", "Francia", "Inglaterra",
        "Alemania", "Portugal", "Estados Unidos", "Canadá", "Bolivia", "Honduras",
        "Costa Rica", "El Salvador", "Panamá", "República Dominicana", "Guatemala",
        "Haití", "Jamaica", "Otro"
    ]

    opciones_segunda_nacionalidad = opciones_paises.copy()

    opciones_caracteristicas = [
        "agresivo", "completo", "tiempista", "dinámico", "velocista", "goleador",
        "juego de espalda", "líder defensivo", "versátil", "posicional", "habilidoso",
        "táctico", "aguerrido", "resolutivo", "creativo", "preciso", "criterioso",
        "aplomado", "temperamental", "técnico", "conductor", "proyección"
    ]

    if not df_players.empty:
        opciones = {f"{row['Nombre']} - {row['Club']}": row["ID_Jugador"] for _, row in df_players.iterrows()}
    else:
        opciones = {}

    seleccion_jug = st.selectbox("🔍 Buscar jugador", [""] + list(opciones.keys()))

    # =========================================================
    # CREAR NUEVO JUGADOR
    # =========================================================
    if not seleccion_jug:
        st.markdown("#### ¿No encontrás al jugador?")
        with st.expander("➕ Agregar nuevo jugador", expanded=False):
            with st.form("nuevo_jugador_form", clear_on_submit=True):
                nuevo_nombre = st.text_input("Nombre completo")
                nueva_fecha = st.text_input("Fecha de nacimiento (dd/mm/aaaa)")
                nueva_altura = st.number_input("Altura (cm)", min_value=140, max_value=210, value=175)
                nuevo_pie = st.selectbox("Pie hábil", opciones_pies)
                nueva_posicion = st.selectbox("Posición principal", opciones_posiciones)
                nuevo_club = st.text_input("Club actual")
                nueva_liga = st.selectbox("Liga o país de competencia", opciones_ligas)
                nueva_nacionalidad = st.selectbox("Nacionalidad principal", opciones_paises)
                nueva_seg_nac = st.selectbox("Segunda nacionalidad (opcional)", [""] + opciones_segunda_nacionalidad)
                nueva_caracteristica = st.multiselect("Características del jugador", opciones_caracteristicas)
                nueva_url_foto = st.text_input("URL de foto (opcional)")
                nueva_url_perfil = st.text_input("URL de perfil externo (opcional)")
                instagram = st.text_input("Instagram (URL)")  # 🆕
                guardar_nuevo = st.form_submit_button("💾 Guardar jugador")

                if guardar_nuevo and nuevo_nombre:
                    try:
                        nuevo_id = generar_id_unico(df_players, "ID_Jugador")
                        nueva_caracteristica_str = ", ".join(nueva_caracteristica) if nueva_caracteristica else ""
                        fila = [
                            nuevo_id, nuevo_nombre, nueva_fecha, nueva_nacionalidad, nueva_seg_nac,
                            nueva_altura, nuevo_pie, nueva_posicion, nueva_caracteristica_str,
                            nuevo_club, nueva_liga, "", nueva_url_foto, nueva_url_perfil,
                            instagram  # 🆕
                        ]
                        ws = obtener_hoja("Jugadores")
                        ws.append_row(fila, value_input_option="USER_ENTERED")
                        st.cache_data.clear()
                        df_players = cargar_datos_sheets("Jugadores")
                        st.toast(f"✅ Jugador '{nuevo_nombre}' agregado correctamente.", icon="✅")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"⚠️ Error al agregar el jugador: {e}")

    # =========================================================
    # MOSTRAR JUGADOR SELECCIONADO
    # =========================================================
    if seleccion_jug:
        id_jugador = opciones[seleccion_jug]
        jugador = df_players[df_players["ID_Jugador"] == id_jugador].iloc[0]

        col1, col2, col3 = st.columns([1.2, 1.2, 1.6])

        # === FICHA ===
        with col1:
            st.markdown(f"### {jugador['Nombre']}")

            # 🆕 Instagram icono
            if pd.notna(jugador.get("Instagram")) and str(jugador["Instagram"]).startswith("http"):
                st.markdown(
                    f"""
                    <a href="{jugador['Instagram']}" target="_blank" title="Ver Instagram">
                        <img src="https://upload.wikimedia.org/wikipedia/commons/a/a5/Instagram_icon.png"
                             width="20" style="vertical-align:middle;">
                    </a>
                    """,
                    unsafe_allow_html=True
                )

            if pd.notna(jugador.get("URL_Foto")) and str(jugador["URL_Foto"]).startswith("http"):
                st.image(jugador["URL_Foto"], width=160)

            edad = calcular_edad(jugador.get("Fecha_Nac"))
            nac_principal = jugador.get("Nacionalidad", "-")
            nac_secundaria = jugador.get("Segunda_Nacionalidad", "")
            nacionalidades = nac_principal if not nac_secundaria else f"{nac_principal}, {nac_secundaria}"

            st.write(f"📅 Fecha de nacimiento: {jugador.get('Fecha_Nac', '')} ({edad} años)")
            st.write(f"🌍 Nacionalidad: {nacionalidades}")
            st.write(f"📏 Altura: {jugador.get('Altura', '-') } cm")
            st.write(f"👟 Pie hábil: {jugador.get('Pie_Hábil', '-')}")
            st.write(f"🎯 Posición: {jugador.get('Posición', '-')}")
            st.write(f"🏟️ Club actual: {jugador.get('Club', '-')} ({jugador.get('Liga', '-')})")

            if pd.notna(jugador.get("URL_Perfil")) and str(jugador["URL_Perfil"]).startswith("http"):
                st.markdown(f"[🌐 Perfil externo]({jugador['URL_Perfil']})", unsafe_allow_html=True)

        # =========================================================
        # EDITAR DATOS DEL JUGADOR
        # =========================================================
        with st.expander("✏️ Editar información del jugador", expanded=False):
            with st.form(f"editar_jugador_form_{jugador['ID_Jugador']}", clear_on_submit=False):
                e_nombre = st.text_input("Nombre completo", value=jugador.get("Nombre", ""))
                e_fecha = st.text_input("Fecha de nacimiento (dd/mm/aaaa)", value=jugador.get("Fecha_Nac", ""))
                e_altura = st.number_input("Altura (cm)", 140, 210, int(float(jugador.get("Altura", 175))) if str(jugador.get("Altura", "")).strip() else 175)
                e_pie = st.selectbox("Pie hábil", opciones_pies, index=opciones_pies.index(jugador["Pie_Hábil"]) if jugador["Pie_Hábil"] in opciones_pies else 0)
                e_pos = st.selectbox("Posición", opciones_posiciones, index=opciones_posiciones.index(jugador["Posición"]) if jugador["Posición"] in opciones_posiciones else 0)
                e_club = st.text_input("Club actual", value=jugador.get("Club", ""))
                e_liga = st.selectbox("Liga", opciones_ligas, index=opciones_ligas.index(jugador["Liga"]) if jugador["Liga"] in opciones_ligas else 0)
                e_nac = st.selectbox("Nacionalidad principal", opciones_paises, index=opciones_paises.index(jugador["Nacionalidad"]) if jugador["Nacionalidad"] in opciones_paises else 0)
                e_seg_opciones = [""] + opciones_segunda_nacionalidad
                e_seg = st.selectbox("Segunda nacionalidad (opcional)", e_seg_opciones, index=e_seg_opciones.index(jugador["Segunda_Nacionalidad"]) if jugador["Segunda_Nacionalidad"] in e_seg_opciones else 0)
                e_car = st.multiselect("Características del jugador", opciones_caracteristicas, default=[c.strip().lower() for c in str(jugador.get("Caracteristica", "")).split(",") if c.strip().lower() in [o.lower() for o in opciones_caracteristicas]])
                e_foto = st.text_input("URL de foto", value=str(jugador.get("URL_Foto", "")))
                e_link = st.text_input("URL perfil externo", value=str(jugador.get("URL_Perfil", "")))
                e_instagram = st.text_input("Instagram (URL)", value=str(jugador.get("Instagram","")))  # 🆕
                guardar_ed = st.form_submit_button("💾 Guardar cambios")

                if guardar_ed:
                    try:
                        ws = obtener_hoja("Jugadores")
                        data = ws.get_all_records()
                        df_actual = pd.DataFrame(data)
                        index_row = df_actual.index[df_actual["ID_Jugador"].astype(str) == str(id_jugador)]

                        if not index_row.empty:
                            row_number = index_row[0] + 2
                            e_car_str = ", ".join(e_car) if e_car else ""
                            valores = [
                                id_jugador, e_nombre, e_fecha, e_nac, e_seg, e_altura, e_pie,
                                e_pos, e_car_str, e_club, e_liga, "", e_foto, e_link,
                                e_instagram  # 🆕
                            ]
                            ws.update(f"A{row_number}:O{row_number}", [valores])  # 🆕
                            st.cache_data.clear()
                            df_players = cargar_datos_sheets("Jugadores")
                            st.toast("✅ Datos actualizados correctamente.", icon="✅")
                            st.experimental_rerun()
                        else:
                            st.warning("⚠️ No se encontró el jugador en la hoja.")
                    except Exception as e:
                        st.error(f"⚠️ Error al guardar: {e}")


# =========================================================
# BLOQUE 4 / 5 — Ver Informes (optimizado y con ficha completa)
# =========================================================

if menu == "Ver informes":
    st.subheader("📝 Informes cargados")

    # --- Unificación segura ---
    try:
        df_reports["ID_Jugador"] = df_reports["ID_Jugador"].astype(str)
        df_players["ID_Jugador"] = df_players["ID_Jugador"].astype(str)
        df_merged = df_reports.merge(df_players, on="ID_Jugador", how="left")
    except Exception as e:
        st.error(f"❌ Error al unir datos: {e}")
        st.stop()

    # =========================================================
    # FILTROS LATERALES
    # =========================================================
    st.sidebar.markdown("<h4 style='color:#00c6ff'>🔎 Filtros</h4>", unsafe_allow_html=True)
    filtro_scout = st.sidebar.multiselect("Scout", sorted(df_merged["Scout"].dropna().unique()), key="fil_scout")
    filtro_jugador = st.sidebar.multiselect("Jugador", sorted(df_merged["Nombre"].dropna().unique()), key="fil_jug")
    filtro_club = st.sidebar.multiselect("Club", sorted(df_merged["Club"].dropna().unique()), key="fil_club")
    filtro_linea = st.sidebar.multiselect("Línea", sorted(df_merged["Línea"].dropna().unique()), key="fil_lin")
    filtro_nac = st.sidebar.multiselect("Nacionalidad", sorted(df_merged["Nacionalidad"].dropna().unique()), key="fil_nac")

    df_filtrado = df_merged.copy()
    if filtro_scout:
        df_filtrado = df_filtrado[df_filtrado["Scout"].isin(filtro_scout)]
    if filtro_jugador:
        df_filtrado = df_filtrado[df_filtrado["Nombre"].isin(filtro_jugador)]
    if filtro_club:
        df_filtrado = df_filtrado[df_filtrado["Club"].isin(filtro_club)]
    if filtro_linea:
        df_filtrado = df_filtrado[df_filtrado["Línea"].isin(filtro_linea)]
    if filtro_nac:
        df_filtrado = df_filtrado[df_filtrado["Nacionalidad"].isin(filtro_nac)]

    # =========================================================
    # TABLA PRINCIPAL (AgGrid)
    # =========================================================
    if not df_filtrado.empty:
        st.markdown("### 📋 Informes disponibles")

        columnas = ["Fecha_Informe", "Nombre", "Club", "Línea", "Scout", "Equipos_Resultados", "Observaciones"]
        df_tabla = df_filtrado[[c for c in columnas if c in df_filtrado.columns]].copy()

        try:
            df_tabla["Fecha_dt"] = pd.to_datetime(df_tabla["Fecha_Informe"], format="%d/%m/%Y", errors="coerce")
            df_tabla = df_tabla.sort_values("Fecha_dt", ascending=False).drop(columns="Fecha_dt")
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
        # FICHA DEL JUGADOR
        # =========================================================
        selected_data = grid_response.get("selected_rows", [])
        if isinstance(selected_data, pd.DataFrame):
            selected_data = selected_data.to_dict("records")
        elif isinstance(selected_data, dict):
            selected_data = [selected_data]

        if selected_data:

            jugador_sel = selected_data[0]
            nombre_jug = jugador_sel.get("Nombre", "")
            jugador_data = df_players[df_players["Nombre"] == nombre_jug]

            if not jugador_data.empty:
                j = jugador_data.iloc[0]

                st.markdown("---")
                st.markdown(f"### 🧾 Ficha del jugador: **{j['Nombre']}**")

                col1, col2, col3 = st.columns([1, 1, 1])

                with col1:
                    st.markdown(f"**📍 Club:** {j.get('Club','-')}")
                    st.markdown(f"**🎯 Posición:** {j.get('Posición','-')}")
                    st.markdown(f"**📏 Altura:** {j.get('Altura','-')} cm")
                    edad_jugador = calcular_edad(j.get("Fecha_Nac"))
                    st.markdown(f"**📅 Edad:** {edad_jugador} años")

                with col2:
                    st.markdown(f"**👟 Pie hábil:** {j.get('Pie_Hábil','-')}")
                    st.markdown(f"**🌍 Nacionalidad:** {j.get('Nacionalidad','-')}")
                    st.markdown(f"**🏆 Liga:** {j.get('Liga','-')}")

                with col3:
                    st.markdown(f"**2ª Nacionalidad:** {j.get('Segunda_Nacionalidad','-')}")
                    st.markdown(f"**🧠 Característica:** {j.get('Caracteristica','-')}")

                    # 🆕 Instagram (ícono clickeable)
                    if pd.notna(j.get("Instagram")) and str(j["Instagram"]).startswith("http"):
                        st.markdown(
                            f"""
                            <a href="{j['Instagram']}" target="_blank" title="Ver Instagram">
                                <img src="https://upload.wikimedia.org/wikipedia/commons/a/a5/Instagram_icon.png"
                                     width="18" style="vertical-align:middle;margin-right:6px;">
                                Instagram
                            </a>
                            """,
                            unsafe_allow_html=True
                        )

                    if pd.notna(j.get("URL_Foto")) and str(j["URL_Foto"]).startswith("http"):
                        st.image(j["URL_Foto"], width=130)

                    if pd.notna(j.get("URL_Perfil")) and str(j["URL_Perfil"]).startswith("http"):
                        st.markdown(f"[🌐 Perfil externo]({j['URL_Perfil']})", unsafe_allow_html=True)

                # =========================================================
                # EXPORTAR PDF SIMPLE — TODOS LOS INFORMES DEL JUGADOR
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
                        pdf.cell(0, 8, f"Nacionalidad: {j.get('Nacionalidad','-')}", ln=True)
                        pdf.ln(5)

                        pdf.set_font("Arial", "B", 12)
                        pdf.cell(0, 8, "Informes:", ln=True)
                        pdf.set_font("Arial", "", 11)

                        informes_pdf = df_reports[df_reports["ID_Jugador"] == j["ID_Jugador"]]

                        for _, inf in informes_pdf.iterrows():
                            pdf.ln(3)
                            pdf.cell(0, 6, f"- Fecha: {inf['Fecha_Partido']}", ln=True)
                            pdf.cell(0, 6, f"  Partido: {inf['Equipos_Resultados']}", ln=True)
                            pdf.cell(0, 6, f"  Scout: {inf['Scout']} | Línea: {inf['Línea']}", ln=True)
                            pdf.multi_cell(0, 6, f"  Obs: {inf['Observaciones'][:300]}")

                        buffer = BytesIO()
                        pdf.output(buffer)
                        buffer.seek(0)

                        st.download_button(
                            label="📄 Descargar PDF simple",
                            data=buffer,
                            file_name=f"Informe_{j['Nombre']}.pdf",
                            mime="application/pdf"
                        )

                    except Exception as e:
                        st.error(f"⚠️ Error PDF simple: {e}")

                # =========================================================
                # EXPANDER — TODOS LOS INFORMES
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
                                "1ra (Fichar)", "2da (Seguir)", "3ra (Ver más adelante)",
                                "4ta (Descartar)", "Joven Promesa"
                            ]

                            nueva_linea = st.selectbox(
                                "Línea", opciones_linea,
                                index=opciones_linea.index(inf.Línea) if inf.Línea in opciones_linea else 2
                            )

                            nuevas_obs = st.text_area("Observaciones", inf.Observaciones, height=120)
                            guardar = st.form_submit_button("💾 Guardar cambios")

                            if guardar:
                                try:
                                    df_reports.loc[
                                        df_reports["ID_Informe"] == inf.ID_Informe,
                                        ["Scout", "Fecha_Partido","Equipos_Resultados","Línea","Observaciones"]
                                    ] = [
                                        nuevo_scout, nueva_fecha, nuevos_equipos, nueva_linea, nuevas_obs
                                    ]

                                    ws_inf = obtener_hoja("Informes")
                                    ws_inf.update(
                                        [df_reports.columns.values.tolist()] +
                                        df_reports.values.tolist()
                                    )

                                    st.toast("✓ Informe actualizado correctamente")
                                except Exception as e:
                                    st.error(f"⚠️ Error al actualizar el informe: {e}")

        else:
            st.info("📍 Seleccioná un registro para ver la ficha del jugador.")

# =========================================================
# BLOQUE 5 / 5 — Lista corta táctica (versión final con privacidad y gestor de eliminación)
# =========================================================

if menu == "Lista corta":
    st.subheader("Lista corta de jugadores")

    df_short = st.session_state.get("df_short", pd.DataFrame())
    df_players = st.session_state.get("df_players", pd.DataFrame())

    if df_short.empty:
        st.info("No hay jugadores cargados en la lista corta actualmente.")
        st.stop()

    # =========================================================
    # FILTRO DE PRIVACIDAD POR USUARIO
    # =========================================================
    if CURRENT_ROLE not in ["admin"]:
        df_short = df_short[df_short["Agregado_Por"] == CURRENT_USER]

    # Aseguramos columnas necesarias
    for col in ["Año", "Semestre"]:
        if col not in df_short.columns:
            df_short[col] = ""

    # =========================================================
    # FILTROS
    # =========================================================
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        filtro_scout = st.selectbox("Scout", [""] + sorted(df_short["Agregado_Por"].dropna().unique()))
    with col2:
        filtro_liga = st.selectbox("Liga", [""] + sorted(df_players["Liga"].dropna().unique()))
    with col3:
        filtro_nac = st.selectbox("Nacionalidad", [""] + sorted(df_players["Nacionalidad"].dropna().unique()))
    with col4:
        filtro_anio = st.selectbox("Año", [""] + sorted([x for x in df_short["Año"].dropna().unique() if x != "-"], reverse=True))
    with col5:
        filtro_sem = st.selectbox("Semestre", ["", "1º", "2º"])
    with col6:
        filtro_promesa = st.selectbox("Promesa", ["", "Sí", "No"])

    df_filtrado = df_short.copy()
    if filtro_scout:
        df_filtrado = df_filtrado[df_filtrado["Agregado_Por"] == filtro_scout]
    if filtro_liga:
        ids_liga = df_players[df_players["Liga"] == filtro_liga]["ID_Jugador"].astype(str).tolist()
        df_filtrado = df_filtrado[df_filtrado["ID_Jugador"].isin(ids_liga)]
    if filtro_nac:
        ids_nac = df_players[df_players["Nacionalidad"] == filtro_nac]["ID_Jugador"].astype(str).tolist()
        df_filtrado = df_filtrado[df_filtrado["ID_Jugador"].isin(ids_nac)]
    if filtro_anio:
        df_filtrado = df_filtrado[df_filtrado["Año"] == filtro_anio]
    if filtro_sem:
        df_filtrado = df_filtrado[df_filtrado["Semestre"] == filtro_sem]
    if filtro_promesa == "Sí":
        df_filtrado = df_filtrado[df_filtrado["Posición"].str.contains("Promesa", case=False, na=False)]
    elif filtro_promesa == "No":
        df_filtrado = df_filtrado[~df_filtrado["Posición"].str.contains("Promesa", case=False, na=False)]

    total_jugadores = len(df_filtrado)
    st.markdown(
        f"### Vista táctica (sistema 4-2-3-1) — <span style='color:#00c6ff;'>Total jugadores: {total_jugadores}</span>",
        unsafe_allow_html=True,
    )

    # =========================================================
    # CSS TARJETAS
    # =========================================================
    st.markdown("""
    <style>
    .player-card {
        display:flex;align-items:center;justify-content:flex-start;
        background:linear-gradient(90deg,#0e1117,#1e3c72);
        padding:0.6em 0.8em;border-radius:12px;color:white;
        font-family:Arial, sans-serif;box-shadow:0 0 6px rgba(0,0,0,0.4);
        width:230px;min-height:75px;margin:6px auto;transition:0.2s;
    }
    .player-card:hover {transform:scale(1.05);box-shadow:0 0 12px #00c6ff;}
    .player-photo {width:55px;height:55px;border-radius:50%;object-fit:cover;
        border:2px solid #00c6ff;margin-right:10px;}
    .player-info h5 {font-size:13px;margin:0;color:#00c6ff;font-weight:bold;}
    .player-info p {font-size:11.5px;margin:1px 0;color:#ccc;}
    .player-link a {color:#00c6ff;font-size:10.5px;text-decoration:none;}
    .player-link a:hover{text-decoration:underline;}
    .line-title {color:#00c6ff;font-weight:bold;font-size:16px;margin:10px 0 5px;text-align:center;}
    </style>
    """, unsafe_allow_html=True)

    # =========================================================
    # SISTEMA 4-2-3-1
    # =========================================================
    sistema = {
        "Arqueros": ["Arquero"],
        "Defensas": [
            "Lateral derecho", "Defensa central derecho",
            "Defensa central izquierdo", "Lateral izquierdo"
        ],
        "Mediocampistas defensivos": ["Mediocampista mixto", "Mediocampista defensivo"],
        "Mediocampistas ofensivos": [
            "Extremo derecho", "Mediocampista ofensivo", "Extremo izquierdo"
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

            # ---- ARQUEROS / DELANTEROS (5x5 filas) ----
            if linea in ["Arqueros", "Delanteros"]:
                jugadores_pos = jugadores_linea.copy()
                if jugadores_pos.empty:
                    st.markdown("<p style='color:gray;font-size:11px;text-align:center;'>— Vacante —</p>", unsafe_allow_html=True)
                else:
                    jugadores_lista = list(jugadores_pos.iterrows())
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
                                edad, altura = row.get("Edad","-"), row.get("Altura","-")
                                club = row.get("Club","-")
                                url_perfil = str(row.get("URL_Perfil",""))
                                link_html = (
                                    f"<div class='player-link'><a href='{url_perfil}' target='_blank'>Ver perfil</a></div>"
                                    if url_perfil.startswith("http") else ""
                                )
                                st.markdown(f"""
                                    <div class="player-card">
                                        <img src="{url_foto}" class="player-photo"/>
                                        <div class="player-info">
                                            <h5>{nombre} {apellido}</h5>
                                            <p>{club}</p>
                                            <p>Edad: {edad} | Altura: {altura} cm</p>
                                            {link_html}
                                        </div>
                                    </div>
                                """, unsafe_allow_html=True)

            # ---- RESTO (Defensas, Mediocampistas) ----
            else:
                cols = st.columns(len(posiciones))
                for i, pos in enumerate(posiciones):
                    jugadores_pos = jugadores_linea[jugadores_linea["Posición"] == pos]
                    with cols[i]:
                        st.markdown(f"<div class='line-title'>{pos}</div>", unsafe_allow_html=True)
                        if jugadores_pos.empty:
                            st.markdown("<p style='color:gray;font-size:11px;text-align:center;'>— Vacante —</p>", unsafe_allow_html=True)
                        else:
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
                                        edad, altura = row.get("Edad","-"), row.get("Altura","-")
                                        club = row.get("Club","-")
                                        url_perfil = str(row.get("URL_Perfil",""))
                                        link_html = (
                                            f"<div class='player-link'><a href='{url_perfil}' target='_blank'>Ver perfil</a></div>"
                                            if url_perfil.startswith("http") else ""
                                        )
                                        st.markdown(f"""
                                            <div class="player-card">
                                                <img src="{url_foto}" class="player-photo"/>
                                                <div class="player-info">
                                                    <h5>{nombre} {apellido}</h5>
                                                    <p>{club}</p>
                                                    <p>Edad: {edad} | Altura: {altura} cm</p>
                                                    {link_html}
                                                </div>
                                            </div>
                                        """, unsafe_allow_html=True)

    # =========================================================
    # GESTOR DE LISTA CORTA — Eliminación limpia con buscador
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
            df_busqueda[["Nombre","Posición","Club","Agregado_Por"]],
            use_container_width=True, hide_index=True
        )
        jugador_sel = st.selectbox("Seleccionar jugador a eliminar", [""] + sorted(df_busqueda["Nombre"].unique()))
        if jugador_sel:
            jugador_row = df_busqueda[df_busqueda["Nombre"] == jugador_sel].iloc[0]
            st.warning(f"⚠️ Vas a eliminar a **{jugador_sel}** de la lista corta.")
            confirmar = st.checkbox("Confirmar eliminación")
            if st.button("🗑️ Eliminar jugador", type="primary", disabled=not confirmar):
                try:
                    ws_short = obtener_hoja("Lista corta")
                    data_short = ws_short.get_all_records()
                    df_short_local = pd.DataFrame(data_short)
                    fila = df_short_local.index[
                        df_short_local["ID_Jugador"].astype(str) == str(jugador_row["ID_Jugador"])
                    ]
                    if not fila.empty:
                        df_short_local = df_short_local.drop(fila[0])
                        ws_short.clear()
                        ws_short.append_row(list(df_short_local.columns))
                        if not df_short_local.empty:
                            ws_short.update(
                                [df_short_local.columns.values.tolist()] + df_short_local.values.tolist()
                            )
                        st.toast(f"🗑️ Jugador {jugador_sel} eliminado correctamente.", icon="🗑️")
                        st.cache_data.clear()
                        st.experimental_rerun()
                    else:
                        st.warning("⚠️ No se encontró el jugador en la hoja.")
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
# 📊 PANEL GENERAL — SCOUTINGAPP PRO
# =========================================================

from datetime import datetime, timedelta

st.markdown("""
<style>
/* ================= PANEL GENERAL WRAPPER ================= */
.panel-wrapper {
    max-width:1600px;
    margin:auto;
}

/* ================= TITULO ================= */
.panel-title-main {
    text-align:center;
    color:#00c6ff;
    font-size:26px;
    font-weight:bold;
    margin-bottom:25px;
}

/* ================= KPI ================= */
.kpi-container {
    display:flex;
    justify-content:space-between;
    gap:22px;
    margin-bottom:35px;
}
.kpi-card {
    background:linear-gradient(90deg,#0e1117,#1e3c72);
    border-radius:14px;
    padding:18px 22px;
    flex:1;
    min-width:220px;
    text-align:center;
    box-shadow:0 0 12px rgba(0,0,0,0.45);
}
.kpi-title {
    color:#00c6ff;
    font-size:14px;
    font-weight:bold;
    margin-bottom:6px;
}
.kpi-value {
    font-size:30px;
    font-weight:bold;
}

/* ================= RANKING ================= */
.panel-title {
    color:#00c6ff;
    font-weight:bold;
    font-size:16px;
    margin:12px 0 6px 0;
    text-align:center;
}
.rank-card {
    background:linear-gradient(90deg,#0e1117,#1e3c72);
    border-radius:10px;
    padding:8px 10px;
    margin-bottom:6px;
    display:flex;
    justify-content:space-between;
    align-items:center;
    box-shadow:0 0 6px rgba(0,0,0,0.45);
}
.rank-left {
    display:flex;
    gap:8px;
    align-items:center;
}
.rank-num {
    color:#ffd700;
    font-weight:bold;
    width:22px;
    font-size:13px;
}
.rank-name {
    font-size:12.5px;
    font-weight:bold;
}
.rank-score {
    color:#00c6ff;
    font-weight:bold;
    font-size:12.5px;
}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='panel-wrapper'>", unsafe_allow_html=True)
st.markdown("<div class='panel-title-main'>📊 Panel General — ScoutingApp PRO</div>", unsafe_allow_html=True)

# =========================================================
# FECHAS
# =========================================================
def parse_fecha(f):
    try:
        return datetime.strptime(str(f), "%d/%m/%Y")
    except:
        return None

df_reports["Fecha_Informe_dt"] = df_reports["Fecha_Informe"].apply(parse_fecha)

# =========================================================
# EDAD
# =========================================================
def calcular_edad(f):
    try:
        d = datetime.strptime(str(f), "%d/%m/%Y")
        return int((datetime.today() - d).days / 365.25)
    except:
        return None

df_players["Edad"] = df_players["Fecha_Nac"].apply(calcular_edad)

# =========================================================
# KPIs
# =========================================================
hoy = datetime.today()
hace_30 = hoy - timedelta(days=30)
inicio_sem = datetime(hoy.year, 1, 1) if hoy.month <= 6 else datetime(hoy.year, 7, 1)

jugadores_eval = df_players["ID_Jugador"].nunique()
informes_total = len(df_reports)
scouts_activos = df_reports["Scout"].nunique()
jugadores_sem = df_reports[df_reports["Fecha_Informe_dt"] >= inicio_sem]["ID_Jugador"].nunique()
informes_30 = len(df_reports[df_reports["Fecha_Informe_dt"] >= hace_30])

st.markdown(f"""
<div class="kpi-container">
    <div class="kpi-card"><div class="kpi-title">Jugadores evaluados</div><div class="kpi-value">{jugadores_eval}</div></div>
    <div class="kpi-card"><div class="kpi-title">Informes cargados</div><div class="kpi-value">{informes_total}</div></div>
    <div class="kpi-card"><div class="kpi-title">Scouts activos</div><div class="kpi-value">{scouts_activos}</div></div>
    <div class="kpi-card"><div class="kpi-title">Jugadores este semestre</div><div class="kpi-value">{jugadores_sem}</div></div>
    <div class="kpi-card"><div class="kpi-title">Informes últimos 30 días</div><div class="kpi-value">{informes_30}</div></div>
</div>
""", unsafe_allow_html=True)

# =========================================================
# MÉTRICAS Y SCORE
# =========================================================
metricas = [
    "Controles","Perfiles","Pase_corto","Pase_largo","Pase_filtrado",
    "1v1_defensivo","Recuperacion","Intercepciones","Duelos_aereos",
    "Regate","Velocidad","Duelos_ofensivos",
    "Resiliencia","Liderazgo","Inteligencia_tactica","Inteligencia_emocional",
    "Posicionamiento","Vision_de_juego","Movimientos_sin_pelota"
]

df_reports["Score_Total"] = df_reports[metricas].mean(axis=1)

df_scores = (
    df_reports
    .groupby("ID_Jugador")[["Score_Total"]]
    .mean()
    .reset_index()
    .merge(df_players, on="ID_Jugador")
    .sort_values("Score_Total", ascending=False)
)

# =========================================================
# FUNCIÓN RENDER
# =========================================================
def render_top(df, titulo):
    st.markdown(f"<div class='panel-title'>{titulo}</div>", unsafe_allow_html=True)
    for i,row in enumerate(df.head(10).itertuples(),1):
        st.markdown(f"""
        <div class='rank-card'>
            <div class='rank-left'>
                <div class='rank-num'>#{i}</div>
                <div class='rank-name'>{row.Nombre}</div>
            </div>
            <div class='rank-score'>{round(row.Score_Total,2)}</div>
        </div>
        """, unsafe_allow_html=True)

# =========================================================
# POSICIONES (4 COLUMNAS)
# =========================================================
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
for i,(pos,tit) in enumerate(posiciones):
    with cols[i % 4]:
        render_top(df_scores[df_scores["Posición"]==pos], tit)

# =========================================================
# EDADES + CONSENSO
# =========================================================
st.markdown("---")
cols2 = st.columns(4)

with cols2[0]:
    consenso = (
        df_reports.groupby(["ID_Jugador","Línea"])
        .size().reset_index(name="n")
        .merge(df_reports.groupby("ID_Jugador").size().reset_index(name="tot"), on="ID_Jugador")
    )
    consenso["Score_Total"] = consenso["n"]/consenso["tot"]*100
    df_c = consenso.sort_values("Score_Total",ascending=False).merge(df_players,on="ID_Jugador")
    render_top(df_c, "🤝 Consenso scouts (%)")

with cols2[1]:
    render_top(df_scores[df_scores["Edad"]<20], "🟢 Top Sub 20")
with cols2[2]:
    render_top(df_scores[(df_scores["Edad"]>=20)&(df_scores["Edad"]<=28)], "🔵 Top 20–28")
with cols2[3]:
    render_top(df_scores[df_scores["Edad"]>28], "🟣 Top +28")

st.markdown("</div>", unsafe_allow_html=True)

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




