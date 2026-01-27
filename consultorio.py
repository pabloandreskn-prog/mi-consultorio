import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import plotly.express as px

# --- 1. CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="Elite System Ultra V10", layout="wide", page_icon="🌿")

BRAND_GREEN = "#60b067"
LIGHT_GREEN = "#90ee90"
WARNING_GOLD = "#ffcc00"

st.markdown(f"""
    <style>
    /* Fondo General Blanco */
    .stApp {{ background-color: #FFFFFF; color: #1E1E1E; }}
    
    .main-title {{ color: {BRAND_GREEN}; font-size: 32px; font-weight: bold; margin-bottom: 20px; }}
    
    /* Tarjetas Esmeriladas con Botones Integrados */
    .turno-card {{
        background: rgba(30, 30, 30, 0.9);
        backdrop-filter: blur(10px);
        border-left: 6px solid {BRAND_GREEN};
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 15px;
        color: white;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.15);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    
    .card-info {{ flex-grow: 1; }}
    
    .card-actions {{
        display: flex;
        flex-direction: column;
        gap: 10px;
        min-width: 140px;
    }}

    /* Estilo de Alertas Internas */
    .alerta-badge {{
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: bold;
        font-size: 11px;
        display: inline-block;
        margin-top: 8px;
    }}
    .penultima {{ background-color: {WARNING_GOLD}; color: #333; }}
    .ultima {{ background-color: {LIGHT_GREEN}; color: #1a5c1a; }}

    /* Sobreescribir Botones de Streamlit para que parezcan integrados */
    div.stButton > button {{
        width: 100%;
        background-color: rgba(255,255,255,0.1) !important;
        color: white !important;
        border: 1px solid rgba(255,255,255,0.3) !important;
        border-radius: 8px !important;
        font-size: 12px !important;
        transition: 0.3s;
    }}
    div.stButton > button:hover {{
        background-color: {BRAND_GREEN} !important;
        border-color: {BRAND_GREEN} !important;
    }}
    
    .chip-libre {{
        background: rgba(96, 176, 103, 0.1);
        color: {BRAND_GREEN};
        padding: 8px;
        border-radius: 10px;
        border: 1px solid {BRAND_GREEN};
        font-weight: bold;
        text-align: center;
        margin-bottom: 5px;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_nube(pestana):
    try:
        return conn.read(worksheet=pestana, ttl="0").dropna(how='all')
    except:
        return pd.DataFrame()

# --- 3. LÓGICA DE TURNOS ---
def obtener_disponibilidad(df_agenda, fecha):
    horas_laborales = ["08:00", "09:00", "10:00", "11:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00"]
    if df_agenda.empty: return horas_laborales
    ocupados = df_agenda[df_agenda['Fecha'].astype(str) == str(fecha)]['Hora'].tolist()
    return [h for h in horas_laborales if h not in ocupados]

# --- 4. NAVEGACIÓN ---
with st.sidebar:
    st.markdown(f'<h1 style="color:{BRAND_GREEN};">🌿 ELITE SYSTEM</h1>', unsafe_allow_html=True)
    menu = st.radio("MENÚ", ["📅 Agenda & Turnos", "📝 Registro & Cobro", "📊 Inteligencia Financiera"])

# --- MÓDULO 1: AGENDA & TURNOS (DISEÑO INTEGRADO) ---
if menu == "📅 Agenda & Turnos":
    st.markdown('<p class="main-title">Agenda Elite</p>', unsafe_allow_html=True)
    df_a = cargar_nube("agenda")
    df_p = cargar_nube("pacientes")
    hoy = datetime.now().date()

    # Disponibilidad Integrada
    with st.expander("🔍 CONSULTAR DISPONIBILIDAD (HUECOS LIBRES)", expanded=False):
        c_f, _ = st.columns([1, 2])
        f_sel = c_f.date_input("Día:", hoy)
        libres = obtener_disponibilidad(df_a, f_sel)
        cols = st.columns(5)
        for i, h in enumerate(libres):
            cols[i % 5].markdown(f'<div class="chip-libre">{h}</div>', unsafe_allow_html=True)

    st.divider()

    t_hoy = df_a[df_a['Fecha'].astype(str) == str(hoy)].sort_values("Hora")
    
    if t_hoy.empty:
        st.info("No hay turnos para hoy.")
    else:
        for _, t in t_hoy.iterrows():
            # Obtener datos de sesiones
            rest = 10
            if not df_p.empty:
                p_match = df_p[df_p['Nombre'] == t['Paciente']]
                if not p_match.empty:
                    rest = pd.to_numeric(p_match['Sesiones_Restantes'].iloc[-1], errors='coerce')

            # Renderizado de Tarjeta Integrada
            with st.container():
                # Creamos el diseño visual con HTML
                alerta_html = ""
                if rest == 2: alerta_html = f"<div class='alerta-badge penultima'>⚠️ PENÚLTIMA SESIÓN</div>"
                elif rest <= 1: alerta_html = f"<div class='alerta-badge ultima'>♻️ ÚLTIMA SESIÓN</div>"

                # Abrimos contenedor de la tarjeta
                st.markdown(f"""
                <div class="turno-card">
                    <div class="card-info">
                        <span style="color:{BRAND_GREEN}; font-size:22px; font-weight:bold;">{t['Hora']} hs</span><br>
                        <span style="font-size:18px;">{t['Paciente']}</span><br>
                        <small style="opacity:0.8;">{t['Servicio']}</small><br>
                        {alerta_html}
                    </div>
                """, unsafe_allow_html=True)
                
                # Insertamos los botones de Streamlit en la sección de acciones de la tarjeta
                c_btn1, c_btn2 = st.columns([4, 1]) # Espaciador para alinear botones a la derecha
                with c_btn2:
                    if rest <= 2:
                        if st.button("🛒 Renovar", key=f"ren_{t['Hora']}_{t['Paciente']}"):
                            st.toast(f"Renovación para {t['Paciente']}")
                    if st.button("⚙️ Reagendar", key=f"mod_{t['Hora']}_{t['Paciente']}"):
                        st.toast("Cambiando turno...")
                
                st.markdown("</div>", unsafe_allow_html=True) # Cerramos el div de la tarjeta

# --- MÓDULO 2: REGISTRO & COBRO (FUNCIONAL V9) ---
elif menu == "📝 Registro & Cobro":
    st.markdown('<p class="main-title">Registro & Venta</p>', unsafe_allow_html=True)
    df_p = cargar_nube("pacientes")
    with st.form("form_v10"):
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Nombre")
            dni = st.text_input("DNI")
            dx = st.text_area("Dx")
        with c2:
            origen = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
            serv = st.selectbox("Servicio", ["Evaluacion", "Sesion Individual", "Plan x5", "Plan x10"])
            m_lista = st.number_input("Precio Lista", min_value=0)
            pago_f = m_lista
            if serv == "Evaluacion" and not df_p.empty:
                if df_p[(df_p['DNI'].astype(str) == str(dni)) & (df_p['Servicio'] == "Evaluacion")].empty:
                    pago_f = 0 if origen == "Socio Gimnasio" else m_lista * 0.5
            st.write(f"### Cobro: ${pago_f}")
        
        st.form_submit_button("CONSOLIDAR")

# --- MÓDULO 3: FINANZAS (FUNCIONAL V9) ---
elif menu == "📊 Inteligencia Financiera":
    st.markdown('<p class="main-title">Finanzas</p>', unsafe_allow_html=True)
    df_f = cargar_nube("pacientes")
    if not df_f.empty:
        df_f['Pago'] = pd.to_numeric(df_f['Pago'], errors='coerce').fillna(0)
        df_stats = df_f.groupby('Servicio')['Pago'].sum().reset_index()
        fig = px.bar(df_stats, x='Servicio', y='Pago', color='Pago', color_continuous_scale='Greens')
        st.plotly_chart(fig, use_container_width=True)
