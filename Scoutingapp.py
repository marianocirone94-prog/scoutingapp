import streamlit as st
import pandas as pd
import os
from datetime import date, datetime
from ui.style import load_custom_css

# ============================
# CONFIGURACIÓN INICIAL
# ============================
st.set_page_config(
    page_title="⚽ Scouting App",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Cargar estilos extra (botones, títulos, etc.)
load_custom_css()

# ============================
# ARCHIVOS
# ============================
FILE_PLAYERS = "jugadores.csv"
FILE_REPORTS = "informes.csv"
FILE_SHORTLIST = "lista_corta.csv"

# Crear CSVs si no existen
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
        "Pase","Control","Remate","Regate",
        "Posicionamiento","Lectura_juego","Presion","Coberturas",
        "Velocidad","Resistencia","Fuerza","Potencia",
        "Personalidad","Concentracion","Competitividad","Adaptacion"
    ])
    df.to_csv(FILE_REPORTS, index=False)

if not os.path.exists(FILE_SHORTLIST):
    df = pd.DataFrame(columns=[
        "ID_Jugador","Nombre","Edad","Altura","Club","Posición","URL_Foto","URL_Perfil"
    ])
    df.to_csv(FILE_SHORTLIST, index=False)

# ============================
# FUNCIONES
# ============================
def calcular_edad(fecha_nac):
    try:
        fn = datetime.strptime(fecha_nac, "%d/%m/%Y")
        hoy = date.today()
        return hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))
    except:
        return "?"

def mostrar_ficha(jugador):
    col1, col2 = st.columns([1,3])
    with col1:
        if pd.notna(jugador["URL_Foto"]) and str(jugador["URL_Foto"]).startswith("http"):
            st.image(jugador["URL_Foto"], width=120, caption=jugador["Nombre"])
    with col2:
        st.markdown(f"### {jugador['Nombre']}")
        st.write(f"📅 Nacimiento: {jugador['Fecha_Nac']} ({calcular_edad(jugador['Fecha_Nac'])} años)")
        nacion = jugador["Nacionalidad"]
        if pd.notna(jugador["Segunda_Nacionalidad"]) and jugador["Segunda_Nacionalidad"] != "":
            nacion += f" / {jugador['Segunda_Nacionalidad']}"
        st.write(f"🌍 Nacionalidad: {nacion}")
        st.write(f"📏 Altura: {jugador['Altura']} cm")
        st.write(f"🦶 Pie: {jugador['Pie_Hábil']}")
        st.write(f"🎯 Posición: {jugador['Posición']}")
        if "Caracteristica" in jugador and pd.notna(jugador["Caracteristica"]):
            st.write(f"✨ Característica: {jugador['Caracteristica']}")
        st.write(f"🏟️ Club: {jugador['Club']} ({jugador['Liga']})")
        if pd.notna(jugador["URL_Perfil"]) and str(jugador["URL_Perfil"]).startswith("http"):
            st.markdown(f"[🌐 Ver perfil externo]({jugador['URL_Perfil']})", unsafe_allow_html=True)

    if st.button("⭐ Agregar a lista corta"):
        df_short = pd.read_csv(FILE_SHORTLIST)
        if jugador["ID_Jugador"] not in df_short["ID_Jugador"].values:
            edad = calcular_edad(jugador["Fecha_Nac"])
            nuevo = [jugador["ID_Jugador"], jugador["Nombre"], edad, jugador["Altura"],
                     jugador["Club"], jugador["Posición"], jugador["URL_Foto"], jugador["URL_Perfil"]]
            df_short.loc[len(df_short)] = nuevo
            df_short.to_csv(FILE_SHORTLIST, index=False)
            st.success("✅ Jugador agregado a la lista corta")
        else:
            st.info("⚠️ El jugador ya está en la lista corta")

# ============================
# CARGAR DATA
# ============================
df_players = pd.read_csv(FILE_PLAYERS)
df_reports = pd.read_csv(FILE_REPORTS)
df_short = pd.read_csv(FILE_SHORTLIST)

# ============================
# MENÚ
# ============================
menu = st.sidebar.radio("Menú", ["Buscar jugador", "Registrar jugador", "Ver informes", "Lista corta"])

