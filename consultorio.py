import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import re

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Elite System Pro V2", layout="wide", page_icon="🌿")

BRAND_GREEN = "#60b067"
BRAND_BLACK = "#1E1E1E"

st.markdown(f"""
    <style>
    .stApp {{ background-color: #FAFAFA; }}
    [data-testid="stSidebar"] {{ background-color: #FFFFFF; border-right: 1px solid #f0f0f0; }}
    .stButton>button {{ 
        background-color: {BRAND_GREEN}; color: white; border-radius: 12px; font-weight: bold; width: 100%;
    }}
    .main-title {{ color: {BRAND_GREEN}; font-size: 28px; font-weight: bold; }}
    .card {{
        background: white; padding: 15px; border-radius: 15px; border-left: 5px solid {BRAND_GREEN}; 
        margin-bottom: 10px; box-shadow: 0px 2px 5px rgba(0,0,0,0.05);
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN CLOUD ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_nube(pestana):
    return conn.read(worksheet=pestana, ttl="0")

# Estructura de Columnas (Asegúrate de que tu Excel las tenga así)
COL_PACIENTES = ["DNI", "Nombre", "Contacto", "Dx", "Origen", "Servicio", "Pago", "Fecha", "Sesiones_Totales"]
COL_AGENDA = ["Fecha", "Hora", "Paciente", "Servicio", "Estado"]

# --- 3. LÓGICA DE NEGOCIO ---
def calcular_comision(pago, origen):
    try:
        pago_f = float(pago)
        tasa = 0.30 if origen == "Socio Gimnasio" else 0.20
        return pago_f * tasa
    except: return 0.0

def extraer_cantidad_sesiones(servicio):
    if "X5" in servicio: return 5
    if "X10" in servicio: return 10
    return 1

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown(f'<h1 class="main-title">🌿 ELITE SYSTEM</h1>', unsafe_allow_html=True)
    menu = st.radio("MENÚ", ["📅 Agenda & Turnos", "📝 Registro & Cobro", "📊 Inteligencia Financiera"])
    st.divider()
    if st.button("📱 Enviar Recordatorios"):
        st.toast("Recordatorios listos para procesar")

# --- MÓDULO: AGENDA ---
if menu == "📅 Agenda & Turnos":
    st.header("Gestión de Turnos")
    fecha_ver = st.date_input("Fecha", datetime.now())
    df_a = cargar_nube("agenda")
    turnos = df_a[df_a['Fecha'].astype(str) == str(fecha_ver)]
    
    col1, col2 = st.columns([2, 1])
    with col1:
        if not turnos.empty:
            for _, t in turnos.sort_values(by="Hora").iterrows():
                st.markdown(f"""
                    <div class="card">
                        <span style="color:{BRAND_GREEN}; font-weight:bold;">{t['Hora']} hs</span> | 
                        <b>{t['Paciente']}</b><br>
                        <small>{t['Servicio']} - {t['Estado']}</small>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Sin turnos para hoy.")

# --- MÓDULO: REGISTRO ---
elif menu == "📝 Registro & Cobro":
    st.header("Nueva Atención y Pack")
    with st.form("reg_form"):
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Nombre Completo")
            dni = st.text_input("DNI")
            whatsapp = st.text_input("WhatsApp (Sin 0 ni 15)")
        with c2:
            servicio = st.selectbox("Servicio", ["Plan X5", "Plan X10", "Sesión Individual", "Evaluación"])
            origen = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
            monto = st.number_input("Cobro Total ($)", min_value=0.0)
        
        st.divider()
        c3, c4 = st.columns(2)
        f_inicio = c3.date_input("Fecha Inicio", datetime.now())
        h_inicio = c4.time_input("Hora de Sesión", datetime.now().time())
        
        usar_pack = st.checkbox("Programar Pack Completo (Semanal)")

        if st.form_submit_button("REGISTRAR Y SINCRONIZAR"):
            if nombre and dni:
                cant = extraer_cantidad_sesiones(servicio)
                
                # 1. Guardar Paciente
                df_p = cargar_nube("pacientes")
                nuevo_p = pd.DataFrame([[dni, nombre, whatsapp, "", origen, servicio, monto, str(f_inicio), cant]], columns=COL_PACIENTES)
                df_p_final = pd.concat([df_p, nuevo_p], ignore_index=True)
                conn.update(worksheet="pacientes", data=df_p_final)
                
                # 2. Generar Agenda Automática (Lógica de packs recuperada)
                lista_t = []
                for i in range(cant):
                    # Si es pack, suma 1 semana a cada sesión
                    f_sesion = f_inicio + timedelta(weeks=i) if usar_pack else f_inicio
                    lista_t.append([str(f_sesion), h_inicio.strftime("%H:%M"), nombre, servicio, "PENDIENTE"])
                
                df_a = cargar_nube("agenda")
                df_a_nueva = pd.concat([df_a, pd.DataFrame(lista_t, columns=COL_AGENDA)], ignore_index=True)
                conn.update(worksheet="agenda", data=df_a_nueva)
                
                st.success(f"¡Sincronizado! {cant} sesiones agendadas para {nombre}.")
                st.rerun()

# --- MÓDULO: FINANZAS ---
elif menu == "📊 Inteligencia Financiera":
    st.header("Análisis de Ingresos Cloud")
    df_f = cargar_nube("pacientes")
    
    if not df_f.empty:
        # Recuperamos el cálculo de utilidad neta y comisiones
        df_f['Comision'] = df_f.apply(lambda x: calcular_comision(x['Pago'], x['Origen']), axis=1)
        df_f['Neto'] = df_f['Pago'].astype(float) - df_f['Comision']
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Ingresos Brutos", f"${df_f['Pago'].sum():,.0f}")
        m2.metric("Comisiones Cedidas", f"-${df_f['Comision'].sum():,.0f}")
        m3.metric("Utilidad Neta Elite", f"${df_f['Neto'].sum():,.0f}")
        
        st.subheader("Historial Completo")
        st.dataframe(df_f, use_container_width=True)
