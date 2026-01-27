import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import plotly.express as px

# --- 1. CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="Elite System Ultra V8", layout="wide", page_icon="🌿")

BRAND_GREEN = "#60b067"
LIGHT_GREEN = "#90ee90"

st.markdown(f"""
    <style>
    .stApp {{ background-color: #FFFFFF; color: #1E1E1E; }}
    .main-title {{ color: {BRAND_GREEN}; font-size: 32px; font-weight: bold; }}
    .turno-card {{
        background: rgba(30, 30, 30, 0.9);
        backdrop-filter: blur(10px);
        border-left: 6px solid {BRAND_GREEN};
        padding: 20px; border-radius: 15px; margin-bottom: 15px; color: white;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.1);
    }}
    .alerta-renovacion {{
        background-color: {LIGHT_GREEN}; color: #1a5c1a; padding: 6px 12px;
        border-radius: 8px; font-weight: bold; display: inline-block; margin-top: 10px; font-size: 12px;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_nube(pestana):
    return conn.read(worksheet=pestana, ttl="0").dropna(how='all')

SERVICIOS_DISPONIBLES = [
    "Evaluacion", "Sesion Especializada", "Sesion Individual", 
    "Plan x5", "Plan x10", "Masaje ZA (piernas y pies)", 
    "Masaje ZB (Espalda y Cabeza)", "Masaje Completo"
]

COL_PACIENTES = ["DNI", "Nombre", "Contacto", "Dx", "Origen", "Servicio", "Pago", "Fecha", "Sesiones_Totales", "Sesiones_Restantes"]
COL_AGENDA = ["Fecha", "Hora", "Paciente", "Servicio", "Estado", "Contacto"]

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

# --- 4. NAVEGACIÓN ---
with st.sidebar:
    st.markdown(f'<h1 style="color:{BRAND_GREEN};">🌿 ELITE SYSTEM</h1>', unsafe_allow_html=True)
    menu = st.radio("MENÚ", ["📅 Agenda & Turnos", "📝 Registro & Cobro", "📊 Inteligencia Financiera"])

# --- MÓDULO: REGISTRO & COBRO (CORREGIDO) ---
if menu == "📝 Registro & Cobro":
    st.markdown('<p class="main-title">Registro de Paciente & Venta</p>', unsafe_allow_html=True)
    df_p = cargar_nube("pacientes")
    hoy = datetime.now().date()
    
    # FORMULARIO UNIFICADO (Para evitar error de Missing Submit Button)
    with st.form("registro_total_v8"):
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Nombre Completo")
            dni = st.text_input("DNI (Sin puntos)")
            contacto = st.text_input("WhatsApp (Ej: 549...)")
            dx = st.text_area("Diagnóstico (Dx)")
        
        with c2:
            origen = st.selectbox("Origen del Paciente", ["Socio Gimnasio", "Captación Propia", "Convenio"])
            serv = st.selectbox("Servicio / Plan", SERVICIOS_DISPONIBLES)
            monto_lista = st.number_input("Precio de Lista ($)", min_value=0)
            
            # LÓGICA DE BONIFICACIÓN ÚNICA
            pago_final = monto_lista
            if serv == "Evaluacion" and dni:
                # Verificar si ya existe una evaluación para ese DNI
                ya_fue_evaluado = not df_p[(df_p['DNI'].astype(str) == str(dni)) & (df_p['Servicio'] == "Evaluacion")].empty
                if ya_fue_evaluado:
                    st.warning("⚠️ Paciente ya evaluado previamente. Se aplica tarifa normal.")
                else:
                    if origen == "Socio Gimnasio":
                        pago_final = 0
                        st.success("🎁 Bonificación 100% aplicada (Socio Primera Vez)")
                    else:
                        pago_final = monto_lista * 0.5
                        st.success("🎁 Bonificación 50% aplicada (Primera Evaluación)")
            
            st.write(f"### Total a cobrar: **${pago_final:,.0f}**")

        st.markdown("---")
        st.subheader("📅 Programación de Turnos")
        f_col, h_col = st.columns(2)
        fecha_inicio = f_col.date_input("Día de Inicio", hoy)
        hora_turno = h_col.time_input("Hora", datetime.now().time())
        dias_plan = st.multiselect("Días Fijos (Si es Plan)", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])
        
        submit = st.form_submit_button("✅ CONSOLIDAR REGISTRO Y AGENDAR")
        
        if submit:
            if not nombre or not dni:
                st.error("Por favor completa Nombre y DNI.")
            else:
                # 1. Calcular Sesiones
                cant = 10 if "x10" in serv else (5 if "x5" in serv else 1)
                fechas = calcular_fechas_fijas(fecha_inicio, dias_plan, cant) if dias_plan else [str(fecha_inicio)]
                
                # 2. Guardar en Pacientes
                nuevo_paciente = pd.DataFrame([[dni, nombre, contacto, dx, origen, serv, pago_final, str(fecha_inicio), cant, cant]], columns=COL_PACIENTES)
                conn.update(worksheet="pacientes", data=pd.concat([df_p, nuevo_paciente], ignore_index=True))
                
                # 3. Guardar en Agenda
                df_a = cargar_nube("agenda")
                h_str = hora_turno.strftime("%H:%M")
                nuevos_turnos = [[f, h_str, nombre, serv, "PENDIENTE", contacto] for f in fechas]
                conn.update(worksheet="agenda", data=pd.concat([df_a, pd.DataFrame(nuevos_turnos, columns=COL_AGENDA)], ignore_index=True))
                
                st.balloons()
                st.success(f"¡Éxito! {len(nuevos_turnos)} sesiones agendadas.")
                st.rerun()

# --- MÓDULO: INTELIGENCIA FINANCIERA (RESTAURADO) ---
elif menu == "📊 Inteligencia Financiera":
    st.markdown('<p class="main-title">Análisis de Impacto Financiero</p>', unsafe_allow_html=True)
    df_f = cargar_nube("pacientes")
    
    if not df_f.empty:
        df_f['Pago'] = pd.to_numeric(df_f['Pago'], errors='coerce').fillna(0)
        
        # Métricas de Beneficio
        total_real = df_f['Pago'].sum()
        evaluaciones = df_f[df_f['Servicio'] == "Evaluacion"]
        ahorro_pacientes = (evaluaciones.shape[0] * 18000) - evaluaciones['Pago'].sum() # Estimando base 18k
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Ingresos Totales", f"${total_real:,.0f}")
        c2.metric("Inversión en Bonos", f"${ahorro_pacientes:,.0f}", help="Dinero no cobrado por beneficios")
        c3.metric("Pacientes Activos", len(df_f['DNI'].unique()))
        
        st.subheader("Distribución de Servicios")
        fig = px.pie(df_f, names='Servicio', values='Pago', color_discrete_sequence=px.colors.sequential.Greens_r)
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Base de Datos Histórica")
        st.dataframe(df_f, use_container_width=True)

# --- MÓDULO: AGENDA ---
elif menu == "📅 Agenda & Turnos":
    st.markdown('<p class="main-title">Gestión de Turnos</p>', unsafe_allow_html=True)
    df_a = cargar_nube("agenda")
    df_p = cargar_nube("pacientes")
    hoy = str(datetime.now().date())
    
    t_hoy = df_a[df_a['Fecha'].astype(str) == hoy].sort_values("Hora")
    
    if t_hoy.empty:
        st.info("No hay turnos para hoy.")
    else:
        for _, t in t_hoy.iterrows():
            info_p = df_p[df_p['Nombre'] == t['Paciente']]
            rest = pd.to_numeric(info_p['Sesiones_Restantes'].iloc[-1], errors='coerce') if not info_p.empty else 10
            
            st.markdown(f"""
            <div class="turno-card">
                <span style="color:{BRAND_GREEN}; font-size:22px; font-weight:bold;">{t['Hora']} hs</span> | {t['Paciente']}<br>
                <b>{t['Servicio']}</b><br>
                {"<div class='alerta-renovacion'>♻️ RENOVAR O FINALIZAR TRATAMIENTO</div>" if rest <= 1 else ""}
            </div>
            """, unsafe_allow_html=True)
