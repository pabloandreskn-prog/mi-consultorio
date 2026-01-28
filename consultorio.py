import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import plotly.express as px
import urllib.parse

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Elite System V30 - Legacy", layout="wide", page_icon="🌿")

PRECIOS_BASE = {
    "Evaluacion": 36000, "Sesion Especializada": 36000, "Sesion Individual": 24000,
    "Plan x5": 110000, "Plan x10": 200000,
    "Masaje ZA": {"Socio": 25000, "Gral": 30000},
    "Masaje ZB": {"Socio": 25000, "Gral": 30000},
    "Masaje Completo": {"Socio": 38000, "Gral": 45000}
}

BRAND_GREEN = "#60b067"

# --- 2. CONEXIÓN ---
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

# --- 3. MOTOR SMART-SYNC ---
def smart_sync():
    ahora = datetime.now()
    fecha_h = ahora.strftime("%Y-%m-%d")
    hora_h = ahora.strftime("%H:%M")
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
menu = st.sidebar.radio("SISTEMA ÉLITE", ["📅 Agenda", "📝 Registro", "📊 Inteligencia Financiera"])
gastos_f = st.sidebar.number_input("Gastos Fijos ($)", value=0)

if menu == "📅 Agenda":
    smart_sync()
    st.title("Agenda de Turnos")
    t1, t2 = st.tabs(["Hoy", "Mañana"])
    def ver(f):
        res = df_a[df_a['Fecha'].astype(str) == f].sort_values("Hora")
        for i, r in res.iterrows():
            with st.container(border=True):
                st.write(f"**{r['Hora']} hs** | {r['Paciente']} | Saldo: {df_p[df_p['DNI'].astype(str)==str(r['DNI'])]['Sesiones_Restantes'].iloc[0] if not df_p[df_p['DNI'].astype(str)==str(r['DNI'])].empty else 0}")
                with st.popover("Acciones"):
                    st.date_input("Nueva Fecha", key=f"f_{i}")
                    if st.button("WhatsApp", key=f"w_{i}"): st.write("Abriendo...")

    with t1: ver(datetime.now().strftime("%Y-%m-%d"))
    with tab2: ver((datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"))

elif menu == "📝 Registro":
    st.title("Nuevo Plan / Paciente")
    with st.form("master_form"):
        c1, c2 = st.columns(2)
        nom = c1.text_input("Nombre")
        dni = c1.text_input("DNI")
        tel = c1.text_input("WhatsApp")
        f_i = c2.date_input("Inicio")
        h_i = c2.time_input("Hora")
        dias = c2.multiselect("Días", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"])
        serv = st.selectbox("Servicio", list(PRECIOS_BASE.keys()))
        orig = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
        
        ya_e = not df_p[df_p['DNI'].astype(str) == str(dni)].empty
        p_sug = PRECIOS_BASE[serv]["Socio" if orig=="Socio Gimnasio" else "Gral"] if "Masaje" in serv else PRECIOS_BASE[serv]
        if serv == "Evaluacion" and not ya_e: p_sug = 0 if orig=="Socio Gimnasio" else p_sug * 0.5
        
        st.write(f"### Total Sugerido: ${p_sug:,.0f}")
        pago = st.number_input("Pago Final", value=float(p_sug))
        
        if st.form_submit_button("CONSOLIDAR"):
            if nom and dni:
                cant = 10 if "x10" in serv else (5 if "x5" in serv else 1)
                # Registro Paciente
                new_p = {c: "" for c in df_p.columns}
                new_p.update({"DNI": dni, "Nombre": nom, "WhatsApp": tel, "Origen": orig, "Servicio": serv, "Pago": pago, "Sesiones_Totales": cant, "Sesiones_Restantes": cant})
                # Agenda
                d_map = {"Lunes":0, "Martes":1, "Miércoles":2, "Jueves":3, "Viernes":4}
                f_plan, curr = [], f_i
                while len(f_plan) < cant:
                    if not dias or curr.weekday() in [d_map[d] for d in dias]: f_plan.append(curr.strftime("%Y-%m-%d"))
                    curr += timedelta(days=1)
                new_a = []
                for f in f_plan:
                    row = {c: "" for c in df_a.columns}; row.update({"Fecha": f, "Hora": h_i.strftime("%H:%M"), "Paciente": nom, "Servicio": serv, "DNI": dni, "WhatsApp": tel, "Estado": "PENDIENTE"})
                    new_a.append(row)
                
                guardar_datos(pd.concat([df_p, pd.DataFrame([new_p])], ignore_index=True), "pacientes")
                guardar_datos(pd.concat([df_a, pd.DataFrame(new_a)], ignore_index=True), "agenda")
                st.success("Grabado")
                st.rerun()

elif menu == "📊 Inteligencia Financiera":
    st.title("Impacto Financiero")
    
    # CÁLCULOS DE CESIÓN
    df_p['% Cesión'] = df_p['Origen'].apply(lambda x: 0.30 if x == "Socio Gimnasio" else 0.20)
    df_p['Monto Cesión'] = df_p['Pago'] * df_p['% Cesión']
    df_p['Ingreso Neto'] = df_p['Pago'] - df_p['Monto Cesión']
    
    bruto = df_p['Pago'].sum()
    total_cesion = df_p['Monto Cesión'].sum()
    neta_total = bruto - total_cesion - gastos_f
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Ingresos Totales", f"${bruto:,.0f}")
    c2.metric("Inversión en Bonos (Cesión)", f"${total_cesion:,.0f}")
    c3.metric("Utilidad Final", f"${neta_total:,.0f}")

    st.divider()
    st.subheader("Base de Datos Histórica con Cesiones")
    # Mostramos la tabla tal cual estaba en tu captura pero con las nuevas columnas
    st.dataframe(df_p[['DNI', 'Nombre', 'Origen', 'Servicio', 'Pago', '% Cesión', 'Monto Cesión', 'Ingreso Neto']], use_container_width=True)

    st.divider()
    # Gráfico de flujo por día
    df_a['Dia'] = pd.to_datetime(df_a['Fecha']).dt.day_name().map({"Monday":"Lunes","Tuesday":"Martes","Wednesday":"Miércoles","Thursday":"Jueves","Friday":"Viernes"})
    st.plotly_chart(px.bar(df_a.groupby('Dia').size().reset_index(name='Cant'), x='Dia', y='Cant', title="Flujo por Día", color_discrete_sequence=[BRAND_GREEN]))
