import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import plotly.express as px
import urllib.parse

# --- 1. CONFIGURACIÓN Y MATRIZ DE PRECIOS ---
st.set_page_config(page_title="Elite System V15 Quantum", layout="wide", page_icon="🌿")

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
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    df_p = conn.read(worksheet="pacientes", ttl="0").dropna(how='all')
    df_a = conn.read(worksheet="agenda", ttl="0").dropna(how='all')
    return df_p, df_a

def guardar_datos(df, hoja):
    conn.update(worksheet=hoja, data=df)
    st.cache_data.clear()

df_p, df_a = cargar_datos()

# --- 3. NAVEGACIÓN ---
with st.sidebar:
    st.markdown(f'<h1 style="color:{BRAND_GREEN};">🌿 ELITE SYSTEM</h1>', unsafe_allow_html=True)
    menu = st.radio("GESTIÓN", ["📅 Agenda & Turnos", "📝 Registro & Cobro", "📊 Inteligencia Financiera"])
    st.divider()
    gastos = st.number_input("Gastos Mensuales ($)", value=0)

# --- MÓDULO 1: AGENDA (CON WHATSAPP DIRECTO) ---
if menu == "📅 Agenda & Turnos":
    st.markdown('<p style="font-size:30px; font-weight:bold;">Agenda Operativa</p>', unsafe_allow_html=True)
    
    hoy_str = datetime.now().strftime("%Y-%m-%d")
    turnos_hoy = df_a[df_a['Fecha'].astype(str) == hoy_str].sort_values("Hora")

    if turnos_hoy.empty:
        st.info("No hay turnos para hoy.")
    else:
        for _, t in turnos_hoy.iterrows():
            st.markdown(f"""
            <div class="turno-card">
                <span style="font-size:20px; font-weight:bold; color:{BRAND_GREEN};">{t['Hora']} hs</span> | <b>{t['Paciente']}</b><br>
                {t['Servicio']} | Estado: {t.get('Estado_Pago', 'Pendiente')}
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            with c1: st.button("🛒 Renovar", key=f"r_{t['Hora']}")
            with c2: st.button("⚙️ Reagendar", key=f"m_{t['Hora']}")
            with c3:
                # Link de WhatsApp automático usando el contacto de la base de datos
                tel = t.get('WhatsApp', '')
                msg = urllib.parse.quote(f"Hola {t['Paciente']}, te recordamos tu turno en Elite System.")
                st.markdown(f'<a href="https://wa.me/{tel}?text={msg}" target="_blank"><button style="width:100%; height:38px; background:#25D366; color:white; border:none; border-radius:8px; cursor:pointer;">📱 WhatsApp</button></a>', unsafe_allow_html=True)

# --- MÓDULO 2: REGISTRO & COBRO (INTELIGENCIA DE PAGO) ---
elif menu == "📝 Registro & Cobro":
    st.markdown('<p style="font-size:30px; font-weight:bold;">Registro & Venta Automática</p>', unsafe_allow_html=True)
    
    # Formulario con lógica de precios predictiva
    with st.form("form_v15"):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre Completo")
            dni = st.text_input("DNI")
            whatsapp = st.text_input("WhatsApp (ej: 549...)")
            dx = st.text_area("Diagnóstico (Dx)")
        
        with col2:
            origen = st.selectbox("Origen del Paciente", ["Socio Gimnasio", "Captación Propia"])
            servicio = st.selectbox("Servicio / Plan", list(PRECIOS_BASE.keys()))
            
            # --- LÓGICA DE PRECIO PREDICTIVA ---
            ya_ev = not df_p[(df_p['DNI'].astype(str) == str(dni)) & (df_p['Servicio'] == "Evaluacion")].empty
            if "Masaje" in servicio:
                precio_sugerido = PRECIOS_BASE[servicio]["Socio" if origen == "Socio Gimnasio" else "Gral"]
            else:
                precio_sugerido = PRECIOS_BASE[servicio]
                if servicio == "Evaluacion" and not ya_ev:
                    precio_sugerido = 0 if origen == "Socio Gimnasio" else precio_sugerido * 0.5
            
            st.markdown(f'<span>Valor del Servicio:</span><br><div class="price-badge">${precio_sugerido:,.0f}</div>', unsafe_allow_html=True)
            
            st.divider()
            # --- NUEVA FUNCIÓN DE PAGO ---
            tipo_pago = st.radio("Estado del Cobro:", ["Pago Total", "Seña / Parcial", "Pendiente"], horizontal=True)
            monto_pagado = st.number_input("Monto Recibido ($)", value=float(precio_sugerido))
            
        st.divider()
        st.subheader("Configuración de Turnos")
        c3, c4 = st.columns(2)
        f_ini = c3.date_input("Fecha de Inicio", datetime.now())
        h_ini = c4.time_input("Hora del turno", datetime.now().time())
        dias = st.multiselect("Días (solo para planes)", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])

        if st.form_submit_button("CONSOLIDAR REGISTRO"):
            # Lógica para guardar en Sheets (Simplificada para el ejemplo)
            st.success(f"✅ Registrado: {nombre}. Cobrado: ${monto_pagado}")
            st.rerun()

# --- MÓDULO 3: INTELIGENCIA FINANCIERA ---
elif menu == "📊 Inteligencia Financiera":
    st.markdown('<p style="font-size:30px; font-weight:bold;">Análisis de Rentabilidad</p>', unsafe_allow_html=True)
    if not df_p.empty:
        df_p['Pago'] = pd.to_numeric(df_p['Pago'], errors='coerce').fillna(0)
        bruto = df_p['Pago'].sum()
        neta = bruto - gastos
        
        c1, c2 = st.columns(2)
        c1.metric("Ingresos Totales", f"${bruto:,.0f}")
        c2.metric("Ganancia Neta", f"${neta:,.0f}", delta=f"{(neta/bruto*100):.1f}% de margen" if bruto > 0 else "0%")
        
        fig = px.pie(df_p, values='Pago', names='Servicio', title="Distribución por Servicio", hole=0.5)
        st.plotly_chart(fig, use_container_width=True)
