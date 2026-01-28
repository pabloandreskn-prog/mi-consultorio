import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import urllib.parse

# --- 1. CONFIGURACIÓN Y ESTÉTICA PROFESIONAL ---
st.set_page_config(page_title="Elite System Master V36", layout="wide", page_icon="🌿")

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
        padding: 20px; border-radius: 15px; margin-bottom: 12px; color: white;
    }}
    .chip-libre {{
        background: rgba(96, 176, 103, 0.1); color: {BRAND_GREEN};
        padding: 8px; border-radius: 10px; border: 1px solid {BRAND_GREEN};
        font-weight: bold; text-align: center; margin-bottom: 5px;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DE DATOS BLINDADO ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        df_p = conn.read(worksheet="pacientes", ttl="0").dropna(how='all')
        df_a = conn.read(worksheet="agenda", ttl="0").dropna(how='all')
        
        # Blindaje contra KeyError: Si no existen, se crean
        for col in ['Pago', 'Sesiones_Restantes', 'Sesiones_Totales']:
            if col in df_p.columns:
                df_p[col] = pd.to_numeric(df_p[col], errors='coerce').fillna(0)
        if 'Fecha_Inicio' not in df_p.columns: df_p['Fecha_Inicio'] = None
        if 'Estado' not in df_a.columns: df_a['Estado'] = 'PENDIENTE'
        
        return df_p, df_a
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_p, df_a = cargar_datos()

def guardar_datos(df, hoja):
    """Alineación dinámica de columnas para evitar ValueError"""
    try:
        # Recuperamos las columnas que realmente existen en el archivo de Google
        cols_reales = conn.read(worksheet=hoja, ttl="0").columns.tolist()
        # Reindexamos el DataFrame para que coincida con el Excel antes de subir
        df_final = df.reindex(columns=cols_reales).fillna("")
        conn.update(worksheet=hoja, data=df_final)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Error al sincronizar con Google Sheets: {e}")

# --- 3. MOTOR SMART-SYNC (EFECTO SUSANA) ---
def smart_sync():
    if df_a.empty: return
    ahora = datetime.now()
    fecha_h = ahora.strftime("%Y-%m-%d")
    hora_h = ahora.strftime("%H:%M")
    
    # Filtro de turnos pasados no procesados
    mask = (df_a['Fecha'].astype(str) <= fecha_h) & (df_a['Hora'].astype(str) < hora_h) & (df_a['Estado'] != 'PROCESADO')
    
    if not df_a[mask].empty:
        df_p_act, df_a_act = df_p.copy(), df_a.copy()
        for idx, t in df_a[mask].iterrows():
            dni = str(t.get('DNI', ''))
            p_idx = df_p_act[df_p_act['DNI'].astype(str) == dni].index
            if not p_idx.empty:
                df_p_act.at[p_idx[0], 'Sesiones_Restantes'] = max(0, df_p_act.at[p_idx[0], 'Sesiones_Restantes'] - 1)
            df_a_act.at[idx, 'Estado'] = 'PROCESADO'
        guardar_datos(df_p_act, "pacientes")
        guardar_datos(df_a_act, "agenda")
        st.rerun()

# --- 4. NAVEGACIÓN PRINCIPAL ---
menu = st.sidebar.radio("SISTEMA ÉLITE MASTER", ["📅 Gestión de Agenda", "📝 Admisión & Registro", "📊 BI & Finanzas"])
gastos_fijos = st.sidebar.number_input("Gastos Fijos Mensuales ($)", value=0)

if menu == "📅 Gestión de Agenda":
    smart_sync()
    st.title("Agenda de Operaciones")
    
    with st.expander("🔍 CONSULTAR DISPONIBILIDAD"):
        f_b = st.date_input("Día:", datetime.now())
        ocup = df_a[df_a['Fecha'].astype(str) == str(f_b)]['Hora'].tolist()
        libres = [h for h in ["08:00","09:00","10:00","11:00","14:00","15:00","16:00","17:00","18:00","19:00"] if h not in ocup]
        cols = st.columns(5)
        for i, h in enumerate(libres): cols[i%5].markdown(f'<div class="chip-libre">{h}</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Sesiones de Hoy", "Sesiones de Mañana"])
    
    def render_agenda(fecha_str):
        turnos = df_a[df_a['Fecha'].astype(str) == fecha_str].sort_values("Hora")
        if turnos.empty: st.info("No hay citas programadas.")
        for i, r in turnos.iterrows():
            # Obtener saldo actual del paciente
            p_row = df_p[df_p['DNI'].astype(str) == str(r.get('DNI', ''))]
            saldo = int(p_row['Sesiones_Restantes'].iloc[0]) if not p_row.empty else 0
            
            st.markdown(f"""
            <div class="turno-card">
                <b>{r['Hora']} hs</b> | {r['Paciente']} | Saldo Restante: <b>{saldo}</b>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                with st.popover("⚙️ Reagendar"):
                    nueva_f = st.date_input("Nueva Fecha", key=f"f_{i}")
                    nueva_h = st.time_input("Nueva Hora", key=f"h_{i}")
                    if st.button("Confirmar Reagendamiento", key=f"btn_r_{i}"):
                        df_a.at[i, 'Fecha'] = nueva_f.strftime("%Y-%m-%d")
                        df_a.at[i, 'Hora'] = nueva_h.strftime("%H:%M")
                        guardar_datos(df_a, "agenda")
                        st.success("Turno actualizado")
                        st.rerun()
            with c2:
                if st.button("🛒 Renovar Plan", key=f"ren_{i}"):
                    st.session_state.paciente_renovar = r['Paciente']
                    st.info(f"Cargue el nuevo plan para {r['Paciente']} en la pestaña Admisión.")
            with c3:
                msg = urllib.parse.quote(f"Hola {r['Paciente']}, te recordamos tu turno en Elite.")
                st.markdown(f'<a href="https://wa.me/{r.get("WhatsApp","")}?text={msg}" target="_blank"><button style="width:100%; background:#25D366; color:white; border:none; height:35px; border-radius:10px; cursor:pointer;">WhatsApp</button></a>', unsafe_allow_html=True)

    with tab1: render_agenda(datetime.now().strftime("%Y-%m-%d"))
    with tab2: render_agenda((datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"))

elif menu == "📝 Admisión & Registro":
    st.title("Consolidación de Pacientes")
    with st.form("master_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        nombre = col1.text_input("Nombre Completo", value=st.session_state.get('paciente_renovar', ''))
        dni = col1.text_input("DNI")
        tel = col1.text_input("WhatsApp (549...)")
        
        f_inicio = col2.date_input("Fecha Inicio", datetime.now())
        h_fija = col2.time_input("Hora del Turno")
        frecuencia = col2.multiselect("Días de Frecuencia", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])
        
        servicio = st.selectbox("Servicio", list(PRECIOS_BASE.keys()))
        origen = st.selectbox("Origen del Paciente", ["Socio Gimnasio", "Captación Propia"])
        
        # Sugerencia de Precio Inteligente
        es_nuevo = df_p[df_p['DNI'].astype(str) == str(dni)].empty
        p_base = PRECIOS_BASE[servicio]["Socio" if origen == "Socio Gimnasio" else "Gral"] if "Masaje" in servicio else PRECIOS_BASE[servicio]
        if servicio == "Evaluacion" and not es_nuevo: p_base = 0 if origen == "Socio Gimnasio" else p_base * 0.5
        
        monto_final = st.number_input("Cobro Acordado ($)", value=float(p_base))
        
        if st.form_submit_button("CONSOLIDAR Y AGENDAR"):
            if nombre and dni:
                cant = 10 if "x10" in servicio else (5 if "x5" in servicio else 1)
                # 1. Registro de Paciente
                new_p = pd.DataFrame([{
                    "DNI": dni, "Nombre": nombre, "WhatsApp": tel, "Origen": origen, 
                    "Servicio": servicio, "Pago": monto_final, "Sesiones_Totales": cant, 
                    "Sesiones_Restantes": cant, "Fecha_Inicio": f_inicio.strftime("%Y-%m-%d")
                }])
                
                # 2. Generación Masiva de Agenda
                d_map = {"Lunes":0, "Martes":1, "Miércoles":2, "Jueves":3, "Viernes":4, "Sábado":5}
                fechas, curr = [], f_inicio
                while len(fechas) < cant:
                    if not frecuencia or curr.weekday() in [d_map[d] for d in frecuencia]:
                        fechas.append(curr.strftime("%Y-%m-%d"))
                    curr += timedelta(days=1)
                
                new_a_rows = [{
                    "Fecha": f, "Hora": h_fija.strftime("%H:%M"), "Paciente": nombre, 
                    "Servicio": servicio, "DNI": dni, "WhatsApp": tel, "Estado": "PENDIENTE"
                } for f in fechas]
                
                guardar_datos(pd.concat([df_p, new_p], ignore_index=True), "pacientes")
                guardar_datos(pd.concat([df_a, pd.DataFrame(new_a_rows)], ignore_index=True), "agenda")
                
                st.success(f"¡Éxito! Plan de {cant} sesiones creado para {nombre}.")
                if 'paciente_renovar' in st.session_state: del st.session_state.paciente_renovar
                st.rerun()

elif menu == "📊 BI & Finanzas":
    st.title("Análisis Financiero & Auditoría")
    
    # Filtro de Fechas Blindado
    c_f1, c_f2 = st.columns(2)
    f_desde = c_f1.date_input("Desde", datetime.now() - timedelta(days=30))
    f_hasta = c_f2.date_input("Hasta", datetime.now())
    
    # Filtrado dinámico
    df_p['Fecha_Inicio'] = pd.to_datetime(df_p['Fecha_Inicio'], errors='coerce')
    df_filtrado = df_p[(df_p['Fecha_Inicio'].dt.date >= f_desde) & (df_p['Fecha_Inicio'].dt.date <= f_hasta)].copy()

    # Cálculos de Rentabilidad (30% Socio / 20% Propio)
    df_filtrado['% Cesión'] = df_filtrado['Origen'].apply(lambda x: 0.30 if x == "Socio Gimnasio" else 0.20)
    df_filtrado['Monto Cesión'] = df_filtrado['Pago'] * df_filtrado['% Cesión']
    df_filtrado['Utilidad Neta'] = df_filtrado['Pago'] - df_filtrado['Monto Cesión']
    
    bruto = df_filtrado['Pago'].sum()
    cesion_total = df_filtrado['Monto Cesión'].sum()
    neta_total = bruto - cesion_total - gastos_fijos

    m1, m2, m3 = st.columns(3)
    m1.metric("Ingresos Brutos", f"${bruto:,.0f}")
    m2.metric("Total Cesiones", f"-${cesion_total:,.0f}")
    m3.metric("Utilidad Final", f"${neta_total:,.0f}")

    st.divider()
    st.subheader("Base de Datos Histórica y Auditoría")
    st.dataframe(df_filtrado[['Nombre', 'Origen', 'Servicio', 'Pago', '% Cesión', 'Monto Cesión', 'Utilidad Neta']], use_container_width=True)
    
    # Botón de exportación seguro
    csv = df_filtrado.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Descargar Reporte (Excel)", csv, "Elite_Financial_Report.csv", "text/csv")
