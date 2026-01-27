import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import plotly.express as px # Para la nueva gráfica

# --- 1. CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="Elite System Ultra V8", layout="wide", page_icon="🌿")

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
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 15px;
        color: white;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.1);
    }}
    .alerta-renovacion {{
        background-color: {LIGHT_GREEN}; color: #1a5c1a; padding: 6px 12px;
        border-radius: 8px; font-weight: bold; display: inline-block; margin-top: 10px;
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

# --- 3. FUNCIONES LÓGICAS ---
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

# --- MÓDULO 1: AGENDA ---
if menu == "📅 Agenda & Turnos":
    st.markdown('<p class="main-title">Agenda & Control</p>', unsafe_allow_html=True)
    df_a = cargar_nube("agenda")
    df_p = cargar_nube("pacientes")
    hoy = datetime.now().date()
    
    t_hoy = df_a[df_a['Fecha'].astype(str) == str(hoy)].sort_values("Hora")
    if t_hoy.empty:
        st.info("No hay turnos para hoy.")
    else:
        for _, t in t_hoy.iterrows():
            info_p = df_p[df_p['Nombre'] == t['Paciente']]
            restantes = pd.to_numeric(info_p['Sesiones_Restantes'].iloc[0], errors='coerce') if not info_p.empty else 10
            
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
                    st.button("⚙️ Gestionar", key=f"btn_{t['Hora']}_{t['Paciente']}")

# --- MÓDULO 2: REGISTRO (CORREGIDO) ---
elif menu == "📝 Registro & Cobro":
    st.markdown('<p class="main-title">Registro & Ventas</p>', unsafe_allow_html=True)
    df_p = cargar_nube("pacientes")
    
    with st.form("registro_pro_v8"):
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Nombre")
            dni = st.text_input("DNI")
            dx = st.text_area("Dx")
            contacto = st.text_input("WhatsApp (ej: 549...)")
        with c2:
            origen = st.selectbox("Categoría", ["Socio Gimnasio", "Captación Propia"])
            serv = st.selectbox("Servicio", SERVICIOS_DISPONIBLES)
            m_base = st.number_input("Precio Lista ($)", min_value=0)
            
            # Inteligencia de Beneficio
            m_final = m_base
            if serv == "Evaluacion":
                ya_ev = not df_p[(df_p['DNI'].astype(str) == str(dni)) & (df_p['Servicio'] == "Evaluacion")].empty
                if not ya_ev:
                    m_final = 0 if origen == "Socio Gimnasio" else m_base * 0.5
                    st.success(f"Beneficio Aplicado: Cobro final ${m_final}")
                else:
                    st.warning("Paciente ya evaluado. Precio regular.")
            st.metric("Total a percibir", f"${m_final}")

        st.divider()
        f_ini = st.date_input("Fecha Inicio", datetime.now())
        h_ini = st.time_input("Hora Turno", datetime.now().time())
        dias = st.multiselect("Días para planes", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"])
        
        # EL BOTÓN DEBE ESTAR DENTRO DEL BLOQUE 'WITH ST.FORM'
        enviar = st.form_submit_button("CONSOLIDAR REGISTRO")
        
    if enviar:
        if not nombre or not dni:
            st.error("Faltan datos críticos.")
        else:
            cant = 10 if "x10" in serv else (5 if "x5" in serv else 1)
            fechas = calcular_fechas_fijas(f_ini, dias, cant) if (dias and cant > 1) else [str(f_ini)]
            h_str = h_ini.strftime("%H:%M")
            
            # Guardar Paciente
            nuevo_p = pd.DataFrame([[dni, nombre, contacto, dx, origen, serv, m_final, str(f_ini), cant, cant]], columns=COL_PACIENTES)
            conn.update(worksheet="pacientes", data=pd.concat([df_p, nuevo_p], ignore_index=True))
            
            # Guardar Agenda
            df_a = cargar_nube("agenda")
            nuevos_t = [[f, h_str, nombre, serv, "PENDIENTE", contacto] for f in fechas]
            conn.update(worksheet="agenda", data=pd.concat([df_a, pd.DataFrame(nuevos_t, columns=COL_AGENDA)], ignore_index=True))
            
            st.balloons()
            st.success("Registro completado con éxito.")
            st.rerun()

# --- MÓDULO 3: FINANZAS (RESTAURADO Y MEJORADO) ---
elif menu == "📊 Inteligencia Financiera":
    st.markdown('<p class="main-title">Impacto Financiero</p>', unsafe_allow_html=True)
    df_f = cargar_nube("pacientes")
    
    if not df_f.empty:
        df_f['Pago'] = pd.to_numeric(df_f['Pago'], errors='coerce').fillna(0)
        
        # 1. Cálculo de Comisiones
        def calcular_comision(row):
            if row['Origen'] == "Socio Gimnasio": return row['Pago'] * 0.30
            return row['Pago'] * 0.20
        
        df_f['Comision'] = df_f.apply(calcular_comision, axis=1)
        df_f['Neto'] = df_f['Pago'] - df_f['Comision']
        
        # 2. Métricas
        c1, c2, c3 = st.columns(3)
        c1.metric("Ingresos Totales", f"${df_f['Pago'].sum():,.0f}")
        c2.metric("Comisiones Cedidas", f"-${df_f['Comision'].sum():,.0f}")
        c3.metric("Utilidad Neta", f"${df_f['Neto'].sum():,.0f}")
        
        # 3. Gráfica de Beneficios (Evaluaciones)
        st.subheader("Análisis de Evaluaciones y Bonificaciones")
        df_ev = df_f[df_f['Servicio'] == "Evaluacion"]
        if not df_ev.empty:
            fig = px.pie(df_ev, names='Origen', title='Distribución de Evaluaciones por Origen',
                         color_discrete_sequence=[BRAND_GREEN, "#333333"])
            st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Detalle de Operaciones")
        st.dataframe(df_f, use_container_width=True)
