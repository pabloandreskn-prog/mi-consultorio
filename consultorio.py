import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import urllib.parse

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Elite System V42", layout="wide", page_icon="🌿")

PRECIOS_BASE = {
    "Evaluacion": 36000, "Sesion Especializada": 36000, "Sesion Individual": 24000,
    "Plan x5": 110000, "Plan x10": 200000,
    "Masaje ZA": {"Socio": 25000, "Gral": 30000},
    "Masaje ZB": {"Socio": 25000, "Gral": 30000},
    "Masaje Completo": {"Socio": 38000, "Gral": 45000}
}

# --- 2. GESTIÓN DE DATOS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        df_p = conn.read(worksheet="pacientes", ttl="0").dropna(how='all')
        df_a = conn.read(worksheet="agenda", ttl="0").dropna(how='all')
        for col in ['Pago', 'Sesiones_Restantes', 'Sesiones_Totales']:
            if col in df_p.columns:
                df_p[col] = pd.to_numeric(df_p[col], errors='coerce').fillna(0)
        return df_p, df_a
    except Exception:
        return pd.DataFrame(), pd.DataFrame()

df_p, df_a = cargar_datos()

def guardar_datos(df, hoja):
    try:
        # Sincronización blindada para evitar el ValueError de la imagen image_14ce80.png
        df_ref = conn.read(worksheet=hoja, ttl="0")
        columnas_destino = df_ref.columns.tolist()
        df_final = df.reindex(columns=columnas_destino).fillna("")
        conn.update(worksheet=hoja, data=df_final)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Error de sincronización: {e}")

# --- 3. MOTOR SMART-SYNC (EFECTO SUSANA) ---
def smart_sync():
    if df_a.empty: return
    ahora = datetime.now()
    f_h, h_h = ahora.strftime("%Y-%m-%d"), ahora.strftime("%H:%M")
    mask = (df_a['Fecha'].astype(str) <= f_h) & (df_a['Hora'].astype(str) < h_h) & (df_a.get('Estado','') != 'PROCESADO')
    if not df_a[mask].empty:
        df_p_act, df_a_act = df_p.copy(), df_a.copy()
        for idx, t in df_a[mask].iterrows():
            dni_pac = str(t.get('DNI', ''))
            p_idx = df_p_act[df_p_act['DNI'].astype(str) == dni_pac].index
            if not p_idx.empty:
                df_p_act.at[p_idx[0], 'Sesiones_Restantes'] = max(0, df_p_act.at[p_idx[0], 'Sesiones_Restantes'] - 1)
            df_a_act.at[idx, 'Estado'] = 'PROCESADO'
        guardar_datos(df_p_act, "pacientes")
        guardar_datos(df_a_act, "agenda")
        st.rerun()

# --- 4. INTERFAZ ---
menu = st.sidebar.radio("SISTEMA ÉLITE V42", ["📅 Agenda", "📝 Registro & DX", "📊 Finanzas"])
gastos_fijos = st.sidebar.number_input("Gastos Fijos ($)", value=0)

