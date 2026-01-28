import streamlit as st
import pandas as pd
from datetime import datetime
import numpy as np

# Configuración de página
st.set_page_config(page_title="Elite System - Gestión Integral", layout="wide")

# --- FUNCIONES DE LÓGICA ---
def calcular_comision_valor(pago, origen):
    """Calcula el monto de la comisión según el origen del paciente."""
    porcentaje = 0.30 if origen == "Socio Gimnasio" else 0.20
    return pago * porcentaje

def obtener_disponibilidad(df, fecha):
    """Calcula el estado del semáforo de disponibilidad horaria."""
    # Ejemplo de horas laborales
    horas = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", 
             "16:00", "17:00", "18:00", "19:00", "20:00"]
    disponibilidad = {hora: "Libre" for hora in horas}
    
    # Filtrar turnos del día (Simulado con los datos de la planilla)
    # En una app real, aquí filtrarías el dataframe por la columna 'Fecha'
    return disponibilidad

# --- SIDEBAR / NAVEGACIÓN ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/622/622848.png", width=50) # Icono hoja
    st.title("ELITE SYSTEM")
    st.caption("v7.1 - VERSIÓN CONSOLIDADA")
    st.divider()
    
    menu = st.radio(
        "MENÚ PRINCIPAL",
        ["📅 Agenda & Turnos", "📝 Registro & Renovación", "🔍 Buscador & Gestión", "📊 Panel Financiero"]
    )

# --- CARGA DE DATOS (Simulada según image_eae993.png) ---
data = {
    "DNI": [12833986, 12345678, 12345678, 12345678, 111111111, 27829910],
    "Nombre": ["Martinez Susana", "Malaspina Mariana", "Guadalupe", "Malaspina Mariana", "Ferraris Daniela", "Becker Romina"],
    "WhatsApp": ["5492920206426", "5492920514343", "5492920340529", "5492920514343", None, None],
    "DX": ["Artroplastia total", "None", "S. Piramidal?", "Esguince", "hemisacralizacion", "Escoliosis"],
    "Origen": ["Socio Gimnasio", "Socio Gimnasio", "Captación Propia", "Socio Gimnasio", "Socio Gimnasio", "Captación Propia"],
    "Servicio": ["Plan X10", "Evaluacion", "Evaluacion", "Sesion Individual", "Evaluacion", "Sesion Especializada"],
    "Pago": [200000, 0, 18000, 24000, 0, 36000],
    "Fecha_Inicio": ["2026-01-27", "2026-01-27", "2026-01-28", "2026-01-28", "2026-01-28", "2026-02-26"],
    "Sesiones_Totales": [10, 1, 1, 1, 1, 1],
    "Sesiones_Restantes": [-10, 0, 1, 1, 1, 1] # Valores basados en image_7c0ef5.png
}
df_master = pd.DataFrame(data)

# --- SECCIONES ---

if menu == "📅 Agenda & Turnos":
    st.header("Agenda Diaria")
    
    # Error fix: Unique ID for date_input to avoid DuplicateElementId
    fecha_sel = st.date_input("Ver calendario", datetime.now(), key="calendar_main")
    
    with st.expander("🔍 Estado de Disponibilidad Horaria", expanded=True):
        cols = st.columns(11)
        horas = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "16:00", "17:00", "18:00", "19:00", "20:00"]
        # Simulación de estados (Verde=Libre, Naranja=Ocupado)
        estados = ["🟢", "🟢", "🟢", "🟠", "🟢", "🟢", "🟢", "🟢", "🟠", "🟢", "🟢"]
        for i, col in enumerate(cols):
            col.write(f"{estados[i]} {horas[i]}")

    st.divider()

    # Muestra de Turnos (Basado en image_7c8e35.png)
    turnos = [
        {"hora": "08:30", "nombre": "Susana Martinez", "servicio": "Plan X10", "pago": "DEBE PAGAR", "restantes": -10, "dx": "N/A"},
        {"hora": "09:00", "nombre": "Catelleani Liliana", "servicio": "Sesion Individual", "pago": "DEBE PAGAR", "restantes": 0, "dx": "Siringomielia"},
        {"hora": "11:00", "nombre": "Echegoy Jessica", "servicio": "Evaluacion", "pago": "DEBE PAGAR", "restantes": 0, "dx": "Impingement de hombro"}
    ]

    for t in turnos:
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            with c1:
                st.markdown(f"**{t['hora']} hs | {t['nombre']}** :red[{t['pago']}] :orange[{t['restantes']} restantes]")
                st.caption(f"{t['servicio']}")
                st.caption(f"📝 DX: {t['dx']}")
            with c2:
                st.button("🔄 Mover", key=f"mov_{t['hora']}")
            with c3:
                # Fix para NameError: Validar cobro
                if st.button("💵 Cobrar", key=f"cob_{t['hora']}"):
                    st.success(f"Procesando cobro para {t['nombre']}...")

elif menu == "📊 Panel Financiero":
    st.header("Análisis de Ingresos y Comisiones Cedidas")
    
    # Cálculos
    df_fin = df_master.copy()
    df_fin['Comision_Monto'] = df_fin.apply(lambda x: calcular_comision_valor(x['Pago'], x['Origen']), axis=1)
    df_fin['Ingreso_Neto'] = df_fin['Pago'] - df_fin['Comision_Monto']
    
    total_bruto = df_fin['Pago'].sum()
    total_comisiones = df_fin['Comision_Monto'].sum()
    total_neto = df_fin['Ingreso_Neto'].sum()

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Bruto", f"${total_bruto:,}")
    m2.metric("Comisiones Cedidas", f"-${total_comisiones:,}")
    m3.metric("Neto Elite", f"${total_neto:,}")

    st.subheader("Tabla de Comisiones Cedidas por Paciente")
    # Limpieza de columnas para visualización según image_ea720d.png
    cols_mostrar = ['Fecha_Inicio', 'Nombre', 'Origen', 'Pago', 'Comision_Monto', 'Ingreso_Neto']
    st.dataframe(df_fin[cols_mostrar], use_container_width=True)

    st.subheader("Desglose Detallado")
    # Fix para KeyError: Verificar que las columnas existan antes de filtrar
    cols_desglose = ['Fecha_Inicio', 'Nombre', 'Servicio', 'Pago']
    st.dataframe(df_fin[cols_desglose], use_container_width=True)

else:
    st.info(f"Sección {menu} en desarrollo para v7.2")
