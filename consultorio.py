import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import urllib.parse

# --- 1. CONFIGURACIÓN Y ESTÉTICA ---
st.set_page_config(page_title="Elite System V40", layout="wide", page_icon="🌿")

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
        padding: 15px; border-radius: 12px; margin-bottom: 10px; color: white;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE DATOS (CONEXIÓN SEGURA) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        df_pacientes = conn.read(worksheet="pacientes", ttl="0").dropna(how='all')
        df_agenda = conn.read(worksheet="agenda", ttl="0").dropna(how='all')
        
        # Formateo de tipos de datos para cálculos
        columnas_num = ['Pago', 'Sesiones_Restantes', 'Sesiones_Totales']
        for col in columnas_num:
            if col in df_pacientes.columns:
                df_pacientes[col] = pd.to_numeric(df_pacientes[col], errors='coerce').fillna(0)
        
        return df_pacientes, df_agenda
    except Exception as e:
        st.error(f"Error de conexión con Sheets: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_p, df_a = cargar_datos()

def guardar_datos(df, hoja):
    """Sincronización profesional que alinea columnas de Google Sheets"""
    try:
        # Mapeo de columnas actuales para evitar errores de desajuste
        df_ref = conn.read(worksheet=hoja, ttl="0")
        columnas_reales = df_ref.columns.tolist()
        df_ajustado = df.reindex(columns=columnas_reales).fillna("")
        conn.update(worksheet=hoja, data=df_ajustado)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Error al grabar datos: {e}")

# --- 3. MOTOR SMART-SYNC (EFECTO SUSANA) ---
def smart_sync():
    if df_a.empty: return
    ahora = datetime.now()
    fecha_hoy = ahora.strftime("%Y-%m-%d")
    hora_hoy = ahora.strftime("%H:%M")
    
    # Detectar turnos que ya pasaron y restarlos del saldo
    mask = (df_a['Fecha'].astype(str) <= fecha_hoy) & (df_a['Hora'].astype(str) < hora_hoy) & (df_a.get('Estado','') != 'PROCESADO')
    
    if not df_a[mask].empty:
        df_p_new, df_a_new = df_p.copy(), df_a.copy()
        for idx, t in df_a[mask].iterrows():
            dni_pac = str(t.get('DNI', ''))
            indices = df_p_new[df_p_new['DNI'].astype(str) == dni_pac].index
            if not indices.empty:
                df_p_new.at[indices[0], 'Sesiones_Restantes'] = max(0, df_p_new.at[indices[0], 'Sesiones_Restantes'] - 1)
            df_a_new.at[idx, 'Estado'] = 'PROCESADO'
        guardar_datos(df_p_new, "pacientes")
        guardar_datos(df_a_new, "agenda")
        st.rerun()

# --- 4. NAVEGACIÓN PRINCIPAL ---
opciones = ["📅 Agenda Operativa", "📝 Admisión & DX", "📊 Business Intelligence"]
menu = st.sidebar.radio("MENÚ ÉLITE MASTER", opciones)
gastos_fijos = st.sidebar.number_input("Gastos Fijos Mensuales ($)", value=0)

if menu == "📅 Agenda Operativa":
    smart_sync()
    st.title("Control de Turnos en Tiempo Real")
    t1, t2 = st.tabs(["Sesiones de Hoy", "Sesiones de Mañana"])

    def mostrar_agenda(f_filtro):
        turnos = df_a[df_a['Fecha'].astype(str) == f_filtro].sort_values("Hora")
        if turnos.empty: st.info("No hay turnos para esta fecha.")
        for i, r in turnos.iterrows():
            with st.container():
                p_data = df_p[df_p['DNI'].astype(str) == str(r.get('DNI',''))]
                saldo = int(p_data['Sesiones_Restantes'].iloc[0]) if not p_data.empty else 0
                diagnostico = p_data['DX'].iloc[0] if not p_data.empty and 'DX' in p_data.columns else "Sin DX"
                
                st.markdown(f"""
                <div class="turno-card">
                    <b>{r['Hora']} hs</b> | {r['Paciente']} | Saldo: <b>{saldo}</b> | DX: <i>{diagnostico}</i>
                </div>
                """, unsafe_allow_html=True)
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    with st.popover("⚙️ Reagendar"):
                        nueva_f = st.date_input("Fecha", key=f"f{i}")
                        nueva_h = st.time_input("Hora", key=f"h{i}")
                        if st.button("Confirmar", key=f"b{i}"):
                            df_a.at[i, 'Fecha'] = nueva_f.strftime("%Y-%m-%d")
                            df_a.at[i, 'Hora'] = nueva_h.strftime("%H:%M")
                            guardar_datos(df_a, "agenda")
                            st.rerun()
                with c2:
                    if st.button("🛒 Renovar", key=f"r{i}"):
                        st.session_state.p_renov = r['Paciente']
                        st.info("Carga el nuevo plan en el menú Admisión.")
                with c3:
                    msg = urllib.parse.quote(f"Hola {r['Paciente']}, te recordamos tu turno en Elite.")
                    st.markdown(f'<a href="https://wa.me/{r.get("WhatsApp","")}?text={msg}" target="_blank"><button style="width:100%; background:#25D366; color:white; border:none; padding:8px; border-radius:8px; cursor:pointer;">WhatsApp</button></a>', unsafe_allow_html=True)

    with t1: mostrar_agenda(datetime.now().strftime("%Y-%m-%d"))
    with t2: mostrar_agenda((datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"))

elif menu == "📝 Admisión & DX":
    st.title("Registro de Pacientes y Diagnóstico")
    with st.form("form_admision", clear_on_submit=True):
        col1, col2 = st.columns(2)
        nombre = col1.text_input("Nombre Completo", value=st.session_state.get('p_renov', ''))
        dni = col1.text_input("DNI")
        tel = col1.text_input("WhatsApp")
        dx_input = col1.text_area("Diagnóstico (DX)")
        
        f_ini = col2.date_input("Fecha Inicio", datetime.now())
        h_ini = col2.time_input("Hora Turno")
        dias_frec = col2.multiselect("Días", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])
        
        serv = st.selectbox("Servicio / Plan", list(PRECIOS_BASE.keys()))
        orig = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
        
        # Precio Sugerido
        es_socio = (orig == "Socio Gimnasio")
        p_base = PRECIOS_BASE[serv]["Socio" if es_socio else "Gral"] if "Masaje" in serv else PRECIOS_BASE[serv]
        pago_final = st.number_input("Cobro ($)", value=float(p_base))
        
        if st.form_submit_button("CONSOLIDAR Y AGENDAR"):
            if nombre and dni:
                # Calcular cantidad de sesiones
                cant = 10 if "x10" in serv else (5 if "x5" in serv else 1)
                
                # 1. Crear Registro de Paciente
                new_pac = pd.DataFrame([{
                    "DNI": dni, "Nombre": nombre, "WhatsApp": tel, "Origen": orig, 
                    "Servicio": serv, "Pago": pago_final, "Sesiones_Totales": cant, 
                    "Sesiones_Restantes": cant, "Fecha_Inicio": f_ini.strftime("%Y-%m-%d"), "DX": dx_input
                }])
                
                # 2. Generar Agenda Automática
                d_map = {"Lunes":0, "Martes":1, "Miércoles":2, "Jueves":3, "Viernes":4, "Sábado":5}
                fechas, actual = [], f_ini
                while len(fechas) < cant:
                    if not dias_frec or actual.weekday() in [d_map[d] for d in dias_frec]:
                        fechas.append(actual.strftime("%Y-%m-%d"))
                    actual += timedelta(days=1)
                
                new_age = pd.DataFrame([{
                    "Fecha": f, "Hora": h_ini.strftime("%H:%M"), "Paciente": nombre, 
                    "DNI": dni, "WhatsApp": tel, "Estado": "PENDIENTE", "Servicio": serv
                } for f in fechas])
                
                guardar_datos(pd.concat([df_p, new_pac], ignore_index=True), "pacientes")
                guardar_datos(pd.concat([df_a, new_age], ignore_index=True), "agenda")
                st.success(f"¡Éxito! Plan consolidado para {nombre}.")
                if 'p_renov' in st.session_state: del st.session_state.p_renov
                st.rerun()

elif menu == "📊 Business Intelligence":
    st.title("Auditoría y Rentabilidad")
    cf1, cf2 = st.columns(2)
    desde, hasta = cf1.date_input("Desde", datetime.now() - timedelta(days=30)), cf2.date_input("Hasta", datetime.now())
    
    df_p['Fecha_Inicio'] = pd.to_datetime(df_p['Fecha_Inicio'], errors='coerce')
    df_f = df_p[(df_p['Fecha_Inicio'].dt.date >= desde) & (df_p['Fecha_Inicio'].dt.date <= hasta)].copy()
    
    # Cálculo de comisiones 30/20 solicitado
    def calc_cesion(row):
        return row['Pago'] * 0.30 if row['Origen'] == "Socio Gimnasio" else row['Pago'] * 0.20
    
    df_f['Monto_Cesion'] = df_f.apply(calc_cesion, axis=1)
    df_f['Utilidad_Neta'] = df_f['Pago'] - df_f['Monto_Cesion']
    
    bruto, total_cesion = df_f['Pago'].sum(), df_f['Monto_Cesion'].sum()
    neta_total = bruto - total_cesion - gastos_fijos

    c1, c2, c3 = st.columns(3)
    c1.metric("Ingresos Totales", f"${bruto:,.0f}")
    c2.metric("Cesiones (Gimnasio/Propio)", f"-${total_cesion:,.0f}")
    c3.metric("Utilidad Neta Final", f"${neta_total:,.0f}")

    st.subheader("Base de Datos Histórica")
    st.dataframe(df_f[['Nombre', 'DX', 'Origen', 'Servicio', 'Pago', 'Monto_Cesion', 'Utilidad_Neta']], use_container_width=True)
    
    csv = df_f.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Exportar Reporte para Excel", csv, "Elite_Report.csv", "text/csv")
