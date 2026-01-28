import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import plotly.express as px

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Elite System V27 - Precision", layout="wide", page_icon="🌿")

PRECIOS_BASE = {
    "Evaluacion": 36000, "Sesion Especializada": 36000, "Sesion Individual": 24000,
    "Plan x5": 110000, "Plan x10": 200000,
    "Masaje ZA": {"Socio": 25000, "Gral": 30000},
    "Masaje ZB": {"Socio": 25000, "Gral": 30000},
    "Masaje Completo": {"Socio": 38000, "Gral": 45000}
}

BRAND_GREEN = "#60b067"

# --- 2. CONEXIÓN Y CARGA ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    df_p = conn.read(worksheet="pacientes", ttl="0").dropna(how='all')
    df_a = conn.read(worksheet="agenda", ttl="0").dropna(how='all')
    return df_p, df_a

df_p, df_a = cargar_datos()

def guardar_datos(df, hoja):
    conn.update(worksheet=hoja, data=df)
    st.cache_data.clear()

# --- 3. LÓGICA DE NEGOCIO ---
def smart_sync():
    ahora = datetime.now()
    fecha_h = ahora.strftime("%Y-%m-%d")
    hora_h = ahora.strftime("%H:%M")
    mask = (df_a['Fecha'].astype(str) <= fecha_h) & (df_a['Hora'].astype(str) < hora_h) & (df_a.get('Estado', '') != 'PROCESADO')
    if not df_a[mask].empty:
        df_p_act = df_p.copy()
        df_a_act = df_a.copy()
        for idx, t in df_a[mask].iterrows():
            dni = str(t.get('DNI', ''))
            p_idx = df_p_act[df_p_act['DNI'].astype(str) == dni].index
            if not p_idx.empty:
                df_p_act.at[p_idx[0], 'Sesiones_Restantes'] = max(0, float(df_p_act.at[p_idx[0], 'Sesiones_Restantes']) - 1)
            df_a_act.at[idx, 'Estado'] = 'PROCESADO'
        guardar_datos(df_p_act, "pacientes")
        guardar_datos(df_a_act, "agenda")
        st.rerun()

# --- 4. INTERFAZ ---
with st.sidebar:
    st.title("🌿 ELITE SYSTEM")
    menu = st.radio("MENÚ", ["📅 Agenda", "📝 Registro & Cobro", "📊 Inteligencia"])
    gastos_f = st.number_input("Gastos Fijos ($)", value=0)

if menu == "📅 Agenda":
    smart_sync()
    st.title("Agenda de Turnos")
    
    with st.expander("🔍 DISPONIBILIDAD"):
        f_b = st.date_input("Día:", datetime.now())
        ocup = df_a[df_a['Fecha'].astype(str) == str(f_b)]['Hora'].tolist()
        libres = [h for h in ["08:00","09:00","10:00","11:00","14:00","15:00","16:00","17:00","18:00"] if h not in ocup]
        st.write("Libres:", libres)

    t1, t2 = st.tabs(["Hoy", "Mañana"])
    def ver_agenda(f):
        res = df_a[df_a['Fecha'].astype(str) == f].sort_values("Hora")
        for i, r in res.iterrows():
            with st.container(border=True):
                st.write(f"**{r['Hora']} hs** | {r['Paciente']} ({r['Servicio']})")
                c1, c2 = st.columns(2)
                if c1.button("⚙️ Reagendar", key=f"re_{i}"):
                    st.info("Función de cambio de fecha habilitada en base de datos.")
                if c2.button("📱 WhatsApp", key=f"wa_{i}"):
                    st.write(f"Abriendo chat con {r.get('WhatsApp', '...')}")

    with t1: ver_agenda(datetime.now().strftime("%Y-%m-%d"))
    with t2: ver_agenda((datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"))

elif menu == "📝 Registro & Cobro":
    st.title("Nuevo Registro")
    with st.form("form_registro"):
        c1, c2 = st.columns(2)
        nombre = c1.text_input("Nombre")
        dni = c1.text_input("DNI")
        whats = c1.text_input("WhatsApp")
        f_ini = c2.date_input("Fecha Inicio")
        h_ini = c2.time_input("Hora")
        dias = c2.multiselect("Días fijos", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"])
        serv = st.selectbox("Servicio", list(PRECIOS_BASE.keys()))
        orig = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
        
        # Cálculo de precio sugerido
        p_sug = PRECIOS_BASE[serv]["Socio" if orig == "Socio Gimnasio" else "Gral"] if "Masaje" in serv else PRECIOS_BASE[serv]
        st.subheader(f"Total Sugerido: ${p_sug:,.0f}")
        pago = st.number_input("Confirmar Monto ($)", value=float(p_sug))
        
        if st.form_submit_button("CONSOLIDAR PLAN"):
            if nombre and dni:
                cant = 10 if "x10" in serv else (5 if "x5" in serv else 1)
                
                # Crear registro de Paciente
                new_p = {col: "" for col in df_p.columns}
                new_p.update({"DNI": dni, "Nombre": nombre, "WhatsApp": whats, "Origen": orig, "Servicio": serv, "Pago": pago, "Sesiones_Totales": cant, "Sesiones_Restantes": cant})
                
                # Crear registros de Agenda (Lógica de fechas)
                d_map = {"Lunes":0, "Martes":1, "Miércoles":2, "Jueves":3, "Viernes":4}
                f_plan, curr = [], f_ini
                while len(f_plan) < cant:
                    if not dias or curr.weekday() in [d_map[d] for d in dias]: f_plan.append(curr.strftime("%Y-%m-%d"))
                    curr += timedelta(days=1)
                
                new_agenda_rows = []
                for f in f_plan:
                    row = {col: "" for col in df_a.columns}
                    row.update({"Fecha": f, "Hora": h_ini.strftime("%H:%M"), "Paciente": nombre, "Servicio": serv, "DNI": dni, "WhatsApp": whats, "Estado": "PENDIENTE"})
                    new_agenda_rows.append(row)
                
                # Guardado masivo
                df_p_final = pd.concat([df_p, pd.DataFrame([new_p])], ignore_index=True)
                df_a_final = pd.concat([df_a, pd.DataFrame(new_agenda_rows)], ignore_index=True)
                
                guardar_datos(df_p_final, "pacientes")
                guardar_datos(df_a_final, "agenda")
                st.success("Plan grabado con éxito.")
                st.rerun()

elif menu == "📊 Inteligencia":
    st.title("Rendimiento")
    df_p['Comis'] = df_p.apply(lambda r: float(r['Pago']) * 0.3 if r['Origen'] == "Socio Gimnasio" else float(r['Pago']) * 0.2, axis=1)
    bruto = df_p['Pago'].sum()
    neta = bruto - df_p['Comis'].sum() - gastos_f
    
    st.metric("Utilidad Neta Actual", f"${neta:,.0f}")
    
    # Gráfico de rentabilidad por día
    df_a['Dia'] = pd.to_datetime(df_a['Fecha']).dt.day_name()
    rent = df_a.groupby('Dia').size().reset_index(name='Turnos')
    st.plotly_chart(px.bar(rent, x='Dia', y='Turnos', title="Sesiones por Día", color_discrete_sequence=[BRAND_GREEN]))
