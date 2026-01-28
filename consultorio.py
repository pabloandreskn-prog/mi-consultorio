import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import plotly.express as px
import urllib.parse
from fpdf import FPDF
import base64

# --- 1. CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="Elite System V32 Omega", layout="wide", page_icon="🌿")

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
    .chip-libre {{
        background: rgba(96, 176, 103, 0.1); color: {BRAND_GREEN};
        padding: 8px; border-radius: 10px; border: 1px solid {BRAND_GREEN};
        font-weight: bold; text-align: center; margin-bottom: 5px;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN Y PERSISTENCIA ---
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

# --- 3. FUNCIONES DE EXPORTACIÓN (PDF) ---
def create_pdf(df, bruto, cesion, neta):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, "Reporte Financiero - Elite System", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.ln(10)
    pdf.cell(200, 10, f"Ingreso Bruto: ${bruto:,.0f}", ln=True)
    pdf.cell(200, 10, f"Total Cesiones: ${cesion:,.0f}", ln=True)
    pdf.cell(200, 10, f"Utilidad Neta: ${neta:,.0f}", ln=True)
    pdf.ln(10)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(40, 10, "Paciente", 1); pdf.cell(30, 10, "Origen", 1); pdf.cell(30, 10, "Pago", 1); pdf.cell(30, 10, "Cesion", 1); pdf.cell(30, 10, "Neto", 1)
    pdf.ln()
    pdf.set_font("Arial", "", 9)
    for _, row in df.iterrows():
        pdf.cell(40, 10, str(row['Nombre'])[:15], 1)
        pdf.cell(30, 10, str(row['Origen']), 1)
        pdf.cell(30, 10, f"{row['Pago']:.0f}", 1)
        pdf.cell(30, 10, f"{row['Monto Cesión']:.0f}", 1)
        pdf.cell(30, 10, f"{row['Ingreso Neto']:.0f}", 1)
        pdf.ln()
    return pdf.output(dest="S").encode("latin-1")

# --- 4. MOTOR SMART-SYNC ---
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
        guardar_datos(df_p_act, "pacientes"); guardar_datos(df_a_act, "agenda")
        st.rerun()

# --- 5. INTERFAZ PRINCIPAL ---
menu = st.sidebar.radio("SISTEMA ÉLITE V32", ["📅 Agenda Predictiva", "📝 Registro & Masivos", "📊 Inteligencia & PDF"])
gastos_f = st.sidebar.number_input("Gastos Fijos ($)", value=0)

if menu == "📅 Agenda Predictiva":
    smart_sync()
    st.title("Gestión de Turnos")
    with st.expander("🔍 CONSULTAR HUECOS LIBRES"):
        f_b = st.date_input("Día:", datetime.now())
        ocup = df_a[df_a['Fecha'].astype(str) == str(f_b)]['Hora'].tolist()
        libres = [h for h in ["08:00","09:00","10:00","11:00","14:00","15:00","16:00","17:00","18:00","19:00"] if h not in ocup]
        cols = st.columns(5); [cols[i%5].markdown(f'<div class="chip-libre">{h}</div>', unsafe_allow_html=True) for i, h in enumerate(libres)]

    t1, t2 = st.tabs(["Hoy", "Mañana"])
    def render(f):
        res = df_a[df_a['Fecha'].astype(str) == f].sort_values("Hora")
        if res.empty: st.info("No hay turnos.")
        for i, r in res.iterrows():
            p_d = df_p[df_p['DNI'].astype(str)==str(r['DNI'])]
            rest = int(p_d['Sesiones_Restantes'].iloc[0]) if not p_d.empty else 0
            st.markdown(f'<div class="turno-card"><b>{r["Hora"]} hs</b> | {r["Paciente"]} | Saldo: {rest}</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1: 
                with st.popover("⚙️ Reagendar"):
                    st.date_input("Nueva Fecha", key=f"f_{i}"); st.button("Guardar", key=f"b_{i}")
            with c2:
                msg = urllib.parse.quote(f"Hola {r['Paciente']}, recordatorio de Elite.")
                st.markdown(f'<a href="https://wa.me/{r.get("WhatsApp","")}?text={msg}" target="_blank"><button style="width:100%; background:#25D366; color:white; border:none; height:35px; border-radius:8px;">WhatsApp</button></a>', unsafe_allow_html=True)
    with t1: render(datetime.now().strftime("%Y-%m-%d"))
    with t2: render((datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"))

elif menu == "📝 Registro & Masivos":
    st.title("Admisión de Planes")
    with st.form("form_v32", clear_on_submit=True):
        c1, c2 = st.columns(2)
        nom, dni, tel = c1.text_input("Nombre"), c1.text_input("DNI"), c1.text_input("WhatsApp")
        f_i, h_i = c2.date_input("Inicio"), c2.time_input("Hora")
        dias = c2.multiselect("Días fijos", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])
        serv = st.selectbox("Servicio", list(PRECIOS_BASE.keys()))
        orig = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
        ya_e = not df_p[df_p['DNI'].astype(str) == str(dni)].empty
        p_sug = PRECIOS_BASE[serv]["Socio" if orig=="Socio Gimnasio" else "Gral"] if "Masaje" in serv else PRECIOS_BASE[serv]
        if serv == "Evaluacion" and not ya_e: p_sug = 0 if orig=="Socio Gimnasio" else p_sug * 0.5
        pago = st.number_input("Pago Final ($)", value=float(p_sug))
        if st.form_submit_button("CONSOLIDAR PLAN"):
            if nom and dni:
                cant = 10 if "x10" in serv else (5 if "x5" in serv else 1)
                new_p = {c: "" for c in df_p.columns}; new_p.update({"DNI": dni, "Nombre": nom, "WhatsApp": tel, "Origen": orig, "Servicio": serv, "Pago": pago, "Sesiones_Totales": cant, "Sesiones_Restantes": cant, "Fecha_Inicio": f_i.strftime("%Y-%m-%d")})
                f_plan, curr, d_map = [], f_i, {"Lunes":0,"Martes":1,"Miércoles":2,"Jueves":3,"Viernes":4,"Sábado":5}
                while len(f_plan) < cant:
                    if not dias or curr.weekday() in [d_map[d] for d in dias]: f_plan.append(curr.strftime("%Y-%m-%d"))
                    curr += timedelta(days=1)
                new_a = []
                for f in f_plan:
                    row = {c: "" for c in df_a.columns}; row.update({"Fecha": f, "Hora": h_i.strftime("%H:%M"), "Paciente": nom, "Servicio": serv, "DNI": dni, "WhatsApp": tel, "Estado": "PENDIENTE"})
                    new_a.append(row)
                guardar_datos(pd.concat([df_p, pd.DataFrame([new_p])], ignore_index=True), "pacientes")
                guardar_datos(pd.concat([df_a, pd.DataFrame(new_a)], ignore_index=True), "agenda")
                st.success("Plan consolidado."); st.rerun()

elif menu == "📊 Inteligencia & PDF":
    st.title("Auditoría Financiera")
    c_f1, c_f2 = st.columns(2)
    f_d, f_h = c_f1.date_input("Desde", datetime.now()-timedelta(days=30)), c_f2.date_input("Hasta", datetime.now())
    df_p['Fecha_Inicio'] = pd.to_datetime(df_p['Fecha_Inicio'], errors='coerce')
    df_hist = df_p[(df_p['Fecha_Inicio'].dt.date >= f_d) & (df_p['Fecha_Inicio'].dt.date <= f_h)].copy()
    df_hist['% Cesión'] = df_hist['Origen'].apply(lambda x: 0.30 if x == "Socio Gimnasio" else 0.20)
    df_hist['Monto Cesión'] = df_hist['Pago'] * df_hist['% Cesión']
    df_hist['Ingreso Neto'] = df_hist['Pago'] - df_hist['Monto Cesión']
    bruto, cesion = df_hist['Pago'].sum(), df_hist['Monto Cesión'].sum()
    neta = bruto - cesion - gastos_f
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Bruto", f"${bruto:,.0f}")
    col2.metric("Cesión", f"-${cesion:,.0f}")
    col3.metric("Neta", f"${neta:,.0f}")
    
    if st.button("📥 Generar Reporte PDF"):
        pdf_bytes = create_pdf(df_hist, bruto, cesion, neta)
        st.download_button(label="Click para Descargar PDF", data=pdf_bytes, file_name=f"Reporte_Elite_{f_d}.pdf", mime="application/pdf")
    
    st.dataframe(df_hist[['Nombre', 'Origen', 'Servicio', 'Pago', 'Monto Cesión', 'Ingreso Neto']], use_container_width=True)
