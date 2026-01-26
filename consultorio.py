import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Gestión de Consultorio", layout="wide", page_icon="🏥")

# --- FUNCIONES DE BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect('consultorio.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS pacientes (
                    id INTEGER PRIMARY KEY,
                    nombre TEXT,
                    edad INTEGER,
                    sexo TEXT,
                    patologia TEXT,
                    contacto TEXT,
                    evaluacion_inicial TEXT,
                    tipo_paciente TEXT,
                    origen TEXT,
                    plan_actual TEXT,
                    sesiones_restantes INTEGER
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS turnos (
                    id INTEGER PRIMARY KEY,
                    paciente_id INTEGER,
                    nombre_paciente TEXT,
                    fecha DATE,
                    hora TIME,
                    tipo_servicio TEXT,
                    detalle_servicio TEXT,
                    FOREIGN KEY(paciente_id) REFERENCES pacientes(id)
                )''')
    conn.commit()
    conn.close()

def agregar_paciente(nombre, edad, sexo, patologia, contacto, eva_ini, tipo, origen, plan, sesiones):
    conn = sqlite3.connect('consultorio.db')
    c = conn.cursor()
    c.execute('''INSERT INTO pacientes (nombre, edad, sexo, patologia, contacto, evaluacion_inicial, tipo_paciente, origen, plan_actual, sesiones_restantes)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                 (nombre, edad, sexo, patologia, contacto, eva_ini, tipo, origen, plan, sesiones))
    conn.commit()
    conn.close()

def actualizar_paciente(id_paciente, nombre, edad, sexo, patologia, contacto, plan, sesiones):
    conn = sqlite3.connect('consultorio.db')
    c = conn.cursor()
    c.execute('''UPDATE pacientes SET nombre=?, edad=?, sexo=?, patologia=?, contacto=?, plan_actual=?, sesiones_restantes=?
                 WHERE id=?''', (nombre, edad, sexo, patologia, contacto, plan, sesiones, id_paciente))
    conn.commit()
    conn.close()

def eliminar_paciente(id_paciente):
    conn = sqlite3.connect('consultorio.db')
    c = conn.cursor()
    c.execute('DELETE FROM pacientes WHERE id=?', (id_paciente,))
    # Opcional: Eliminar también sus turnos
    c.execute('DELETE FROM turnos WHERE paciente_id=?', (id_paciente,))
    conn.commit()
    conn.close()

def agendar_turno(paciente_id, nombre, fecha, hora, tipo_servicio, detalle):
    conn = sqlite3.connect('consultorio.db')
    c = conn.cursor()
    c.execute('''INSERT INTO turnos (paciente_id, nombre_paciente, fecha, hora, tipo_servicio, detalle_servicio)
                 VALUES (?, ?, ?, ?, ?, ?)''', (paciente_id, nombre, fecha, hora, tipo_servicio, detalle))
    c.execute('UPDATE pacientes SET sesiones_restantes = sesiones_restantes - 1 WHERE id = ? AND sesiones_restantes > 0', (paciente_id,))
    conn.commit()
    conn.close()

def obtener_pacientes():
    conn = sqlite3.connect('consultorio.db')
    df = pd.read_sql_query("SELECT * FROM pacientes", conn)
    conn.close()
    return df

def obtener_turnos():
    conn = sqlite3.connect('consultorio.db')
    df = pd.read_sql_query("SELECT * FROM turnos ORDER BY fecha, hora", conn)
    conn.close()
    return df

# --- INICIALIZAR APP ---
init_db()

# --- INTERFAZ GRÁFICA ---
st.title("🏥 Gestión de Consultorio y Agenda V2.0")

menu = st.sidebar.selectbox("Menú Principal", 
    ["Registro de Pacientes", "Administrar Pacientes (Editar/Borrar)", "Agenda y Turnos", "Alertas y Estado"])

# 1. REGISTRO
if menu == "Registro de Pacientes":
    st.header("Nuevo Paciente")
    with st.form("form_registro"):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre Completo")
            edad = st.number_input("Edad", min_value=0, max_value=120)
            sexo = st.selectbox("Sexo", ["Femenino", "Masculino", "Otro"])
            contacto = st.text_input("Contacto (Tel/Email)")
        with col2:
            patologia = st.text_input("Patología / Motivo")
            origen = st.radio("Origen", ["Gimnasio", "Captación Propia"])
            tipo_paciente = st.radio("Estado", ["Nuevo", "Recurrente"])
            evaluacion = st.checkbox("¿Evaluación Inicial Realizada?")
        
        st.subheader("Plan Inicial")
        plan_seleccionado = st.selectbox("Seleccionar Plan", ["Sin Plan (Sesión suelta)", "Plan X5", "Plan X10"])
        
        sesiones = 0
        if plan_seleccionado == "Plan X5": sesiones = 5
        elif plan_seleccionado == "Plan X10": sesiones = 10
            
        submitted = st.form_submit_button("Guardar Paciente")
        if submitted:
            if nombre:
                eva_txt = "Sí" if evaluacion else "No"
                agregar_paciente(nombre, edad, sexo, patologia, contacto, eva_txt, tipo_paciente, origen, plan_seleccionado, sesiones)
                st.success(f"Paciente {nombre} registrado.")
            else:
                st.error("Nombre obligatorio.")

