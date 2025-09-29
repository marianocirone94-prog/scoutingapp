import streamlit as st
import pandas as pd
import os
from datetime import date, datetime

# Archivos locales
FILE_PLAYERS = "jugadores.csv"
FILE_REPORTS = "informes.csv"

# Crear CSVs si no existen
if not os.path.exists(FILE_PLAYERS):
    df = pd.DataFrame(columns=["ID_Jugador","Nombre","Fecha_Nac","Nacionalidad","Altura",
                               "Pie_Hábil","Posición","Club","Liga","Sexo","URL_Foto","URL_Perfil"])
    df.to_csv(FILE_PLAYERS, index=False)

if not os.path.exists(FILE_REPORTS):
    df = pd.DataFrame(columns=["ID_Informe","ID_Jugador","Scout","Fecha_Partido","Fecha_Informe",
                               "Equipos_Resultados","Formación","Controles","Perfiles","Pase_Corto",
                               "Pase_Largo","Pase_Filtrado","1v1_Defensivo","Recuperación","Interceptaciones",
                               "Duelos_Aereos","Regate","Velocidad","Duelos_Ofensivos","Resiliencia",
                               "Liderazgo","Inteligencia_Táctica","Inteligencia_Emocional","Posicionamiento",
                               "Visión_Juego","Movimientos_sin_Pelota","Observaciones","Línea"])
    df.to_csv(FILE_REPORTS, index=False)

# Funciones auxiliares
def calcular_edad(fecha_nac):
    try:
        fn = datetime.strptime(fecha_nac, "%d/%m/%Y")
        hoy = date.today()
        return hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))
    except:
        return "?"

def mostrar_ficha_editable(jugador, df_players):
    st.markdown("### 🧾 Ficha del jugador (editable)")

    nombre = st.text_input("Nombre", jugador.get("Nombre",""))
    fecha_nac = st.text_input("Fecha de nacimiento (dd/mm/aaaa)", jugador.get("Fecha_Nac",""))
    nacionalidad = st.text_input("Nacionalidad", jugador.get("Nacionalidad",""))
    altura = st.text_input("Altura (cm)", str(jugador.get("Altura","")))
    pie = st.selectbox("Pie hábil", ["", "Derecho", "Izquierdo", "Ambidiestro"], 
                       index=["", "Derecho", "Izquierdo", "Ambidiestro"].index(jugador.get("Pie_Hábil","")) if jugador.get("Pie_Hábil","") in ["Derecho","Izquierdo","Ambidiestro"] else 0)
    posicion = st.text_input("Posición", jugador.get("Posición",""))
    club = st.text_input("Club", jugador.get("Club",""))
    liga = st.text_input("Liga", jugador.get("Liga",""))
    sexo = st.selectbox("Sexo", ["", "Masculino", "Femenino"], 
                        index=["", "Masculino", "Femenino"].index(jugador.get("Sexo","")) if jugador.get("Sexo","") in ["Masculino","Femenino"] else 0)
    url_foto = st.text_input("URL Foto", jugador.get("URL_Foto",""))
    url_perfil = st.text_input("URL Perfil", jugador.get("URL_Perfil",""))

    if st.button("💾 Guardar cambios en jugador"):
        df_players.loc[df_players["ID_Jugador"] == jugador["ID_Jugador"], 
                       ["Nombre","Fecha_Nac","Nacionalidad","Altura","Pie_Hábil","Posición","Club","Liga","Sexo","URL_Foto","URL_Perfil"]] = \
                       [nombre, fecha_nac, nacionalidad, altura, pie, posicion, club, liga, sexo, url_foto, url_perfil]
        df_players.to_csv(FILE_PLAYERS, index=False)
        st.success("✅ Datos del jugador actualizados")

    # Mostrar visual
    col1, col2 = st.columns([1,2])
    with col1:
        if url_foto and url_foto.startswith("http"):
            st.image(url_foto, width=150)
    with col2:
        st.write(f"**Nombre:** {nombre}")
        if fecha_nac:
            st.write(f"**Fecha de nacimiento:** {fecha_nac} ({calcular_edad(fecha_nac)} años)")
        st.write(f"**Club:** {club}")
        st.write(f"**Nacionalidad:** {nacionalidad}")
        st.write(f"**Posición:** {posicion}")
        st.write(f"**Pie:** {pie}")
        st.write(f"**Altura:** {altura} cm")
        if url_perfil and url_perfil.startswith("http"):
            st.markdown(f"[🌐 Perfil externo]({url_perfil})")

