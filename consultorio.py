import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import re

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Elite System Cloud", layout="wide", page_icon="🌿")

BRAND_GREEN = "#60b067"
BRAND_BLACK = "#1E1E1E"

st.markdown(f"""
    <style>
    .stApp {{ background-color: #FAFAFA; }}
    .stButton>button {{ 
        background-color: {BRAND_GREEN}; color: white; border-radius: 12px; border: none; font-weight: bold; width: 100%;
    }}
    .main-title {{ color: {BRAND_GREEN}; font-size: 28px; font-weight: bold; }}
    .card {{
        background: white; padding: 15px; border-radius: 15px; border-left: 5px solid {BRAND_GREEN}; margin-bottom: 10px; box-shadow: 0px 2px 5px rgba(0,0,0,0.05);
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_nube(pestana):
    # Trae los datos siempre actualizados (ttl=0)
    return conn.read(worksheet=pestana, ttl="0")

# Columnas exactas para evitar el ValueError
COL_PACIENTES = ["DNI", "Nombre", "Contacto", "Dx", "Origen", "Servicio", "Pago", "Fecha", "Sesiones_Totales", "Sesiones_Restantes"]
COL_AGENDA = ["Fecha", "Hora", "Paciente", "Servicio", "Estado"]

# --- 3. LÓGICA ---
def calcular_comision(pago, origen):
    tasa = 0.30 if origen == "Socio Gimnasio" else 0.20
    return float(pago) * tasa

def extraer_sesiones(nombre_servicio):
    match = re.search(r'X(\d+)', nombre_servicio, re.IGNORECASE)
    return int(match.group(1)) if match else 1

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown(f'<h1 class="main-title">🌿 ELITE SYSTEM</h1>', unsafe_allow_html=True)
    menu = st.radio("MENÚ", ["📅 Agenda & Turnos", "📝 Registro & Evolución", "📊 Inteligencia Financiera"])

# --- MÓDULO: AGENDA ---
if menu == "📅 Agenda & Turnos":
    st.header("Agenda del Día")
    fecha_ver = st.date_input("Seleccionar Fecha", datetime.now())
    df_agenda = cargar_nube("agenda")
    
    # Filtramos por fecha
    turnos_dia = df_agenda[df_agenda['Fecha'].astype(str) == str(fecha_ver)]
    
    st.metric("Total Turnos", len(turnos_dia))
    if not turnos_dia.empty:
        for i, t in turnos_dia.sort_values(by="Hora").iterrows():
            st.markdown(f"""<div class="card">
                <b>{t['Hora']} hs</b> | <b>{t['Paciente']}</b><br>
                <small>{t['Servicio']} - {t['Estado']}</small>
            </div>""", unsafe_allow_html=True)
    else:
        st.info("No hay turnos para hoy.")

# --- MÓDULO: REGISTRO ---
elif menu == "📝 Registro & Evolución":
    st.header("Cargar Nueva Atención")
    with st.form("registro_form"):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre Completo")
            dni = st.text_input("DNI")
            contacto = st.text_input("WhatsApp")
        with col2:
            origen = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
            servicio = st.selectbox("Servicio", ["Plan X5", "Plan X10", "Sesión Individual", "Evaluación"])
        
        monto = st.number_input("Pago Recibido ($)", min_value=0.0)
        f_inicio = st.date_input("Fecha de inicio", datetime.now())
        h_inicio = st.time_input("Hora del turno", datetime.now().time())
        auto_agenda = st.checkbox("Programar resto de sesiones automáticamente")

        if st.form_submit_button("GUARDAR EN NUBE"):
            if not nombre or not dni:
                st.error("Nombre y DNI son obligatorios")
            else:
                cant = extraer_sesiones(servicio)
                # 1. Guardar Paciente
                df_p = cargar_nube("pacientes")
                nuevo_p = pd.DataFrame([[dni, nombre, contacto, "", origen, servicio, monto, str(f_inicio), cant, cant]], columns=COL_PACIENTES)
                conn.update(worksheet="pacientes", data=pd.concat([df_p, nuevo_p], ignore_index=True))
                
                # 2. Guardar Turnos
                nuevos_t_list = []
                if auto_agenda and cant > 1:
                    for j in range(cant):
                        f_turno = f_inicio + timedelta(weeks=j)
                        nuevos_t_list.append([str(f_turno), h_inicio.strftime("%H:%M"), nombre, servicio, "PENDIENTE"])
                else:
                    nuevos_t_list.append([str(f_inicio), h_inicio.strftime("%H:%M"), nombre, servicio, "PENDIENTE"])
                
                df_a = cargar_nube("agenda")
                conn.update(worksheet="agenda", data=pd.concat([df_a, pd.DataFrame(nuevos_t_list, columns=COL_AGENDA)], ignore_index=True))
                
                st.success(f"¡Atención de {nombre} registrada exitosamente!")
                st.rerun()

# --- MÓDULO: FINANZAS ---
elif menu == "📊 Inteligencia Financiera":
    st.header("Análisis de Ingresos")
    df_f = cargar_nube("pacientes")
    if not df_f.empty:
        df_f['Comision'] = df_f.apply(lambda x: calcular_comision(x['Pago'], x['Origen']), axis=1)
        df_f['Neto'] = df_f['Pago'].astype(float) - df_f['Comision']
        
        c1, c2 = st.columns(2)
        c1.metric("Bruto Total", f"${df_f['Pago'].sum():,.0f}")
        c2.metric("Utilidad Elite", f"${df_f['Neto'].sum():,.0f}")
        st.dataframe(df_f)
