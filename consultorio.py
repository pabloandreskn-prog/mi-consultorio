import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN Y ESTILO ELITE ---
st.set_page_config(page_title="Elite System Cloud", layout="wide", page_icon="🌿")

BRAND_GREEN = "#60b067"
BRAND_RED = "#ff4b4b"
BRAND_BLACK = "#1E1E1E"

st.markdown(f"""
    <style>
    .stApp {{ background-color: #FAFAFA; }}
    [data-testid="stSidebar"] {{ background-color: #FFFFFF; border-right: 1px solid #f0f0f0; }}
    .stButton>button {{ 
        border-radius: 12px; font-weight: bold; width: 100%; padding: 10px;
    }}
    .main-title {{ color: {BRAND_GREEN}; font-size: 30px; font-weight: bold; }}
    .card {{ 
        background: white; padding: 20px; border-radius: 15px; 
        border-left: 5px solid {BRAND_GREEN}; margin-bottom: 10px; 
        box-shadow: 0px 2px 5px rgba(0,0,0,0.05); 
    }}
    .alert-pago {{ color: {BRAND_RED}; font-weight: bold; font-size: 13px; border: 1px solid {BRAND_RED}; padding: 2px 5px; border-radius: 5px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN Y DATOS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def obtener_datos(pestaña):
    return conn.read(worksheet=pestaña, ttl="0")

COL_PACIENTES = ["DNI", "Nombre", "WhatsApp", "DX", "Origen", "Servicio", "Pago", "Fecha_Inicio", "Sesiones_Totales"]
COL_AGENDA = ["Fecha", "Hora", "Paciente", "Servicio"]

# --- 3. LÓGICA DE NAVEGACIÓN ---
if 'menu_actual' not in st.session_state:
    st.session_state['menu_actual'] = "📅 Agenda & Turnos"

# --- 4. MENÚ LATERAL ---
with st.sidebar:
    st.markdown(f'<h1 class="main-title">🌿 ELITE <span style="color:{BRAND_BLACK}; font-weight:normal; font-style:italic;">SYSTEM</span></h1>', unsafe_allow_html=True)
    st.caption("v5.0 - FULL OPTIMIZED")
    st.divider()
    opciones = ["📅 Agenda & Turnos", "📝 Registro & Renovación", "🔍 Buscador & Gestión", "📊 Panel Financiero"]
    st.session_state['menu_actual'] = st.radio("NAVEGACIÓN", opciones, index=opciones.index(st.session_state['menu_actual']))

# --- MÓDULO 1: AGENDA & TURNOS ---
if st.session_state['menu_actual'] == "📅 Agenda & Turnos":
    st.header("Gestión de Turnos Diarios")
    fecha_ver = st.date_input("Seleccionar Día", datetime.now())
    
    df_a = obtener_datos("agenda")
    turnos_dia = df_a[df_a['Fecha'] == str(fecha_ver)]
    
    # Desplegable informativo solicitado
    with st.expander(f"📊 Resumen del día {fecha_ver}", expanded=True):
        st.write(f"**Total de turnos:** {len(turnos_dia)}")
        if not turnos_dia.empty:
            st.write(f"**Pacientes esperados:** {', '.join(turnos_dia['Paciente'].tolist())}")

    st.divider()
    
    if not turnos_dia.empty:
        for i, t in turnos_dia.sort_values(by="Hora").iterrows():
            with st.container():
                c1, c2, c3 = st.columns([3, 1, 1])
                es_pack = "Plan X" in str(t['Servicio'])
                
                with c1:
                    status = "" if es_pack else '<span class="alert-pago">DEBE PAGAR</span>'
                    st.markdown(f"""
                        <div class="card">
                            <span style="color:{BRAND_GREEN}; font-weight:bold;">{t['Hora']} hs</span> | 
                            <b>{t['Paciente']}</b> {status}<br>
                            <small style="color:gray;">{t['Servicio']}</small>
                        </div>
                    """, unsafe_allow_html=True)
                with c2:
                    if st.button("🔄 Mover", key=f"re_{i}"):
                        st.session_state['reagenda'] = t['Paciente']
                        st.session_state['re_servicio'] = t['Servicio']
                        st.session_state['fecha_vieja'] = t['Fecha'] # Para borrar el anterior
                        st.session_state['menu_actual'] = "📝 Registro & Renovación"
                        st.rerun()
                with c3:
                    if not es_pack:
                        if st.button("💵 Cobrar", key=f"pay_{i}"):
                            st.success("Pago marcado")
    else:
        st.info("No hay turnos programados.")

# --- MÓDULO 2: REGISTRO, RENOVACIÓN Y REAGENDA ---
elif st.session_state['menu_actual'] == "📝 Registro & Renovación":
    st.header("Formulario de Entrada")
    
    re_paciente = st.session_state.get('reagenda', "")
    re_serv = st.session_state.get('re_servicio', "Plan X10")
    
    if re_paciente:
        st.warning(f"🔄 Editando turno de: {re_paciente}")

    with st.form("form_registro"):
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Paciente", value=re_paciente)
            dni = st.text_input("DNI")
            whatsapp = st.text_input("WhatsApp")
        with c2:
            dx = st.text_input("Diagnóstico")
            origen = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
            servicio = st.selectbox("Servicio", ["Plan X10", "Plan X5", "Sesion Individual", "Evaluacion"],
                                   index=["Plan X10", "Plan X5", "Sesion Individual", "Evaluacion"].index(re_serv) if re_serv in ["Plan X10", "Plan X5", "Sesion Individual", "Evaluacion"] else 0)
        
        monto = st.number_input("Pago Recibido ($)", min_value=0)
        f_inicio = st.date_input("Fecha")
        h_inicio = st.time_input("Hora")
        
        st.divider()
        auto_prog = st.checkbox("Programar Pack Completo")
        dias_selec = st.multiselect("Días", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])

        if st.form_submit_button("GUARDAR CAMBIOS EN CLOUD"):
            if nombre:
                # 1. Si es REAGENDA, borramos el turno anterior antes de crear el nuevo
                if 'fecha_vieja' in st.session_state:
                    df_a_old = obtener_datos("agenda")
                    df_a_clean = df_a_old[~((df_a_old['Paciente'] == re_paciente) & (df_a_old['Fecha'] == st.session_state['fecha_vieja']))]
                    conn.update(worksheet="agenda", data=df_a_clean)

                # 2. Registrar Paciente/Venta
                cant = 10 if "X10" in servicio else (5 if "X5" in servicio else 1)
                df_p_p = obtener_datos("pacientes")
                nuevo_p = pd.DataFrame([[dni, nombre, whatsapp, dx, origen, servicio, monto, str(f_inicio), cant]], columns=COL_PACIENTES)
                conn.update(worksheet="pacientes", data=pd.concat([df_p_p, nuevo_p], ignore_index=True))
                
                # 3. Registrar Turnos
                lista_turnos = []
                if auto_prog and dias_selec:
                    d_map = {"Lunes":0, "Martes":1, "Miércoles":2, "Jueves":3, "Viernes":4, "Sábado":5}
                    d_num = [d_map[d] for d in dias_selec]
                    curr_f, agendados = f_inicio, 0
                    while agendados < cant:
                        if curr_f.weekday() in d_num:
                            lista_turnos.append([str(curr_f), h_inicio.strftime("%H:%M"), nombre, servicio])
                            agendados += 1
                        curr_f += timedelta(days=1)
                else:
                    lista_turnos.append([str(f_inicio), h_inicio.strftime("%H:%M"), nombre, servicio])
                
                df_a_p = obtener_datos("agenda")
                conn.update(worksheet="agenda", data=pd.concat([df_a_p, pd.DataFrame(lista_turnos, columns=COL_AGENDA)], ignore_index=True))
                
                # Limpiar y Volver
                for key in ['reagenda', 're_servicio', 'fecha_vieja']:
                    if key in st.session_state: del st.session_state[key]
                st.session_state['menu_actual'] = "📅 Agenda & Turnos"
                st.rerun()

# --- MÓDULO 3: BUSCADOR & GESTIÓN ---
elif st.session_state['menu_actual'] == "🔍 Buscador & Gestión":
    st.header("Buscador de Pacientes")
    df_p = obtener_datos("pacientes")
    df_a = obtener_datos("agenda")
    
    busqueda = st.text_input("Nombre o DNI")
    if busqueda:
        res = df_p[df_p['Nombre'].str.contains(busqueda, case=False, na=False) | df_p['DNI'].astype(str).str.contains(busqueda)]
        if not res.empty:
            for _, row in res.iterrows():
                atendidas = len(df_a[(df_a['Paciente'] == row['Nombre']) & (pd.to_datetime(df_a['Fecha']) <= datetime.now())])
                restantes = int(row['Sesiones_Totales']) - atendidas
                st.markdown(f'<div class="card"><b>{row["Nombre"]}</b> | Sesiones rest: {restantes}</div>', unsafe_allow_html=True)
                if restantes <= 1:
                    if st.button(f"🔄 Renovar Plan: {row['Nombre']}"):
                        st.session_state['reagenda'] = row['Nombre']
                        st.session_state['menu_actual'] = "📝 Registro & Renovación"
                        st.rerun()
    else:
        st.dataframe(df_p, use_container_width=True)

# --- MÓDULO 4: PANEL FINANCIERO ---
elif st.session_state['menu_actual'] == "📊 Panel Financiero":
    st.header("Panel de Comisiones")
    df_p = obtener_datos("pacientes")
    if not df_p.empty:
        df_p['Fecha_Inicio'] = pd.to_datetime(df_p['Fecha_Inicio'])
        df_p['Mes'] = df_p['Fecha_Inicio'].dt.strftime('%m-%Y')
        mes = st.selectbox("Mes", sorted(df_p['Mes'].unique(), reverse=True))
        df_mes = df_p[df_p['Mes'] == mes].copy()
        
        # Lógica de comisiones
        df_mes['Comision'] = df_mes.apply(lambda x: float(x['Pago']) * (0.3 if x['Origen']=="Socio Gimnasio" else 0.2) if float(x['Pago'])>0 else 0, axis=1)
        df_mes['Neto'] = df_mes['Pago'].astype(float) - df_mes['Comision']
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Bruto", f"${df_mes['Pago'].sum():,.0f}")
        c2.metric("Comisiones", f"-${df_mes['Comision'].sum():,.0f}")
        c3.metric("Neto Elite", f"${df_mes['Neto'].sum():,.0f}")
        st.dataframe(df_mes, use_container_width=True)
