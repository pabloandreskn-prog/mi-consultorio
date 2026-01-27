import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import plotly.express as px
import urllib.parse

# --- 1. CONFIGURACIÓN Y PRECIOS ---
st.set_page_config(page_title="Elite System V21 - Quantum Persistence", layout="wide", page_icon="🌿")

PRECIOS_BASE = {
    "Evaluacion": 36000, "Sesion Especializada": 36000, "Sesion Individual": 24000,
    "Plan x5": 110000, "Plan x10": 200000,
    "Masaje ZA (piernas y pies)": {"Socio": 25000, "Gral": 30000},
    "Masaje ZB (Espalda y Cabeza)": {"Socio": 25000, "Gral": 30000},
    "Masaje Completo": {"Socio": 38000, "Gral": 45000}
}

BRAND_GREEN = "#60b067"

st.markdown(f"""
    <style>
    .stApp {{ background-color: #FFFFFF; color: #1E1E1E; }}
    .turno-card {{
        background: rgba(30, 30, 30, 0.95);
        backdrop-filter: blur(15px);
        border-left: 8px solid {BRAND_GREEN};
        padding: 18px; border-radius: 12px; margin-bottom: 8px; color: white;
    }}
    .price-card {{
        background: {BRAND_GREEN}; color: white; padding: 15px;
        border-radius: 10px; text-align: center; font-size: 26px; font-weight: bold;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN Y MOTOR DE DATOS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    df_p = conn.read(worksheet="pacientes", ttl="0").dropna(how='all')
    df_a = conn.read(worksheet="agenda", ttl="0").dropna(how='all')
    for col in ['Pago', 'Sesiones_Restantes', 'Sesiones_Totales']:
        if col in df_p.columns:
            df_p[col] = pd.to_numeric(df_p[col], errors='coerce').fillna(0)
    return df_p, df_a

def guardar_datos(df, hoja):
    conn.update(worksheet=hoja, data=df)
    st.cache_data.clear()

df_p, df_a = cargar_datos()

# --- 3. LÓGICA DE AGENDAMIENTO ---
def calcular_fechas_plan(fecha_inicio, dias_seleccionados, cantidad):
    dias_map = {"Lunes": 0, "Martes": 1, "Miércoles": 2, "Jueves": 3, "Viernes": 4, "Sábado": 5}
    indices_objetivo = [dias_map[d] for d in dias_seleccionados]
    fechas = []
    actual = fecha_inicio
    while len(fechas) < cantidad:
        if actual.weekday() in indices_objetivo:
            fechas.append(actual.strftime("%Y-%m-%d"))
        actual += timedelta(days=1)
    return fechas

# --- 4. NAVEGACIÓN ---
with st.sidebar:
    st.markdown(f'<h1 style="color:{BRAND_GREEN};">🌿 ELITE SYSTEM</h1>', unsafe_allow_html=True)
    menu = st.radio("MENÚ", ["📅 Agenda & Turnos", "📝 Registro & Cobro", "📊 Inteligencia Financiera"])
    st.divider()
    gastos_fijos = st.number_input("Gastos Fijos Mensuales ($)", value=0)

# --- MÓDULO 1: AGENDA (HOY Y MAÑANA) ---
if menu == "📅 Agenda & Turnos":
    st.title("Control de Turnos")
    col_hoy, col_manana = st.tabs(["☀️ HOY", "🌅 MAÑANA"])
    
    with col_hoy:
        hoy = datetime.now().strftime("%Y-%m-%d")
        t_hoy = df_a[df_a['Fecha'].astype(str) == hoy].sort_values("Hora")
        if t_hoy.empty: st.info("No hay turnos hoy.")
        else:
            for _, t in t_hoy.iterrows():
                st.markdown(f'<div class="turno-card"><b>{t["Hora"]} hs</b> | {t["Paciente"]}<br><small>{t["Servicio"]}</small></div>', unsafe_allow_html=True)

    with col_manana:
        manana = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        t_manana = df_a[df_a['Fecha'].astype(str) == manana].sort_values("Hora")
        if t_manana.empty: st.info("No hay turnos mañana.")
        else:
            for _, t in t_manana.iterrows():
                st.markdown(f'<div class="turno-card" style="border-left-color:#888;"><b>{t["Hora"]} hs</b> | {t["Paciente"]}<br><small>{t["Servicio"]}</small></div>', unsafe_allow_html=True)

# --- MÓDULO 2: REGISTRO & COBRO (ESCRITURA MASIVA) ---
elif menu == "📝 Registro & Cobro":
    st.title("Nuevo Registro & Venta")
    c1, c2 = st.columns([2, 1])
    
    with c1:
        with st.form("form_v21"):
            nombre = st.text_input("Nombre Completo")
            dni = st.text_input("DNI")
            whatsapp = st.text_input("WhatsApp")
            dx = st.text_area("Diagnóstico")
            st.divider()
            f_inicio = st.date_input("Fecha Inicio", datetime.now())
            h_fija = st.time_input("Hora fija", datetime.now().time())
            dias_fijos = st.multiselect("Días fijos", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])
            servicio = st.selectbox("Servicio", list(PRECIOS_BASE.keys()))
            origen = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
            submit = st.form_submit_button("CONSOLIDAR REGISTRO Y AGENDAR")

    with c2:
        # Precio Instantáneo
        ya_ev = not df_p[(df_p['DNI'].astype(str) == str(dni)) & (df_p['Servicio'] == "Evaluacion")].empty
        precio_sug = PRECIOS_BASE[servicio]["Socio" if origen == "Socio Gimnasio" else "Gral"] if "Masaje" in servicio else PRECIOS_BASE[servicio]
        if servicio == "Evaluacion" and not ya_ev:
            precio_sug = 0 if origen == "Socio Gimnasio" else precio_sug * 0.5
        
        st.markdown(f'<div class="price-card"><small>Cobro Sugerido</small><br>${precio_sug:,.0f}</div>', unsafe_allow_html=True)
        pago_final = st.number_input("Confirmar monto recibido ($)", value=float(precio_sug))

        if submit:
            if not nombre or not dni:
                st.error("Por favor completa Nombre y DNI.")
            else:
                # 1. Crear filas para el historial de pacientes
                cant = 10 if "x10" in servicio else (5 if "x5" in servicio else 1)
                nuevo_paciente = pd.DataFrame([[dni, nombre, whatsapp, dx, origen, servicio, pago_final, f_inicio.strftime("%Y-%m-%d"), cant, cant]], columns=df_p.columns)
                
                # 2. Generar múltiples turnos para la agenda
                fechas = calcular_fechas_plan(f_inicio, dias_fijos, cant) if dias_fijos else [f_inicio.strftime("%Y-%m-%d")]
                nuevos_turnos = pd.DataFrame([[f, h_fija.strftime("%H:%M"), nombre, servicio, "PENDIENTE", whatsapp, dni] for f in fechas], columns=df_a.columns)
                
                # 3. Guardado Masivo
                guardar_datos(pd.concat([df_p, nuevo_paciente], ignore_index=True), "pacientes")
                guardar_datos(pd.concat([df_a, nuevos_turnos], ignore_index=True), "agenda")
                
                st.success(f"✅ ¡Éxito! {nombre} registrado y {len(fechas)} sesiones agendadas.")
                st.balloons()

# --- MÓDULO 3: INTELIGENCIA FINANCIERA ---
elif menu == "📊 Inteligencia Financiera":
    st.title("Análisis de Rentabilidad")
    df_p['Comision'] = df_p.apply(lambda r: r['Pago'] * 0.3 if r['Origen'] == "Socio Gimnasio" else r['Pago'] * 0.2, axis=1)
    bruto = df_p['Pago'].sum()
    cesiones = df_p['Comision'].sum()
    neta = bruto - cesiones - gastos_fijos

    st.columns(4)[0].metric("Bruto", f"${bruto:,.0f}")
    st.columns(4)[1].metric("Comisiones", f"-${cesiones:,.0f}")
    st.columns(4)[2].metric("Gastos", f"-${gastos_fijos:,.0f}")
    st.columns(4)[3].metric("NETO", f"${neta:,.0f}")
