import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN DE PÁGINA Y ESTILO ---
st.set_page_config(page_title="Elite System Cloud", layout="wide", page_icon="🌿")

BRAND_GREEN = "#60b067"
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
    div[data-testid="stMetricValue"] {{ color: {BRAND_GREEN}; font-weight: bold; }}
    .card {{ 
        background: white; padding: 20px; border-radius: 15px; 
        border-left: 5px solid {BRAND_GREEN}; margin-bottom: 10px; 
        box-shadow: 0px 2px 5px rgba(0,0,0,0.05); 
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN Y DATOS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def obtener_datos(pestaña):
    return conn.read(worksheet=pestaña, ttl="0")

COL_PACIENTES = ["DNI", "Nombre", "WhatsApp", "DX", "Origen", "Servicio", "Pago", "Fecha_Inicio", "Sesiones_Totales"]
COL_AGENDA = ["Fecha", "Hora", "Paciente", "Servicio"]

def calcular_comision_v2(pago, origen):
    try:
        pago_float = float(pago)
        if pago_float <= 0: return 0.0
        porcentaje = 0.30 if origen == "Socio Gimnasio" else 0.20
        return pago_float * porcentaje
    except:
        return 0.0

# --- 3. MENÚ LATERAL ---
with st.sidebar:
    st.markdown(f'<h1 class="main-title">🌿 ELITE <span style="color:{BRAND_BLACK}; font-weight:normal; font-style:italic;">SYSTEM</span></h1>', unsafe_allow_html=True)
    menu = st.radio("NAVEGACIÓN", ["📅 Agenda & Turnos", "📝 Registro de Pacientes", "🔍 Buscador & Historial", "📊 Panel Financiero"])

# --- MÓDULO 1: AGENDA & TURNOS ---
if menu == "📅 Agenda & Turnos":
    st.header("Gestión de Turnos Diarios")
    fecha_ver = st.date_input("Seleccionar Fecha", datetime.now())
    df_agenda = obtener_datos("agenda")
    turnos_dia = df_agenda[df_agenda['Fecha'] == str(fecha_ver)]
    
    if not turnos_dia.empty:
        for _, t in turnos_dia.sort_values(by="Hora").iterrows():
            st.markdown(f'<div class="card"><b>{t["Hora"]} hs</b> | {t["Paciente"]} ({t["Servicio"]})</div>', unsafe_allow_html=True)
    else:
        st.info("No hay turnos para hoy.")

# --- MÓDULO 2: REGISTRO DE PACIENTES ---
elif menu == "📝 Registro de Pacientes":
    st.header("Registro de Nuevo Paciente / Venta")
    with st.form("form_registro"):
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Nombre y Apellido")
            dni = st.text_input("DNI")
            whatsapp = st.text_input("WhatsApp")
        with c2:
            dx = st.text_input("Diagnóstico (DX)")
            origen = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
            servicio = st.selectbox("Servicio", ["Plan X10", "Plan X5", "Sesion Individual", "Evaluacion"])
        
        monto = st.number_input("Pago Recibido ($)", min_value=0)
        f_inicio = st.date_input("Fecha Inicio", datetime.now())
        h_inicio = st.time_input("Hora", datetime.now().time())
        
        dias_fijos = st.checkbox("Programar Pack Automáticamente")
        dias_selec = st.multiselect("Días", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])

        if st.form_submit_button("GUARDAR"):
            cant = 10 if "X10" in servicio else (5 if "X5" in servicio else 1)
            df_p_previo = obtener_datos("pacientes")
            nuevo_p = pd.DataFrame([[dni, nombre, whatsapp, dx, origen, servicio, monto, str(f_inicio), cant]], columns=COL_PACIENTES)
            conn.update(worksheet="pacientes", data=pd.concat([df_p_previo, nuevo_p], ignore_index=True))
            
            lista_turnos = []
            if dias_fijos and dias_selec:
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
            st.success("Sincronizado!")
            st.rerun()

# --- MÓDULO 3: BUSCADOR ---
elif menu == "🔍 Buscador & Historial":
    st.header("Buscador de Pacientes")
    df_p = obtener_datos("pacientes")
    busqueda = st.text_input("Nombre o DNI")
    if busqueda:
        res = df_p[df_p['Nombre'].str.contains(busqueda, case=False, na=False) | df_p['DNI'].astype(str).str.contains(busqueda)]
        st.dataframe(res, use_container_width=True)
    else:
        st.dataframe(df_p, use_container_width=True)

# --- MÓDULO 4: PANEL FINANCIERO (FILTROS Y SESIONES) ---
elif menu == "📊 Panel Financiero":
    st.header("Análisis Financiero")
    df_f = obtener_datos("pacientes")
    df_a = obtener_datos("agenda")
    
    if not df_f.empty:
        # Convertir fechas para filtrar
        df_f['Fecha_Inicio'] = pd.to_datetime(df_f['Fecha_Inicio'])
        df_f['Mes'] = df_f['Fecha_Inicio'].dt.strftime('%B %Y')
        
        # --- FILTRO POR MES ---
        meses_disponibles = df_f['Mes'].unique().tolist()
        mes_selec = st.selectbox("📅 Filtrar por Mes de Ingreso", meses_disponibles)
        df_mes = df_f[df_f['Mes'] == mes_selec].copy()
        
        # --- LÓGICA DE BONIFICACIÓN Y COMISIÓN ---
        df_mes['Comision_Monto'] = df_mes.apply(lambda x: calcular_comision_v2(x['Pago'], x['Origen']), axis=1)
        df_mes['Bonificación'] = df_mes.apply(lambda x: "100%" if x['Servicio']=="Evaluacion" and x['Origen']=="Socio Gimnasio" else ("50%" if x['Servicio']=="Evaluacion" else "No"), axis=1)
        df_mes['Neto_Elite'] = df_mes['Pago'].astype(float) - df_mes['Comision_Monto']
        
        # --- LÓGICA POR SESIÓN ATENDIDA ---
        # Calculamos el "Valor por Sesión" (Precio Pack / Cantidad Sesiones)
        df_mes['Valor_Sesion'] = df_mes['Pago'].astype(float) / df_mes['Sesiones_Totales'].astype(float)
        
        # Cruzamos con la Agenda para ver sesiones ya ocurridas (Pasado o Hoy)
        hoy_str = datetime.now().strftime('%Y-%m-%d')
        df_a['Fecha'] = pd.to_datetime(df_a['Fecha'])
        sesiones_atendidas = df_a[df_a['Fecha'] <= datetime.now()]
        
        # Métricas principales del mes
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Total Cobrado (Packs)", f"${df_mes['Pago'].sum():,.0f}")
        with c2:
            st.metric("Comisiones Cedidas", f"-${df_mes['Comision_Monto'].sum():,.0f}")
        with c3:
            st.metric("Neto Elite Mes", f"${df_mes['Neto_Elite'].sum():,.0f}")

        st.divider()
        st.subheader(f"Desglose de Facturación: {mes_selec}")
        st.dataframe(df_mes[['Fecha_Inicio', 'Nombre', 'Servicio', 'Origen', 'Bonificación', 'Pago', 'Comision_Monto', 'Neto_Elite']], use_container_width=True)

        st.divider()
        st.subheader("⚠️ Sesiones Individuales Atendidas (Pendientes de Cobro/Registro)")
        # Mostramos sesiones que NO son parte de los Packs registrados en 'pacientes'
        nombres_packs = df_mes['Nombre'].unique()
        sesiones_sueltas = sesiones_atendidas[~sesiones_atendidas['Paciente'].isin(nombres_packs)]
        
        if not sesiones_sueltas.empty:
            st.write("Estas sesiones ocurrieron pero no están vinculadas a un Plan pagado en este mes:")
            st.table(sesiones_sueltas[['Fecha', 'Paciente', 'Servicio']])
        else:
            st.success("Todas las sesiones atendidas están cubiertas por los planes cobrados.")
            
    else:
        st.info("Sin datos financieros.")
