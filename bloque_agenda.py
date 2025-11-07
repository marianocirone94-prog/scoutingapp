# =========================================================
# 🕐 BLOQUE 6 / 6 — Agenda de Seguimiento — ScoutingApp PRO
# =========================================================
# - Conectada a Google Sheets (crea hoja "Agenda" si no existe)
# - Jugadores obtenidos directamente desde df_players
# - Tarjetas visuales 5x5 con botón de "Marcar visto"
# =========================================================

import streamlit as st
import pandas as pd
from datetime import datetime
import uuid

# =========================================================
# FUNCIÓN PRINCIPAL
# =========================================================
def render_agenda(current_user, current_role, df_players):
    st.markdown("<h2 style='text-align:center;color:#00c6ff;'>📅 Agenda de Seguimiento</h2>", unsafe_allow_html=True)

    # =========================================================
    # CONEXIÓN CON GOOGLE SHEETS
    # =========================================================
    try:
        from Scoutingapp import obtener_hoja
    except Exception as e:
        st.error(f"⚠️ No se pudo importar funciones base: {e}")
        return

    columnas_base = ["ID_Jugador", "Nombre", "Scout", "Fecha_Revisar", "Motivo", "Visto"]

    try:
        ws = obtener_hoja("Agenda", columnas_base)
    except Exception as e:
        st.error(f"⚠️ No se pudo acceder o crear la hoja Agenda: {e}")
        return

    # =========================================================
    # LECTURA DE DATOS
    # =========================================================
    try:
        data = ws.get_all_records()
        df_agenda = pd.DataFrame(data)
    except Exception as e:
        st.error(f"⚠️ No se pudo leer la hoja Agenda: {e}")
        return

    if df_agenda.empty:
        df_agenda = pd.DataFrame(columns=columnas_base)

    if "Fecha_Revisar" in df_agenda.columns:
        df_agenda["Fecha_Revisar"] = pd.to_datetime(df_agenda["Fecha_Revisar"], errors="coerce")

    # =========================================================
    # CSS VISUAL (tema oscuro coherente)
    # =========================================================
    st.markdown("""
    <style>
    .agenda-card {
        background: linear-gradient(90deg,#0e1117,#1e3c72);
        border-radius: 14px;
        padding: 10px 12px;
        margin: 8px 0;
        color: white;
        box-shadow: 0 0 10px rgba(0,0,0,0.45);
        transition: 0.2s ease-in-out;
        min-height: 115px;
    }
    .agenda-card:hover {
        transform: scale(1.03);
        box-shadow: 0 0 12px #00c6ff;
    }
    .agenda-title { color: #00c6ff; font-size: 14px; font-weight: bold; margin-bottom: 4px; text-align:center; }
    .agenda-sub { font-size: 12.5px; color: #b0b0b0; margin: 2px 0; text-align:center; }
    .agenda-date { font-size: 12px; color: white; margin-top: 3px; text-align:center; }
    </style>
    """, unsafe_allow_html=True)

    # =========================================================
    # FORMULARIO NUEVO SEGUIMIENTO
    # =========================================================
    st.markdown("### ➕ Agendar nuevo seguimiento")

    with st.expander("Nuevo seguimiento", expanded=False):
        with st.form("form_agenda"):
            col1, col2 = st.columns(2)
            with col1:
                jugador_sel = st.selectbox("Jugador", [""] + sorted(df_players["Nombre"].dropna().unique()))
                scout = st.text_input("Scout", value=current_user)
            with col2:
                fecha_rev = st.date_input("Fecha de revisión", format="DD/MM/YYYY")
                motivo = st.text_input("Motivo del seguimiento")

            guardar = st.form_submit_button("💾 Guardar seguimiento")

            if guardar:
                if not jugador_sel or not fecha_rev:
                    st.warning("⚠️ Debes seleccionar jugador y fecha.")
                else:
                    try:
                        id_jug = df_players.loc[df_players["Nombre"] == jugador_sel, "ID_Jugador"].iloc[0]
                        nueva_fila = [
                            id_jug,
                            jugador_sel,
                            scout,
                            fecha_rev.strftime("%Y-%m-%d"),
                            motivo,
                            "Pendiente"
                        ]
                        ws.append_row(nueva_fila)
                        st.success(f"✅ Seguimiento agendado para {jugador_sel} el {fecha_rev.strftime('%d/%m/%Y')}")
                        try:
                            st.cache_data.clear()
                        except Exception:
                            pass
                        st.rerun()
                    except Exception as e:
                        st.error(f"⚠️ Error al guardar seguimiento: {e}")

    # =========================================================
    # SEPARACIÓN DE ESTADOS
    # =========================================================
    pendientes = df_agenda[df_agenda["Visto"] != "Sí"] if not df_agenda.empty else pd.DataFrame()
    vistos = df_agenda[df_agenda["Visto"] == "Sí"] if not df_agenda.empty else pd.DataFrame()

    # =========================================================
    # BLOQUE PENDIENTES
    # =========================================================
    st.markdown("---")
    st.markdown("### 🟡 Seguimientos pendientes")

    if pendientes.empty:
        st.info("No hay seguimientos pendientes.")
    else:
        for fila in range(0, len(pendientes), 5):
            cols = st.columns(5)
            sub = pendientes.iloc[fila:fila + 5]
            for col_idx, (_, row) in enumerate(sub.iterrows()):
                with cols[col_idx]:
                    fecha_txt = (
                        row["Fecha_Revisar"].strftime("%d/%m/%Y")
                        if pd.notnull(row["Fecha_Revisar"])
                        else "-"
                    )

                    unique_key = f"mark_{row['ID_Jugador']}_{str(row['Fecha_Revisar'])}"

                    st.markdown(f"""
                    <div class="agenda-card">
                        <div class="agenda-title">{row['Nombre']}</div>
                        <div class="agenda-sub">Scout: {row['Scout']}</div>
                        <div class="agenda-sub">Motivo: {row['Motivo']}</div>
                        <div class="agenda-date">📅 {fecha_txt}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    if st.button("✅ Marcar visto", key=unique_key):
                        try:
                            df_agenda.loc[
                                (df_agenda["ID_Jugador"] == row["ID_Jugador"]) &
                                (df_agenda["Fecha_Revisar"] == row["Fecha_Revisar"]),
                                "Visto"
                            ] = "Sí"

                            ws.clear()
                            ws.update([df_agenda.columns.values.tolist()] + df_agenda.fillna("").values.tolist())
                            st.success(f"👀 Marcado como visto: {row['Nombre']}")
                            try:
                                st.cache_data.clear()
                            except Exception:
                                pass
                            st.rerun()
                        except Exception as e:
                            st.error(f"⚠️ Error al actualizar: {e}")

    # =========================================================
    # BLOQUE YA VISTOS
    # =========================================================
    st.markdown("---")
    st.markdown("### 🟢 Seguimientos ya vistos")

    if vistos.empty:
        st.info("No hay seguimientos vistos aún.")
    else:
        for fila in range(0, len(vistos), 5):
            cols = st.columns(5)
            sub = vistos.iloc[fila:fila + 5]
            for col_idx, (_, row) in enumerate(sub.iterrows()):
                with cols[col_idx]:
                    fecha_txt = (
                        row["Fecha_Revisar"].strftime("%d/%m/%Y")
                        if pd.notnull(row["Fecha_Revisar"])
                        else "-"
                    )
                    st.markdown(f"""
                    <div class="agenda-card" style="background:linear-gradient(90deg,#1e3c72,#0e1117);">
                        <div class="agenda-title">{row['Nombre']}</div>
                        <div class="agenda-sub">Scout: {row['Scout']}</div>
                        <div class="agenda-sub">Motivo: {row['Motivo']}</div>
                        <div class="agenda-date">📅 {fecha_txt}</div>
                    </div>
                    """, unsafe_allow_html=True)


# =========================================================
# FIN DEL BLOQUE AGENDA
# =========================================================
