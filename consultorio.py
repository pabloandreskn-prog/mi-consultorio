import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import plotly.express as px

# --- 1. CONFIGURACIÓN, MATRIZ DE PRECIOS Y ESTILO ---
st.set_page_config(page_title="Elite System Ultra V11", layout="wide", page_icon="🌿")

PRECIOS_BASE = {
    "Evaluacion": 36000,
    "Sesion Especializada": 36000,
    "Sesion Individual": 24000,
    "Plan x5": 110000,
    "Plan x10": 200000,
    "Masaje ZA (piernas y pies)": {"Socio": 25000, "Gral": 30000},
    "Masaje ZB (Espalda y Cabeza)": {"Socio": 25000, "Gral": 30000},
    "Masaje Completo": {"Socio": 38000, "Gral": 45000}
}

BRAND_GREEN = "#60b067"
NEON_GREEN = "#39FF14"

st.markdown(f"""
    <style>
    .stApp {{ background-color: #FFFFFF; color: #1E1E1E; }}
    .main-title {{ color: {BRAND_GREEN}; font-size: 32px; font-weight: bold; }}
    
    /* Tarjeta Esmerilada V11 */
    .turno-card {{
        background: rgba(30, 30, 30, 0.95);
        backdrop-filter: blur(15px);
        border-left: 8px solid {BRAND_GREEN};
        padding: 25px;
        border-radius: 20px;
        margin-bottom: 5px;
        color: white;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0px 10px 30px rgba(0,0,0,0.3);
    }}
    
    /* Área de Trabajo Desplegable */
    .sub-panel {{
        background: rgba(45, 45, 45, 0.5);
        border-radius: 0 0 20px 20px;
        padding: 20px;
        margin-top: -10px;
        margin-bottom: 20px;
        border: 1px solid rgba(255,255,255,0.1);
        border-top: none;
    }}

    /* Botones Pro */
    div.stButton > button {{
        border-radius: 12px !important;
        font-weight: bold !important;
        transition: 0.4s !important;
        height: 45px !important;
    }}
    .btn-renovar > div.stButton > button {{
        background-color: transparent !important;
        color: {NEON_GREEN} !important;
        border: 2px solid {NEON_GREEN} !important;
    }}
    .btn-renovar > div.stButton > button:hover {{
        background-color: {NEON_GREEN} !important;
        color: black !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_nube(pestana):
    try: return conn.read(worksheet=pestana, ttl="0").dropna(how='all')
    except: return pd.DataFrame()

# --- 3. LÓGICA DE NEGOCIO ---
def calcular_pago(servicio, origen, es_primera_ev):
    if "Masaje" in servicio:
        tipo = "Socio" if origen == "Socio Gimnasio" else "Gral"
        return PRECIOS_BASE[servicio][tipo]
    
    precio = PRECIOS_BASE.get(servicio, 0)
    if servicio == "Evaluacion" and es_primera_ev:
        return 0 if origen == "Socio Gimnasio" else precio * 0.5
    return precio

# --- 4. NAVEGACIÓN ---
with st.sidebar:
    st.markdown(f'<h1 style="color:{BRAND_GREEN};">🌿 ELITE SYSTEM</h1>', unsafe_allow_html=True)
    menu = st.radio("MENÚ", ["📅 Agenda & Turnos", "📝 Registro & Cobro", "📊 Inteligencia Financiera"])

# --- MÓDULO 1: AGENDA & TURNOS (CON SUB-PANELES) ---
if menu == "📅 Agenda & Turnos":
    st.markdown('<p class="main-title">Control de Sesiones</p>', unsafe_allow_html=True)
    df_a = cargar_nube("agenda")
    df_p = cargar_nube("pacientes")
    hoy = datetime.now().date()

    t_hoy = df_a[df_a['Fecha'].astype(str) == str(hoy)].sort_values("Hora")
    
    if t_hoy.empty:
        st.info("No hay turnos para hoy.")
    else:
        for _, t in t_hoy.iterrows():
            rest = 10
            if not df_p.empty:
                p_match = df_p[df_p['Nombre'] == t['Paciente']]
                if not p_match.empty:
                    rest = pd.to_numeric(p_match['Sesiones_Restantes'].iloc[-1], errors='coerce')

            # Render de Tarjeta
            st.markdown(f"""
            <div class="turno-card">
                <div>
                    <span style="color:{BRAND_GREEN}; font-size:24px; font-weight:bold;">{t['Hora']} hs</span><br>
                    <span style="font-size:20px;">{t['Paciente']}</span><br>
                    <small style="color:{NEON_GREEN if rest <= 2 else 'white'};">Sesiones restantes: {rest}</small>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Botones con espacio debajo
            c1, c2, c3 = st.columns([1, 1, 2])
            with c1:
                renovar = st.button("🛒 Renovar", key=f"r_{t['Hora']}")
            with c2:
                reagendar = st.button("⚙️ Reagendar", key=f"m_{t['Hora']}")
            
            # SUB-PANELES DINÁMICOS
            if renovar:
                st.markdown('<div class="sub-panel">', unsafe_allow_html=True)
                st.write(f"### Renovación para {t['Paciente']}")
                st.selectbox("Nuevo Plan:", ["Plan x5", "Plan x10"], key=f"sel_{t['Hora']}")
                st.button("Confirmar Pago y Renovar", key=f"conf_{t['Hora']}")
                st.markdown('</div>', unsafe_allow_html=True)
            
            if reagendar:
                st.markdown('<div class="sub-panel">', unsafe_allow_html=True)
                st.write("### Seleccionar Nuevo Horario")
                st.time_input("Nueva Hora:", key=f"time_{t['Hora']}")
                st.button("Actualizar Turno", key=f"upd_{t['Hora']}")
                st.markdown('</div>', unsafe_allow_html=True)

# --- MÓDULO 2: REGISTRO & COBRO (AUTOMATIZADO) ---
elif menu == "📝 Registro & Cobro":
    st.markdown('<p class="main-title">Registro & Venta Automática</p>', unsafe_allow_html=True)
    df_p = cargar_nube("pacientes")
    
    with st.form("registro_v11"):
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Nombre Completo")
            dni = st.text_input("DNI")
            origen = st.selectbox("Origen del Paciente", ["Socio Gimnasio", "Captación Propia"])
        with c2:
            serv = st.selectbox("Servicio / Plan", list(PRECIOS_BASE.keys()))
            
            # Cálculo automático de bonificación
            es_primera_ev = True
            if not df_p.empty and dni:
                es_primera_ev = df_p[(df_p['DNI'].astype(str) == str(dni)) & (df_p['Servicio'] == "Evaluacion")].empty
            
            precio_final = calcular_pago(serv, origen, es_primera_ev)
            st.write(f"## Total a Cobrar: ${precio_final:,.0f}")
            if serv == "Evaluacion" and es_primera_ev:
                st.success("¡Bonificación por primera vez aplicada!")
        
        st.form_submit_button("CONSOLIDAR REGISTRO")

# --- MÓDULO 3: FINANZAS ---
elif menu == "📊 Inteligencia Financiera":
    st.markdown('<p class="main-title">Rendimiento Financiero Elite</p>', unsafe_allow_html=True)
    df_f = cargar_nube("pacientes")
    if not df_f.empty:
        df_f['Pago'] = pd.to_numeric(df_f['Pago'], errors='coerce').fillna(0)
        st.metric("Utilidad Total", f"${df_f['Pago'].sum():,.0f}")
        fig = px.bar(df_f.groupby('Servicio')['Pago'].sum().reset_index(), x='Servicio', y='Pago', color='Pago', color_continuous_scale='Greens')
        st.plotly_chart(fig, use_container_width=True)
