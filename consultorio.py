import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import urllib.parse

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Elite System V37", layout="wide", page_icon="🌿")

PRECIOS_BASE = {
    "Evaluacion": 36000, "Sesion Especializada": 36000, "Sesion Individual": 24000,
    "Plan x5": 110000, "Plan x10": 200000,
    "Masaje ZA": {"Socio": 25000, "Gral": 30000},
    "Masaje ZB": {"Socio": 25000, "Gral": 30000},
    "Masaje Completo": {"Socio": 38000, "Gral": 45000}
}

# --- 2. CONEXIÓN BLINDADA ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        df_p = conn.read(worksheet="pacientes", ttl="0").dropna(how='all')
        df_a = conn.read(worksheet="agenda", ttl="0").dropna(how='all')
        
        # Asegurar tipos numéricos para cálculos
        for col in ['Pago', 'Sesiones_Restantes', 'Sesiones_Totales']:
            if col in df_p.columns:
                df_p[col] = pd.to_numeric(df_p[col], errors='coerce').fillna(0)
        
        # Asegurar columnas necesarias
        if 'Fecha_Inicio' not in df_p.columns: df_p['Fecha_Inicio'] = datetime.now().strftime("%Y-%m-%d")
        if 'Estado' not in df_a.columns: df_a['Estado'] = 'PENDIENTE'
        
        return df_p, df_a
    except Exception:
        st.error("Error de conexión. Verifica que las pestañas se llamen 'pacientes' y 'agenda'.")
        return pd.DataFrame(), pd.DataFrame()

df_p, df_a = cargar_datos()

def guardar_datos(df, hoja):
    """Sincroniza el DataFrame con Google Sheets alineando columnas automáticamente"""
    try:
        df_actual = conn.read(worksheet=hoja, ttl="0")
        columnas_destino = df_actual.columns.tolist()
        # Solo enviamos las columnas que el Excel espera recibir
        df_para_subir = df.reindex(columns=columnas_destino).fillna("")
        conn.update(worksheet=hoja, data=df_para_subir)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Error al guardar: {e}")

# --- 3. MOTOR SMART-SYNC ---
def smart_sync():
    if df_a.empty: return
    ahora = datetime.now()
    fecha_h = ahora.strftime("%Y-%m-%d")
    hora_h = ahora.strftime("%H:%M")
    
    # Identificar sesiones pasadas no procesadas
    mask = (df_a['Fecha'].astype(str) <= fecha_h) & (df_a['Hora'].astype(str) < hora_h) & (df_a['Estado'] != 'PROCESADO')
    
    if not df_a[mask].empty:
        df_p_n, df_a_n = df_p.copy(), df_a.copy()
        for idx, t in df_a[mask].iterrows():
            dni = str(t.get('DNI', ''))
            idx_p = df_p_n[df_p_n['DNI'].astype(str) == dni].index
            if not idx_p.empty:
                df_p_n.at[idx_p[0], 'Sesiones_Restantes'] = max(0, df_p_n.at[idx_p[0], 'Sesiones_Restantes'] - 1)
            df_a_n.at[idx, 'Estado'] = 'PROCESADO'
        guardar_datos(df_p_n, "pacientes")
        guardar_datos(df_a_n, "agenda")
        st.rerun()

# --- 4. INTERFAZ ---
menu = st.sidebar.radio("MENÚ ÉLITE", ["📅 Agenda", "📝 Registro", "📊 Finanzas"])
gastos_f = st.sidebar.number_input("Gastos Fijos Mensuales ($)", value=0)

