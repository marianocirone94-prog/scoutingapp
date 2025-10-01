import streamlit as st

def kpi_card(title, value):
    st.markdown(
        f"""
        <div class="card">
            <div class="card-title">{title}</div>
            <div class="card-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

def player_card(name, age, position, club, nationality, photo_url):
    st.markdown(
        f"""
        <div class="card" style="display:flex; align-items:center; gap:15px;">
            <img src="{photo_url}" style="width:60px; height:60px; border-radius:50%;">
            <div>
                <div class="card-value">{name} ({age})</div>
                <div>{position} | {club} | {nationality}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