# ============================
# BUSCAR JUGADOR
# ============================
if menu == "Buscar jugador":
    st.subheader("🔎 Buscar jugador")

    if not df_players.empty:
        opciones = {f"{row['Nombre']} - {row['Club']}": row["ID_Jugador"] for _, row in df_players.iterrows()}
        seleccion = st.selectbox("Seleccioná un jugador", [""] + list(opciones.keys()))

        if seleccion:
            id_jugador = opciones[seleccion]
            jugador = df_players[df_players["ID_Jugador"] == id_jugador].iloc[0]

            mostrar_ficha(jugador)

            st.subheader(f"📝 Cargar informe para {jugador['Nombre']}")
            scout = st.text_input("Nombre del Scout")
            fecha_partido = st.date_input("Fecha del partido", format="DD/MM/YYYY")
            equipos_resultados = st.text_input("Equipos y resultado")
            formacion = st.selectbox("Formación", ["4-2-3-1","4-3-1-2","4-4-2","4-3-3","3-5-2","3-4-3","5-3-2"])
            observaciones = st.text_area("Observaciones")
            linea = st.selectbox("Línea", ["1ra (Fichar)", "2da (Seguir)", "3ra (Ver más adelante)", "4ta (Descartar)", "Joven Promesa"])

            st.write("### Evaluación del jugador (0 a 5)")
            for bloque, items in {
                "Técnica": ["Pase", "Control", "Remate", "Regate"],
                "Táctica": ["Posicionamiento", "Lectura de juego", "Presión", "Coberturas"],
                "Físico": ["Velocidad", "Resistencia", "Fuerza", "Potencia"],
                "Mental": ["Personalidad", "Concentración", "Competitividad", "Adaptación"]
            }.items():
                st.markdown(f"#### {bloque}")
                cols = st.columns(4)
                valores = []
                for i, campo in enumerate(items):
                    with cols[i]:
                        valores.append(st.slider(campo, 0.0, 5.0, 0.0, 0.5))
                if bloque == "Técnica": pase, control, remate, regate = valores
                elif bloque == "Táctica": posic, lectura, presion, cobert = valores
                elif bloque == "Físico": vel, res, fue, pot = valores
                else: pers, conc, comp, adap = valores

            if st.button("💾 Guardar informe"):
                nuevo = [len(df_reports)+1, id_jugador, scout, fecha_partido.strftime("%d/%m/%Y"),
                         date.today().strftime("%d/%m/%Y"), equipos_resultados, formacion,
                         observaciones, linea,
                         pase, control, remate, regate,
                         posic, lectura, presion, cobert,
                         vel, res, fue, pot,
                         pers, conc, comp, adap]
                df_reports.loc[len(df_reports)] = nuevo
                df_reports.to_csv(FILE_REPORTS, index=False)
                st.success("✅ Informe guardado")

# ============================
# REGISTRAR JUGADOR
# ============================
if menu == "Registrar jugador":
    st.subheader("➕ Registrar jugador nuevo")

    NACIONALIDADES = ["Argentina","Brasil","Uruguay","Paraguay","Chile","Colombia","Perú","Ecuador","Venezuela","Bolivia",
        "Italia","España","Francia","Alemania","Portugal","Inglaterra","Países Bajos","Otro"]
    POSICIONES = ["Arquero","Defensa central derecho","Defensa central izquierdo","Lateral derecho","Lateral izquierdo",
        "Mediocampista defensivo","Mediocampista mixto","Mediocampista ofensivo",
        "Extremo derecho","Extremo izquierdo","Delantero centro"]
    LIGAS = ["Liga Profesional Argentina","Primera Nacional","Uruguay","Paraguay","Chile","Colombia",
        "Perú","Ecuador","Venezuela","Brasil","MLS","México","España","Italia","Francia",
        "Alemania","Inglaterra","España B","Bélgica","Polonia","Portugal","Holanda","Otro"]
    CARACTERISTICAS = ["Agresividad","Lectura de juego","Velocidad","Resistencia",
        "Timing","Personalidad","Competitividad","Creatividad","Pase largo","Regate","Juego aéreo","Otro"]

    nombre = st.text_input("Nombre completo")
    fecha_nac = st.date_input("Fecha de nacimiento", min_value=date(1980,1,1), max_value=date.today(), format="DD/MM/YYYY")
    nacionalidad = st.selectbox("Nacionalidad", NACIONALIDADES)
    segunda_nac = st.selectbox("Segunda nacionalidad (opcional)", [""] + NACIONALIDADES)
    altura = st.number_input("Altura (cm)", min_value=140, max_value=210)
    pie = st.selectbox("Pie hábil", ["Derecho","Izquierdo","Ambidiestro"])
    posicion = st.selectbox("Posición específica", POSICIONES)
    caracteristica = st.selectbox("Característica principal", CARACTERISTICAS)
    club = st.text_input("Club")
    liga = st.selectbox("Liga", LIGAS)
    sexo = st.selectbox("Sexo", ["Masculino","Femenino"])
    url_foto = st.text_input("URL de foto")
    url_perfil = st.text_input("URL de perfil externo")

    if st.button("Guardar jugador"):
        nuevo = [len(df_players)+1, nombre, fecha_nac.strftime("%d/%m/%Y"), nacionalidad, segunda_nac,
                 altura, pie, posicion, caracteristica, club, liga, sexo, url_foto, url_perfil]
        df_players.loc[len(df_players)] = nuevo
        df_players.to_csv(FILE_PLAYERS, index=False)
        st.success("✅ Jugador registrado")

