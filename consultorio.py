import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Elite System v13.0", layout="wide", page_icon="🌿")

# Estilos visuales
BRAND_GREEN, BRAND_RED, BRAND_ORANGE = "#60b067", "#ff4b4b", "#f39c12"

st.markdown(f"""
    <style>
    .stApp {{ background-color: #FAFAFA; }}
    .card {{ 
        background: white; padding: 15px; border-radius: 12px; 
        border-left: 6px solid {BRAND_GREEN}; margin-bottom: 10px; 
        box-shadow: 0px 4px 10px rgba(0,0,0,0.05); 
    }}
    .sesiones-tag {{ background: #e8f5e9; padding: 2px 10px; border-radius: 10px; font-weight: bold; font-size: 12px; }}
    .alert-pago {{ color: {BRAND_RED}; font-weight: bold; font-size: 10px; border: 1.5px solid {BRAND_RED}; padding: 2px 5px; border-radius: 4px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. SERVICIOS Y PRECIOS ---
SERVICIOS_PRECIOS = {
    "Plan x10": 200000, "Plan x 5": 110000, "Sesión Individual": 24000,
    "Sesión Especializada": 36000, "Evaluación": 36000,
    "Masaje Zona A (Piernas/Pies)": {"Socio Gimnasio": 25000, "Captación Propia": 30000},
    "Masaje Zona B (Espalda/Cabeza)": {"Socio Gimnasio": 25000, "Captación Propia": 30000},
    "Masaje Completo": {"Socio Gimnasio": 38000, "Captación Propia": 45000}
}

HORARIOS = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "16:00", "17:00", "18:00", "19:00", "20:00"]

# --- 3. CONEXIÓN Y ESTADO ---
conn = st.connection("gsheets", type=GSheetsConnection)

if 'menu' not in st.session_state: st.session_state.menu = "📅 Agenda"
if 'p_renovando' not in st.session_state: st.session_state.p_renovando = {}

def cargar_datos(pestaña):
    return conn.read(worksheet=pestaña, ttl="0")

# --- 4. NAVEGACIÓN ---
with st.sidebar:
    st.markdown(f"<h1 style='color:{BRAND_GREEN}; text-align:center;'>ELITE SYSTEM</h1>", unsafe_allow_html=True)
    if st.button("📅 Agenda", use_container_width=True): st.session_state.menu = "📅 Agenda"
    if st.button("📝 Registro & Renovación", use_container_width=True): st.session_state.menu = "📝 Registro"
    if st.button("📊 Finanzas", use_container_width=True): st.session_state.menu = "📊 Finanzas"

# --- 5. MÓDULO: AGENDA ---
if st.session_state.menu == "📅 Agenda":
    st.header("Agenda Diaria")
    fecha_sel = st.date_input("Ver calendario", datetime.now(), key="agenda_date_v13")
    
    df_a = cargar_datos("agenda")
    df_p = cargar_datos("pacientes")
    
    turnos_dia = df_a[df_a['Fecha'].astype(str) == str(fecha_sel)].copy()
    
    if not turnos_dia.empty:
        for idx, row in turnos_dia.sort_values(by="Hora").iterrows():
            p_ficha = df_p[df_p['Nombre'] == row['Paciente']].tail(1)
            debe_pago = False
            necesita_renovar = False
            tag = ""
            
            if not p_ficha.empty:
                p = p_ficha.iloc[0]
                debe_pago = float(p.get('Pago', 0)) <= 0
                if "Plan" in str(row['Servicio']):
                    total = int(p.get('Sesiones_Totales', 0))
                    f_pack = str(p.get('Fecha_Inicio', '2000-01-01'))
                    # Contamos sesiones en agenda para este paciente DESDE la fecha de compra del plan
                    asistencias = len(df_a[(df_a['Paciente'] == row['Paciente']) & (df_a['Fecha'].astype(str) >= f_pack)])
                    res = total - asistencias
                    tag = f"<span class='sesiones-tag'>{res} rest.</span>"
                    if res <= 1: necesita_renovar = True
                else:
                    tag = f"<span class='sesiones-tag'>{row['Servicio']}</span>"
                    necesita_renovar = True

            with st.container():
                c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                c1.markdown(f"""<div class="card"><b>{row['Hora']}</b> | {row['Paciente']} {'<span class="alert-pago">DEBE</span>' if debe_pago else ''} {tag}</div>""", unsafe_allow_html=True)
                
                if c2.button("🔄 Mover", key=f"m_{idx}"):
                    st.session_state[f"edit_{idx}"] = not st.session_state.get(f"edit_{idx}", False)
                
                if debe_pago:
                    if c3.button("💵 Cobrar", key=f"c_{idx}"):
                        p_idx = df_p[df_p['Nombre'] == row['Paciente']].index[-1]
                        df_p.at[p_idx, 'Pago'] = 1 
                        conn.update(worksheet="pacientes", data=df_p)
                        st.rerun()
                
                if necesita_renovar:
                    if c4.button("➕ Renovar", key=f"r_{idx}"):
                        st.session_state.p_renovando = {"Nombre": row['Paciente'], "DNI": str(p['DNI']) if not p_ficha.empty else ""}
                        st.session_state.menu = "📝 Registro"
                        st.rerun()

            if st.session_state.get(f"edit_{idx}", False):
                with st.expander("Configurar nueva fecha/hora", expanded=True):
                    ce1, ce2 = st.columns(2)
                    nf = ce1.date_input("Nueva Fecha", value=fecha_sel, key=f"nf_{idx}")
                    h_val = row['Hora'] if row['Hora'] in HORARIOS else HORARIOS[0]
                    nh = ce2.selectbox("Nueva Hora", HORARIOS, index=HORARIOS.index(h_val), key=f"nh_{idx}")
                    if st.button("Confirmar Cambio", key=f"s_{idx}"):
                        # Buscamos la fila exacta en el DataFrame original usando el índice
                        df_a.loc[idx, 'Fecha'] = str(nf)
                        df_a.loc[idx, 'Hora'] = nh
                        conn.update(worksheet="agenda", data=df_a)
                        st.session_state[f"edit_{idx}"] = False
                        st.rerun()
    else:
        st.info("No hay turnos para hoy.")

# --- 6. MÓDULO: REGISTRO & RENOVACIÓN ---
elif st.session_state.menu == "📝 Registro":
    st.header("Ingreso / Renovación de Paciente")
    p_data = st.session_state.p_renovando
    
    with st.form("f_reg_v13"):
        c1, c2 = st.columns(2)
        nom = c1.text_input("Paciente", value=p_data.get("Nombre", ""))
        dni = c2.text_input("DNI", value=p_data.get("DNI", ""))
        orig = c1.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
        serv = c2.selectbox("Servicio", list(SERVICIOS_PRECIOS.keys()))
        
        # Selección de días fijos para agendamiento masivo
        st.write("📅 **Agendamiento Automático (Planes)**")
        col_d, col_s = st.columns(2)
        dias_fijos = col_d.multiselect("Días de la semana", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"])
        num_semanas = col_s.number_input("¿Cuántas semanas agendar?", min_value=1, max_value=12, value=1)
        
        # Precio automático
        precio_ref = SERVICIOS_PRECIOS[serv]
        monto_sug = precio_ref[orig] if isinstance(precio_ref, dict) else precio_ref
        
        monto = st.number_input("Monto total a cobrar ($)", value=monto_sug)
        f_inicio = st.date_input("Fecha primer sesión / Inicio Plan")
        h_inicio = st.selectbox("Hora preferida", HORARIOS)
        dx = st.text_input("Diagnóstico / Observaciones")
        
        if st.form_submit_button("Finalizar y Agendar"):
            df_p = cargar_datos("pacientes")
            cant_s = 10 if "x10" in serv else (5 if "x 5" in serv else 1)
            
            # 1. Registro en Pacientes (Asegurando columnas exactas)
            # DNI, Nombre, WhatsApp, DX, Origen, Servicio, Pago, Fecha_Inicio, Sesiones_Totales
            nueva_fila_p = {
                "DNI": dni, "Nombre": nom, "WhatsApp": "", "DX": dx,
                "Origen": orig, "Servicio": serv, "Pago": monto,
                "Fecha_Inicio": str(f_inicio), "Sesiones_Totales": cant_s
            }
            df_p = pd.concat([df_p, pd.DataFrame([nueva_fila_p])], ignore_index=True)
            conn.update(worksheet="pacientes", data=df_p)
            
            # 2. Agendamiento en Agenda
            df_a = cargar_datos("agenda")
            nuevos_turnos = []
            dict_dias = {"Lunes":0, "Martes":1, "Miércoles":2, "Jueves":3, "Viernes":4}
            
            if dias_fijos:
                dias_num = [dict_dias[d] for d in dias_fijos]
                count = 0
                curr_date = f_inicio
                while count < (len(dias_fijos) * num_semanas):
                    if curr_date.weekday() in dias_num:
                        nuevos_turnos.append({"Fecha": str(curr_date), "Hora": h_inicio, "Paciente": nom, "Servicio": serv})
                        count += 1
                    curr_date += timedelta(days=1)
            else:
                nuevos_turnos.append({"Fecha": str(f_inicio), "Hora": h_inicio, "Paciente": nom, "Servicio": serv})
            
            df_a = pd.concat([df_a, pd.DataFrame(nuevos_turnos)], ignore_index=True)
            conn.update(worksheet="agenda", data=df_a)
            
            st.session_state.p_renovando = {}
            st.success("¡Paciente y turnos registrados!")
            st.rerun()

# --- 7. MÓDULO: FINANZAS ---
elif st.session_state.menu == "📊 Finanzas":
    st.header("Panel Financiero Inteligente")
    
    df_p = cargar_datos("pacientes")
    df_a = cargar_datos("agenda")
    
    if not df_p.empty:
        # Filtro por Mes
        df_p['Fecha_DT'] = pd.to_datetime(df_p['Fecha_Inicio'], errors='coerce')
        meses = df_p['Fecha_DT'].dt.strftime('%Y-%m').unique().tolist()
        mes_sel = st.selectbox("Seleccionar Mes de Liquidación", sorted(meses, reverse=True))
        
        # Procesar cobros del mes seleccionado
        df_mes = df_p[df_p['Fecha_DT'].dt.strftime('%Y-%m') == mes_sel].copy()
        df_mes['Pago'] = pd.to_numeric(df_mes['Pago'], errors='coerce').fillna(0)
        
        # IMPORTANTE: Solo contamos lo que el paciente YA pagó (Pago > 1)
        # y lo liquidamos por sesión realizada si es el caso
        df_mes['Comision'] = df_mes.apply(lambda x: x['Pago'] * 0.3 if x['Origen'] == "Socio Gimnasio" else x['Pago'] * 0.2, axis=1)
        df_mes['Neto'] = df_mes['Pago'] - df_mes['Comision']
        
        col1, col2, col3 = st.columns(3)
        col1.metric(f"Recaudado {mes_sel}", f"${df_mes['Pago'].sum():,.0f}")
        col2.metric("Total Comisiones", f"-${df_mes['Comision'].sum():,.0f}")
        col3.metric("Utilidad Neta", f"${df_mes['Neto'].sum():,.0f}")
        
        st.subheader("Desglose de Liquidación")
        # Mostrar solo columnas relevantes y formatear
        st.dataframe(df_mes[['Fecha_Inicio', 'Nombre', 'Servicio', 'Origen', 'Pago', 'Comision', 'Neto']], use_container_width=True)
