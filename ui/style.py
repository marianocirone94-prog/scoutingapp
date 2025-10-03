import streamlit as st

def load_custom_css():
    st.markdown(
        """
        <style>
        /* ---------------- FONDO APP ---------------- */
        [data-testid="stAppViewContainer"] {
            background-color: #002147 !important; /* Azul Rosario Central oscuro */
        }
        [data-testid="stSidebar"] {
            background-color: #141c2e !important; /* Sidebar */
        }

        /* ---------------- TITULOS ---------------- */
        h1, h2, h3, h4 {
            color: #00c6ff !important; /* Azul eléctrico */
        }

        /* ---------------- BOTONES ---------------- */
        div.stButton > button {
            background: linear-gradient(90deg, #1e3c72, #2a5298);
            color: #fff;
            border: none;
            border-radius: 6px;
            padding: 8px 20px;
            font-weight: 600;
            transition: all 0.2s ease-in-out;
        }
        div.stButton > button:hover {
            transform: scale(1.04);
            box-shadow: 0px 0px 12px rgba(42, 82, 152, 0.6);
        }

        /* ---------------- SLIDER CUSTOM ---------------- */
        /* Track inactivo (fondo de la barra) */
        [data-baseweb="slider"] > div > div:nth-child(2) {
            background-color: #141c2e !important; /* oscuro discreto */
        }
        /* Track activo (parte rellena hasta la bolita) */
        [data-baseweb="slider"] > div > div:nth-child(3) {
            background-color: #00c6ff !important; /* Azul eléctrico */
            height: 4px !important;
        }
        /* Bolita (handler) */
        [data-baseweb="slider"] > div > div:nth-child(4) {
            background-color: #00c6ff !important;
            border: 2px solid #ffffff !important;
            box-shadow: 0 0 6px #00c6ff;
            width: 18px !important;
            height: 18px !important;
        }
        [data-baseweb="slider"] > div > div:nth-child(4):hover {
            box-shadow: 0 0 12px #00c6ff;
        }

        /* Texto del slider */
        .stSlider label, .stSlider span {
            color: #ffffff !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
