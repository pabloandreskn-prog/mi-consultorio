import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import plotly.express as px
import urllib.parse

# --- 1. CONFIGURACIÓN DE ÉLITE ---
st.set_page_config(page_title="Elite System V22 Infinity", layout="wide", page_icon="🌿")

PRECIOS_BASE = {
    "Evaluacion": 36000, "Sesion Especializada": 36000, "Sesion Individual": 24000,
    "Plan x5": 110000, "Plan x10": 200000,
    "Masaje ZA (piernas y pies)": {"Socio": 25000, "Gral": 30000},
    "Masaje ZB (Espalda y Cabeza)": {"Socio": 25000, "Gral": 30000},
    "Masaje Completo": {"Socio": 38000, "Gral": 45000}
}

BRAND_GREEN = "#60b067"
DARK_GLASS = "rgba(20, 20, 20, 0.9)"

st.markdown(f"""
    <style>
    .stApp {{ background-color: #FFFFFF; color: #1E1E1E; }}
    .main-title {{ font-size: 32px; font-weight: 800; color: {BRAND_GREEN}; margin-bottom: 20px; }}
    .turno-card {{
        background: {DARK_GLASS}; backdrop-filter: blur(10px);
        border-left: 6px solid {BRAND_GREEN}; padding: 20px;
        border-radius: 15px; margin-bottom: 12px; color: white;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }}
    .price-card {{
        background: linear-gradient(135deg, {BRAND_GREEN}, #4a8c4f);
        color: white; padding: 20px; border-radius: 15px;
        text-align: center; font-size: 28px; font-weight: bold;
        box-shadow: 0 6px 20px rgba(96, 176, 103, 0.4);
    }}
    .status-badge {{
        background: rgba(255,255,255,0.1); padding: 4px 10px;
        border-radius: 6px; font-size: 12px;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN Y PERSISTENCIA ---
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

# --- 3. MOTOR DE DESCUENTO AUTOMÁTICO (SMART-SYNC) ---
def sincronizar_sesiones():
    ahora = datetime.now()
    fecha_hoy = ahora.strftime("%Y-%m-%d")
    hora_actual = ahora.strftime("%H:%M")
    
    # Filtrar turnos pasados no procesados
    mask = (df_a['Fecha'].astype(str) <= fecha_hoy) & \
           (df_a['Hora'].astype(str) < hora_actual) & \
           (df_a['Estado'] != 'PROCESADO')
    
    turnos_pasados = df_a[mask]
    
    if not turnos_pasados.empty:
        for idx_a, t in turnos_pasados.iterrows():
            dni_p = str(t.get('DNI', ''))
            idx_p = df_p[df_p['DNI'].astype(str) == dni_p].index
            if not idx_p.empty:
                val = df_p.at[idx_p[0], 'Sesiones_Restantes']
                if val > 0:
                    df_p.at[idx_p[0], 'Sesiones_Restantes'] = val - 1
            df_a.at[idx_a, 'Estado'] = 'PROCESADO'
        
        guardar_datos(df_p, "pacientes")
        guardar_datos(df_a, "agenda")
        st.rerun()

# --- 4. INTERFAZ Y NAVEGACIÓN ---
with st.sidebar:
    st.markdown(f'<h1 style="color:{BRAND_GREEN};">🌿 ELITE SYSTEM</h1>', unsafe_allow_html=True)
    menu = st.radio("SISTEMA DE GESTIÓN", ["📅 Agenda Predictiva", "📝 Registro & Cobro", "📊 Inteligencia de Negocio"])
    st.divider()
    gastos_fijos = st.number_input("Gastos Fijos Mensuales ($)", value=0)
    st.info("V22 Infinity - Operativo")

# --- MÓDULO 1: AGENDA PREDICTIVA ---
if menu == "📅 Agenda Predictiva":
    sincronizar_sesiones()
    st.markdown('<p class="main-title">Agenda Operativa</p>', unsafe_allow_html=True)
    
    with st.expander("🔍 CONSULTAR DISPONIBILIDAD (HUECOS LIBRES)"):
        f_busq = st.date_input("Ver día:", datetime.now())
        ocupados = df_a[df_a['Fecha'].astype(str) == str(f_busq)]['Hora'].tolist()
        libres = [h for h in ["08:00", "09:00", "10:00", "11:00", "14:00", "15:00", "16:00", "17:00", "18:00"] if h not in ocupados]
        cols = st.columns(len(libres) if libres else 1)
        for i, h in enumerate(libres): cols[i].markdown(f'<div style="text-align:center; color:{BRAND_GREEN};"><b>{h}</b></div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📋 TURNOS DE HOY", "📋 TURNOS DE MAÑANA"])
    
    def render_agenda(fecha_str):
        turnos = df_a[df_a['Fecha'].astype(str) == fecha_str].sort_values("Hora")
        if turnos.empty:
            st.write("No hay pacientes agendados.")
        else:
            for _, t in turnos.iterrows():
                p_info = df_p[df_p['DNI'].astype(str) == str(t.get('DNI',''))]
                rest = int(p_info['Sesiones_Restantes'].iloc[0]) if not p_info.empty else 0
                
                st.markdown(f"""
                <div class="turno-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="font-size: 22px; font-weight: bold; color: {BRAND_GREEN};">{t['Hora']} hs</span> | {t['Paciente']} <br>
                            <span class="status-badge">{t['Servicio']}</span>
                        </div>
                        <div style="text-align: right;">
                            <span style="font-size: 18px; font-weight: bold;">{rest}</span><br><small>restantes</small>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                c1, c2, c3 = st.columns(3)
                with c1: st.button("🛒 Renovar", key=f"ren_{t['Hora']}_{fecha_str}")
                with c2: st.button("⚙️ Reagendar", key=f"re_{t['Hora']}_{fecha_str}")
                with c3:
                    tel = t.get('WhatsApp', '')
                    msg = urllib.parse.quote(f"Hola {t['Paciente']}, te escribo de Elite System...")
                    st.markdown(f'<a href="https://wa.me/{tel}?text={msg}" target="_blank"><button style="width:100%; border-radius:10px; height:38px; background:#25D366; color:white; border:none; cursor:pointer;">📱 WhatsApp</button></a>', unsafe_allow_html=True)

    with tab1: render_agenda(datetime.now().strftime("%Y-%m-%d"))
    with tab2: render_agenda((datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"))

# --- MÓDULO 2: REGISTRO & COBRO DINÁMICO ---
elif menu == "📝 Registro & Cobro":
    st.markdown('<p class="main-title">Nueva Admisión & Venta</p>', unsafe_allow_html=True)
    
    c1, c2 = st.columns([1.8, 1])
    
    with c1:
        with st.form("registro_infinity"):
            st.subheader("📝 Datos del Paciente")
            nom = st.text_input("Nombre y Apellido")
            id_dni = st.text_input("DNI")
            tel = st.text_input("WhatsApp")
            diag = st.text_area("Diagnóstico / Notas")
            
            st.divider()
            st.subheader("📅 Planificación del Plan")
            f_ini = st.date_input("Fecha Inicio", datetime.now())
            h_fija = st.time_input("Hora fija", datetime.now().time())
            dias = st.multiselect("Días de frecuencia", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])
            
            serv = st.selectbox("Servicio / Plan", list(PRECIOS_BASE.keys()))
            ori = st.selectbox("Origen del Paciente", ["Socio Gimnasio", "Captación Propia"])
            
            consolidar = st.form_submit_button("CONSOLIDAR Y AGENDAR PLAN")

    with c2:
        st.subheader("💰 Resumen de Cobro")
        # Lógica de Precio Automática
        ya_eval = not df_p[(df_p['DNI'].astype(str) == str(id_dni)) & (df_p['Servicio'] == "Evaluacion")].empty
        if "Masaje" in serv:
            monto_sug = PRECIOS_BASE[serv]["Socio" if ori == "Socio Gimnasio" else "Gral"]
        else:
            monto_sug = PRECIOS_BASE[serv]
            if serv == "Evaluacion" and not ya_eval:
                monto_sug = 0 if ori == "Socio Gimnasio" else monto_sug * 0.5
        
        st.markdown(f'<div class="price-card"><small>PRECIO SUGERIDO</small><br>${monto_sug:,.0f}</div>', unsafe_allow_html=True)
        pago_final = st.number_input("Monto a percibir ($)", value=float(monto_sug))
        
        if consolidar:
            if not nom or not id_dni:
                st.error("Nombre y DNI son obligatorios.")
            else:
                cant = 10 if "x10" in serv else (5 if "x5" in serv else 1)
                # Guardar Paciente
                new_p = pd.DataFrame([[id_dni, nom, tel, diag, ori, serv, pago_final, f_ini.strftime("%Y-%m-%d"), cant, cant]], columns=df_p.columns)
                # Guardar Agenda Masiva
                d_map = {"Lunes":0, "Martes":1, "Miércoles":2, "Jueves":3, "Viernes":4, "Sábado":5}
                indices = [d_map[d] for d in dias]
                f_plan = []
                curr = f_ini
                while len(f_plan) < cant:
                    if not dias or curr.weekday() in indices: f_plan.append(curr.strftime("%Y-%m-%d"))
                    curr += timedelta(days=1)
                
                new_a = pd.DataFrame([[f, h_fija.strftime("%H:%M"), nom, serv, "PENDIENTE", tel, id_dni] for f in f_plan], columns=df_a.columns)
                
                guardar_datos(pd.concat([df_p, new_p]), "pacientes")
                guardar_datos(pd.concat([df_a, new_a]), "agenda")
                st.success(f"Plan de {cant} sesiones creado para {nom}")
                st.balloons()

# --- MÓDULO 3: INTELIGENCIA FINANCIERA ---
elif menu == "📊 Inteligencia de Negocio":
    st.markdown('<p class="main-title">Analítica Financiera</p>', unsafe_allow_html=True)
    
    df_p['Comision'] = df_p.apply(lambda r: r['Pago'] * 0.3 if r['Origen'] == "Socio Gimnasio" else r['Pago'] * 0.2, axis=1)
    bruto = df_p['Pago'].sum()
    cesiones = df_p['Comision'].sum()
    neta = bruto - cesiones - gastos_fijos

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ingresos Brutos", f"${bruto:,.0f}")
    c2.metric("Comisiones Cedidas", f"-${cesiones:,.0f}", delta_color="inverse")
    c3.metric("Gastos Fijos", f"-${gastos_fijos:,.0f}")
    c4.metric("UTILIDAD REAL", f"${neta:,.0f}", delta=f"{(neta/bruto*100 if bruto>0 else 0):.1f}% margen")

    st.divider()
    col_l, col_r = st.columns(2)
    with col_l:
        st.plotly_chart(px.pie(df_p, values='Pago', names='Origen', title="Ingresos por Captación", hole=0.5, color_discrete_sequence=[BRAND_GREEN, "#2e7d32"]), use_container_width=True)
    with col_r:
        df_p['Salud'] = df_p['Sesiones_Restantes'].apply(lambda x: "Crítico (Renovar)" if x <= 2 else "Activo")
        st.plotly_chart(px.bar(df_p.groupby('Salud').size().reset_index(name='Cant'), x='Salud', y='Cant', color='Salud', color_discrete_map={"Crítico (Renovar)":"#FF4B4B", "Activo":BRAND_GREEN}), use_container_width=True)
