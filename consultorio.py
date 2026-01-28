import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import urllib.parse

# --- CONFIGURACIÓN DE SEGURIDAD ---
st.set_page_config(page_title="Elite System V44", layout="wide", page_icon="🌿")

# Diccionario de precios plano para evitar errores de traducción
PRECIOS = {
    "Evaluacion": 36000, "Sesion Especializada": 36000, "Sesion Individual": 24000,
    "Plan x5": 110000, "Plan x10": 200000,
    "Masaje ZA Socio": 25000, "Masaje ZA Gral": 30000,
    "Masaje Completo Socio": 38000, "Masaje Completo Gral": 45000
}

# --- CONEXIÓN DE DATOS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        # Cargamos con ttl=0 para datos frescos
        p_df = conn.read(worksheet="pacientes", ttl="0").dropna(how='all')
        a_df = conn.read(worksheet="agenda", ttl="0").dropna(how='all')
        return p_df, a_df
    except Exception:
        return pd.DataFrame(), pd.DataFrame()

df_p, df_a = cargar_datos()

def guardar_seguro(df, nombre_hoja):
    """Evita errores de desajuste de columnas (image_14ce80.png)"""
    try:
        # Leemos el encabezado actual del Sheets para no corromperlo
        header = conn.read(worksheet=nombre_hoja, ttl="0").columns.tolist()
        # Alineamos nuestro DataFrame al orden del Sheets
        df_save = df.reindex(columns=header).fillna("")
        conn.update(worksheet=nombre_hoja, data=df_save)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Error al sincronizar: {e}")

# --- MOTOR DE SESIONES ---
def procesar_pasados():
    if df_a.empty: return
    ahora = datetime.now()
    hoy_f, hoy_h = ahora.strftime("%Y-%m-%d"), ahora.strftime("%H:%M")
    
    # Buscamos turnos que ya ocurrieron y no fueron procesados
    mask = (df_a['Fecha'].astype(str) <= hoy_f) & (df_a['Hora'].astype(str) < hoy_h) & (df_a.get('Estado','') != 'PROCESADO')
    
    if not df_a[mask].empty:
        p_new, a_new = df_p.copy(), df_a.copy()
        for idx, row in df_a[mask].iterrows():
            dni_val = str(row.get('DNI', ''))
            indices = p_new[p_new['DNI'].astype(str) == dni_val].index
            if not indices.empty:
                # Restamos 1 sesión de forma segura
                actual = pd.to_numeric(p_new.at[indices[0], 'Sesiones_Restantes'], errors='coerce')
                p_new.at[indices[0], 'Sesiones_Restantes'] = max(0, int(actual if pd.notnull(actual) else 0) - 1)
            a_new.at[idx, 'Estado'] = 'PROCESADO'
        guardar_seguro(p_new, "pacientes")
        guardar_seguro(a_new, "agenda")
        st.rerun()

# --- INTERFAZ PRINCIPAL ---
st.sidebar.title("ELITE MASTER V44")
opcion = st.sidebar.radio("Navegación", ["📅 Agenda", "📝 Registro & DX", "📊 Business"])
fijos = st.sidebar.number_input("Gastos Fijos", value=0)

