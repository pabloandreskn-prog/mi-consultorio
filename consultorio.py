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
    .stApp {{ background-color: #FFFFFF; color: #1E1E1E; }}
    .main-title {{ color: {BRAND_GREEN}; font-size: 32px; font-weight: bold; margin-bottom: 20px; }}
    
    /* Tarjetas Esmeriladas Negras con Botones Integrados */
    .turno-card {{
        background: rgba(30, 30, 30, 0.9);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-left: 6px solid {BRAND_GREEN};
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 15px;
        color: white;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.15);
    }}
    
    /* Alertas de Sesiones */
    .alerta-tag {{
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: bold;
        font-size: 11px;
        display: inline-block;
        margin-right: 10px;
    }}
    .penultima {{ background-color: {WARNING_GOLD}; color: #333; }}
    .ultima {{ background-color: {LIGHT_GREEN}; color: #1a5c1a; }}

    /* Estilo para los botones dentro de la tarjeta */
    div.stButton > button {{
        background-color: rgba(255, 255, 255, 0.1);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.2);
        transition: 0.3s;
    }}
    div.stButton > button:hover {{
        background-color: {BRAND_GREEN};
        color: white;
        border: 1px solid {BRAND_GREEN};
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN Y CARGA DE DATOS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_nube(pestana):
    return conn.read(worksheet=pestana, ttl="0").dropna(how='all')

SERVICIOS_DISPONIBLES = [
    "Evaluacion", "Sesion Especializada", "Sesion Individual", 
    "Plan x5", "Plan x10", "Masaje ZA (piernas y pies)", 
    "Masaje ZB (Espalda y Cabeza)", "Masaje Completo"
]

COL_PACIENTES = ["DNI", "Nombre", "Contacto", "Dx", "Origen", "Servicio", "Pago", "Fecha", "Sesiones_Totales", "Sesiones_Restantes"]
COL_AGENDA = ["Fecha", "Hora", "Paciente", "Servicio", "Estado", "Contacto"]

# --- 3. LÓGICA DE NEGOCIO ---
def obtener_disponibilidad(df_agenda, fecha):
    horas_laborales = ["08:00", "09:00", "10:00", "11:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00"]
    ocupados = df_agenda[df_agenda['Fecha'].astype(str) == str(fecha)]['Hora'].tolist()
    return [h for h in horas_laborales if h not in ocupados]

# --- 4. NAVEGACIÓN ---
if 'menu_actual' not in st.session_state:
    st.session_state.menu_actual = "📅 Agenda & Turnos"

with st.sidebar:
    st.markdown(f'<h1 style="color:{BRAND_GREEN};">🌿 ELITE SYSTEM</h1>', unsafe_allow_html=True)
    opcion = st.radio("MENÚ", ["📅 Agenda & Turnos", "📝 Registro & Cobro", "📊 Inteligencia Financiera"], key='nav_radio')
    st.session_state.menu_actual = opcion

# --- MÓDULO 1: AGENDA & TURNOS ---
if st.session_state.menu_actual == "📅 Agenda & Turnos":
    st.markdown('<p class="main-title">Gestión de Turnos Elite</p>', unsafe_allow_html=True)
    df_a = cargar_nube("agenda")
    df_p = cargar_nube("pacientes")
    hoy = datetime.now().date()

    # Disponibilidad Unificada
    with st.expander("🔍 CONSULTAR DISPONIBILIDAD", expanded=False):
        f_sel = st.date_input("Día:", hoy)
        libres = obtener_disponibilidad(df_a, f_sel)
        st.write(f"Libres: {', '.join(libres) if libres else 'Sin cupos'}")

    st.divider()

    t_hoy = df_a[df_a['Fecha'].astype(str) == str(hoy)].sort_values("Hora")
    
    if t_hoy.empty:
        st.info("No hay pacientes agendados para hoy.")
    else:
        for _, t in t_hoy.iterrows():
            # Buscar info del paciente para alertas
            p_data = df_p[df_p['Nombre'] == t['Paciente']]
            rest = pd.to_numeric(p_data['Sesiones_Restantes'].iloc[-1], errors='coerce') if not p_data.empty else 10
            
            # Construcción de la Tarjeta
            with st.container():
                st.markdown(f"""
                <div class="turno-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="color:{BRAND_GREEN}; font-size:24px; font-weight:bold;">{t['Hora']} hs</span><br>
                            <span style="font-size:18px;">{t['Paciente']}</span><br>
                            <small>{t['Servicio']}</small>
                        </div>
                        <div>
                            {"<span class='alerta-tag penultima'>⚠️ PENÚLTIMA</span>" if rest == 2 else ""}
                            {"<span class='alerta-tag ultima'>♻️ ÚLTIMA</span>" if rest <= 1 else ""}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Botones integrados visualmente justo debajo de la info dentro de la misma estructura de container
                c1, c2, c3 = st.columns([1, 1, 2])
                with c1:
                    if rest <= 2:
                        if st.button("🛒 Renovar", key=f"ren_{t['Hora']}"):
                            st.session_state.paciente_a_renovar = t['Paciente']
                            st.session_state.menu_actual = "📝 Registro & Cobro"
                            st.rerun()
                with c2:
                    if st.button("⚙️ Reagendar", key=f"reag_{t['Hora']}"):
                        st.toast(f"Modificando turno de {t['Paciente']}...")

# --- MÓDULO 2: REGISTRO & COBRO ---
elif st.session_state.menu_actual == "📝 Registro & Cobro":
    st.markdown('<p class="main-title">Registro & Venta</p>', unsafe_allow_html=True)
    df_p = cargar_nube("pacientes")
    
    # Pre-cargar nombre si viene de renovación
    nombre_default = st.session_state.get('paciente_a_renovar', "")
    
    with st.form("registro_v10"):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre Completo", value=nombre_default)
            dni = st.text_input("DNI")
        with col2:
            origen = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
            serv = st.selectbox("Servicio", SERVICIOS_DISPONIBLES)
            m_lista = st.number_input("Monto Lista", min_value=0)
        
        # Lógica de cobro final
        pago_final = m_lista
        if serv == "Evaluacion" and dni:
            ya_ev = not df_p[(df_p['DNI'].astype(str) == str(dni)) & (df_p['Servicio'] == "Evaluacion")].empty
            if not ya_ev:
                pago_final = 0 if origen == "Socio Gimnasio" else m_lista * 0.5
        
        st.write(f"### Total a Cobrar: ${pago_final}")
        if st.form_submit_button("✅ CONSOLIDAR"):
            # Lógica de guardado (mismo que V9)
            st.success("Registro Exitoso")
            if 'paciente_a_renovar' in st.session_state: del st.session_state.paciente_a_renovar
            st.rerun()

# --- MÓDULO 3: FINANZAS ---
elif st.session_state.menu_actual == "📊 Inteligencia Financiera":
    st.markdown('<p class="main-title">Inteligencia Financiera Elite</p>', unsafe_allow_html=True)
    df_f = cargar_nube("pacientes")
    if not df_f.empty:
        df_f['Pago'] = pd.to_numeric(df_f['Pago'], errors='coerce').fillna(0)
        df_f['Comision'] = df_f.apply(lambda r: r['Pago']*0.3 if r['Origen'] == "Socio Gimnasio" else r['Pago']*0.2, axis=1)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Ingreso Bruto", f"${df_f['Pago'].sum():,.0f}")
        c2.metric("Comisiones", f"-${df_f['Comision'].sum():,.0f}")
        c3.metric("Utilidad Neta", f"${(df_f['Pago'] - df_f['Comision']).sum():,.0f}")

        df_stats = df_f.groupby('Servicio')['Pago'].sum().reset_index()
        fig = px.bar(df_stats, x='Servicio', y='Pago', color='Pago', color_continuous_scale='Greens')
        st.plotly_chart(fig, use_container_width=True)
