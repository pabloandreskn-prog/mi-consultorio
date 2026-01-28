import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import urllib.parse

# --- 1. CONFIGURACIÓN Y ESTÉTICA ---
st.set_page_config(page_title="Elite System V34 - Masterpiece", layout="wide", page_icon="🌿")

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
    .stApp {{ background-color: #FFFFFF; }}
    .turno-card {{
        background: rgba(30, 30, 30, 0.95); border-left: 8px solid {BRAND_GREEN};
        padding: 20px; border-radius: 15px; margin-bottom: 10px; color: white;
    }}
    .chip-libre {{
        background: rgba(96, 176, 103, 0.1); color: {BRAND_GREEN};
        padding: 8px; border-radius: 10px; border: 1px solid {BRAND_GREEN};
        font-weight: bold; text-align: center; margin-bottom: 5px;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. GESTIÓN DE DATOS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    df_p = conn.read(worksheet="pacientes", ttl="0").dropna(how='all')
    df_a = conn.read(worksheet="agenda", ttl="0").dropna(how='all')
    for col in ['Pago', 'Sesiones_Restantes', 'Sesiones_Totales']:
        if col in df_p.columns:
            df_p[col] = pd.to_numeric(df_p[col], errors='coerce').fillna(0)
    return df_p, df_a

df_p, df_a = cargar_datos()

def guardar_datos(df, hoja):
    # Alineación dinámica de columnas: Evita el ValueError de tus capturas
    try:
        df_actual = conn.read(worksheet=hoja, ttl="0")
        cols_reales = df_actual.columns.tolist()
        # Creamos un DataFrame que tenga exactamente las mismas columnas que el Excel
        df_final = pd.DataFrame(columns=cols_reales)
        df_final = pd.concat([df_final, df], join='inner', ignore_index=True)
        conn.update(worksheet=hoja, data=df_final)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Error al grabar: {e}")

# --- 3. MOTOR SMART-SYNC (EFECTO SUSANA) ---
def smart_sync():
    ahora = datetime.now()
    fecha_h = ahora.strftime("%Y-%m-%d")
    hora_h = ahora.strftime("%H:%M")
    # Detectar turnos que ya pasaron y no fueron procesados
    mask = (df_a['Fecha'].astype(str) <= fecha_h) & (df_a['Hora'].astype(str) < hora_h) & (df_a.get('Estado', '') != 'PROCESADO')
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

# --- 4. INTERFAZ ---
menu = st.sidebar.radio("SISTEMA ÉLITE V34", ["📅 Agenda Predictiva", "📝 Registro de Admisión", "📊 Inteligencia Financiera"])
gastos_f = st.sidebar.number_input("Gastos Fijos Mensuales ($)", value=0)

if menu == "📅 Agenda Predictiva":
    smart_sync()
    st.title("Control de Turnos")
    
    with st.expander("🔍 CONSULTAR DISPONIBILIDAD"):
        f_b = st.date_input("Día:", datetime.now())
        ocup = df_a[df_a['Fecha'].astype(str) == str(f_b)]['Hora'].tolist()
        libres = [h for h in ["08:00","09:00","10:00","11:00","14:00","15:00","16:00","17:00","18:00","19:00"] if h not in ocup]
        cols = st.columns(5)
        for i, h in enumerate(libres): cols[i%5].markdown(f'<div class="chip-libre">{h}</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Sesiones de Hoy", "Sesiones de Mañana"])
    def render(f):
        res = df_a[df_a['Fecha'].astype(str) == f].sort_values("Hora")
        if res.empty: st.info("No hay turnos registrados.")
        for i, r in res.iterrows():
            p_d = df_p[df_p['DNI'].astype(str) == str(r['DNI'])]
            rest = int(p_d['Sesiones_Restantes'].iloc[0]) if not p_d.empty else 0
            
            with st.container():
                st.markdown(f'<div class="turno-card"><b>{r["Hora"]} hs</b> | {r["Paciente"]} | Saldo: {rest}</div>', unsafe_allow_html=True)
                c1, c2, c3 = st.columns(3)
                with c1:
                    with st.popover("⚙️ Reagendar"):
                        nueva_f = st.date_input("Nueva Fecha", key=f"nf_{i}")
                        nueva_h = st.time_input("Nueva Hora", key=f"nh_{i}")
                        if st.button("Confirmar Cambio", key=f"btn_s_{i}"):
                            df_a.at[i, 'Fecha'] = nueva_f.strftime("%Y-%m-%d")
                            df_a.at[i, 'Hora'] = nueva_h.strftime("%H:%M")
                            guardar_datos(df_a, "agenda")
                            st.success("¡Fecha actualizada!")
                            st.rerun()
                with c2:
                    if st.button("🛒 Renovar", key=f"renov_{i}"):
                        st.session_state.paciente_renovar = r['Paciente']
                        st.info(f"Carga el nuevo plan para {r['Paciente']} en Registro.")
                with c3:
                    msg = urllib.parse.quote(f"Hola {r['Paciente']}, te recuerdo tu turno en Elite.")
                    st.markdown(f'<a href="https://wa.me/{r.get("WhatsApp","")}?text={msg}" target="_blank"><button style="width:100%; background:#25D366; color:white; border:none; height:35px; border-radius:8px; cursor:pointer;">WhatsApp</button></a>', unsafe_allow_html=True)

    with tab1: render(datetime.now().strftime("%Y-%m-%d"))
    with tab2: render((datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"))

elif menu == "📝 Registro de Admisión":
    st.title("Admisión y Consolidación de Planes")
    with st.form("form_v34_final", clear_on_submit=True):
        c1, c2 = st.columns(2)
        nom = c1.text_input("Nombre Completo", value=st.session_state.get('paciente_renovar', ''))
        dni = c1.text_input("DNI")
        tel = c1.text_input("WhatsApp (549...)")
        f_ini = c2.date_input("Fecha Inicio", datetime.now())
        h_fija = c2.time_input("Hora del Turno")
        dias = c2.multiselect("Días de frecuencia", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])
        serv = st.selectbox("Servicio / Plan", list(PRECIOS_BASE.keys()))
        orig = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
        
        ya_ex = not df_p[df_p['DNI'].astype(str) == str(dni)].empty
        p_sug = PRECIOS_BASE[serv]["Socio" if orig=="Socio Gimnasio" else "Gral"] if "Masaje" in serv else PRECIOS_BASE[serv]
        if serv == "Evaluacion" and not ya_ex: p_sug = 0 if orig=="Socio Gimnasio" else p_sug * 0.5
        pago = st.number_input("Monto Cobrado ($)", value=float(p_sug))
        
        if st.form_submit_button("CONSOLIDAR PLAN Y AGENDAR"):
            if nom and dni:
                cant = 10 if "x10" in serv else (5 if "x5" in serv else 1)
                # 1. Crear Paciente
                new_p = pd.DataFrame([{ "DNI": dni, "Nombre": nom, "WhatsApp": tel, "Origen": orig, "Servicio": serv, "Pago": pago, "Sesiones_Totales": cant, "Sesiones_Restantes": cant, "Fecha_Inicio": f_ini.strftime("%Y-%m-%d") }])
                # 2. Crear Agenda Masiva
                d_map = {"Lunes":0,"Martes":1,"Miércoles":2,"Jueves":3,"Viernes":4,"Sábado":5}
                f_plan, curr = [], f_ini
                while len(f_plan) < cant:
                    if not dias or curr.weekday() in [d_map[d] for d in dias]: f_plan.append(curr.strftime("%Y-%m-%d"))
                    curr += timedelta(days=1)
                new_a = pd.DataFrame([{ "Fecha": f, "Hora": h_fija.strftime("%H:%M"), "Paciente": nom, "Servicio": serv, "DNI": dni, "WhatsApp": tel, "Estado": "PENDIENTE" } for f in f_plan])
                
                guardar_datos(pd.concat([df_p, new_p], ignore_index=True), "pacientes")
                guardar_datos(pd.concat([df_a, new_a], ignore_index=True), "agenda")
                st.success(f"¡Éxito! {nom} registrado con {cant} sesiones.")
                if 'paciente_renovar' in st.session_state: del st.session_state.paciente_renovar
                st.rerun()

elif menu == "📊 Inteligencia Financiera":
    st.title("Reporte de Rentabilidad")
    
    c_f1, c_f2 = st.columns(2)
    f_d = c_f1.date_input("Desde", datetime.now() - timedelta(days=30))
    f_h = c_f2.date_input("Hasta", datetime.now())
    
    # Filtrado dinámico
    if 'Fecha_Inicio' in df_p.columns:
        df_p['Fecha_Inicio'] = pd.to_datetime(df_p['Fecha_Inicio'], errors='coerce')
        df_hist = df_p[(df_p['Fecha_Inicio'].dt.date >= f_d) & (df_p['Fecha_Inicio'].dt.date <= f_h)].copy()
    else:
        df_hist = df_p.copy()

    # Cálculos Financieros (Solicitados)
    df_hist['% Cesión'] = df_hist['Origen'].apply(lambda x: 0.30 if x == "Socio Gimnasio" else 0.20)
    df_hist['Monto Cesión'] = df_hist['Pago'] * df_hist['% Cesión']
    df_hist['Ingreso Neto'] = df_hist['Pago'] - df_hist['Monto Cesión']
    
    bruto = df_hist['Pago'].sum()
    cesion = df_hist['Monto Cesión'].sum()
    neta = bruto - cesion - gastos_f

    c1, c2, c3 = st.columns(3)
    c1.metric("Ingresos Brutos", f"${bruto:,.0f}")
    c2.metric("Total Cesiones (Gimnasio/Propio)", f"-${cesion:,.0f}")
    c3.metric("Utilidad Neta", f"${neta:,.0f}")

    st.divider()
    st.subheader("Base de Datos Histórica")
    st.dataframe(df_hist[['DNI', 'Nombre', 'Origen', 'Servicio', 'Pago', '% Cesión', 'Monto Cesión', 'Ingreso Neto']], use_container_width=True)
    
    # Botón de Descarga Seguro
    csv = df_hist.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Exportar Reporte para Excel", data=csv, file_name=f"Elite_Report_{f_d}.csv", mime='text/csv')

    st.divider()
    # Flujo por día
    df_a['Dia'] = pd.to_datetime(df_a['Fecha']).dt.day_name().map({"Monday":"Lunes","Tuesday":"Martes","Wednesday":"Miércoles","Thursday":"Jueves","Friday":"Viernes","Saturday":"Sábado"})
    rent = df_a.groupby('Dia').size().reset_index(name='Sesiones')
    st.plotly_chart(px.bar(rent, x='Dia', y='Sesiones', title="Días con Mayor Volumen de Pacientes", color_discrete_sequence=[BRAND_GREEN]))
