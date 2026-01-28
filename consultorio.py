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
    .card {{ 
        background: white; padding: 18px; border-radius: 12px; 
        border-left: 6px solid {BRAND_GREEN}; margin-bottom: 12px; 
        box-shadow: 0px 3px 6px rgba(0,0,0,0.08); 
    }}
    .dx-label {{ color: #555; font-style: italic; font-size: 13px; margin-top: 5px; }}
    .sesiones-tag {{ background: #e8f5e9; padding: 2px 8px; border-radius: 10px; font-weight: bold; font-size: 12px; }}
    .alert-pago {{ color: {BRAND_RED}; font-weight: bold; font-size: 11px; border: 1px solid {BRAND_RED}; padding: 1px 4px; border-radius: 4px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN Y FUNCIONES ---
conn = st.connection("gsheets", type=GSheetsConnection)

def obtener_datos(pestaña):
    return conn.read(worksheet=pestaña, ttl="0")

def normalizar_hora(hora_str):
    try:
        h = str(hora_str).lower().replace(" hs", "").replace(".", "").strip()
        if "am" in h or "pm" in h:
            return datetime.strptime(h, "%I:%M:%S %p").strftime("%H:%M")
        return datetime.strptime(h[:5], "%H:%M").strftime("%H:%M")
    except: return str(hora_str)[:5]

HORARIOS_LABORALES = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "16:00", "17:00", "18:00", "19:00", "20:00"]

if 'menu_actual' not in st.session_state:
    st.session_state['menu_actual'] = "📅 Agenda & Turnos"

# --- 3. NAVEGACIÓN ---
with st.sidebar:
    st.markdown(f'<h1 style="color:{BRAND_GREEN};">🌿 ELITE SYSTEM</h1>', unsafe_allow_html=True)
    st.caption("v7.0 - LÓGICA DE SESIONES & COBRO")
    st.divider()
    opciones = ["📅 Agenda & Turnos", "📝 Registro & Renovación", "🔍 Buscador & Gestión", "📊 Panel Financiero"]
    st.session_state['menu_actual'] = st.radio("MENÚ", opciones, index=opciones.index(st.session_state['menu_actual']))

# --- MÓDULO 1: AGENDA & TURNOS ---
if st.session_state['menu_actual'] == "📅 Agenda & Turnos":
    st.header("Agenda Diaria")
    fecha_ver = st.date_input("Ver calendario", datetime.now(), key="main_calendar")
    fecha_str = fecha_ver.strftime("%Y-%m-%d")
    
    df_a = obtener_datos("agenda")
    df_p = obtener_datos("pacientes")
    
    turnos_dia = df_a[df_a['Fecha'].astype(str) == fecha_str].copy()
    horas_ocupadas = [normalizar_hora(h) for h in turnos_dia['Hora'].tolist()]

    with st.expander("🔍 Estado de Disponibilidad", expanded=True):
        cols = st.columns(len(HORARIOS_LABORALES))
        for idx, h in enumerate(HORARIOS_LABORALES):
            color = BRAND_ORANGE if h in horas_ocupadas else BRAND_GREEN
            cols[idx].markdown(f"<div style='text-align:center; color:{color};'><b>{'🟠' if h in horas_ocupadas else '🟢'} {h}</b></div>", unsafe_allow_html=True)

    st.divider()

    if not turnos_dia.empty:
        for i, t in turnos_dia.sort_values(by="Hora").iterrows():
            # Obtener el registro más reciente de este paciente
            p_ficha = df_p[df_p['Nombre'] == t['Paciente']].tail(1).to_dict('records')
            p = p_ficha[0] if p_ficha else {}
            
            # Lógica de Sesiones Restantes (Solo para Planes)
            servicio_actual = str(t['Servicio'])
            sesiones_info = ""
            if "Plan X" in servicio_actual:
                total = int(p.get('Sesiones_Totales', 0))
                # Contamos turnos desde la fecha de inicio del último pack
                fecha_f = str(p.get('Fecha_Inicio', '2000-01-01'))
                consumidas = len(df_a[(df_a['Paciente'] == t['Paciente']) & (df_a['Fecha'].astype(str) >= fecha_f)])
                restantes = max(0, total - consumidas)
                c_res = BRAND_RED if restantes <= 1 else "#2e7d32"
                sesiones_info = f"<span class='sesiones-tag' style='color:{c_res}'>{restantes} restantes</span>"
            else:
                sesiones_info = f"<span class='sesiones-tag' style='color:#666'>Servicio Único</span>"

            # Estado de Pago
            debe_pagar = float(p.get('Pago', 0)) <= 0

            with st.container():
                c1, c2, c3 = st.columns([3.5, 1, 1])
                with c1:
                    status_pago = '<span class="alert-pago">DEBE PAGAR</span>' if debe_pagar else ""
                    st.markdown(f"""
                        <div class="card">
                            <b>{t["Hora"]}</b> | <b>{t["Paciente"]}</b> {status_pago} {sesiones_info}<br>
                            <small>{servicio_actual}</small>
                            <div class='dx-label'>📋 DX: {p.get('DX', 'N/A')}</div>
                        </div>
                    """, unsafe_allow_html=True)
                with c2:
                    if st.button("🔄 Mover", key=f"mov_{i}"):
                        st.session_state['reagenda_data'] = {
                            'Paciente': t['Paciente'], 'Servicio': t['Servicio'],
                            'Fecha_Vieja': t['Fecha'], 'Hora_Vieja': t['Hora'],
                            'DNI': p.get('DNI', ""), 'WhatsApp': p.get('WhatsApp', ""),
                            'DX': p.get('DX', ""), 'Origen': p.get('Origen', "Socio Gimnasio")
                        }
                        st.session_state['menu_actual'] = "📝 Registro & Renovación"
                        st.rerun()
                with c3:
                    if debe_pago:
                        if st.button("💵 Cobrar", key=f"pay_{i}"):
                            # Actualizar el último registro del paciente con un monto simbólico para quitar la alerta
                            df_p.loc[df_p[df_p['Nombre'] == t['Paciente']].index[-1], 'Pago'] = 1 
                            conn.update(worksheet="pacientes", data=df_p)
                            st.success(f"Cobro de {t['Paciente']} registrado")
                            st.rerun()
    else:
        st.info("Sin turnos para hoy.")

# --- MÓDULOS 2, 3 Y 4 PRESERVADOS ---
elif st.session_state['menu_actual'] == "📝 Registro & Renovación":
    st.header("Gestión de Turnos")
    re = st.session_state.get('reagenda_data', {})
    with st.form("registro_form"):
        c1, c2 = st.columns(2)
        with c1:
            nom = st.text_input("Paciente", value=re.get('Paciente', ""))
            dni = st.text_input("DNI", value=re.get('DNI', ""))
        with c2:
            dx = st.text_input("DX", value=re.get('DX', ""))
            srv = st.selectbox("Servicio", ["Plan X10", "Plan X5", "Sesion Individual", "Evaluacion"])
        pago = st.number_input("Pago", min_value=0)
        f = st.date_input("Fecha")
        h = st.selectbox("Hora", HORARIOS_LABORALES)
        if st.form_submit_button("CONFIRMAR"):
            # Lógica de guardado idéntica a v6.1 para mantener estabilidad
            df_a = obtener_datos("agenda")
            if re: df_a = df_a[~((df_a['Paciente'] == re['Paciente']) & (df_a['Fecha'].astype(str) == str(re['Fecha_Vieja'])))]
            nuevo_a = pd.DataFrame([[str(f), h, nom, srv]], columns=["Fecha", "Hora", "Paciente", "Servicio"])
            conn.update(worksheet="agenda", data=pd.concat([df_a, nuevo_a], ignore_index=True))
            
            df_p = obtener_datos("pacientes")
            cant = 10 if "X10" in srv else (5 if "X5" in srv else 1)
            nuevo_p = pd.DataFrame([[dni, nom, "", dx, "Socio Gimnasio", srv, pago, str(f), cant]], 
                                    columns=["DNI", "Nombre", "WhatsApp", "DX", "Origen", "Servicio", "Pago", "Fecha_Inicio", "Sesiones_Totales"])
            conn.update(worksheet="pacientes", data=pd.concat([df_p, nuevo_p], ignore_index=True))
            st.session_state.pop('reagenda_data', None)
            st.session_state['menu_actual'] = "📅 Agenda & Turnos"
            st.rerun()

elif st.session_state['menu_actual'] == "🔍 Buscador & Gestión":
    st.header("Buscador")
    df_p = obtener_datos("pacientes")
    busc = st.text_input("Nombre")
    if busc: st.dataframe(df_p[df_p['Nombre'].str.contains(busc, case=False, na=False)], use_container_width=True)

elif st.session_state['menu_actual'] == "📊 Panel Financiero":
    st.header("Panel Financiero")
    df_p = obtener_datos("pacientes")
    if not df_p.empty:
        df_p['Fecha_Inicio'] = pd.to_datetime(df_p['Fecha_Inicio'])
        df_p['Mes'] = df_p['Fecha_Inicio'].dt.strftime('%m-%Y')
        m = st.selectbox("Mes", sorted(df_p['Mes'].unique(), reverse=True))
        df_m = df_p[df_p['Mes'] == m].copy()
        df_m['Comision'] = df_m.apply(lambda x: float(x['Pago']) * (0.3 if x['Origen'] == "Socio Gimnasio" else 0.2), axis=1)
        st.metric("Neto Elite", f"${(df_m['Pago'].astype(float).sum() - df_m['Comision'].sum()):,.0f}")
        st.dataframe(df_m, use_container_width=True)
