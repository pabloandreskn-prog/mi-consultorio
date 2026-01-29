import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Elite System v12.0", layout="wide", page_icon="🌿")

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
    .alert-pago {{ color: {BRAND_RED}; font-weight: bold; font-size: 10px; border: 1px solid {BRAND_RED}; padding: 2px 5px; border-radius: 4px; text-transform: uppercase; }}
    .renovacion-tag {{ background: #fff3e0; color: {BRAND_ORANGE}; padding: 2px 10px; border-radius: 10px; font-weight: bold; border: 1px solid {BRAND_ORANGE}; font-size: 12px; }}
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

if 'menu' not in st.session_state:
    st.session_state.menu = "📅 Agenda"
if 'p_renovando' not in st.session_state:
    st.session_state.p_renovando = {}

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
    fecha_sel = st.date_input("Ver calendario", datetime.now(), key="agenda_date")
    
    df_a = cargar_datos("agenda")
    df_p = cargar_datos("pacientes")
    
    turnos_dia = df_a[df_a['Fecha'].astype(str) == str(fecha_sel)].copy()
    
    if not turnos_dia.empty:
        for idx, row in turnos_dia.sort_values(by="Hora").iterrows():
            p_ficha = df_p[df_p['Nombre'] == row['Paciente']].tail(1)
            debe_pago = False
            necesita_renovar = False
            
            if not p_ficha.empty:
                p = p_ficha.iloc[0]
                debe_pago = float(p.get('Pago', 0)) <= 0
                if "Plan" in str(row['Servicio']):
                    total = int(p.get('Sesiones_Totales', 0))
                    asistencias = len(df_a[(df_a['Paciente'] == row['Paciente']) & (df_a['Fecha'].astype(str) >= str(p['Fecha_Inicio']))])
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
                        st.session_state.p_renovando = {"Nombre": row['Paciente'], "DNI": p['DNI'] if not p_ficha.empty else ""}
                        st.session_state.menu = "📝 Registro"
                        st.rerun()

            if st.session_state.get(f"edit_{idx}", False):
                with st.expander("Configurar nueva fecha/hora", expanded=True):
                    ce1, ce2 = st.columns(2)
                    nf = ce1.date_input("Nueva Fecha", value=fecha_sel, key=f"nf_{idx}")
                    # Solución al ValueError: Verificamos si la hora existe en la lista
                    hora_val = row['Hora'] if row['Hora'] in HORARIOS else HORARIOS[0]
                    nh = ce2.selectbox("Nueva Hora", HORARIOS, index=HORARIOS.index(hora_val), key=f"nh_{idx}")
                    if st.button("Guardar Cambio", key=f"s_{idx}"):
                        df_a.loc[idx, 'Fecha'] = str(nf)
                        df_a.loc[idx, 'Hora'] = nh
                        conn.update(worksheet="agenda", data=df_a)
                        st.session_state[f"edit_{idx}"] = False
                        st.rerun()
    else:
        st.info("No hay turnos para hoy.")

# --- 6. MÓDULO: REGISTRO & RENOVACIÓN ---
elif st.session_state.menu == "📝 Registro":
    st.header("Formulario de Ingreso / Renovación")
    p_data = st.session_state.p_renovando
    
    with st.form("f_reg"):
        c1, c2 = st.columns(2)
        nom = c1.text_input("Paciente", value=p_data.get("Nombre", ""))
        dni = c2.text_input("DNI", value=p_data.get("DNI", ""))
        orig = c1.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
        serv = c2.selectbox("Servicio", list(SERVICIOS_PRECIOS.keys()))
        
        # Selección de días fijos para planes
        dias_fijos = st.multiselect("Días fijos (solo para planes)", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"])
        num_semanas = st.number_input("Cantidad de semanas a agendar", min_value=1, max_value=10, value=1)
        
        monto = st.number_input("Monto ($)", value=0)
        f_inicio = st.date_input("Fecha Inicio")
        h_inicio = st.selectbox("Hora", HORARIOS)
        
        if st.form_submit_button("Confirmar e Iniciar"):
            df_p = cargar_datos("pacientes")
            cant_s = 10 if "x10" in serv else (5 if "x 5" in serv else 1)
            new_p = pd.DataFrame([[dni, nom, "", "", orig, serv, monto, str(f_inicio), cant_s]], columns=df_p.columns)
            conn.update(worksheet="pacientes", data=pd.concat([df_p, new_p], ignore_index=True))
            
            # Lógica de agendamiento múltiple
            df_a = cargar_datos("agenda")
            nuevos_turnos = []
            dict_dias = {"Lunes":0, "Martes":1, "Miércoles":2, "Jueves":3, "Viernes":4}
            
            if dias_fijos:
                for i in range(num_semanas * 7):
                    dia_iter = f_inicio + timedelta(days=i)
                    if dia_iter.weekday() in [dict_dias[d] for d in dias_fijos]:
                        nuevos_turnos.append([str(dia_iter), h_inicio, nom, serv])
            else:
                nuevos_turnos.append([str(f_inicio), h_inicio, nom, serv])
            
            df_a_new = pd.DataFrame(nuevos_turnos, columns=df_a.columns)
            conn.update(worksheet="agenda", data=pd.concat([df_a, df_a_new], ignore_index=True))
            
            st.session_state.p_renovando = {}
            st.success("Registrado correctamente.")
            st.rerun()

# --- 7. MÓDULO: FINANZAS ---
elif st.session_state.menu == "📊 Finanzas":
    st.header("Panel Financiero")
    df_p = cargar_datos("pacientes")
    if not df_p.empty:
        # Filtrar solo lo cobrado (Pago > 0)
        df_p['Pago'] = pd.to_numeric(df_p['Pago'], errors='coerce').fillna(0)
        cobrado = df_p[df_p['Pago'] > 1].copy() # Tomamos montos reales de inscripción
        
        cobrado['Comisión'] = cobrado.apply(lambda x: x['Pago'] * 0.3 if x['Origen'] == "Socio Gimnasio" else x['Pago'] * 0.2, axis=1)
        cobrado['Neto'] = cobrado['Pago'] - cobrado['Comisión']
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Bruto (Cobrado)", f"${cobrado['Pago'].sum():,.0f}")
        c2.metric("Comisiones Total", f"-${cobrado['Comisión'].sum():,.0f}")
        c3.metric("Neto Elite", f"${cobrado['Neto'].sum():,.0f}")
        
        st.subheader("Detalle de Comisiones por Atención")
        st.table(cobrado[['Fecha_Inicio', 'Nombre', 'Servicio', 'Pago', 'Comisión', 'Neto']])
