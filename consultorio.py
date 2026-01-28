import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import urllib.parse

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Elite System V35", layout="wide", page_icon="🌿")

PRECIOS_BASE = {
    "Evaluacion": 36000, "Sesion Especializada": 36000, "Sesion Individual": 24000,
    "Plan x5": 110000, "Plan x10": 200000,
    "Masaje ZA": {"Socio": 25000, "Gral": 30000},
    "Masaje ZB": {"Socio": 25000, "Gral": 30000},
    "Masaje Completo": {"Socio": 38000, "Gral": 45000}
}

# --- 2. GESTIÓN DE DATOS BLINDADA ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        df_p = conn.read(worksheet="pacientes", ttl="0").dropna(how='all')
        df_a = conn.read(worksheet="agenda", ttl="0").dropna(how='all')
        
        # Asegurar columnas críticas para evitar KeyError
        if 'Fecha_Inicio' not in df_p.columns: df_p['Fecha_Inicio'] = datetime.now().strftime("%Y-%m-%d")
        if 'Estado' not in df_a.columns: df_a['Estado'] = 'PENDIENTE'
        
        for col in ['Pago', 'Sesiones_Restantes', 'Sesiones_Totales']:
            if col in df_p.columns:
                df_p[col] = pd.to_numeric(df_p[col], errors='coerce').fillna(0)
        return df_p, df_a
    except Exception:
        st.error("Error de conexión. Revisa el nombre de las pestañas en Google Sheets.")
        return pd.DataFrame(), pd.DataFrame()

df_p, df_a = cargar_datos()

def guardar_datos(df, hoja):
    """Función de guardado ultra-segura que alinea columnas automáticamente"""
    try:
        # Leemos la estructura actual para no romper nada
        df_actual = conn.read(worksheet=hoja, ttl="0")
        cols_reales = df_actual.columns.tolist()
        # Alineamos el nuevo dataframe a las columnas que ya existen en el Excel
        df_final = df.reindex(columns=cols_reales).fillna("")
        conn.update(worksheet=hoja, data=df_final)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Error crítico al grabar: {e}")

# --- 3. MOTOR SMART-SYNC (EFECTO SUSANA) ---
def smart_sync():
    if df_a.empty: return
    ahora = datetime.now()
    fecha_h = ahora.strftime("%Y-%m-%d")
    hora_h = ahora.strftime("%H:%M")
    
    # Buscamos turnos pasados no procesados
    mask = (df_a['Fecha'].astype(str) <= fecha_h) & (df_a['Hora'].astype(str) < hora_h) & (df_a['Estado'] != 'PROCESADO')
    
    if not df_a[mask].empty:
        df_p_act = df_p.copy()
        df_a_act = df_a.copy()
        for idx, t in df_a[mask].iterrows():
            dni = str(t.get('DNI', ''))
            p_idx = df_p_act[df_p_act['DNI'].astype(str) == dni].index
            if not p_idx.empty:
                df_p_act.at[p_idx[0], 'Sesiones_Restantes'] = max(0, df_p_act.at[p_idx[0], 'Sesiones_Restantes'] - 1)
            df_a_act.at[idx, 'Estado'] = 'PROCESADO'
        guardar_datos(df_p_act, "pacientes")
        guardar_datos(df_a_act, "agenda")
        st.rerun()

# --- 4. INTERFAZ ---
menu = st.sidebar.radio("MENÚ ÉLITE", ["📅 Agenda", "📝 Admisión", "📊 Finanzas"])
gastos_f = st.sidebar.number_input("Gastos Fijos ($)", value=0)

