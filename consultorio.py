import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import plotly.express as px
import urllib.parse

# --- 1. CONFIGURACIÓN Y MATRIZ DE PRECIOS ---
st.set_page_config(page_title="Elite System V13 Quantum", layout="wide", page_icon="🌿")

PRECIOS_BASE = {
    "Evaluacion": 36000,
    "Sesion Especializada": 36000,
    "Sesion Individual": 24000,
    "Plan x5": 110000,
    "Plan x10": 200000,
    "Masaje ZA (piernas y pies)": {"Socio": 25000, "Gral": 30000},
    "Masaje ZB (Espalda y Cabeza)": {"Socio": 25000, "Gral": 30000},
    "Masaje Completo": {"Socio": 38000, "Gral": 45000}
}

BRAND_GREEN = "#60b067"
NEON_GREEN = "#39FF14"

st.markdown(f"""
    <style>
    .stApp {{ background-color: #FFFFFF; color: #1E1E1E; }}
    [data-testid="stSidebar"] {{ background-color: #f8f9fa; border-right: 1px solid #eee; }}
    .turno-card {{
        background: rgba(30, 30, 30, 0.95);
        backdrop-filter: blur(15px);
        border-left: 8px solid {BRAND_GREEN};
        padding: 20px; border-radius: 15px; margin-bottom: 10px; color: white;
        display: flex; justify-content: space-between; align-items: center;
    }}
    .sub-panel {{
        background: #f0f2f6; padding: 20px; border-radius: 0 0 15px 15px;
        margin-top: -10px; margin-bottom: 20px; border: 1px solid #ddd;
    }}
    .metric-box {{
        background: white; padding: 15px; border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05); border: 1px solid #eee;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN Y DATOS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    df_p = conn.read(worksheet="pacientes", ttl="0").dropna(how='all')
    df_a = conn.read(worksheet="agenda", ttl="0").dropna(how='all')
    return df_p, df_a

def guardar_datos(df, hoja):
    conn.update(worksheet=hoja, data=df)
    st.cache_data.clear()

# --- 3. LÓGICA PREDICTIVA Y AUXILIAR ---
def calcular_fechas(f_ini, dias_semana, cant):
    dias_map = {"Lunes": 0, "Martes": 1, "Miércoles": 2, "Jueves": 3, "Viernes": 4}
    nums_objetivo = [dias_map[d] for d in dias_semana]
    fechas = []
    actual = f_ini
    while len(fechas) < cant:
        if actual.weekday() in nums_objetivo:
            fechas.append(actual.strftime("%Y-%m-%d"))
        actual += timedelta(days=1)
    return fechas

# --- 4. NAVEGACIÓN ---
df_p, df_a = cargar_datos()

with st.sidebar:
    st.markdown(f'<h1 style="color:{BRAND_GREEN};">🌿 ELITE SYSTEM</h1>', unsafe_allow_html=True)
    menu = st.radio("MENÚ DE GESTIÓN", ["📅 Agenda & Turnos", "📝 Registro & Cobro", "📊 Inteligencia & Análisis"])

# --- MÓDULO 1: AGENDA & TURNOS ---
if menu == "📅 Agenda & Turnos":
    st.markdown('<p class="main-title">Control de Agenda Inteligente</p>', unsafe_allow_html=True)
    
    with st.expander("🔍 DISPONIBILIDAD DE HUECOS"):
        f_busq = st.date_input("Consultar fecha:", datetime.now())
        ocupados = df_a[df_a['Fecha'].astype(str) == str(f_busq)]['Hora'].tolist()
        libres = [h for h in ["08:00", "09:00", "10:00", "11:00", "14:00", "15:00", "16:00", "17:00", "18:00"] if h not in ocupados]
        cols = st.columns(len(libres) if libres else 1)
        for i, h in enumerate(libres): cols[i].button(h, key=f"h_{h}")

    st.divider()
    hoy_str = datetime.now().strftime("%Y-%m-%d")
    turnos_hoy = df_a[df_a['Fecha'].astype(str) == hoy_str].sort_values("Hora")

    if turnos_hoy.empty:
        st.info("No hay pacientes agendados para hoy.")
    else:
        for _, t in turnos_hoy.iterrows():
            # Buscar info del paciente para análisis
            p_info = df_p[df_p['Nombre'] == t['Paciente']].iloc[-1] if not df_p[df_p['Nombre'] == t['Paciente']].empty else None
            sesiones_r = int(p_info['Sesiones_Restantes']) if p_info is not None else 0
            
            st.markdown(f"""
            <div class="turno-card">
                <div>
                    <span style="font-size:22px; font-weight:bold; color:{BRAND_GREEN};">{t['Hora']} hs</span> | {t['Paciente']}<br>
                    <small>{t['Servicio']} | <b>Restan: {sesiones_r}</b></small>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns([1, 1, 1])
            if c1.button("🛒 Renovar", key=f"ren_{t['Hora']}"):
                st.session_state.accion = ("renovar", t['Paciente'])
            if c2.button("⚙️ Reagendar", key=f"mod_{t['Hora']}"):
                st.session_state.accion = ("reagendar", t['Paciente'])
            
            # WhatsApp Directo
            msg = urllib.parse.quote(f"Hola {t['Paciente']}, te escribo de Elite System para coordinar tu turno...")
            c3.markdown(f'''<a href="https://wa.me/{p_info['Contacto'] if p_info is not None else ''}?text={msg}" target="_blank">
                <button style="width:100%; border-radius:12px; height:40px; background:#25D366; color:white; border:none; cursor:pointer;">📱 WhatsApp</button></a>''', unsafe_allow_html=True)

# --- MÓDULO 2: REGISTRO & COBRO (MOTOR DE PERSISTENCIA V13) ---
elif menu == "📝 Registro & Cobro":
    st.markdown('<p class="main-title">Registro & Venta Automática</p>', unsafe_allow_html=True)
    
    with st.form("form_quantum"):
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Nombre Completo")
            dni = st.text_input("DNI")
            whatsapp = st.text_input("WhatsApp (ej: 549...)")
            dx = st.text_area("Diagnóstico")
        with c2:
            origen = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
            servicio = st.selectbox("Servicio / Plan", list(PRECIOS_BASE.keys()))
            
            # Lógica de Precios Predictiva
            ya_fue_evaluado = not df_p[(df_p['DNI'].astype(str) == str(dni)) & (df_p['Servicio'] == "Evaluacion")].empty
            monto = 0
            if "Masaje" in servicio:
                monto = PRECIOS_BASE[servicio]["Socio" if origen == "Socio Gimnasio" else "Gral"]
            else:
                monto = PRECIOS_BASE[servicio]
                if servicio == "Evaluacion" and not ya_fue_evaluado:
                    monto = 0 if origen == "Socio Gimnasio" else monto * 0.5
            
            st.metric("Total a Cobrar", f"${monto:,.0f}")
        
        st.divider()
        c3, c4 = st.columns(2)
        f_ini = c3.date_input("Fecha Inicio", datetime.now())
        h_ini = c4.time_input("Hora", datetime.now().time())
        dias = st.multiselect("Días para Planes", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"])
        
        if st.form_submit_button("CONSOLIDAR REGISTRO"):
            cant = 10 if "x10" in servicio else (5 if "x5" in servicio else 1)
            fechas_plan = calcular_fechas(f_ini, dias, cant) if dias else [f_ini.strftime("%Y-%m-%d")]
            
            # 1. Actualizar Pacientes
            nuevo_p = pd.DataFrame([[dni, nombre, whatsapp, dx, origen, servicio, monto, f_ini.strftime("%Y-%m-%d"), cant, cant]], 
                                 columns=df_p.columns)
            guardar_datos(pd.concat([df_p, nuevo_p], ignore_index=True), "pacientes")
            
            # 2. Actualizar Agenda
            nuevos_t = pd.DataFrame([[f, h_ini.strftime("%H:%M"), nombre, servicio, "PENDIENTE", whatsapp] for f in fechas_plan], 
                                   columns=df_a.columns)
            guardar_datos(pd.concat([df_a, nuevos_t], ignore_index=True), "agenda")
            
            st.success("✅ Registro y Agenda sincronizados con éxito.")
            st.rerun()

# --- MÓDULO 3: INTELIGENCIA & ANÁLISIS (EL SALTO CUÁNTICO) ---
elif menu == "📊 Inteligencia & Análisis":
    st.markdown('<p class="main-title">Análisis de Impacto & Salud del Negocio</p>', unsafe_allow_html=True)
    
    # KPIs Rápidos
    c1, c2, c3 = st.columns(3)
    ingresos_brutos = pd.to_numeric(df_p['Pago'], errors='coerce').sum()
    c1.metric("Ingresos Totales", f"${ingresos_brutos:,.0f}")
    
    pacientes_criticos = df_p[pd.to_numeric(df_p['Sesiones_Restantes'], errors='coerce') <= 2].shape[0]
    c2.metric("Pacientes por Renovar", pacientes_criticos, delta="- Alerta", delta_color="inverse")
    
    # Análisis Predictivo: ¿Cuánto dinero hay "en la mesa"?
    # Calculamos el valor promedio de sesión por los planes activos
    df_p['Sesiones_Restantes'] = pd.to_numeric(df_p['Sesiones_Restantes'], errors='coerce')
    ingreso_asegurado = (df_p['Pago'] / df_p['Sesiones_Totales'] * df_p['Sesiones_Restantes']).sum()
    c3.metric("Capital en Sesiones Pendientes", f"${ingreso_asegurado:,.0f}", help="Valor monetario de las sesiones que ya cobraste pero aún debes brindar.")

    st.divider()
    
    col_izq, col_der = st.columns(2)
    with col_izq:
        st.subheader("Distribución de Ingresos")
        fig_pie = px.pie(df_p, values='Pago', names='Servicio', hole=0.4, color_discrete_sequence=px.colors.sequential.Greens_r)
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col_der:
        st.subheader("Estado de Retención de Pacientes")
        fig_bar = px.bar(df_p, x='Nombre', y='Sesiones_Restantes', color='Sesiones_Restantes', 
                         color_continuous_scale='RdYlGn', title="Sesiones Restantes por Paciente")
        st.plotly_chart(fig_bar, use_container_width=True)
