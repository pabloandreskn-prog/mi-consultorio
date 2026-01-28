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
    # Trae los datos ignorando el cache (ttl=0) para ver cambios inmediatos
    return conn.read(worksheet=pestaña, ttl="0")

COL_PACIENTES = ["DNI", "Nombre", "Contacto", "Dx", "Origen", "Servicio", "Pago", "Fecha", "Sesiones"]
COL_AGENDA = ["Fecha", "Hora", "Paciente", "Servicio"]

def calcular_comision(pago, origen):
    try:
        # 30% para socios del gym, 20% para captación propia
        tasa = 0.30 if origen == "Socio Gimnasio" else 0.20
        return float(pago) * tasa
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
    # Filtrar por fecha seleccionada
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

# --- MÓDULO 2: REGISTRO DE PACIENTES & PACKS ---
elif menu == "📝 Registro de Pacientes":
    st.header("Registro de Nuevo Paciente / Venta")
    with st.form("form_registro"):
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Nombre y Apellido")
            dni = st.text_input("DNI")
            contacto = st.text_input("WhatsApp (Sin 0 ni 15)")
        with c2:
            dx = st.text_input("Diagnóstico / Motivo")
            origen = st.selectbox("Origen del Paciente", ["Socio Gimnasio", "Captación Propia"])
            servicio = st.selectbox("Servicio", ["Plan X5", "Plan X10", "Sesión Individual", "Evaluación"])
        
        monto = st.number_input("Pago Recibido ($)", min_value=0)
        f_inicio = st.date_input("Fecha de Primera Sesión", datetime.now())
        h_inicio = st.time_input("Hora del Turno", datetime.now().time())
        
        st.divider()
        st.subheader("Programación Automática")
        dias_fijos = st.checkbox("¿Programar todo el Pack automáticamente?")
        dias_selec = st.multiselect("Seleccionar días de asistencia", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])

        if st.form_submit_button("GUARDAR Y SINCRONIZAR"):
            if nombre and dni:
                # Determinar sesiones según servicio
                cant = 5 if "X5" in servicio else (10 if "X10" in servicio else 1)
                
                # A. Actualizar Base de Pacientes
                df_p_previo = obtener_datos("pacientes")
                nuevo_p = pd.DataFrame([[dni, nombre, contacto, dx, origen, servicio, monto, str(f_inicio), cant]], columns=COL_PACIENTES)
                df_p_final = pd.concat([df_p_previo, nuevo_p], ignore_index=True)
                conn.update(worksheet="pacientes", data=df_p_final)
                
                # B. Lógica de Agenda (Programación de múltiples días)
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
                
                # C. Actualizar Agenda en la Nube
                df_a_previo = obtener_datos("agenda")
                df_a_nuevo = pd.DataFrame(lista_turnos, columns=COL_AGENDA)
                df_a_final = pd.concat([df_a_previo, df_a_nuevo], ignore_index=True)
                conn.update(worksheet="agenda", data=df_a_final)
                
                st.success(f"✅ ¡{nombre} registrado con éxito! {len(lista_turnos)} turnos añadidos.")
                st.balloons()
                st.rerun()
            else:
                st.error("Por favor completa Nombre y DNI.")

# --- MÓDULO 3: BUSCADOR & HISTORIAL ---
elif menu == "🔍 Buscador & Historial":
    st.header("Buscador de Pacientes")
    df_p = obtener_datos("pacientes")
    
    busqueda = st.text_input("Buscar por Nombre o DNI")
    
    if busqueda:
        resultado = df_p[df_p['Nombre'].str.contains(busqueda, case=False) | df_p['DNI'].astype(str).str.contains(busqueda)]
        if not resultado.empty:
            st.dataframe(resultado, use_container_width=True)
            
            # Ver turnos específicos del paciente buscado
            nombre_paciente = resultado.iloc[0]['Nombre']
            st.subheader(f"Historial de Turnos: {nombre_paciente}")
            df_a = obtener_datos("agenda")
            turnos_paciente = df_a[df_a['Paciente'] == nombre_paciente]
            st.table(turnos_paciente.sort_values(by="Fecha", ascending=False))
        else:
            st.warning("No se encontraron coincidencias.")
    else:
        st.dataframe(df_p, use_container_width=True)

# --- MÓDULO 4: PANEL FINANCIERO ---
elif menu == "📊 Panel Financiero":
    st.header("Análisis de Ingresos y Comisiones")
    df_f = obtener_datos("pacientes")
    
    if not df_f.empty:
        # Cálculos en tiempo real
        df_f['Comision'] = df_f.apply(lambda x: calcular_comision(x['Pago'], x['Origen']), axis=1)
        df_f['Neto'] = df_f['Pago'].astype(float) - df_f['Comision']
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Ingreso Bruto", f"${df_f['Pago'].sum():,.0f}")
        with c2:
            st.metric("Comisiones Gym", f"-${df_f['Comision'].sum():,.0f}", delta_color="inverse")
        with c3:
            st.metric("Neto Elite", f"${df_f['Neto'].sum():,.0f}")
        
        st.divider()
        st.subheader("Desglose Detallado")
        st.dataframe(df_f[['Fecha', 'Nombre', 'Servicio', 'Pago', 'Comision', 'Neto']], use_container_width=True)
    else:
        st.info("Aún no hay registros financieros.")
