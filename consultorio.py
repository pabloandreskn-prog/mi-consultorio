import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import plotly.express as px

# --- 1. CONFIGURACIÓN Y ESTILO (BASE V8.2) ---
st.set_page_config(page_title="Elite System Ultra V8.2", layout="wide", page_icon="🌿")
BRAND_GREEN = "#60b067"
LIGHT_GREEN = "#90ee90"

st.markdown(f"""
    <style>
    .stApp {{ background-color: #FFFFFF; color: #1E1E1E; }}
    .main-title {{ color: {BRAND_GREEN}; font-size: 32px; font-weight: bold; }}
    .turno-card {{
        background: rgba(30, 30, 30, 0.9);
        backdrop-filter: blur(10px);
        border-left: 6px solid {BRAND_GREEN};
        padding: 20px; border-radius: 15px; margin-bottom: 15px; color: white;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.1);
    }}
    .alerta-renovacion {{
        background-color: {LIGHT_GREEN}; color: #1a5c1a; padding: 6px 12px;
        border-radius: 8px; font-weight: bold; display: inline-block; margin-top: 10px; font-size: 12px;
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

# --- 3. LÓGICA DE FECHAS ---
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

# --- 4. NAVEGACIÓN ---
with st.sidebar:
    st.markdown(f'<h1 style="color:{BRAND_GREEN};">🌿 ELITE SYSTEM</h1>', unsafe_allow_html=True)
    menu = st.radio("MENÚ", ["📅 Agenda & Turnos", "📝 Registro & Cobro", "📊 Inteligencia Financiera"])

# --- MÓDULO: AGENDA ---
if menu == "📅 Agenda & Turnos":
    st.markdown('<p class="main-title">Agenda & Control de Sesiones</p>', unsafe_allow_html=True)
    df_a = cargar_nube("agenda")
    df_p = cargar_nube("pacientes")
    hoy = str(datetime.now().date())
    
    t_hoy = df_a[df_a['Fecha'].astype(str) == hoy].sort_values("Hora")
    
    if t_hoy.empty:
        st.info("No hay turnos para hoy.")
    else:
        for _, t in t_hoy.iterrows():
            # Buscar sesiones restantes en la base de pacientes
            info_p = df_p[df_p['Nombre'] == t['Paciente']]
            rest = pd.to_numeric(info_p['Sesiones_Restantes'].iloc[-1], errors='coerce') if not info_p.empty else 10
            
            st.markdown(f"""
            <div class="turno-card">
                <span style="color:{BRAND_GREEN}; font-size:22px; font-weight:bold;">{t['Hora']} hs</span> | {t['Paciente']}<br>
                <b>{t['Servicio']}</b><br>
                {"<div class='alerta-renovacion'>♻️ RENOVAR O FINALIZAR TRATAMIENTO</div>" if rest <= 1 else ""}
            </div>
            """, unsafe_allow_html=True)

# --- MÓDULO: REGISTRO & COBRO ---
elif menu == "📝 Registro & Cobro":
    st.markdown('<p class="main-title">Registro & Venta</p>', unsafe_allow_html=True)
    df_p = cargar_nube("pacientes")
    
    with st.form("registro_v82"):
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Nombre Completo")
            dni = st.text_input("DNI")
            dx = st.text_area("Diagnóstico (Dx)")
        with c2:
            origen = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
            serv = st.selectbox("Servicio", SERVICIOS_DISPONIBLES)
            m_lista = st.number_input("Precio Lista", min_value=0)
            
            # Lógica de Evaluación Única
            pago_f = m_lista
            if serv == "Evaluacion" and dni:
                ya_ev = not df_p[(df_p['DNI'].astype(str) == str(dni)) & (df_p['Servicio'] == "Evaluacion")].empty
                if not ya_ev:
                    pago_f = 0 if origen == "Socio Gimnasio" else m_lista * 0.5
                    st.success(f"Beneficio Aplicado: ${pago_f}")
            st.write(f"### Total: ${pago_f}")

        st.divider()
        f_col, h_col = st.columns(2)
        f_ini = f_col.date_input("Fecha Inicio", datetime.now())
        h_ini = h_col.time_input("Hora", datetime.now().time())
        dias = st.multiselect("Días (Planes)", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"])
        
        if st.form_submit_button("CONSOLIDAR REGISTRO"):
            cant = 10 if "x10" in serv else (5 if "x5" in serv else 1)
            fechas = calcular_fechas_fijas(f_ini, dias, cant) if dias else [str(f_ini)]
            
            # Guardar Paciente
            nuevo_p = pd.DataFrame([[dni, nombre, "", dx, origen, serv, pago_f, str(f_ini), cant, cant]], columns=COL_PACIENTES)
            conn.update(worksheet="pacientes", data=pd.concat([df_p, nuevo_p], ignore_index=True))
            
            # Guardar Agenda
            df_a = cargar_nube("agenda")
            h_str = h_ini.strftime("%H:%M")
            nuevos_t = [[f, h_str, nombre, serv, "PENDIENTE", ""] for f in fechas]
            conn.update(worksheet="agenda", data=pd.concat([df_a, pd.DataFrame(nuevos_t, columns=COL_AGENDA)], ignore_index=True))
            st.rerun()

# --- MÓDULO: FINANZAS ---
elif menu == "📊 Inteligencia Financiera":
    st.markdown('<p class="main-title">Inteligencia de Negocio</p>', unsafe_allow_html=True)
    df_f = cargar_nube("pacientes")
    if not df_f.empty:
        df_f['Pago'] = pd.to_numeric(df_f['Pago'], errors='coerce').fillna(0)
        df_f['Comision'] = df_f.apply(lambda r: r['Pago']*0.3 if r['Origen'] == "Socio Gimnasio" else r['Pago']*0.2, axis=1)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Ingreso Bruto", f"${df_f['Pago'].sum():,.0f}")
        c2.metric("Comisiones Cedidas", f"-${df_f['Comision'].sum():,.0f}")
        c3.metric("Utilidad Neta", f"${(df_f['Pago'] - df_f['Comision']).sum():,.0f}")

        # Gráfico de Barras Detallado
        st.subheader("Ingresos por Servicio (%)")
        df_stats = df_f.groupby('Servicio')['Pago'].sum().reset_index()
        fig = px.bar(df_stats, x='Servicio', y='Pago', text_auto='.2s', color='Pago', color_continuous_scale='Greens')
        st.plotly_chart(fig, use_container_width=True)
