import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="Elite System Cloud", layout="wide", page_icon="🌿")

BRAND_GREEN = "#60b067"
BRAND_RED = "#ff4b4b"

st.markdown(f"""
    <style>
    .stApp {{ background-color: #FAFAFA; }}
    .stButton>button {{ border-radius: 12px; font-weight: bold; width: 100%; }}
    .card {{ 
        background: white; padding: 20px; border-radius: 15px; 
        border-left: 5px solid {BRAND_GREEN}; margin-bottom: 10px; 
        box-shadow: 0px 2px 5px rgba(0,0,0,0.05); 
    }}
    .alert-pago {{ color: {BRAND_RED}; font-weight: bold; font-size: 13px; border: 1px solid {BRAND_RED}; padding: 2px 5px; border-radius: 5px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

def obtener_datos(pestaña):
    return conn.read(worksheet=pestaña, ttl="0")

COL_PACIENTES = ["DNI", "Nombre", "WhatsApp", "DX", "Origen", "Servicio", "Pago", "Fecha_Inicio", "Sesiones_Totales"]
COL_AGENDA = ["Fecha", "Hora", "Paciente", "Servicio"]
HORARIOS_LABORALES = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "16:00", "17:00", "18:00", "19:00", "20:00"]

# --- 3. LÓGICA DE NAVEGACIÓN ---
if 'menu_actual' not in st.session_state:
    st.session_state['menu_actual'] = "📅 Agenda & Turnos"

# --- 4. MENÚ LATERAL ---
with st.sidebar:
    st.markdown(f'<h1 style="color:{BRAND_GREEN};">🌿 ELITE SYSTEM</h1>', unsafe_allow_html=True)
    st.caption("v5.0 - GESTIÓN TOTAL")
    st.divider()
    opciones = ["📅 Agenda & Turnos", "📝 Registro & Renovación", "🔍 Buscador & Gestión", "📊 Panel Financiero"]
    st.session_state['menu_actual'] = st.radio("MENÚ PRINCIPAL", opciones, index=opciones.index(st.session_state['menu_actual']))

# --- MÓDULO 1: AGENDA & TURNOS (Con Disponibilidad y Reagenda) ---
if st.session_state['menu_actual'] == "📅 Agenda & Turnos":
    st.header("Agenda Diaria")
    fecha_ver = st.date_input("Ver calendario", datetime.now())
    
    df_a = obtener_datos("agenda")
    turnos_dia = df_a[df_a['Fecha'] == str(fecha_ver)]
    
    # --- EXPANDER DE TURNOS VACÍOS ---
    with st.expander("🔍 Ver Disponibilidad de Horarios"):
        horas_ocupadas = turnos_dia['Hora'].tolist()
        horas_libres = [h for h in HORARIOS_LABORALES if h not in horas_ocupadas]
        if horas_libres:
            cols = st.columns(len(horas_libres))
            for idx, h_libre in enumerate(horas_libres):
                cols[idx].info(f"🟢 {h_libre}")
        else:
            st.warning("Día completo. No hay turnos vacíos.")

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
                        # Guardamos datos para eliminar el viejo al guardar el nuevo
                        st.session_state['reagenda_data'] = t.to_dict()
                        st.session_state['menu_actual'] = "📝 Registro & Renovación"
                        st.rerun()
                with c3:
                    if not es_pack:
                        st.button("💵 Cobrar", key=f"pay_{i}")
    else:
        st.info("No hay turnos agendados.")

# --- MÓDULO 2: REGISTRO & RENOVACIÓN (Con Borrado de turno viejo) ---
elif st.session_state['menu_actual'] == "📝 Registro & Renovación":
    st.header("Formulario de Turnos")
    
    re_data = st.session_state.get('reagenda_data', {})
    re_paciente = re_data.get('Paciente', "")
    re_serv = re_data.get('Servicio', "Plan X10")
    
    if re_paciente:
        st.warning(f"🔄 Reagendando a: {re_paciente} (El turno anterior se borrará al confirmar)")

    with st.form("form_registro"):
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Paciente", value=re_paciente)
            dni = st.text_input("DNI")
            whatsapp = st.text_input("WhatsApp")
        with c2:
            dx = st.text_input("Diagnóstico (DX)")
            origen = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
            servicio = st.selectbox("Servicio", ["Plan X10", "Plan X5", "Sesion Individual", "Evaluacion"], 
                                  index=["Plan X10", "Plan X5", "Sesion Individual", "Evaluacion"].index(re_serv) if re_serv in ["Plan X10", "Plan X5", "Sesion Individual", "Evaluacion"] else 0)
        
        monto = st.number_input("Pago Recibido ($)", min_value=0)
        f_inicio = st.date_input("Fecha")
        h_inicio = st.time_input("Hora")
        
        st.divider()
        auto_prog = st.checkbox("Programar Pack completo")
        dias_selec = st.multiselect("Días", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])

        if st.form_submit_button("CONFIRMAR Y ACTUALIZAR CLOUD"):
            if nombre:
                # 1. Si es REAGENDA, borramos el registro viejo de la Agenda
                df_agenda_actual = obtener_datos("agenda")
                if re_data:
                    df_agenda_actual = df_agenda_actual[~((df_agenda_actual['Paciente'] == re_paciente) & 
                                                        (df_agenda_actual['Fecha'] == re_data['Fecha']) & 
                                                        (df_agenda_actual['Hora'] == re_data['Hora']))]
                
                # 2. Creamos los nuevos turnos
                cant = 10 if "X10" in servicio else (5 if "X5" in servicio else 1)
                nuevos_turnos = []
                if auto_prog and dias_selec:
                    d_map = {"Lunes":0, "Martes":1, "Miércoles":2, "Jueves":3, "Viernes":4, "Sábado":5}
                    d_num = [d_map[d] for d in dias_selec]
                    curr_f, agendados = f_inicio, 0
                    while agendados < cant:
                        if curr_f.weekday() in d_num:
                            nuevos_turnos.append([str(curr_f), h_inicio.strftime("%H:%M"), nombre, servicio])
                            agendados += 1
                        curr_f += timedelta(days=1)
                else:
                    nuevos_turnos.append([str(f_inicio), h_inicio.strftime("%H:%M"), nombre, servicio])
                
                # 3. Actualizamos Sheets
                df_final_agenda = pd.concat([df_agenda_actual, pd.DataFrame(nuevos_turnos, columns=COL_AGENDA)], ignore_index=True)
                conn.update(worksheet="agenda", data=df_final_agenda)
                
                # Solo guardamos en 'pacientes' si hay un pago o es registro nuevo
                if monto > 0 or not re_data:
                    df_p_previo = obtener_datos("pacientes")
                    nuevo_p = pd.DataFrame([[dni, nombre, whatsapp, dx, origen, servicio, monto, str(f_inicio), cant]], columns=COL_PACIENTES)
                    conn.update(worksheet="pacientes", data=pd.concat([df_p_previo, nuevo_p], ignore_index=True))

                if 'reagenda_data' in st.session_state: del st.session_state['reagenda_data']
                st.session_state['menu_actual'] = "📅 Agenda & Turnos"
                st.balloons()
                st.rerun()

# --- MÓDULO 3: BUSCADOR & GESTIÓN ---
elif st.session_state['menu_actual'] == "🔍 Buscador & Gestión":
    st.header("Buscador de Pacientes")
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

# --- MÓDULO 4: PANEL FINANCIERO ---
elif st.session_state['menu_actual'] == "📊 Panel Financiero":
    st.header("Contabilidad")
    df_p = obtener_datos("pacientes")
    if not df_p.empty:
        df_p['Fecha_Inicio'] = pd.to_datetime(df_p['Fecha_Inicio'])
        df_p['Mes'] = df_p['Fecha_Inicio'].dt.strftime('%m-%Y')
        mes_selec = st.selectbox("Seleccionar Mes", sorted(df_p['Mes'].unique(), reverse=True))
        df_mes = df_p[df_p['Mes'] == mes_selec].copy()
        
        # Lógica de comisiones y bonificaciones (30% Socio Gym / 20% Propia)
        def calcular_finanzas(row):
            comision = 0
            pago = float(row['Pago'])
            if "Plan" in str(row['Servicio']) or row['Fecha_Inicio'] <= datetime.now():
                if pago > 0:
                    tasa = 0.30 if row['Origen'] == "Socio Gimnasio" else 0.20
                    comision = pago * tasa
                return pd.Series([pago, comision, pago - comision])
            return pd.Series([0, 0, 0])

        df_mes[['Real', 'Cedido', 'Neto']] = df_mes.apply(calcular_finanzas, axis=1)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Ingreso Bruto", f"${df_mes['Real'].sum():,.0f}")
        c2.metric("Comisiones", f"-${df_mes['Cedido'].sum():,.0f}")
        c3.metric("Neto Elite", f"${df_mes['Neto'].sum():,.0f}")
        st.dataframe(df_mes[['Fecha_Inicio', 'Nombre', 'Servicio', 'Origen', 'Real', 'Cedido', 'Neto']], use_container_width=True)
