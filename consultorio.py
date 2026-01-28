import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import urllib.parse

# --- CONFIGURACIÓN DE SEGURIDAD ---
st.set_page_config(page_title="Elite System V43", layout="wide")

# Precios sin estructuras complejas para evitar errores de traducción
PRECIOS = {
    "Evaluacion": 36000, "Plan x5": 110000, "Plan x10": 200000,
    "Masaje ZA Socio": 25000, "Masaje ZA Gral": 30000,
    "Masaje Completo Socio": 38000, "Masaje Completo Gral": 45000
}

# --- CONEXIÓN DE DATOS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        p = conn.read(worksheet="pacientes", ttl="0").dropna(how='all')
        a = conn.read(worksheet="agenda", ttl="0").dropna(how='all')
        return p, a
    except:
        return pd.DataFrame(), pd.DataFrame()

df_p, df_a = cargar_datos()

def guardar(df, hoja):
    try:
        # Blindaje de columnas (Soluciona image_14ce80.png)
        ref = conn.read(worksheet=hoja, ttl="0")
        cols = ref.columns.tolist()
        df_final = df.reindex(columns=cols).fillna("")
        conn.update(worksheet=hoja, data=df_final)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Error de red: {e}")

# --- MOTOR DE SESIONES (SMART-SYNC) ---
def sincronizar():
    if df_a.empty: return
    ahora = datetime.now()
    hoy_str, hora_str = ahora.strftime("%Y-%m-%d"), ahora.strftime("%H:%M")
    
    # Filtro de turnos pasados
    mask = (df_a['Fecha'].astype(str) <= hoy_str) & (df_a['Hora'].astype(str) < hora_str) & (df_a.get('Estado','') != 'PROCESADO')
    
    if not df_a[mask].empty:
        p_act, a_act = df_p.copy(), df_a.copy()
        for idx, r in df_a[mask].iterrows():
            dni_val = str(r.get('DNI', ''))
            indices = p_act[p_act['DNI'].astype(str) == dni_val].index
            if not indices.empty:
                val = pd.to_numeric(p_act.at[indices[0], 'Sesiones_Restantes'], errors='coerce')
                p_act.at[indices[0], 'Sesiones_Restantes'] = max(0, int(val or 0) - 1)
            a_act.at[idx, 'Estado'] = 'PROCESADO'
        guardar(p_act, "pacientes")
        guardar(a_act, "agenda")
        st.rerun()

# --- INTERFAZ ---
menu = st.sidebar.radio("MENÚ", ["📅 Agenda", "📝 Admisión (DX)", "📊 Auditoría"])
gastos = st.sidebar.number_input("Gastos Fijos", value=0)

if menu == "📅 Agenda":
    sincronizar()
    st.title("Control de Sesiones")
    t1, t2 = st.tabs(["Hoy", "Mañana"])
    
    def dibujar(fec):
        items = df_a[df_a['Fecha'].astype(str) == fec].sort_values("Hora")
        if items.empty: st.info("Día sin turnos.")
        for i, r in items.iterrows():
            with st.container(border=True):
                p_row = df_p[df_p['DNI'].astype(str) == str(r.get('DNI',''))]
                saldo = p_row['Sesiones_Restantes'].iloc[0] if not p_row.empty else 0
                dx_p = p_row['DX'].iloc[0] if not p_row.empty and 'DX' in p_row.columns else "---"
                st.write(f"**{r['Hora']}** | {r['Paciente']} | Saldo: **{saldo}** | DX: *{dx_p}*")
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Renovar", key=f"ren_{i}"):
                        st.session_state.p_ren = r['Paciente']
                with c2:
                    msg = urllib.parse.quote(f"Hola {r['Paciente']}, recordatorio de turno.")
                    st.markdown(f'''<a href="https://wa.me/{r.get('WhatsApp','')}?text={msg}" target="_blank">
                        <button style="width:100%;background:#25D366;color:white;border:none;border-radius:5px;padding:5px">WhatsApp</button></a>''', unsafe_allow_html=True)

    with t1: dibujar(datetime.now().strftime("%Y-%m-%d"))
    with t2: dibujar((datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"))

elif menu == "📝 Admisión (DX)":
    st.title("Nuevo Plan / Paciente")
    with st.form("f_adm"):
        c1, c2 = st.columns(2)
        nom = c1.text_input("Nombre", value=st.session_state.get('p_ren', ''))
        dni = c1.text_input("DNI")
        tel = c1.text_input("WhatsApp")
        dx_in = c1.text_area("Diagnóstico (DX)")
        f_i = c2.date_input("Fecha Inicio")
        h_i = c2.time_input("Hora")
        dias = c2.multiselect("Días", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"])
        serv = st.selectbox("Servicio", list(PRECIOS.keys()))
        orig = st.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
        monto = st.number_input("Monto Cobrado", value=float(PRECIOS[serv]))
        
        if st.form_submit_button("CONSOLIDAR"):
            cant = 10 if "x10" in serv else (5 if "x5" in serv else 1)
            # Registro Paciente
            np = pd.DataFrame([{"DNI": dni, "Nombre": nom, "WhatsApp": tel, "Origen": orig, "Servicio": serv, "Pago": monto, "Sesiones_Totales": cant, "Sesiones_Restantes": cant, "Fecha_Inicio": f_i.strftime("%Y-%m-%d"), "DX": dx_in}])
            # Registro Agenda
            d_map = {"Lunes":0, "Martes":1, "Miércoles":2, "Jueves":3, "Viernes":4, "Sábado":5}
            f_list, curr = [], f_i
            while len(f_list) < cant:
                if not dias or curr.weekday() in [d_map[d] for d in dias]: f_list.append(curr.strftime("%Y-%m-%d"))
                curr += timedelta(days=1)
            na = pd.DataFrame([{"Fecha": f, "Hora": h_i.strftime("%H:%M"), "Paciente": nom, "DNI": dni, "WhatsApp": tel, "Estado": "PENDIENTE", "Servicio": serv} for f in f_list])
            
            guardar(pd.concat([df_p, np], ignore_index=True), "pacientes")
            guardar(pd.concat([df_a, na], ignore_index=True), "agenda")
            st.success("¡Listo!"); st.rerun()

elif menu == "📊 Auditoría":
    st.title("Métricas de Negocio")
    # Auditoría sin lambdas para evitar error image_f8365e.png
    if not df_p.empty:
        df_p['Fecha_Inicio'] = pd.to_datetime(df_p['Fecha_Inicio'], errors='coerce')
        total_b = df_p['Pago'].sum()
        
        # Cálculo de comisiones manual (Cero Lambdas)
        cesion = 0
        for _, row in df_p.iterrows():
            pago_val = float(row.get('Pago', 0))
            if row.get('Origen') == "Socio Gimnasio":
                cesion += pago_val * 0.30
            else:
                cesion += pago_val * 0.20
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Bruto", f"${total_b:,.0f}")
        c2.metric("Cesión", f"-${cesion:,.0f}")
        c3.metric("Neto", f"${total_b - cesion - gastos:,.0f}")
        st.dataframe(df_p)