if menu == "📅 Agenda":
    smart_sync()
    st.title("Agenda de Turnos")
    
    t1, t2 = st.tabs(["Hoy", "Mañana"])
    def render_dia(f):
        res = df_a[df_a['Fecha'].astype(str) == f].sort_values("Hora")
        if res.empty: st.info("Día libre.")
        for i, r in res.iterrows():
            with st.container(border=True):
                p_info = df_p[df_p['DNI'].astype(str) == str(r['DNI'])]
                restante = int(p_info['Sesiones_Restantes'].iloc[0]) if not p_info.empty else 0
                st.write(f"**{r['Hora']} hs** | {r['Paciente']} | Saldo: **{restante}**")
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    with st.popover("⚙️ Reagendar"):
                        nf = st.date_input("Nueva Fecha", key=f"f{i}")
                        nh = st.time_input("Nueva Hora", key=f"h{i}")
                        if st.button("Confirmar", key=f"b{i}"):
                            df_a.at[i, 'Fecha'] = nf.strftime("%Y-%m-%d")
                            df_a.at[i, 'Hora'] = nh.strftime("%H:%M")
                            guardar_datos(df_a, "agenda")
                            st.success("Actualizado")
                            st.rerun()
                with c2:
                    if st.button("🛒 Renovar", key=f"r{i}"):
                        st.session_state.p_renovar = r['Paciente']
                        st.info("Ve a Admisión")
                with c3:
                    msg = urllib.parse.quote(f"Hola {r['Paciente']}, recordatorio de turno.")
                    st.markdown(f'<a href="https://wa.me/{r.get("WhatsApp","")}?text={msg}" target="_blank"><button style="width:100%; background:#25D366; color:white; border:none; padding:5px; border-radius:5px;">WhatsApp</button></a>', unsafe_allow_html=True)

    with t1: render_dia(datetime.now().strftime("%Y-%m-%d"))
    with t2: render_dia((datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"))

elif menu == "📝 Admisión":
    st.title("Registro de Plan")
    with st.form("main_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        nom = c1.text_input("Nombre", value=st.session_state.get('p_renovar', ''))
        dni = c1.text_input("DNI")
        tel = c1.text_input("WhatsApp")
        f_i = c2.date_input("Inicio")
        h_i = c2.time_input("Hora")
        dias = c2.multiselect("Días", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])
        serv = st.selectbox("Servicio", list(PRECIOS_BASE.keys()))
        orig = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
        
        # Cálculo de precio
        p_base = PRECIOS_BASE[serv]["Socio" if orig=="Socio Gimnasio" else "Gral"] if "Masaje" in serv else PRECIOS_BASE[serv]
        pago = st.number_input("Monto Recibido", value=float(p_base))
        
        if st.form_submit_button("CONSOLIDAR PLAN"):
            if nom and dni:
                cant = 10 if "x10" in serv else (5 if "x5" in serv else 1)
                # Registro Paciente
                new_p_row = {col: "" for col in df_p.columns}
                new_p_row.update({"DNI": dni, "Nombre": nom, "WhatsApp": tel, "Origen": orig, "Servicio": serv, "Pago": pago, "Sesiones_Totales": cant, "Sesiones_Restantes": cant, "Fecha_Inicio": f_i.strftime("%Y-%m-%d")})
                
                # Registro Agenda
                d_map = {"Lunes":0, "Martes":1, "Miércoles":2, "Jueves":3, "Viernes":4, "Sábado":5}
                fechas, curr = [], f_i
                while len(fechas) < cant:
                    if not dias or curr.weekday() in [d_map[d] for d in dias]: fechas.append(curr.strftime("%Y-%m-%d"))
                    curr += timedelta(days=1)
                
                new_a_rows = []
                for f in fechas:
                    a_row = {col: "" for col in df_a.columns}
                    a_row.update({"Fecha": f, "Hora": h_i.strftime("%H:%M"), "Paciente": nom, "DNI": dni, "WhatsApp": tel, "Estado": "PENDIENTE", "Servicio": serv})
                    new_a_rows.append(a_row)
                
                guardar_datos(pd.concat([df_p, pd.DataFrame([new_p_row])], ignore_index=True), "pacientes")
                guardar_datos(pd.concat([df_a, pd.DataFrame(new_a_rows)], ignore_index=True), "agenda")
                st.success("¡Plan Guardado!")
                st.rerun()

elif menu == "📊 Finanzas":
    st.title("Análisis Financiero")
    c1, c2 = st.columns(2)
    f_d = c1.date_input("Desde", datetime.now() - timedelta(days=30))
    f_h = c2.date_input("Hasta", datetime.now())
    
    df_p['Fecha_Inicio'] = pd.to_datetime(df_p['Fecha_Inicio'], errors='coerce')
    df_f = df_p[(df_p['Fecha_Inicio'].dt.date >= f_d) & (df_p['Fecha_Inicio'].dt.date <= f_h)].copy()
    
    # Lógica de Cesión 30/20 solicitada
    df_f['% Cesión'] = df_f['Origen'].apply(lambda x: 0.30 if x == "Socio Gimnasio" else 0.20)
    df_f['Monto Cesión'] = df_f['Pago'] * df_f['% Cesión']
    df_f['Neto'] = df_f['Pago'] - df_f['Monto Cesión']
    
    bruto, cesion = df_f['Pago'].sum(), df_f['Monto Cesión'].sum()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Ingreso Bruto", f"${bruto:,.0f}")
    m2.metric("Cesión Total", f"-${cesion:,.0f}")
    m3.metric("Utilidad Neta", f"${bruto - cesion - gastos_f:,.0f}")
    
    st.subheader("Histórico de Pacientes y Cesiones")
    st.dataframe(df_f[['Nombre', 'Origen', 'Pago', '% Cesión', 'Monto Cesión', 'Neto']], use_container_width=True)
    
    csv = df_f.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Descargar Excel (CSV)", csv, "Reporte_Elite.csv", "text/csv")
