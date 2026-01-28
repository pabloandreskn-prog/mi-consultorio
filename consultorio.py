import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="Elite System Cloud", layout="wide", page_icon="🌿")

BRAND_GREEN = "#60b067"
BRAND_RED = "#ff4b4b"
BRAND_ORANGE = "#f39c12"

st.markdown(f"""
    <style>
    .stApp {{ background-color: #FAFAFA; }}
    .card {{ 
        background: white; padding: 20px; border-radius: 15px; 
        border-left: 5px solid {BRAND_GREEN}; margin-bottom: 10px; 
        box-shadow: 0px 2px 5px rgba(0,0,0,0.05); 
    }}
    .alert-pago {{ color: {BRAND_RED}; font-weight: bold; font-size: 13px; border: 1px solid {BRAND_RED}; padding: 2px 5px; border-radius: 5px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN Y FUNCIONES ---
conn = st.connection("gsheets", type=GSheetsConnection)

def obtener_datos(pestaña):
    return conn.read(worksheet=pestaña, ttl="0")

def calcular_comision_valor(pago, origen):
    try:
        pago_f = float(pago)
        return pago_f * (0.30 if origen == "Socio Gimnasio" else 0.20)
    except: return 0.0

COL_PACIENTES = ["DNI", "Nombre", "WhatsApp", "DX", "Origen", "Servicio", "Pago", "Fecha_Inicio", "Sesiones_Totales"]
COL_AGENDA = ["Fecha", "Hora", "Paciente", "Servicio"]
HORARIOS_LABORALES = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "16:00", "17:00", "18:00", "19:00", "20:00"]

if 'menu_actual' not in st.session_state:
    st.session_state['menu_actual'] = "📅 Agenda & Turnos"

# --- 3. MENÚ LATERAL ---
with st.sidebar:
    st.markdown(f'<h1 style="color:{BRAND_GREEN};">🌿 ELITE SYSTEM</h1>', unsafe_allow_html=True)
    st.caption("v5.4 - SEMÁFORO CORREGIDO")
    st.divider()
    opciones = ["📅 Agenda & Turnos", "📝 Registro & Renovación", "🔍 Buscador & Gestión", "📊 Panel Financiero"]
    st.session_state['menu_actual'] = st.radio("MENÚ PRINCIPAL", opciones, index=opciones.index(st.session_state['menu_actual']))

# --- MÓDULO 1: AGENDA & TURNOS (Semáforo Corregido) ---
if st.session_state['menu_actual'] == "📅 Agenda & Turnos":
    st.header("Agenda Diaria")
    fecha_ver = st.date_input("Ver calendario", datetime.now())
    fecha_str = fecha_ver.strftime("%Y-%m-%d") # Normalización de fecha
    
    df_a = obtener_datos("agenda")
    df_p = obtener_datos("pacientes")
    
    # Filtrado robusto
    turnos_dia = df_a[df_a['Fecha'].astype(str) == fecha_str]
    
    with st.expander("🔍 Estado de Disponibilidad Horaria", expanded=True):
        # Extraemos las horas ocupadas asegurando que no haya espacios extra
        horas_ocupadas = turnos_dia['Hora'].astype(str).str.strip().tolist()
        cols = st.columns(len(HORARIOS_LABORALES))
        
        for idx, h in enumerate(HORARIOS_LABORALES):
            if h in horas_ocupadas:
                cols[idx].markdown(f"<div style='text-align:center; color:{BRAND_ORANGE};'><b>🟠 {h}</b></div>", unsafe_allow_html=True)
            else:
                cols[idx].markdown(f"<div style='text-align:center; color:{BRAND_GREEN};'><b>🟢 {h}</b></div>", unsafe_allow_html=True)

    st.divider()

    if not turnos_dia.empty:
        for i, t in turnos_dia.sort_values(by="Hora").iterrows():
            with st.container():
                c1, c2, c3 = st.columns([3, 1, 1])
                es_pack = "Plan X" in str(t['Servicio'])
                with c1:
                    status = "" if es_pack else '<span class="alert-pago">DEBE PAGAR</span>'
                    st.markdown(f'<div class="card"><b>{t["Hora"]} hs</b> | <b>{t["Paciente"]}</b> {status}<br><small>{t["Servicio"]}</small></div>', unsafe_allow_html=True)
                with c2:
                    if st.button("🔄 Mover", key=f"re_{i}"):
                        info = df_p[df_p['Nombre'] == t['Paciente']].tail(1).to_dict('records')
                        p = info[0] if info else {}
                        st.session_state['reagenda_data'] = {
                            'Paciente': t['Paciente'], 'Servicio': t['Servicio'],
                            'Fecha_Vieja': t['Fecha'], 'Hora_Vieja': t['Hora'],
                            'DNI': p.get('DNI', ""), 'WhatsApp': p.get('WhatsApp', ""),
                            'DX': p.get('DX', ""), 'Origen': p.get('Origen', "Socio Gimnasio")
                        }
                        st.session_state['menu_actual'] = "📝 Registro & Renovación"
                        st.rerun()
                with c3:
                    if not es_pack: st.button("💵 Cobrar", key=f"pay_{i}")
    else:
        st.info(f"No hay turnos para el {fecha_str}")

# --- MÓDULO 2: REGISTRO (Mantiene toda la funcionalidad previa) ---
elif st.session_state['menu_actual'] == "📝 Registro & Renovación":
    st.header("Gestión de Turnos")
    re = st.session_state.get('reagenda_data', {})
    
    with st.form("form_registro"):
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Paciente", value=re.get('Paciente', ""))
            dni = st.text_input("DNI", value=re.get('DNI', ""))
            whatsapp = st.text_input("WhatsApp", value=re.get('WhatsApp', ""))
        with c2:
            dx = st.text_input("Diagnóstico (DX)", value=re.get('DX', ""))
            origen = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"], 
                                  index=0 if re.get('Origen') == "Socio Gimnasio" else 1)
            servicio = st.selectbox("Servicio", ["Plan X10", "Plan X5", "Sesion Individual", "Evaluacion"])
        
        monto = st.number_input("Pago ($)", min_value=0)
        f_inicio = st.date_input("Fecha")
        h_inicio = st.selectbox("Hora", HORARIOS_LABORALES)
        
        if st.form_submit_button("CONFIRMAR"):
            df_agenda = obtener_datos("agenda")
            # Borrar anterior si es reagenda
            if re:
                df_agenda = df_agenda[~((df_agenda['Paciente'] == re['Paciente']) & 
                                      (df_agenda['Fecha'] == str(re['Fecha_Vieja'])) & 
                                      (df_agenda['Hora'] == str(re['Hora_Vieja'])))]
            
            nuevo = pd.DataFrame([[str(f_inicio), h_inicio, nombre, servicio]], columns=COL_AGENDA)
            conn.update(worksheet="agenda", data=pd.concat([df_agenda, nuevo], ignore_index=True))
            
            # Actualizar ficha paciente
            df_p = obtener_datos("pacientes")
            cant = 10 if "X10" in servicio else (5 if "X5" in servicio else 1)
            nuevo_p = pd.DataFrame([[dni, nombre, whatsapp, dx, origen, servicio, monto, str(f_inicio), cant]], columns=COL_PACIENTES)
            conn.update(worksheet="pacientes", data=pd.concat([df_p, nuevo_p], ignore_index=True))

            if 'reagenda_data' in st.session_state: del st.session_state['reagenda_data']
            st.session_state['menu_actual'] = "📅 Agenda & Turnos"
            st.rerun()

# --- MÓDULO 3: BUSCADOR (Cálculo de Sesiones Restantes) ---
elif st.session_state['menu_actual'] == "🔍 Buscador & Gestión":
    st.header("Buscador Inteligente")
    df_p = obtener_datos("pacientes")
    df_a = obtener_datos("agenda")
    busqueda = st.text_input("Nombre o DNI")
    if busqueda:
        res = df_p[df_p['Nombre'].str.contains(busqueda, case=False, na=False)]
        for _, row in res.iterrows():
            atendidas = len(df_a[(df_a['Paciente'] == row['Nombre']) & (pd.to_datetime(df_a['Fecha']) <= datetime.now())])
            restantes = int(row['Sesiones_Totales']) - atendidas
            c1, c2 = st.columns(2)
            c1.metric("Sesiones Restantes", restantes)
            if restantes <= 1:
                if c2.button(f"🔄 RENOVAR: {row['Nombre']}"):
                    st.session_state['reagenda_data'] = {'Paciente': row['Nombre'], 'Servicio': row['Servicio']}
                    st.session_state['menu_actual'] = "📝 Registro & Renovación"
                    st.rerun()
            st.dataframe(df_a[df_a['Paciente'] == row['Nombre']].sort_values("Fecha"), use_container_width=True)
    else:
        st.dataframe(df_p, use_container_width=True)

# --- MÓDULO 4: PANEL FINANCIERO (Inteligencia de Mes y Cobro) ---
elif st.session_state['menu_actual'] == "📊 Panel Financiero":
    st.header("Análisis Financiero")
    df_p = obtener_datos("pacientes")
    df_a = obtener_datos("agenda")
    if not df_p.empty:
        df_p['Fecha_Inicio'] = pd.to_datetime(df_p['Fecha_Inicio'])
        df_p['Mes'] = df_p['Fecha_Inicio'].dt.strftime('%m-%Y')
        mes_selec = st.selectbox("Seleccionar Mes", sorted(df_p['Mes'].unique(), reverse=True))
        df_mes = df_p[df_p['Mes'] == mes_selec].copy()
        hoy = datetime.now()

        def determinar_facturado(row):
            if "Plan" in str(row['Servicio']): return float(row['Pago'])
            return float(row['Pago']) if pd.to_datetime(row['Fecha_Inicio']) <= hoy else 0.0

        df_mes['Facturado_Real'] = df_mes.apply(determinar_facturado, axis=1)
        df_mes['Comision'] = df_mes.apply(lambda x: calcular_comision_valor(x['Facturado_Real'], x['Origen']), axis=1)
        df_mes['Neto'] = df_mes['Facturado_Real'] - df_mes['Comision']
        
        atendidas_mes = len(df_a[(pd.to_datetime(df_a['Fecha']).dt.strftime('%m-%Y') == mes_selec) & (pd.to_datetime(df_a['Fecha']) <= hoy)])

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ingreso Real", f"${df_mes['Facturado_Real'].sum():,.0f}")
        c2.metric("Comisiones", f"-${df_mes['Comision'].sum():,.0f}")
        c3.metric("Neto Elite", f"${df_mes['Neto'].sum():,.0f}")
        c4.metric("Atendidas Mes", atendidas_mes)
        st.dataframe(df_mes[['Fecha_Inicio', 'Nombre', 'Servicio', 'Facturado_Real', 'Comision', 'Neto']], use_container_width=True)

