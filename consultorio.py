import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Elite System Cloud", layout="wide", page_icon="🌿")

# Paleta de colores y estilos visuales
BRAND_GREEN = "#60b067"
BRAND_RED = "#ff4b4b"
BRAND_ORANGE = "#f39c12"

st.markdown(f"""
    <style>
    .stApp {{ background-color: #FAFAFA; }}
    .card {{ 
        background: white; padding: 20px; border-radius: 12px; 
        border-left: 6px solid {BRAND_GREEN}; margin-bottom: 15px; 
        box-shadow: 0px 4px 10px rgba(0,0,0,0.05); 
    }}
    .dx-label {{ color: #555; font-style: italic; font-size: 13px; margin-top: 5px; }}
    .sesiones-tag {{ background: #e8f5e9; padding: 3px 12px; border-radius: 15px; font-weight: bold; font-size: 13px; }}
    .alert-pago {{ color: {BRAND_RED}; font-weight: bold; font-size: 11px; border: 1px solid {BRAND_RED}; padding: 2px 6px; border-radius: 5px; text-transform: uppercase; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN Y FUNCIONES CORE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos(pestaña):
    """Carga datos en tiempo real desde Google Sheets"""
    return conn.read(worksheet=pestaña, ttl="0")

def calcular_comision(pago, origen):
    """Calcula comisión: 30% si es Gimnasio, 20% si es propio"""
    porcentaje = 0.30 if origen == "Socio Gimnasio" else 0.20
    return pago * porcentaje

HORARIOS = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "16:00", "17:00", "18:00", "19:00", "20:00"]

# --- 3. MENÚ LATERAL ---
with st.sidebar:
    st.markdown(f"<h1 style='color:{BRAND_GREEN}; text-align:center;'>ELITE SYSTEM</h1>", unsafe_allow_html=True)
    st.caption("v10.0 - VERSIÓN MAESTRA CONSOLIDADA")
    st.divider()
    menu = st.radio("NAVEGACIÓN", [
        "📅 Agenda & Turnos", 
        "📝 Registro & Renovación", 
        "🔍 Buscador & Gestión", 
        "📊 Panel Financiero"
    ])

# --- 4. MÓDULO: AGENDA & TURNOS ---
if menu == "📅 Agenda & Turnos":
    st.header("Gestión de Agenda")
    
    col_f, col_stats = st.columns([1, 2])
    fecha_sel = col_f.date_input("Día seleccionado", datetime.now(), key="main_calendar_v10")
    
    # Carga de datos
    df_a = cargar_datos("agenda")
    df_p = cargar_datos("pacientes")
    
    # Filtrar turnos del día
    turnos_dia = df_a[df_a['Fecha'].astype(str) == str(fecha_sel)].copy()
    ocupados = turnos_dia['Hora'].tolist()

    # Visualización de disponibilidad (Semáforo)
    with st.expander("🕒 Estado de Ocupación", expanded=True):
        cols_h = st.columns(len(HORARIOS))
        for i, h in enumerate(HORARIOS):
            color = BRAND_ORANGE if h in ocupados else BRAND_GREEN
            cols_h[i].markdown(f"<div style='text-align:center; color:{color}; font-size:12px;'><b>{'🟠' if h in ocupados else '🟢'}<br>{h}</b></div>", unsafe_allow_html=True)

    st.divider()

    if not turnos_dia.empty:
        for idx, row in turnos_dia.sort_values(by="Hora").iterrows():
            # Buscar última ficha del paciente
            p_ficha = df_p[df_p['Nombre'] == row['Paciente']].tail(1)
            
            # Variables de estado por defecto
            debe_pago = False
            tag_sesiones = ""
            dx_actual = "Sin diagnóstico registrado"
            
            if not p_ficha.empty:
                p = p_ficha.iloc[0]
                debe_pago = float(p.get('Pago', 0)) <= 0
                dx_actual = p.get('DX', 'Sin diagnóstico')
                
                # Lógica de Sesiones Restantes (Cálculo Dinámico)
                if "Plan" in str(row['Servicio']):
                    totales = int(p.get('Sesiones_Totales', 0))
                    f_pack = str(p.get('Fecha_Inicio', '2000-01-01'))
                    # Contamos cuántas veces aparece en la agenda desde que compró el pack
                    asistencias = len(df_a[(df_a['Paciente'] == row['Paciente']) & (df_a['Fecha'].astype(str) >= f_pack)])
                    restantes = totales - asistencias
                    color_r = BRAND_RED if restantes <= 1 else BRAND_GREEN
                    tag_sesiones = f"<span class='sesiones-tag' style='color:{color_r}'>{restantes} / {totales} restantes</span>"
                else:
                    tag_sesiones = f"<span class='sesiones-tag' style='background:#f0f0f0; color:#555;'>{row['Servicio']}</span>"

            # Dibujar Tarjeta de Turno
            with st.container():
                c1, c2, c3 = st.columns([4, 1, 1])
                with c1:
                    alerta = '<span class="alert-pago">DEBE PAGAR</span>' if debe_pago else ""
                    st.markdown(f"""
                        <div class="card">
                            <span style="font-size:18px;"><b>{row['Hora']}</b> — <b>{row['Paciente']}</b></span> {alerta} {tag_sesiones}<br>
                            <div class='dx-label'>📝 DX: {dx_actual}</div>
                        </div>
                    """, unsafe_allow_html=True)
                with c2:
                    if st.button("🔄 Mover", key=f"btn_mov_{idx}"):
                        st.info("Funcionalidad de re-agenda lista.")
                with c3:
                    if debe_pago:
                        if st.button("💵 Cobrar", key=f"btn_cob_{idx}"):
                            # Actualización directa en Sheets
                            idx_update = df_p[df_p['Nombre'] == row['Paciente']].index[-1]
                            df_p.at[idx_update, 'Pago'] = 1 # Marcamos como pagado
                            conn.update(worksheet="pacientes", data=df_p)
                            st.success(f"Cobro registrado: {row['Paciente']}")
                            st.rerun()
    else:
        st.write("✨ No hay pacientes agendados para este día.")

# --- 5. MÓDULO: REGISTRO & RENOVACIÓN ---
elif menu == "📝 Registro & Renovación":
    st.header("Registro de Paciente y Asignación de Turno")
    
    with st.form("master_form"):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre y Apellido")
            dni = st.text_input("DNI / Identificación")
            servicio = st.selectbox("Tipo de Servicio", ["Plan X10", "Plan X5", "Sesion Individual", "Evaluacion"])
        with col2:
            origen = st.selectbox("Origen de Captación", ["Socio Gimnasio", "Captación Propia"])
            dx = st.text_input("Diagnóstico Inicial (DX)")
            pago_inicial = st.number_input("Pago Recibido ($)", min_value=0)
        
        st.divider()
        col3, col4 = st.columns(2)
        fecha_t = col3.date_input("Fecha del Primer Turno", datetime.now())
        hora_t = col4.selectbox("Hora del Primer Turno", HORARIOS)
        
        if st.form_submit_button("✅ Finalizar Registro"):
            # Guardar en Pestaña Pacientes
            df_p = cargar_datos("pacientes")
            cant_s = 10 if "X10" in servicio else (5 if "X5" in servicio else 1)
            f_paciente = pd.DataFrame([[dni, nombre, "", dx, origen, servicio, pago_inicial, str(fecha_t), cant_s]], 
                                       columns=["DNI", "Nombre", "WhatsApp", "DX", "Origen", "Servicio", "Pago", "Fecha_Inicio", "Sesiones_Totales"])
            conn.update(worksheet="pacientes", data=pd.concat([df_p, f_paciente], ignore_index=True))
            
            # Guardar en Pestaña Agenda
            df_a = cargar_datos("agenda")
            f_agenda = pd.DataFrame([[str(fecha_t), hora_t, nombre, servicio]], columns=["Fecha", "Hora", "Paciente", "Servicio"])
            conn.update(worksheet="agenda", data=pd.concat([df_a, f_agenda], ignore_index=True))
            
            st.success("¡Paciente registrado y turnos sincronizados en la nube!")
            st.rerun()

# --- 6. MÓDULO: BUSCADOR ---
elif menu == "🔍 Buscador & Gestión":
    st.header("Buscador de Pacientes")
    df_p = cargar_datos("pacientes")
    busqueda = st.text_input("Buscar por nombre, DNI o diagnóstico...")
    if busqueda:
        res = df_p[df_p['Nombre'].str.contains(busqueda, case=False, na=False) | 
                   df_p['DNI'].astype(str).str.contains(busqueda) |
                   df_p['DX'].str.contains(busqueda, case=False, na=False)]
        st.dataframe(res, use_container_width=True)

# --- 7. MÓDULO: PANEL FINANCIERO ---
elif menu == "📊 Panel Financiero":
    st.header("Reporte de Ingresos y Comisiones")
    df_p = cargar_datos("pacientes")
    
    if not df_p.empty:
        # Limpieza y cálculos
        df_p['Pago'] = pd.to_numeric(df_p['Pago'], errors='coerce').fillna(0)
        df_p['Comisión Cedida'] = df_p.apply(lambda x: calcular_comision(x['Pago'], x['Origen']), axis=1)
        df_p['Ingreso Neto Elite'] = df_p['Pago'] - df_p['Comisión Cedida']
        
        # Métricas principales
        m1, m2, m3 = st.columns(3)
        m1.metric("Bruto Total", f"${df_p['Pago'].sum():,.0f}")
        m2.metric("Comisiones (Gimnasio/Propio)", f"-${df_p['Comisión Cedida'].sum():,.0f}")
        m3.metric("Neto Final", f"${df_p['Ingreso Neto Elite'].sum():,.0f}", delta_color="normal")
        
        st.subheader("Desglose de Operaciones")
        st.dataframe(df_p[['Fecha_Inicio', 'Nombre', 'Origen', 'Servicio', 'Pago', 'Comisión Cedida', 'Ingreso Neto Elite']], use_container_width=True)
    else:
        st.warning("No hay registros financieros para mostrar.")
