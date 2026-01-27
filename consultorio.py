import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import urllib.parse

# --- 1. CONFIGURACIÓN Y ESTILO AVANZADO ---
st.set_page_config(page_title="Elite System Ultra V7", layout="wide", page_icon="🌿")

BRAND_GREEN = "#60b067"
LIGHT_GREEN = "#90ee90"

st.markdown(f"""
    <style>
    .stApp {{ background-color: #0E1117; color: white; }}
    .main-title {{ color: {BRAND_GREEN}; font-size: 32px; font-weight: bold; }}
    
    /* Efecto Esmerilado Negro (Glassmorphism) */
    .turno-card {{
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-left: 5px solid {BRAND_GREEN};
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 15px;
        transition: 0.3s;
    }}
    .turno-card:hover {{ transform: scale(1.01); background: rgba(255, 255, 255, 0.08); }}
    
    .alerta-renovacion {{
        background-color: {LIGHT_GREEN};
        color: #1a5c1a;
        padding: 8px 15px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
        margin-top: 10px;
        font-size: 13px;
    }}
    
    .disponibilidad-chip {{
        background: rgba(96, 176, 103, 0.2);
        color: {BRAND_GREEN};
        padding: 5px 12px;
        border-radius: 8px;
        border: 1px solid {BRAND_GREEN};
        margin: 5px;
        display: inline-block;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_nube(pestana):
    return conn.read(worksheet=pestana, ttl="0").dropna(how='all')

# --- 3. LÓGICA DE TURNOS DISPONIBLES ---
def obtener_disponibilidad(df_agenda, fecha):
    horas_laborales = ["08:00", "09:00", "10:00", "11:00", "15:00", "16:00", "17:00", "18:00", "19:00"]
    ocupados = df_agenda[df_agenda['Fecha'].astype(str) == str(fecha)]['Hora'].tolist()
    return [h for h in horas_laborales if h not in ocupados]

# --- 4. INTERFAZ ---
with st.sidebar:
    st.markdown(f'<h1 style="color:{BRAND_GREEN};">🌿 ELITE SYSTEM</h1>', unsafe_allow_html=True)
    menu = st.radio("NAVEGACIÓN", ["📅 Agenda & Turnos", "📝 Registro & Cobro", "📊 Inteligencia Financiera"])

if menu == "📅 Agenda & Turnos":
    st.markdown('<p class="main-title">Agenda Inteligente</p>', unsafe_allow_html=True)
    
    df_a = cargar_nube("agenda")
    df_p = cargar_nube("pacientes")
    hoy = datetime.now().date()
    
    tab1, tab2 = st.tabs(["🕒 Turnos del Día", "✨ Disponibilidad de Huecos"])
    
    with tab1:
        t_hoy = df_a[df_a['Fecha'].astype(str) == str(hoy)].sort_values("Hora")
        
        if t_hoy.empty:
            st.info("No hay turnos registrados para hoy.")
        else:
            for _, t in t_hoy.iterrows():
                # Buscar info del paciente para ver sesiones restantes
                info_p = df_p[df_p['Nombre'] == t['Paciente']]
                restantes = int(info_p['Sesiones_Restantes'].iloc[0]) if not info_p.empty else 10
                
                # Renderizado de Card Esmerilada
                with st.container():
                    col_info, col_actions = st.columns([3, 1])
                    
                    with col_info:
                        st.markdown(f"""
                        <div class="turno-card">
                            <span style="color:{BRAND_GREEN}; font-size:20px; font-weight:bold;">{t['Hora']} hs</span><br>
                            <span style="font-size:18px;">{t['Paciente']}</span><br>
                            <small style="color:gray;">{t['Servicio']}</small><br>
                            {"<div class='alerta-renovacion'>♻️ RENOVAR O FINALIZAR TRATAMIENTO</div>" if restantes <= 1 else ""}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col_actions:
                        st.write("") # Espaciador
                        if restantes <= 1:
                            if st.button(f"🛒 Renovar", key=f"ren_{t['Hora']}"):
                                st.switch_page("consultorio.py") # Redirige a registro
                        else:
                            if st.button(f"⚙️ Modificar", key=f"mod_{t['Hora']}"):
                                st.info("Abriendo editor...")

    with tab2:
        st.subheader("Consultar Huecos Libres")
        fecha_consulta = st.date_input("Ver día:", hoy)
        libres = obtener_disponibilidad(df_a, fecha_consulta)
        
        if libres:
            st.write(f"Horas disponibles para el {fecha_consulta}:")
            cols = st.columns(4)
            for i, h in enumerate(libres):
                cols[i % 4].markdown(f'<div class="disponibilidad-chip">🕒 {h}</div>', unsafe_allow_html=True)
        else:
            st.error("Día completo sin disponibilidad.")

elif menu == "📝 Registro & Cobro":
    # Mantenemos la lógica de la V6 con el catálogo ampliado y beneficios
    st.markdown('<p class="main-title">Registro & Ventas</p>', unsafe_allow_html=True)
    # ... (Resto del código de registro V6)
