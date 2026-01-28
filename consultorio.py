import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import urllib.parse
import plotly.express as px

# --- 1. CONFIGURACIÓN DE ESCENA ---
st.set_page_config(page_title="Elite System Professional", layout="wide", page_icon="🌿")

# Paleta de colores y estilos
BRAND_GREEN = "#60b067"
st.markdown(f"""
    <style>
    .main {{ background-color: #f5f7f9; }}
    .stButton>button {{ width: 100%; border-radius: 10px; height: 3em; font-weight: bold; }}
    .turno-card {{
        background: white; border-left: 5px solid {BRAND_GREEN};
        padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 10px; color: #1E1E1E;
    }}
    .metric-box {{
        background: white; padding: 20px; border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); text-align: center;
    }}
    </style>
    """, unsafe_allow_html=True)

PRECIOS_BASE = {
    "Evaluacion": 36000, "Sesion Especializada": 36000, "Sesion Individual": 24000,
    "Plan x5": 110000, "Plan x10": 200000,
    "Masaje ZA": {"Socio": 25000, "Gral": 30000},
    "Masaje ZB": {"Socio": 25000, "Gral": 30000},
    "Masaje Completo": {"Socio": 38000, "Gral": 45000}
}

# --- 2. MOTOR DE DATOS (NÚCLEO DEL SISTEMA) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        # Carga con TTL 0 para datos siempre frescos
        df_p = conn.read(worksheet="pacientes", ttl="0").dropna(how='all')
        df_a = conn.read(worksheet="agenda", ttl="0").dropna(how='all')
        
        # BLINDAJE: Asegurar columnas mínimas para que no de KeyError
        cols_p_necesarias = ['DNI', 'Nombre', 'WhatsApp', 'Origen', 'Servicio', 'Pago', 'Sesiones_Totales', 'Sesiones_Restantes', 'Fecha_Inicio']
        for c in cols_p_necesarias:
            if c not in df_p.columns: df_p[c] = 0 if 'Sesiones' in c else ""
            
        cols_a_necesarias = ['Fecha', 'Hora', 'Paciente', 'DNI', 'WhatsApp', 'Estado']
        for c in cols_a_necesarias:
            if c not in df_a.columns: df_a[c] = "PENDIENTE" if c == 'Estado' else ""

        # Tipado de datos
        df_p['Sesiones_Restantes'] = pd.to_numeric(df_p['Sesiones_Restantes'], errors='coerce').fillna(0)
        df_p['Pago'] = pd.to_numeric(df_p['Pago'], errors='coerce').fillna(0)
        
        return df_p, df_a
    except Exception as e:
        st.error(f"Error de conexión con Google Sheets: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_p, df_a = cargar_datos()

def guardar_datos(df, hoja):
    try:
        # Alineación estricta de columnas para evitar el ValueError de tu captura
        df_esquema = conn.read(worksheet=hoja, ttl="0")
        df_final = df.reindex(columns=df_esquema.columns).fillna("")
        conn.update(worksheet=hoja, data=df_final)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Fallo al sincronizar con la nube: {e}")

# --- 3. SMART-SYNC: DESCUENTO AUTOMÁTICO (Efecto Susana) ---
def smart_sync():
    if df_a.empty: return
    ahora = datetime.now()
    fecha_hoy = ahora.strftime("%Y-%m-%d")
    hora_actual = ahora.strftime("%H:%M")
    
    # Identificar turnos pasados no procesados
    mask = (df_a['Fecha'].astype(str) <= fecha_hoy) & (df_a['Hora'].astype(str) < hora_actual) & (df_a['Estado'] != 'PROCESADO')
    
    if not df_a[mask].empty:
        df_p_act, df_a_act = df_p.copy(), df_a.copy()
        for idx, t in df_a[mask].iterrows():
            dni_t = str(t.get('DNI', ''))
            idx_p = df_p_act[df_p_act['DNI'].astype(str) == dni_t].index
            if not idx_p.empty:
                df_p_act.at[idx_p[0], 'Sesiones_Restantes'] = max(0, df_p_act.at[idx_p[0], 'Sesiones_Restantes'] - 1)
            df_a_act.at[idx, 'Estado'] = 'PROCESADO'
        guardar_datos(df_p_act, "pacientes")
        guardar_datos(df_a_act, "agenda")
        st.rerun()

# --- 4. NAVEGACIÓN Y PANELES ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3209/3209109.png", width=100)
menu = st.sidebar.selectbox("NAVEGACIÓN", ["📅 Agenda Predictiva", "📝 Registro de Admisión", "📊 Finanzas & Auditoría"])
gastos_fijos = st.sidebar.number_input("Gastos Mensuales ($)", value=0, step=1000)

# --- PANEL 1: AGENDA ---
if menu == "📅 Agenda Predictiva":
    smart_sync()
    st.title("Gestión de Sesiones")
    
    with st.expander("🔍 Consultar Disponibilidad"):
        f_check = st.date_input("Día a consultar", datetime.now())
        ocupados = df_a[df_a['Fecha'].astype(str) == str(f_check)]['Hora'].tolist()
        libres = [h for h in ["08:00","09:00","10:00","11:00","14:00","15:00","16:00","17:00","18:00","19:00"] if h not in ocupados]
        cols = st.columns(5)
        for i, h in enumerate(libres):
            cols[i%5].info(f"✨ {h}")

    tab_h, tab_m = st.tabs(["Hoy", "Mañana"])
    
    def mostrar_agenda(f_str):
        turnos = df_a[df_a['Fecha'].astype(str) == f_str].sort_values("Hora")
        if turnos.empty: st.info("No hay pacientes agendados.")
        for i, r in turnos.iterrows():
            p_sel = df_p[df_p['DNI'].astype(str) == str(r['DNI'])]
            saldo = int(p_sel['Sesiones_Restantes'].iloc[0]) if not p_sel.empty else 0
            
            st.markdown(f"""<div class="turno-card"><b>{r['Hora']} hs</b> | {r['Paciente']} | Saldo actual: {saldo} sesiones</div>""", unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            with c1:
                with st.popover("⚙️ Reagendar"):
                    nf = st.date_input("Nueva Fecha", key=f"nf{i}")
                    nh = st.time_input("Nueva Hora", key=f"nh{i}")
                    if st.button("Confirmar Reagenda", key=f"rb{i}"):
                        df_a.at[i, 'Fecha'] = nf.strftime("%Y-%m-%d")
                        df_a.at[i, 'Hora'] = nh.strftime("%H:%M")
                        guardar_datos(df_a, "agenda")
                        st.success("Reagendado")
                        st.rerun()
            with c2:
                if st.button("🛒 Renovar", key=f"ren{i}"):
                    st.session_state.p_renovar = r['Paciente']
                    st.info("Ve al menú Admisión")
            with c3:
                txt = urllib.parse.quote(f"Hola {r['Paciente']}, te recuerdo tu turno del {r['Fecha']} a las {r['Hora']}.")
                st.markdown(f' <a href="https://wa.me/{r.get("WhatsApp","")}?text={txt}" target="_blank"><button style="background:#25D366; color:white; border:none; padding:8px; width:100%; border-radius:10px; cursor:pointer;">WhatsApp</button></a>', unsafe_allow_html=True)

    with tab_h: mostrar_agenda(datetime.now().strftime("%Y-%m-%d"))
    with tab_m: mostrar_agenda((datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"))

# --- PANEL 2: ADMISIÓN ---
elif menu == "📝 Registro de Admisión":
    st.title("Consolidación de Pacientes")
    with st.form("form_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        n = col1.text_input("Nombre Completo", value=st.session_state.get('p_renovar', ''))
        d = col1.text_input("DNI / Cédula")
        w = col1.text_input("WhatsApp (Sin el +)")
        
        f_i = col2.date_input("Día de Inicio")
        h_f = col2.time_input("Hora fija")
        dias = col2.multiselect("Días de frecuencia", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])
        
        s = st.selectbox("Plan / Servicio", list(PRECIOS_BASE.keys()))
        o = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
        
        # Precio Inteligente
        p_base = PRECIOS_BASE[s]["Socio" if o == "Socio Gimnasio" else "Gral"] if "Masaje" in s else PRECIOS_BASE[s]
        pago_final = st.number_input("Monto a Cobrar ($)", value=float(p_base))
        
        if st.form_submit_button("CONSOLIDAR PLAN Y AGENDAR"):
            if n and d:
                cant = 10 if "x10" in s else (5 if "x5" in s else 1)
                
                # 1. Registro Paciente
                np = pd.DataFrame([{"DNI":d, "Nombre":n, "WhatsApp":w, "Origen":o, "Servicio":s, "Pago":pago_final, "Sesiones_Totales":cant, "Sesiones_Restantes":cant, "Fecha_Inicio":f_i.strftime("%Y-%m-%d")}])
                
                # 2. Generar Agenda Masiva
                d_map = {"Lunes":0,"Martes":1,"Miércoles":2,"Jueves":3,"Viernes":4,"Sábado":5}
                f_plan, curr = [], f_i
                while len(f_plan) < cant:
                    if not dias or curr.weekday() in [d_map[d_nom] for d_nom in dias]: f_plan.append(curr.strftime("%Y-%m-%d"))
                    curr += timedelta(days=1)
                
                na = pd.DataFrame([{"Fecha": f, "Hora": h_f.strftime("%H:%M"), "Paciente": n, "DNI": d, "WhatsApp": w, "Estado": "PENDIENTE"} for f in f_plan])
                
                guardar_datos(pd.concat([df_p, np], ignore_index=True), "pacientes")
                guardar_datos(pd.concat([df_a, na], ignore_index=True), "agenda")
                st.success("¡Operación exitosa! Plan consolidado.")
                st.rerun()

# --- PANEL 3: FINANZAS ---
elif menu == "📊 Finanzas & Auditoría":
    st.title("Centro de Inteligencia")
    c_f1, c_f2 = st.columns(2)
    desde = c_f1.date_input("Desde", datetime.now() - timedelta(days=30))
    hasta = c_f2.date_input("Hasta", datetime.now())
    
    df_p['Fecha_Inicio'] = pd.to_datetime(df_p['Fecha_Inicio'], errors='coerce')
    df_f = df_p[(df_p['Fecha_Inicio'].dt.date >= desde) & (df_p['Fecha_Inicio'].dt.date <= hasta)].copy()
    
    # Cálculos de Cesión 30/20
    df_f['% Cesión'] = df_f['Origen'].apply(lambda x: 0.30 if x == "Socio Gimnasio" else 0.20)
    df_f['Monto Cesión'] = df_f['Pago'] * df_f['% Cesión']
    df_f['Neto'] = df_f['Pago'] - df_f['Monto Cesión']
    
    bruto, total_c = df_f['Pago'].sum(), df_f['Monto Cesión'].sum()
    
    m1, m2, m3 = st.columns(3)
    with m1: st.markdown(f'<div class="metric-box"><h3>Bruto</h3><h2 style="color:{BRAND_GREEN}">${bruto:,.0f}</h2></div>', unsafe_allow_html=True)
    with m2: st.markdown(f'<div class="metric-box"><h3>Cesión</h3><h2 style="color:#e74c3c">-${total_c:,.0f}</h2></div>', unsafe_allow_html=True)
    with m3: st.markdown(f'<div class="metric-box"><h3>Utilidad</h3><h2>${bruto-total_c-gastos_fijos:,.0f}</h2></div>', unsafe_allow_html=True)

    st.subheader("Auditoría de Movimientos")
    st.dataframe(df_f[['Nombre', 'Origen', 'Pago', '% Cesión', 'Monto Cesión', 'Neto']], use_container_width=True)
    
    csv = df_f.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Descargar Auditoría para Excel", csv, "Reporte_Elite.csv", "text/csv")
