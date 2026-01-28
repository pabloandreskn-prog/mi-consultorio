import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# Forzamos una configuración limpia
st.set_page_config(page_title="Elite Master V52", layout="wide")

# Conector
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        # Cargamos los datos. Asegúrate de tener las hojas 'pacientes' y 'agenda'
        p = conn.read(worksheet="pacientes", ttl=0)
        a = conn.read(worksheet="agenda", ttl=0)
        return p, a
    except Exception as e:
        st.error(f"Error de base de datos: {e}")
        return pd.DataFrame(), pd.DataFrame()

# Título
st.title("🚀 Sistema Elite - Conectado")

df_p, df_a = get_data()

# Menú lateral
sel = st.sidebar.selectbox("Acción", ["Revisar Agenda", "Cargar Paciente"])

if sel == "Revisar Agenda":
    if not df_a.empty:
        st.write("### Turnos Actuales")
        st.dataframe(df_a)
    else:
        st.info("La agenda está vacía o no se encuentra la hoja.")

elif sel == "Cargar Paciente":
    with st.form("registro"):
        st.write("### Nueva Admisión")
        nom = st.text_input("Nombre Completo")
        dni = st.text_input("DNI")
        dx = st.text_area("Diagnóstico (DX)")
        if st.form_submit_button("Guardar"):
            st.success(f"Datos recibidos para: {nom}")
            st.info("Presione 'Revisar Agenda' para actualizar.")
