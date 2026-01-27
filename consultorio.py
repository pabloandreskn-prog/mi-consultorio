import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import urllib.parse
import re

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Elite System Ultra V6", layout="wide", page_icon="🌿")
BRAND_GREEN = "#60b067"

# Catálogo completo de servicios solicitado
SERVICIOS_DISPONIBLES = [
    "Evaluacion", "Sesion Especializada", "Sesion Individual", 
    "Plan x5", "Plan x10", "Masaje ZA (piernas y pies)", 
    "Masaje ZB (Espalda y Cabeza)", "Masaje Completo"
]

# --- 2. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_nube(pestana):
    return conn.read(worksheet=pestana, ttl="0").dropna(how='all')

COL_PACIENTES = ["DNI", "Nombre", "Contacto", "Dx", "Origen", "Servicio", "Pago", "Fecha", "Sesiones_Totales", "Sesiones_Restantes"]
COL_AGENDA = ["Fecha", "Hora", "Paciente", "Servicio", "Estado", "Contacto"]

# --- 3. FUNCIONES DE INTELIGENCIA ---
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

# --- 4. INTERFAZ ---
with st.sidebar:
    st.markdown('<h1 style="color:#60b067;">🌿 ELITE SYSTEM</h1>', unsafe_allow_html=True)
    menu = st.radio("NAVEGACIÓN", ["📅 Agenda & Turnos", "📝 Registro & Cobro", "📊 Inteligencia Financiera"])

# --- MÓDULO REGISTRO (CON LOGICA DE BENEFICIOS) ---
if menu == "📝 Registro & Cobro":
    st.markdown('<p style="color:#60b067; font-size:32px; font-weight:bold;">Registro & Beneficios</p>', unsafe_allow_html=True)
    df_p = cargar_nube("pacientes")
    
    with st.form("form_alta", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre del Paciente")
            dni = st.text_input("DNI")
            wpp = st.text_input("WhatsApp (ej. 549341...)")
            dx = st.text_area("Diagnóstico (Dx)")
        
        with col2:
            origen = st.selectbox("Categoría de Paciente", ["Socio Gimnasio", "Captación Propia", "Convenio"])
            serv = st.selectbox("Servicio / Plan", SERVICIOS_DISPONIBLES)
            monto_base = st.number_input("Precio de Lista ($)", min_value=0)
            
            # Inteligencia de Beneficio de Evaluación
            es_evaluacion = (serv == "Evaluacion")
            ya_evaluado = not df_p[(df_p['DNI'].astype(str) == str(dni)) & (df_p['Servicio'] == "Evaluacion")].empty
            
            aplicar_beneficio = False
            if es_evaluacion:
                if ya_evaluado:
                    st.warning("⚠️ Este paciente ya posee una evaluación previa. No aplica bonificación.")
                else:
                    aplicar_beneficio = st.checkbox("Aplicar Beneficio de Primera Evaluación", value=True)
            
            # Cálculo de monto final
            monto_final = monto_base
            if aplicar_beneficio:
                if origen == "Socio Gimnasio":
                    monto_final = 0 # 100% Bonificado
                    st.success("✅ Beneficio Socio: 100% Bonificado")
                else:
                    monto_final = monto_base * 0.50 # 50% Bonificado
                    st.info("✅ Beneficio Externo: 50% Bonificado")
            
            st.metric("Total a Cobrar", f"${monto_final:,.0f}")

        st.markdown("---")
        st.subheader("📅 Configuración de Turnos")
        c_f1, c_f2 = st.columns(2)
        fecha_ini = c_f1.date_input("Fecha", datetime.now())
        hora_sel = c_f2.time_input("Hora", datetime.now().time())
        hora_str = hora_sel.strftime("%H:%M")
        dias_fijos = st.multiselect("Días fijos (solo para Planes)", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])
        
        if st.form_submit_button("CONSOLIDAR REGISTRO"):
            if not nombre or not dni:
                st.error("Nombre y DNI son obligatorios.")
            else:
                cant = 10 if "x10" in serv else (5 if "x5" in serv else 1)
                fechas_t = calcular_fechas_fijas(fecha_ini, dias_fijos, cant) if (dias_fijos and cant > 1) else [str(fecha_ini)]
                
                # Guardar Paciente con el monto FINAL calculado
                nuevo_p = pd.DataFrame([[dni, nombre, wpp, dx, origen, serv, monto_final, str(fecha_ini), cant, cant]], columns=COL_PACIENTES)
                conn.update(worksheet="pacientes", data=pd.concat([df_p, nuevo_p], ignore_index=True))
                
                # Guardar Agenda
                df_a = cargar_nube("agenda")
                nuevos_turnos = [[f, hora_str, nombre, serv, "PENDIENTE", wpp] for f in fechas_t]
                df_a_final = pd.concat([df_a, pd.DataFrame(nuevos_turnos, columns=COL_AGENDA)], ignore_index=True)
                conn.update(worksheet="agenda", data=df_a_final)
                
                st.balloons()
                st.success(f"¡Registrado! Cobro final: ${monto_final}")
                st.rerun()

# --- MÓDULO FINANZAS (CON IMPACTO DE BENEFICIOS) ---
elif menu == "📊 Inteligencia Financiera":
    st.markdown('<p style="color:#60b067; font-size:32px; font-weight:bold;">Análisis Financiero & Beneficios</p>', unsafe_allow_html=True)
    df_f = cargar_nube("pacientes")
    
    if not df_f.empty:
        # Cálculo de comisiones (20% propio / 30% socio) - Mantenemos tu estructura base
        def calcular_comision(row):
            pago = float(row['Pago'])
            if row['Origen'] == "Socio Gimnasio": return pago * 0.30
            return pago * 0.20
        
        df_f['Comision'] = df_f.apply(calcular_comision, axis=1)
        df_f['Neto'] = df_f['Pago'].astype(float) - df_f['Comision']
        
        # Métricas principales
        c1, c2, c3 = st.columns(3)
        c1.metric("Ingresos Reales", f"${df_f['Pago'].astype(float).sum():,.0f}")
        c2.metric("Comisiones Cedidas", f"-${df_f['Comision'].sum():,.0f}")
        c3.metric("Utilidad Elite", f"${df_f['Neto'].sum():,.0f}")
        
        st.subheader("Historial de Pacientes y Sesiones")
        st.dataframe(df_f, use_container_width=True)

# --- MÓDULO AGENDA (ESTRUCTURA V5) ---
elif menu == "📅 Agenda & Turnos":
    st.markdown('<p style="color:#60b067; font-size:32px; font-weight:bold;">Agenda</p>', unsafe_allow_html=True)
    df_a = cargar_nube("agenda")
    hoy = datetime.now().date()
    t_hoy = df_a[df_a['Fecha'].astype(str) == str(hoy)]
    for _, t in t_hoy.sort_values("Hora").iterrows():
        st.markdown(f'<div style="background:white; padding:15px; border-radius:10px; border-left:5px solid #60b067; margin-bottom:10px;"><b>{t["Hora"]} hs</b> | {t["Paciente"]} - {t["Servicio"]}</div>', unsafe_allow_html=True)
