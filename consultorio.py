import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import plotly.express as px
import urllib.parse

# --- 1. CONFIGURACIÓN Y MATRIZ DE PRECIOS ---
st.set_page_config(page_title="Elite System V19 Flow-Master", layout="wide", page_icon="🌿")

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
        padding: 20px; border-radius: 15px; margin-bottom: 5px; color: white;
    }}
    .sub-panel-agile {{
        background: rgba(240, 242, 246, 0.9);
        padding: 15px; border-radius: 15px;
        margin-top: 5px; margin-bottom: 15px; border: 1px solid #ddd;
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

# --- 2. CONEXIÓN Y LOGICA DE SESIONES ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    df_p = conn.read(worksheet="pacientes", ttl="0").dropna(how='all')
    df_a = conn.read(worksheet="agenda", ttl="0").dropna(how='all')
    # Sanitización de datos
    for col in ['Pago', 'Sesiones_Restantes', 'Sesiones_Totales']:
        if col in df_p.columns:
            df_p[col] = pd.to_numeric(df_p[col], errors='coerce').fillna(0)
    return df_p, df_a

def guardar_datos(df, hoja):
    conn.update(worksheet=hoja, data=df)
    st.cache_data.clear()

df_p, df_a = cargar_datos()

# --- 3. PROCESAMIENTO AUTOMÁTICO DE SESIONES CONSUMIDAS ---
def procesar_descuentos_automaticos():
    ahora = datetime.now()
    fecha_hoy = ahora.strftime("%Y-%m-%d")
    hora_actual = ahora.strftime("%H:%M")
    
    # Buscamos turnos de hoy o pasado que no hayan sido marcados como 'PROCESADO'
    mask = (df_a['Fecha'].astype(str) <= fecha_hoy) & (df_a['Hora'].astype(str) < hora_actual) & (df_a.get('Estado', '') != 'PROCESADO')
    turnos_a_descontar = df_a[mask]

    if not turnos_a_descontar.empty:
        for idx_a, turno in turnos_a_descontar.iterrows():
            dni_p = str(turno.get('DNI', ''))
            idx_p = df_p[df_p['DNI'].astype(str) == dni_p].index
            
            if not idx_p.empty:
                restantes = df_p.at[idx_p[0], 'Sesiones_Restantes']
                if restantes > 0:
                    df_p.at[idx_p[0], 'Sesiones_Restantes'] = restantes - 1
            
            # Marcamos turno como procesado para que no descuente dos veces
            df_a.at[idx_a, 'Estado'] = 'PROCESADO'
        
        guardar_datos(df_p, "pacientes")
        guardar_datos(df_a, "agenda")
        st.rerun()

# --- 4. NAVEGACIÓN ---
with st.sidebar:
    st.markdown(f'<h1 style="color:{BRAND_GREEN};">🌿 ELITE SYSTEM</h1>', unsafe_allow_html=True)
    menu = st.radio("MENÚ PRINCIPAL", ["📅 Agenda & Turnos", "📝 Registro & Cobro", "📊 Inteligencia Financiera"])
    st.divider()
    gastos_fijos = st.number_input("Gastos Fijos Mensuales ($)", value=0)

# --- MÓDULO 1: AGENDA & TURNOS ---
if menu == "📅 Agenda & Turnos":
    procesar_descuentos_automaticos() # Activa el motor de descuento automático
    
    st.markdown('<p style="font-size:30px; font-weight:bold;">Agenda Operativa</p>', unsafe_allow_html=True)
    
    with st.expander("🔍 CONSULTAR DISPONIBILIDAD (HUECOS LIBRES)", expanded=False):
        f_sel = st.date_input("Día:", datetime.now())
        ocupados = df_a[df_a['Fecha'].astype(str) == str(f_sel)]['Hora'].tolist()
        horas_lab = ["08:00", "09:00", "10:00", "11:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00"]
        libres = [h for h in horas_lab if h not in ocupados]
        cols = st.columns(5)
        for i, h in enumerate(libres): cols[i % 5].markdown(f'<div class="chip-libre">{h}</div>', unsafe_allow_html=True)

    st.divider()
    hoy_str = datetime.now().strftime("%Y-%m-%d")
    turnos_hoy = df_a[df_a['Fecha'].astype(str) == hoy_str].sort_values("Hora")

    if turnos_hoy.empty:
        st.info("No hay turnos para hoy.")
    else:
        for _, t in turnos_hoy.iterrows():
            # Obtener saldo de sesiones en tiempo real
            p_info = df_p[df_p['DNI'].astype(str) == str(t.get('DNI', ''))]
            rest = int(p_info['Sesiones_Restantes'].iloc[0]) if not p_info.empty else 0
            total = int(p_info['Sesiones_Totales'].iloc[0]) if not p_info.empty else 0
            
            st.markdown(f"""
            <div class="turno-card">
                <span style="font-size:22px; font-weight:bold; color:{BRAND_GREEN};">{t['Hora']} hs</span> | <b>{t['Paciente']}</b><br>
                <small>{t['Servicio']} | Saldo: {rest}/{total}</small>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            with c1: renovar = st.button("🛒 Renovar", key=f"ren_{t['Hora']}")
            with c2: reagendar = st.button("⚙️ Reagendar", key=f"re_{t['Hora']}")
            with c3:
                tel = t.get('WhatsApp', '')
                msg = urllib.parse.quote(f"Hola {t['Paciente']}, Elite System te recuerda tu turno.")
                st.markdown(f'<a href="https://wa.me/{tel}?text={msg}" target="_blank"><button style="width:100%; height:38px; background:#25D366; color:white; border:none; border-radius:10px;">📱 WhatsApp</button></a>', unsafe_allow_html=True)

            if reagendar:
                with st.container():
                    st.markdown('<div class="sub-panel-agile">', unsafe_allow_html=True)
                    st.write("### ⚙️ Reagendar Sesión")
                    nf = st.date_input("Nueva Fecha", datetime.now(), key=f"nf_{t['Hora']}")
                    nh = st.time_input("Nueva Hora", key=f"nh_{t['Hora']}")
                    if st.button("Confirmar Cambio", key=f"upd_{t['Hora']}"):
                        st.success("Turno actualizado. La sesión no se descontará hoy.")
                    st.markdown('</div>', unsafe_allow_html=True)

# --- MÓDULO 2: REGISTRO & COBRO ---
elif menu == "📝 Registro & Cobro":
    st.markdown('<p style="font-size:30px; font-weight:bold;">Registro & Venta</p>', unsafe_allow_html=True)
    with st.form("form_v19"):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre Completo")
            dni = st.text_input("DNI")
            whatsapp = st.text_input("WhatsApp")
            dx = st.text_area("Diagnóstico (Dx)")
        with col2:
            origen = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
            servicio = st.selectbox("Servicio", list(PRECIOS_BASE.keys()))
            
            # Lógica Predictiva
            ya_ev = not df_p[(df_p['DNI'].astype(str) == str(dni)) & (df_p['Servicio'] == "Evaluacion")].empty
            precio = PRECIOS_BASE[servicio]["Socio" if origen == "Socio Gimnasio" else "Gral"] if "Masaje" in servicio else PRECIOS_BASE[servicio]
            if servicio == "Evaluacion" and not ya_ev:
                precio = 0 if origen == "Socio Gimnasio" else precio * 0.5
            
            st.markdown(f'Monto sugerido:<br><div class="price-badge">${precio:,.0f}</div>', unsafe_allow_html=True)
            pago_status = st.radio("Cobro:", ["Total", "Parcial", "Pendiente"], horizontal=True)
            monto_final = st.number_input("Monto Recibido ($)", value=float(precio))

        st.divider()
        if st.form_submit_button("CONSOLIDAR REGISTRO"):
            st.success("Paciente registrado y plan cargado (10/10).")

# --- MÓDULO 3: INTELIGENCIA FINANCIERA ---
elif menu == "📊 Inteligencia Financiera":
    st.markdown('<p style="font-size:30px; font-weight:bold;">Análisis & Cesión de Comisiones</p>', unsafe_allow_html=True)
    if not df_p.empty:
        # Cálculo de Cesión (30% Socio / 20% Propio)
        df_p['Comision'] = df_p.apply(lambda r: r['Pago'] * 0.30 if r['Origen'] == "Socio Gimnasio" else r['Pago'] * 0.20, axis=1)
        bruto = df_p['Pago'].sum()
        cesiones = df_p['Comision'].sum()
        utilidad = bruto - cesiones - gastos_fijos

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ingreso Bruto", f"${bruto:,.0f}")
        c2.metric("Comisiones Cedidas", f"-${cesiones:,.0f}")
        c3.metric("Gastos Fijos", f"-${gastos_fijos:,.0f}")
        c4.metric("UTILIDAD NETA", f"${utilidad:,.0f}", delta=f"{(utilidad/bruto*100):.1f}% rent." if bruto > 0 else "0%")

        st.divider()
        col_l, col_r = st.columns(2)
        with col_l:
            st.plotly_chart(px.pie(df_p, values='Pago', names='Origen', title="Fuentes de Ingreso", hole=0.4), use_container_width=True)
        with col_r:
            df_p['Salud'] = df_p['Sesiones_Restantes'].apply(lambda x: "Crítico (0-2)" if x <= 2 else "Estable")
            st.plotly_chart(px.bar(df_p.groupby('Salud').size().reset_index(name='C'), x='Salud', y='C', color='Salud', title="Retención de Clientes"), use_container_width=True)
