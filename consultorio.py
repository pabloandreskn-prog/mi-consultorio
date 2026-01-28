import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN E INTERFAZ ---
st.set_page_config(page_title="Elite System Cloud", layout="wide", page_icon="🌿")

# Colores de marca
BRAND_GREEN = "#60b067"
BRAND_RED = "#ff4b4b"
BRAND_ORANGE = "#f39c12"

st.markdown(f"""
    <style>
    .stApp {{ background-color: #FAFAFA; }}
    .stButton>button {{ border-radius: 12px; font-weight: bold; width: 100%; }}
    .card {{ 
        background: white; padding: 18px; border-radius: 12px; 
        border-left: 6px solid {BRAND_GREEN}; margin-bottom: 12px; 
        box-shadow: 0px 3px 6px rgba(0,0,0,0.08); 
    }}
    .dx-label {{ color: #555; font-style: italic; font-size: 13px; margin-top: 5px; }}
    .sesiones-tag {{ background: #e8f5e9; color: #2e7d32; padding: 2px 8px; border-radius: 10px; font-weight: bold; font-size: 12px; }}
    .alert-pago {{ color: {BRAND_RED}; font-weight: bold; font-size: 11px; border: 1px solid {BRAND_RED}; padding: 1px 4px; border-radius: 4px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN Y LÓGICA DE NEGOCIO ---
conn = st.connection("gsheets", type=GSheetsConnection)

def obtener_datos(pestaña):
    return conn.read(worksheet=pestaña, ttl="0")

def calcular_comision_valor(pago, origen):
    try:
        pago_f = float(pago)
        # 30% para gimnasio, 20% para captación propia
        tasa = 0.30 if str(origen).strip() == "Socio Gimnasio" else 0.20
        return pago_f * tasa
    except:
        return 0.0

# Constantes de estructura
COL_PACIENTES = ["DNI", "Nombre", "WhatsApp", "DX", "Origen", "Servicio", "Pago", "Fecha_Inicio", "Sesiones_Totales"]
COL_AGENDA = ["Fecha", "Hora", "Paciente", "Servicio"]
HORARIOS_LABORALES = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "16:00", "17:00", "18:00", "19:00", "20:00"]

# --- 3. NAVEGACIÓN ---
if 'menu_actual' not in st.session_state:
    st.session_state['menu_actual'] = "📅 Agenda & Turnos"

with st.sidebar:
    st.markdown(f'<h1 style="color:{BRAND_GREEN};">🌿 ELITE SYSTEM</h1>', unsafe_allow_html=True)
    st.caption("v5.7 - GESTIÓN TOTAL")
    st.divider()
    opciones = ["📅 Agenda & Turnos", "📝 Registro & Renovación", "🔍 Buscador & Gestión", "📊 Panel Financiero"]
    # Usamos un key único para evitar DuplicateElementId
    seleccion = st.radio("MENÚ PRINCIPAL", opciones, index=opciones.index(st.session_state['menu_actual']), key="main_nav")
    st.session_state['menu_actual'] = seleccion

# --- MÓDULO 1: AGENDA & TURNOS ---
if st.session_state['menu_actual'] == "📅 Agenda & Turnos":
    st.header("Agenda Diaria")
    
    c_fecha, c_vacio = st.columns([1, 2])
    fecha_ver = c_fecha.date_input("Ver calendario", datetime.now(), key="agenda_date")
    fecha_str = fecha_ver.strftime("%Y-%m-%d")
    
    df_a = obtener_datos("agenda")
    df_p = obtener_datos("pacientes")
    
    # Filtrado y limpieza para semáforo
    turnos_dia = df_a[df_a['Fecha'].astype(str) == fecha_str].copy()
    horas_ocupadas = turnos_dia['Hora'].astype(str).str.replace(" hs", "").str.strip().tolist()

    with st.expander("🔍 Estado de Disponibilidad Horaria", expanded=True):
        cols = st.columns(len(HORARIOS_LABORALES))
        for idx, h in enumerate(HORARIOS_LABORALES):
            if h in horas_ocupadas:
                cols[idx].markdown(f"<div style='text-align:center; color:{BRAND_ORANGE};'><b>🟠 {h}</b></div>", unsafe_allow_html=True)
            else:
                cols[idx].markdown(f"<div style='text-align:center; color:{BRAND_GREEN};'><b>🟢 {h}</b></div>", unsafe_allow_html=True)

    st.divider()

    if not turnos_dia.empty:
        for i, t in turnos_dia.sort_values(by="Hora").iterrows():
            # Datos del paciente para la tarjeta
            info_p = df_p[df_p['Nombre'] == t['Paciente']].tail(1).to_dict('records')
            p = info_p[0] if info_p else {}
            
            # Cálculo de sesiones restantes
            total_s = int(p.get('Sesiones_Totales', 1))
            atendidas = len(df_a[(df_a['Paciente'] == t['Paciente']) & (pd.to_datetime(df_a['Fecha']) <= datetime.now())])
            restantes = total_s - atendidas

            with st.container():
                c1, c2, c3 = st.columns([3.5, 1, 1])
                es_pack = "Plan X" in str(t['Servicio'])
                
                with c1:
                    pago_status = "" if es_pack else '<span class="alert-pago">DEBE PAGAR</span>'
                    st.markdown(f"""
                        <div class="card">
                            <b>{t["Hora"]}</b> | <b>{t["Paciente"]}</b> {pago_status} <span class="sesiones-tag">{restantes} ses. restantes</span><br>
                            <small>{t["Servicio"]}</small>
                            <div class="dx-label">📋 DX: {p.get('DX', 'Sin diagnóstico')}</div>
                        </div>
                    """, unsafe_allow_html=True)
                
                with c2:
                    if st.button("🔄 Mover", key=f"btn_mov_{i}"):
                        st.session_state['reagenda_data'] = {
                            'Paciente': t['Paciente'], 'Servicio': t['Servicio'],
                            'Fecha_Vieja': t['Fecha'], 'Hora_Vieja': t['Hora'],
                            'DNI': p.get('DNI', ""), 'WhatsApp': p.get('WhatsApp', ""),
                            'DX': p.get('DX', ""), 'Origen': p.get('Origen', "Socio Gimnasio")
                        }
                        st.session_state['menu_actual'] = "📝 Registro & Renovación"
                        st.rerun()
                with c3:
                    if not es_pack: st.button("💵 Cobrar", key=f"btn_cob_{i}")
    else:
        st.info("No hay turnos para esta fecha.")

# --- MÓDULO 2: REGISTRO & RENOVACIÓN ---
elif st.session_state['menu_actual'] == "📝 Registro & Renovación":
    st.header("Gestión de Turnos y Packs")
    re = st.session_state.get('reagenda_data', {})
    
    if re: st.warning(f"🔄 Reagendando a: {re['Paciente']}")

    with st.form("form_gestion"):
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Nombre Completo", value=re.get('Paciente', ""))
            dni = st.text_input("DNI", value=re.get('DNI', ""))
            whatsapp = st.text_input("WhatsApp", value=re.get('WhatsApp', ""))
        with c2:
            dx = st.text_input("Diagnóstico (DX)", value=re.get('DX', ""))
            origen = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"], index=0 if re.get('Origen') == "Socio Gimnasio" else 1)
            servicio = st.selectbox("Servicio", ["Plan X10", "Plan X5", "Sesion Individual", "Evaluacion"])
        
        monto = st.number_input("Pago Recibido ($)", min_value=0)
        f_inicio = st.date_input("Fecha Turno", value=datetime.now())
        h_inicio = st.selectbox("Hora Turno", HORARIOS_LABORALES)
        
        st.divider()
        auto_pack = st.checkbox("Programar Pack Automático (Solo para Planes)")
        dias_pack = st.multiselect("Días de la semana", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])

        if st.form_submit_button("GUARDAR CAMBIOS"):
            if nombre:
                df_agenda = obtener_datos("agenda")
                # Borrar turno anterior si es reagenda
                if re:
                    df_agenda = df_agenda[~((df_agenda['Paciente'] == re['Paciente']) & 
                                          (df_agenda['Fecha'].astype(str) == str(re['Fecha_Vieja'])) & 
                                          (df_agenda['Hora'].astype(str) == str(re['Hora_Vieja'])))]
                
                # Lógica de programación
                cant = 10 if "X10" in servicio else (5 if "X5" in servicio else 1)
                nuevos_turnos = []
                if auto_pack and dias_pack:
                    d_map = {"Lunes":0, "Martes":1, "Miércoles":2, "Jueves":3, "Viernes":4, "Sábado":5}
                    d_num = [d_map[d] for d in dias_pack]
                    curr_f, cont = f_inicio, 0
                    while cont < cant:
                        if curr_f.weekday() in d_num:
                            nuevos_turnos.append([str(curr_f), h_inicio, nombre, servicio])
                            cont += 1
                        curr_f += timedelta(days=1)
                else:
                    nuevos_turnos.append([str(f_inicio), h_inicio, nombre, servicio])
                
                # Actualizar Sheets
                df_up_a = pd.concat([df_agenda, pd.DataFrame(nuevos_turnos, columns=COL_AGENDA)], ignore_index=True)
                conn.update(worksheet="agenda", data=df_up_a)
                
                # Actualizar Ficha Paciente
                df_p = obtener_datos("pacientes")
                nuevo_p = pd.DataFrame([[dni, nombre, whatsapp, dx, origen, servicio, monto, str(f_inicio), cant]], columns=COL_PACIENTES)
                conn.update(worksheet="pacientes", data=pd.concat([df_p, nuevo_p], ignore_index=True))

                if 'reagenda_data' in st.session_state: del st.session_state['reagenda_data']
                st.session_state['menu_actual'] = "📅 Agenda & Turnos"
                st.success("Operación Exitosa")
                st.rerun()

# --- MÓDULO 3: BUSCADOR ---
elif st.session_state['menu_actual'] == "🔍 Buscador & Gestión":
    st.header("Historial de Pacientes")
    df_p = obtener_datos("pacientes")
    df_a = obtener_datos("agenda")
    
    busq = st.text_input("Buscar por nombre o DNI")
    if busq:
        res = df_p[df_p['Nombre'].str.contains(busq, case=False, na=False)]
        for _, r in res.iterrows():
            with st.expander(f"Ver ficha de {r['Nombre']}"):
                st.write(f"**DNI:** {r['DNI']} | **Origen:** {r['Origen']}")
                st.write(f"**DX:** {r['DX']}")
                st.divider()
                st.write("Turnos en Agenda:")
                st.dataframe(df_a[df_a['Paciente'] == r['Nombre']])
    else:
        st.dataframe(df_p, use_container_width=True)

# --- MÓDULO 4: PANEL FINANCIERO ---
elif st.session_state['menu_actual'] == "📊 Panel Financiero":
    st.header("Análisis de Ingresos")
    df_p = obtener_datos("pacientes")
    if not df_p.empty:
        df_p['Fecha_Inicio'] = pd.to_datetime(df_p['Fecha_Inicio'])
        df_p['Mes'] = df_p['Fecha_Inicio'].dt.strftime('%m-%Y')
        meses = sorted(df_p['Mes'].unique(), reverse=True)
        mes_sel = st.selectbox("Seleccionar Mes de análisis", meses)
        
        df_mes = df_p[df_p['Mes'] == mes_sel].copy()
        df_mes['Pago'] = df_mes['Pago'].astype(float)
        df_mes['Comision'] = df_mes.apply(lambda x: calcular_comision_valor(x['Pago'], x['Origen']), axis=1)
        df_mes['Neto'] = df_mes['Pago'] - df_mes['Comision']
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Ingreso Bruto", f"${df_mes['Pago'].sum():,.0f}")
        c2.metric("Comisiones Cedidas", f"-${df_mes['Comision'].sum():,.0f}")
        c3.metric("Neto Elite", f"${df_mes['Neto'].sum():,.0f}")
        
        st.subheader("Desglose por Paciente")
        st.dataframe(df_mes[['Fecha_Inicio', 'Nombre', 'Origen', 'Pago', 'Comision', 'Neto']], use_container_width=True)
