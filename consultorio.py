import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import plotly.express as px
import urllib.parse

# --- 1. CONFIGURACIÓN Y MATRIZ DE PRECIOS ---
st.set_page_config(page_title="Elite System V16 Quantum", layout="wide", page_icon="🌿")

PRECIOS_BASE = {
    "Evaluacion": 36000, "Sesion Especializada": 36000, "Sesion Individual": 24000,
    "Plan x5": 110000, "Plan x10": 200000,
    "Masaje ZA (piernas y pies)": {"Socio": 25000, "Gral": 30000},
    "Masaje ZB (Espalda y Cabeza)": {"Socio": 25000, "Gral": 30000},
    "Masaje Completo": {"Socio": 38000, "Gral": 45000}
}

BRAND_GREEN = "#60b067"
NEON_GREEN = "#39FF14"

st.markdown(f"""
    <style>
    .stApp {{ background-color: #FFFFFF; color: #1E1E1E; }}
    .turno-card {{
        background: rgba(30, 30, 30, 0.95);
        backdrop-filter: blur(15px);
        border-left: 8px solid {BRAND_GREEN};
        padding: 20px; border-radius: 15px; margin-bottom: 10px; color: white;
    }}
    .price-badge {{
        background-color: {BRAND_GREEN}; color: white; padding: 10px 20px;
        border-radius: 10px; font-size: 24px; font-weight: bold; display: inline-block;
    }}
    .chip-libre {{
        background: rgba(96, 176, 103, 0.1); color: {BRAND_GREEN};
        padding: 8px; border-radius: 10px; border: 1px solid {BRAND_GREEN};
        font-weight: bold; text-align: center; margin-bottom: 5px;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN Y CARGA ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    df_p = conn.read(worksheet="pacientes", ttl="0").dropna(how='all')
    df_a = conn.read(worksheet="agenda", ttl="0").dropna(how='all')
    # Limpieza de tipos
    df_p['Pago'] = pd.to_numeric(df_p['Pago'], errors='coerce').fillna(0)
    df_p['Sesiones_Restantes'] = pd.to_numeric(df_p['Sesiones_Restantes'], errors='coerce').fillna(0)
    return df_p, df_a

def guardar_datos(df, hoja):
    conn.update(worksheet=hoja, data=df)
    st.cache_data.clear()

df_p, df_a = cargar_datos()

# --- 3. NAVEGACIÓN ---
with st.sidebar:
    st.markdown(f'<h1 style="color:{BRAND_GREEN};">🌿 ELITE SYSTEM</h1>', unsafe_allow_html=True)
    menu = st.radio("MENÚ", ["📅 Agenda & Turnos", "📝 Registro & Cobro", "📊 Inteligencia Financiera"])
    st.divider()
    gastos_fijos = st.number_input("Gastos Fijos Mensuales ($)", value=0)

# --- MÓDULO 1: AGENDA (RESTAURADO EXPANDER) ---
if menu == "📅 Agenda & Turnos":
    st.markdown('<p style="font-size:30px; font-weight:bold;">Agenda Operativa</p>', unsafe_allow_html=True)
    
    # 1. FUNCIONALIDAD RECUPERADA: EXPANDER DE DISPONIBILIDAD
    with st.expander("🔍 CONSULTAR TURNOS DISPONIBLES (HUECOS LIBRES)", expanded=False):
        c_f, _ = st.columns([1, 2])
        f_busq = c_f.date_input("Día a consultar:", datetime.now())
        ocupados = df_a[df_a['Fecha'].astype(str) == str(f_busq)]['Hora'].tolist()
        horas_lab = ["08:00", "09:00", "10:00", "11:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00"]
        libres = [h for h in horas_lab if h not in ocupados]
        if libres:
            cols = st.columns(5)
            for i, h in enumerate(libres):
                cols[i % 5].markdown(f'<div class="chip-libre">{h}</div>', unsafe_allow_html=True)
        else: st.warning("Sin disponibilidad para este día.")

    st.divider()
    hoy_str = datetime.now().strftime("%Y-%m-%d")
    turnos_hoy = df_a[df_a['Fecha'].astype(str) == hoy_str].sort_values("Hora")

    if turnos_hoy.empty:
        st.info("No hay turnos para hoy.")
    else:
        for _, t in turnos_hoy.iterrows():
            st.markdown(f"""
            <div class="turno-card">
                <span style="font-size:22px; font-weight:bold; color:{BRAND_GREEN};">{t['Hora']} hs</span> | <b>{t['Paciente']}</b><br>
                <small>{t['Servicio']}</small>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            with c1: st.button("🛒 Renovar", key=f"r_{t['Hora']}")
            with c2: st.button("⚙️ Reagendar", key=f"m_{t['Hora']}")
            with c3:
                tel = t.get('WhatsApp', '')
                msg = urllib.parse.quote(f"Hola {t['Paciente']}, Elite System te recuerda tu turno.")
                st.markdown(f'<a href="https://wa.me/{tel}?text={msg}" target="_blank"><button style="width:100%; height:38px; background:#25D366; color:white; border:none; border-radius:10px; cursor:pointer;">📱 WhatsApp</button></a>', unsafe_allow_html=True)

# --- MÓDULO 2: REGISTRO & COBRO (INTELIGENCIA PREDICTIVA) ---
elif menu == "📝 Registro & Cobro":
    st.markdown('<p style="font-size:30px; font-weight:bold;">Registro & Venta</p>', unsafe_allow_html=True)
    with st.form("form_v16"):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre Completo")
            dni = st.text_input("DNI")
            whatsapp = st.text_input("WhatsApp")
            dx = st.text_area("Diagnóstico (Dx)")
        with col2:
            origen = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
            servicio = st.selectbox("Servicio", list(PRECIOS_BASE.keys()))
            
            # Cálculo automático del valor
            ya_ev = not df_p[(df_p['DNI'].astype(str) == str(dni)) & (df_p['Servicio'] == "Evaluacion")].empty
            precio_sug = PRECIOS_BASE[servicio]["Socio" if origen == "Socio Gimnasio" else "Gral"] if "Masaje" in servicio else PRECIOS_BASE[servicio]
            if servicio == "Evaluacion" and not ya_ev:
                precio_sug = 0 if origen == "Socio Gimnasio" else precio_sug * 0.5
            
            st.markdown(f'Valor sugerido:<br><div class="price-badge">${precio_sug:,.0f}</div>', unsafe_allow_html=True)
            tipo_pago = st.radio("Cobro:", ["Pago Total", "Parcial", "Pendiente"], horizontal=True)
            monto_final = st.number_input("Monto Final ($)", value=float(precio_sug))
        
        st.divider()
        st.form_submit_button("CONSOLIDAR REGISTRO")

# --- MÓDULO 3: INTELIGENCIA FINANCIERA (COMISIONES RESTAURADAS) ---
elif menu == "📊 Inteligencia Financiera":
    st.markdown('<p style="font-size:30px; font-weight:bold;">Análisis Financiero & Comisiones</p>', unsafe_allow_html=True)
    
    if not df_p.empty:
        # 2. FUNCIONALIDAD RECUPERADA: CESIÓN DE COMISIONES (30% Socio, 20% Captación)
        df_p['Comision'] = df_p.apply(lambda r: r['Pago'] * 0.30 if r['Origen'] == "Socio Gimnasio" else r['Pago'] * 0.20, axis=1)
        
        bruto = df_p['Pago'].sum()
        total_comisiones = df_p['Comision'].sum()
        utilidad_neta = bruto - total_comisiones - gastos_fijos

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ingreso Bruto", f"${bruto:,.0f}")
        c2.metric("Comisiones Cedidas", f"-${total_comisiones:,.0f}")
        c3.metric("Gastos Fijos", f"-${gastos_fijos:,.0f}")
        c4.metric("UTILIDAD REAL", f"${utilidad_neta:,.0f}", delta=f"{(utilidad_neta/bruto*100):.1f}%" if bruto > 0 else "0%")

        st.divider()
        st.subheader("Salud del Negocio")
        col_a, col_b = st.columns(2)
        with col_a:
            fig_pie = px.pie(df_p, values='Pago', names='Origen', title="Ingresos por Origen", hole=0.4, color_discrete_sequence=['#60b067', '#2e7d32'])
            st.plotly_chart(fig_pie, use_container_width=True)
        with col_b:
            # Gráfico escalable: Estado de pacientes
            df_p['Estado_Sesion'] = df_p['Sesiones_Restantes'].apply(lambda x: "Crítico (0-2)" if x <= 2 else "Activo")
            fig_bar = px.bar(df_p.groupby('Estado_Sesion').size().reset_index(name='Cant'), x='Estado_Sesion', y='Cant', color='Estado_Sesion', color_discrete_map={"Crítico (0-2)": "#FF4B4B", "Activo": "#60b067"})
            st.plotly_chart(fig_bar, use_container_width=True)
