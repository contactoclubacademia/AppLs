"""
=============================================================================
 MODULO: PLANTILLAS Y REGISTROS
=============================================================================
Modulo: listado general de jugadores inscritos (solo Administrador).
Diseno corporativo: contenedores con borde, botones primary, iconos Material.
=============================================================================
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import streamlit as st

from estilos import inject_css
from database import (obtener_jugadores, obtener_categorias, obtener_profesor_de,
                      actualizar_jugador, eliminar_jugador)


def render_plantillas() -> None:
    """Modulo: listado general de jugadores inscritos (solo Administrador)."""
    inject_css()

    st.title(":material/table: Plantillas y Registros")
    
    if "msg_jugador_exito" in st.session_state:
        st.success(st.session_state.msg_jugador_exito)
        del st.session_state.msg_jugador_exito

    jugadores_todos = obtener_jugadores()
    if not jugadores_todos:
        st.info("Aun no hay jugadores registrados. Ve a Registrar Jugador para comenzar.")
        return

    categorias = obtener_categorias()

    tab1, tab2 = st.tabs(["Listado General", "Modificar Jugadores"])

    with tab1:
        with st.container(border=True):
            st.subheader(":material/analytics: Resumen")
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Jugadores", len(jugadores_todos))
            m2.metric("Categorias activas", len(categorias))
            fecha_raw = str(jugadores_todos[-1].get("fecha_registro", ""))
            fecha_corta = fecha_raw.split("T")[0] if "T" in fecha_raw else fecha_raw.split(" ")[0]
            m3.metric("Ultimo registro", fecha_corta)

            filtro_categoria = st.selectbox("Filtrar por categoria", ["Todas"] + categorias)

        if filtro_categoria != "Todas":
            jugadores_tabla = obtener_jugadores(filtro_categoria)
            profesor_cat = obtener_profesor_de(filtro_categoria)
            st.caption(f"Profesor a cargo de {filtro_categoria}: {profesor_cat or 'Sin asignar'}")
        else:
            jugadores_tabla = jugadores_todos

        if not jugadores_tabla:
            st.warning("No hay jugadores registrados en esta categoria todavia.")
        else:
            with st.container(border=True):
                st.subheader(":material/list: Listado de Jugadores")
                df = pd.DataFrame(jugadores_tabla)
                
                # Filtrar solo las columnas que existen (sin 'posicion' que ya no se pide)
                columnas_db = ["nombre", "rut", "categoria", "apoderado_nombre", "apoderado_telefono", "fecha_registro"]
                df = df[[col for col in columnas_db if col in df.columns]]
                
                # Formatear la fecha para que se vea corta (solo YYYY-MM-DD)
                if "fecha_registro" in df.columns:
                    df["fecha_registro"] = df["fecha_registro"].apply(lambda x: str(x).split("T")[0] if "T" in str(x) else str(x).split(" ")[0])

                df.columns = ["Nombre", "RUT", "Categoria", "Apoderado", "Telefono Apoderado", "Fecha Registro"]

                st.dataframe(df, width="stretch", hide_index=True)

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
                        idx_cat = categorias.index(j_data["categoria"]) if j_data["categoria"] in categorias else 0
                        nueva_categoria = st.selectbox("Categoría *", categorias, index=idx_cat)
                    
                    st.markdown("#### Datos del Apoderado")
                    c3, c4 = st.columns(2)
                    with c3:
                        nuevo_apo_nombre = st.text_input("Nombre del Apoderado *", value=j_data.get("apoderado_nombre", ""))
                        nuevo_apo_tel = st.text_input("Teléfono Apoderado *", value=j_data.get("apoderado_telefono", ""))
                        nuevo_tel_emergencia = st.text_input("Teléfono de Emergencia *", value=j_data.get("telefono_emergencia", ""))
                    with c4:
                        nuevo_apo_rut = st.text_input("RUT Apoderado *", value=j_data.get("apoderado_rut", ""))
                        nuevo_apo_correo = st.text_input("Correo Apoderado *", value=j_data.get("apoderado_correo", ""))

                    st.markdown("---")
                    c5, c6 = st.columns(2)
                    with c5:
                        btn_guardar = st.form_submit_button("Guardar Cambios", type="primary", width="stretch")
                    with c6:
                        btn_eliminar = st.form_submit_button("Eliminar Jugador", type="secondary", width="stretch")
                        
                    if btn_guardar:
                        nuevos_datos = {
                            "nombre": nuevo_nombre.strip(),
                            "anio_nacimiento": nuevo_anio,
                            "categoria": nueva_categoria,
                            "apoderado_nombre": nuevo_apo_nombre.strip(),
                            "apoderado_telefono": nuevo_apo_tel.strip(),
                            "telefono_emergencia": nuevo_tel_emergencia.strip(),
                            "apoderado_rut": nuevo_apo_rut.strip(),
                            "apoderado_correo": nuevo_apo_correo.strip()
                        }
                        campos_obligatorios = [nuevo_nombre, nuevo_apo_nombre, nuevo_apo_tel, nuevo_tel_emergencia, nuevo_apo_rut, nuevo_apo_correo]
                        if not all(str(c).strip() for c in campos_obligatorios):
                            st.error("Los campos marcados con * son obligatorios.")
                        elif actualizar_jugador(j_data["rut"], nuevos_datos):
                            st.session_state.msg_jugador_exito = f"Datos de {nuevo_nombre} actualizados correctamente."
                            st.cache_data.clear()
                            st.cache_resource.clear()
                            st.rerun()
                            
                    if btn_eliminar:
                        if eliminar_jugador(j_data["rut"]):
                            st.session_state.msg_jugador_exito = f"Jugador {j_data['nombre']} eliminado del sistema."
                            st.cache_data.clear()
                            st.cache_resource.clear()
                            st.rerun()