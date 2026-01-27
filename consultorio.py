import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import plotly.express as px
import urllib.parse

# --- 1. CONFIGURACIÓN Y MATRIZ DE PRECIOS ---
st.set_page_config(page_title="Elite System V14 Master", layout="wide", page_icon="🌿")

PRECIOS_BASE = {
    "Evaluacion": 36000, "Sesion Especializada": 36000, "Sesion Individual": 24000,
    "Plan x5": 110000, "Plan x10": 200000,
    "Masaje ZA (piernas y pies)": {"Socio": 25000, "Gral": 30000},
    "Masaje ZB (Espalda y Cabeza)": {"Socio": 25000, "Gral": 30000},
    "Masaje Completo": {"Socio": 38000, "Gral": 45000}
}

BRAND_GREEN = "#60b067"
NEON_GREEN = "#39FF14"
WARNING_RED = "#FF4B4B"

st.markdown(f"""
    <style>
    .stApp {{ background-color: #FFFFFF; color: #1E1E1E; }}
    .turno-card {{
        background: rgba(30, 30, 30, 0.95);
        backdrop-filter: blur(15px);
        border-left: 8px solid {BRAND_GREEN};
        padding: 20px; border-radius: 15px; margin-bottom: 10px; color: white;
        display: flex; justify-content: space-between; align-items: center;
    }}
    .metric-card {{
        background: #f8f9fa; padding: 20px; border-radius: 12px;
        border: 1px solid #eee; text-align: center;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN Y DATOS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    df_p = conn.read(worksheet="pacientes", ttl="0").dropna(how='all')
    df_a = conn.read(worksheet="agenda", ttl="0").dropna(how='all')
    # Asegurar tipos de datos
    df_p['Pago'] = pd.to_numeric(df_p['Pago'], errors='coerce').fillna(0)
    df_p['Sesiones_Restantes'] = pd.to_numeric(df_p['Sesiones_Restantes'], errors='coerce').fillna(0)
    return df_p, df_a

def guardar_datos(df, hoja):
    conn.update(worksheet=hoja, data=df)
    st.cache_data.clear()

# --- 3. LÓGICA DE FECHAS ---
def calcular_fechas(f_ini, dias_semana, cant):
    dias_map = {"Lunes": 0, "Martes": 1, "Miércoles": 2, "Jueves": 3, "Viernes": 4, "Sábado": 5}
    nums_objetivo = [dias_map[d] for d in dias_semana]
    fechas = []
    actual = f_ini
    while len(fechas) < cant:
        if actual.weekday() in nums_objetivo:
            fechas.append(actual.strftime("%Y-%m-%d"))
        actual += timedelta(days=1)
    return fechas

df_p, df_a = cargar_datos()

# --- 4. NAVEGACIÓN ---
with st.sidebar:
    st.markdown(f'<h1 style="color:{BRAND_GREEN};">🌿 ELITE SYSTEM</h1>', unsafe_allow_html=True)
    menu = st.radio("GESTIÓN PROFESIONAL", ["📅 Agenda & Turnos", "📝 Registro & Cobro", "📊 Inteligencia Financiera"])
    st.divider()
    st.subheader("⚙️ Gastos Fijos")
    alquiler = st.number_input("Alquiler/Servicios", value=0)
    insumos = st.number_input("Insumos/Otros", value=0)
    gastos_totales = alquiler + insumos

# --- MÓDULO 1: AGENDA & TURNOS ---
if menu == "📅 Agenda & Turnos":
    st.markdown('<p class="main-title">Agenda Operativa</p>', unsafe_allow_html=True)
    
    with st.expander("🔍 DISPONIBILIDAD RÁPIDA"):
        f_busq = st.date_input("Fecha:", datetime.now())
        ocupados = df_a[df_a['Fecha'].astype(str) == str(f_busq)]['Hora'].tolist()
        libres = [h for h in ["08:00", "09:00", "10:00", "11:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00"] if h not in ocupados]
        cols = st.columns(5)
        for i, h in enumerate(libres): cols[i % 5].info(f"🕒 {h}")

    st.divider()
    hoy_str = datetime.now().strftime("%Y-%m-%d")
    turnos_hoy = df_a[df_a['Fecha'].astype(str) == hoy_str].sort_values("Hora")

    if turnos_hoy.empty:
        st.info("No hay turnos para hoy.")
    else:
        for _, t in turnos_hoy.iterrows():
            p_match = df_p[df_p['Nombre'] == t['Paciente']]
            rest = int(p_match['Sesiones_Restantes'].iloc[-1]) if not p_match.empty else 0
            
            st.markdown(f"""
            <div class="turno-card">
                <div>
                    <span style="font-size:22px; font-weight:bold; color:{BRAND_GREEN};">{t['Hora']} hs</span> | {t['Paciente']}<br>
                    <small>{t['Servicio']} | <b>Sesiones restantes: {rest}</b></small>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns([1, 1, 1])
            with c1: st.button("🛒 Renovar", key=f"r_{t['Hora']}")
            with c2: st.button("⚙️ Reagendar", key=f"m_{t['Hora']}")
            with c3:
                tel = p_match['Contacto'].iloc[-1] if not p_match.empty else ""
                msg = urllib.parse.quote(f"Hola {t['Paciente']}, Elite System te recuerda tu turno hoy {t['Hora']} hs.")
                st.markdown(f'<a href="https://wa.me/{tel}?text={msg}" target="_blank"><button style="width:100%; height:40px; background:#25D366; color:white; border:none; border-radius:10px;">📱 WhatsApp</button></a>', unsafe_allow_html=True)

# --- MÓDULO 2: REGISTRO & COBRO ---
elif menu == "📝 Registro & Cobro":
    st.markdown('<p class="main-title">Nueva Venta Elite</p>', unsafe_allow_html=True)
    with st.form("form_v14"):
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Paciente")
            dni = st.text_input("DNI")
            whatsapp = st.text_input("WhatsApp")
            dx = st.text_area("Dx")
        with c2:
            origen = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
            servicio = st.selectbox("Servicio", list(PRECIOS_BASE.keys()))
            
            # Lógica de Precios
            ya_ev = not df_p[(df_p['DNI'].astype(str) == str(dni)) & (df_p['Servicio'] == "Evaluacion")].empty
            if "Masaje" in servicio:
                monto = PRECIOS_BASE[servicio]["Socio" if origen == "Socio Gimnasio" else "Gral"]
            else:
                monto = PRECIOS_BASE[servicio]
                if servicio == "Evaluacion" and not ya_ev:
                    monto = 0 if origen == "Socio Gimnasio" else monto * 0.5
            
            st.metric("Total a Cobrar", f"${monto:,.0f}")
        
        st.divider()
        c3, c4 = st.columns(2)
        f_ini = c3.date_input("Fecha Inicio", datetime.now())
        h_ini = c4.time_input("Hora", datetime.now().time())
        dias = st.multiselect("Días para Planes", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"])
        
        if st.form_submit_button("CONSOLIDAR"):
            cant = 10 if "x10" in servicio else (5 if "x5" in servicio else 1)
            fechas_p = calcular_fechas(f_ini, dias, cant) if dias else [f_ini.strftime("%Y-%m-%d")]
            
            nuevo_p = pd.DataFrame([[dni, nombre, whatsapp, dx, origen, servicio, monto, f_ini.strftime("%Y-%m-%d"), cant, cant]], columns=df_p.columns)
            guardar_datos(pd.concat([df_p, nuevo_p], ignore_index=True), "pacientes")
            
            nuevos_t = pd.DataFrame([[f, h_ini.strftime("%H:%M"), nombre, servicio, "PENDIENTE", whatsapp] for f in fechas_p], columns=df_a.columns)
            guardar_datos(pd.concat([df_a, nuevos_t], ignore_index=True), "agenda")
            st.rerun()

# --- MÓDULO 3: INTELIGENCIA FINANCIERA (ANALÍTICA ESCALABLE) ---
elif menu == "📊 Inteligencia Financiera":
    st.markdown('<p class="main-title">Análisis de Retención e Impacto</p>', unsafe_allow_html=True)
    
    if not df_p.empty:
        # Cálculos de Comisiones y Utilidad
        df_p['Comision'] = df_p.apply(lambda r: r['Pago'] * 0.3 if r['Origen'] == "Socio Gimnasio" else r['Pago'] * 0.2, axis=1)
        bruto = df_p['Pago'].sum()
        comisiones = df_p['Comision'].sum()
        neta_pre_gastos = bruto - comisiones
        final_real = neta_pre_gastos - gastos_totales

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ingreso Bruto", f"${bruto:,.0f}")
        c2.metric("Comisiones", f"-${comisiones:,.0f}")
        c3.metric("Gastos Fijos", f"-${gastos_totales:,.0f}")
        c4.metric("GANANCIA REAL", f"${final_real:,.0f}", delta=f"{ (final_real/bruto*100):.1f}% rentab.")

        st.divider()

        # MEJORA: Gráfico de Barras Segmentado (Escalable para 80+ pacientes)
        st.subheader("🔍 Análisis de Retención (Salud de la Cartera)")
        
        # Clasificar pacientes por riesgo de abandono
        def clasificar(r):
            if r <= 2: return "🔴 Críticos (0-2 sesiones)"
            if r <= 6: return "🟡 En Progreso (3-6 sesiones)"
            return "🟢 Estables (7+ sesiones)"
        
        df_p['Estado'] = df_p['Sesiones_Restantes'].apply(clasificar)
        df_segmento = df_p.groupby('Estado').size().reset_index(name='Cantidad')
        
        col_a, col_b = st.columns(2)
        with col_a:
            fig_seg = px.bar(df_segmento, x='Estado', y='Cantidad', color='Estado',
                             color_discrete_map={"🔴 Críticos (0-2 sesiones)": "#FF4B4B", 
                                               "🟡 En Progreso (3-6 sesiones)": "#FFCC00", 
                                               "🟢 Estables (7+ sesiones)": "#60b067"})
            st.plotly_chart(fig_seg, use_container_width=True)
        
        with col_b:
            # Gráfico de ingresos por origen (Predictivo)
            fig_origen = px.pie(df_p, values='Pago', names='Origen', title="Fuentes de Ingreso", hole=0.5)
            st.plotly_chart(fig_origen, use_container_width=True)

        st.subheader("📋 Detalle de Pacientes Críticos (Acción Inmediata)")
        criticos = df_p[df_p['Sesiones_Restantes'] <= 2][['Nombre', 'Servicio', 'Sesiones_Restantes', 'Contacto']]
        st.table(criticos)