if menu == "📅 Agenda":
    smart_sync()
    st.title("Control de Turnos")
    t1, t2 = st.tabs(["Hoy", "Mañana"])

    def mostrar_agenda(f):
        hoy = df_a[df_a['Fecha'].astype(str) == f].sort_values("Hora")
        if hoy.empty: st.info("Sin turnos programados.")
        for i, r in hoy.iterrows():
            with st.container(border=True):
                p_data = df_p[df_p['DNI'].astype(str) == str(r['DNI'])]
                saldo = int(p_data['Sesiones_Restantes'].iloc[0]) if not p_data.empty else 0
                st.write(f"**{r['Hora']} hs** | {r['Paciente']} | Saldo: **{saldo}**")
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    with st.popover("⚙️ Cambiar"):
                        nueva_f = st.date_input("Fecha", key=f"f_{i}")
                        nueva_h = st.time_input("Hora", key=f"h_{i}")
                        if st.button("Guardar", key=f"b_{i}"):
                            df_a.at[i, 'Fecha'] = nueva_f.strftime("%Y-%m-%d")
                            df_a.at[i, 'Hora'] = nueva_h.strftime("%H:%M")
                            guardar_datos(df_a, "agenda")
                            st.rerun()
                with c2:
                    if st.button("🛒 Renovar", key=f"ren_{i}"):
                        st.session_state.p_renovar = r['Paciente']
                        st.info("Carga el nuevo plan en Registro.")
                with c3:
                    msg = urllib.parse.quote(f"Hola {r['Paciente']}, recordatorio de turno.")
                    st.markdown(f'<a href="https://wa.me/{r.get("WhatsApp","")}?text={msg}" target="_blank"><button style="width:100%; background:#25D366; color:white; border:none; padding:5px; border-radius:5px; cursor:pointer;">WhatsApp</button></a>', unsafe_allow_html=True)

    with t1: mostrar_agenda(datetime.now().strftime("%Y-%m-%d"))
    with t2: mostrar_agenda((datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"))

elif menu == "📝 Registro":
    st.title("Registro de Pacientes y Planes")
    with st.form("form_registro", clear_on_submit=True):
        c1, c2 = st.columns(2)
        nom = c1.text_input("Nombre", value=st.session_state.get('p_renovar', ''))
        dni = c1.text_input("DNI")
        tel = c1.text_input("WhatsApp")
        f_i = c2.date_input("Fecha Inicio")
        h_i = c2.time_input("Hora")
        dias = c2.multiselect("Días", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])
        serv = st.selectbox("Servicio", list(PRECIOS_BASE.keys()))
        orig = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
        
        p_base = PRECIOS_BASE[serv]["Socio" if orig=="Socio Gimnasio" else "Gral"] if "Masaje" in serv else PRECIOS_BASE[serv]
        pago = st.number_input("Precio Final ($)", value=float(p_base))
        
        if st.form_submit_button("GRABAR Y AGENDAR"):
            if nom and dni:
                cant = 10 if "x10" in serv else (5 if "x5" in serv else 1)
                # 1. Crear Paciente
                np = pd.DataFrame([{"DNI": dni, "Nombre": nom, "WhatsApp": tel, "Origen": orig, "Servicio": serv, "Pago": pago, "Sesiones_Totales": cant, "Sesiones_Restantes": cant, "Fecha_Inicio": f_i.strftime("%Y-%m-%d")}])
                # 2. Crear Agenda Masiva
                d_map = {"Lunes":0, "Martes":1, "Miércoles":2, "Jueves":3, "Viernes":4, "Sábado":5}
                fechas, curr = [], f_i
                while len(fechas) < cant:
                    if not dias or curr.weekday() in [d_map[d] for d in dias]: fechas.append(curr.strftime("%Y-%m-%d"))
                    curr += timedelta(days=1)
                na = pd.DataFrame([{"Fecha": f, "Hora": h_i.strftime("%H:%M"), "Paciente": nom, "DNI": dni, "WhatsApp": tel, "Estado": "PENDIENTE", "Servicio": serv} for f in fechas])
                
                guardar_datos(pd.concat([df_p, np], ignore_index=True), "pacientes")
                guardar_datos(pd.concat([df_a, na], ignore_index=True), "agenda")
                st.success("Plan consolidado con éxito.")
                st.rerun()

elif menu == "📊 Finanzas":
    st.title("Auditoría de Rentabilidad")
    c1, c2 = st.columns(2)
    f_desde = c1.date_input("Desde", datetime.now() - timedelta(days=30))
    f_hasta = c2.date_input("Hasta", datetime.now())
    
    df_p['Fecha_Inicio'] = pd.to_datetime(df_p['Fecha_Inicio'], errors='coerce')
    df_f = df_p[(df_p['Fecha_Inicio'].dt.date >= f_desde) & (df_p['Fecha_Inicio'].dt.date <= f_hasta)].copy()
    
    # Cálculo de comisiones 30/20
    df_f['% Cesión'] = df_f['Origen'].apply(lambda x: 0.30 if x == "Socio Gimnasio" else 0.20)
    df_f['Monto Cesión'] = df_f['Pago'] * df_f['% Cesión']
    df_f['Utilidad Neta'] = df_f['Pago'] - df_f['Monto Cesión']
    
    bruto, cesion = df_f['Pago'].sum(), df_f['Monto Cesión'].sum()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Ingresos Totales", f"${bruto:,.0f}")
    m2.metric("Cesiones Totales", f"-${cesion:,.0f}")
    m3.metric("Utilidad Neta", f"${bruto - cesion - gastos_f:,.0f}")
    
    st.dataframe(df_f[['Nombre', 'Origen', 'Servicio', 'Pago', '% Cesión', 'Monto Cesión', 'Utilidad Neta']], use_container_width=True)
    csv = df_f.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Descargar Reporte Excel", csv, "Reporte_Elite.csv", "text/csv")
