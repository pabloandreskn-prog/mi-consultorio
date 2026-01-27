import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import urllib.parse
import re

# --- 1. CONFIGURACIÓN ESTÉTICA ---
st.set_page_config(page_title="Elite System Ultra", layout="wide", page_icon="🌿")

BRAND_GREEN = "#60b067"
BRAND_BLACK = "#1E1E1E"

st.markdown(f"""
    <style>
    .stApp {{ background-color: #FAFAFA; }}
    .stButton>button {{ background-color: {BRAND_GREEN}; color: white; border-radius: 12px; font-weight: bold; height: 3em; }}
    .main-title {{ color: {BRAND_GREEN}; font-size: 32px; font-weight: bold; margin-bottom: 20px; }}
    .card {{
        background: white; padding: 20px; border-radius: 15px; border-left: 5px solid {BRAND_GREEN}; 
        margin-bottom: 15px; box-shadow: 0px 4px 10px rgba(0,0,0,0.03);
    }}
    .stat-box {{ background: white; padding: 20px; border-radius: 15px; text-align: center; border: 1px solid #eee; }}
    .sidebar-brand {{ font-size: 24px; font-weight: bold; color: {BRAND_GREEN}; text-align: center; padding: 20px 0; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN Y CARGA ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_nube(pestana):
    return conn.read(worksheet=pestana, ttl="0")

# --- 3. LÓGICA DE NEGOCIO ---
def calcular_fechas_fijas(fecha_inicio, dias_semana, cantidad):
    dias_map = {"Lunes": 0, "Martes": 1, "Miércoles": 2, "Jueves": 3, "Viernes": 4, "Sábado": 5}
    nums_objetivo = [dias_map[d] for d in dias_semana]
    fechas_generadas = []
    fecha_actual = fecha_inicio
    
    while len(fechas_generadas) < cantidad:
        if fecha_actual.weekday() in nums_objetivo:
            fechas_generadas.append(str(fecha_actual))
        fecha_actual += timedelta(days=1)
    return fechas_generadas

def generar_link_wpp(nombre, fecha, hora, contacto):
    contacto_limpio = re.sub(r'\D', '', str(contacto))
    msj = f"Hola {nombre}, te recordamos tu sesión en *Elite System* para el día {fecha} a las {hora} hs. 🌿 ¡Te esperamos!"
    return f"https://wa.me/{contacto_limpio}?text={urllib.parse.quote(msj)}"

# --- 4. INTERFAZ ---
with st.sidebar:
    st.markdown('<div class="sidebar-brand">🌿 ELITE SYSTEM <br><span style="font-size:12px; color:gray;">Gestiōn de Alto Nivel</span></div>', unsafe_allow_html=True)
    menu = st.radio("NAVEGACIÓN", ["📅 Agenda & Turnos", "📝 Registro & Cobro", "📊 Inteligencia Financiera"], label_visibility="collapsed")
    st.divider()
    st.info("💡 Consejo: Revisa las alertas de renovación antes de iniciar el día.")

# --- MÓDULO 1: AGENDA & TURNOS ---
if menu == "📅 Agenda & Turnos":
    st.markdown('<p class="main-title">Control de Agenda</p>', unsafe_allow_html=True)
    
    # Carga de datos
    df_a = cargar_nube("agenda")
    hoy = datetime.now().date()
    manana = hoy + timedelta(days=1)
    
    tab1, tab2, tab3 = st.tabs(["🕒 Turnos Hoy/Mañana", "🔄 Reprogramar", "✨ Disponibilidad"])

    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Turnos de Hoy")
            t_hoy = df_a[df_a['Fecha'].astype(str) == str(hoy)]
            if t_hoy.empty: st.write("No hay citas.")
            for _, t in t_hoy.sort_values("Hora").iterrows():
                with st.container():
                    col_info, col_btn = st.columns([3, 1])
                    col_info.markdown(f'<div class="card"><b>{t["Hora"]} hs</b> | {t["Paciente"]}<br><small>{t["Servicio"]}</small></div>', unsafe_allow_html=True)
                    url_wpp = generar_link_wpp(t['Paciente'], t['Fecha'], t['Hora'], t['Contacto'])
                    col_btn.markdown(f'<br><a href="{url_wpp}" target="_blank"><button style="width:100%; border-radius:10px; border:1px solid #25D366; background:white; color:#25D366; cursor:pointer;">WhatsApp</button></a>', unsafe_allow_html=True)

        with c2:
            st.subheader("Vista Previa Mañana")
            t_man = df_a[df_a['Fecha'].astype(str) == str(manana)]
            for _, t in t_man.sort_values("Hora").iterrows():
                st.markdown(f'<div class="card" style="border-left-color:gray;"><b>{t["Hora"]} hs</b> | {t["Paciente"]}</div>', unsafe_allow_html=True)

    with tab2:
        st.subheader("Reprogramar Turno")
        with st.form("reprogramar"):
            p_repro = st.selectbox("Seleccionar Paciente", df_a['Paciente'].unique())
            f_nueva = st.date_input("Nueva Fecha")
            h_nueva = st.time_input("Nueva Hora")
            if st.form_submit_button("Actualizar en Nube"):
                st.warning("Para editar: Modifica directamente en tu Google Sheet y presiona R.")

    with tab3:
        st.subheader("Espacios Libres")
        horas_lab = ["08:30", "09:30", "10:30", "16:00", "17:00", "18:00"]
        ocupadas = t_hoy['Hora'].tolist()
        for h in horas_lab:
            if h not in ocupadas: st.success(f"✅ Disponible a las {h}")

# --- MÓDULO 2: REGISTRO & COBRO ---
elif menu == "📝 Registro & Cobro":
    st.markdown('<p class="main-title">Registro & Ventas</p>', unsafe_allow_html=True)
    
    # ALERTAS DE RENOVACIÓN
    df_p = cargar_nube("pacientes")
    criticos = df_p[df_p['Sesiones_Restantes'].astype(int) <= 1]
    if not criticos.empty:
        for _, c in criticos.iterrows():
            st.error(f"⚠️ **RENOVACIÓN:** {c['Nombre']} tiene solo {c['Sesiones_Restantes']} sesión restante.")

    with st.form("form_alta", clear_on_submit=True):
        c1, c2, c3 = st.columns([2, 1, 1])
        nombre = c1.text_input("Nombre del Paciente")
        dni = c2.text_input("DNI")
        wpp = c3.text_input("WhatsApp (ej. 549341...)")
        
        serv = st.selectbox("Servicio / Plan", ["Sesión Individual", "Plan X5", "Plan X10", "Masaje"])
        monto = st.number_input("Cobro Total ($)", min_value=0)
        
        st.markdown("---")
        st.subheader("Configuración de Agenda")
        col_f1, col_f2 = st.columns(2)
        fecha_ini = col_f1.date_input("¿Cuándo comienza?", datetime.now())
        hora_ini = col_f2.time_input("Hora del turno", datetime.now().time())
        
        dias_fijos = st.multiselect("Días fijos (para Planes)", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])
        
        if st.form_submit_button("CONSOLIDAR REGISTRO"):
            if not nombre or not dni:
                st.error("Datos incompletos.")
            else:
                # 1. Calcular cantidad
                cant = 10 if "X10" in serv else (5 if "X5" in serv else 1)
                
                # 2. Generar Fechas (Lógica Martes/Jueves etc)
                fechas_t = calcular_fechas_fijas(fecha_ini, dias_fijos, cant) if dias_fijos else [str(fecha_ini)]
                
                # 3. Guardar Paciente
                nuevo_p = pd.DataFrame([[dni, nombre, wpp, "", "Propia", serv, monto, str(fecha_ini), cant, cant]], columns=COL_PACIENTES)
                conn.update(worksheet="pacientes", data=pd.concat([df_p, nuevo_p], ignore_index=True))
                
                # 4. Guardar Agenda
                df_a = cargar_nube("agenda")
                nuevos_turnos = [[f, hora_ini.strftime("%H:%M"), nombre, serv, "PENDIENTE", wpp] for f in fechas_t]
                df_a_final = pd.concat([df_a, pd.DataFrame(nuevos_turnos, columns=COL_AGENDA)], ignore_index=True)
                conn.update(worksheet="agenda", data=df_a_final)
                
                st.balloons()
                st.success(f"¡Éxito! {len(nuevos_turnos)} turnos agendados y cobro registrado.")
                st.rerun()

# --- MÓDULO 3: FINANZAS ---
elif menu == "📊 Inteligencia Financiera":
    st.markdown('<p class="main-title">Métricas de Rendimiento</p>', unsafe_allow_html=True)
    df_f = cargar_nube("pacientes")
    
    if not df_f.empty:
        ingreso_total = df_f['Pago'].astype(float).sum()
        c1, c2, c3 = st.columns(3)
        c1.markdown(f'<div class="stat-box"><small>INGRESOS TOTALES</small><br><span style="font-size:24px; color:{BRAND_GREEN}; font-weight:bold;">${ingreso_total:,.0f}</span></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="stat-box"><small>PACIENTES ACTIVOS</small><br><span style="font-size:24px; font-weight:bold;">{len(df_f)}</span></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="stat-box"><small>PROMEDIO TICKET</small><br><span style="font-size:24px; font-weight:bold;">${ingreso_total/len(df_f):,.0f}</span></div>', unsafe_allow_html=True)
        
        st.subheader("Desglose Histórico")
        st.dataframe(df_f, use_container_width=True)
