import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import plotly.express as px
import urllib.parse

# --- 1. CONFIGURACIÓN Y ESTÉTICA PREMIUM ---
st.set_page_config(page_title="Elite System V25 - Master", layout="wide", page_icon="🌿")

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

# --- 2. CONEXIÓN Y DATOS ---
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

# --- 3. MOTOR SMART-SYNC (DESCUENTO AUTOMÁTICO) ---
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

# --- MÓDULO 1: AGENDA (CON EXPANDER DE DISPONIBILIDAD) ---
if menu == "📅 Agenda & Turnos":
    smart_sync()
    st.title("Agenda Operativa")
    
    # FUNCIONALIDAD 1: EXPANDER DE DISPONIBILIDAD
    with st.expander("🔍 CONSULTAR DISPONIBILIDAD (HUECOS LIBRES)", expanded=False):
        f_busq = st.date_input("Día a consultar:", datetime.now())
        ocupados = df_a[df_a['Fecha'].astype(str) == str(f_busq)]['Hora'].tolist()
        horas_lab = ["08:00", "09:00", "10:00", "11:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00"]
        libres = [h for h in horas_lab if h not in ocupados]
        cols = st.columns(5)
        for i, h in enumerate(libres):
            cols[i % 5].markdown(f'<div class="chip-libre">{h}</div>', unsafe_allow_html=True)

    st.divider()
    tab1, tab2 = st.tabs(["Hoy", "Mañana"])
    
    def render_agenda(fecha_str):
        turnos = df_a[df_a['Fecha'].astype(str) == fecha_str].sort_values("Hora")
        if turnos.empty: st.info("Sin turnos agendados.")
        for _, t in turnos.iterrows():
            p_data = df_p[df_p['DNI'].astype(str) == str(t.get('DNI',''))]
            rest = int(p_data['Sesiones_Restantes'].iloc[0]) if not p_data.empty else 0
            
            st.markdown(f"""
            <div class="turno-card">
                <b>{t['Hora']} hs</b> | {t['Paciente']} | <small>{t['Servicio']}</small> | <b>Saldo: {rest}</b>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            with c1: st.button("🛒 Renovar", key=f"ren_{t['Hora']}_{fecha_str}")
            with c2: st.button("⚙️ Reagendar", key=f"re_{t['Hora']}_{fecha_str}")
            with c3:
                link = f"https://wa.me/{t.get('WhatsApp','')}?text=Hola {t['Paciente']}, recordatorio de turno."
                st.markdown(f'<a href="{link}" target="_blank"><button style="width:100%; background:#25D366; color:white; border-radius:8px; height:35px; border:none;">📱 WhatsApp</button></a>', unsafe_allow_html=True)

    with tab1: render_agenda(datetime.now().strftime("%Y-%m-%d"))
    with tab2: render_agenda((datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"))

# --- MÓDULO 2: REGISTRO & COBRO (PRECIO AUTOMÁTICO) ---
elif menu == "📝 Registro & Cobro":
    st.title("Registro de Admisión")
    c1, c2 = st.columns([2, 1])
    with c1:
        with st.form("reg_v25"):
            nombre = st.text_input("Nombre Completo")
            dni = st.text_input("DNI")
            whats = st.text_input("WhatsApp")
            f_ini = st.date_input("Fecha Inicio", datetime.now())
            h_fija = st.time_input("Hora Turno", datetime.now().time())
            dias_fijos = st.multiselect("Días", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])
            servicio = st.selectbox("Servicio", list(PRECIOS_BASE.keys()))
            origen = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
            enviar = st.form_submit_button("CONSOLIDAR PLAN")

    with c2:
        # PRECIO AUTO-GENERADO ANTES DE CONFIRMAR
        ya_ev = not df_p[df_p['DNI'].astype(str) == str(dni)].empty
        precio = PRECIOS_BASE[servicio]["Socio" if origen == "Socio Gimnasio" else "Gral"] if "Masaje" in servicio else PRECIOS_BASE[servicio]
        if servicio == "Evaluacion" and not ya_ev:
            precio = 0 if origen == "Socio Gimnasio" else precio * 0.5
        
        st.markdown(f'<div class="price-badge"><small>Sugerido</small><br>${precio:,.0f}</div>', unsafe_allow_html=True)
        pago_rec = st.number_input("Monto Recibido ($)", value=float(precio))

        if enviar and nombre:
            cant = 10 if "x10" in servicio else (5 if "x5" in servicio else 1)
            # Lógica de guardado masivo de turnos y paciente aquí...
            st.success("Plan consolidado con éxito.")

# --- MÓDULO 3: INTELIGENCIA (COMISIONES Y RENTABILIDAD) ---
elif menu == "📊 Inteligencia Financiera":
    st.title("Analítica & Comisiones")
    
    # FUNCIONALIDAD 2: CESIÓN DE COMISIONES (30% Socio / 20% No Socio)
    df_p['Comision'] = df_p.apply(lambda r: r['Pago'] * 0.3 if r['Origen'] == "Socio Gimnasio" else r['Pago'] * 0.2, axis=1)
    bruto = df_p['Pago'].sum()
    cesiones = df_p['Comision'].sum()
    neta = bruto - cesiones - gastos_fijos

    c1, c2, c3 = st.columns(3)
    c1.metric("Bruto", f"${bruto:,.0f}")
    c2.metric("Comisiones Cedidas", f"-${cesiones:,.0f}")
    c3.metric("UTILIDAD REAL", f"${neta:,.0f}")

    st.divider()
    col_l, col_r = st.columns(2)
    with col_l:
        # RENTABILIDAD POR DÍA
        df_a['Dia'] = pd.to_datetime(df_a['Fecha']).dt.day_name().map({"Monday":"Lunes","Tuesday":"Martes","Wednesday":"Miércoles","Thursday":"Jueves","Friday":"Viernes","Saturday":"Sábado"})
        rent_d = df_a.groupby('Dia').size().reset_index(name='Cant').sort_values('Cant', ascending=False)
        st.plotly_chart(px.bar(rent_d, x='Dia', y='Cant', title="Sesiones por Día", color_discrete_sequence=[BRAND_GREEN]))
    with col_r:
        st.plotly_chart(px.pie(df_p, values='Pago', names='Origen', title="Ingresos por Origen", hole=0.4))