if opcion == "📅 Agenda":
    procesar_pasados()
    st.title("Gestión de Turnos")
    t1, t2 = st.tabs(["Hoy", "Mañana"])
    
    def render_dia(fecha_str):
        turnos = df_a[df_a['Fecha'].astype(str) == fecha_str].sort_values("Hora")
        if turnos.empty: st.info("Día libre o sin turnos.")
        for i, r in turnos.iterrows():
            with st.container(border=True):
                # Buscamos DX y Saldo del paciente
                p_info = df_p[df_p['DNI'].astype(str) == str(r.get('DNI',''))]
                saldo = p_info['Sesiones_Restantes'].iloc[0] if not p_info.empty else 0
                dx_pac = p_info['DX'].iloc[0] if not p_info.empty and 'DX' in p_info.columns else "Sin DX"
                
                st.write(f"**{r['Hora']} hs** | {r['Paciente']} | Saldo: **{saldo}** | DX: *{dx_pac}*")
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Renovar Plan", key=f"ren_{i}"):
                        st.session_state.p_renov = r['Paciente']
                        st.info("Pasa a Registro")
                with c2:
                    msg = urllib.parse.quote(f"Hola {r['Paciente']}, te recordamos tu turno en Elite.")
                    st.markdown(f'<a href="https://wa.me/{r.get("WhatsApp","")}?text={msg}" target="_blank"><button style="width:100%; background:#25D366; color:white; border:none; padding:8px; border-radius:10px; cursor:pointer;">WhatsApp</button></a>', unsafe_allow_html=True)

    with t1: render_dia(datetime.now().strftime("%Y-%m-%d"))
    with t2: render_dia((datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"))

elif opcion == "📝 Registro & DX":
    st.title("Nueva Admisión")
    with st.form("registro_form"):
        c1, c2 = st.columns(2)
        nombre = c1.text_input("Nombre", value=st.session_state.get('p_renov', ''))
        dni_p = c1.text_input("DNI")
        tel_p = c1.text_input("WhatsApp")
        dx_p = c1.text_area("Diagnóstico (DX)")
        
        f_ini = c2.date_input("Inicia")
        h_ini = c2.time_input("Hora Turno")
        dias_p = c2.multiselect("Días", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])
        serv_p = st.selectbox("Servicio", list(PRECIOS.keys()))
        orig_p = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
        monto_p = st.number_input("Cobro ($)", value=float(PRECIOS[serv_p]))
        
        if st.form_submit_button("CONSOLIDAR"):
            if nombre and dni_p:
                cant_s = 10 if "x10" in serv_p else (5 if "x5" in serv_p else 1)
                # 1. Crear Paciente
                new_p = pd.DataFrame([{"DNI": dni_p, "Nombre": nombre, "WhatsApp": tel_p, "Origen": orig_p, "Servicio": serv_p, "Pago": monto_p, "Sesiones_Totales": cant_s, "Sesiones_Restantes": cant_s, "Fecha_Inicio": f_ini.strftime("%Y-%m-%d"), "DX": dx_p}])
                # 2. Generar Agenda
                d_m = {"Lunes":0, "Martes":1, "Miércoles":2, "Jueves":3, "Viernes":4, "Sábado":5}
                fs, actual = [], f_ini
                while len(fs) < cant_s:
                    if not dias_p or actual.weekday() in [d_m[d] for d in dias_p]: fs.append(actual.strftime("%Y-%m-%d"))
                    actual += timedelta(days=1)
                new_a = pd.DataFrame([{"Fecha": f, "Hora": h_ini.strftime("%H:%M"), "Paciente": nombre, "DNI": dni_p, "WhatsApp": tel_p, "Estado": "PENDIENTE", "Servicio": serv_p} for f in fs])
                
                guardar_seguro(pd.concat([df_p, new_p], ignore_index=True), "pacientes")
                guardar_seguro(pd.concat([df_a, new_a], ignore_index=True), "agenda")
                st.success("¡Plan Guardado!"); st.rerun()

elif opcion == "📊 Business":
    st.title("Auditoría Financiera")
    if not df_p.empty:
        # Cálculo manual sin Lambdas para evitar error image_f8365e.png
        ingreso_b = pd.to_numeric(df_p['Pago'], errors='coerce').sum()
        cesiones = 0.0
        for _, row in df_p.iterrows():
            p_val = float(row.get('Pago', 0))
            if row.get('Origen') == "Socio Gimnasio":
                cesiones += p_val * 0.30
            else:
                cesiones += p_val * 0.20
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Bruto", f"${ingreso_b:,.0f}")
        c2.metric("Cesión", f"-${cesiones:,.0f}")
        c3.metric("Neto", f"${ingreso_b - cesiones - fijos:,.0f}")
        st.dataframe(df_p, use_container_width=True)
