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
    .stButton>button {{ border-radius: 12px; font-weight: bold; width: 100%; }}
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
    st.caption("v5.5 - INTEGRIDAD TOTAL")
    st.divider()
    opciones = ["📅 Agenda & Turnos", "📝 Registro & Renovación", "🔍 Buscador & Gestión", "📊 Panel Financiero"]
    st.session_state['menu_actual'] = st.radio("MENÚ PRINCIPAL", opciones, index=opciones.index(st.session_state['menu_actual']))

# --- MÓDULO 1: AGENDA & TURNOS (Semáforo Corregido) ---
if st.session_state['menu_actual'] == "📅 Agenda & Turnos":
    st.header("Agenda Diaria")
    fecha_ver = st.date_input("Ver calendario", datetime.now())
    fecha_str = fecha_ver.strftime("%Y-%m-%d")
    
    df_a = obtener_datos("agenda")
    df_p = obtener_datos("pacientes")
    turnos_dia = df_a[df_a['Fecha'].astype(str) == fecha_str]
    
    with st.expander("🔍 Estado de Disponibilidad Horaria", expanded=True):
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
        st.info(f"Día sin turnos agendados.")

# --- MÓDULO 2: REGISTRO & RENOVACIÓN (Preservado) ---
elif st.session_state['menu_actual'] == "📝 Registro & Renovación":
    st.header("Formulario de Turnos")
    re = st.session_state.get('reagenda_data', {})
    
    if re: st.warning(f"🔄 Reagendando a: {re['Paciente']}")

    with st.form("form_registro"):
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Paciente", value=re.get('Paciente', ""))
            dni = st.text_input("DNI", value=re.get('DNI', ""))
            whatsapp = st.text_input("WhatsApp", value=re.get('WhatsApp', ""))
        with c2:
            dx = st.text_input("Diagnóstico (DX)", value=re.get('DX', ""))
            origen = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"], index=0 if re.get('Origen') == "Socio Gimnasio" else 1)
            serv_list = ["Plan X10", "Plan X5", "Sesion Individual", "Evaluacion"]
            servicio = st.selectbox("Servicio", serv_list, index=serv_list.index(re.get('Servicio', "Plan X10")) if re.get('Servicio') in serv_list else 0)
        
        monto = st.number_input("Pago ($)", min_value=0)
        f_inicio = st.date_input("Nueva Fecha")
        h_inicio = st.selectbox("Hora", HORARIOS_LABORALES)
        
        st.divider()
        auto_prog = st.checkbox("Programar Pack completo")
        dias_selec = st.multiselect("Días", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])

        if st.form_submit_button("CONFIRMAR"):
            if nombre:
                df_agenda = obtener_datos("agenda")
                if re:
                    df_agenda = df_agenda[~((df_agenda['Paciente'] == re['Paciente']) & 
                                          (df_agenda['Fecha'].astype(str) == str(re['Fecha_Vieja'])) & 
                                          (df_agenda['Hora'].astype(str) == str(re['Hora_Vie_ja'])))]
                
                cant = 10 if "X10" in servicio else (5 if "X5" in servicio else 1)
                nuevos = []
                if auto_prog and dias_selec:
                    d_map = {"Lunes":0, "Martes":1, "Miércoles":2, "Jueves":3, "Viernes":4, "Sábado":5}
                    d_num = [d_map[d] for d in dias_selec]
                    curr_f, agendados = f_inicio, 0
                    while agendados < cant:
                        if curr_f.weekday() in d_num:
                            nuevos.append([str(curr_f), h_inicio, nombre, servicio])
                            agendados += 1
                        curr_f += timedelta(days=1)
                else:
                    nuevos.append([str(f_inicio), h_inicio, nombre, servicio])
                
                conn.update(worksheet="agenda", data=pd.concat([df_agenda, pd.DataFrame(nuevos, columns=COL_AGENDA)], ignore_index=True))
                
                if monto > 0 or not re:
                    df_p = obtener_datos("pacientes")
                    nuevo_p = pd.DataFrame([[dni, nombre, whatsapp, dx, origen, servicio, monto, str(f_inicio), cant]], columns=COL_PACIENTES)
                    conn.update(worksheet="pacientes", data=pd.concat([df_p, nuevo_p], ignore_index=True))

                if 'reagenda_data' in st.session_state: del st.session_state['reagenda_data']
                st.session_state['menu_actual'] = "📅 Agenda & Turnos"
                st.rerun()

# --- MÓDULOS 3 Y 4 (Preservados: Buscador y Financiero) ---
elif st.session_state['menu_actual'] == "🔍 Buscador & Gestión":
    st.header("Buscador")
    df_p, df_a = obtener_datos("pacientes"), obtener_datos("agenda")
    busqueda = st.text_input("Nombre")
    if busqueda:
        res = df_p[df_p['Nombre'].str.contains(busqueda, case=False, na=False)]
        for _, row in res.iterrows():
            atendidas = len(df_a[(df_a['Paciente'] == row['Nombre']) & (pd.to_datetime(df_a['Fecha']) <= datetime.now())])
            st.metric(f"Sesiones Restantes: {row['Nombre']}", int(row['Sesiones_Totales']) - atendidas)
            st.dataframe(df_a[df_a['Paciente'] == row['Nombre']].sort_values("Fecha"), use_container_width=True)
    else: st.dataframe(df_p, use_container_width=True)

elif st.session_state['menu_actual'] == "📊 Panel Financiero":
    st.header("Contabilidad")
    df_p = obtener_datos("pacientes")
    if not df_p.empty:
        df_p['Fecha_Inicio'] = pd.to_datetime(df_p['Fecha_Inicio'])
        df_p['Mes'] = df_p['Fecha_Inicio'].dt.strftime('%m-%Y')
        mes_selec = st.selectbox("Mes", sorted(df_p['Mes'].unique(), reverse=True))
        df_mes = df_p[df_p['Mes'] == mes_selec].copy()
        df_mes['Real'] = df_mes['Pago'].astype(float)
        df_mes['Comision'] = df_mes.apply(lambda x: calcular_comision_valor(x['Real'], x['Origen']), axis=1)
        df_mes['Neto'] = df_mes['Real'] - df_mes['Comision']
        st.metric("Neto Elite Mes", f"${df_mes['Neto'].sum():,.0f}")
        st.dataframe(df_mes[['Fecha_Inicio', 'Nombre', 'Servicio', 'Real', 'Comision', 'Neto']], use_container_width=True)