if menu == "📅 Agenda":
    smart_sync()
    st.title("Agenda de Turnos")
    t1, t2 = st.tabs(["Hoy", "Mañana"])
    def render_dia(f):
        res = df_a[df_a['Fecha'].astype(str) == f].sort_values("Hora")
        if res.empty: st.info("Sin turnos.")
        for i, r in res.iterrows():
            with st.container(border=True):
                p_row = df_p[df_p['DNI'].astype(str) == str(r.get('DNI',''))]
                saldo = int(p_row['Sesiones_Restantes'].iloc[0]) if not p_row.empty else 0
                dx = p_row['DX'].iloc[0] if not p_row.empty and 'DX' in p_row.columns else "---"
                st.write(f"**{r['Hora']} hs** | {r['Paciente']} | Saldo: **{saldo}** | DX: *{dx}*")
                c1, c2, c3 = st.columns(3)
                with c1:
                    with st.popover("⚙️ Reagendar"):
                        nf = st.date_input("Fecha", key=f"f{i}")
                        nh = st.time_input("Hora", key=f"h{i}")
                        if st.button("Grabar", key=f"b{i}"):
                            df_a.at[i, 'Fecha'], df_a.at[i, 'Hora'] = nf.strftime("%Y-%m-%d"), nh.strftime("%H:%M")
                            guardar_datos(df_a, "agenda"); st.rerun()
                with c2:
                    if st.button("🛒 Renovar", key=f"r{i}"):
                        st.session_state.p_renov = r['Paciente']; st.info("Ve a Registro")
                with c3:
                    msg = urllib.parse.quote(f"Hola {r['Paciente']}, recordatorio de turno.")
                    st.markdown(f'<a href="https://wa.me/{r.get("WhatsApp","")}?text={msg}" target="_blank"><button style="width:100%; background:#25D366; color:white; border:none; padding:8px; border-radius:8px;">WhatsApp</button></a>', unsafe_allow_html=True)
    with t1: render_dia(datetime.now().strftime("%Y-%m-%d"))
    with t2: render_dia((datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"))

elif menu == "📝 Registro & DX":
    st.title("Admisión de Pacientes")
    with st.form("form_adm", clear_on_submit=True):
        c1, c2 = st.columns(2)
        nom, dni, tel = c1.text_input("Nombre", value=st.session_state.get('p_renov', '')), c1.text_input("DNI"), c1.text_input("WhatsApp")
        dx_in = c1.text_area("DX (Diagnóstico)")
        f_i, h_i = c2.date_input("Inicio"), c2.time_input("Hora")
        dias = c2.multiselect("Días", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])
        serv, orig = st.selectbox("Servicio", list(PRECIOS_BASE.keys())), st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
        p_sug = PRECIOS_BASE[serv]["Socio" if orig=="Socio Gimnasio" else "Gral"] if "Masaje" in serv else PRECIOS_BASE[serv]
        pago = st.number_input("Monto ($)", value=float(p_sug))
        if st.form_submit_button("CONSOLIDAR PLAN"):
            if nom and dni:
                cant = 10 if "x10" in serv else (5 if "x5" in serv else 1)
                new_p = pd.DataFrame([{"DNI": dni, "Nombre": nom, "WhatsApp": tel, "Origen": orig, "Servicio": serv, "Pago": pago, "Sesiones_Totales": cant, "Sesiones_Restantes": cant, "Fecha_Inicio": f_i.strftime("%Y-%m-%d"), "DX": dx_in}])
                d_m = {"Lunes":0, "Martes":1, "Miércoles":2, "Jueves":3, "Viernes":4, "Sábado":5}
                fs, curr = [], f_i
                while len(fs) < cant:
                    if not dias or curr.weekday() in [d_m[d] for d in dias]: fs.append(curr.strftime("%Y-%m-%d"))
                    curr += timedelta(days=1)
                new_a = pd.DataFrame([{"Fecha": f, "Hora": h_ini.strftime("%H:%M") if 'h_ini' in locals() else h_i.strftime("%H:%M"), "Paciente": nom, "DNI": dni, "WhatsApp": tel, "Estado": "PENDIENTE", "Servicio": serv} for f in fs])
                guardar_datos(pd.concat([df_p, new_p], ignore_index=True), "pacientes")
                guardar_datos(pd.concat([df_a, new_a], ignore_index=True), "agenda")
                st.success("Plan grabado"); st.rerun()

elif menu == "📊 Finanzas":
    st.title("Rentabilidad")
    cf1, cf2 = st.columns(2)
    d_f, h_f = cf1.date_input("Desde", datetime.now()-timedelta(days=30)), cf2.date_input("Hasta", datetime.now())
    df_p['Fecha_Inicio'] = pd.to_datetime(df_p['Fecha_Inicio'], errors='coerce')
    df_f = df_p[(df_p['Fecha_Inicio'].dt.date >= d_f) & (df_p['Fecha_Inicio'].dt.date <= h_f)].copy()
    
    # Lógica de comisiones 30/20 robusta
    def calc_comision(row):
        return row['Pago'] * (0.30 if row['Origen'] == "Socio Gimnasio" else 0.20)
    
    df_f['Comision'] = df_f.apply(calc_comision, axis=1)
    df_f['Neto'] = df_f['Pago'] - df_f['Comision']
    b, c = df_f['Pago'].sum(), df_f['Comision'].sum()
    st.columns(3)[0].metric("Ingresos", f"${b:,.0f}")
    st.columns(3)[1].metric("Cesiones", f"-${c:,.0f}")
    st.columns(3)[2].metric("Final", f"${b-c-gastos_fijos:,.0f}")
    st.dataframe(df_f[['Nombre', 'DX', 'Origen', 'Pago', 'Comision', 'Neto']], use_container_width=True)
    st.download_button("Descargar CSV", df_f.to_csv(index=False).encode('utf-8'), "Elite.csv", "text/csv")
