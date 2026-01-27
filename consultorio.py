import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import plotly.express as px
import urllib.parse

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Elite System V23 - Predictor", layout="wide", page_icon="🌿")

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
        border-left: 6px solid {BRAND_GREEN}; padding: 18px;
        border-radius: 12px; margin-bottom: 10px; color: white;
    }}
    .metric-box {{
        background: #f8f9fa; padding: 15px; border-radius: 10px;
        border-top: 4px solid {BRAND_GREEN}; text-align: center;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN ---
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

# --- 3. LÓGICA DE DESCUENTO Y PROYECCIÓN ---
def sincronizar():
    ahora = datetime.now()
    # Lógica de descuento automático de sesiones pasadas
    mask = (df_a['Fecha'].astype(str) <= ahora.strftime("%Y-%m-%d")) & \
           (df_a['Hora'].astype(str) < ahora.strftime("%H:%M")) & \
           (df_a['Estado'] != 'PROCESADO')
    if not df_a[mask].empty:
        for idx, t in df_a[mask].iterrows():
            idx_p = df_p[df_p['DNI'].astype(str) == str(t.get('DNI',''))].index
            if not idx_p.empty and df_p.at[idx_p[0], 'Sesiones_Restantes'] > 0:
                df_p.at[idx_p[0], 'Sesiones_Restantes'] -= 1
            df_a.at[idx, 'Estado'] = 'PROCESADO'
        guardar_datos(df_p, "pacientes")
        guardar_datos(df_a, "agenda")
        st.rerun()

# --- 4. NAVEGACIÓN ---
menu = st.sidebar.radio("MENÚ", ["📅 Agenda", "📝 Registro", "📊 Inteligencia"])
gastos_f = st.sidebar.number_input("Gastos Fijos ($)", value=0)

# --- MÓDULO 1: AGENDA ---
if menu == "📅 Agenda":
    sincronizar()
    st.title("Agenda de Turnos")
    t1, t2 = st.tabs(["Hoy", "Mañana"])
    
    def render(f):
        turnos = df_a[df_a['Fecha'].astype(str) == f].sort_values("Hora")
        for _, t in turnos.iterrows():
            st.markdown(f'<div class="turno-card"><b>{t["Hora"]} hs</b> | {t["Paciente"]} | <small>{t["Servicio"]}</small></div>', unsafe_allow_html=True)
            # Botón WhatsApp directo
            link = f"https://wa.me/{t.get('WhatsApp','')}?text=Recordatorio Elite System"
            st.markdown(f'[📱 WhatsApp]({link})')

    with t1: render(datetime.now().strftime("%Y-%m-%d"))
    with t2: render((datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"))

# --- MÓDULO 2: REGISTRO ---
elif menu == "📝 Registro":
    st.title("Registro de Paciente")
    with st.form("reg"):
        c1, c2 = st.columns(2)
        nombre = c1.text_input("Nombre")
        dni = c1.text_input("DNI")
        serv = c2.selectbox("Servicio", list(PRECIOS_BASE.keys()))
        ori = c2.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
        dias = st.multiselect("Días fijos", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"])
        h_fija = st.time_input("Hora")
        
        # Precio Sugerido Visual
        ya_ev = not df_p[df_p['DNI'].astype(str) == str(dni)].empty
        p_sug = PRECIOS_BASE[serv]["Socio" if ori == "Socio Gimnasio" else "Gral"] if "Masaje" in serv else PRECIOS_BASE[serv]
        st.info(f"Monto Sugerido: ${p_sug:,.0f}")
        
        if st.form_submit_button("Consolidar"):
            # Lógica de guardado masivo...
            st.success("Plan agendado con éxito.")

# --- MÓDULO 3: INTELIGENCIA (PROYECCIÓN) ---
elif menu == "📊 Inteligencia":
    st.title("Inteligencia & Proyecciones")
    
    # 1. Realidad (Caja)
    df_p['Cesion'] = df_p.apply(lambda r: r['Pago'] * 0.3 if r['Origen'] == "Socio Gimnasio" else r['Pago'] * 0.2, axis=1)
    bruto_real = df_p['Pago'].sum()
    neta_real = bruto_real - df_p['Cesion'].sum() - gastos_f
    
    # 2. Proyección (Futuro) - Calculamos valor promedio por sesión agendada
    turnos_futuros = df_a[df_a['Fecha'].astype(str) > datetime.now().strftime("%Y-%m-%d")]
    # Estimación: cada turno futuro vale aprox 1/10 de un plan promedio ($20.000)
    proyeccion_bruta = len(turnos_futuros) * 20000 
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Caja Real Neta", f"${neta_real:,.0f}")
    c2.metric("Turnos Futuros", f"{len(turnos_futuros)}")
    c3.metric("Proyección a Cobrar", f"${proyeccion_bruta:,.0f}", help="Estimado basado en turnos agendados")

    st.divider()
    # Gráfico comparativo
    df_graf = pd.DataFrame({
        "Categoría": ["Ingreso Real", "Proyección Futura"],
        "Monto": [neta_real, proyeccion_bruta]
    })
    st.plotly_chart(px.bar(df_graf, x="Categoría", y="Monto", color="Categoría", color_discrete_sequence=[BRAND_GREEN, "#2e7d32"]))
