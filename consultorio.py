import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta

# --- 1. CONFIGURACIÓN ---
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
    .sesiones-tag {{ background: #e8f5e9; color: #2e7d32; padding: 2px 8px; border-radius: 10px; font-weight: bold; font-size: 12px; }}
    .alert-pago {{ color: {BRAND_RED}; font-weight: bold; font-size: 11px; border: 1px solid {BRAND_RED}; padding: 1px 4px; border-radius: 4px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN Y UTILIDADES ---
conn = st.connection("gsheets", type=GSheetsConnection)

def obtener_datos(pestaña):
    return conn.read(worksheet=pestaña, ttl="0")

def normalizar_hora(hora_str):
    """Maneja el formato '9:00:00 a.m.' de Google Sheets"""
    try:
        h = str(hora_str).lower().replace(".", "").strip()
        if "am" in h or "pm" in h:
            # Limpieza para strptime
            h = h.replace(" a m", " am").replace(" p m", " pm")
            return datetime.strptime(h, "%I:%M:%S %p").strftime("%H:%M")
        return datetime.strptime(h[:5], "%H:%M").strftime("%H:%M")
    except:
        return str(hora_str)[:5]

HORARIOS_LABORALES = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "16:00", "17:00", "18:00", "19:00", "20:00"]

if 'menu_actual' not in st.session_state:
    st.session_state['menu_actual'] = "📅 Agenda & Turnos"

# --- 3. NAVEGACIÓN ---
with st.sidebar:
    st.markdown(f'<h1 style="color:{BRAND_GREEN};">🌿 ELITE SYSTEM</h1>', unsafe_allow_html=True)
    st.caption("v6.1 - CORRECCIÓN DE SESIONES")
    opciones = ["📅 Agenda & Turnos", "📝 Registro & Renovación", "🔍 Buscador & Gestión", "📊 Panel Financiero"]
    seleccion = st.radio("MENÚ", opciones, index=opciones.index(st.session_state['menu_actual']))
    st.session_state['menu_actual'] = seleccion

# --- MÓDULO 1: AGENDA & TURNOS ---
if st.session_state['menu_actual'] == "📅 Agenda & Turnos":
    st.header("Agenda Diaria")
    fecha_ver = st.date_input("Ver calendario", datetime.now(), key="main_calendar")
    fecha_str = fecha_ver.strftime("%Y-%m-%d")
    
    df_a = obtener_datos("agenda")
    df_p = obtener_datos("pacientes")
    
    turnos_dia = df_a[df_a['Fecha'].astype(str) == fecha_str].copy()
    horas_ocupadas = [normalizar_hora(h) for h in turnos_dia['Hora'].tolist()]

    with st.expander("🔍 Disponibilidad de Horarios", expanded=True):
        cols = st.columns(len(HORARIOS_LABORALES))
        for idx, h in enumerate(HORARIOS_LABORALES):
            color = BRAND_ORANGE if h in horas_ocupadas else BRAND_GREEN
            icon = "🟠" if h in horas_ocupadas else "🟢"
            cols[idx].markdown(f"<div style='text-align:center; color:{color};'><b>{icon} {h}</b></div>", unsafe_allow_html=True)

    st.divider()

    if not turnos_dia.empty:
        for i, t in turnos_dia.sort_values(by="Hora").iterrows():
            # LÓGICA DE SESIONES CORREGIDA
            p_historial = df_p[df_p['Nombre'] == t['Paciente']].sort_index(ascending=False)
            if not p_historial.empty:
                ultimo_plan = p_historial.iloc[0] # La compra más reciente
                total_contratadas = int(ultimo_plan.get('Sesiones_Totales', 1))
                fecha_compra = pd.to_datetime(ultimo_plan['Fecha_Inicio'])
                
                # Contamos sesiones en agenda desde la fecha de compra hasta hoy
                asistidas = len(df_a[(df_a['Paciente'] == t['Paciente']) & 
                                     (pd.to_datetime(df_a['Fecha']) >= fecha_compra) & 
                                     (pd.to_datetime(df_a['Fecha']) <= datetime.now())])
                restantes = total_contratadas - asistidas
            else:
                restantes, total_contratadas = 0, 0
                ultimo_plan = {}

            color_sesion = BRAND_RED if restantes <= 1 else "#2e7d32"

            with st.container():
                c1, c2, c3 = st.columns([3.5, 1, 1])
                with c1:
                    status = "" if "Plan" in str(t['Servicio']) else '<span class="alert-pago">DEBE PAGAR</span>'
                    st.markdown(f"""
                        <div class="card">
                            <b>{t["Hora"]}</b> | <b>{t["Paciente"]}</b> {status} 
                            <span class='sesiones-tag' style='color:{color_sesion}'>{restantes} restantes</span><br>
                            <small>{t["Servicio"]}</small>
                            <div class='dx-label'>📋 DX: {ultimo_plan.get('DX', 'N/A')}</div>
                        </div>
                    """, unsafe_allow_html=True)
                with c2:
                    if st.button("🔄 Mover", key=f"mov_{i}"):
                        st.session_state['reagenda_data'] = {
                            'Paciente': t['Paciente'], 'Servicio': t['Servicio'],
                            'Fecha_Vieja': t['Fecha'], 'Hora_Vieja': t['Hora'],
                            'DNI': ultimo_plan.get('DNI', ""), 'WhatsApp': ultimo_plan.get('WhatsApp', ""),
                            'DX': ultimo_plan.get('DX', ""), 'Origen': ultimo_plan.get('Origen', "Socio Gimnasio")
                        }
                        st.session_state['menu_actual'] = "📝 Registro & Renovación"
                        st.rerun()
                with c3:
                    if "Plan" not in str(t['Servicio']): st.button("💵 Cobrar", key=f"cob_{i}")
    else:
        st.info("No hay turnos para esta fecha.")

# --- MÓDULO 2: REGISTRO & RENOVACIÓN (Preservado) ---
elif st.session_state['menu_actual'] == "📝 Registro & Renovación":
    st.header("Gestión de Turnos")
    re = st.session_state.get('reagenda_data', {})
    with st.form("form_registro"):
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Paciente", value=re.get('Paciente', ""))
            dni = st.text_input("DNI", value=re.get('DNI', ""))
            whatsapp = st.text_input("WhatsApp", value=re.get('WhatsApp', ""))
        with c2:
            dx = st.text_input("Diagnóstico (DX)", value=re.get('DX', ""))
            origen = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"], index=0 if re.get('Origen') == "Socio Gimnasio" else 1)
            servicio = st.selectbox("Servicio", ["Plan X10", "Plan X5", "Sesion Individual", "Evaluacion"])
        
        monto = st.number_input("Pago ($)", min_value=0)
        f_inicio = st.date_input("Fecha", value=datetime.now())
        h_inicio = st.selectbox("Hora", HORARIOS_LABORALES)
        
        st.divider()
        auto_prog = st.checkbox("Programar Pack completo")
        dias_selec = st.multiselect("Días para el pack", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])

        if st.form_submit_button("CONFIRMAR"):
            df_agenda = obtener_datos("agenda")
            if re: # Borrar turno viejo si es reagenda
                df_agenda = df_agenda[~((df_agenda['Paciente'] == re['Paciente']) & (df_agenda['Fecha'].astype(str) == str(re['Fecha_Vieja'])))]
            
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
            
            conn.update(worksheet="agenda", data=pd.concat([df_agenda, pd.DataFrame(nuevos, columns=["Fecha", "Hora", "Paciente", "Servicio"])], ignore_index=True))
            
            df_p = obtener_datos("pacientes")
            nuevo_p = pd.DataFrame([[dni, nombre, whatsapp, dx, origen, servicio, monto, str(f_inicio), cant]], columns=["DNI", "Nombre", "WhatsApp", "DX", "Origen", "Servicio", "Pago", "Fecha_Inicio", "Sesiones_Totales"])
            conn.update(worksheet="pacientes", data=pd.concat([df_p, nuevo_p], ignore_index=True))

            st.session_state.pop('reagenda_data', None)
            st.session_state['menu_actual'] = "📅 Agenda & Turnos"
            st.rerun()

# --- MÓDULOS 3 Y 4 (Preservados e Intactos) ---
elif st.session_state['menu_actual'] == "🔍 Buscador & Gestión":
    st.header("Buscador")
    df_p = obtener_datos("pacientes")
    busc = st.text_input("Nombre o DNI")
    if busc:
        res = df_p[df_p['Nombre'].str.contains(busc, case=False, na=False)]
        st.dataframe(res, use_container_width=True)

elif st.session_state['menu_actual'] == "📊 Panel Financiero":
    st.header("Contabilidad")
    df_p = obtener_datos("pacientes")
    if not df_p.empty:
        df_p['Fecha_Inicio'] = pd.to_datetime(df_p['Fecha_Inicio'])
        df_p['Mes'] = df_p['Fecha_Inicio'].dt.strftime('%m-%Y')
        mes = st.selectbox("Mes", sorted(df_p['Mes'].unique(), reverse=True))
        df_mes = df_p[df_p['Mes'] == mes].copy()
        df_mes['Comision'] = df_mes.apply(lambda x: float(x['Pago']) * (0.3 if x['Origen'] == "Socio Gimnasio" else 0.2), axis=1)
        st.metric("Neto Mes", f"${(df_mes['Pago'].sum() - df_mes['Comision'].sum()):,.0f}")
        st.dataframe(df_mes, use_container_width=True)
