"""
=============================================================================
 MODULO: GESTION DE CATEGORIAS
=============================================================================
Modulo: crear, eliminar y asignar profesor a las categorias (solo Administrador).
Diseno corporativo: contenedores con borde, botones primary, iconos Material.
=============================================================================
"""


import streamlit as st

from estilos import inject_css
from database import (obtener_categorias_config, obtener_usuarios,
                      crear_categoria, actualizar_profesor_categoria,
                      eliminar_categoria, obtener_jugadores)


def render_categorias() -> None:
    """Modulo: crear, eliminar y asignar profesor a las categorias (solo Administrador)."""
    inject_css()

    # Verificación de permisos
    permisos = st.session_state.user.get("permisos") or []
    rol = st.session_state.user.get("rol")
    if rol != "Administrador" and "Categorias" not in permisos:
        st.error("No tienes permisos para acceder a este módulo.", icon=":material/error:")
        return

    st.title(":material/category: Categorias")

    # Cargar usuarios una sola vez (evita N+1 queries)
    usuarios = obtener_usuarios()
    roster = [u["nombre"] for u in usuarios if u["rol"] != "Administrador"]

    with st.container(border=True):
        st.subheader(":material/description: Gestiona categorias de edad: crea, elimina o asigna profesor. Nada es fijo.")

    with st.container(border=True):
        st.subheader(":material/add_circle: Crear nueva categoria")
        
        if "msg_crear_exito" in st.session_state:
            st.success(st.session_state.msg_crear_exito, icon=":material/check_circle:")
            del st.session_state.msg_crear_exito

        with st.form("form_crear_cat", clear_on_submit=True):
            cc1, cc2 = st.columns([1.1, 1.4])
            with cc1:
                nombre_nueva = st.text_input("Nombre de la categoria *", placeholder="Ej: Sub-14")
            with cc2:
                # roster ya fue cargado arriba
                
                prof_sel = st.selectbox(
                    "Seleccionar profesor asignado", 
                    roster, 
                    index=None,
                    placeholder="Selecciona un profesor"
                )

            st.write("")
            crear = st.form_submit_button("CREAR CATEGORIA", use_container_width=True, type="primary")

            if crear:
                if not nombre_nueva.strip():
                    st.error("Ingresa un nombre para la categoria.", icon=":material/error:")
                else:
                    profesor_final = prof_sel if prof_sel else ""
                    if crear_categoria(nombre_nueva, profesor_final):
                        st.session_state.msg_crear_exito = f"Categoria {nombre_nueva.strip()} creada correctamente."
                        st.cache_data.clear()
                        st.rerun()

    with st.container(border=True):
        st.subheader(":material/list: Categorias actuales")

        if "msg_lista_exito" in st.session_state:
            st.success(st.session_state.msg_lista_exito, icon=":material/check_circle:")
            del st.session_state.msg_lista_exito
        if "msg_lista_error" in st.session_state:
            st.error(st.session_state.msg_lista_error, icon=":material/error:")
            del st.session_state.msg_lista_error

        categorias = obtener_categorias_config()
        if not categorias:
            st.info("Aun no hay categorias creadas. Usa el formulario de arriba para crear la primera.")
            return

        for cat in categorias:
            etiqueta_prof = cat["profesor"] or "Sin profesor asignado"
            with st.expander(f"{cat['nombre']} · {etiqueta_prof}"):
                # roster ya fue cargado arriba

                with st.form(f"form_actualizar_prof_{cat['nombre']}", clear_on_submit=True):
                    ec1, ec2 = st.columns([2, 1])
                    with ec1:
                        nuevo_prof_sel = st.selectbox(
                            "Seleccionar profesor asignado", 
                            roster, 
                            index=None,
                            placeholder="Selecciona un profesor"
                        )
                    with ec2:
                        st.write("")
                        st.write("")
                        guardar = st.form_submit_button("Guardar profesor", use_container_width=True, type="primary")

                    if guardar:
                        profesor_final = nuevo_prof_sel if nuevo_prof_sel else ""
                        if actualizar_profesor_categoria(cat["nombre"], profesor_final):
                            st.session_state.msg_lista_exito = f"Profesor actualizado correctamente para {cat['nombre']}."
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error("No se pudo actualizar el profesor", icon=":material/error:")

                # Botón eliminar
                st.write("")
                if st.button("Eliminar categoria", key=f"eliminar_{cat['nombre']}", use_container_width=True, type="secondary"):
                    # Verificar si hay jugadores en la categoria antes de intentar borrar
                    jugadores_en_cat = obtener_jugadores(cat["nombre"])
                    if jugadores_en_cat:
                        st.error(f"No se puede eliminar: hay {len(jugadores_en_cat)} jugador(es) en esta categoría.", icon=":material/error:")
                    else:
                        if eliminar_categoria(cat["nombre"]):
                            st.session_state.msg_lista_exito = f"Categoría {cat['nombre']} eliminada con éxito."
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error("Fallo al eliminar (revisa permisos o recarga la página).", icon=":material/error:")