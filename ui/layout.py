import streamlit as st
from ui.components import kpi_card

def dashboard_header(df_players, df_reports, df_short):
    total_players = len(df_players)
    total_reports = len(df_reports)
    total_short = len(df_short)

    col1, col2, col3 = st.columns(3)
    with col1:
        kpi_card("Jugadores Registrados", total_players)
    with col2:
        kpi_card("Informes Cargados", total_reports)
    with col3:
        kpi_card("Lista Corta", total_short)
