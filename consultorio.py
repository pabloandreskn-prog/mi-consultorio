import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import re

# --- 1. CONFIGURACIÓN ESTÉTICA ---
st.set_page_config(page_title="Elite System Cloud", layout="wide", page_icon="🌿")

BRAND_GREEN = "#60b067"
BRAND_BLACK = "#1E1E1E"

st.markdown(f"""
    <style>
    .stApp {{ background-color: #FAFAFA; }}
    [data-testid="stSidebar"] {{ background-color: #FFFFFF; border-right: 1px solid #f0f0f0; }}
    .stButton>button {{ 
        background-color: {BRAND_GREEN}; color: white; border-radius: 12px; 
        border: none; font-weight: bold; width: 100%; padding: 10px;
    }}
    .main-title {{ color: {BRAND_GREEN}; font-size: 28px; font-weight: bold; }}
    div[data-testid="stMetricValue"] {{ color: {BRAND_GREEN}; font-weight: bold; font-size: 24px; }}
    .card {{
        background: white; padding: 15px; border-radius: 15px; 
        border-left: 5px solid {BRAND_GREEN}; margin-bottom: 10px; 
        box-shadow: 0px 2px 5px rgba(0,0,0,0.05);
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN CLOUD ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_nube(pestaña):
    return conn.read(worksheet=pestaña, ttl="0")

# Definición de columnas blindadas para evitar el ValueError de tus imágenes
COL_PACIENTES = ["DNI", "Nombre", "Contacto", "Dx", "Origen", "Servicio", "Pago", "Fecha", "Sesiones_Totales", "Sesiones_Restantes"]
COL_AGENDA = ["Fecha", "Hora", "Paciente", "Servicio", "Estado"]

# --- 3. LÓGICA DE NEGOCIO ---
def calcular_comision(pago, origen):
    tasa = 0.30 if origen == "Socio Gimnasio" else 0.20
    return float(pago) * tasa

def extraer_sesiones(nombre_servicio):
    match = re.search(r'X(\d+)', nombre_servicio, re.IGNORECASE)
    return int(match.group(1)) if match else 1

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown(f'<h1 class="main-title">🌿 ELITE <span style="color:{BRAND_BLACK}; font-weight:normal; font-style:italic;">SYSTEM</span></h1>', unsafe_allow_html=True)
    menu = st.radio("MENÚ", ["📅 Agenda & Turnos", "📝 Registro & Evolución", "📊 Inteligencia Financiera"])

# --- MÓDULO: AGENDA ---
if menu == "📅 Agenda & Turnos":
    st.header("Agenda de Trabajo")
    fecha_ver = st.date_input("Ver Fecha", datetime.now())
    df_agenda = cargar_nube("agenda")
    turnos_dia = df_agenda[df_agenda['Fecha'] == str(fecha_ver)]
    
    st.metric("Turnos", len(turnos_dia))
    if not turnos_dia.empty:
        for i, t in turnos_dia.sort_values(by="Hora").iterrows():
            st.markdown(f"""
                <div class="card">
                    <b style="color:{BRAND_GREEN};">{t['Hora']} hs</b> | <b>{t['Paciente']}</b><br>
                    <small>{t['Servicio']} - {t['Estado']}</small>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Sin turnos agendados.")

# --- MÓDULO: REGISTRO ---
elif menu == "📝 Registro & Evolución":
    st.header("Nueva Atención")
    with st.form("registro_form"):
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Nombre Completo")
            dni = st.text_input("DNI")
        with c2:
            origen = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
            servicio = st.selectbox("Servicio", ["Plan X5", "Plan X10", "Sesión Individual", "Evaluación"])
        
        monto = st.number_input("Cobro ($)", min_value=0.0)
        f_inicio = st.date_input("Fecha", datetime.now())
        h_inicio = st.time_input("Hora", datetime.now().time())
        auto_agenda = st.checkbox("Programar Pack automáticamente")

        if st.form_submit_button("REGISTRAR"):
            cant = extraer_sesiones(servicio)
            # Actualizar Pacientes
            df_p = cargar_nube("pacientes")
            nuevo_p = pd.DataFrame([[dni, nombre, "", "", origen, servicio, monto, str(f_inicio), cant, cant]], columns=COL_PACIENTES)
            conn.update(worksheet="pacientes", data=pd.concat([df_p, nuevo_p], ignore_index=True))
            
            # Generar Turnos
            nuevos_t = []
            if auto_agenda and cant > 1:
                for j in range(cant):
                    f_turno = f_inicio + timedelta(weeks=j) # Ejemplo: 1 sesión por semana
                    nuevos_t.append([str(f_turno), h_inicio.strftime("%H:%M"), nombre, servicio, "PENDIENTE"])
            else:
                nuevos_t.append([str(f_inicio), h_inicio.strftime("%H:%M"), nombre, servicio, "PENDIENTE"])
            
            df_a = cargar_nube("agenda")
            conn.update(worksheet="agenda", data=pd.concat([df_a, pd.DataFrame(nuevos_t, columns=COL_AGENDA)], ignore_index=True))
            st.success("Sincronizado con éxito")
            st.rerun()

# --- MÓDULO: FINANZAS ---
elif menu == "📊 Inteligencia Financiera":
    st.header("Finanzas Cloud")
    df_f = cargar_nube("pacientes")
    if not df_f.empty:
        df_f['Comision'] = df_f.apply(lambda x: calcular_comision(x['Pago'], x['Origen']), axis=1)
        df_f['Neto'] = df_f['Pago'].astype(float) - df_f['Comision']
        st.metric("Utilidad Neta Elite", f"${df_f['Neto'].sum():,.0f}")
        st.dataframe(df_f)
