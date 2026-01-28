import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# Configuración de página - Debe ser la PRIMERA línea de código
st.set_page_config(page_title="Elite Master V53", layout="wide")

st.title("🌿 Sistema Elite - Conexión Estable")

try:
    # Conexión simplificada
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Menú lateral para probar que la app responde
    menu = st.sidebar.selectbox("Acciones", ["Estado de Conexión", "Ver Datos"])

    if menu == "Estado de Conexión":
        st.success("✅ La aplicación está corriendo correctamente.")
        st.write("Si ves este mensaje, el error de instalación se ha solucionado.")
        st.info("Ahora falta verificar si tus Secrets de Google Sheets están configurados.")

    elif menu == "Ver Datos":
        st.subheader("Datos de la Planilla")
        # Leemos solo si el usuario lo pide para evitar errores al cargar
        df = conn.read(worksheet="pacientes", ttl=0)
        st.dataframe(df)

except Exception as e:
    st.error("Error de configuración detectado")
    st.write("Asegúrate de haber pegado los 'Secrets' en Streamlit Cloud.")
    st.info(f"Detalle técnico: {e}")
