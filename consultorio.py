import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import plotly.express as px
import urllib.parse

# --- 1. CONFIGURACIÓN Y ESTÉTICA DE ALTA GAMA ---
st.set_page_config(page_title="Elite System V24 - Intelligence", layout="wide", page_icon="🌿")

PRECIOS_BASE = {
    "Evaluacion": 36000, "Sesion Especializada": 36000, "Sesion Individual": 24000,
    "Plan x5": 110000, "Plan x10": 200000,
    "Masaje ZA (piernas y pies)": {"Socio": 25000, "Gral": 30000},
    "Masaje ZB (Espalda y Cabeza)": {"Socio": 25000, "Gral": 30000},
    "Masaje Completo": {"Socio": 38000, "Gral": 45000}
}

BRAND_GREEN = "#60b067"
DARK_ACCENT = "#1E1E1E"

st.markdown(f"""
    <style>
    .stApp {{ background-color: #FFFFFF; color: #1E1E1E; }}
    .turno-card {{
        background: {DARK_ACCENT}; backdrop-filter: blur(10px);
        border-left: 8px solid {BRAND_GREEN}; padding: 20px;
        border-radius: 15px; margin-bottom: 12px; color: white;
    }}
    .price-card {{
        background: linear-gradient(135deg, {BRAND_GREEN}, #4a8c4f);
        color: white; padding: 20px; border-radius: 15px;
        text-align: center; font-size: 28px; font-weight: bold;
        box-shadow: 0 6px 20px rgba(96, 176, 103, 0.4);
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

# --- 3. MOTOR DE SINCRONIZACIÓN Y DESCUENTOS ---
def smart_sync():
    ahora = datetime.now()
    fecha_h = ahora.strftime("%Y-%m-%d")
    hora_h = ahora.strftime("%H:%M")
    
    # Identificar turnos pasados no procesados
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

# --- 4. NAVEGACIÓN PRINCIPAL ---
with st.sidebar:
    st.markdown(f'<h1 style="color:{BRAND_GREEN};">🌿 ELITE SYSTEM</h1>', unsafe_allow_html=True)
    menu = st.radio("MÓDULOS", ["📅 Agenda Predictiva", "📝 Registro & Cobro", "📊 Inteligencia Financiera"])
    st.divider()
    gastos_fijos = st.number_input("Gastos Mensuales ($)", value=0)

# --- MÓDULO 1: AGENDA (HOY Y MAÑANA) ---
if menu == "📅 Agenda Predictiva":
    smart_sync()
    st.title("Gestión de Turnos")
    t1, t2 = st.tabs(["Hoy", "Mañana"])
    
    def render_dia(f_str):
        turnos = df_a[df_a['Fecha'].astype(str) == f_str].sort_values("Hora")
        if turnos.empty: st.info("No hay turnos registrados.")
        for _, t in turnos.iterrows():
            p_data = df_p[df_p['DNI'].astype(str) == str(t.get('DNI',''))]
            restantes = int(p_data['Sesiones_Restantes'].iloc[0]) if not p_data.empty else 0
            
            st.markdown(f"""
            <div class="turno-card">
                <b>{t['Hora']} hs</b> | {t['Paciente']} | <small>{t['Servicio']}</small> | <b>Saldo: {restantes}</b>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            with c1: st.button("🛒 Renovar", key=f"ren_{t['Hora']}_{f_str}")
            with c2: st.button("⚙️ Reagendar", key=f"re_{t['Hora']}_{f_str}")
            with c3:
                link = f"https://wa.me/{t.get('WhatsApp','')}?text=Hola {t['Paciente']}, recordatorio de turno."
                st.markdown(f'<a href="{link}" target="_blank"><button style="width:100%; background:#25D366; color:white; border-radius:8px; height:35px; border:none;">📱 WhatsApp</button></a>', unsafe_allow_html=True)

    with t1: render_dia(datetime.now().strftime("%Y-%m-%d"))
    with t2: render_dia((datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"))

# --- MÓDULO 2: REGISTRO & COBRO DINÁMICO ---
elif menu == "📝 Registro & Cobro":
    st.title("Admisión de Paciente")
    col_f, col_p = st.columns([1.8, 1])
    
    with col_f:
        with st.form("registro_v24"):
            st.subheader("Datos Personales")
            nombre = st.text_input("Nombre Completo")
            dni = st.text_input("DNI")
            whats = st.text_input("WhatsApp")
            dx = st.text_area("Diagnóstico")
            st.divider()
            st.subheader("Agenda Fija")
            f_ini = st.date_input("Fecha Inicio", datetime.now())
            h_fija = st.time_input("Hora del Turno", datetime.now().time())
            dias_fijos = st.multiselect("Días de la Semana", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])
            servicio = st.selectbox("Servicio", list(PRECIOS_BASE.keys()))
            origen = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
            enviar = st.form_submit_button("CONSOLIDAR REGISTRO")

    with col_p:
        st.subheader("Resumen de Pago")
        ya_eval = not df_p[df_p['DNI'].astype(str) == str(dni)].empty
        precio = PRECIOS_BASE[servicio]["Socio" if origen == "Socio Gimnasio" else "Gral"] if "Masaje" in servicio else PRECIOS_BASE[servicio]
        if servicio == "Evaluacion" and not ya_eval:
            precio = 0 if origen == "Socio Gimnasio" else precio * 0.5
        
        st.markdown(f'<div class="price-card"><small>PRECIO SUGERIDO</small><br>${precio:,.0f}</div>', unsafe_allow_html=True)
        pago_final = st.number_input("Pago Recibido ($)", value=float(precio))
        tipo_pago = st.radio("Estado:", ["Pago Total", "Parcial", "Pendiente"], horizontal=True)

        if enviar and nombre and dni:
            cant = 10 if "x10" in servicio else (5 if "x5" in servicio else 1)
            # Guardar Paciente
            nuevo_p = pd.DataFrame([[dni, nombre, whats, dx, origen, servicio, pago_final, f_ini.strftime("%Y-%m-%d"), cant, cant]], columns=df_p.columns)
            # Guardar Agenda Masiva
            d_map = {"Lunes":0, "Martes":1, "Miércoles":2, "Jueves":3, "Viernes":4, "Sábado":5}
            idx_dias = [d_map[d] for d in dias_fijos]
            fechas_plan = []
            curr = f_ini
            while len(fechas_plan) < cant:
                if not dias_fijos or curr.weekday() in idx_dias: fechas_plan.append(curr.strftime("%Y-%m-%d"))
                curr += timedelta(days=1)
            
            nuevo_a = pd.DataFrame([[f, h_fija.strftime("%H:%M"), nombre, servicio, "PENDIENTE", whats, dni] for f in fechas_plan], columns=df_a.columns)
            guardar_datos(pd.concat([df_p, nuevo_p]), "pacientes")
            guardar_datos(pd.concat([df_a, nuevo_a]), "agenda")
            st.success(f"¡Hecho! {len(fechas_plan)} turnos cargados.")
            st.balloons()

# --- MÓDULO 3: INTELIGENCIA & RENTABILIDAD ---
elif menu == "📊 Inteligencia Financiera":
    st.title("Business Intelligence Elite")
    
    # Cálculos Reales
    df_p['Comision'] = df_p.apply(lambda r: r['Pago'] * 0.3 if r['Origen'] == "Socio Gimnasio" else r['Pago'] * 0.2, axis=1)
    bruto = df_p['Pago'].sum()
    neta = bruto - df_p['Comision'].sum() - gastos_fijos
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Utilidad Neta Actual", f"${neta:,.0f}")
    
    # FUNCIÓN: RENTABILIDAD POR DÍA
    df_a['Dia_Semana'] = pd.to_datetime(df_a['Fecha']).dt.day_name()
    # Mapeo a español para claridad
    dias_es = {"Monday":"Lunes", "Tuesday":"Martes", "Wednesday":"Miércoles", "Thursday":"Jueves", "Friday":"Viernes", "Saturday":"Sábado"}
    df_a['Dia'] = df_a['Dia_Semana'].map(dias_es)
    rent_dia = df_a.groupby('Dia').size().reset_index(name='Sesiones')
    orden_dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
    rent_dia['Dia'] = pd.Categorical(rent_dia['Dia'], categories=orden_dias, ordered=True)
    rent_dia = rent_dia.sort_values('Dia')

    c2.metric("Día de mayor flujo", rent_dia.loc[rent_dia['Sesiones'].idxmax(), 'Dia'] if not rent_dia.empty else "N/A")
    
    # Proyección Futura
    t_futuros = df_a[df_a['Fecha'].astype(str) > datetime.now().strftime("%Y-%m-%d")]
    proy_futura = len(t_futuros) * (bruto/len(df_a) if len(df_a)>0 else 0)
    c3.metric("Proyección a Cobrar", f"${proy_futura:,.0f}")

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(px.bar(rent_dia, x='Dia', y='Sesiones', title="Sesiones por Día de la Semana", color_discrete_sequence=[BRAND_GREEN]))
    with col_b:
        df_p['Estado_S'] = df_p['Sesiones_Restantes'].apply(lambda x: "Crítico" if x <= 2 else "Ok")
        st.plotly_chart(px.pie(df_p, names='Estado_S', title="Estado de Renovaciones", hole=0.5, color_discrete_map={"Crítico":"#FF4B4B", "Ok":BRAND_GREEN}))
