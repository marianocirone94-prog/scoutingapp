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
# BLOQUE DE CONEXIÓN A GOOGLE SHEETS (FINAL — LOCAL + CLOUD)
# =========================================================

import os, json
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import streamlit as st

# --- Configuración general ---
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
SHEET_ID = "1IInJ87xaaEwJfaz96mUlLLiX9_tk0HvqzoBoZGhrBi8"  # ID del archivo Scouting_DB
CREDS_PATH = os.path.join("credentials", "credentials.json")


def conectar_sheets():
    """
    Conecta con Google Sheets.
    Usa credenciales locales si existen (modo PC),
    o st.secrets cuando se ejecuta en Streamlit Cloud.
    """
    try:
        # --- Modo CLOUD ---
        if "GOOGLE_SERVICE_ACCOUNT_JSON" in st.secrets:
            creds_dict = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"])
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
        else:
            # --- Modo LOCAL ---
            if not os.path.exists(CREDS_PATH):
                st.error("❌ No se encontró el archivo credentials.json ni el secreto en Streamlit Cloud.")
                st.stop()
            creds = Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPE)

        client = gspread.authorize(creds)
        book = client.open_by_key(SHEET_ID)
        return book

    except Exception as e:
        st.error(f"⚠️ No se pudo conectar con Google Sheets: {e}")
        st.stop()


def obtener_hoja(nombre_hoja: str, columnas_base: list = None):
    """
    Devuelve la hoja solicitada; si no existe, la crea con las columnas base.
    """
    try:
        book = conectar_sheets()
        hojas = [ws.title for ws in book.worksheets()]
        if nombre_hoja not in hojas:
            ws = book.add_worksheet(title=nombre_hoja, rows=100, cols=20)
            if columnas_base:
                ws.append_row(columnas_base)
            st.warning(f"⚠️ Hoja '{nombre_hoja}' creada automáticamente en Scouting_DB.")
            return ws
        else:
            return book.worksheet(nombre_hoja)
    except Exception as e:
        st.error(f"⚠️ Error al obtener o crear la hoja '{nombre_hoja}': {e}")
        st.stop()


def cargar_datos_sheets(nombre_hoja: str, columnas_base: list = None) -> pd.DataFrame:
    """
    Carga datos de la hoja indicada y devuelve un DataFrame.
    Si no existen filas, devuelve DataFrame vacío con columnas base.
    """
    try:
        ws = obtener_hoja(nombre_hoja, columnas_base)
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        st.success(f"✅ Hoja '{nombre_hoja}' conectada correctamente ({len(df)} filas).")
        if df.empty and columnas_base:
            df = pd.DataFrame(columns=columnas_base)
        return df
    except Exception as e:
        st.error(f"⚠️ Error al cargar la hoja '{nombre_hoja}': {e}")
        if columnas_base:
            return pd.DataFrame(columns=columnas_base)
        return pd.DataFrame()


def actualizar_hoja(nombre_hoja: str, df: pd.DataFrame):
    """
    Reemplaza el contenido completo de la hoja con los datos del DataFrame.
    """
    try:
        ws = obtener_hoja(nombre_hoja, list(df.columns))
        ws.clear()
        if not df.empty:
            ws.update([df.columns.values.tolist()] + df.values.tolist())
        st.success(f"✅ Hoja '{nombre_hoja}' actualizada correctamente.")
    except Exception as e:
        st.error(f"⚠️ Error al actualizar '{nombre_hoja}': {e}")


def agregar_fila(nombre_hoja: str, fila: list):
    """
    Agrega una nueva fila al final de la hoja.
    """
    try:
        ws = obtener_hoja(nombre_hoja)
        ws.append_row(fila, value_input_option="USER_ENTERED")
        st.success(f"✅ Fila agregada correctamente en '{nombre_hoja}'.")
    except Exception as e:
        st.error(f"⚠️ Error al agregar fila en '{nombre_hoja}': {e}")



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
# FUNCIONES AUXILIARES Y DE CÁLCULO
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
    """Promedio de cada atributo de un jugador."""
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
    return {col: informes[col].mean() for col in columnas if col in informes.columns}


