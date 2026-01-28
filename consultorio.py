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
        background-color: {BRAND_GREEN}; color: white; border-radius: 12px; 
        border: none; font-weight: bold; width: 100%; padding: 10px;
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

# --- 2. CONEXIÓN Y LÓGICA DE DATOS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def obtener_datos(pestaña):
    return conn.read(worksheet=pestaña, ttl="0")

COL_PACIENTES = ["DNI", "Nombre", "WhatsApp", "DX", "Origen", "Servicio", "Pago", "Fecha_Inicio", "Sesiones_Totales"]
COL_AGENDA = ["Fecha", "Hora", "Paciente", "Servicio"]

def calcular_comision(pago, origen, servicio):
    try:
        pago_float = float(pago)
        if pago_float <= 0: return 0.0 # Bonificación 100% = 0 comisión
        porcentaje = 0.30 if origen == "Socio Gimnasio" else 0.20
        return pago_float * porcentaje
    except: return 0.0

# --- 3. MENÚ LATERAL ---
with st.sidebar:
    st.markdown(f'<h1 class="main-title">🌿 ELITE <span style="color:{BRAND_BLACK}; font-weight:normal; font-style:italic;">SYSTEM</span></h1>', unsafe_allow_html=True)
    st.caption("v4.0 - FULL CLOUD SYNC")
    st.divider()
    menu = st.radio("MENÚ PRINCIPAL", ["📅 Agenda & Turnos", "📝 Registro & Renovación", "🔍 Buscador & Gestión", "📊 Panel Financiero"])

# --- MÓDULO 1: AGENDA & TURNOS (Incluye Reagendar y Confirmar Pago) ---
if menu == "📅 Agenda & Turnos":
    st.header("Agenda del Día")
    fecha_ver = st.date_input("Ver calendario", datetime.now())
    
    df_a = obtener_datos("agenda")
    df_p = obtener_datos("pacientes")
    turnos_dia = df_a[df_a['Fecha'] == str(fecha_ver)]
    
    if not turnos_dia.empty:
        for i, t in turnos_dia.sort_values(by="Hora").iterrows():
            with st.container():
                c1, c2, c3 = st.columns([3, 1, 1])
                # Lógica: Se considera pagado si el monto en 'pacientes' es > 0
                pago_val = df_p[df_p['Nombre'] == t['Paciente']]['Pago'].sum()
                pagado = pago_val > 0
                
                with c1:
                    status = "" if pagado else '<span class="alert-pago">DEBE PAGAR</span>'
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
                        st.success(f"Listo para reagendar a {t['Paciente']}")
                with c3:
                    if not pagado:
                        if st.button("💵 Cobrar", key=f"pay_{i}"):
                            st.info("Función: Registrar pago en Sheets")
    else:
        st.info("Día sin turnos programados.")

# --- MÓDULO 2: REGISTRO, REAGENDA Y PROGRAMACIÓN DE PACKS ---
elif menu == "📝 Registro & Renovación":
    st.header("Formulario de Ingreso")
    re_paciente = st.session_state.get('reagenda', "")
    
    with st.form("form_registro"):
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Nombre y Apellido", value=re_paciente)
            dni = st.text_input("DNI")
            whatsapp = st.text_input("WhatsApp")
        with c2:
            dx = st.text_input("Diagnóstico (DX)")
            origen = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
            servicio = st.selectbox("Servicio", ["Plan X10", "Plan X5", "Sesion Individual", "Evaluacion"])
        
        monto = st.number_input("Monto Recibido ($)", min_value=0)
        f_inicio = st.date_input("Fecha de Turno", datetime.now())
        h_inicio = st.time_input("Hora", datetime.now().time())
        
        st.divider()
        st.subheader("Programación de Packs (X5 / X10)")
        auto_prog = st.checkbox("Programar todas las sesiones automáticamente")
        dias_selec = st.multiselect("Días de la semana", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])

        if st.form_submit_button("SINCRONIZAR CON CLOUD"):
            if nombre and dni:
                cant = 10 if "X10" in servicio else (5 if "X5" in servicio else 1)
                
                # Guardar Paciente
                df_p_previo = obtener_datos("pacientes")
                nuevo_p = pd.DataFrame([[dni, nombre, whatsapp, dx, origen, servicio, monto, str(f_inicio), cant]], columns=COL_PACIENTES)
                conn.update(worksheet="pacientes", data=pd.concat([df_p_previo, nuevo_p], ignore_index=True))
                
                # Guardar Agenda
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
                
                df_a_previo = obtener_datos("agenda")
                conn.update(worksheet="agenda", data=pd.concat([df_a_previo, pd.DataFrame(lista_turnos, columns=COL_AGENDA)], ignore_index=True))
                
                if 'reagenda' in st.session_state: del st.session_state['reagenda']
                st.balloons()
                st.rerun()

