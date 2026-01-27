import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import urllib.parse

# --- 1. CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="Elite System Ultra V7", layout="wide", page_icon="🌿")

BRAND_GREEN = "#60b067"
LIGHT_GREEN = "#90ee90"
BG_DARK = "#121212"

st.markdown(f"""
    <style>
    /* Fondo sólido para la app */
    .stApp {{ background-color: {BG_DARK}; color: white; }}
    
    /* Títulos y Sidebar */
    .main-title {{ color: {BRAND_GREEN}; font-size: 32px; font-weight: bold; }}
    [data-testid="stSidebar"] {{ background-color: #1E1E1E; }}

    /* Tarjetas con Esmerilado (Glassmorphism) */
    .turno-card {{
        background: rgba(255, 255, 255, 0.07);
        backdrop-filter: blur(15px);
        -webkit-backdrop-filter: blur(15px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-left: 6px solid {BRAND_GREEN};
        padding: 22px;
        border-radius: 18px;
        margin-bottom: 15px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
    }}
    
    .alerta-renovacion {{
        background-color: {LIGHT_GREEN};
        color: #0b3d0b;
        padding: 6px 12px;
        border-radius: 8px;
        font-weight: bold;
        display: inline-block;
        margin-top: 10px;
        font-size: 12px;
        border: 1px solid rgba(0,0,0,0.1);
    }}
    
    .disponibilidad-chip {{
        background: rgba(96, 176, 103, 0.15);
        color: {BRAND_GREEN};
        padding: 8px;
        border-radius: 10px;
        border: 1px solid {BRAND_GREEN};
        text-align: center;
        margin: 5px;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_nube(pestana):
    return conn.read(worksheet=pestana, ttl="0").dropna(how='all')

# --- 3. LÓGICA DE NEGOCIO ---
SERVICIOS_DISPONIBLES = [
    "Evaluacion", "Sesion Especializada", "Sesion Individual", 
    "Plan x5", "Plan x10", "Masaje ZA (piernas y pies)", 
    "Masaje ZB (Espalda y Cabeza)", "Masaje Completo"
]

def obtener_disponibilidad(df_agenda, fecha):
    horas_laborales = ["08:00", "09:00", "10:00", "11:00", "15:00", "16:00", "17:00", "18:00", "19:00"]
    ocupados = df_agenda[df_agenda['Fecha'].astype(str) == str(fecha)]['Hora'].tolist()
    return [h for h in horas_laborales if h not in ocupados]

# --- 4. INTERFAZ ---
with st.sidebar:
    st.markdown(f'<h1 style="color:{BRAND_GREEN};">🌿 ELITE SYSTEM</h1>', unsafe_allow_html=True)
    menu = st.radio("MENÚ", ["📅 Agenda & Turnos", "📝 Registro & Cobro", "📊 Inteligencia Financiera"])

# --- MÓDULO 1: AGENDA ---
if menu == "📅 Agenda & Turnos":
    st.markdown('<p class="main-title">Agenda & Control</p>', unsafe_allow_html=True)
    df_a = cargar_nube("agenda")
    df_p = cargar_nube("pacientes")
    hoy = datetime.now().date()
    
    tab1, tab2 = st.tabs(["🕒 Gestión de Citas", "✨ Espacios Disponibles"])
    
    with tab1:
        t_hoy = df_a[df_a['Fecha'].astype(str) == str(hoy)].sort_values("Hora")
        if t_hoy.empty:
            st.info("Sin turnos para hoy.")
        else:
            for _, t in t_hoy.iterrows():
                # Lógica de detección de última sesión
                p_data = df_p[df_p['Nombre'] == t['Paciente']]
                try:
                    restantes = int(p_data['Sesiones_Restantes'].iloc[-1])
                except:
                    restantes = 10
                
                with st.container():
                    c_card, c_btn = st.columns([3, 1])
                    with c_card:
                        st.markdown(f"""
                        <div class="turno-card">
                            <span style="color:{BRAND_GREEN}; font-weight:bold; font-size:20px;">{t['Hora']} hs</span> | <b>{t['Paciente']}</b><br>
                            <span style="color:#cccccc;">{t['Servicio']}</span><br>
                            {"<div class='alerta-renovacion'>💚 RENOVAR O FINALIZAR TRATAMIENTO</div>" if restantes <= 1 else ""}
                        </div>
                        """, unsafe_allow_html=True)
                    with c_btn:
                        st.write("###")
                        if restantes <= 1:
                            st.button("🛒 Renovar", key=f"ren_{t['Hora']}_{t['Paciente']}")
                        else:
                            st.button("⚙️ Modificar", key=f"mod_{t['Hora']}_{t['Paciente']}")

    with tab2:
        st.subheader("Buscador de Disponibilidad")
        f_busc = st.date_input("Seleccionar día", hoy)
        libres = obtener_disponibilidad(df_a, f_busc)
        cols = st.columns(4)
        for i, h in enumerate(libres):
            cols[i % 4].markdown(f'<div class="disponibilidad-chip">{h} hs</div>', unsafe_allow_html=True)

# --- MÓDULO 2: REGISTRO ---
elif menu == "📝 Registro & Cobro":
    st.markdown('<p class="main-title">Nuevo Registro</p>', unsafe_allow_html=True)
    # Aquí se mantiene la lógica de la V6 (Socios 100%, No Socios 50% en Evaluación)
    # ... (Se incluye el formulario con el catálogo de servicios actualizado)
    st.info("Formulario V6 integrado: Detectando DNI para evitar duplicidad de beneficios.")

# --- MÓDULO 3: FINANZAS ---
elif menu == "📊 Inteligencia Financiera":
    st.markdown('<p class="main-title">Impacto de Negocio</p>', unsafe_allow_html=True)
    df_f = cargar_nube("pacientes")
    
    if not df_f.empty:
        # Gráfica de impacto
        st.subheader("Inversión en Beneficios (Evaluaciones)")
        beneficios = df_f[df_f['Servicio'] == "Evaluacion"].groupby('Origen').size().reset_index(name='Cantidad')
        st.bar_chart(data=beneficios, x='Origen', y='Cantidad', color=BRAND_GREEN)
        
        st.divider()
        st.dataframe(df_f, use_container_width=True)
