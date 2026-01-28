import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import urllib.parse

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Elite Master V46", layout="wide")

PRECIOS_REF = {
    "Evaluacion": 36000, "Sesion Individual": 24000,
    "Plan x5": 110000, "Plan x10": 200000,
    "Masaje Socio": 25000, "Masaje Gral": 30000
}

# --- CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

def traer_datos():
    try:
        p = conn.read(worksheet="pacientes", ttl="0").dropna(how='all')
        a = conn.read(worksheet="agenda", ttl="0").dropna(how='all')
        return p, a
    except:
        return pd.DataFrame(), pd.DataFrame()

df_p, df_a = traer_datos()

def subir_datos(df, nombre_hoja):
    try:
        # Alineación forzada para evitar el error de la imagen [image_14ce80.png]
        esquema = conn.read(worksheet=nombre_hoja, ttl="0").columns.tolist()
        df_para_subir = df.reindex(columns=esquema).fillna("")
        conn.update(worksheet=nombre_hoja, data=df_para_subir)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Fallo de conexión: {e}")

# --- PROCESO AUTOMÁTICO (SMART-SYNC) ---
def motor_sincronizacion():
    if df_a.empty: return
    ahora = datetime.now()
    hoy_f = ahora.strftime("%Y-%m-%d")
    hoy_h = ahora.strftime("%H:%M")
    
    # Filtro de sesiones que ya pasaron
    pasados = (df_a['Fecha'].astype(str) <= hoy_f) & (df_a['Hora'].astype(str) < hoy_h) & (df_a.get('Estado','') != 'PROCESADO')
    
    if not df_a[pasados].empty:
        p_temp, a_temp = df_p.copy(), df_a.copy()
        for i, fila in df_a[pasados].iterrows():
            dni_buscado = str(fila.get('DNI', ''))
            idx_paciente = p_temp[p_temp['DNI'].astype(str) == dni_buscado].index
            if not idx_paciente.empty:
                # Descuento de saldo
                actual = pd.to_numeric(p_temp.at[idx_paciente[0], 'Sesiones_Restantes'], errors='coerce')
                p_temp.at[idx_paciente[0], 'Sesiones_Restantes'] = max(0, int(actual if pd.notnull(actual) else 0) - 1)
            a_temp.at[i, 'Estado'] = 'PROCESADO'
        subir_datos(p_temp, "pacientes")
        subir_datos(a_temp, "agenda")
        st.rerun()

# --- INTERFAZ ---
menu = st.sidebar.radio("SISTEMA", ["📅 Agenda", "📝 Admisión (DX)", "📊 Auditoría"])
gastos_fijos = st.sidebar.number_input("Gastos Fijos Mensuales", value=0)

if menu == "📅 Agenda":
    motor_sincronizacion()
    st.title("Agenda Operativa")
    t1, t2 = st.tabs(["Turnos de Hoy", "Mañana"])
    
    def render_lista(fec):
        hoy = df_a[df_a['Fecha'].astype(str) == fec].sort_values("Hora")
        if hoy.empty: st.info("No hay turnos registrados.")
        for idx, r in hoy.iterrows():
            with st.container(border=True):
                p_datos = df_p[df_p['DNI'].astype(str) == str(r.get('DNI',''))]
                saldo = p_datos['Sesiones_Restantes'].iloc[0] if not p_datos.empty else 0
                dx_pac = p_datos['DX'].iloc[0] if not p_datos.empty and 'DX' in p_datos.columns else "Sin diagnóstico"
                
                st.write(f"**{r['Hora']}** | {r['Paciente']} | Saldo: **{saldo}** | DX: *{dx_pac}*")
                
                if st.button("🔄 Renovar", key=f"btn_{idx}"):
                    st.session_state.pac_renovar = r['Paciente']
                    st.info("Pasa a la pestaña de Admisión")
                
                txt_wa = urllib.parse.quote(f"Hola {r['Paciente']}, recordatorio de turno en Elite.")
                st.markdown(f'<a href="https://wa.me/{r.get("WhatsApp","")}?text={txt_wa}" target="_blank"><button style="width:100%; background:#25D366; color:white; border:none; padding:8px; border-radius:5px;">WhatsApp</button></a>', unsafe_allow_html=True)

    with t1: render_lista(datetime.now().strftime("%Y-%m-%d"))
    with t2: render_lista((datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"))

elif menu == "📝 Admisión (DX)":
    st.title("Registro de Pacientes y Planes")
    with st.form("form_alta"):
        c1, c2 = st.columns(2)
        nom = c1.text_input("Nombre Completo", value=st.session_state.get('pac_renovar', ''))
        id_p = c1.text_input("DNI / Cédula")
        cel = c1.text_input("WhatsApp")
        dx_val = c1.text_area("Diagnóstico (DX)")
        
        inicio = c2.date_input("Fecha de Inicio")
        hora = c2.time_input("Hora del Turno")
        dias = c2.multiselect("Días de Sesión", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])
        serv = st.selectbox("Plan/Servicio", list(PRECIOS_REF.keys()))
        ori = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
        pago = st.number_input("Precio Cobrado", value=float(PRECIOS_REF[serv]))
        
        if st.form_submit_button("CONSOLIDAR REGISTRO"):
            if nom and id_p:
                cant_s = 10 if "x10" in serv else (5 if "x5" in serv else 1)
                # 1. Tabla Pacientes
                fila_p = pd.DataFrame([{"DNI": id_p, "Nombre": nom, "WhatsApp": cel, "Origen": ori, "Servicio": serv, "Pago": pago, "Sesiones_Totales": cant_s, "Sesiones_Restantes": cant_s, "Fecha_Inicio": inicio.strftime("%Y-%m-%d"), "DX": dx_val}])
                # 2. Tabla Agenda
                mapa_d = {"Lunes":0, "Martes":1, "Miércoles":2, "Jueves":3, "Viernes":4, "Sábado":5}
                fec_list, actual = [], inicio
                while len(fec_list) < cant_s:
                    if not dias or actual.weekday() in [mapa_d[d] for d in dias]:
                        fec_list.append(actual.strftime("%Y-%m-%d"))
                    actual += timedelta(days=1)
                filas_a = pd.DataFrame([{"Fecha": f, "Hora": hora.strftime("%H:%M"), "Paciente": nom, "DNI": id_p, "WhatsApp": cel, "Estado": "PENDIENTE", "Servicio": serv} for f in fec_list])
                
                subir_datos(pd.concat([df_p, fila_p], ignore_index=True), "pacientes")
                subir_datos(pd.concat([df_a, filas_a], ignore_index=True), "agenda")
                st.success("¡Plan registrado con éxito!")
                if 'pac_renovar' in st.session_state: del st.session_state.pac_renovar
                st.rerun()

elif menu == "📊 Auditoría":
    st.title("Métricas de Rentabilidad")
    if not df_p.empty:
        ingreso_bruto = pd.to_numeric(df_p['Pago'], errors='coerce').sum()
        total_cesion = 0.0
        for i, f in df_p.iterrows():
            monto = float(f.get('Pago', 0))
            if f.get('Origen') == "Socio Gimnasio":
                total_cesion += monto * 0.30
            else:
                total_cesion += monto * 0.20
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Ingresos Brutos", f"${ingreso_bruto:,.0f}")
        c2.metric("Cesiones Totales", f"-${total_cesion:,.0f}")
        c3.metric("Utilidad Final", f"${ingreso_bruto - total_cesion - gastos_fijos:,.0f}")
        st.dataframe(df_p, use_container_width=True)
