import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import urllib.parse

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Elite Master V45", layout="wide")

# Lista de precios simplificada para evitar errores de traducción
VALORES = {
    "Evaluacion": 36000, "Sesion Individual": 24000,
    "Plan x5": 110000, "Plan x10": 200000,
    "Masaje Socio": 25000, "Masaje Gral": 30000
}

# --- 2. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        p = conn.read(worksheet="pacientes", ttl="0").dropna(how='all')
        a = conn.read(worksheet="agenda", ttl="0").dropna(how='all')
        return p, a
    except:
        return pd.DataFrame(), pd.DataFrame()

df_p, df_a = cargar_datos()

def grabar(df, hoja):
    try:
        # Alineación automática de columnas (Evita errores de image_14ce80.png)
        ref = conn.read(worksheet=hoja, ttl="0")
        df_save = df.reindex(columns=ref.columns.tolist()).fillna("")
        conn.update(worksheet=hoja, data=df_save)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Error de red: {e}")

# --- 3. MOTOR DE ACTUALIZACIÓN ---
def sync_sesiones():
    if df_a.empty: return
    ahora = datetime.now()
    hoy_f, hoy_h = ahora.strftime("%Y-%m-%d"), ahora.strftime("%H:%M")
    
    # Filtro de turnos ya ocurridos
    mask = (df_a['Fecha'].astype(str) <= hoy_f) & (df_a['Hora'].astype(str) < hoy_h) & (df_a.get('Estado','') != 'PROCESADO')
    
    if not df_a[mask].empty:
        p_act, a_act = df_p.copy(), df_a.copy()
        for idx, r in df_a[mask].iterrows():
            dni_v = str(r.get('DNI', ''))
            indices = p_act[p_act['DNI'].astype(str) == dni_v].index
            if not indices.empty:
                val = pd.to_numeric(p_act.at[indices[0], 'Sesiones_Restantes'], errors='coerce')
                p_act.at[indices[0], 'Sesiones_Restantes'] = max(0, int(val if pd.notnull(val) else 0) - 1)
            a_act.at[idx, 'Estado'] = 'PROCESADO'
        grabar(p_act, "pacientes")
        grabar(a_act, "agenda")
        st.rerun()

# --- 4. INTERFAZ ---
menu = st.sidebar.radio("SISTEMA", ["📅 Agenda", "📝 Admisión (con DX)", "📊 Finanzas"])
fijos = st.sidebar.number_input("Gastos Fijos", value=0)

if menu == "📅 Agenda":
    sync_sesiones()
    st.title("Control de Turnos")
    t1, t2 = st.tabs(["Hoy", "Mañana"])
    
    def mostrar(f):
        items = df_a[df_a['Fecha'].astype(str) == f].sort_values("Hora")
        if items.empty: st.info("Sin turnos.")
        for i, r in items.iterrows():
            with st.container(border=True):
                p_row = df_p[df_p['DNI'].astype(str) == str(r.get('DNI',''))]
                saldo = p_row['Sesiones_Restantes'].iloc[0] if not p_row.empty else 0
                dx_text = p_row['DX'].iloc[0] if not p_row.empty and 'DX' in p_row.columns else "---"
                st.write(f"**{r['Hora']}** | {r['Paciente']} | Saldo: **{saldo}** | DX: *{dx_text}*")
                
                if st.button("Renovar", key=f"r_{i}"):
                    st.session_state.p_ren = r['Paciente']
                
                msg = urllib.parse.quote(f"Hola {r['Paciente']}, recordatorio de turno.")
                st.markdown(f'<a href="https://wa.me/{r.get("WhatsApp","")}?text={msg}" target="_blank"><button style="width:100%; background:#25D366; color:white; border:none; padding:5px; border-radius:5px;">WhatsApp</button></a>', unsafe_allow_html=True)

    with t1: mostrar(datetime.now().strftime("%Y-%m-%d"))
    with t2: mostrar((datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"))

elif menu == "📝 Admisión (con DX)":
    st.title("Registro y DX")
    with st.form("f_reg"):
        c1, c2 = st.columns(2)
        nom = c1.text_input("Nombre", value=st.session_state.get('p_ren', ''))
        dni = c1.text_input("DNI")
        tel = c1.text_input("WhatsApp")
        dx_in = c1.text_area("Diagnóstico (DX)")
        f_i, h_i = c2.date_input("Inicia"), c2.time_input("Hora")
        dias = c2.multiselect("Días", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])
        serv = st.selectbox("Servicio", list(VALORES.keys()))
        orig = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
        monto = st.number_input("Cobro", value=float(VALORES[serv]))
        
        if st.form_submit_button("GUARDAR PLAN"):
            cant = 10 if "x10" in serv else (5 if "x5" in serv else 1)
            np = pd.DataFrame([{"DNI": dni, "Nombre": nom, "WhatsApp": tel, "Origen": orig, "Servicio": serv, "Pago": monto, "Sesiones_Totales": cant, "Sesiones_Restantes": cant, "Fecha_Inicio": f_i.strftime("%Y-%m-%d"), "DX": dx_in}])
            d_m = {"Lunes":0, "Martes":1, "Miércoles":2, "Jueves":3, "Viernes":4, "Sábado":5}
            fs, cur = [], f_i
            while len(fs) < cant:
                if not dias or cur.weekday() in [d_m[d] for d in dias]: fs.append(cur.strftime("%Y-%m-%d"))
                cur += timedelta(days=1)
            na = pd.DataFrame([{"Fecha": f, "Hora": h_i.strftime("%H:%M"), "Paciente": nom, "DNI": dni, "WhatsApp": tel, "Estado": "PENDIENTE", "Servicio": serv} for f in fs])
            grabar(pd.concat([df_p, np], ignore_index=True), "pacientes")
            grabar(pd.concat([df_a, na], ignore_index=True), "agenda")
            st.success("Grabado")

elif menu == "📊 Finanzas":
    st.title("Resumen")
    if not df_p.empty:
        bruto = pd.to_numeric(df_p['Pago'], errors='coerce').sum()
        cesion = 0
        for _, r in df_p.iterrows():
            val = float(r.get('Pago', 0))
            cesion += val * (0.3 if r.get('Origen') == "Socio Gimnasio" else 0.2)
        
        st.metric("Ingresos", f"${bruto:,.0f}")
        st.metric("Neto", f"${bruto - cesion - fijos:,.0f}")
        st.dataframe(df_p)
