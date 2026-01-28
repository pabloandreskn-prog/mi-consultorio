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

# --- 2. CONEXIÓN Y FUNCIONES CRÍTICAS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def obtener_datos(pestaña):
    return conn.read(worksheet=pestaña, ttl="0")

def normalizar_hora(hora_str):
    """Sincroniza formato de Google Sheets (9:00:00 a.m.) con el semáforo"""
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
    st.caption("v6.1 - LÓGICA DE SESIONES CORREGIDA")
    st.divider()
    opciones = ["📅 Agenda & Turnos", "📝 Registro & Renovación", "🔍 Buscador & Gestión", "📊 Panel Financiero"]
    st.session_state['menu_actual'] = st.radio("MENÚ PRINCIPAL", opciones, index=opciones.index(st.session_state['menu_actual']))

# --- MÓDULO 1: AGENDA & TURNOS ---
if st.session_state['menu_actual'] == "📅 Agenda & Turnos":
    st.header("Agenda Diaria")
    fecha_ver = st.date_input("Ver calendario", datetime.now(), key="date_main")
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
            # Info del paciente y lógica de sesiones corregida
            p_ficha = df_p[df_p['Nombre'] == t['Paciente']].tail(1).to_dict('records')
            p = p_ficha[0] if p_ficha else {}
            
            # Conteo real: contratadas vs agendadas
            total_contratadas = int(p.get('Sesiones_Totales', 0))
            agendadas = len(df_a[df_a['Paciente'] == t['Paciente']])
            restantes = total_contratadas - agendadas
            
            # Alerta de pago: Si el pago en la ficha es 0 o menor
            debe_pagar = float(p.get('Pago', 0)) <= 0

            with st.container():
                c1, c2, c3 = st.columns([3.5, 1, 1])
                with c1:
                    status_pago = '<span class="alert-pago">DEBE PAGAR</span>' if debe_pagar else ""
                    color_res = BRAND_RED if restantes <= 1 else "#2e7d32"
                    st.markdown(f"""
                        <div class="card">
                            <b>{t["Hora"]}</b> | <b>{t["Paciente"]}</b> {status_pago} 
                            <span class='sesiones-tag' style='color:{color_res}'>{restantes} restantes</span><br>
                            <small>{t["Servicio"]}</small>
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
                    if debe_pagar: st.button("💵 Cobrar", key=f"pay_{i}")
    else:
        st.info("No hay turnos agendados para este día.")

# --- MÓDULO 2: REGISTRO & RENOVACIÓN ---
elif st.session_state['menu_actual'] == "📝 Registro & Renovación":
    st.header("Gestión de Pacientes")
    re = st.session_state.get('reagenda_data', {})
    
    with st.form("form_registro"):
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Nombre Completo", value=re.get('Paciente', ""))
            dni = st.text_input("DNI", value=re.get('DNI', ""))
            whatsapp = st.text_input("WhatsApp", value=re.get('WhatsApp', ""))
        with c2:
            dx = st.text_input("Diagnóstico (DX)", value=re.get('DX', ""))
            origen = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"], index=0 if re.get('Origen') == "Socio Gimnasio" else 1)
            servicio = st.selectbox("Servicio", ["Plan X10", "Plan X5", "Sesion Individual", "Evaluacion"])
        
        pago = st.number_input("Monto Pagado ($)", min_value=0)
        fecha = st.date_input("Fecha Turno")
        hora = st.selectbox("Hora Turno", HORARIOS_LABORALES)
        
        st.divider()
        auto_pack = st.checkbox("Programar pack completo")
        dias = st.multiselect("Días (solo para packs)", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])

        if st.form_submit_button("GUARDAR REGISTRO"):
            df_a = obtener_datos("agenda")
            # Borrar turno viejo si es reagenda
            if re:
                df_a = df_a[~((df_a['Paciente'] == re['Paciente']) & (df_a['Fecha'].astype(str) == str(re['Fecha_Vieja'])))]
            
            # Lógica de creación de turnos
            cant = 10 if "X10" in servicio else (5 if "X5" in servicio else 1)
            nuevos = []
            if auto_pack and dias:
                d_map = {"Lunes":0, "Martes":1, "Miércoles":2, "Jueves":3, "Viernes":4, "Sábado":5}
                target_dias = [d_map[d] for d in dias]
                curr_f, cont = fecha, 0
                while cont < cant:
                    if curr_f.weekday() in target_dias:
                        nuevos.append([str(curr_f), hora, nombre, servicio])
                        cont += 1
                    curr_f += timedelta(days=1)
            else:
                nuevos.append([str(fecha), hora, nombre, servicio])
            
            # Actualizar Agenda
            df_new_a = pd.concat([df_a, pd.DataFrame(nuevos, columns=["Fecha", "Hora", "Paciente", "Servicio"])], ignore_index=True)
            conn.update(worksheet="agenda", data=df_new_a)
            
            # Actualizar Pacientes
            df_p = obtener_datos("pacientes")
            df_new_p = pd.concat([df_p, pd.DataFrame([[dni, nombre, whatsapp, dx, origen, servicio, pago, str(fecha), cant]], 
                                columns=["DNI", "Nombre", "WhatsApp", "DX", "Origen", "Servicio", "Pago", "Fecha_Inicio", "Sesiones_Totales"])], ignore_index=True)
            conn.update(worksheet="pacientes", data=df_new_p)

            st.session_state.pop('reagenda_data', None)
            st.session_state['menu_actual'] = "📅 Agenda & Turnos"
            st.rerun()

# --- MÓDULOS PRESERVADOS (3 y 4) ---
elif st.session_state['menu_actual'] == "🔍 Buscador & Gestión":
    st.header("Historial de Pacientes")
    df_p = obtener_datos("pacientes")
    busc = st.text_input("Buscar por nombre")
    if busc:
        st.dataframe(df_p[df_p['Nombre'].str.contains(busc, case=False, na=False)], use_container_width=True)
    else: st.dataframe(df_p, use_container_width=True)

elif st.session_state['menu_actual'] == "📊 Panel Financiero":
    st.header("Balance Mensual")
    df_p = obtener_datos("pacientes")
    if not df_p.empty:
        df_p['Fecha_Inicio'] = pd.to_datetime(df_p['Fecha_Inicio'])
        df_p['Mes'] = df_p['Fecha_Inicio'].dt.strftime('%m-%Y')
        m = st.selectbox("Mes", sorted(df_p['Mes'].unique(), reverse=True))
        df_m = df_p[df_p['Mes'] == m].copy()
        
        df_m['Comision'] = df_m.apply(lambda x: float(x['Pago']) * (0.3 if x['Origen'] == "Socio Gimnasio" else 0.2), axis=1)
        df_m['Neto'] = df_m['Pago'].astype(float) - df_m['Comision']
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Ingresos", f"${df_m['Pago'].sum():,.0f}")
        c2.metric("Comisiones", f"-${df_m['Comision'].sum():,.0f}")
        c3.metric("Neto Elite", f"${df_m['Neto'].sum():,.0f}")
        st.dataframe(df_m[['Fecha_Inicio', 'Nombre', 'Servicio', 'Pago', 'Comision', 'Neto']], use_container_width=True)
