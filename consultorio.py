import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import urllib.parse

# --- 1. CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="Elite System V33 - Ultimate", layout="wide", page_icon="🌿")

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
        padding: 20px; border-radius: 15px; margin-bottom: 10px; color: white;
    }}
    .chip-libre {{
        background: rgba(96, 176, 103, 0.1); color: {BRAND_GREEN};
        padding: 8px; border-radius: 10px; border: 1px solid {BRAND_GREEN};
        font-weight: bold; text-align: center; margin-bottom: 5px;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN Y DATOS ---
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
    conn.update(worksheet=hoja, data=df)
    st.cache_data.clear()

# --- 3. MOTOR SMART-SYNC (DESCUENTO AUTO) ---
def smart_sync():
    ahora = datetime.now()
    fecha_h = ahora.strftime("%Y-%m-%d")
    hora_h = ahora.strftime("%H:%M")
    # Detectar turnos pasados no procesados
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

# --- 4. NAVEGACIÓN ---
menu = st.sidebar.radio("MENÚ PRINCIPAL", ["📅 Agenda Predictiva", "📝 Registro de Admisión", "📊 Inteligencia Financiera"])
gastos_fijos = st.sidebar.number_input("Gastos Fijos Mensuales ($)", value=0)

# --- MÓDULO AGENDA ---
if menu == "📅 Agenda Predictiva":
    smart_sync()
    st.title("Control de Turnos")
    
    with st.expander("🔍 CONSULTAR DISPONIBILIDAD (HUECOS)"):
        f_busq = st.date_input("Día:", datetime.now())
        ocupados = df_a[df_a['Fecha'].astype(str) == str(f_busq)]['Hora'].tolist()
        libres = [h for h in ["08:00","09:00","10:00","11:00","14:00","15:00","16:00","17:00","18:00","19:00"] if h not in ocupados]
        cols = st.columns(5)
        for i, h in enumerate(libres):
            cols[i%5].markdown(f'<div class="chip-libre">{h}</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Sesiones de Hoy", "Sesiones de Mañana"])
    
    def render_agenda(fecha_str):
        turnos = df_a[df_a['Fecha'].astype(str) == fecha_str].sort_values("Hora")
        if turnos.empty: st.info("No hay turnos para este día.")
        for i, t in turnos.iterrows():
            p_data = df_p[df_p['DNI'].astype(str) == str(t.get('DNI',''))]
            rest = int(p_data['Sesiones_Restantes'].iloc[0]) if not p_data.empty else 0
            
            st.markdown(f'<div class="turno-card"><b>{t["Hora"]} hs</b> | {t["Paciente"]} | Saldo: {rest}</div>', unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                with st.popover("⚙️ Reagendar"):
                    st.date_input("Nueva Fecha", key=f"f_{i}")
                    st.button("Confirmar", key=f"b_{i}")
            with c2:
                if st.button("🛒 Renovar", key=f"ren_{i}"): st.info("Ir a Registro")
            with c3:
                msg = urllib.parse.quote(f"Hola {t['Paciente']}, recordatorio de turno en Elite.")
                st.markdown(f'<a href="https://wa.me/{t.get("WhatsApp","")}?text={msg}" target="_blank"><button style="width:100%; background:#25D366; color:white; border:none; height:35px; border-radius:8px;">WhatsApp</button></a>', unsafe_allow_html=True)

    with tab1: render_agenda(datetime.now().strftime("%Y-%m-%d"))
    with tab2: render_agenda((datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"))

# --- MÓDULO REGISTRO ---
elif menu == "📝 Registro de Admisión":
    st.title("Registro y Consolidación de Planes")
    with st.form("form_ultimate", clear_on_submit=True):
        col1, col2 = st.columns(2)
        nombre = col1.text_input("Nombre Completo")
        dni = col1.text_input("DNI")
        whats = col1.text_input("WhatsApp (549...)")
        
        f_ini = col2.date_input("Fecha Inicio", datetime.now())
        h_fija = col2.time_input("Hora del Turno")
        dias = col2.multiselect("Días de la semana", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])
        
        servicio = st.selectbox("Servicio / Plan", list(PRECIOS_BASE.keys()))
        origen = st.selectbox("Origen del Paciente", ["Socio Gimnasio", "Captación Propia"])
        
        # Lógica de Precio
        ya_ev = not df_p[df_p['DNI'].astype(str) == str(dni)].empty
        p_sug = PRECIOS_BASE[servicio]["Socio" if origen == "Socio Gimnasio" else "Gral"] if "Masaje" in servicio else PRECIOS_BASE[servicio]
        if servicio == "Evaluacion" and not ya_ev:
            p_sug = 0 if origen == "Socio Gimnasio" else p_sug * 0.5
        
        st.write(f"### 💳 Pago Sugerido: ${p_sug:,.0f}")
        pago_final = st.number_input("Monto Recibido ($)", value=float(p_sug))
        
        if st.form_submit_button("CONSOLIDAR PLAN"):
            if nombre and dni:
                cant = 10 if "x10" in servicio else (5 if "x5" in servicio else 1)
                
                # 1. Registro Paciente (Blindado)
                new_p = {c: "" for c in df_p.columns}
                new_p.update({
                    "DNI": dni, "Nombre": nombre, "WhatsApp": whats, "Origen": origen, 
                    "Servicio": servicio, "Pago": pago_final, "Sesiones_Totales": cant, 
                    "Sesiones_Restantes": cant, "Fecha_Inicio": f_ini.strftime("%Y-%m-%d")
                })
                
                # 2. Registro Agenda Masiva
                d_map = {"Lunes":0, "Martes":1, "Miércoles":2, "Jueves":3, "Viernes":4, "Sábado":5}
                f_plan, curr = [], f_ini
                while len(f_plan) < cant:
                    if not dias or curr.weekday() in [d_map[d] for d in dias]:
                        f_plan.append(curr.strftime("%Y-%m-%d"))
                    curr += timedelta(days=1)
                
                new_a_rows = []
                for f in f_plan:
                    row = {c: "" for c in df_a.columns}
                    row.update({
                        "Fecha": f, "Hora": h_fija.strftime("%H:%M"), "Paciente": nombre, 
                        "Servicio": servicio, "DNI": dni, "WhatsApp": whats, "Estado": "PENDIENTE"
                    })
                    new_a_rows.append(row)
                
                guardar_datos(pd.concat([df_p, pd.DataFrame([new_p])], ignore_index=True), "pacientes")
                guardar_datos(pd.concat([df_a, pd.DataFrame(new_a_rows)], ignore_index=True), "agenda")
                st.success(f"¡Éxito! Plan de {cant} sesiones agendado.")
                st.rerun()

# --- MÓDULO INTELIGENCIA ---
elif menu == "📊 Inteligencia Financiera":
    st.title("Análisis de Rentabilidad y Auditoría")
    
    # Filtro de Fechas
    c_f1, c_f2 = st.columns(2)
    f_desde = c_f1.date_input("Desde", datetime.now() - timedelta(days=30))
    f_hasta = c_f2.date_input("Hasta", datetime.now())
    
    df_p['Fecha_Inicio'] = pd.to_datetime(df_p['Fecha_Inicio'], errors='coerce')
    mask = (df_p['Fecha_Inicio'].dt.date >= f_desde) & (df_p['Fecha_Inicio'].dt.date <= f_hasta)
    df_filtrado = df_p[mask].copy()

    # Cálculos de Cesión (30% Socio / 20% Propio)
    df_filtrado['% Cesión'] = df_filtrado['Origen'].apply(lambda x: 0.30 if x == "Socio Gimnasio" else 0.20)
    df_filtrado['Monto Cesión'] = df_filtrado['Pago'] * df_filtrado['% Cesión']
    df_filtrado['Ingreso Neto'] = df_filtrado['Pago'] - df_filtrado['Monto Cesión']
    
    bruto = df_filtrado['Pago'].sum()
    total_cesion = df_filtrado['Monto Cesión'].sum()
    neta = bruto - total_cesion - gastos_fijos

    c1, c2, c3 = st.columns(3)
    c1.metric("Ingresos Totales", f"${bruto:,.0f}")
    c2.metric("Total Cesiones", f"-${total_cesion:,.0f}")
    c3.metric("Utilidad Final", f"${neta:,.0f}")

    st.divider()
    st.subheader("Base de Datos Histórica")
    st.dataframe(df_filtrado[['DNI', 'Nombre', 'Origen', 'Servicio', 'Pago', '% Cesión', 'Monto Cesión', 'Ingreso Neto']], use_container_width=True)
    
    # Exportación Segura a CSV
    csv = df_filtrado.to_csv(index=False).encode('utf-8')
    st.download_button(label="📥 Descargar Reporte (Excel/CSV)", data=csv, file_name=f"Reporte_Elite_{f_desde}.csv", mime='text/csv')

    st.divider()
    # Gráfico de flujo
    df_a['Dia'] = pd.to_datetime(df_a['Fecha']).dt.day_name().map({"Monday":"Lunes","Tuesday":"Martes","Wednesday":"Miércoles","Thursday":"Jueves","Friday":"Viernes","Saturday":"Sábado"})
    rent = df_a.groupby('Dia').size().reset_index(name='Sesiones')
    st.plotly_chart(px.bar(rent, x='Dia', y='Sesiones', title="Sesiones por Día de la Semana", color_discrete_sequence=[BRAND_GREEN]))
