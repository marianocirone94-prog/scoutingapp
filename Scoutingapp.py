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
from datetime import date, datetime
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
# BLOQUE 2 / 5 — Funciones base + carga de datos + menú
# =========================================================

# =========================================================
# FUNCIONES AUXILIARES Y DE CÁLCULO (versión estable con refresco automático)
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
    """Calcula promedios reales (0-5) del jugador, corrigiendo decimales y tipos."""
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
                    .astype(float)
                )
                prom = valores.mean()
                if prom > 5:
                    prom = prom / 10
                promedios[col] = round(prom, 2)
            except:
                promedios[col] = None
    return promedios


def calcular_promedios_posicion(df_reports, df_players, posicion):
    """Promedio global de la posición, con corrección de decimales."""
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
                    .astype(float)
                )
                prom = valores.mean()
                if prom > 5:
                    prom = prom / 10
                promedios[col] = round(prom, 2)
            except:
                promedios[col] = None
    return promedios


def radar_chart(prom_jugador, prom_posicion):
    """Radar comparativo jugador vs promedio de posición."""
    categorias = list(prom_jugador.keys())
    valores_jug = [prom_jugador.get(c, 0) for c in categorias]
    valores_pos = [prom_posicion.get(c, 0) for c in categorias] if prom_posicion else [0]*len(categorias)
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
    ax.legend(loc="upper right", bbox_to_anchor=(1.2, 1.1), facecolor="#0e1117", labelcolor="white")
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
# REFRESCO AUTOMÁTICO DE DATAFRAMES (nuevo)
# =========================================================
def actualizar_dataframe(nombre_hoja, df_local):
    """Recarga solo la hoja indicada sin limpiar caché ni reiniciar la app."""
    try:
        ws = obtener_hoja(nombre_hoja)
        data = ws.get_all_records()
        if not data:
            return df_local
        df_nuevo = pd.DataFrame(data)
        if nombre_hoja == "Jugadores":
            global df_players
            df_players = df_nuevo
        elif nombre_hoja == "Informes":
            global df_reports
            df_reports = df_nuevo
        elif nombre_hoja == "Lista corta":
            global df_short
            df_short = df_nuevo
        return df_nuevo
    except Exception as e:
        st.warning(f"⚠️ No se pudo refrescar la hoja '{nombre_hoja}': {e}")
        return df_local


# =========================================================
# CARGA DE DATOS DESDE GOOGLE SHEETS
# =========================================================

@st.cache_data(ttl=300)
def cargar_datos():
    """Carga los tres datasets principales desde Google Sheets."""
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
# MENÚ PRINCIPAL + FILTRO POR ROL Y USUARIO (versión final)
# =========================================================
df_players, df_reports, df_short = cargar_datos()

# Normalizamos texto
if "Scout" in df_reports.columns:
    df_reports["Scout"] = df_reports["Scout"].astype(str).str.strip()

# --- Lógica de acceso ---
if CURRENT_ROLE == "admin":
    # ✅ Mariano y Dario ven todos los informes
    if CURRENT_USER in ["Mariano Cirone", "Dario Marra"]:
        pass  # No filtramos nada
    else:
        # Otros admins (si existieran) solo ven los suyos
        df_reports = df_reports[df_reports["Scout"] == CURRENT_USER]

elif CURRENT_ROLE == "scout":
    # Cada scout solo ve sus propios informes
    df_reports = df_reports[df_reports["Scout"] == CURRENT_USER]

elif CURRENT_ROLE == "viewer":
    # Solo visualizan, sin edición
    st.info("👀 Estás en modo visualización: solo podés ver los datos.")

# --- Menú lateral principal ---
menu = st.sidebar.radio(
    "📋 Menú principal",
    ["Jugadores", "Ver informes", "Lista corta"]
)

