import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# --- 1. CONFIGURACIÓN Y ESTILOS ---
st.set_page_config(page_title="Elite System v11.0", layout="wide", page_icon="🌿")

BRAND_GREEN, BRAND_RED, BRAND_ORANGE, BRAND_BLUE = "#60b067", "#ff4b4b", "#f39c12", "#3498db"

st.markdown(f"""
    <style>
    .stApp {{ background-color: #FAFAFA; }}
    .card {{ 
        background: white; padding: 20px; border-radius: 12px; 
        border-left: 6px solid {BRAND_GREEN}; margin-bottom: 15px; 
        box-shadow: 0px 4px 10px rgba(0,0,0,0.05); 
    }}
    .sesiones-tag {{ background: #e8f5e9; padding: 3px 12px; border-radius: 15px; font-weight: bold; font-size: 13px; }}
    .alert-pago {{ color: {BRAND_RED}; font-weight: bold; font-size: 11px; border: 1.5px solid {BRAND_RED}; padding: 2px 6px; border-radius: 5px; text-transform: uppercase; }}
    .renovacion-tag {{ background: #fff3e0; color: {BRAND_ORANGE}; padding: 3px 12px; border-radius: 15px; font-weight: bold; border: 1px solid {BRAND_ORANGE}; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. BASE DE PRECIOS Y SERVICIOS ---
SERVICIOS_PRECIOS = {
    "Plan x10": 200000,
    "Plan x 5": 110000,
    "Sesión Individual": 24000,
    "Sesión Especializada": 36000,
    "Evaluación": 36000,
    "Masaje Zona A (Piernas/Pies)": {"Socio Gimnasio": 25000, "Captación Propia": 30000},
    "Masaje Zona B (Espalda/Cabeza)": {"Socio Gimnasio": 25000, "Captación Propia": 30000},
    "Masaje Completo": {"Socio Gimnasio": 38000, "Captación Propia": 45000}
}

HORARIOS = [f"{h:02d}:00" for h in [8,9,10,11,12,13,16,17,18,19,20]]

# --- 3. CONEXIÓN ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos(pestaña):
    return conn.read(worksheet=pestaña, ttl="0")

# --- 4. MENÚ LATERAL ---
with st.sidebar:
    st.markdown(f"<h1 style='color:{BRAND_GREEN}; text-align:center;'>ELITE SYSTEM</h1>", unsafe_allow_html=True)
    st.caption("v11.0 - MOVIMIENTO ÁGIL & PRECIOS")
    menu = st.radio("NAVEGACIÓN", ["📅 Agenda", "📝 Registro & Renovación", "📊 Finanzas"])

# --- 5. MÓDULO: AGENDA ---
if menu == "📅 Agenda":
    st.header("Gestión de Agenda")
    fecha_sel = st.date_input("Día", datetime.now(), key="cal_v11")
    
    df_a = cargar_datos("agenda")
    df_p = cargar_datos("pacientes")
    
    turnos_dia = df_a[df_a['Fecha'].astype(str) == str(fecha_sel)].copy()
    
    if not turnos_dia.empty:
        for idx, row in turnos_dia.sort_values(by="Hora").iterrows():
            p_ficha = df_p[df_p['Nombre'] == row['Paciente']].tail(1)
            
            # Lógica de Sesiones y Alertas
            debe_pago = False
            necesita_renovar = False
            tag_html = ""
            
            if not p_ficha.empty:
                p = p_ficha.iloc[0]
                debe_pago = float(p.get('Pago', 0)) <= 0
                
                if "Plan" in str(row['Servicio']):
                    totales = int(p.get('Sesiones_Totales', 0))
                    f_pack = str(p.get('Fecha_Inicio', '2000-01-01'))
                    asistencias = len(df_a[(df_a['Paciente'] == row['Paciente']) & (df_a['Fecha'].astype(str) >= f_pack)])
                    restantes = totales - asistencias
                    tag_html = f"<span class='sesiones-tag'>{restantes} / {totales} rest.</span>"
                    if restantes <= 1: necesita_renovar = True
                else:
                    tag_html = f"<span class='sesiones-tag'>{row['Servicio']}</span>"
                    necesita_renovar = True

            # Tarjeta de Turno
            with st.container():
                c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                with c1:
                    alerta = '<span class="alert-pago">DEBE PAGAR</span>' if debe_pago else ""
                    renov = '<span class="renovacion-tag">RENOVAR</span>' if necesita_renovar else ""
                    st.markdown(f"""<div class="card"><b>{row['Hora']}</b> — <b>{row['Paciente']}</b> {alerta} {tag_html} {renov}</div>""", unsafe_allow_html=True)
                
                with c2: # ACCIÓN: MOVER ÁGIL
                    if st.button("🔄 Mover", key=f"mov_{idx}"):
                        st.session_state[f"edit_{idx}"] = True
                    
                with c3: # ACCIÓN: COBRAR
                    if debe_pago:
                        if st.button("💵 Cobrar", key=f"cob_{idx}"):
                            p_idx = df_p[df_p['Nombre'] == row['Paciente']].index[-1]
                            df_p.at[p_idx, 'Pago'] = 1 
                            conn.update(worksheet="pacientes", data=df_p)
                            st.rerun()

                with c4: # ACCIÓN: RENOVAR
                    if necesita_renovar:
                        if st.button("➕ Renovar", key=f"ren_{idx}"):
                            st.session_state.paciente_renovando = row['Paciente']
                            st.session_state.menu = "📝 Registro & Renovación"
                            st.rerun()

            # Mini Formulario para Mover Turno (Aparece abajo de la tarjeta)
            if st.session_state.get(f"edit_{idx}", False):
                with st.expander("Configurar nueva fecha/hora", expanded=True):
                    col_ea, col_eb = st.columns(2)
                    nueva_f = col_ea.date_input("Nueva Fecha", value=fecha_sel, key=f"nf_{idx}")
                    nueva_h = col_eb.selectbox("Nueva Hora", HORARIOS, index=HORARIOS.index(row['Hora']), key=f"nh_{idx}")
                    if st.button("Guardar Cambio", key=f"save_{idx}"):
                        # Buscamos en la pestaña agenda y actualizamos
                        mask = (df_a['Paciente'] == row['Paciente']) & (df_a['Fecha'].astype(str) == str(row['Fecha'])) & (df_a['Hora'] == row['Hora'])
                        df_a.loc[mask, 'Fecha'] = str(nueva_f)
                        df_a.loc[mask, 'Hora'] = nueva_h
                        conn.update(worksheet="agenda", data=df_a)
                        st.session_state[f"edit_{idx}"] = False
                        st.rerun()

# --- 6. MÓDULO: REGISTRO & RENOVACIÓN ---
elif menu == "📝 Registro & Renovación":
    st.header("Formulario de Ingreso / Renovación")
    
    # Auto-completar si viene de renovación
    nombre_preset = st.session_state.get('paciente_renovando', "")
    
    with st.form("reg_v11"):
        c1, c2 = st.columns(2)
        nombre = c1.text_input("Paciente", value=nombre_preset)
        dni = c2.text_input("DNI")
        orig = c1.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
        serv = c2.selectbox("Servicio", list(SERVICIOS_PRECIOS.keys()))
        
        # Lógica automática de precio
        precio_sugerido = 0
        val = SERVICIOS_PRECIOS[serv]
        if isinstance(val, dict):
            precio_sugerido = val[orig]
        else:
            precio_sugerido = val
            
        monto = st.number_input("Monto a Cobrar ($)", value=precio_sugerido)
        fecha_ini = st.date_input("Fecha de Turno / Inicio")
        hora_ini = st.selectbox("Hora", HORARIOS)
        dx = st.text_input("DX / Notas")

        if st.form_submit_button("Confirmar Registro"):
            # Guardar en Pacientes
            df_p = cargar_datos("pacientes")
            tot_s = 10 if "x10" in serv else (5 if "x 5" in serv else 1)
            new_p = pd.DataFrame([[dni, nombre, "", dx, orig, serv, monto, str(fecha_ini), tot_s]], columns=df_p.columns)
            conn.update(worksheet="pacientes", data=pd.concat([df_p, new_p], ignore_index=True))
            
            # Guardar en Agenda
            df_a = cargar_datos("agenda")
            new_a = pd.DataFrame([[str(fecha_ini), hora_ini, nombre, serv]], columns=df_a.columns)
            conn.update(worksheet="agenda", data=pd.concat([df_a, new_a], ignore_index=True))
            
            st.session_state.paciente_renovando = ""
            st.success("Operación Exitosa")
            st.rerun()

# --- 7. MÓDULO: FINANZAS ---
elif menu == "📊 Finanzas":
    st.header("Panel de Ingresos")
    df_p = cargar_datos("pacientes")
    if not df_p.empty:
        df_p['Pago'] = pd.to_numeric(df_p['Pago'], errors='coerce').fillna(0)
        df_p['Comisión'] = df_p.apply(lambda x: x['Pago'] * 0.3 if x['Origen'] == "Socio Gimnasio" else x['Pago'] * 0.2, axis=1)
        df_p['Neto'] = df_p['Pago'] - df_p['Comisión']
        
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Bruto", f"${df_p['Pago'].sum():,.0f}")
        col_m2.metric("Comisiones", f"-${df_p['Comisión'].sum():,.0f}")
        col_m3.metric("Neto Elite", f"${df_p['Neto'].sum():,.0f}")
        st.dataframe(df_p[['Fecha_Inicio', 'Nombre', 'Servicio', 'Pago', 'Neto']], use_container_width=True)