# ============================
# VER INFORMES
# ============================
if menu == "Ver informes":
    st.subheader("📝 Informes cargados")

    df_merged = df_reports.merge(df_players, on="ID_Jugador", how="left")

    st.sidebar.markdown("### 🔎 Filtros")
    filtro_scout = st.sidebar.multiselect("Scout", sorted(df_merged["Scout"].dropna().unique()))
    filtro_jugador = st.sidebar.multiselect("Jugador", sorted(df_merged["Nombre"].dropna().unique()))
    filtro_club = st.sidebar.multiselect("Club", sorted(df_merged["Club"].dropna().unique()))
    filtro_nacionalidad = st.sidebar.multiselect("Nacionalidad", sorted(df_merged["Nacionalidad"].dropna().unique()))
    filtro_posicion = st.sidebar.multiselect("Posición", sorted(df_merged["Posición"].dropna().unique()))
    filtro_linea = st.sidebar.multiselect("Línea", sorted(df_merged["Línea"].dropna().unique()))
    filtro_caracteristica = st.sidebar.multiselect("Característica", sorted(df_merged["Caracteristica"].dropna().unique()))
    filtro_edad = st.sidebar.slider("Edad", 15, 40, (15,40))

    df_filtrado = df_merged.copy()
    if filtro_scout: df_filtrado = df_filtrado[df_filtrado["Scout"].isin(filtro_scout)]
    if filtro_jugador: df_filtrado = df_filtrado[df_filtrado["Nombre"].isin(filtro_jugador)]
    if filtro_club: df_filtrado = df_filtrado[df_filtrado["Club"].isin(filtro_club)]
    if filtro_nacionalidad: df_filtrado = df_filtrado[df_filtrado["Nacionalidad"].isin(filtro_nacionalidad)]
    if filtro_posicion: df_filtrado = df_filtrado[df_filtrado["Posición"].isin(filtro_posicion)]
    if filtro_linea: df_filtrado = df_filtrado[df_filtrado["Línea"].isin(filtro_linea)]
    if filtro_caracteristica: df_filtrado = df_filtrado[df_filtrado["Caracteristica"].isin(filtro_caracteristica)]
    if "Fecha_Nac" in df_filtrado.columns:
        df_filtrado["Edad"] = df_filtrado["Fecha_Nac"].apply(calcular_edad)
        df_filtrado = df_filtrado[(df_filtrado["Edad"] >= filtro_edad[0]) & (df_filtrado["Edad"] <= filtro_edad[1])]

    if not df_filtrado.empty:
        st.markdown("### 📋 Tabla de informes")
        columnas_mostrar = ["Nombre", "Observaciones", "Línea", "Scout", "Equipos_Resultados"]
        st.dataframe(df_filtrado[columnas_mostrar], use_container_width=True, height=400)

        seleccion = st.selectbox("👤 Seleccioná un jugador", [""] + list(df_filtrado["Nombre"].unique()))

        if seleccion:
            jugador_sel = df_players[df_players["Nombre"] == seleccion].iloc[0]

            st.markdown("### 📋 Ficha del jugador")
            col1, col2 = st.columns([1,3])
            with col1:
                if pd.notna(jugador_sel["URL_Foto"]) and str(jugador_sel["URL_Foto"]).startswith("http"):
                    st.image(jugador_sel["URL_Foto"], width=120, caption=jugador_sel["Nombre"])
            with col2:
                st.write(f"**Nombre:** {jugador_sel['Nombre']}")
                st.write(f"🏟️ Club: {jugador_sel['Club']}")
                st.write(f"🗓️ Edad: {calcular_edad(jugador_sel['Fecha_Nac'])}")
                st.write(f"📏 Altura: {jugador_sel['Altura']} cm")
                st.write(f"🧦 Pie: {jugador_sel['Pie_Hábil']}")
                st.write(f"🎯 Posición: {jugador_sel['Posición']}")
                st.write(f"🌍 Nacionalidad: {jugador_sel['Nacionalidad']}")
                st.write(f"🏆 Liga: {jugador_sel['Liga']}")
                st.write(f"✨ Característica: {jugador_sel['Caracteristica']}")

            informes_sel = df_reports[df_reports["ID_Jugador"] == jugador_sel["ID_Jugador"]].copy()
            if not informes_sel.empty:
                st.markdown("### 📝 Informes del jugador")
                for _, inf in informes_sel.iterrows():
                    st.markdown(f"**🗓️ {inf['Fecha_Partido']} | Scout: {inf['Scout']} | Línea: {inf['Línea']}**")
                    st.write(f"🏟️ Equipos: {inf['Equipos_Resultados']}")
                    st.text_area("Observaciones", inf["Observaciones"], height=120, disabled=True)
                    st.markdown("---")

