import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import plotly.express as px

# --- 1. CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="Elite System Ultra V9", layout="wide", page_icon="🌿")

BRAND_GREEN = "#60b067"
LIGHT_GREEN = "#90ee90"
WARNING_GOLD = "#ffcc00"

st.markdown(f"""
    <style>
    /* Fondo General Blanco */
    .stApp {{ background-color: #FFFFFF; color: #1E1E1E; }}
    
    .main-title {{ color: {BRAND_GREEN}; font-size: 32px; font-weight: bold; margin-bottom: 20px; }}
    
    /* Tarjetas Esmeriladas Negras */
    .turno-card {{
        background: rgba(30, 30, 30, 0.9);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-left: 6px solid {BRAND_GREEN};
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 15px;
        color: white;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.15);
    }}
    
    /* Alertas de Sesiones */
    .alerta-penultima {{
        background-color: {WARNING_GOLD};
        color: #333;
        padding: 6px 12px;
        border-radius: 8px;
        font-weight: bold;
        display: inline-block;
        margin-top: 10px;
        font-size: 12px;
    }}
    
    .alerta-final {{
        background-color: {LIGHT_GREEN};
        color: #1a5c1a;
        padding: 6px 12px;
        border-radius: 8px;
        font-weight: bold;
        display: inline-block;
        margin-top: 10px;
        font-size: 12px;
    }}

    /* Chips de Disponibilidad */
    .chip-libre {{
        background: rgba(96, 176, 103, 0.1);
        color: {BRAND_GREEN};
        padding: 8px;
        border-radius: 10px;
        border: 1px solid {BRAND_GREEN};
        font-weight: bold;
        text-align: center;
        margin-bottom: 5px;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN Y CARGA DE DATOS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_nube(pestana):
    return conn.read(worksheet=pestana, ttl="0").dropna(how='all')

SERVICIOS_DISPONIBLES = [
    "Evaluacion", "Sesion Especializada", "Sesion Individual", 
    "Plan x5", "Plan x10", "Masaje ZA (piernas y pies)", 
    "Masaje ZB (Espalda y Cabeza)", "Masaje Completo"
]

COL_PACIENTES = ["DNI", "Nombre", "Contacto", "Dx", "Origen", "Servicio", "Pago", "Fecha", "Sesiones_Totales", "Sesiones_Restantes"]
COL_AGENDA = ["Fecha", "Hora", "Paciente", "Servicio", "Estado", "Contacto"]

# --- 3. FUNCIONES DE LÓGICA ---
def calcular_fechas_fijas(fecha_inicio, dias_semana, cantidad):
    dias_map = {"Lunes": 0, "Martes": 1, "Miércoles": 2, "Jueves": 3, "Viernes": 4, "Sábado": 5}
    nums_objetivo = [dias_map[d] for d in dias_semana]
    fechas_generadas = []
    fecha_actual = fecha_inicio
    while len(fechas_generadas) < cantidad:
        if fecha_actual.weekday() in nums_objetivo:
            fechas_generadas.append(str(fecha_actual))
        fecha_actual += timedelta(days=1)
    return fechas_generadas

def obtener_disponibilidad(df_agenda, fecha):
    horas_laborales = ["08:00", "09:00", "10:00", "11:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00"]
    ocupados = df_agenda[df_agenda['Fecha'].astype(str) == str(fecha)]['Hora'].tolist()
    return [h for h in horas_laborales if h not in ocupados]

# --- 4. NAVEGACIÓN ---
with st.sidebar:
    st.markdown(f'<h1 style="color:{BRAND_GREEN};">🌿 ELITE SYSTEM</h1>', unsafe_allow_html=True)
    menu = st.radio("MENÚ", ["📅 Agenda & Turnos", "📝 Registro & Cobro", "📊 Inteligencia Financiera"])

# --- MÓDULO 1: AGENDA & TURNOS (UNIFICADO) ---
if menu == "📅 Agenda & Turnos":
    st.markdown('<p class="main-title">Agenda & Control de Sesiones</p>', unsafe_allow_html=True)
    df_a = cargar_nube("agenda")
    df_p = cargar_nube("pacientes")
    hoy = datetime.now().date()

    # --- Vista de Disponibilidad Integrada ---
    with st.expander("🔍 CONSULTAR TURNOS DISPONIBLES", expanded=False):
        c_f, _ = st.columns([1, 2])
        fecha_sel = c_f.date_input("Seleccionar día:", hoy)
        libres = obtener_disponibilidad(df_a, fecha_sel)
        if libres:
            st.write(f"Huecos libres para el {fecha_sel}:")
            cols = st.columns(5)
            for i, h in enumerate(libres):
                cols[i % 5].markdown(f'<div class="chip-libre">🕒 {h}</div>', unsafe_allow_html=True)
        else:
            st.warning("No hay turnos disponibles para esta fecha.")

    st.divider()

    # --- Listado de Turnos del Día ---
    t_hoy = df_a[df_a['Fecha'].astype(str) == str(hoy)].sort_values("Hora")
    if t_hoy.empty:
        st.info("No hay turnos agendados para hoy.")
    else:
        for _, t in t_hoy.iterrows():
            # Obtener sesiones restantes
            p_data = df_p[df_p['Nombre'] == t['Paciente']]
            rest = pd.to_numeric(p_data['Sesiones_Restantes'].iloc[-1], errors='coerce') if not p_data.empty else 10
            
            with st.container():
                col_card, col_btns = st.columns([3, 1])
                with col_card:
                    # Lógica de alertas visuales
                    alerta = ""
                    if rest == 2:
                        alerta = "<div class='alerta-penultima'>⚠️ PENÚLTIMA SESIÓN: Sugerir Renovación</div>"
                    elif rest <= 1:
                        alerta = "<div class='alerta-final'>♻️ ÚLTIMA SESIÓN: Renovar o Finalizar</div>"
                    
                    st.markdown(f"""
                    <div class="turno-card">
                        <span style="color:{BRAND_GREEN}; font-size:22px; font-weight:bold;">{t['Hora']} hs</span> | {t['Paciente']}<br>
                        <b>{t['Servicio']}</b>
                        {alerta}
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_btns:
                    st.write("###")
                    if rest <= 2:
                        if st.button("🛒 Renovar", key=f"r_{t['Hora']}_{t['Paciente']}"):
                            st.toast(f"Preparando renovación para {t['Paciente']}")
                    if st.button("⚙️ Reagendar", key=f"m_{t['Hora']}_{t['Paciente']}"):
                        st.info("Función de cambio de horario activa.")

# --- MÓDULO 2: REGISTRO & COBRO ---
elif menu == "📝 Registro & Cobro":
    st.markdown('<p class="main-title">Nuevo Registro Elite</p>', unsafe_allow_html=True)
    df_p = cargar_nube("pacientes")
    
    with st.form("form_v9"):
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Nombre Completo")
            dni = st.text_input("DNI")
            dx = st.text_area("Diagnóstico (Dx)")
        with c2:
            origen = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
            serv = st.selectbox("Servicio", SERVICIOS_DISPONIBLES)
            m_lista = st.number_input("Precio Lista", min_value=0)
            
            # Lógica de beneficio único
            pago_f = m_lista
            if serv == "Evaluacion" and dni:
                ya_ev = not df_p[(df_p['DNI'].astype(str) == str(dni)) & (df_p['Servicio'] == "Evaluacion")].empty
                if not ya_ev:
                    pago_f = 0 if origen == "Socio Gimnasio" else m_lista * 0.5
                    st.success(f"Beneficio aplicado: Cobro final ${pago_f}")
            st.write(f"### Total: ${pago_f}")

        st.divider()
        f_c, h_c = st.columns(2)
        f_ini = f_c.date_input("Fecha Inicio", datetime.now())
        h_ini = h_c.time_input("Hora", datetime.now().time())
        dias = st.multiselect("Días (Planes)", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"])
        
        if st.form_submit_button("CONSOLIDAR REGISTRO"):
            cant = 10 if "x10" in serv else (5 if "x5" in serv else 1)
            fechas = calcular_fechas_fijas(f_ini, dias, cant) if dias else [str(f_ini)]
            
            # Guardar
            nuevo_p = pd.DataFrame([[dni, nombre, "", dx, origen, serv, pago_f, str(f_ini), cant, cant]], columns=COL_PACIENTES)
            conn.update(worksheet="pacientes", data=pd.concat([df_p, nuevo_p], ignore_index=True))
            
            df_a = cargar_nube("agenda")
            h_str = h_ini.strftime("%H:%M")
            nuevos_t = [[f, h_str, nombre, serv, "PENDIENTE", ""] for f in fechas]
            conn.update(worksheet="agenda", data=pd.concat([df_a, pd.DataFrame(nuevos_t, columns=COL_AGENDA)], ignore_index=True))
            st.rerun()

# --- MÓDULO 3: FINANZAS ---
elif menu == "📊 Inteligencia Financiera":
    st.markdown('<p class="main-title">Rendimiento Financiero</p>', unsafe_allow_html=True)
    df_f = cargar_nube("pacientes")
    if not df_f.empty:
        df_f['Pago'] = pd.to_numeric(df_f['Pago'], errors='coerce').fillna(0)
        df_f['Comision'] = df_f.apply(lambda r: r['Pago']*0.3 if r['Origen'] == "Socio Gimnasio" else r['Pago']*0.2, axis=1)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Ingreso Bruto", f"${df_f['Pago'].sum():,.0f}")
        c2.metric("Comisiones Cedidas", f"-${df_f['Comision'].sum():,.0f}")
        c3.metric("Utilidad Neta", f"${(df_f['Pago'] - df_f['Comision']).sum():,.0f}")

        st.subheader("Ingresos por Servicio")
        df_stats = df_f.groupby('Servicio')['Pago'].sum().reset_index()
        fig = px.bar(df_stats, x='Servicio', y='Pago', text_auto='.2s', color='Pago', color_continuous_scale='Greens')
        st.plotly_chart(fig, use_container_width=True)
