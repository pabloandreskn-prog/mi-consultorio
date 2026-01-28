import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import plotly.express as px
import urllib.parse

# --- 1. CONFIGURACIÓN Y ESTÉTICA ---
st.set_page_config(page_title="Elite System V29 - Financial Master", layout="wide", page_icon="🌿")

PRECIOS_BASE = {
    "Evaluacion": 36000, "Sesion Especializada": 36000, "Sesion Individual": 24000,
    "Plan x5": 110000, "Plan x10": 200000,
    "Masaje ZA": {"Socio": 25000, "Gral": 30000},
    "Masaje ZB": {"Socio": 25000, "Gral": 30000},
    "Masaje Completo": {"Socio": 38000, "Gral": 45000}
}

BRAND_GREEN = "#60b067"
DARK_CARD = "rgba(30, 30, 30, 0.95)"

st.markdown(f"""
    <style>
    .stApp {{ background-color: #FFFFFF; color: #1E1E1E; }}
    .turno-card {{
        background: {DARK_CARD}; border-left: 8px solid {BRAND_GREEN};
        padding: 20px; border-radius: 15px; margin-bottom: 5px; color: white;
    }}
    .metric-container {{
        background: #f8f9fa; padding: 20px; border-radius: 15px;
        border-top: 5px solid {BRAND_GREEN}; text-align: center;
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

# --- 3. MOTOR SMART-SYNC (EFECTO SUSANA) ---
def smart_sync():
    ahora = datetime.now()
    fecha_h = ahora.strftime("%Y-%m-%d")
    hora_h = ahora.strftime("%H:%M")
    
    mask = (df_a['Fecha'].astype(str) <= fecha_h) & (df_a['Hora'].astype(str) < hora_h) & (df_a['Estado'] != 'PROCESADO')
    pendientes = df_a[mask]
    
    if not pendientes.empty:
        df_p_act, df_a_act = df_p.copy(), df_a.copy()
        for idx_a, t in pendientes.iterrows():
            dni_p = str(t.get('DNI', ''))
            idx_p = df_p_act[df_p_act['DNI'].astype(str) == dni_p].index
            if not idx_p.empty:
                rest = df_p_act.at[idx_p[0], 'Sesiones_Restantes']
                df_p_act.at[idx_p[0], 'Sesiones_Restantes'] = max(0, rest - 1)
            df_a_act.at[idx_a, 'Estado'] = 'PROCESADO'
        guardar_datos(df_p_act, "pacientes")
        guardar_datos(df_a_act, "agenda")
        st.rerun()

# --- 4. NAVEGACIÓN ---
menu = st.sidebar.radio("SISTEMA ÉLITE V29", ["📅 Agenda Predictiva", "📝 Registro & Venta", "📊 Inteligencia Financiera"])
gastos_fijos = st.sidebar.number_input("Gastos Fijos Mensuales ($)", value=0)

# --- MÓDULO 1: AGENDA ---
if menu == "📅 Agenda Predictiva":
    smart_sync()
    st.title("Control de Turnos")
    
    with st.expander("🔍 CONSULTAR DISPONIBILIDAD (HUECOS)"):
        f_busq = st.date_input("Día:", datetime.now())
        ocupados = df_a[df_a['Fecha'].astype(str) == str(f_busq)]['Hora'].tolist()
        libres = [h for h in ["08:00","09:00","10:00","11:00","14:00","15:00","16:00","17:00","18:00","19:00"] if h not in ocupados]
        cols = st.columns(5)
        for i, h in enumerate(libres): cols[i%5].markdown(f'<div class="chip-libre">{h}</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Sesiones de Hoy", "Sesiones de Mañana"])
    
    def render_agenda(fecha_str):
        turnos = df_a[df_a['Fecha'].astype(str) == fecha_str].sort_values("Hora")
        if turnos.empty: st.info("No hay pacientes agendados para este día.")
        for i, t in turnos.iterrows():
            p_data = df_p[df_p['DNI'].astype(str) == str(t.get('DNI',''))]
            rest = int(p_data['Sesiones_Restantes'].iloc[0]) if not p_data.empty else 0
            
            st.markdown(f'<div class="turno-card"><b>{t["Hora"]} hs</b> | {t["Paciente"]} | <small>{t["Servicio"]}</small> | Saldo: {rest}</div>', unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                with st.popover("⚙️ Reagendar"):
                    st.date_input("Nueva Fecha", key=f"f_{i}")
                    st.time_input("Nueva Hora", key=f"h_{i}")
                    if st.button("Confirmar", key=f"save_{i}"): st.success("Actualizado")
            with c2:
                if st.button("🛒 Renovar", key=f"btn_ren_{i}"): st.info("Ir a Registro")
            with c3:
                msg = urllib.parse.quote(f"Hola {t['Paciente']}, te recuerdo tu turno hoy.")
                st.markdown(f'<a href="https://wa.me/{t.get("WhatsApp","")}?text={msg}" target="_blank"><button style="width:100%; background:#25D366; color:white; border:none; height:35px; border-radius:8px; cursor:pointer;">WhatsApp</button></a>', unsafe_allow_html=True)

    with tab1: render_agenda(datetime.now().strftime("%Y-%m-%d"))
    with tab2: render_agenda((datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"))

# --- MÓDULO 2: REGISTRO & VENTA ---
elif menu == "📝 Registro & Venta":
    st.title("Admisión y Consolidación")
    with st.form("form_master", clear_on_submit=True):
        col1, col2 = st.columns(2)
        nombre = col1.text_input("Nombre del Paciente")
        dni = col1.text_input("DNI")
        whats = col1.text_input("WhatsApp (ej: 549...)")
        
        f_ini = col2.date_input("Fecha Inicio", datetime.now())
        h_fija = col2.time_input("Hora Fija")
        dias = col2.multiselect("Días de frecuencia", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])
        
        serv = st.selectbox("Servicio / Plan", list(PRECIOS_BASE.keys()))
        orig = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
        
        # Lógica de precio automática
        ya_e = not df_p[df_p['DNI'].astype(str) == str(dni)].empty
        p_sug = PRECIOS_BASE[serv]["Socio" if orig == "Socio Gimnasio" else "Gral"] if "Masaje" in serv else PRECIOS_BASE[serv]
        if serv == "Evaluacion" and not ya_e: p_sug = 0 if orig == "Socio Gimnasio" else p_sug * 0.5
        
        st.write(f"### 💳 Pago Sugerido: ${p_sug:,.0f}")
        pago_final = st.number_input("Monto Cobrado ($)", value=float(p_sug))
        
        if st.form_submit_button("CONSOLIDAR REGISTRO"):
            if nombre and dni:
                cant = 10 if "x10" in serv else (5 if "x5" in serv else 1)
                # 1. Registro Paciente
                new_p = {c: "" for c in df_p.columns}
                new_p.update({"DNI": dni, "Nombre": nombre, "WhatsApp": whats, "Origen": orig, "Servicio": serv, "Pago": pago_final, "Sesiones_Totales": cant, "Sesiones_Restantes": cant})
                
                # 2. Registro Agenda Masiva
                d_map = {"Lunes":0, "Martes":1, "Miércoles":2, "Jueves":3, "Viernes":4, "Sábado":5}
                f_plan, curr = [], f_ini
                while len(f_plan) < cant:
                    if not dias or curr.weekday() in [d_map[d] for d in dias]: f_plan.append(curr.strftime("%Y-%m-%d"))
                    curr += timedelta(days=1)
                
                new_a_rows = []
                for f in f_plan:
                    row = {c: "" for c in df_a.columns}
                    row.update({"Fecha": f, "Hora": h_fija.strftime("%H:%M"), "Paciente": nombre, "Servicio": serv, "DNI": dni, "WhatsApp": whats, "Estado": "PENDIENTE"})
                    new_a_rows.append(row)
                
                guardar_datos(pd.concat([df_p, pd.DataFrame([new_p])], ignore_index=True), "pacientes")
                guardar_datos(pd.concat([df_a, pd.DataFrame(new_a_rows)], ignore_index=True), "agenda")
                st.success(f"Éxito: {nombre} registrado con {cant} sesiones.")
                st.rerun()

# --- MÓDULO 3: INTELIGENCIA FINANCIERA ---
elif menu == "📊 Inteligencia Financiera":
    st.title("Analítica de Rentabilidad")
    
    # FUNCIONALIDAD CLAVE: DESGLOSE DE COMISIONES
    df_p['Comis_Gimnasio'] = df_p.apply(lambda r: r['Pago'] * 0.3 if r['Origen'] == "Socio Gimnasio" else 0, axis=1)
    df_p['Comis_Propia'] = df_p.apply(lambda r: r['Pago'] * 0.2 if r['Origen'] == "Captación Propia" else 0, axis=1)
    
    bruto = df_p['Pago'].sum()
    total_comisiones = df_p['Comis_Gimnasio'].sum() + df_p['Comis_Propia'].sum()
    neta = bruto - total_comisiones - gastos_fijos

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ingreso Bruto", f"${bruto:,.0f}")
    c2.metric("Cedido Gimnasio", f"-${df_p['Comis_Gimnasio'].sum():,.0f}")
    c3.metric("Cedido Propio", f"-${df_p['Comis_Propia'].sum():,.0f}")
    c4.metric("UTILIDAD REAL", f"${neta:,.0f}")

    st.divider()
    col_l, col_r = st.columns(2)
    with col_l:
        # RENTABILIDAD POR DÍA
        df_a['Dia'] = pd.to_datetime(df_a['Fecha']).dt.day_name().map({"Monday":"Lunes","Tuesday":"Martes","Wednesday":"Miércoles","Thursday":"Jueves","Friday":"Viernes","Saturday":"Sábado"})
        rent_d = df_a.groupby('Dia').size().reset_index(name='Cant').sort_values('Cant', ascending=False)
        st.plotly_chart(px.bar(rent_d, x='Dia', y='Cant', title="Flujo de Sesiones por Día", color_discrete_sequence=[BRAND_GREEN]))
    with col_r:
        st.plotly_chart(px.pie(df_p, values='Pago', names='Origen', title="Distribución de Ingresos", hole=0.5))
