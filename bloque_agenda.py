# =========================================================
# 🕐 BLOQUE AGENDA — ScoutingApp PRO (versión final)
# =========================================================

import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import os

# =========================================================
# ESTILO Y CONFIGURACIÓN
# =========================================================
st.set_page_config(page_title="📅 Agenda — ScoutingApp PRO", layout="wide")

st.markdown("""
<style>
body, .stApp {
    background-color:#0e1117 !important;
    color:white !important;
    font-family:'Segoe UI',sans-serif;
}
h1,h2,h3,h4,h5,h6 { color:white !important; }

.card-container {
    display:flex;
    flex-wrap:wrap;
    justify-content:center;
    gap:14px;
    margin-bottom:1em;
}
.card {
    background:linear-gradient(90deg,#0e1117,#1e3c72);
    border-radius:10px;
    padding:0.6em 0.9em;
    color:white;
    box-shadow:0 0 8px rgba(0,0,0,0.5);
    transition:0.2s ease-in-out;
    width:210px;
    min-height:135px;
}
.card:hover {transform:scale(1.04);}
.card h5 {color:#00c6ff;font-size:14px;margin:0 0 3px 0;text-align:left;}
.card p {font-size:12px;color:#b0b0b0;margin:2px 0;}
.card.visto {opacity:0.7;background:linear-gradient(90deg,#1a1f2e,#2a3a5a);}
.label {
    display:inline-block;font-size:11px;padding:2px 6px;border-radius:5px;
    font-weight:bold;margin-bottom:5px;
}
.vencido{background-color:#8b0000;color:white;}
.hoy{background-color:#ffd700;color:black;}
.proximo{background-color:#006400;color:white;}
.futuro{background-color:#004488;color:white;}
</style>
""", unsafe_allow_html=True)

st.markdown("<h3 style='text-align:center;color:#00c6ff;'>📅 Agenda de Seguimiento — ScoutingApp PRO</h3>", unsafe_allow_html=True)

# =========================================================
# CARGA DE DATOS
# =========================================================
PATH_JUGADORES = "jugadores.csv"
PATH_AGENDA = "agenda.csv"

@st.cache_data
def cargar_jugadores():
    if not os.path.exists(PATH_JUGADORES):
        ejemplo = pd.DataFrame({
            "ID_Jugador":[1,2,3,4,5],
            "Nombre":["Tomás O'Connor","Gaspar Duarte","Santiago Segovia","Francesco Lo Celso","Kevin Ortiz"]
        })
        ejemplo.to_csv(PATH_JUGADORES,index=False,encoding="utf-8")
        return ejemplo
    return pd.read_csv(PATH_JUGADORES,encoding="utf-8").fillna("")

def cargar_agenda():
    columnas=["ID_Jugador","Nombre","Scout","Fecha_Revisar","Motivo","Visto"]
    if not os.path.exists(PATH_AGENDA):
        hoy=datetime.now().date()
        ejemplo=pd.DataFrame([
            [1,"Tomás O'Connor","Mariano Cirone",hoy+timedelta(days=2),"Revisión general",False],
            [2,"Gaspar Duarte","Dario Marra",hoy-timedelta(days=1),"Revisar intensidad",False],
            [3,"Santiago Segovia","Mariano Cirone",hoy+timedelta(days=5),"Controlar rendimiento físico",True],
        ],columns=columnas)
        ejemplo.to_csv(PATH_AGENDA,index=False,encoding="utf-8")
        return ejemplo
    df=pd.read_csv(PATH_AGENDA,encoding="utf-8").fillna("")
    df["Fecha_Revisar"]=pd.to_datetime(df["Fecha_Revisar"],errors="coerce")
    df=df[df["Fecha_Revisar"].notna()]
    df["Visto"]=df["Visto"].astype(str).str.lower().isin(["true","1","si","sí"])
    return df

df_players=cargar_jugadores()
df_agenda=cargar_agenda()

# =========================================================
# FUNCIONES
# =========================================================
def marcar_visto(nombre):
    df=pd.read_csv(PATH_AGENDA,encoding="utf-8")
    df.loc[df["Nombre"]==nombre,"Visto"]=True
    df.to_csv(PATH_AGENDA,index=False,encoding="utf-8")
    st.toast(f"✅ {nombre} marcado como visto.", icon="✅")
    st.cache_data.clear()
    st.rerun()

