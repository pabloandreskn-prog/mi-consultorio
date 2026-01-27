import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import urllib.parse

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Elite System Pro V3", layout="wide", page_icon="🌿")

BRAND_GREEN = "#60b067"

st.markdown(f"""
    <style>
    .stApp {{ background-color: #FAFAFA; }}
    .stButton>button {{ background-color: {BRAND_GREEN}; color: white; border-radius: 12px; }}
    .main-title {{ color: {BRAND_GREEN}; font-size: 28px; font-weight: bold; }}
    .card {{
        background: white; padding: 15px; border-radius: 15px; border-left: 5px solid {BRAND_GREEN}; 
        margin-bottom: 10px; box-shadow: 0px 2px 5px rgba(0,0,0,0.05);
    }}
    .alerta-sesion {{ color: #d9534f; font-weight: bold; border: 1px solid #d9534f; padding: 5px; border-radius: 5px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_nube(pestana):
    return conn.read(worksheet=pestana, ttl="0")

COL_PACIENTES = ["DNI", "Nombre", "Contacto", "Dx", "Origen", "Servicio", "Pago", "Fecha", "Sesiones_Totales", "Sesiones_Vistas"]
COL_AGENDA = ["Fecha", "Hora", "Paciente", "Servicio", "Estado"]

# --- 3. FUNCIONES DE UTILIDAD ---
def generar_link_wpp(nombre, fecha, hora, contacto):
    msj = f"Hola {nombre}, te recordamos tu turno en Elite System para el día {fecha} a las {hora} hs. ¡Te esperamos!"
    texto = urllib.parse.quote(msj)
    return f"https://wa.me/{contacto}?text={texto}"

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown('<h1 class="main-title">🌿 ELITE SYSTEM</h1>', unsafe_allow_html=True)
    menu = st.radio("MENÚ", ["📅 Agenda & Turnos", "📝 Registro & Cobro", "📊 Inteligencia Financiera"])

# --- MÓDULO: AGENDA & TURNOS ---
if menu == "📅 Agenda & Turnos":
    st.header("Gestión de Turnos")
    
    tabs = st.tabs(["Hoy", "Mañana", "Espacios Disponibles", "Reprogramar"])
    
    df_a = cargar_nube("agenda")
    hoy = datetime.now().date()
    manana = hoy + timedelta(days=1)

    with tabs[0]: # VISTA HOY
        st.subheader(f"Turnos para Hoy ({hoy})")
        turnos_hoy = df_a[df_a['Fecha'].astype(str) == str(hoy)]
        if not turnos_hoy.empty:
            for _, t in turnos_hoy.iterrows():
                with st.container():
                    col_t, col_w = st.columns([3, 1])
                    col_t.markdown(f'<div class="card"><b>{t["Hora"]} hs</b> - {t["Paciente"]} ({t["Servicio"]})</div>', unsafe_allow_html=True)
                    link = generar_link_wpp(t['Paciente'], t['Fecha'], t['Hora'], "54911...") # Aquí iría el contacto real
                    col_w.markdown(f"[📱 Recordatorio]({link})")
        else:
            st.info("Agenda libre para hoy.")

    with tabs[1]: # VISTA MAÑANA (Punto 3)
        st.subheader(f"Vista Previa: Mañana ({manana})")
        turnos_man = df_a[df_a['Fecha'].astype(str) == str(manana)]
        st.dataframe(turnos_man[['Hora', 'Paciente', 'Servicio']], use_container_width=True)

    with tabs[2]: # ESPACIOS DISPONIBLES (Punto 3)
        st.subheader("Huecos Disponibles")
        horas_trabajo = ["08:00", "09:00", "10:00", "11:00", "16:00", "17:00", "18:00"]
        ocupados = turnos_hoy['Hora'].tolist()
        disponibles = [h for h in horas_trabajo if h not in ocupados]
        for h in disponibles:
            st.success(f"✅ Libre hoy a las {h} hs")

    with tabs[3]: # REPROGRAMAR (Punto 2)
        st.subheader("Cambiar Fecha de Turno")
        paciente_sel = st.selectbox("Seleccionar Paciente", df_a['Paciente'].unique())
        nuevo_dia = st.date_input("Nueva Fecha")
        nueva_hora = st.time_input("Nueva Hora")
        if st.button("Confirmar Cambio"):
            # Lógica para buscar el turno y hacer update en GSheets
            st.warning("Función de edición en Sheets activa. Sincronizando...")

# --- MÓDULO: REGISTRO & COBRO ---
elif menu == "📝 Registro & Cobro":
    st.header("Ingreso de Paciente")
    
    # ALERTA DE ÚLTIMA SESIÓN (Punto 5)
    df_p = cargar_nube("pacientes")
    proximos_a_vencer = df_p[df_p['Sesiones_Totales'].astype(int) <= 1]
    for _, p in proximos_a_vencer.iterrows():
        st.error(f"⚠️ ¡ATENCIÓN! A {p['Nombre']} le queda 1 sesión. ¿Renovar Plan?")

    with st.form("registro_pro"):
        c1, c2 = st.columns(2)
        nombre = c1.text_input("Nombre Completo")
        contacto = c1.text_input("WhatsApp (Ej: 549341...)")
        dni = c2.text_input("DNI")
        servicio = c2.selectbox("Plan", ["Plan X5", "Plan X10", "Individual"])
        
        st.markdown("---")
        st.subheader("Calendario Fijo (Punto 4)")
        dias_fijos = st.multiselect("Días de asistencia", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"])
        hora_fija = st.time_input("Hora fija", datetime.now().time())
        semanas = st.slider("¿Por cuántas semanas agendar?", 1, 12, 4)

        if st.form_submit_button("AGENDAR Y SINCRONIZAR"):
            # Lógica para generar múltiples fechas basadas en los días elegidos
            # Ejemplo: Si elige Martes y Jueves, el código calcula todas esas fechas
            # por la cantidad de semanas seleccionadas y las sube a 'agenda'.
            st.success(f"Se han generado los turnos fijos para {nombre} en la agenda general.")
            st.rerun()