# ============================
# LISTA CORTA
# ============================
if menu == "Lista corta":
    st.subheader("⭐ Lista corta")

    if df_short.empty:
        st.info("No hay jugadores en la lista corta todavía.")
    else:
        st.markdown("### 📊 Jugadores en la lista corta")

        cols = st.columns(3)  # hasta 3 tarjetas por fila

        for i, row in df_short.iterrows():
            with cols[i % 3]:  # distribuir tarjetas en columnas
                st.markdown(f"""
                <div style="
                    background: linear-gradient(90deg, #1e3c72, #2a5298);
                    padding: 0.8em;
                    border-radius: 10px;
                    margin-bottom: 12px;
                    color: white;
                    text-align: center;
                    box-shadow: 0 0 8px rgba(0,0,0,0.25);
                ">
                    <img src="{row['URL_Foto'] if pd.notna(row['URL_Foto']) and str(row['URL_Foto']).startswith('http') else 'https://via.placeholder.com/120x140.png?text=Jugador'}" 
                         style="width:100px; border-radius:8px; margin-bottom:0.5em;" />
                    <h5 style="margin:0;">{row['Nombre']}</h5>
                    <p style="margin:0.2em 0;">Edad: {row['Edad']} años</p>
                    <p style="margin:0.2em 0;">{row['Posición']}</p>
                    <p style="margin:0.2em 0;">{row['Club']}</p>
                </div>
                """, unsafe_allow_html=True)

                # Botón para ver informes
                if st.button("📑 Ver informes", key=f"inf_{row['ID_Jugador']}"):
                    informes_sel = df_reports[df_reports["ID_Jugador"] == row["ID_Jugador"]].copy()
                    if informes_sel.empty:
                        st.info("⚠️ No hay informes aún de este jugador.")
                    else:
                        st.markdown(f"### Informes de {row['Nombre']}")
                        for _, inf in informes_sel.iterrows():
                            st.markdown(f"**🗓️ {inf['Fecha_Partido']} | Scout: {inf['Scout']} | Línea: {inf['Línea']}**")
                            st.write(f"🏟️ Equipos: {inf['Equipos_Resultados']}")
                            st.text_area("Observaciones", inf["Observaciones"], height=100, disabled=True)
                            st.markdown("---")

              # Botón para eliminar de lista corta
if st.button("🗑️ Eliminar", key=f"del_{row['ID_Jugador']}"):
    df_short = df_short[df_short["ID_Jugador"] != row["ID_Jugador"]]
    df_short.to_csv(FILE_SHORTLIST, index=False)
    st.success(f"Jugador {row['Nombre']} eliminado de la lista corta")
    st.rerun()  # recargar la app
