import os
import pandas as pd
from supabase import create_client, Client
import math

def get_supabase_clients() -> tuple[Client, Client]:
    # Leer variables usando TOML parser manual para evitar problemas de contexto de Streamlit
    try:
        import toml
        secrets = toml.load(".streamlit/secrets.toml")
        url_1 = secrets.get("SUPABASE_URL")
        key_1 = secrets.get("SUPABASE_KEY")
        
        url_2 = secrets.get("SUPABASE_DW_URL")
        key_2 = secrets.get("SUPABASE_DW_KEY")
    except Exception:
        # Fallback si por alguna razon toml no sirve
        import streamlit as st
        url_1 = st.secrets["SUPABASE_URL"]
        key_1 = st.secrets["SUPABASE_KEY"]
        
        url_2 = st.secrets["SUPABASE_DW_URL"]
        key_2 = st.secrets["SUPABASE_DW_KEY"]
        
    return create_client(url_1, key_1), create_client(url_2, key_2)

def clean_nan(d):
    """Limpia los valores NaN de un diccionario antes de enviarlos a Supabase"""
    if isinstance(d, list):
        return [clean_nan(i) for i in d]
    if isinstance(d, dict):
        return {k: clean_nan(v) for k, v in d.items()}
    if isinstance(d, float) and math.isnan(d):
        return None
    return d

def run_etl():
    print("Iniciando proceso ETL (Supabase -> Supabase DW)...")
    try:
        supa_oltp, supa_dw = get_supabase_clients()
    except Exception as e:
        print(f"Error al conectar con Supabase: {e}")
        return
    
    # 1. Extraer datos crudos
    print("1. Extrayendo datos desde Supabase Transaccional (App)...")
    jugadores_data = supa_oltp.table("jugadores").select("*").execute().data
    categorias_data = supa_oltp.table("categorias").select("*").execute().data
    pagos_data = supa_oltp.table("pagos").select("*").execute().data
    asistencia_data = supa_oltp.table("asistencia").select("*").execute().data
    
    # Convertir a DataFrames para fácil manipulación
    df_jugadores = pd.DataFrame(jugadores_data)
    df_categorias = pd.DataFrame(categorias_data)
    df_pagos = pd.DataFrame(pagos_data)
    df_asistencia = pd.DataFrame(asistencia_data)
    
    print("2. Transformando datos (Modelo Estrella)...")
    
    # --- DIMENSIONES ---
    # dim_jugador
    if not df_jugadores.empty:
        dim_jugador = df_jugadores[["id", "rut", "nombre", "anio_nacimiento"]].rename(
            columns={"id": "id_jugador"}
        )
    else:
        dim_jugador = pd.DataFrame(columns=["id_jugador", "rut", "nombre", "anio_nacimiento"])
        
    # dim_categoria
    if not df_categorias.empty:
        dim_categoria = df_categorias[["id", "nombre", "profesor"]].rename(
            columns={"id": "id_categoria", "nombre": "nombre_categoria"}
        )
    else:
        dim_categoria = pd.DataFrame(columns=["id_categoria", "nombre_categoria", "profesor"])
        
    # dim_tiempo (Generar tabla basada en fechas de asistencia y pagos)
    fechas_asistencia = df_asistencia['fecha'].unique() if not df_asistencia.empty else []
    fechas_pagos = df_pagos['fecha_pago'].unique() if not df_pagos.empty else []
    
    todas_fechas = list(set(fechas_asistencia).union(set(fechas_pagos)))
    
    if todas_fechas:
        df_fechas = pd.DataFrame({"fecha_str": todas_fechas})
        df_fechas['fecha'] = pd.to_datetime(df_fechas['fecha_str'])
        
        meses_es = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
                    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
        
        dim_tiempo = pd.DataFrame({
            "id_tiempo": df_fechas['fecha'].dt.strftime("%Y%m%d"),
            "fecha": df_fechas['fecha'].dt.strftime("%Y-%m-%d"),
            "dia": df_fechas['fecha'].dt.day,
            "mes": df_fechas['fecha'].dt.month,
            "anio": df_fechas['fecha'].dt.year,
            "nombre_mes": df_fechas['fecha'].dt.month.map(meses_es)
        })
    else:
        dim_tiempo = pd.DataFrame(columns=["id_tiempo", "fecha", "dia", "mes", "anio", "nombre_mes"])

    # --- HECHOS ---
    
    # fact_pagos
    if not df_pagos.empty:
        fact_pagos = df_pagos[["id", "jugador_id", "fecha_pago", "monto", "metodo"]].rename(
            columns={"id": "id_pago"}
        )
        fact_pagos["fecha_pago"] = pd.to_datetime(fact_pagos["fecha_pago"])
        fact_pagos["id_tiempo"] = fact_pagos["fecha_pago"].dt.strftime("%Y%m%d")
        fact_pagos = fact_pagos.drop(columns=["fecha_pago"])
    else:
        fact_pagos = pd.DataFrame(columns=["id_pago", "jugador_id", "id_tiempo", "monto", "metodo"])

    # fact_asistencia
    if not df_asistencia.empty:
        fact_asistencia = df_asistencia[["id", "jugador_id", "categoria_id", "fecha", "estado"]].rename(
            columns={"id": "id_asistencia"}
        )
        fact_asistencia["fecha"] = pd.to_datetime(fact_asistencia["fecha"])
        fact_asistencia["id_tiempo"] = fact_asistencia["fecha"].dt.strftime("%Y%m%d")
        fact_asistencia = fact_asistencia.drop(columns=["fecha"])
    else:
        fact_asistencia = pd.DataFrame(columns=["id_asistencia", "jugador_id", "categoria_id", "id_tiempo", "estado"])
        
    print("3. Cargando datos en Supabase (Data Warehouse)...")
    
    def upsert_dataframe(table_name, df, id_col):
        if df.empty:
            return
        # Convertir a dict y limpiar NaNs (Supabase JSON builder no soporta NaN)
        records = clean_nan(df.to_dict(orient="records"))
        
        # Eliminar todos los registros (borrado completo) - esto es válido en DW pequeños
        # Si hubiera miles de registros, se debería usar UPSERT, pero Supabase Python no 
        # soporta truncates nativos de manera simple, usaremos un truco:
        # Ya que tenemos un constraint ON DELETE CASCADE, podemos borrar solo las dimensiones,
        # pero es más fácil simplemente hacer UPSERT (si un id existe, lo pisa, si no, lo inserta).
        try:
            res = supa_dw.table(table_name).upsert(records).execute()
        except Exception as e:
            print(f"Error al subir tabla {table_name}: {e}")

    try:
        # Upsert Dimensiones
        upsert_dataframe("dim_jugador", dim_jugador, "id_jugador")
        upsert_dataframe("dim_categoria", dim_categoria, "id_categoria")
        upsert_dataframe("dim_tiempo", dim_tiempo, "id_tiempo")
        
        # Upsert Hechos
        upsert_dataframe("fact_pagos", fact_pagos, "id_pago")
        upsert_dataframe("fact_asistencia", fact_asistencia, "id_asistencia")
    except Exception as e:
        print(f"Error fatal durante la carga: {e}")
        return
        
    print("Proceso ETL completado con éxito. Los datos están ahora en la nube.")

if __name__ == "__main__":
    run_etl()
