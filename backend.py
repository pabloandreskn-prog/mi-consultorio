import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import uuid

# --- CONFIGURACIÓN DE NEGOCIO ---
PRECIOS = {
    "Evaluación": 36000,
    "Sesión Individual": 24000,
    "Sesión Especializada": 36000,
    "Plan x 5": 110000,
    "Plan x10": 200000,
    "Masaje Zona A": {"Socio Gimnasio": 25000, "Captación Propia": 30000},
    "Masaje Zona B": {"Socio Gimnasio": 25000, "Captación Propia": 30000},
    "Masaje Completo": {"Socio Gimnasio": 38000, "Captación Propia": 45000},
}

HORARIOS = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "16:00", "17:00", "18:00", "19:00", "20:00"]

class EliteManager:
    def __init__(self):
        self.conn = st.connection("gsheets", type=GSheetsConnection)

    def _get_data(self, sheet):
        try:
            return self.conn.read(worksheet=sheet, ttl=0)
        except:
            return pd.DataFrame()

    def _save_data(self, sheet, df):
        self.conn.update(worksheet=sheet, data=df)

    def obtener_precio(self, servicio, origen):
        item = PRECIOS.get(servicio, 0)
        if isinstance(item, dict):
            return item.get(origen, 0)
        return item

    def registrar_paciente(self, datos_dict, dias_fijos=None, semanas=0, hora_fija=None):
        # 1. Guardar Paciente
        df_p = self._get_data("pacientes")
        
        # Aseguramos que el DF tenga las columnas correctas aunque esté vacío
        columnas_p = ["ID", "Fecha_Alta", "DNI", "Nombre", "Origen", "Servicio", "Monto_Pactado", "Pagado", "Sesiones_Totales", "Diagnostico", "Estado"]
        if df_p.empty:
             df_p = pd.DataFrame(columns=columnas_p)
        
        # Inyectamos datos calculados
        datos_dict["ID"] = str(uuid.uuid4())[:8]
        datos_dict["Fecha_Alta"] = str(datetime.now().date())
        datos_dict["Pagado"] = 0.0 # Por defecto no pagado
        datos_dict["Estado"] = "Activo"
        
        # Crear fila usando DataFrame constructor para evitar errores de columnas
        nueva_fila = pd.DataFrame([datos_dict])
        
        # Concatenar asegurando columnas
        df_final_p = pd.concat([df_p, nueva_fila], ignore_index=True)
        # Rellenar NaN con valores seguros para evitar errores futuros
        df_final_p = df_final_p.fillna("")
        self._save_data("pacientes", df_final_p)

        # 2. Generar Agenda (Turnos)
        turnos = []
        fecha_inicio = datetime.strptime(datos_dict["Fecha_Inicio"], "%Y-%m-%d")
        
        if "Plan" in datos_dict["Servicio"] and dias_fijos and semanas > 0:
            # Lógica Plan
            mapa_dias = {"Lunes":0, "Martes":1, "Miércoles":2, "Jueves":3, "Viernes":4}
            dias_num = [mapa_dias[d] for d in dias_fijos]
            
            sesiones_generadas = 0
            dia_actual = fecha_inicio
            limit = semanas * 7 + 14 # Buffer de dias
            
            for _ in range(limit):
                if sesiones_generadas >= datos_dict["Sesiones_Totales"]: break
                if dia_actual.weekday() in dias_num:
                    turnos.append({
                        "ID_Turno": str(uuid.uuid4())[:8],
                        "Fecha": str(dia_actual.date()),
                        "Hora": hora_fija,
                        "Paciente": datos_dict["Nombre"],
                        "Servicio": datos_dict["Servicio"],
                        "Estado": "Agendado"
                    })
                    sesiones_generadas += 1
                dia_actual += timedelta(days=1)
        else:
            # Lógica Sesión Única / Evaluación
            turnos.append({
                "ID_Turno": str(uuid.uuid4())[:8],
                "Fecha": datos_dict["Fecha_Inicio"],
                "Hora": hora_fija,
                "Paciente": datos_dict["Nombre"],
                "Servicio": datos_dict["Servicio"],
                "Estado": "Agendado"
            })

        # Guardar en Agenda
        if turnos:
            df_a = self._get_data("agenda")
            col_a = ["ID_Turno", "Fecha", "Hora", "Paciente", "Servicio", "Estado"]
            if df_a.empty: df_a = pd.DataFrame(columns=col_a)
            
            df_new_turnos = pd.DataFrame(turnos)
            df_final_a = pd.concat([df_a, df_new_turnos], ignore_index=True)
            self._save_data("agenda", df_final_a)
            
        return True

    def obtener_metricas_financieras(self, mes_anio):
        df_p = self._get_data("pacientes")
        if df_p.empty: return None

        # Convertir columnas numéricas de forma segura
        df_p['Monto_Pactado'] = pd.to_numeric(df_p['Monto_Pactado'], errors='coerce').fillna(0)
        df_p['Pagado'] = pd.to_numeric(df_p['Pagado'], errors='coerce').fillna(0)
        
        # Filtro de fecha (por Alta o Inicio)
        df_p['Fecha_DT'] = pd.to_datetime(df_p['Fecha_Alta'], errors='coerce')
        df_filtrado = df_p[df_p['Fecha_DT'].dt.strftime('%Y-%m') == mes_anio].copy()
        
        if df_filtrado.empty: return pd.DataFrame()

        # Cálculos
        def calc_comision(row):
            tasa = 0.30 if row['Origen'] == "Socio Gimnasio" else 0.20
            # La comisión se calcula sobre lo COBRADO (Pagado), no sobre lo pactado
            return row['Pagado'] * tasa

        df_filtrado['Comision'] = df_filtrado.apply(calc_comision, axis=1)
        df_filtrado['Neto'] = df_filtrado['Pagado'] - df_filtrado['Comision']
        
        return df_filtrado
