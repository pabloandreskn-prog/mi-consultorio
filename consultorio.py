import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import urllib.parse

# --- 1. CONFIGURACIÓN Y ESTÉTICA ---
st.set_page_config(page_title="Elite System V41", layout="wide", page_icon="🌿")

PRECIOS_BASE = {
    "Evaluacion": 36000, "Sesion Especializada": 36000, "Sesion Individual": 24000,
    "Plan x5": 110000, "Plan x10": 200000,
    "Masaje ZA": {"Socio": 25000, "Gral": 30000},
    "Masaje ZB": {"Socio": 25000, "Gral": 30000},
    "Masaje Completo": {"Socio": 38000, "Gral": 45000}
}

BRAND_GREEN = "#60b067"

st.markdown(f"""
    <style>
    .stApp {{ background-color: #FFFFFF; color: #1E1E1E; }}
    .turno-card {{
        background: rgba(30, 30, 30, 0.95); border-left: 8px solid {BRAND_GREEN};
        padding: 20px; border-radius: 15px; margin-bottom: 15px; color: white;
    }}
    .stButton>button {{ width: 100%; border-radius: 8px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. GESTIÓN DE DATOS (CONEXIÓN SEGURA) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        df_p = conn.read(worksheet="pacientes", ttl="0").dropna(how='all')
        df_a = conn.read(worksheet="agenda", ttl="0").dropna(how='all')
        
        # Formateo numérico para evitar errores en cálculos
        for col in ['Pago', 'Sesiones_Restantes', 'Sesiones_Totales']:
            if col in df_p.columns:
                df_p[col] = pd.to_numeric(df_p[col], errors='coerce').fillna(0)
        return df_p, df_a
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_p, df_a = cargar_datos()

def guardar_datos(df, hoja):
    """Función maestra de guardado: Alinea columnas dinámicamente para evitar ValueError"""
    try:
        # Leemos el esquema real del Sheets
        esquema = conn.read(worksheet=hoja, ttl="0").columns.tolist()
        # Ajustamos el DataFrame al esquema (rellena DX, Pago, etc., si faltan)
        df_final = df.reindex(columns=esquema).fillna("")
        conn.update(worksheet=hoja, data=df_final)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Error al sincronizar Sheets: {e}")

# --- 3. MOTOR SMART-SYNC (EFECTO SUSANA) ---
def smart_sync():
    if df_a.empty: return
    ahora = datetime.now()
    f_h, h_h = ahora.strftime("%Y-%m-%d"), ahora.strftime("%H:%M")
    
    # Filtro: Turnos pasados no procesados
    mask = (df_a['Fecha'].astype(str) <= f_h) & (df_a['Hora'].astype(str) < h_h) & (df_a.get('Estado','') != 'PROCESADO')
    
    if not df_a[mask].empty:
        df_p_act, df_a_act = df_p.copy(), df_a.copy()
        for idx, t in df_a[mask].iterrows():
            dni_pac = str(t.get('DNI', ''))
            p_idx = df_p_act[df_p_act['DNI'].astype(str) == dni_pac].index
            if not p_idx.empty:
                df_p_act.at[p_idx[0], 'Sesiones_Restantes'] = max(0, df_p_act.at[p_idx[0], 'Sesiones_Restantes'] - 1)
            df_a_act.at[idx, 'Estado'] = 'PROCESADO'
        guardar_datos(df_p_act, "pacientes")
        guardar_datos(df_a_act, "agenda")
        st.rerun()

# --- 4. NAVEGACIÓN ---
menu = st.sidebar.radio("ELITE MASTER V41", ["📅 Agenda Predictiva", "📝 Admisión & DX", "📊 Business Intelligence"])
gastos_fijos = st.sidebar.number_input("Gastos Fijos Mensuales ($)", value=0)

if menu == "📅 Agenda Predictiva":
    smart_sync()
    st.title("Control de Turnos")
    t1, t2 = st.tabs(["Hoy", "Mañana"])

    def render_agenda(fecha_target):
        res = df_a[df_a['Fecha'].astype(str) == fecha_target].sort_values("Hora")
        if res.empty: st.info("No hay turnos registrados.")
        for i, r in res.iterrows():
            p_info = df_p[df_p['DNI'].astype(str) == str(r.get('DNI',''))]
            saldo = int(p_info['Sesiones_Restantes'].iloc[0]) if not p_info.empty else 0
            dx_text = p_info['DX'].iloc[0] if not p_info.empty and 'DX' in p_info.columns else "Sin diagnóstico"
            
            with st.container():
                st.markdown(f"""
                <div class="turno-card">
                    <b>{r['Hora']} hs</b> | {r['Paciente']} | Saldo: <b>{saldo}</b> | DX: <i>{dx_text}</i>
                </div>
                """, unsafe_allow_html=True)
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    with st.popover("⚙️ Reagendar"):
                        nf = st.date_input("Nueva Fecha", key=f"f_{i}")
                        nh = st.time_input("Nueva Hora", key=f"h_{i}")
                        if st.button("Confirmar Cambio", key=f"b_{i}"):
                            df_a.at[i, 'Fecha'], df_a.at[i, 'Hora'] = nf.strftime("%Y-%m-%d"), nh.strftime("%H:%M")
                            guardar_datos(df_a, "agenda")
                            st.rerun()
                with c2:
                    if st.button("🛒 Renovar", key=f"r_{i}"):
                        st.session_state.p_renov = r['Paciente']
                        st.info("Pasa a la pestaña 'Admisión' para cargar el nuevo plan.")
                with c3:
                    msg = urllib.parse.quote(f"Hola {r['Paciente']}, recordatorio de turno en Elite.")
                    st.markdown(f'<a href="https://wa.me/{r.get("WhatsApp","")}?text={msg}" target="_blank"><button style="width:100%; background:#25D366; color:white; border:none; height:38px; border-radius:8px; cursor:pointer;">WhatsApp</button></a>', unsafe_allow_html=True)

    with t1: render_agenda(datetime.now().strftime("%Y-%m-%d"))
    with t2: render_agenda((datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"))

elif menu == "📝 Admisión & DX":
    st.title("Admisión y Diagnóstico")
    with st.form("form_admision", clear_on_submit=True):
        col1, col2 = st.columns(2)
        nombre = col1.text_input("Nombre Completo", value=st.session_state.get('p_renov', ''))
        dni = col1.text_input("DNI")
        tel = col1.text_input("WhatsApp (549...)")
        dx = col1.text_area("DX (Diagnóstico)")
        
        f_ini = col2.date_input("Fecha Inicio")
        h_ini = col2.time_input("Hora Turno")
        dias = col2.multiselect("Días de frecuencia", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])
        serv = st.selectbox("Servicio", list(PRECIOS_BASE.keys()))
        orig = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
        
        # Lógica de precio sugerido
        p_base = PRECIOS_BASE[serv]["Socio" if orig == "Socio Gimnasio" else "Gral"] if "Masaje" in serv else PRECIOS_BASE[serv]
        pago = st.number_input("Cobro Final ($)", value=float(p_base))
        
        if st.form_submit_button("CONSOLIDAR PLAN"):
            if nombre and dni:
                cant = 10 if "x10" in serv else (5 if "x5" in serv else 1)
                # 1. Crear Paciente (Incluye DX)
                new_p = pd.DataFrame([{"DNI": dni, "Nombre": nombre, "WhatsApp": tel, "Origen": orig, "Servicio": serv, "Pago": pago, "Sesiones_Totales": cant, "Sesiones_Restantes": cant, "Fecha_Inicio": f_ini.strftime("%Y-%m-%d"), "DX": dx}])
                
                # 2. Generar Agenda Automática
                d_m = {"Lunes":0, "Martes":1, "Miércoles":2, "Jueves":3, "Viernes":4, "Sábado":5}
                fs, curr = [], f_ini
                while len(fs) < cant:
                    if not dias or curr.weekday() in [d_m[d] for d in dias]: fs.append(curr.strftime("%Y-%m-%d"))
                    curr += timedelta(days=1)
                new_a = pd.DataFrame([{"Fecha": f, "Hora": h_ini.strftime("%H:%M"), "Paciente": nombre, "DNI": dni, "WhatsApp": tel, "Estado": "PENDIENTE", "Servicio": serv} for f in fs])
                
                guardar_datos(pd.concat([df_p, new_p], ignore_index=True), "pacientes")
                guardar_datos(pd.concat([df_a, new_a], ignore_index=True), "agenda")
                st.success(f"Plan consolidado para {nombre}.")
                if 'p_renov' in st.session_state: del st.session_state.p_renov
                st.rerun()

elif menu == "📊 Business Intelligence":
    st.title("Reporte de Rentabilidad")
    cf1, cf2 = st.columns(2)
    d_f, h_f = cf1.date_input("Desde", datetime.now()-timedelta(days=30)), cf2.date_input("Hasta", datetime.now())
    
    df_p['Fecha_Inicio'] = pd.to_datetime(df_p['Fecha_Inicio'], errors='coerce')
    df_f = df_p[(df_p['Fecha_Inicio'].dt.date >= d_f) & (df_p['Fecha_Inicio'].dt.date <= h_f)].copy()
    
    # Comisiones 30/20
    df_f['Comision'] = df_f.apply(lambda x: x['Pago']*0.30 if x['Origen']=="Socio Gimnasio" else x['Pago']*0.20, axis=1)
    df_f['Ingreso_Neto'] = df_f['Pago'] - df_f['Comision']
    
    bruto, cesion = df_f['Pago'].sum(), df_f['Comision'].sum()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Ingreso Bruto", f"${bruto:,.0f}")
    m2.metric("Cesión Total", f"-${cesion:,.0f}")
    m3.metric("Utilidad Final", f"${bruto - cesion - gastos_fijos:,.0f}")
    
    st.subheader("Base de Datos Histórica")
    st.dataframe(df_f[['Nombre', 'DX', 'Origen', 'Servicio', 'Pago', 'Comision', 'Ingreso_Neto']], use_container_width=True)
    
    # Exportación CSV (Segura y funcional)
    st.download_button("📥 Descargar Reporte Excel", df_f.to_csv(index=False).encode('utf-8'), "Elite_Report.csv", "text/csv")