# =========================================================
# BLOQUE 3 / 5 — Sección Jugadores (versión final completa y estable)
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
        "Ecuador - LigaPro Serie A", "Perú - Liga 1", "Venezuela - Liga FUTVE", "México - Liga MX",
        "España - LaLiga", "España - LaLiga 2", "Italia - Serie A", "Italia - Serie B",
        "Inglaterra - Premier League", "Inglaterra - Championship", "Francia - Ligue 1",
        "Alemania - Bundesliga", "Portugal - Primeira Liga", "Países Bajos - Eredivisie",
        "Suiza - Super League", "Bélgica - Pro League", "Grecia - Super League",
        "Turquía - Süper Lig", "Arabia Saudita - Saudi Pro League", "Estados Unidos - MLS",
        "Otro / Sin especificar"
    ]
    opciones_paises = [
        "Argentina", "Brasil", "Chile", "Uruguay", "Paraguay", "Colombia", "México",
        "Ecuador", "Perú", "Venezuela", "España", "Italia", "Francia", "Inglaterra",
        "Alemania", "Portugal", "Otro"
    ]

    # --- BUSCADOR DE JUGADORES ---
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
                nueva_seg_nac = st.text_input("Segunda nacionalidad (opcional)")
                nueva_caracteristica = st.text_input("Característica distintiva (opcional)")
                nueva_url_foto = st.text_input("URL de foto (opcional)")
                nueva_url_perfil = st.text_input("URL de perfil externo (opcional)")
                guardar_nuevo = st.form_submit_button("💾 Guardar jugador")

                if guardar_nuevo and nuevo_nombre:
                    try:
                        nuevo_id = generar_id_unico(df_players, "ID_Jugador")
                        fila = [
                            nuevo_id, nuevo_nombre, nueva_fecha, nueva_nacionalidad, nueva_seg_nac,
                            nueva_altura, nuevo_pie, nueva_posicion, nueva_caracteristica,
                            nuevo_club, nueva_liga, "", nueva_url_foto, nueva_url_perfil
                        ]
                        ws = obtener_hoja("Jugadores")
                        ws.append_row(fila, value_input_option="USER_ENTERED")
                        st.success(f"✅ Jugador '{nuevo_nombre}' agregado correctamente.")
                        st.cache_data.clear()
                        st.rerun()
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
            if pd.notna(jugador.get("URL_Foto")) and str(jugador["URL_Foto"]).startswith("http"):
                st.image(jugador["URL_Foto"], width=160)
            edad = calcular_edad(jugador.get("Fecha_Nac"))
            st.write(f"📅 {jugador.get('Fecha_Nac', '')} ({edad} años)")
            st.write(f"🌍 {jugador.get('Nacionalidad', '-')}")
            if jugador.get("Segunda_Nacionalidad"):
                st.write(f"🪪 {jugador['Segunda_Nacionalidad']}")
            st.write(f"📏 {jugador.get('Altura', '-') } cm")
            st.write(f"👟 {jugador.get('Pie_Hábil', '-')}")
            st.write(f"🎯 {jugador.get('Posición', '-')}")
            st.write(f"🏟️ {jugador.get('Club', '-')} ({jugador.get('Liga', '-')})")
            if pd.notna(jugador.get("URL_Perfil")) and str(jugador["URL_Perfil"]).startswith("http"):
                st.markdown(f"[🌐 Perfil externo]({jugador['URL_Perfil']})", unsafe_allow_html=True)

        # === COMPARATIVA CENTRAL ===
        with col2:
            st.markdown("### 🔍 Comparativa por grupos")
            prom_jugador = calcular_promedios_jugador(df_reports, id_jugador)
            prom_posicion = calcular_promedios_posicion(df_reports, df_players, jugador["Posición"])
            if prom_jugador and prom_posicion:
                grupos = {
                    "Habilidades técnicas": ["Controles", "Perfiles", "Pase_corto", "Pase_largo", "Pase_filtrado"],
                    "Aspectos defensivos": ["1v1_defensivo", "Recuperacion", "Intercepciones", "Duelos_aereos"],
                    "Aspectos ofensivos": ["Regate", "Velocidad", "Duelos_ofensivos"],
                    "Aspectos mentales / tácticos": [
                        "Resiliencia", "Liderazgo", "Inteligencia_tactica", "Inteligencia_emocional",
                        "Posicionamiento", "Vision_de_juego", "Movimientos_sin_pelota"
                    ]
                }
                for grupo, atributos in grupos.items():
                    val_j = [prom_jugador.get(a, 0) for a in atributos]
                    val_p = [prom_posicion.get(a, 0) for a in atributos]
                    if val_j and val_p:
                        diff = np.mean(val_j) - np.mean(val_p)
                        color = "#4CAF50" if diff > 0.2 else "#D16C6C" if diff < -0.2 else "#B8B78A"
                        emoji = "⬆️" if diff > 0.2 else "⬇️" if diff < -0.2 else "➡️"
                        st.markdown(f"""
                        <div style='background: linear-gradient(135deg,{color},#1e3c72);
                            border-radius:10px;padding:10px;margin-bottom:6px;text-align:center;color:white;font-weight:600'>
                            <h5 style='margin:0;font-size:15px;'>{grupo}</h5>
                            <p style='margin:5px 0;font-size:20px;'>{emoji} {np.mean(val_j):.2f}</p>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("ℹ️ Aún no hay informes cargados.")

        # === RADAR ===
        with col3:
            if prom_jugador:
                st.markdown("### 📊 Radar comparativo")
                radar_chart(prom_jugador, prom_posicion)
            else:
                st.info("📉 No hay suficientes informes para generar el radar.")

        # === EDITAR JUGADOR ===
        if CURRENT_ROLE in ["admin", "scout"]:
            st.markdown("---")
            if "editar_jugador" not in st.session_state:
                st.session_state.editar_jugador = False
            if st.button("✏️ Editar jugador"):
                st.session_state.editar_jugador = not st.session_state.editar_jugador
            if st.session_state.editar_jugador:
                st.subheader("✏️ Editar información del jugador")
                with st.form(f"editar_jugador_form_{jugador['ID_Jugador']}", clear_on_submit=False):
                    e_nombre = st.text_input("Nombre completo", value=jugador.get("Nombre", ""))
                    e_fecha = st.text_input("Fecha de nacimiento (dd/mm/aaaa)", value=jugador.get("Fecha_Nac", ""))
                    e_altura = st.number_input("Altura (cm)", 140, 210,
                        int(float(jugador.get("Altura", 175))) if str(jugador.get("Altura", "")).strip() else 175)
                    e_pie = st.selectbox("Pie hábil", opciones_pies,
                        index=opciones_pies.index(jugador["Pie_Hábil"]) if jugador["Pie_Hábil"] in opciones_pies else 0)
                    e_pos = st.selectbox("Posición", opciones_posiciones,
                        index=opciones_posiciones.index(jugador["Posición"]) if jugador["Posición"] in opciones_posiciones else 0)
                    e_club = st.text_input("Club actual", value=jugador.get("Club", ""))
                    e_liga = st.selectbox("Liga", opciones_ligas,
                        index=opciones_ligas.index(jugador["Liga"]) if jugador["Liga"] in opciones_ligas else 0)
                    e_nac = st.selectbox("Nacionalidad", opciones_paises,
                        index=opciones_paises.index(jugador["Nacionalidad"]) if jugador["Nacionalidad"] in opciones_paises else 0)
                    e_seg = st.text_input("Segunda nacionalidad", value=jugador.get("Segunda_Nacionalidad", ""))
                    e_car = st.text_input("Característica distintiva", value=jugador.get("Caracteristica", ""))
                    e_foto = st.text_input("URL de foto", value=str(jugador.get("URL_Foto", "")))
                    e_link = st.text_input("URL perfil externo", value=str(jugador.get("URL_Perfil", "")))
                    guardar_ed = st.form_submit_button("💾 Guardar cambios")
                    if guardar_ed:
                        try:
                            df_players.loc[df_players["ID_Jugador"] == id_jugador, [
                                "Nombre","Fecha_Nac","Altura","Pie_Hábil","Posición",
                                "Club","Liga","Nacionalidad","Segunda_Nacionalidad",
                                "Caracteristica","URL_Foto","URL_Perfil"
                            ]] = [
                                e_nombre,e_fecha,e_altura,e_pie,e_pos,
                                e_club,e_liga,e_nac,e_seg,e_car,e_foto,e_link
                            ]
                            ws = obtener_hoja("Jugadores")
                            ws.update([df_players.columns.values.tolist()] + df_players.values.tolist())
                            jugador.update({
                                "Nombre": e_nombre,"Fecha_Nac": e_fecha,"Altura": e_altura,
                                "Pie_Hábil": e_pie,"Posición": e_pos,"Club": e_club,"Liga": e_liga,
                                "Nacionalidad": e_nac,"Segunda_Nacionalidad": e_seg,"Caracteristica": e_car,
                                "URL_Foto": e_foto,"URL_Perfil": e_link
                            })
                            st.success("✅ Cambios guardados correctamente.")
                            st.toast("Cambios sincronizados ☁️", icon="✅")
                            st.session_state.editar_jugador = False
                            st.experimental_rerun()
                        except Exception as e:
                            st.error(f"⚠️ Error al guardar: {e}")


        # =========================================================
        # AGREGAR A LISTA CORTA
        # =========================================================
        if CURRENT_ROLE in ["admin", "scout"]:
            st.markdown("---")
            if st.button("⭐ Agregar a lista corta"):
                try:
                    edad = calcular_edad(jugador["Fecha_Nac"])
                    fila = [
                        jugador["ID_Jugador"], jugador["Nombre"], edad, jugador["Altura"],
                        jugador["Club"], jugador["Posición"], jugador["URL_Foto"],
                        jugador["URL_Perfil"], CURRENT_USER, date.today().strftime("%d/%m/%Y")
                    ]
                    ws_short = obtener_hoja("Lista corta")
                    ws_short.append_row(fila, value_input_option="USER_ENTERED")
                    st.toast(f"⭐ {jugador['Nombre']} agregado a la lista corta.", icon="⭐")
                except Exception as e:
                    st.error(f"⚠️ Error al agregar a la lista corta: {e}")

        # =========================================================
        # ELIMINAR JUGADOR
        # =========================================================
        if CURRENT_ROLE in ["admin", "scout"]:
            st.markdown("---")
            eliminar_confirm = st.checkbox("Confirmar eliminación del jugador")
            if st.button("🗑️ Eliminar jugador permanentemente"):
                if eliminar_confirm:
                    try:
                        ws_jug = obtener_hoja("Jugadores")
                        data_jug = ws_jug.get_all_records()
                        df_jug_actual = pd.DataFrame(data_jug)
                        df_jug_actual = df_jug_actual[df_jug_actual["ID_Jugador"].astype(str) != str(id_jugador)]
                        ws_jug.clear()
                        ws_jug.append_row(list(df_jug_actual.columns))
                        if not df_jug_actual.empty:
                            ws_jug.update([df_jug_actual.columns.values.tolist()] + df_jug_actual.values.tolist())

                        ws_short = obtener_hoja("Lista corta")
                        data_short = ws_short.get_all_records()
                        df_short_actual = pd.DataFrame(data_short)
                        df_short_actual = df_short_actual[df_short_actual["ID_Jugador"].astype(str) != str(id_jugador)]
                        ws_short.clear()
                        ws_short.append_row(list(df_short_actual.columns))
                        if not df_short_actual.empty:
                            ws_short.update([df_short_actual.columns.values.tolist()] + df_short_actual.values.tolist())

                        st.toast(f"🗑️ Jugador '{jugador['Nombre']}' eliminado correctamente.", icon="🗑️")
                        st.cache_data.clear()
                        df_players = cargar_datos_sheets("Jugadores")
                        df_short = cargar_datos_sheets("Lista corta")

                    except Exception as e:
                        st.error(f"⚠️ Error al eliminar el jugador: {e}")
                else:
                    st.warning("Debes marcar la casilla antes de eliminar.")



# =========================================================
# BLOQUE 4 / 5 — Ver Informes (única tabla + ficha clickeable)
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
    # FILTROS LATERALES (con claves únicas)
    # =========================================================
    st.sidebar.markdown("<h4 style='color:#00c6ff'>🔎 Filtros</h4>", unsafe_allow_html=True)
    filtro_scout = st.sidebar.multiselect("Scout", sorted(df_merged["Scout"].dropna().unique()), key="fil_scout")
    filtro_jugador = st.sidebar.multiselect("Jugador", sorted(df_merged["Nombre"].dropna().unique()), key="fil_jug")
    filtro_club = st.sidebar.multiselect("Club", sorted(df_merged["Club"].dropna().unique()), key="fil_club")
    filtro_linea = st.sidebar.multiselect("Línea", sorted(df_merged["Línea"].dropna().unique()), key="fil_lin")
    filtro_nac = st.sidebar.multiselect("Nacionalidad", sorted(df_merged["Nacionalidad"].dropna().unique()), key="fil_nac")

    df_filtrado = df_merged.copy()
    if filtro_scout: df_filtrado = df_filtrado[df_filtrado["Scout"].isin(filtro_scout)]
    if filtro_jugador: df_filtrado = df_filtrado[df_filtrado["Nombre"].isin(filtro_jugador)]
    if filtro_club: df_filtrado = df_filtrado[df_filtrado["Club"].isin(filtro_club)]
    if filtro_linea: df_filtrado = df_filtrado[df_filtrado["Línea"].isin(filtro_linea)]
    if filtro_nac: df_filtrado = df_filtrado[df_filtrado["Nacionalidad"].isin(filtro_nac)]

    # =========================================================
    # TABLA PRINCIPAL (única)
    # =========================================================
    if not df_filtrado.empty:
        st.markdown("### 📋 Informes disponibles")

        columnas = ["Fecha_Informe", "Nombre", "Club", "Línea", "Scout", "Equipos_Resultados", "Observaciones"]
        df_tabla = df_filtrado[[c for c in columnas if c in df_filtrado.columns]].copy()

        # Ordenar por fecha si es posible
        try:
            df_tabla["Fecha_dt"] = pd.to_datetime(df_tabla["Fecha_Informe"], format="%d/%m/%Y", errors="coerce")
            df_tabla = df_tabla.sort_values("Fecha_dt", ascending=False).drop(columns="Fecha_dt")
        except Exception:
            pass

        # Configuración visual AgGrid
        gb = GridOptionsBuilder.from_dataframe(df_tabla)
        gb.configure_selection("single", use_checkbox=False)
        gb.configure_pagination(enabled=True, paginationAutoPageSize=True)
        gb.configure_grid_options(domLayout="normal")

        widths = {
            "Fecha_Informe": 100, "Nombre": 150, "Club": 130, "Línea": 120,
            "Scout": 120, "Equipos_Resultados": 150, "Observaciones": 420
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
                ".ag-header": {"background-color": "#1e3c72", "color": "white", "font-weight": "bold", "font-size": "13px"},
                ".ag-row-even": {"background-color": "#2a5298 !important", "color": "white !important"},
                ".ag-row-odd": {"background-color": "#3b6bbf !important", "color": "white !important"},
                ".ag-cell": {"white-space": "normal !important", "line-height": "1.25", "padding": "5px", "font-size": "12.5px"},
            },
        )

        # =========================================================
        # FICHA ARRIBA (clic funcional)
        # =========================================================
        selected_data = grid_response.get("selected_rows", [])
        if isinstance(selected_data, pd.DataFrame):
            selected_data = selected_data.to_dict("records")
        elif isinstance(selected_data, dict):
            selected_data = [selected_data]

        if len(selected_data) > 0:  # ✅ evita ValueError
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
                with col2:
                    st.markdown(f"**👟 Pie hábil:** {j.get('Pie_Hábil','-')}")
                    st.markdown(f"**🌍 Nacionalidad:** {j.get('Nacionalidad','-')}")
                    st.markdown(f"**🏆 Liga:** {j.get('Liga','-')}")
                with col3:
                    st.markdown(f"**2ª Nacionalidad:** {j.get('Segunda_Nacionalidad','-')}")
                    st.markdown(f"**🧠 Característica:** {j.get('Caracteristica','-')}")
                    if pd.notna(j.get("URL_Foto")) and str(j["URL_Foto"]).startswith("http"):
                        st.image(j["URL_Foto"], width=130)

                # =========================================================
                # INFORMES ASOCIADOS + EDICIÓN + PDF
                # =========================================================
                informes_sel = df_reports[df_reports["ID_Jugador"] == j["ID_Jugador"]]
                if not informes_sel.empty:
                    st.markdown(f"### 📄 Informes de {j['Nombre']}")

                    if st.button("📥 Exportar informes en PDF", key=f"pdf_{j['ID_Jugador']}"):
                        try:
                            pdf = FPDF(orientation="P", unit="mm", format="A4")
                            pdf.add_page()
                            pdf.set_font("Arial", "B", 16)
                            pdf.cell(0, 10, f"Informes de {j['Nombre']}", ln=True, align="C")
                            pdf.ln(5)
                            pdf.set_font("Arial", "", 12)
                            pdf.cell(0, 8, f"Club: {j.get('Club','')}", ln=True)
                            pdf.cell(0, 8, f"Posición: {j.get('Posición','')}", ln=True)
                            pdf.ln(8)
                            for _, inf in informes_sel.iterrows():
                                pdf.set_font("Arial", "B", 12)
                                pdf.cell(0, 8, f"{inf.get('Fecha_Partido','')} | Scout: {inf.get('Scout','')} | Línea: {inf.get('Línea','')}", ln=True)
                                pdf.set_font("Arial", "I", 10)
                                pdf.cell(0, 6, f"{inf.get('Equipos_Resultados','')}", ln=True)
                                pdf.set_font("Arial", "", 10)
                                pdf.multi_cell(0, 6, f"{inf.get('Observaciones','') or '-'}")
                                pdf.ln(4)
                            buffer = BytesIO()
                            pdf.output(buffer)
                            buffer.seek(0)
                            st.download_button(
                                label="📄 Descargar PDF",
                                data=buffer,
                                file_name=f"Informes_{j['Nombre']}.pdf",
                                mime="application/pdf"
                            )
                        except Exception as e:
                            st.error(f"⚠️ Error al generar PDF: {e}")

                    # --- Expander editable para cada informe ---
                    for _, inf in informes_sel.iterrows():
                        titulo = f"{inf.get('Fecha_Partido','')} | Scout: {inf.get('Scout','')} | Línea: {inf.get('Línea','')}"
                        with st.expander(titulo):
                            with st.form(f"form_edit_{inf['ID_Informe']}"):
                                nuevo_scout = st.text_input("Scout", inf.get("Scout",""), key=f"scout_{inf['ID_Informe']}")
                                nueva_fecha = st.text_input("Fecha del partido", inf.get("Fecha_Partido",""), key=f"fecha_{inf['ID_Informe']}")
                                nuevos_equipos = st.text_input("Equipos y resultado", inf.get("Equipos_Resultados",""), key=f"equipos_{inf['ID_Informe']}")
                                nueva_linea = st.selectbox(
                                    "Línea",
                                    ["1ra (Fichar)","2da (Seguir)","3ra (Ver más adelante)","4ta (Descartar)","Joven Promesa"],
                                    index=["1ra (Fichar)","2da (Seguir)","3ra (Ver más adelante)","4ta (Descartar)","Joven Promesa"].index(
                                        inf.get("Línea","3ra (Ver más adelante)")
                                    ),
                                    key=f"linea_{inf['ID_Informe']}"
                                )
                                nuevas_obs = st.text_area("Observaciones", inf.get("Observaciones",""), height=120, key=f"obs_{inf['ID_Informe']}")
                                guardar = st.form_submit_button("💾 Guardar cambios")

                                if guardar:
                                    try:
                                        df_reports.loc[df_reports["ID_Informe"] == inf["ID_Informe"], [
                                            "Scout","Fecha_Partido","Equipos_Resultados","Línea","Observaciones"
                                        ]] = [nuevo_scout, nueva_fecha, nuevos_equipos, nueva_linea, nuevas_obs]
                                        ws_inf = obtener_hoja("Informes")
                                        ws_inf.update([df_reports.columns.values.tolist()] + df_reports.values.tolist())
                                        st.toast("✅ Informe actualizado correctamente.", icon="✅")
                                    except Exception as e:
                                        st.error(f"⚠️ Error al actualizar el informe: {e}")
        else:
            st.info("📍 Seleccioná un registro para ver la ficha del jugador.")
    else:
        st.warning("⚠️ No se encontraron informes con los filtros seleccionados.")

# =========================================================
# BLOQUE 5 / 5 — Lista corta + Cancha + Cierre (versión final estable)
# =========================================================

if menu == "Lista corta":
    st.subheader("⭐ Lista corta de jugadores")

    # --- Filtrado por rol ---
    if CURRENT_ROLE == "scout":
        df_short = df_short[df_short["Agregado_Por"] == CURRENT_USER]

    if df_short.empty:
        st.info("ℹ️ No hay jugadores en la lista corta todavía.")
    else:
        # =========================================================
        # FILTROS
        # =========================================================
        st.sidebar.markdown("### 🔎 Filtros lista corta")
        filtro_pos = st.sidebar.multiselect("Posición", sorted(df_short["Posición"].dropna().unique()))
        filtro_club = st.sidebar.multiselect("Club", sorted(df_short["Club"].dropna().unique()))
        filtro_nac = st.sidebar.multiselect("Nacionalidad", sorted(df_players["Nacionalidad"].dropna().unique()))

        df_filtrado = df_short.copy()
        if filtro_pos:
            df_filtrado = df_filtrado[df_filtrado["Posición"].isin(filtro_pos)]
        if filtro_club:
            df_filtrado = df_filtrado[df_filtrado["Club"].isin(filtro_club)]
        if filtro_nac:
            ids_filtrados = df_players[df_players["Nacionalidad"].isin(filtro_nac)]["ID_Jugador"].tolist()
            df_filtrado = df_filtrado[df_filtrado["ID_Jugador"].isin(ids_filtrados)]

        # =========================================================
        # PESTAÑAS: LISTADO / TABLA / CANCHA
        # =========================================================
        tabs = st.tabs(["📋 Listado", "📊 Tabla", "⚽ Cancha"])

        # =========================================================
        # 📋 LISTADO EN CARTAS
        # =========================================================
        with tabs[0]:
            st.markdown("### 📇 Jugadores en lista corta (vista de cartas)")
            df_filtrado = df_filtrado.sort_values("Posición")
            cols = st.columns(3)

            for i, row in df_filtrado.iterrows():
                with cols[i % 3]:
                    st.markdown(f"""
                    <div style="background: linear-gradient(90deg, #1e3c72, #2a5298);
                        padding: 0.5em; border-radius: 5px; margin-bottom: 10px;
                        color: white; text-align: center; font-family: Arial, sans-serif; max-width: 220px;">
                        <img src="{row['URL_Foto'] if pd.notna(row['URL_Foto']) and str(row['URL_Foto']).startswith('http') else 'https://via.placeholder.com/120'}"
                             style="width:80px; border-radius:6px; margin-bottom:5px;" />
                        <h5 style="font-size:16px; margin:4px 0;">{row['Nombre']}</h5>
                        <p style="font-size:14px; margin:2px 0;">Edad: {row.get('Edad','-')}</p>
                        <p style="font-size:14px; margin:2px 0;">{row.get('Posición','-')}</p>
                        <p style="font-size:14px; margin:2px 0;">{row.get('Club','-')}</p>
                    </div>
                    """, unsafe_allow_html=True)

                    if CURRENT_ROLE in ["admin", "scout"]:
                        if st.button(f"🗑️ Borrar {row['Nombre']}", key=f"del_{i}"):
                            try:
                                ws_short = obtener_hoja("Lista corta")
                                data_short = ws_short.get_all_records()
                                df_short_local = pd.DataFrame(data_short)
                                df_short_local = df_short_local[df_short_local["ID_Jugador"].astype(str) != str(row["ID_Jugador"])]
                                ws_short.clear()
                                ws_short.append_row(list(df_short_local.columns))
                                if not df_short_local.empty:
                                    ws_short.update([df_short_local.columns.values.tolist()] + df_short_local.values.tolist())
                                st.toast(f"🗑️ Jugador {row['Nombre']} eliminado de la lista corta.", icon="🗑️")
                                st.cache_data.clear()
                                df_short = cargar_datos_sheets("Lista corta")
                            except Exception as e:
                                st.error(f"⚠️ Error al eliminar: {e}")

        # =========================================================
        # 📊 TABLA COMPLETA
        # =========================================================
        with tabs[1]:
            st.markdown("### 📊 Vista en tabla")
            columnas_tabla = ["Nombre","Edad","Posición","Club","Agregado_Por","Fecha_Agregado"]
            columnas_presentes = [c for c in columnas_tabla if c in df_filtrado.columns]
            st.dataframe(df_filtrado[columnas_presentes], use_container_width=True)

        # =========================================================
        # ⚽ VISTA EN CANCHA
        # =========================================================
        with tabs[2]:
            st.markdown("### ⚽ Distribución en cancha")

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

            # --- Asignar jugador a posición ---
            with col1:
                if CURRENT_ROLE in ["admin", "scout"]:
                    st.markdown("#### Asignar jugador a una posición")
                    jugador_opt = st.selectbox("Seleccionar jugador", [""] + list(df_short["Nombre"]))
                    pos_opt = st.selectbox("Posición en cancha", list(posiciones_cancha.keys()))
                    if st.button("Agregar a posición"):
                        if jugador_opt:
                            jugador_data = df_short[df_short["Nombre"] == jugador_opt].iloc[0]
                            jugador_info = {
                                "Nombre": jugador_data["Nombre"],
                                "Edad": jugador_data.get("Edad", "-"),
                                "Altura": jugador_data.get("Altura", "-"),
                                "Club": jugador_data.get("Club", "-")
                            }
                            if not isinstance(st.session_state["alineacion"][pos_opt], list):
                                st.session_state["alineacion"][pos_opt] = []
                            st.session_state["alineacion"][pos_opt].append(jugador_info)
                            st.toast(f"✅ {jugador_opt} agregado a {pos_opt}", icon="✅")

            # --- Dibujar cancha ---
            with col2:
                st.markdown("#### Vista en cancha")
                try:
                    cancha = plt.imread(CANCHA_IMG)
                    fig, ax = plt.subplots(figsize=(6, 9))
                    ax.imshow(cancha)
                except:
                    fig, ax = plt.subplots(figsize=(6, 9))
                    ax.set_facecolor("#003366")

                for pos, coords in posiciones_cancha.items():
                    jugadores = st.session_state["alineacion"].get(pos, [])
                    jugadores = [j for j in jugadores if isinstance(j, dict) and "Nombre" in j]
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

            # --- Eliminar jugadores de la alineación ---
            if CURRENT_ROLE in ["admin", "scout"]:
                st.markdown("### ❌ Eliminar jugadores de la alineación")
                for pos, jugadores in st.session_state["alineacion"].items():
                    jugadores = [j for j in jugadores if isinstance(j, dict) and "Nombre" in j]
                    for idx, jugador in enumerate(jugadores):
                        col_del1, col_del2 = st.columns([4, 1])
                        with col_del1:
                            st.write(f"{pos}: {jugador['Nombre']} ({jugador.get('Club','-')})")
                        with col_del2:
                            if st.button("❌", key=f"del_{pos}_{idx}"):
                                st.session_state["alineacion"][pos].pop(idx)
                                st.toast(f"🗑️ {jugador['Nombre']} eliminado de {pos}", icon="🗑️")


# =========================================================
# CIERRE PROFESIONAL (versión final optimizada)
# =========================================================

st.markdown("---")
st.markdown(f"""
<div style="text-align:center; color:#00c6ff; margin-top:30px;">
    <h4>ScoutingApp Profesional v2.0</h4>
    <p>Usuario activo: <strong>{CURRENT_USER}</strong> ({CURRENT_ROLE})</p>
    <p style="color:gray; font-size:13px;">
        Desarrollada por Mariano Cirone · Área de Scouting Profesional
    </p>
</div>
""", unsafe_allow_html=True)

# --- Limpieza de alineación temporal (sin recarga global) ---
if "user" in st.session_state:
    if "alineacion" in st.session_state and CURRENT_ROLE != "admin":
        if st.button("🧹 Limpiar alineación temporal"):
            try:
                st.session_state["alineacion"] = {
                    "Arquero": [],
                    "Defensa central derecho": [],
                    "Defensa central izquierdo": [],
                    "Lateral derecho": [],
                    "Lateral izquierdo": [],
                    "Mediocampista defensivo": [],
                    "Mediocampista mixto": [],
                    "Mediocampista ofensivo": [],
                    "Extremo derecho": [],
                    "Extremo izquierdo": [],
                    "Delantero centro": []
                }
                st.toast("🧹 Alineación limpia para la próxima sesión.", icon="🧼")
            except Exception as e:
                st.error(f"⚠️ No se pudo limpiar la alineación: {e}")

# --- Footer final ---
st.markdown(
    "<p style='text-align:center; color:gray; font-size:12px;'>© 2025 · Mariano Cirone · ScoutingApp Profesional</p>",
    unsafe_allow_html=True
)










































































