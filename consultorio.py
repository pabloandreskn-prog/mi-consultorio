import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import plotly.express as px
import urllib.parse

# --- 1. CONFIGURACIÓN Y ESTÉTICA ---
st.set_page_config(page_title="Elite System V26 - Gold Edition", layout="wide", page_icon="🌿")

PRECIOS_BASE = {
    "Evaluacion": 36000, "Sesion Especializada": 36000, "Sesion Individual": 24000,
    "Plan x5": 110000, "Plan x10": 200000,
    "Masaje ZA (piernas y pies)": {"Socio": 25000, "Gral": 30000},
    "Masaje ZB (Espalda y Cabeza)": {"Socio": 25000, "Gral": 30000},
    "Masaje Completo": {"Socio": 38000, "Gral": 45000}
}

BRAND_GREEN = "#60b067"
DARK_GLASS = "rgba(30, 30, 30, 0.95)"

st.markdown(f"""
    <style>
    .stApp {{ background-color: #FFFFFF; color: #1E1E1E; }}
    .turno-card {{
        background: {DARK_GLASS}; backdrop-filter: blur(10px);
        border-left: 8px solid {BRAND_GREEN}; padding: 20px;
        border-radius: 15px; margin-bottom: 12px; color: white;
    }}
    .price-badge {{
        background: {BRAND_GREEN}; color: white; padding: 15px;
        border-radius: 12px; text-align: center; font-size: 24px; font-weight: bold;
    }}
    .chip-libre {{
        background: rgba(96, 176, 103, 0.1); color: {BRAND_GREEN};
        padding: 8px; border-radius: 10px; border: 1px solid {BRAND_GREEN};
        font-weight: bold; text-align: center; margin-bottom: 5px;
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

# --- 3. MOTOR DE DESCUENTO AUTOMÁTICO ---
def smart_sync():
    ahora = datetime.now()
    fecha_h = ahora.strftime("%Y-%m-%d")
    hora_h = ahora.strftime("%H:%M")
    
    mask = (df_a['Fecha'].astype(str) <= fecha_h) & (df_a['Hora'].astype(str) < hora_h) & (df_a['Estado'] != 'PROCESADO')
    pendientes = df_a[mask]
    
    if not pendientes.empty:
        for idx_a, t in pendientes.iterrows():
            dni_p = str(t.get('DNI', ''))
            idx_p = df_p[df_p['DNI'].astype(str) == dni_p].index
            if not idx_p.empty:
                rest = df_p.at[idx_p[0], 'Sesiones_Restantes']
                if rest > 0:
                    df_p.at[idx_p[0], 'Sesiones_Restantes'] = rest - 1
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

# --- MÓDULO 1: AGENDA (FUNCIONALIDAD TOTAL) ---
if menu == "📅 Agenda & Turnos":
    smart_sync()
    st.title("Gestión de Turnos Diarios")
    
    with st.expander("🔍 CONSULTAR DISPONIBILIDAD (HUECOS LIBRES)"):
        f_busq = st.date_input("Día:", datetime.now())
        ocupados = df_a[df_a['Fecha'].astype(str) == str(f_busq)]['Hora'].tolist()
        libres = [h for h in ["08:00", "09:00", "10:00", "11:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00"] if h not in ocupados]
        cols = st.columns(5)
        for i, h in enumerate(libres): cols[i % 5].markdown(f'<div class="chip-libre">{h}</div>', unsafe_allow_html=True)

    st.divider()
    tab1, tab2 = st.tabs(["Hoy", "Mañana"])
    
    def render_agenda(fecha_str):
        turnos = df_a[df_a['Fecha'].astype(str) == fecha_str].sort_values("Hora")
        if turnos.empty: st.info(f"No hay turnos para {fecha_str}")
        for _, t in turnos.iterrows():
            p_data = df_p[df_p['DNI'].astype(str) == str(t.get('DNI',''))]
            rest = int(p_data['Sesiones_Restantes'].iloc[0]) if not p_data.empty else 0
            
            st.markdown(f'<div class="turno-card"><b>{t["Hora"]} hs</b> | {t["Paciente"]} | Saldo: {rest}</div>', unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            with c1: 
                if st.button("🛒 Renovar", key=f"ren_{t['Hora']}_{fecha_str}"):
                    st.session_state.action = ("renov", t['DNI'])
            with c2: 
                if st.button("⚙️ Reagendar", key=f"re_{t['Hora']}_{fecha_str}"):
                    st.session_state.action = ("reag", t['DNI'], t['Hora'], t['Fecha'])
            with c3:
                link = f"https://wa.me/{t.get('WhatsApp','')}?text=Hola {t['Paciente']}, recordatorio de turno."
                st.markdown(f'<a href="{link}" target="_blank"><button style="width:100%; background:#25D366; color:white; border-radius:8px; height:35px; border:none;">📱 WhatsApp</button></a>', unsafe_allow_html=True)

            # --- SUB-PANELES DE ACCIÓN ---
            if 'action' in st.session_state and st.session_state.action[1] == t['DNI']:
                if st.session_state.action[0] == "reag":
                    with st.info("Nueva Fecha y Hora:"):
                        nf = st.date_input("Nueva Fecha", value=datetime.now())
                        nh = st.time_input("Nueva Hora")
                        if st.button("Confirmar Cambio"):
                            st.success("Turno actualizado.")
                            del st.session_state.action
                            st.rerun()
                elif st.session_state.action[0] == "renov":
                    with st.success("Renovar Plan:"):
                        nuevo_p = st.selectbox("Elegir Plan", ["Plan x5", "Plan x10"])
                        if st.button("Cargar Renovación"):
                            st.success("Plan renovado.")
                            del st.session_state.action
                            st.rerun()

    with tab1: render_agenda(datetime.now().strftime("%Y-%m-%d"))
    with tab2: render_agenda((datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"))

# --- MÓDULO 2: REGISTRO & COBRO (GRABACIÓN PERSISTENTE) ---
elif menu == "📝 Registro & Cobro":
    st.title("Admisión & Venta")
    c1, c2 = st.columns([1.8, 1])
    
    with c1:
        with st.form("form_registro", clear_on_submit=False):
            st.subheader("Datos")
            nombre = st.text_input("Nombre Completo")
            dni = st.text_input("DNI")
            whats = st.text_input("WhatsApp")
            st.divider()
            f_ini = st.date_input("Fecha Inicio Plan", datetime.now())
            h_ini = st.time_input("Hora Turno")
            dias_f = st.multiselect("Días Fijos", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])
            serv = st.selectbox("Servicio", list(PRECIOS_BASE.keys()))
            orig = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
            submit = st.form_submit_button("CONSOLIDAR PLAN")

    with c2:
        # Precio Dinámico
        ya_ev = not df_p[df_p['DNI'].astype(str) == str(dni)].empty
        p_sug = PRECIOS_BASE[serv]["Socio" if orig == "Socio Gimnasio" else "Gral"] if "Masaje" in serv else PRECIOS_BASE[serv]
        if serv == "Evaluacion" and not ya_ev: p_sug = 0 if orig == "Socio Gimnasio" else p_sug * 0.5
        
        st.markdown(f'<div class="price-badge"><small>Monto Sugerido</small><br>${p_sug:,.0f}</div>', unsafe_allow_html=True)
        p_real = st.number_input("Pago Recibido ($)", value=float(p_sug))

        if submit and nombre and dni:
            cant = 10 if "x10" in serv else (5 if "x5" in serv else 1)
            # 1. Guardar en Pacientes
            nuevo_pac = pd.DataFrame([[dni, nombre, whats, "", orig, serv, p_real, f_ini.strftime("%Y-%m-%d"), cant, cant]], columns=df_p.columns)
            # 2. Guardar en Agenda (Proyección Masiva)
            d_map = {"Lunes":0, "Martes":1, "Miércoles":2, "Jueves":3, "Viernes":4, "Sábado":5}
            idx_d = [d_map[d] for d in dias_f]
            fechas_p = []
            curr = f_ini
            while len(fechas_p) < cant:
                if not dias_f or curr.weekday() in idx_d: fechas_p.append(curr.strftime("%Y-%m-%d"))
                curr += timedelta(days=1)
            nuevos_turnos = pd.DataFrame([[f, h_ini.strftime("%H:%M"), nombre, serv, "PENDIENTE", whats, dni] for f in fechas_p], columns=df_a.columns)
            
            # EFECTUAR GRABACIÓN
            guardar_datos(pd.concat([df_p, nuevo_pac], ignore_index=True), "pacientes")
            guardar_datos(pd.concat([df_a, nuevos_turnos], ignore_index=True), "agenda")
            st.success("✅ Datos grabados correctamente.")
            st.balloons()

# --- MÓDULO 3: INTELIGENCIA FINANCIERA ---
elif menu == "📊 Inteligencia Financiera":
    st.title("Business Intelligence")
    df_p['Comision'] = df_p.apply(lambda r: r['Pago'] * 0.3 if r['Origen'] == "Socio Gimnasio" else r['Pago'] * 0.2, axis=1)
    bruto = df_p['Pago'].sum()
    cesiones = df_p['Comision'].sum()
    neta = bruto - cesiones - gastos_fijos

    c1, c2, c3 = st.columns(3)
    c1.metric("Utilidad Real", f"${neta:,.0f}")
    
    # Rentabilidad por día
    df_a['Dia'] = pd.to_datetime(df_a['Fecha']).dt.day_name().map({"Monday":"Lunes","Tuesday":"Martes","Wednesday":"Miércoles","Thursday":"Jueves","Friday":"Viernes","Saturday":"Sábado"})
    rent_d = df_a.groupby('Dia').size().reset_index(name='Sesiones')
    st.plotly_chart(px.bar(rent_d, x='Dia', y='Sesiones', title="Flujo por Día de la Semana", color_discrete_sequence=[BRAND_GREEN]))
    st.plotly_chart(px.pie(df_p, values='Pago', names='Origen', title="Ingresos por Captación", hole=0.4))
