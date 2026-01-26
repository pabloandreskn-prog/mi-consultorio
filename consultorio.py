import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN ESTÉTICA (ELITE SYSTEM) ---
st.set_page_config(page_title="Elite System Pro", layout="wide", page_icon="🌿")

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
    .main-title {{ color: {BRAND_GREEN}; font-size: 30px; font-weight: bold; }}
    div[data-testid="stMetricValue"] {{ color: {BRAND_GREEN}; font-weight: bold; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. GESTIÓN DE DATOS ---
if not os.path.exists('data'):
    os.makedirs('data')

def cargar_datos(archivo, columnas):
    path = f'data/{{archivo}}.csv'
    if not os.path.exists(path):
        pd.DataFrame(columns=columnas).to_csv(path, index=False)
    return pd.read_csv(path)

df_pacientes = cargar_datos('pacientes', ["DNI", "Nombre", "Contacto", "Dx", "Origen", "Servicio", "Pago", "Fecha", "Sesiones"])
df_agenda = cargar_datos('agenda', ["Fecha", "Hora", "Paciente", "Servicio"])

# --- 3. LÓGICA DE NEGOCIO ---
def calcular_comision(pago, origen):
    tasa = 0.30 if origen == "Socio Gimnasio" else 0.20
    return pago * tasa

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown(f'<h1 class="main-title">🌿 ELITE <span style="color:{BRAND_BLACK}; font-weight:normal; font-style:italic;">SYSTEM</span></h1>', unsafe_allow_html=True)
    st.caption("CONSULTORIO PRO V1.1")
    st.divider()
    menu = st.radio("MENÚ", ["📅 Agenda & Turnos", "📝 Registro & Cobro", "📊 Inteligencia Financiera"])
    
    st.divider()
    if st.button("📱 Generar Recordatorios"):
        st.toast("Links de WhatsApp generados con éxito")

# --- MÓDULO: AGENDA ---
if menu == "📅 Agenda & Turnos":
    st.header("Agenda de Trabajo")
    col_f1, col_f2 = st.columns([1, 1])
    with col_f1:
        fecha_ver = st.date_input("Ver Fecha", datetime.now())
    
    turnos_dia = df_agenda[df_agenda['Fecha'] == str(fecha_ver)]
    
    with col_f2:
        st.metric("Turnos para hoy", len(turnos_dia))

    if not turnos_dia.empty:
        for _, t in turnos_dia.sort_values(by="Hora").iterrows():
            with st.container():
                st.markdown(f"""
                <div style="background:white; padding:20px; border-radius:15px; border-left: 5px solid {BRAND_GREEN}; margin-bottom:10px; box-shadow: 0px 2px 5px rgba(0,0,0,0.05);">
                    <span style="color:{BRAND_GREEN}; font-weight:bold;">{t['Hora']} hs</span> | 
                    <span style="font-weight:bold; font-size:18px;">{t['Paciente']}</span><br>
                    <small style="color:gray;">{t['Servicio']}</small>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Libre - Sin compromisos para esta fecha.")

# --- MÓDULO: REGISTRO ---
elif menu == "📝 Registro & Cobro":
    st.header("Nueva Atención")
    with st.form("registro_form"):
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Nombre Completo")
            dni = st.text_input("Documento (DNI)")
            contacto = st.text_input("WhatsApp (549...)")
        with c2:
            dx = st.text_input("Motivo / Diagnóstico")
            origen = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
            servicio = st.selectbox("Servicio", ["Plan X5", "Plan X10", "Sesión Individual", "Evaluación"])
        
        monto = st.number_input("Monto Total Cobrado ($)", min_value=0)
        
        st.markdown("### Programación")
        c3, c4 = st.columns(2)
        f_inicio = c3.date_input("Fecha Inicio", datetime.now())
        h_inicio = c4.time_input("Hora de Sesión", datetime.now().time())
        
        dias_fijos = st.checkbox("¿Usar días fijos para el resto de sesiones?")
        dias_selec = st.multiselect("Días de la semana", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]) if dias_fijos else []

        if st.form_submit_button("CONFIRMAR Y AGENDAR PACK"):
            # Determinar cantidad de sesiones
            cant = 1
            if "X5" in servicio: cant = 5
            elif "X10" in servicio: cant = 10
            
            # Guardar Paciente
            nuevo_p = pd.DataFrame([[dni, nombre, contacto, dx, origen, servicio, monto, str(f_inicio), cant]], columns=df_pacientes.columns)
            nuevo_p.to_csv('data/pacientes.csv', mode='a', header=False, index=False)
            
            # Generar Turnos
            nuevos_t_list = []
            if dias_fijos and dias_selec:
                dict_dias = {"Lunes":0, "Martes":1, "Miércoles":2, "Jueves":3, "Viernes":4, "Sábado":5}
                dias_num = [dict_dias[d] for d in dias_selec]
                
                curr_fecha = f_inicio
                agendados = 0
                while agendados < cant:
                    if curr_fecha.weekday() in dias_num:
                        nuevos_t_list.append([str(curr_fecha), h_inicio.strftime("%H:%M"), nombre, servicio])
                        agendados += 1
                    curr_fecha += timedelta(days=1)
            else:
                nuevos_t_list.append([str(f_inicio), h_inicio.strftime("%H:%M"), nombre, servicio])
            
            df_new_t = pd.DataFrame(nuevos_t_list, columns=df_agenda.columns)
            df_new_t.to_csv('data/agenda.csv', mode='a', header=False, index=False)
            
            st.success("¡Atención registrada y sesiones agendadas!")

# --- MÓDULO: FINANZAS ---
elif menu == "📊 Inteligencia Financiera":
    st.header("Inteligencia Financiera")
    df_p = pd.read_csv('data/pacientes.csv')
    
    if not df_p.empty:
        df_p['Comision'] = df_p.apply(lambda x: calcular_comision(x['Pago'], x['Origen']), axis=1)
        df_p['Neto'] = df_p['Pago'] - df_p['Comision']
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Ingresos Brutos", f"${df_p['Pago'].sum():,.0f}")
        c2.metric("Comisiones Cedidas", f"-${df_p['Comision'].sum():,.0f}")
        c3.metric("Utilidad Neta Elite", f"${df_p['Neto'].sum():,.0f}")
        
        st.subheader("Historial de Cobros")
        st.dataframe(df_p, use_container_width=True)
    else:
        st.warning("No hay datos financieros registrados aún.")
