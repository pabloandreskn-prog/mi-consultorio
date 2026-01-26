import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import re

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Elite System Cloud", layout="wide", page_icon="🌿")

# Estilos corregidos para evitar errores de llaves en HTML
st.markdown("""
    <style>
    .stApp { background-color: #FAFAFA; }
    .main-title { color: #60b067; font-size: 28px; font-weight: bold; }
    .card {
        background: white; padding: 15px; border-radius: 15px; 
        border-left: 5px solid #60b067; margin-bottom: 10px; 
        box-shadow: 0px 2px 5px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN CLOUD (Aquí se resuelve el error de tus imágenes) ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    def cargar_nube(pestana):
        return conn.read(worksheet=pestana, ttl="0")
except Exception as e:
    st.error("Error de conexión: Verifica que el link en 'Secrets' sea correcto.")
    st.stop()

# Columnas exactas para evitar el ValueError de estructura
COL_PACIENTES = ["DNI", "Nombre", "Contacto", "Dx", "Origen", "Servicio", "Pago", "Fecha", "Sesiones_Totales", "Sesiones_Restantes"]
COL_AGENDA = ["Fecha", "Hora", "Paciente", "Servicio", "Estado"]

# --- 3. LÓGICA DE NEGOCIO ---
def extraer_sesiones(nombre_servicio):
    match = re.search(r'X(\d+)', nombre_servicio, re.IGNORECASE)
    return int(match.group(1)) if match else 1

# --- 4. INTERFAZ ---
with st.sidebar:
    st.markdown('<h1 class="main-title">🌿 ELITE SYSTEM</h1>', unsafe_allow_html=True)
    menu = st.radio("MENÚ", ["📅 Agenda & Turnos", "📝 Registro & Evolución", "📊 Inteligencia Financiera"])

if menu == "📅 Agenda & Turnos":
    st.header("Agenda de Hoy")
    fecha_ver = st.date_input("Fecha", datetime.now())
    df_a = cargar_nube("agenda")
    turnos = df_a[df_a['Fecha'].astype(str) == str(fecha_ver)]
    
    if not turnos.empty:
        for _, t in turnos.iterrows():
            # HTML corregido (Líneas 183/196 de tu error anterior)
            st.markdown(f"""
                <div class="card">
                    <b>{t['Hora']} hs</b> | <b>{t['Paciente']}</b><br>
                    <small>{t['Servicio']} - {t['Estado']}</small>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Sin turnos para esta fecha.")

elif menu == "📝 Registro & Evolución":
    st.header("Nueva Atención")
    with st.form("reg"):
        nombre = st.text_input("Nombre")
        dni = st.text_input("DNI")
        # Lista de servicios corregida (Línea 122 de tu error anterior)
        serv = st.selectbox("Servicio", ["Plan X5", "Plan X10", "Sesión Individual", "Evaluación"])
        pago = st.number_input("Pago", min_value=0.0)
        fecha = st.date_input("Fecha", datetime.now())
        hora = st.time_input("Hora", datetime.now().time())
        
        if st.form_submit_button("GUARDAR"):
            cant = extraer_sesiones(serv)
            # Guardar Paciente
            df_p = cargar_nube("pacientes")
            nuevo_p = pd.DataFrame([[dni, nombre, "", "", "Propia", serv, pago, str(fecha), cant, cant]], columns=COL_PACIENTES)
            conn.update(worksheet="pacientes", data=pd.concat([df_p, nuevo_p], ignore_index=True))
            
            # Guardar Turno
            df_a = cargar_nube("agenda")
            nuevo_t = pd.DataFrame([[str(fecha), hora.strftime("%H:%M"), nombre, serv, "PENDIENTE"]], columns=COL_AGENDA)
            conn.update(worksheet="agenda", data=pd.concat([df_a, nuevo_t], ignore_index=True))
            st.success("¡Datos sincronizados!")
            st.rerun()

elif menu == "📊 Inteligencia Financiera":
    st.header("Finanzas")
    df_f = cargar_nube("pacientes")
    if not df_f.empty:
        st.metric("Total Recaudado", f"${df_f['Pago'].astype(float).sum():,.0f}")
        st.dataframe(df_f)
