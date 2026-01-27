import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import urllib.parse
import re

# --- 1. CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="Elite System Ultra V7", layout="wide", page_icon="🌿")

BRAND_GREEN = "#60b067"
LIGHT_GREEN = "#90ee90"

st.markdown(f"""
    <style>
    /* Fondo de la App en Blanco */
    .stApp {{ background-color: #FFFFFF; color: #1E1E1E; }}
    
    .main-title {{ color: {BRAND_GREEN}; font-size: 32px; font-weight: bold; }}
    
    /* Esmerilado Negro solo para las Tarjetas */
    .turno-card {{
        background: rgba(30, 30, 30, 0.85);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-left: 6px solid {BRAND_GREEN};
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 15px;
        color: white; /* Texto blanco sobre el esmerilado negro */
        box-shadow: 0px 4px 15px rgba(0,0,0,0.1);
    }}
    
    .alerta-renovacion {{
        background-color: {LIGHT_GREEN};
        color: #1a5c1a;
        padding: 6px 12px;
        border-radius: 8px;
        font-weight: bold;
        display: inline-block;
        margin-top: 10px;
        font-size: 12px;
    }}
    
    .disponibilidad-chip {{
        background: rgba(96, 176, 103, 0.1);
        color: {BRAND_GREEN};
        padding: 8px 15px;
        border-radius: 10px;
        border: 1px solid {BRAND_GREEN};
        font-weight: bold;
        text-align: center;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN ---
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

# --- 3. FUNCIONES ---
def calcular_fechas_fijas(fecha_inicio, dias_semana, cantidad):
    dias_map = {"Lunes": 0, "Martes": 1, "Miércoles": 2, "Jueves": 3, "Viernes": 4, "Sábado": 5}
    nums_objetivo = [dias_map[d] for d in dias_semana]
    fechas_generadas = []
    fecha_actual = fecha_inicio
    while len(fechas_generadas) < cantidad:
        if fecha_actual.weekday() in nums_objetivo:
            fechas_generadas.append(str(fecha_actual))
        fecha_actual += timedelta(days=1)
    return fechas_generadas

def obtener_disponibilidad(df_agenda, fecha):
    horas_laborales = ["08:00", "09:00", "10:00", "11:00", "15:00", "16:00", "17:00", "18:00", "19:00"]
    ocupados = df_agenda[df_agenda['Fecha'].astype(str) == str(fecha)]['Hora'].tolist()
    return [h for h in horas_laborales if h not in ocupados]

# --- 4. NAVEGACIÓN ---
with st.sidebar:
    st.markdown(f'<h1 style="color:{BRAND_GREEN};">🌿 ELITE SYSTEM</h1>', unsafe_allow_html=True)
    menu = st.radio("MENÚ", ["📅 Agenda & Turnos", "📝 Registro & Cobro", "📊 Inteligencia Financiera"])

# --- MÓDULO 1: AGENDA & TURNOS ---
if menu == "📅 Agenda & Turnos":
    st.markdown('<p class="main-title">Agenda & Control</p>', unsafe_allow_html=True)
    df_a = cargar_nube("agenda")
    df_p = cargar_nube("pacientes")
    hoy = datetime.now().date()
    
    tab1, tab2 = st.tabs(["🕒 Turnos de Hoy", "🔍 Ver Disponibilidad"])
    
    with tab1:
        t_hoy = df_a[df_a['Fecha'].astype(str) == str(hoy)].sort_values("Hora")
        if t_hoy.empty:
            st.info("No hay turnos para hoy.")
        else:
            for _, t in t_hoy.iterrows():
                # Lógica de sesiones restantes para alertas
                info_p = df_p[df_p['Nombre'] == t['Paciente']]
                restantes = 10 # Default
                if not info_p.empty:
                    restantes = pd.to_numeric(info_p['Sesiones_Restantes'].iloc[0], errors='coerce')
                
                with st.container():
                    c_card, c_btn = st.columns([4, 1])
                    with c_card:
                        st.markdown(f"""
                        <div class="turno-card">
                            <span style="color:{BRAND_GREEN}; font-size:22px; font-weight:bold;">{t['Hora']} hs</span> | {t['Paciente']}<br>
                            <small>{t['Servicio']}</small><br>
                            {"<div class='alerta-renovacion'>♻️ RENOVAR O FINALIZAR TRATAMIENTO</div>" if restantes <= 1 else ""}
                        </div>
                        """, unsafe_allow_html=True)
                    with c_btn:
                        st.write("###")
                        if restantes <= 1:
                            st.button("🛒 Renovar", key=f"renov_{t['Hora']}")
                        else:
                            st.button("⚙️ Modificar", key=f"edit_{t['Hora']}")

    with tab2:
        fecha_disp = st.date_input("Consultar disponibilidad:", hoy)
        libres = obtener_disponibilidad(df_a, fecha_disp)
        cols = st.columns(5)
        for i, h in enumerate(libres):
            cols[i % 5].markdown(f'<div class="disponibilidad-chip">{h}</div>', unsafe_allow_html=True)

# --- MÓDULO 2: REGISTRO (Mantiene toda la lógica V6) ---
elif menu == "📝 Registro & Cobro":
    st.markdown('<p class="main-title">Registro & Ventas</p>', unsafe_allow_html=True)
    df_p = cargar_nube("pacientes")
    
    with st.form("registro_pro"):
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Nombre")
            dni = st.text_input("DNI")
            dx = st.text_area("Dx")
        with c2:
            origen = st.selectbox("Socio?", ["Socio Gimnasio", "Captación Propia"])
            serv = st.selectbox("Servicio", SERVICIOS_DISPONIBLES)
            m_base = st.number_input("Precio Lista", min_value=0)
            
            # Lógica de beneficios integrada
            m_final = m_base
            if serv == "Evaluacion":
                ya_ev = not df_p[(df_p['DNI'].astype(str) == str(dni)) & (df_p['Servicio'] == "Evaluacion")].empty
                if not ya_ev:
                    m_final = 0 if origen == "Socio Gimnasio" else m_base * 0.5
                    st.success(f"Beneficio aplicado: Cobro final ${m_final}")
                else:
                    st.warning("Paciente ya evaluado previamente.")
        
        st.divider()
        f_ini = st.date_input("Inicio", hoy)
        h_ini = st.time_input("Hora", datetime.now().time())
        dias = st.multiselect("Días fijos", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"])
        
        if st.form_submit_button("CONSOLIDAR"):
            cant = 10 if "x10" in serv else (5 if "x5" in serv else 1)
            fechas = calcular_fechas_fijas(f_ini, dias, cant) if dias else [str(f_ini)]
            
            # Guardar
            nuevo_p = pd.DataFrame([[dni, nombre, "", dx, origen, serv, m_final, str(f_ini), cant, cant]], columns=COL_PACIENTES)
            conn.update(worksheet="pacientes", data=pd.concat([df_p, nuevo_p], ignore_index=True))
            
            df_a = cargar_nube("agenda")
            h_str = h_ini.strftime("%H:%M")
            nuevos_t = [[f, h_str, nombre, serv, "PENDIENTE", ""] for f in fechas]
            conn.update(worksheet="agenda", data=pd.concat([df_a, pd.DataFrame(nuevos_t, columns=COL_AGENDA)], ignore_index=True))
            st.rerun()

# --- MÓDULO 3: FINANZAS ---
elif menu == "📊 Inteligencia Financiera":
    st.markdown('<p class="main-title">Finanzas</p>', unsafe_allow_html=True)
    df_f = cargar_nube("pacientes")
    st.dataframe(df_f)