def calcular_promedios_posicion(df_reports, df_players, posicion):
    """Promedio por posición, usado para comparar jugador vs media de su rol."""
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
    return {col: informes[col].mean() for col in columnas if col in informes.columns}


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
    ax.set_xticklabels(categorias, color="white")
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

    # Normalización de IDs
    for df in [df_players, df_reports, df_short]:
        if "ID_Jugador" in df.columns:
            df["ID_Jugador"] = df["ID_Jugador"].astype(str)

    return df_players, df_reports, df_short


# =========================================================
# MENÚ PRINCIPAL
# =========================================================
df_players, df_reports, df_short = cargar_datos()

menu = st.sidebar.radio("📋 Menú principal", ["Jugadores", "Ver informes", "Lista corta"])
# =========================================================
# BLOQUE 3 / 5 — Sección Jugadores
# =========================================================

if menu == "Jugadores":
    st.subheader("🎯 Buscador de jugadores y creación de informes")

    # --- OPCIONES PREDEFINIDAS ---
    opciones_pies = ["Derecho", "Izquierdo", "Ambidiestro"]
    opciones_posiciones = [
        "Arquero", "Lateral derecho", "Defensa central derecho", "Defensa central izquierdo",
        "Lateral izquierdo", "Mediocampista defensivo", "Mediocampista mixto",
        "Mediocampista ofensivo", "Extremo derecho", "Extremo izquierdo", "Delantero centro"
    ]
    opciones_ligas = [
        "Argentina - LPF", "Argentina - Primera Nacional", "Argentina - Federal A",
        "Brasil - Serie A", "Chile - Primera División", "Uruguay - Primera División",
        "Paraguay - División Profesional", "Colombia - Categoría Primera A",
        "México - Liga MX", "España - LaLiga", "Italia - Serie A", "Inglaterra - Premier League",
        "Francia - Ligue 1", "Alemania - Bundesliga", "Otro"
    ]
    opciones_paises = [
        "Argentina", "Brasil", "Chile", "Uruguay", "Paraguay", "Colombia", "México",
        "Ecuador", "Perú", "Venezuela", "España", "Italia", "Francia", "Inglaterra",
        "Alemania", "Portugal", "Otro"
    ]

    # --- OPCIONES DEL BUSCADOR ---
    if not df_players.empty:
        opciones = {f"{row['Nombre']} - {row['Club']}": row["ID_Jugador"] for _, row in df_players.iterrows()}
    else:
        opciones = {}

    seleccion = st.selectbox("Seleccioná un jugador", [""] + list(opciones.keys()))

    # =========================================================
    # CREAR NUEVO JUGADOR
    # =========================================================
    if not seleccion:
        st.markdown("#### ¿No encontrás al jugador?")
        if st.button("➕ Agregar nuevo jugador"):
            st.markdown("### 🧾 Crear nuevo jugador")
            with st.form("nuevo_jugador_form"):
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
                guardar_nuevo = st.form_submit_button("Guardar jugador")

                if guardar_nuevo:
                    try:
                        nuevo_id = generar_id_unico(df_players, "ID_Jugador")
                        nuevo_registro = pd.DataFrame([{
                            "ID_Jugador": nuevo_id,
                            "Nombre": nuevo_nombre,
                            "Fecha_Nac": nueva_fecha,
                            "Nacionalidad": nueva_nacionalidad,
                            "Segunda_Nacionalidad": nueva_seg_nac,
                            "Altura": nueva_altura,
                            "Pie_Hábil": nuevo_pie,
                            "Posición": nueva_posicion,
                            "Caracteristica": nueva_caracteristica,
                            "Club": nuevo_club,
                            "Liga": nueva_liga,
                            "Sexo": "",
                            "URL_Foto": nueva_url_foto,
                            "URL_Perfil": nueva_url_perfil
                        }])
                        df_players = pd.concat([df_players, nuevo_registro], ignore_index=True)
                        actualizar_hoja("Jugadores", df_players)
                        st.success(f"✅ Jugador '{nuevo_nombre}' agregado correctamente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"⚠️ Ocurrió un error al agregar el jugador: {e}")

    # =========================================================
# MOSTRAR JUGADOR SELECCIONADO
# =========================================================
if seleccion:
    id_jugador = opciones[seleccion]
    jugador = df_players[df_players["ID_Jugador"] == id_jugador].iloc[0]

    if "editar_jugador" not in st.session_state:
        st.session_state.editar_jugador = False

    col1, col2, col3, col4 = st.columns([1.5, 1, 1, 1.5])

    # --- FICHA DEL JUGADOR ---
    with col1:
        st.markdown(f"### {jugador['Nombre']}")
        if pd.notna(jugador.get("URL_Foto")) and str(jugador["URL_Foto"]).startswith("http"):
            st.image(jugador["URL_Foto"], width=150)

        edad = calcular_edad(jugador.get("Fecha_Nac"))
        st.write(f"📅 {jugador.get('Fecha_Nac', '')} ({edad} años)")
        st.write(f"🌍 Nacionalidad: {jugador.get('Nacionalidad', '-')}")
        st.write(f"📏 Altura: {jugador.get('Altura', '-') } cm")
        st.write(f"👟 Pie hábil: {jugador.get('Pie_Hábil', '-')}")
        st.write(f"🎯 Posición: {jugador.get('Posición', '-')}")
        st.write(f"🏟️ Club: {jugador.get('Club', '-')} ({jugador.get('Liga', '-')})")

        if pd.notna(jugador.get("URL_Perfil")) and str(jugador["URL_Perfil"]).startswith("http"):
            st.markdown(f"[Enlace externo]({jugador['URL_Perfil']})", unsafe_allow_html=True)

        # --- BOTÓN EDITAR JUGADOR ---
        if CURRENT_ROLE in ["admin", "scout"]:
            if st.button("✏️ Editar datos del jugador"):
                st.session_state.editar_jugador = not st.session_state.editar_jugador

    # =========================================================
    # FORMULARIO DE EDICIÓN
    # =========================================================
    if st.session_state.editar_jugador:
        st.markdown("### 📝 Editar información del jugador")
        with st.form("editar_jugador_form", clear_on_submit=False):
            e_nombre = st.text_input("Nombre completo", value=jugador.get("Nombre", ""))
            e_fecha = st.text_input("Fecha de nacimiento (dd/mm/aaaa)", value=jugador.get("Fecha_Nac", ""))

            try:
                e_altura = st.number_input(
                    "Altura (cm)", min_value=140, max_value=210,
                    value=int(float(jugador.get("Altura", 175))) if str(jugador.get("Altura", "")).strip() else 175
                )
            except Exception:
                e_altura = st.number_input("Altura (cm)", min_value=140, max_value=210, value=175)

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
            e_foto = st.text_input("URL de foto (opcional)", value=str(jugador.get("URL_Foto", "")))
            e_link = st.text_input("URL perfil (opcional)", value=str(jugador.get("URL_Perfil", "")))

            guardar_ed = st.form_submit_button("💾 Guardar cambios")

        # --- GUARDAR CAMBIOS (fuera del formulario) ---
        if guardar_ed:
            try:
                df_players.loc[df_players["ID_Jugador"] == id_jugador, [
                    "Nombre", "Fecha_Nac", "Altura", "Pie_Hábil", "Posición",
                    "Club", "Liga", "Nacionalidad", "Segunda_Nacionalidad",
                    "Caracteristica", "URL_Foto", "URL_Perfil"
                ]] = [
                    e_nombre, e_fecha, e_altura, e_pie, e_pos,
                    e_club, e_liga, e_nac, e_seg, e_car, e_foto, e_link
                ]

                actualizar_hoja("Jugadores", df_players)
                st.success("✅ Datos actualizados correctamente.")
                st.session_state.editar_jugador = False
                st.experimental_rerun()

            except Exception as e:
                st.error(f"⚠️ Error al guardar cambios: {e}")

    # =========================================================
    # AGREGAR A LISTA CORTA
    # =========================================================
    if CURRENT_ROLE in ["admin", "scout"]:
        st.markdown("---")
        if st.button("⭐ Agregar a lista corta"):
            try:
                edad = calcular_edad(jugador["Fecha_Nac"])
                columnas_short = [
                    "ID_Jugador", "Nombre", "Edad", "Altura", "Club", "Posición",
                    "URL_Foto", "URL_Perfil", "Agregado_Por", "Fecha_Agregado"
                ]
                df_short_local = cargar_datos_sheets("Lista corta", columnas_short)
                if jugador["ID_Jugador"] not in df_short_local["ID_Jugador"].values:
                    nuevo = pd.DataFrame([[ 
                        jugador.get("ID_Jugador", ""), jugador.get("Nombre", ""), edad,
                        jugador.get("Altura", ""), jugador.get("Club", ""),
                        jugador.get("Posición", ""), jugador.get("URL_Foto", ""),
                        jugador.get("URL_Perfil", ""), CURRENT_USER, date.today().strftime("%d/%m/%Y")
                    ]], columns=columnas_short)
                    df_short_local = pd.concat([df_short_local, nuevo], ignore_index=True)
                    actualizar_hoja("Lista corta", df_short_local)
                    st.success("⭐ Jugador agregado a la lista corta.")
                else:
                    st.info("⚠️ Este jugador ya está en la lista corta.")
            except Exception as e:
                st.error(f"⚠️ Error al agregar a lista corta: {e}")

    # =========================================================
    # ELIMINAR JUGADOR
    # =========================================================
    if CURRENT_ROLE == "admin":
        st.markdown("---")
        st.markdown("#### ⚠️ Eliminar jugador permanentemente")
        eliminar_confirm = st.checkbox("Confirmar eliminación")
        if st.button("🗑️ Eliminar jugador"):
            if eliminar_confirm:
                try:
                    df_players = df_players[df_players["ID_Jugador"] != id_jugador]
                    actualizar_hoja("Jugadores", df_players)
                    df_short_local = cargar_datos_sheets("Lista corta")
                    df_short_local = df_short_local[df_short_local["ID_Jugador"] != id_jugador]
                    actualizar_hoja("Lista corta", df_short_local)
                    st.success(f"Jugador '{jugador['Nombre']}' eliminado correctamente.")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"⚠️ Error al eliminar: {e}")
            else:
                st.warning("Debes confirmar la eliminación antes de continuar.")


        # =========================================================
        # FORMULARIO DE INFORME
        # =========================================================
        st.subheader(f"📝 Cargar nuevo informe para {jugador['Nombre']}")

        if CURRENT_ROLE in ["admin","scout"]:
            scout = CURRENT_USER
            fecha_partido = st.date_input("Fecha del partido", format="DD/MM/YYYY")
            equipos_resultados = st.text_input("Equipos y resultado")
            formacion = st.selectbox("Formación", ["4-2-3-1","4-3-1-2","4-4-2","4-3-3","3-5-2","3-4-3","5-3-2"])
            observaciones = st.text_area("Observaciones generales")
            linea = st.selectbox("Línea de seguimiento", [
                "1ra (Fichar)","2da (Seguir)","3ra (Ver más adelante)","4ta (Descartar)","Joven Promesa"
            ])

            st.write("### Evaluación técnica (0 a 5)")
            with st.expander("Habilidades técnicas"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    controles = st.slider("Controles",0.0,5.0,0.0,0.5)
                    perfiles = st.slider("Perfiles",0.0,5.0,0.0,0.5)
                with col2:
                    pase_corto = st.slider("Pase corto",0.0,5.0,0.0,0.5)
                    pase_largo = st.slider("Pase largo",0.0,5.0,0.0,0.5)
                with col3:
                    pase_filtrado = st.slider("Pase filtrado",0.0,5.0,0.0,0.5)

            with st.expander("Aspectos defensivos"):
                col1, col2 = st.columns(2)
                with col1:
                    v1_def = st.slider("1v1 defensivo",0.0,5.0,0.0,0.5)
                    recuperacion = st.slider("Recuperación",0.0,5.0,0.0,0.5)
                with col2:
                    intercepciones = st.slider("Intercepciones",0.0,5.0,0.0,0.5)
                    duelos_aereos = st.slider("Duelos aéreos",0.0,5.0,0.0,0.5)

            with st.expander("Aspectos ofensivos"):
                col1, col2 = st.columns(2)
                with col1:
                    regate = st.slider("Regate",0.0,5.0,0.0,0.5)
                    velocidad = st.slider("Velocidad",0.0,5.0,0.0,0.5)
                with col2:
                    duelos_of = st.slider("Duelos ofensivos",0.0,5.0,0.0,0.5)

            with st.expander("Aspectos mentales / psicológicos"):
                col1, col2 = st.columns(2)
                with col1:
                    resiliencia = st.slider("Resiliencia",0.0,5.0,0.0,0.5)
                    liderazgo = st.slider("Liderazgo",0.0,5.0,0.0,0.5)
                with col2:
                    int_tactica = st.slider("Inteligencia táctica",0.0,5.0,0.0,0.5)
                    int_emocional = st.slider("Inteligencia emocional",0.0,5.0,0.0,0.5)

            with st.expander("Aspectos tácticos"):
                col1, col2 = st.columns(2)
                with col1:
                    posicionamiento = st.slider("Posicionamiento",0.0,5.0,0.0,0.5)
                    vision = st.slider("Visión de juego",0.0,5.0,0.0,0.5)
                with col2:
                    movimientos = st.slider("Movimientos sin pelota",0.0,5.0,0.0,0.5)

            if st.button("💾 Guardar informe"):
                try:
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
                    actualizar_hoja("Informes", df_reports)
                    st.success("✅ Informe guardado correctamente.")
                except Exception as e:
                    st.error(f"⚠️ Error al guardar el informe: {e}")
# =========================================================
# BLOQUE 4 / 5 — Ver Informes (filtros, edición, PDF)
# =========================================================

if menu == "Ver informes":
    st.subheader("📝 Informes cargados")

    # --- Verificamos columnas ID ---
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
        st.info("🔎 Modo visualización: no puede editar ni eliminar informes.")

    # =========================================================
    # FILTROS
    # =========================================================
    st.sidebar.markdown("### 🔎 Filtros")
    filtro_scout = st.sidebar.multiselect("Scout", sorted(df_merged["Scout"].dropna().unique()))
    filtro_jugador = st.sidebar.multiselect("Jugador", sorted(df_merged["Nombre"].dropna().unique()))
    filtro_club = st.sidebar.multiselect("Club", sorted(df_merged["Club"].dropna().unique()))
    filtro_nacionalidad = st.sidebar.multiselect("Nacionalidad", sorted(df_merged["Nacionalidad"].dropna().unique()))
    filtro_posicion = st.sidebar.multiselect("Posición", sorted(df_merged["Posición"].dropna().unique()))
    filtro_linea = st.sidebar.multiselect("Línea", sorted(df_merged["Línea"].dropna().unique()))
    filtro_edad = st.sidebar.slider("Edad", 15, 40, (15, 40))

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

    # --- Calcular edad si existe ---
    if "Fecha_Nac" in df_filtrado.columns:
        try:
            df_filtrado["Edad"] = df_filtrado["Fecha_Nac"].apply(calcular_edad)
            df_filtrado = df_filtrado[
                (df_filtrado["Edad"].apply(lambda x: isinstance(x, int)) &
                 (df_filtrado["Edad"] >= filtro_edad[0]) &
                 (df_filtrado["Edad"] <= filtro_edad[1]))
            ]
        except Exception as e:
            st.warning(f"⚠️ No se pudo calcular la edad correctamente: {e}")

    # =========================================================
    # TABLA PRINCIPAL
    # =========================================================
    if not df_filtrado.empty:
        st.markdown("### 📋 Tabla de informes filtrados")

        columnas_visibles = [
            "Fecha_Partido","Nombre","Posición","Club","Línea","Scout","Equipos_Resultados","Observaciones"
        ]
        columnas_presentes = [col for col in columnas_visibles if col in df_filtrado.columns]
        df_tabla = df_filtrado[columnas_presentes].copy()

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

        # =========================================================
        # INFORMES INDIVIDUALES
        # =========================================================
        seleccion_inf = st.selectbox("👤 Seleccioná un jugador", [""] + list(df_filtrado["Nombre"].unique()))
        if seleccion_inf:
            jugador_sel = df_players[df_players["Nombre"] == seleccion_inf].iloc[0]
            informes_sel = df_reports[df_reports["ID_Jugador"] == jugador_sel["ID_Jugador"]]
            st.markdown(f"### 📄 Informes de {jugador_sel['Nombre']}")

            # === EXPORTAR A PDF ===
            if CURRENT_ROLE in ["admin","scout"] and not informes_sel.empty:
                if st.button("📥 Exportar todos los informes en PDF"):
                    try:
                        pdf = FPDF(orientation="P", unit="mm", format="A4")
                        pdf.add_page()
                        pdf.set_font("Arial", "B", 16)
                        pdf.cell(0, 10, f"Informes de {jugador_sel['Nombre']}", ln=True, align="C")
                        pdf.ln(5)
                        pdf.set_font("Arial", "", 12)
                        pdf.cell(0, 8, f"Club: {jugador_sel.get('Club','')}", ln=True)
                        pdf.cell(0, 8, f"Posición: {jugador_sel.get('Posición','')}", ln=True)
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
                            file_name=f"Informes_{jugador_sel['Nombre']}.pdf",
                            mime="application/pdf"
                        )
                    except Exception as e:
                        st.error(f"⚠️ Error al generar el PDF: {e}")

            # === LISTADO DE INFORMES ===
            for _, inf in informes_sel.iterrows():
                titulo = f"{inf.get('Fecha_Partido','')} | Scout: {inf.get('Scout','')} | Línea: {inf.get('Línea','')}"
                with st.expander(titulo):
                    if CURRENT_ROLE == "viewer":
                        st.write(f"**Scout:** {inf.get('Scout','')}")
                        st.write(f"**Fecha partido:** {inf.get('Fecha_Partido','')}")
                        st.write(f"**Equipos:** {inf.get('Equipos_Resultados','')}")
                        st.write(f"**Línea:** {inf.get('Línea','')}")
                        st.write(f"**Observaciones:** {inf.get('Observaciones','')}")
                    else:
                        with st.form(f"form_edit_{inf['ID_Informe']}"):
                            nuevo_scout = st.text_input("Scout", inf.get("Scout",""))
                            nueva_fecha = st.text_input("Fecha del partido", inf.get("Fecha_Partido",""))
                            nuevos_equipos = st.text_input("Equipos y resultado", inf.get("Equipos_Resultados",""))
                            nueva_linea = st.selectbox(
                                "Línea",
                                ["1ra (Fichar)","2da (Seguir)","3ra (Ver más adelante)","4ta (Descartar)","Joven Promesa"],
                                index=["1ra (Fichar)","2da (Seguir)","3ra (Ver más adelante)","4ta (Descartar)","Joven Promesa"]
                                .index(inf.get("Línea","3ra (Ver más adelante)"))
                            )
                            nuevas_obs = st.text_area("Observaciones", inf.get("Observaciones",""), height=120)
                            guardar = st.form_submit_button("💾 Guardar cambios")

                            if guardar:
                                try:
                                    df_reports.loc[df_reports["ID_Informe"] == inf["ID_Informe"], [
                                        "Scout","Fecha_Partido","Equipos_Resultados","Línea","Observaciones"
                                    ]] = [nuevo_scout, nueva_fecha, nuevos_equipos, nueva_linea, nuevas_obs]
                                    actualizar_hoja("Informes", df_reports)
                                    st.success("✅ Informe actualizado correctamente.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"⚠️ Error al actualizar el informe: {e}")

    else:
        st.info("ℹ️ No se encontraron informes con los filtros seleccionados.")

# =========================================================
# BLOQUE 5 / 5 — Lista corta + Cancha + Cierre
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

        # --- LISTADO EN CARTAS ---
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
                        <p style="font-size:14px; margin:2px 0;">Edad: {row['Edad']}</p>
                        <p style="font-size:14px; margin:2px 0;">{row['Posición']}</p>
                        <p style="font-size:14px; margin:2px 0;">{row['Club']}</p>
                    </div>
                    """, unsafe_allow_html=True)

                    if CURRENT_ROLE in ["admin", "scout"]:
                        if st.button(f"🗑️ Borrar {row['Nombre']}", key=f"del_{i}"):
                            try:
                                df_short = df_short[df_short["ID_Jugador"] != row["ID_Jugador"]]
                                actualizar_hoja("Lista corta", df_short)
                                st.success(f"✅ Jugador {row['Nombre']} eliminado de la lista corta.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"⚠️ Error al eliminar: {e}")

        # --- TABLA COMPLETA ---
        with tabs[1]:
            st.markdown("### 📊 Vista en tabla")
            st.dataframe(
                df_filtrado[["Nombre","Edad","Posición","Club","Agregado_Por","Fecha_Agregado"]],
                use_container_width=True
            )

        # --- VISTA EN CANCHA ---
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
                                "Edad": jugador_data["Edad"],
                                "Altura": jugador_data["Altura"],
                                "Club": jugador_data["Club"]
                            }
                            if not isinstance(st.session_state["alineacion"][pos_opt], list):
                                st.session_state["alineacion"][pos_opt] = []
                            st.session_state["alineacion"][pos_opt].append(jugador_info)
                            st.success(f"✅ {jugador_opt} agregado a {pos_opt}")

            # --- Dibujar cancha ---
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

            # --- Eliminar jugadores de la alineación ---
            if CURRENT_ROLE in ["admin", "scout"]:
                st.markdown("### ❌ Eliminar jugadores de la alineación")
                for pos, jugadores in st.session_state["alineacion"].items():
                    jugadores = [j for j in jugadores if isinstance(j, dict) and "Nombre" in j]
                    for idx, jugador in enumerate(jugadores):
                        col_del1, col_del2 = st.columns([4, 1])
                        with col_del1:
                            st.write(f"{pos}: {jugador['Nombre']} ({jugador['Club']})")
                        with col_del2:
                            if st.button("❌", key=f"del_{pos}_{idx}"):
                                st.session_state["alineacion"][pos].pop(idx)
                                st.rerun()

# =========================================================
# CIERRE PROFESIONAL
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

if "user" in st.session_state:
    if "alineacion" in st.session_state and CURRENT_ROLE != "admin":
        if st.button("🧹 Limpiar alineación temporal"):
            st.session_state["alineacion"] = {pos: [] for pos in [
                "Arquero","Defensa central derecho","Defensa central izquierdo",
                "Lateral derecho","Lateral izquierdo","Mediocampista defensivo",
                "Mediocampista mixto","Mediocampista ofensivo",
                "Extremo derecho","Extremo izquierdo","Delantero centro"
            ]}
            st.success("Alineación limpia para la próxima sesión.")
            st.rerun()

st.markdown(
    "<p style='text-align:center; color:gray; font-size:12px;'>© 2025 · Mariano Cirone · ScoutingApp Profesional</p>",
    unsafe_allow_html=True
)



