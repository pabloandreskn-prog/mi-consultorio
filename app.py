import streamlit as st
import pandas as pd
from datetime import datetime
from backend import EliteManager, PRECIOS, HORARIOS

# --- CONFIGURACIÓN UI ---
st.set_page_config(page_title="Elite System vFinal", layout="wide", page_icon="🌿")
manager = EliteManager()

# Estilos CSS
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .metric-box { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }
    .card-turno { border-left: 5px solid #60b067; background: white; padding: 15px; margin-bottom: 10px; border-radius: 5px; }
    .status-debt { color: #dc3545; font-weight: bold; font-size: 0.8em; border: 1px solid #dc3545; padding: 2px 5px; border-radius: 4px; }
    .status-ok { color: #28a745; font-weight: bold; font-size: 0.8em; }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.title("🌿 ELITE SYSTEM")
    st.markdown("---")
    menu = st.radio("Navegación", ["📅 Agenda", "📝 Nuevo Ingreso", "💰 Finanzas"])
    st.markdown("---")
    if st.button("🔄 Actualizar Datos"):
        st.cache_data.clear()
        st.rerun()

# --- MÓDULO 1: AGENDA ---
if menu == "📅 Agenda":
    st.header("Agenda Diaria")
    col_date, col_info = st.columns([1, 3])
    fecha_sel = col_date.date_input("Fecha", datetime.now())
    
    df_a = manager._get_data("agenda")
    df_p = manager._get_data("pacientes")
    
    # Procesamiento de Agenda
    if not df_a.empty:
        df_dia = df_a[df_a['Fecha'].astype(str) == str(fecha_sel)].copy()
        
        if df_dia.empty:
            st.info("No hay turnos programados para hoy.")
        else:
            # Ordenar por hora
            df_dia = df_dia.sort_values("Hora")
            
            for _, row in df_dia.iterrows():
                # Buscar info del paciente para ver deudas
                info_p = df_p[df_p['Nombre'] == row['Paciente']]
                deuda_html = ""
                btn_cobrar = False
                
                if not info_p.empty:
                    p_data = info_p.iloc[-1] # Último registro
                    monto_pactado = float(p_data['Monto_Pactado']) if p_data['Monto_Pactado'] != '' else 0
                    pagado = float(p_data['Pagado']) if p_data['Pagado'] != '' else 0
                    
                    if pagado < monto_pactado:
                        deuda_html = f"<span class='status-debt'>ADEUDA ${monto_pactado - pagado:,.0f}</span>"
                        btn_cobrar = True
                    else:
                        deuda_html = "<span class='status-ok'>PAGADO</span>"

                # Tarjeta Visual
                with st.container():
                    c1, c2, c3 = st.columns([3, 1, 1])
                    c1.markdown(f"""
                    <div class="card-turno">
                        <h3>{row['Hora']} - {row['Paciente']}</h3>
                        <p>{row['Servicio']} | {deuda_html}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if btn_cobrar:
                        if c2.button("💵 Cobrar", key=f"pay_{row['ID_Turno']}"):
                            # Actualizar pago en BD Pacientes
                            idx = df_p[df_p['ID'] == p_data['ID']].index
                            if not idx.empty:
                                df_p.at[idx[0], 'Pagado'] = df_p.at[idx[0], 'Monto_Pactado']
                                manager._save_data("pacientes", df_p)
                                st.success("Pago registrado!")
                                st.rerun()
                                
                    if c3.button("📝 Renovar", key=f"ren_{row['ID_Turno']}"):
                        st.session_state['renovar_paciente'] = row['Paciente']
                        st.info("Ve a la pestaña 'Nuevo Ingreso' para completar la renovación.")

# --- MÓDULO 2: REGISTRO ---
elif menu == "📝 Nuevo Ingreso":
    st.header("Gestión de Pacientes")
    
    # Autocompletado si viene de renovar
    default_name = st.session_state.get('renovar_paciente', "")
    
    with st.form("form_alta"):
        c1, c2 = st.columns(2)
        nombre = c1.text_input("Nombre Completo", value=default_name)
        dni = c2.text_input("DNI")
        origen = c1.selectbox("Origen", ["Socio Gimnasio", "Captación Propia"])
        servicio = c2.selectbox("Servicio", list(PRECIOS.keys()))
        
        # Precio Automático
        precio_sug = manager.obtener_precio(servicio, origen)
        monto = st.number_input("Monto a Cobrar ($)", value=float(precio_sug))
        
        st.markdown("### 📅 Planificación")
        f_inicio = st.date_input("Fecha Inicio")
        h_fija = st.selectbox("Hora Preferida", HORARIOS)
        
        dias = []
        semanas = 0
        
        if "Plan" in servicio:
            st.info("Configuración de Plan (Múltiples Turnos)")
            dias = st.multiselect("Días Fijos", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"])
            semanas = st.number_input("Semanas a agendar", 1, 12, 4)
            cant_sesiones = 10 if "x10" in servicio else 5
        else:
            cant_sesiones = 1
            
        dx = st.text_area("Diagnóstico / Notas")
        
        if st.form_submit_button("💾 Guardar Paciente y Generar Agenda"):
            if not nombre:
                st.error("El nombre es obligatorio")
            else:
                datos = {
                    "DNI": dni, "Nombre": nombre, "Origen": origen,
                    "Servicio": servicio, "Monto_Pactado": monto,
                    "Fecha_Inicio": str(f_inicio), "Sesiones_Totales": cant_sesiones,
                    "Diagnostico": dx
                }
                
                with st.spinner("Procesando..."):
                    manager.registrar_paciente(datos, dias, semanas, h_fija)
                
                st.success("¡Paciente registrado exitosamente!")
                st.session_state.pop('renovar_paciente', None)
                st.rerun()

# --- MÓDULO 3: FINANZAS ---
elif menu == "💰 Finanzas":
    st.header("Panel Financiero")
    
    # Selector de Mes basado en datos reales
    df_p = manager._get_data("pacientes")
    if not df_p.empty:
        df_p['Fecha_Alta'] = pd.to_datetime(df_p['Fecha_Alta'], errors='coerce')
        opciones_mes = df_p['Fecha_Alta'].dt.strftime('%Y-%m').unique()
        # Eliminar NaT y ordenar
        opciones_mes = sorted([x for x in opciones_mes if str(x) != 'nan'], reverse=True)
        
        mes_sel = st.selectbox("Seleccionar Mes", opciones_mes)
        
        df_fin = manager.obtener_metricas_financieras(mes_sel)
        
        if df_fin is not None and not df_fin.empty:
            col1, col2, col3 = st.columns(3)
            
            total_bruto = df_fin['Pagado'].sum()
            total_comision = df_fin['Comision'].sum()
            total_neto = df_fin['Neto'].sum()
            
            col1.metric("Ingreso Bruto (Cobrado)", f"${total_bruto:,.0f}")
            col2.metric("Comisiones Cedidas", f"-${total_comision:,.0f}")
            col3.metric("Neto Elite", f"${total_neto:,.0f}", delta="Ganancia Real")
            
            st.markdown("### Detalle de Movimientos")
            st.dataframe(
                df_fin[['Fecha_Alta', 'Nombre', 'Servicio', 'Pagado', 'Comision', 'Neto']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning("No hay pagos registrados en este mes.")
    else:
        st.warning("No hay datos de pacientes aún.")
