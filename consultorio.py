import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import urllib.parse

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Elite Master V47", layout="wide")

PRECIOS_REF = {
    "Evaluacion": 36000, "Sesion Individual": 24000,
    "Plan x5": 110000, "Plan x10": 200000,
    "Masaje Socio": 25000, "Masaje Gral": 30000
}

# --- CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        p = conn.read(worksheet="pacientes", ttl="0").dropna(how='all')
        a = conn.read(worksheet="agenda", ttl="0").dropna(how='all')
        return p, a
    except:
        return pd.DataFrame(), pd.DataFrame()

df_p, df_a = get_data()

def update_data(df, sheet_name):
    try:
        # Alineación de columnas para evitar el error ValueError
        cols = conn.read(worksheet=sheet_name, ttl="0").columns.tolist()
        df_save = df.reindex(columns=cols).fillna("")
        conn.update(worksheet=sheet_name, data=df_save)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Error de red: {e}")

# --- MOTOR SMART-SYNC (EFECTO SUSANA) ---
def motor_sync():
    if df_a.empty: return
    now = datetime.now()
    f_hoy, h_hoy = now.strftime("%Y-%m-%d"), now.strftime("%H:%M")
    
    # Filtrar turnos pasados pendientes
    mask = (df_a['Fecha'].astype(str) <= f_hoy) & (df_a['Hora'].astype(str) < h_hoy) & (df_a.get('Estado','') != 'PROCESADO')
    
    if not df_a[mask].empty:
        p_upd, a_upd = df_p.copy(), df_a.copy()
        for idx, row in df_a[mask].iterrows():
            dni_val = str(row.get('DNI', ''))
            p_idx = p_upd[p_upd['DNI'].astype(str) == dni_val].index
            if not p_idx.empty:
                # Restar sesión del saldo
                current = pd.to_numeric(p_upd.at[p_idx[0], 'Sesiones_Restantes'], errors='coerce')
                p_upd.at[p_idx[0], 'Sesiones_Restantes'] = max(0, int(current if pd.notnull(current) else 0) - 1)
            a_upd.at[idx, 'Estado'] = 'PROCESADO'
        update_data(p_upd, "pacientes")
        update_data(a_upd, "agenda")
        st.rerun()

# --- INTERFAZ ---
st.sidebar.title("ELITE MASTER")
menu = st.sidebar.radio("Navegación", ["📅 Agenda", "📝 Admisión & DX", "📊 Auditoría"])
fijos = st.sidebar.number_input("Gastos Fijos", value=0)

if menu == "📅 Agenda":
    motor_sync()
    st.title("Control de Sesiones")
    t1, t2 = st.tabs(["Hoy", "Mañana"])
    
    def show_day(fecha):
        res = df_a[df_a['Fecha'].astype(str) == fecha].sort_values("Hora")
        if res.empty: st.info("Sin turnos.")
        for i, r in res.iterrows():
            with st.container(border=True):
                p_row = df_p[df_p['DNI'].astype(str) == str(r.get('DNI',''))]
                saldo = p_row['Sesiones_Restantes'].iloc[0] if not p_row.empty else 0
                dx_p = p_row['DX'].iloc[0] if not p_row.empty and 'DX' in p_row.columns else "---"
                st.write(f"**{r['Hora']}** | {r['Paciente']} | Saldo: **{saldo}** | DX: *{dx_p}*")
                
                if st.button("Renovar", key=f"btn_{i}"):
                    st.session_state.ren_pac = r['Paciente']
                    st.info("Pasa a Admisión")
                
                msg_wa = urllib.parse.quote(f"Hola {r['Paciente']}, recordatorio de turno.")
                st.markdown(f'<a href="https://wa.me/{r.get("WhatsApp","")}?text={msg_wa}" target="_blank"><button style="width:100%; background:#25D366; color:white; border:none; border-radius:8px; padding:5px;">WhatsApp</button></a>', unsafe_allow_html=True)

    with t1: show_day(datetime.now().strftime("%Y-%m-%d"))
    with t2: show_day((datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"))

elif menu == "📝 Admisión & DX":
    st.title("Nuevo Registro")
    with st.form("f_adm"):
        c1, c2 = st.columns(2)
        n_p = c1.text_input("Nombre", value=st.session_state.get('ren_pac', ''))
        d_p = c1.text_input("DNI")
        w_p = c1.text_input("WhatsApp")
        dx_val = c1.text_area("Diagnóstico (DX)")
        f_i, h_i = c2.date_input("Inicio"), c2.time_input("Hora")
        dias = c2.multiselect("Días", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])
        serv = st.selectbox("Plan", list(PRECIOS_REF.keys()))
        orig = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
        pago = st.number_input("Cobro", value=float(PRECIOS_REF[serv]))
        
        if st.form_submit_button("CONSOLIDAR"):
            if n_p and d_p:
                cant = 10 if "x10" in serv else (5 if "x5" in serv else 1)
                # Datos Paciente
                new_p = pd.DataFrame([{"DNI": d_p, "Nombre": n_p, "WhatsApp": w_p, "Origen": orig, "Servicio": serv, "Pago": pago, "Sesiones_Totales": cant, "Sesiones_Restantes": cant, "Fecha_Inicio": f_i.strftime("%Y-%m-%d"), "DX": dx_val}])
                # Agenda
                dm = {"Lunes":0, "Martes":1, "Miércoles":2, "Jueves":3, "Viernes":4, "Sábado":5}
                fl, cur = [], f_i
                while len(fl) < cant:
                    if not dias or cur.weekday() in [dm[d] for d in dias]: fl.append(cur.strftime("%Y-%m-%d"))
                    cur += timedelta(days=1)
                new_a = pd.DataFrame([{"Fecha": f, "Hora": h_i.strftime("%H:%M"), "Paciente": n_p, "DNI": d_p, "WhatsApp": w_p, "Estado": "PENDIENTE", "Servicio": serv} for f in fl])
                
                update_data(pd.concat([df_p, new_p], ignore_index=True), "pacientes")
                update_data(pd.concat([df_a, new_a], ignore_index=True), "agenda")
                st.success("Grabado con éxito"); st.rerun()

elif menu == "📊 Auditoría":
    st.title("Rentabilidad")
    if not df_p.empty:
        ingreso = pd.to_numeric(df_p['Pago'], errors='coerce').sum()
        cesion = 0.0
        for idx, row in df_p.iterrows():
            p_val = float(row.get('Pago', 0))
            # Comisiones 30/20 según origen
            cesion += p_val * (0.30 if row.get('Origen') == "Socio Gimnasio" else 0.20)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Bruto", f"${ingreso:,.0f}")
        c2.metric("Cesión", f"-${cesion:,.0f}")
        c3.metric("Neto", f"${ingreso - cesion - fijos:,.0f}")
        st.dataframe(df_p)
