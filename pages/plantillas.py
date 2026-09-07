"""
=============================================================================
 MODULO: PLANTILLAS Y REGISTROS
=============================================================================
Modulo: listado general de jugadores inscritos (solo Administrador).
Diseno corporativo: contenedores con borde, botones primary, iconos Material.
=============================================================================
"""


import io
from pathlib import Path

import pandas as pd
import streamlit as st

from estilos import inject_css
from database import (obtener_jugadores, obtener_categorias, obtener_profesor_de,
                      actualizar_jugador, eliminar_jugador, activar_jugador)



def format_cat(cat):
    if isinstance(cat, dict):
        return cat["nombre"]
    return cat

def render_plantillas() -> None:
    """Modulo: listado general de jugadores inscritos (solo Administrador)."""
    inject_css()

    # Verificación de permisos
    permisos = st.session_state.user.get("permisos") or []
    rol = st.session_state.user.get("rol")
    if rol != "Administrador" and "Plantillas" not in permisos:
        st.error("No tienes permisos para acceder a este módulo.", icon=":material/error:")
        return

    st.title(":material/table: Plantillas y Registros")
    
    if "msg_jugador_exito" in st.session_state:
        st.success(st.session_state.msg_jugador_exito)
        del st.session_state.msg_jugador_exito

    jugadores_todos = obtener_jugadores()
    if not jugadores_todos:
        st.info("Aun no hay jugadores registrados. Ve a Registrar Jugador para comenzar.")
        return

    categorias = obtener_categorias()

    tab1, tab2, tab3 = st.tabs(["Listado General", "Modificar Jugadores", "Carga Masiva (Excel)"])

    with tab1:
        with st.container(border=True):
            st.subheader(":material/analytics: Resumen")
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Jugadores", len(jugadores_todos))
            m2.metric("Categorias activas", len(categorias))
            fecha_raw = str(jugadores_todos[-1].get("fecha_registro", ""))
            fecha_corta = fecha_raw.split("T")[0] if "T" in fecha_raw else fecha_raw.split(" ")[0]
            m3.metric("Ultimo registro", fecha_corta)

            c_f1, c_f2 = st.columns(2)
            with c_f1:
                filtro_estado = st.selectbox("Estado", ["Activos", "Inactivos", "Todos"])
            with c_f2:
                filtro_categoria = st.selectbox("Filtrar por categoria", ["Todas"] + categorias, format_func=format_cat)

        jugadores_tabla = jugadores_todos
        if filtro_estado == "Activos":
            jugadores_tabla = [j for j in jugadores_tabla if j.get("estado") != "Inactivo"]
        elif filtro_estado == "Inactivos":
            jugadores_tabla = [j for j in jugadores_tabla if j.get("estado") == "Inactivo"]

        if filtro_categoria != "Todas":
            jugadores_tabla = [j for j in jugadores_tabla if j.get("categoria") == filtro_categoria["nombre"]]
            profesor_cat = filtro_categoria.get("profesor", "Sin asignar")
            st.caption(f"Profesor a cargo de {filtro_categoria['nombre']}: {profesor_cat or 'Sin asignar'}")

        if not jugadores_tabla:
            st.warning("No hay jugadores registrados con estos filtros todavia.")
        else:
            with st.container(border=True):
                st.subheader(":material/list: Listado de Jugadores")
                df = pd.DataFrame(jugadores_tabla)
                
                columnas_db = ["nombre", "rut", "categoria", "estado", "apoderado_nombre", "apoderado_telefono", "fecha_registro"]
                df = df[[col for col in columnas_db if col in df.columns]]
                
                if "estado" in df.columns:
                    df["estado"] = df["estado"].fillna("Activo")
                else:
                    df["estado"] = "Activo"
                
                if "fecha_registro" in df.columns:
                    df["fecha_registro"] = df["fecha_registro"].apply(lambda x: str(x).split("T")[0] if "T" in str(x) else str(x).split(" ")[0])

                df = df.rename(columns={
                    "nombre": "Nombre",
                    "rut": "RUT",
                    "categoria": "Categoria",
                    "estado": "Estado",
                    "apoderado_nombre": "Apoderado",
                    "apoderado_telefono": "Telefono Apoderado",
                    "fecha_registro": "Fecha Registro"
                })

                st.dataframe(df, width="stretch", hide_index=True)
                
                st.write("")
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name="Jugadores")
                
                st.download_button(
                    label=":material/download: Descargar Listado en Excel",
                    data=excel_buffer.getvalue(),
                    file_name="Listado_Jugadores.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )

    with tab2:
        with st.container(border=True):
            st.subheader(":material/manage_accounts: Modificar Jugador")
            st.write("Selecciona un jugador para actualizar su categoría, nombre, etc. o para eliminarlo.")
            
            opciones_jugadores = {f"{j['rut']} - {j['nombre']}": j for j in jugadores_todos}
            jugador_sel_str = st.selectbox(
                "Buscar y Seleccionar Jugador", 
                options=list(opciones_jugadores.keys()), 
                index=None, 
                placeholder="Escribe el nombre o RUT..."
            )
            
            if jugador_sel_str:
                j_data = opciones_jugadores[jugador_sel_str]
                
                with st.form(f"form_editar_{j_data['rut']}"):
                    st.markdown(f"**Editando a:** {j_data['nombre']} (RUT: {j_data['rut']})")
                    
                    st.markdown("---")
                    st.markdown("#### Datos del Jugador")
                    c1, c2 = st.columns(2)
                    with c1:
                        nuevo_nombre = st.text_input("Nombre Completo *", value=j_data["nombre"])
                        anio_actual = j_data.get("anio_nacimiento")
                        if not isinstance(anio_actual, (int, float)):
                            anio_actual = 2014
                        nuevo_anio = st.number_input("Año de Nacimiento *", value=int(anio_actual), step=1)
                    
                    with c2:
                        idx_cat = next((i for i, c in enumerate(categorias) if c["nombre"] == j_data["categoria"]), 0)
                        nueva_categoria = st.selectbox("Categoría *", categorias, index=idx_cat, format_func=format_cat)
                    
                    st.markdown("#### Datos del Apoderado")
                    c3, c4 = st.columns(2)
                    with c3:
                        nuevo_apo_nombre = st.text_input("Nombre del Apoderado *", value=j_data.get("apoderado_nombre", ""))
                        nuevo_apo_tel = st.text_input("Teléfono Apoderado *", value=j_data.get("apoderado_telefono", ""))
                        nuevo_tel_emergencia = st.text_input("Teléfono de Emergencia *", value=j_data.get("telefono_emergencia", ""))
                    with c4:
                        nuevo_apo_rut = st.text_input("RUT Apoderado *", value=j_data.get("apoderado_rut", ""))
                        nuevo_apo_correo = st.text_input("Correo Apoderado (Opcional)", value=j_data.get("apoderado_correo", ""))

                    st.markdown("---")
                    c5, c6 = st.columns(2)
                    with c5:
                        btn_guardar = st.form_submit_button("Guardar Cambios", type="primary", width="stretch")
                    
                    es_inactivo = j_data.get("estado") == "Inactivo"
                    
                    with c6:
                        if es_inactivo:
                            btn_activar = st.form_submit_button("Restaurar (Activar)", type="primary", width="stretch")
                            btn_eliminar = False
                        else:
                            btn_eliminar = st.form_submit_button("Dar de Baja (Inactivar)", type="secondary", width="stretch")
                            btn_activar = False
                        
                    if btn_guardar:
                        nuevos_datos = {
                            "nombre": nuevo_nombre.strip(),
                            "anio_nacimiento": nuevo_anio,
                            "categoria_id": nueva_categoria["id"] if isinstance(nueva_categoria, dict) else None,
                            "apoderado_nombre": nuevo_apo_nombre.strip(),
                            "apoderado_telefono": nuevo_apo_tel.strip(),
                            "telefono_emergencia": nuevo_tel_emergencia.strip(),
                            "apoderado_rut": nuevo_apo_rut.strip(),
                            "apoderado_correo": nuevo_apo_correo.strip()
                        }
                        campos_obligatorios = [nuevo_nombre, nuevo_apo_nombre, nuevo_apo_tel, nuevo_tel_emergencia, nuevo_apo_rut]
                        if not all(str(c).strip() for c in campos_obligatorios):
                            st.error("Los campos marcados con * son obligatorios.", icon=":material/error:")
                        elif actualizar_jugador(j_data["id"], nuevos_datos):
                            st.session_state.msg_jugador_exito = f"Datos de {nuevo_nombre} actualizados correctamente."
                            st.cache_data.clear()
                            st.rerun()
                            
                    if btn_eliminar:
                        if eliminar_jugador(j_data["id"]):
                            st.session_state.msg_jugador_exito = f"Jugador {j_data['nombre']} ha sido dado de baja."
                            st.cache_data.clear()
                            st.rerun()
                            
                    if btn_activar:
                        if activar_jugador(j_data["id"], nueva_categoria["id"] if isinstance(nueva_categoria, dict) else None):
                            st.session_state.msg_jugador_exito = f"Jugador {j_data['nombre']} ha sido restaurado exitosamente."
                            st.cache_data.clear()
                            st.rerun()

    with tab3:
        with st.container(border=True):
            st.subheader(":material/upload_file: Carga Masiva de Jugadores")
            st.write("Sube un archivo Excel para agregar o registrar múltiples jugadores rápidamente.")
            
            st.markdown("##### 1. Descarga la plantilla")
            
            ruta_plantilla = Path(__file__).parent.parent / "Plantilla_Oficial.xlsx"
            
            if ruta_plantilla.exists():
                with open(ruta_plantilla, "rb") as f:
                    template_data = f.read()
                st.download_button(
                    label=":material/download: Descargar Plantilla Oficial",
                    data=template_data,
                    file_name="Plantilla_Oficial.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                df_template = pd.DataFrame(columns=[
                    "Nombre Completo", "RUT (Ej: 12345678-9)", "Categoria", "Anio Nacimiento", 
                    "Nombre Apoderado", "RUT Apoderado", "Telefono Apoderado", 
                    "Telefono Emergencia", "Correo Apoderado"
                ])
                template_buffer = io.BytesIO()
                with pd.ExcelWriter(template_buffer, engine='openpyxl') as writer:
                    df_template.to_excel(writer, index=False, sheet_name="Plantilla")
                
                st.download_button(
                    label=":material/download: Descargar Plantilla (Autogenerada)",
                    data=template_buffer.getvalue(),
                    file_name="Plantilla_Generada.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            st.markdown("##### 2. Sube el Excel completado")
            archivo_subido = st.file_uploader("Selecciona el archivo", type=["xlsx", "xls"])
            
            if archivo_subido is not None:
                try:
                    df_subido = pd.read_excel(archivo_subido)
                    
                    if len(df_subido) > 500:
                        st.error("El archivo no puede tener más de 500 registros.", icon=":material/error:")
                    elif len(df_subido) > 0:
                        st.write(f"Se encontraron **{len(df_subido)}** registros en el archivo. Previsualización:")
                        st.dataframe(df_subido.head(), use_container_width=True)
                        
                        if st.button("Procesar y Guardar Jugadores", type="primary", use_container_width=True):
                            from database import guardar_jugador
                            from datetime import datetime
                            cat_map = {c["nombre"].strip().lower(): c["id"] for c in categorias}
                            
                            exitosos = 0
                            errores = 0
                            
                            with st.spinner("Guardando jugadores en la base de datos..."):
                                for index, row in df_subido.iterrows():
                                    try:
                                        # Manejar NaN y limpiar datos
                                        rut_str = str(row.get("RUT (Ej: 12345678-9)", "")).strip()
                                        nombre_str = str(row.get("Nombre Completo", "")).strip()
                                        
                                        if rut_str.lower() == "nan" or not rut_str or nombre_str.lower() == "nan" or not nombre_str:
                                            errores += 1
                                            continue
                                            
                                        from utils import validar_rut
                                        if not validar_rut(rut_str):
                                            errores += 1
                                            continue
                                        
                                        # Resolver categoría del Excel al ID de la BD
                                        cat_nombre = str(row.get("Categoria", "")).strip().lower()
                                        cat_id = cat_map.get(cat_nombre)
                                        
                                        # Año de nacimiento
                                        anio_raw = row.get("Anio Nacimiento", 2014)
                                        try:
                                            anio = int(anio_raw)
                                        except (ValueError, TypeError):
                                            anio = 2014
                                            
                                        jugador = {
                                            "rut": rut_str,
                                            "nombre": nombre_str,
                                            "anio_nacimiento": anio,
                                            "categoria_id": cat_id,
                                            "apoderado_nombre": str(row.get("Nombre Apoderado", "")).strip().replace("nan", ""),
                                            "apoderado_rut": str(row.get("RUT Apoderado", "")).strip().replace("nan", ""),
                                            "apoderado_telefono": str(row.get("Telefono Apoderado", "")).strip().replace("nan", ""),
                                            "telefono_emergencia": str(row.get("Telefono Emergencia", "")).strip().replace("nan", ""),
                                            "apoderado_correo": str(row.get("Correo Apoderado", "")).strip().replace("nan", ""),
                                            "fecha_registro": datetime.now().isoformat()
                                        }
                                        
                                        if guardar_jugador(jugador):
                                            exitosos += 1
                                        else:
                                            errores += 1
                                    except Exception as e:
                                        errores += 1
                                        
                            if exitosos > 0:
                                st.success(f"Se guardaron {exitosos} jugadores correctamente.", icon=":material/check_circle:")
                            if errores > 0:
                                st.error(f"Hubo {errores} registros con errores (datos incompletos o jugador ya existe).", icon=":material/error:")
                    else:
                        st.warning("El archivo Excel está vacío. Llena los datos usando la plantilla.", icon=":material/warning:")
                except Exception as e:
                    st.error(f"Error al leer el archivo Excel. Asegúrate de usar la plantilla correcta. Detalle: {e}", icon=":material/error:")

if __name__ == '__main__':
    import streamlit as st
    if 'authenticated' not in st.session_state or not st.session_state.authenticated:
        st.switch_page('app.py')
    else:
        render_plantillas()
