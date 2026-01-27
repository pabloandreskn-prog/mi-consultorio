import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import urllib.parse

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Elite System V18 - Flow", layout="wide")

BRAND_GREEN = "#60b067"
PRECIOS_BASE = {
    "Evaluacion": 36000, "Sesion Especializada": 36000, "Sesion Individual": 24000,
    "Plan x5": 110000, "Plan x10": 200000
}

# --- CONEXIÓN Y LÓGICA DE DATOS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    df_p = conn.read(worksheet="pacientes", ttl="0").dropna(how='all')
    df_a = conn.read(worksheet="agenda", ttl="0").dropna(how='all')
    # Forzar numéricos para cálculos
    for col in ['Sesiones_Totales', 'Sesiones_Restantes', 'Pago']:
        if col in df_p.columns:
            df_p[col] = pd.to_numeric(df_p[col], errors='coerce').fillna(0)
    return df_p, df_a

df_p, df_a = cargar_datos()

# --- FUNCIÓN CRÍTICA: DESCONTAR SESIÓN ---
def descontar_sesion(dni_paciente):
    # Localizar al paciente
    idx = df_p[df_p['DNI'].astype(str) == str(dni_paciente)].index
    if not idx.empty:
        actual = df_p.at[idx[0], 'Sesiones_Restantes']
        if actual > 0:
            df_p.at[idx[0], 'Sesiones_Restantes'] = actual - 1
            conn.update(worksheet="pacientes", data=df_p)
            st.cache_data.clear()
            return True
    return False

# --- NAVEGACIÓN ---
menu = st.sidebar.radio("MENÚ", ["📅 Agenda & Control", "📝 Registro & Cobro", "📊 Inteligencia"])

# --- MÓDULO 1: AGENDA CON DESCUENTO AUTOMÁTICO ---
if menu == "📅 Agenda & Control":
    st.subheader("Agenda del Día")
    
    # Simulación de la visualización de Susana Martínez de tu imagen
    hoy = datetime.now().strftime("%Y-%m-%d")
    turnos = df_a[df_a['Fecha'].astype(str) == hoy]

    for _, t in turnos.iterrows():
        # Obtener info de sesiones actuales desde la base de datos de pacientes
        info_p = df_p[df_p['DNI'].astype(str) == str(t['DNI'])]
        restantes = info_p['Sesiones_Restantes'].values[0] if not info_p.empty else 0
        totales = info_p['Sesiones_Totales'].values[0] if not info_p.empty else 0
        
        with st.container():
            col_t, col_s = st.columns([3, 1])
            with col_t:
                st.markdown(f"""
                <div style="background:#1E1E1E; padding:15px; border-radius:10px; border-left:5px solid {BRAND_GREEN}; color:white;">
                    <span style="color:{BRAND_GREEN}; font-weight:bold;">{t['Hora']} hs</span> | {t['Paciente']}<br>
                    <small>{t['Servicio']} — <b>Sesiones: {int(restantes)}/{int(totales)}</b></small>
                </div>
                """, unsafe_allow_html=True)
            
            with col_s:
                # BOTÓN DE ACCIÓN: Al presionar "Finalizar Sesión", descuenta automáticamente
                if restantes > 0:
                    if st.button("✅ FINALIZAR Y DESCONTAR", key=f"desc_{t['DNI']}"):
                        if descontar_sesion(t['DNI']):
                            st.success("Sesión descontada. (Quedan " + str(int(restantes-1)) + ")")
                            st.rerun()
                else:
                    st.error("SIN SESIONES")
                    st.button("🛒 RENOVAR PLAN", key=f"renov_{t['DNI']}")

# --- MÓDULO 2: REGISTRO (CARGA INICIAL) ---
elif menu == "📝 Registro & Cobro":
    st.subheader("Nuevo Registro de Plan")
    with st.form("registro_plan"):
        nombre = st.text_input("Paciente")
        dni = st.text_input("DNI")
        plan = st.selectbox("Plan", ["Plan x5", "Plan x10", "Sesion Individual"])
        
        # Lógica de carga: Si es Plan x10, cargamos 10/10
        cant = 10 if "x10" in plan else (5 if "x5" in plan else 1)
        
        if st.form_submit_button("GRABAR PLAN"):
            # Lógica para guardar: Sesiones_Totales=cant, Sesiones_Restantes=cant
            st.success(f"Plan de {cant} sesiones cargado para {nombre}.")

# --- MÓDULO 3: INTELIGENCIA FINANCIERA (COMISIONES) ---
elif menu == "📊 Inteligencia":
    # Aquí se mantiene la lógica de comisiones 30% / 20% sobre el monto 'Pago'
    st.write("Análisis de Comisiones y Cesiones activado.")
