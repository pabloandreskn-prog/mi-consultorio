import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN DE PÁGINA Y ESTILO ELITE ---
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

# --- 2. CONEXIÓN Y FUNCIONES DE DATOS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def obtener_datos(pestaña):
    return conn.read(worksheet=pestaña, ttl="0")

COL_PACIENTES = ["DNI", "Nombre", "WhatsApp", "DX", "Origen", "Servicio", "Pago", "Fecha_Inicio", "Sesiones_Totales"]
COL_AGENDA = ["Fecha", "Hora", "Paciente", "Servicio"]

def calcular_comision_v2(pago, origen, servicio):
    try:
        pago_float = float(pago)
        # REGLA DE BONIFICACIÓN: Si el pago es 0 (Evaluación bonificada), la comisión es 0
        if pago_float <= 0:
            return 0.0
        
        # Socio Gimnasio cede 30%, Captación Propia cede 20%
        porcentaje = 0.30 if origen == "Socio Gimnasio" else 0.20
        return pago_float * porcentaje
    except:
        return 0.0

# --- 3. MENÚ LATERAL ---
with st.sidebar:
    st.markdown(f'<h1 class="main-title">🌿 ELITE <span style="color:{BRAND_BLACK}; font-weight:normal; font-style:italic;">SYSTEM</span></h1>', unsafe_allow_html=True)
    st.caption("CONEXIÓN CLOUD ACTIVA")
    st.divider()
    menu = st.radio("NAVEGACIÓN", ["📅 Agenda & Turnos", "📝 Registro de Pacientes", "🔍 Buscador & Historial", "📊 Panel Financiero"])

# --- MÓDULO 1: AGENDA & TURNOS ---
if menu == "📅 Agenda & Turnos":
    st.header("Gestión de Turnos Diarios")
    fecha_ver = st.date_input("Seleccionar Fecha", datetime.now())
    
    df_agenda = obtener_datos("agenda")
    turnos_dia = df_agenda[df_agenda['Fecha'] == str(fecha_ver)]
    
    c1, c2 = st.columns([1, 3])
    with c1:
        st.metric("Turnos Hoy", len(turnos_dia))
    
    with c2:
        if not turnos_dia.empty:
            for _, t in turnos_dia.sort_values(by="Hora").iterrows():
                st.markdown(f"""
                    <div class="card">
                        <span style="color:{BRAND_GREEN}; font-weight:bold;">{t['Hora']} hs</span> | 
                        <span style="font-weight:bold; font-size:18px;">{t['Paciente']}</span><br>
                        <small style="color:gray;">{t['Servicio']}</small>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No hay turnos programados para esta fecha.")

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
            origen = st.selectbox("Origen del Paciente", ["Socio Gimnasio", "Captación Propia"])
            servicio = st.selectbox("Servicio", ["Plan X10", "Plan X5", "Sesion Individual", "Evaluacion"])
        
        # Sugerencia de precio según bonificación
        st.info("💡 Evaluación Socio: $0 (Bonif. 100%) | Evaluación Gral: $18.000 (Bonif. 50%)")
        monto = st.number_input("Pago Recibido ($)", min_value=0)
        
        f_inicio = st.date_input("Fecha de Primera Sesión", datetime.now())
        h_inicio = st.time_input("Hora del Turno", datetime.now().time())
        
        st.divider()
        dias_fijos = st.checkbox("¿Programar todo el Pack automáticamente?")
        dias_selec = st.multiselect("Días de asistencia", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])

        if st.form_submit_button("GUARDAR Y SINCRONIZAR"):
            if nombre and dni:
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
                st.success("✅ Sincronizado con Google Sheets")
                st.rerun()

# --- MÓDULO 3: BUSCADOR ---
elif menu == "🔍 Buscador & Historial":
    st.header("Buscador de Pacientes")
    df_p = obtener_datos("pacientes")
    busqueda = st.text_input("Buscar por Nombre o DNI")
    if busqueda:
        resultado = df_p[df_p['Nombre'].str.contains(busqueda, case=False, na=False) | df_p['DNI'].astype(str).str.contains(busqueda)]
        st.dataframe(resultado, use_container_width=True)
    else:
        st.dataframe(df_p, use_container_width=True)

# --- MÓDULO 4: PANEL FINANCIERO (ACTUALIZADO) ---
elif menu == "📊 Panel Financiero":
    st.header("Análisis de Ingresos y Comisiones")
    df_f = obtener_datos("pacientes")
    
    if not df_f.empty:
        # 1. Cálculos de Comisiones y Bonificaciones
        df_f['Comision_Monto'] = df_f.apply(lambda x: calcular_comision_v2(x['Pago'], x['Origen'], x['Servicio']), axis=1)
        
        def detectar_bonif(row):
            if row['Servicio'] == "Evaluacion":
                return "100% (Socio)" if row['Origen'] == "Socio Gimnasio" else "50% (Gral)"
            return "No"
            
        df_f['Bonificación'] = df_f.apply(detectar_bonif, axis=1)
        df_f['Neto_Elite'] = df_f['Pago'].astype(float) - df_f['Comision_Monto']
        
        # 2. Métricas
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Total Bruto", f"${df_f['Pago'].astype(float).sum():,.0f}")
        with c2:
            st.metric("Comisiones Cedidas", f"-${df_f['Comision_Monto'].sum():,.0f}", delta_color="inverse")
        with c3:
            st.metric("Neto Elite", f"${df_f['Neto_Elite'].sum():,.0f}")
        
        st.divider()
        st.subheader("Desglose Detallado por Servicio")
        
        # 3. Tabla Final Optimizada
        tabla_final = df_f[['Fecha_Inicio', 'Nombre', 'Servicio', 'Origen', 'Bonificación', 'Pago', 'Comision_Monto', 'Neto_Elite']]
        st.dataframe(tabla_final, use_container_width=True)
    else:
        st.info("No hay datos financieros registrados.")