# 2. ADMINISTRAR (NUEVA SECCIÓN)
elif menu == "Administrar Pacientes (Editar/Borrar)":
    st.header("🛠️ Edición y Eliminación")
    df = obtener_pacientes()
    
    if not df.empty:
        paciente_a_editar = st.selectbox("Seleccionar Paciente para Editar/Borrar", df['nombre'].tolist())
        datos_paciente = df[df['nombre'] == paciente_a_editar].iloc[0]
        
        with st.expander("📝 Editar Datos del Paciente", expanded=True):
            with st.form("form_edicion"):
                nuevo_nombre = st.text_input("Nombre", value=datos_paciente['nombre'])
                nueva_edad = st.number_input("Edad", value=datos_paciente['edad'])
                nuevo_sexo = st.selectbox("Sexo", ["Femenino", "Masculino", "Otro"], index=["Femenino", "Masculino", "Otro"].index(datos_paciente['sexo']))
                nueva_patologia = st.text_input("Patología", value=datos_paciente['patologia'])
                nuevo_contacto = st.text_input("Contacto", value=datos_paciente['contacto'])
                
                nuevo_plan = st.selectbox("Plan Actual", ["Sin Plan (Sesión suelta)", "Plan X5", "Plan X10"], index=["Sin Plan (Sesión suelta)", "Plan X5", "Plan X10"].index(datos_paciente['plan_actual']))
                nuevas_sesiones = st.number_input("Sesiones Restantes", value=datos_paciente['sesiones_restantes'])
                
                if st.form_submit_button("💾 Guardar Cambios"):
                    actualizar_paciente(datos_paciente['id'], nuevo_nombre, nueva_edad, nuevo_sexo, nueva_patologia, nuevo_contacto, nuevo_plan, nuevas_sesiones)
                    st.success("Datos actualizados. Recarga la página si no ves los cambios.")
                    st.rerun()

        st.markdown("---")
        with st.expander("🗑️ Zona de Peligro (Eliminar)"):
            st.warning(f"¿Estás seguro de que deseas eliminar a {paciente_a_editar}? Esta acción no se puede deshacer.")
            if st.button("Sí, Eliminar Paciente Definitivamente"):
                eliminar_paciente(datos_paciente['id'])
                st.error("Paciente eliminado.")
                st.rerun()
    else:
        st.info("No hay pacientes para editar.")

# 3. AGENDA
elif menu == "Agenda y Turnos":
    st.header("📅 Agenda")
    df_pacientes = obtener_pacientes()
    if not df_pacientes.empty:
        paciente_sel = st.selectbox("Paciente", df_pacientes['nombre'].tolist())
        id_paciente = df_pacientes[df_pacientes['nombre'] == paciente_sel]['id'].values[0]
        
        col1, col2 = st.columns(2)
        with col1:
            fecha = st.date_input("Fecha", min_value=datetime.today())
            hora = st.time_input("Hora")
        with col2:
            servicio = st.selectbox("Servicio", ["Sesión Individual", "Masoterapia"])
            detalle = "-"
            if servicio == "Masoterapia":
                detalle = st.radio("Zona", ["Cuerpo Completo", "Parcial"])
        
        if st.button("Confirmar Turno"):
            agendar_turno(id_paciente, paciente_sel, fecha, hora, servicio, detalle)
            st.success("Turno agendado.")
            st.rerun() # Refrescar para ver el turno abajo inmediatamente
            
    st.divider()
    st.subheader("Próximos Turnos")
    df_turnos = obtener_turnos()
    if not df_turnos.empty:
        st.dataframe(df_turnos[['fecha', 'hora', 'nombre_paciente', 'tipo_servicio', 'detalle_servicio']], use_container_width=True)

# 4. ALERTAS
elif menu == "Alertas y Estado":
    st.header("🔔 Estado de Planes")
    df = obtener_pacientes()
    if not df.empty:
        df_planes = df[df['plan_actual'] != "Sin Plan (Sesión suelta)"]
        for _, row in df_planes.iterrows():
            rest = row['sesiones_restantes']
            nom = row['nombre']
            if rest <= 1: st.error(f"⚠️ {nom}: Quedan {rest} sesiones")
            elif rest <= 3: st.warning(f"🔸 {nom}: Quedan {rest} sesiones")
            else: st.success(f"✅ {nom}: Quedan {rest} sesiones")
        st.divider()
        st.write("Base de Datos Completa:")
        st.dataframe(df)