def mostrar_informes(df_reports, id_jugador):
    informes = df_reports[df_reports["ID_Jugador"] == id_jugador]
    if informes.empty:
        st.info("⚠️ No hay informes cargados todavía")
    else:
        for _, inf in informes.iterrows():
            with st.expander(f"📅 {inf['Fecha_Partido']} | Scout: {inf['Scout']} | Línea: {inf['Línea']}"):
                st.write(f"**Resultado:** {inf['Equipos_Resultados']} | **Formación:** {inf['Formación']}")
                st.write("**Observaciones:**")
                st.write(inf["Observaciones"])
                st.write("**Ratings técnicos:**")
                ratings = {k: inf[k] for k in ["Controles","Perfiles","Pase_Corto","Pase_Largo","Pase_Filtrado",
                                               "1v1_Defensivo","Recuperación","Interceptaciones","Duelos_Aereos",
                                               "Regate","Velocidad","Duelos_Ofensivos","Resiliencia","Liderazgo",
                                               "Inteligencia_Táctica","Inteligencia_Emocional","Posicionamiento",
                                               "Visión_Juego","Movimientos_sin_Pelota"]}
                st.json(ratings)

def formatear_opcion(jugador):
    try:
        año = datetime.strptime(jugador["Fecha_Nac"], "%d/%m/%Y").year
    except:
        año = "?"
    return f"{jugador['Nombre']} ({año}) - {jugador['Club']}"

# ================== APP ==================

st.title("⚽ Scouting App")

# Cargar data
df_players = pd.read_csv(FILE_PLAYERS)
df_reports = pd.read_csv(FILE_REPORTS)

menu = st.sidebar.radio("Menú", ["Buscar jugador", "Registrar jugador", "Ver jugadores", "Ver informes"])

# === BUSCAR JUGADOR ===
if menu == "Buscar jugador":
    st.subheader("🔎 Buscar jugador")

    if not df_players.empty:
        opciones = {formatear_opcion(row): row["ID_Jugador"] for _, row in df_players.iterrows()}
        seleccion = st.selectbox("Seleccioná un jugador", [""] + list(opciones.keys()))

        if seleccion:
            id_jugador = opciones[seleccion]
            jugador = df_players[df_players["ID_Jugador"] == id_jugador].iloc[0].to_dict()

            # Ficha editable
            mostrar_ficha_editable(jugador, df_players)

            # Formulario de informe
            st.subheader(f"📝 Nuevo informe para {jugador['Nombre']}")
            scout = st.text_input("Nombre del Scout")
            fecha_partido = st.date_input("Fecha del partido")
            equipos_resultados = st.text_input("Equipos y resultado")
            formacion = st.selectbox("Formación", ["4-2-3-1","4-3-1-2","4-4-2","4-3-3","3-5-2","3-4-3","5-3-2"])
            observaciones = st.text_area("Observaciones")
            linea = st.selectbox("Línea", ["1ra (Fichar)", "2da (Seguir)", "3ra (Ver más adelante)", "4ta (Descartar)", "Joven Promesa"])

            if st.button("💾 Guardar informe"):
                nuevo = [len(df_reports)+1, id_jugador, scout, fecha_partido.strftime("%d/%m/%Y"),
                         date.today().strftime("%d/%m/%Y"), equipos_resultados, formacion,
                         0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,  # acá podrías agregar sliders de ratings
                         observaciones, linea]
                df_reports.loc[len(df_reports)] = nuevo
                df_reports.to_csv(FILE_REPORTS, index=False)
                st.success("✅ Informe guardado")

            # Visualización de informes cargados
            st.subheader("📊 Informes cargados")
            mostrar_informes(df_reports, id_jugador)
    else:
        st.info("Todavía no hay jugadores cargados")

# === REGISTRAR JUGADOR ===
if menu == "Registrar jugador":
    st.subheader("➕ Registrar jugador nuevo")

    nombre = st.text_input("Nombre completo")
    fecha_nac = st.date_input("Fecha de nacimiento", min_value=date(1986,1,1), max_value=date.today())
    nacionalidad = st.text_input("Nacionalidad")
    altura = st.number_input("Altura (cm)", min_value=140, max_value=210)
    pie = st.selectbox("Pie hábil", ["Derecho", "Izquierdo", "Ambidiestro"])
    posicion = st.text_input("Posición")
    club = st.text_input("Club")
    liga = st.text_input("Liga")
    sexo = st.selectbox("Sexo", ["Masculino", "Femenino"])
    url_foto = st.text_input("URL de foto")
    url_perfil = st.text_input("URL de perfil externo (BeSoccer, Transfermarkt, etc.)")

    if st.button("Guardar jugador"):
        nuevo = [len(df_players)+1, nombre, fecha_nac.strftime("%d/%m/%Y"), nacionalidad, altura,
                 pie, posicion, club, liga, sexo, url_foto, url_perfil]
        df_players.loc[len(df_players)] = nuevo
        df_players.to_csv(FILE_PLAYERS, index=False)
        st.success("✅ Jugador registrado")

# === VER JUGADORES ===
if menu == "Ver jugadores":
    st.subheader("📋 Jugadores registrados")
    st.dataframe(df_players)

# === VER INFORMES ===
if menu == "Ver informes":
    st.subheader("📝 Informes cargados")
    st.dataframe(df_reports)