# --- MÓDULO 3: BUSCADOR & RENOVACIÓN (Control de Sesiones) ---
elif menu == "🔍 Buscador & Gestión":
    st.header("Buscador Inteligente")
    df_p = obtener_datos("pacientes")
    df_a = obtener_datos("agenda")
    
    busqueda = st.text_input("Nombre o DNI")
    if busqueda:
        res = df_p[df_p['Nombre'].str.contains(busqueda, case=False, na=False) | df_p['DNI'].astype(str).str.contains(busqueda)]
        if not res.empty:
            for _, row in res.iterrows():
                st.write(f"### {row['Nombre']}")
                atendidas = len(df_a[(df_a['Paciente'] == row['Nombre']) & (pd.to_datetime(df_a['Fecha']) <= datetime.now())])
                restantes = int(row['Sesiones_Totales']) - atendidas
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Sesiones Restantes", restantes)
                c2.write(f"**WhatsApp:** {row['WhatsApp']}")
                
                if restantes <= 1:
                    with c3:
                        st.warning("¡Pack por agotar!")
                        if st.button(f"🔄 RENOVAR: {row['Nombre']}"):
                            st.session_state['reagenda'] = row['Nombre']
                            st.rerun()
                st.dataframe(df_a[df_a['Paciente'] == row['Nombre']].sort_values("Fecha"), use_container_width=True)
        else:
            st.warning("No se encontró el paciente.")
    else:
        st.dataframe(df_p, use_container_width=True)

# --- MÓDULO 4: PANEL FINANCIERO (Filtros por Mes y Lógica de Cobro) ---
elif menu == "📊 Panel Financiero":
    st.header("Contabilidad & Comisiones")
    df_p = obtener_datos("pacientes")
    df_a = obtener_datos("agenda")
    
    if not df_p.empty:
        df_p['Fecha_Inicio'] = pd.to_datetime(df_p['Fecha_Inicio'])
        df_p['Mes'] = df_p['Fecha_Inicio'].dt.strftime('%m-%Y')
        
        mes_selec = st.selectbox("Seleccionar Mes", sorted(df_p['Mes'].unique(), reverse=True))
        df_mes = df_p[df_p['Mes'] == mes_selec].copy()
        
        # Lógica de Cobro: Planes (Adelantado), Otros (Solo si fecha ya pasó)
        hoy = datetime.now()
        def determinar_ingreso(row):
            if "Plan" in str(row['Servicio']): return row['Pago']
            return row['Pago'] if row['Fecha_Inicio'] <= hoy else 0.0

        df_mes['Facturado'] = df_mes.apply(determinar_ingreso, axis=1)
        df_mes['Comision_Cedida'] = df_mes.apply(lambda x: calcular_comision(x['Facturado'], x['Origen'], x['Servicio']), axis=1)
        df_mes['Neto_Elite'] = df_mes['Facturado'].astype(float) - df_mes['Comision_Cedida']
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Ingreso Bruto Mes", f"${df_mes['Facturado'].sum():,.0f}")
        c2.metric("Comisiones Cedidas", f"-${df_mes['Comision_Cedida'].sum():,.0f}")
        c3.metric("Neto Elite", f"${df_mes['Neto_Elite'].sum():,.0f}")
        
        st.divider()
        st.subheader("Desglose Detallado")
        df_mes['Bonif'] = df_mes.apply(lambda x: "100%" if x['Servicio']=="Evaluacion" and x['Origen']=="Socio Gimnasio" else ("50%" if x['Servicio']=="Evaluacion" else "0%"), axis=1)
        
        st.dataframe(df_mes[['Fecha_Inicio', 'Nombre', 'Servicio', 'Origen', 'Bonif', 'Facturado', 'Comision_Cedida', 'Neto_Elite']], use_container_width=True)