def guardar_nuevo(id_jugador, nombre, scout, fecha, motivo):
    fecha=pd.to_datetime(fecha)
    df=pd.read_csv(PATH_AGENDA,encoding="utf-8") if os.path.exists(PATH_AGENDA) else pd.DataFrame()
    nueva=pd.DataFrame([{
        "ID_Jugador":id_jugador,"Nombre":nombre,"Scout":scout,
        "Fecha_Revisar":fecha,"Motivo":motivo,"Visto":False
    }])
    df_final=pd.concat([df,nueva],ignore_index=True)
    df_final.to_csv(PATH_AGENDA,index=False,encoding="utf-8")
    st.success(f"✅ Seguimiento agendado para {nombre} el {fecha.strftime('%d/%m/%Y')}")
    st.cache_data.clear()
    st.rerun()

# =========================================================
# DATOS
# =========================================================
hoy = pd.Timestamp(datetime.now().date())
pendientes = df_agenda[df_agenda["Visto"] == False]
vistos = df_agenda[df_agenda["Visto"] == True]

# =========================================================
# PENDIENTES
# =========================================================
with st.expander("🕐 Seguimientos pendientes", expanded=True):
    if pendientes.empty:
        st.info("No hay seguimientos pendientes.")
    else:
        st.markdown("<div class='card-container'>", unsafe_allow_html=True)
        for _,row in pendientes.sort_values("Fecha_Revisar").iterrows():
            nombre,scout,fecha,motivo=row["Nombre"],row["Scout"],row["Fecha_Revisar"],row["Motivo"]
            if pd.isnull(fecha): continue
            dias=(fecha - hoy).days
            if dias < 0: label="<span class='label vencido'>Vencido</span>"
            elif dias == 0: label="<span class='label hoy'>Hoy</span>"
            elif dias <= 7: label=f"<span class='label proximo'>En {dias} días</span>"
            else: label=f"<span class='label futuro'>En {dias} días</span>"
            st.markdown(f"""
            <div class='card'>
                {label}
                <h5>{nombre}</h5>
                <p>Scout: {scout}</p>
                <p>📅 {fecha.strftime('%d/%m/%Y')}</p>
                <p><i>{motivo}</i></p>
            </div>
            """, unsafe_allow_html=True)
            st.button("👁 Marcar visto", key=f"visto_{nombre}", on_click=marcar_visto, args=(nombre,))
        st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# YA VISTOS (Misma estructura horizontal)
# =========================================================
with st.expander("👁 Seguimientos ya vistos", expanded=False):
    if vistos.empty:
        st.info("No hay jugadores vistos aún.")
    else:
        st.markdown("<div class='card-container'>", unsafe_allow_html=True)
        for _,row in vistos.sort_values("Fecha_Revisar").iterrows():
            nombre,scout,fecha,motivo=row["Nombre"],row["Scout"],row["Fecha_Revisar"],row["Motivo"]
            if pd.isnull(fecha): continue
            st.markdown(f"""
            <div class='card visto'>
                <span class='label futuro'>Visto</span>
                <h5>{nombre}</h5>
                <p>Scout: {scout}</p>
                <p>📅 {fecha.strftime('%d/%m/%Y')}</p>
                <p><i>{motivo}</i></p>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# FORMULARIO NUEVO SEGUIMIENTO
# =========================================================
st.markdown("---")
with st.expander("➕ Agendar nuevo seguimiento", expanded=False):
    jugadores_dict={row["Nombre"]:row["ID_Jugador"] for _,row in df_players.iterrows()}

    col1, col2 = st.columns(2)
    with col1:
        jugador_sel=st.selectbox("Seleccioná un jugador",[""]+list(jugadores_dict.keys()))
        scout=st.text_input("Scout responsable")
    with col2:
        fecha_rev=st.date_input("Fecha de revisión", value=datetime.now().date()+timedelta(days=7))
        motivo=st.text_area("Motivo del seguimiento", height=70)

    if jugador_sel and st.button("💾 Guardar seguimiento"):
        id_jugador=jugadores_dict[jugador_sel]
        guardar_nuevo(id_jugador, jugador_sel, scout, fecha_rev, motivo)
