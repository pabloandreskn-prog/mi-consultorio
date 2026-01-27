import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import urllib.parse
import re

# --- 1. CONFIGURACIÓN ESTÉTICA ---
st.set_page_config(page_title="Elite System Ultra V5", layout="wide", page_icon="🌿")
BRAND_GREEN = "#60b067"

st.markdown(f"""
    <style>
    .stApp {{ background-color: #FAFAFA; }}
    .stButton>button {{ background-color: {BRAND_GREEN}; color: white; border-radius: 12px; font-weight: bold; height: 3em; }}
    .main-title {{ color: {BRAND_GREEN}; font-size: 32px; font-weight: bold; margin-bottom: 20px; }}
    .card {{
        background: white; padding: 20px; border-radius: 15px; border-left: 5px solid {BRAND_GREEN}; 
        margin-bottom: 15px; box-shadow: 0px 4px 10px rgba(0,0,0,0.03);
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_nube(pestana):
    return conn.read(worksheet=pestana, ttl="0").dropna(how='all')

# Definición de columnas para asegurar el orden al guardar
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

# --- 4. INTERFAZ ---
with st.sidebar:
    st.markdown('<h1 style="color:#60b067;">🌿 ELITE SYSTEM</h1>', unsafe_allow_html=True)
    menu = st.radio("NAVEGACIÓN", ["📅 Agenda & Turnos", "📝 Registro & Cobro", "📊 Inteligencia Financiera"])

if menu == "📅 Agenda & Turnos":
    st.markdown('<p class="main-title">Control de Agenda</p>', unsafe_allow_html=True)
    df_a = cargar_nube("agenda")
    hoy = datetime.now().date()
    
    tab1, tab2 = st.tabs(["🕒 Turnos de Hoy", "✨ Disponibilidad"])
    
    with tab1:
        t_hoy = df_a[df_a['Fecha'].astype(str) == str(hoy)]
        if t_hoy.empty: st.info("No hay turnos para hoy.")
        for _, t in t_hoy.sort_values("Hora").iterrows():
            st.markdown(f'<div class="card"><b>{t["Hora"]} hs</b> | {t["Paciente"]}<br><small>{t["Servicio"]}</small></div>', unsafe_allow_html=True)

elif menu == "📝 Registro & Cobro":
    st.markdown('<p class="main-title">Registro & Ventas</p>', unsafe_allow_html=True)
    df_p = cargar_nube("pacientes")
    
    with st.form("form_alta", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre del Paciente")
            dni = st.text_input("DNI")
            wpp = st.text_input("WhatsApp (ej. 549341...)")
            dx = st.text_area("Diagnóstico (Dx)", placeholder="Ej: Lumbalgia crónica / Post-operatorio")
        
        with col2:
            origen = st.selectbox("¿Es Socio?", ["Socio Gimnasio", "Captación Propia", "Convenio"])
            serv = st.selectbox("Servicio / Plan", ["Sesión Individual", "Plan X5", "Plan X10", "Masaje"])
            monto = st.number_input("Cobro Total ($)", min_value=0)
        
        st.markdown("---")
        st.subheader("📅 Configuración de Turnos")
        c_f1, c_f2 = st.columns(2)
        fecha_ini = c_f1.date_input("Fecha de inicio", datetime.now())
        # Capturamos la hora y la convertimos a string inmediatamente
        hora_sel = c_f2.time_input("Hora del turno", datetime.now().time())
        hora_str = hora_sel.strftime("%H:%M")
        
        dias_fijos = st.multiselect("Días fijos (solo para Planes)", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])
        
        if st.form_submit_button("CONSOLIDAR REGISTRO"):
            if not nombre or not dni:
                st.error("Nombre y DNI son obligatorios.")
            else:
                cant = 10 if "X10" in serv else (5 if "X5" in serv else 1)
                fechas_t = calcular_fechas_fijas(fecha_ini, dias_fijos, cant) if (dias_fijos and cant > 1) else [str(fecha_ini)]
                
                # 1. Guardar Paciente (Incluye Dx y Origen)
                nuevo_p = pd.DataFrame([[dni, nombre, wpp, dx, origen, serv, monto, str(fecha_ini), cant, cant]], columns=COL_PACIENTES)
                conn.update(worksheet="pacientes", data=pd.concat([df_p, nuevo_p], ignore_index=True))
                
                # 2. Guardar Agenda (Usa hora_str calculada arriba)
                df_a = cargar_nube("agenda")
                nuevos_turnos = [[f, hora_str, nombre, serv, "PENDIENTE", wpp] for f in fechas_t]
                df_a_final = pd.concat([df_a, pd.DataFrame(nuevos_turnos, columns=COL_AGENDA)], ignore_index=True)
                conn.update(worksheet="agenda", data=df_a_final)
                
                st.balloons()
                st.success(f"¡Sincronizado! Se agendaron {len(nuevos_turnos)} sesiones a las {hora_str} hs.")
                st.rerun()

elif menu == "📊 Inteligencia Financiera":
    st.markdown('<p class="main-title">Métricas</p>', unsafe_allow_html=True)
    df_f = cargar_nube("pacientes")
    st.dataframe(df_f, use_container_width=True)
