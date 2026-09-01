"""
=============================================================================
 MODULO: GESTION DE CATEGORIAS
=============================================================================
Modulo: crear, eliminar y asignar profesor a las categorias (solo Administrador).
Diseno corporativo: contenedores con borde, botones primary, iconos Material.
=============================================================================
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from estilos import inject_css
from database import (obtener_categorias_config, obtener_profesores_roster,
                      crear_categoria, actualizar_profesor_categoria,
                      eliminar_categoria, obtener_jugadores)


def render_categorias() -> None:
    """Modulo: crear, eliminar y asignar profesor a las categorias (solo Administrador)."""
    inject_css()

    st.title(":material/category: Categorias")

    with st.container(border=True):
        st.subheader(":material/description: Gestiona categorias de edad: crea, elimina o asigna profesor. Nada es fijo.")

    with st.container(border=True):
        st.subheader(":material/add_circle: Crear nueva categoria")
        
        # Estado inicial para limpiar el form manualmente
        if "nombre_nueva_txt" not in st.session_state: st.session_state["nombre_nueva_txt"] = ""
        if "prof_sel_nueva" not in st.session_state: st.session_state["prof_sel_nueva"] = None
        if "prof_nuevo_nueva" not in st.session_state: st.session_state["prof_nuevo_nueva"] = ""

        cc1, cc2 = st.columns([1.1, 1.4])
        with cc1:
            nombre_nueva = st.text_input("Nombre de la categoria *", placeholder="Ej: Sub-14", key="nombre_nueva_txt")
        with cc2:
            roster = obtener_profesores_roster()
            prof_sel = st.selectbox(
                "Seleccionar profesor existente", 
                roster, 
                index=None,
                placeholder="Selecciona un profesor",
                key="prof_sel_nueva"
            )
            prof_nuevo = st.text_input(
                "O escribir un nuevo profesor", placeholder="Nombre y apellidos",
                key="prof_nuevo_nueva"
            )

        st.write("")
        crear = st.button("CREAR CATEGORIA", use_container_width=True, type="primary")

        if "msg_crear_exito" in st.session_state:
            st.success(st.session_state.msg_crear_exito)
            del st.session_state.msg_crear_exito

        if crear:
            if prof_sel and prof_nuevo.strip():
                st.error("⚠️ No puedes seleccionar un profesor existente y escribir uno nuevo al mismo tiempo. Por favor, deja uno en blanco.")
            elif not nombre_nueva.strip():
                st.error("Ingresa un nombre para la categoria.")
            else:
                profesor_final = prof_nuevo.strip() if prof_nuevo.strip() else (prof_sel if prof_sel else "")
                if crear_categoria(nombre_nueva, profesor_final):
                    st.session_state.msg_crear_exito = f"Categoria {nombre_nueva.strip()} creada correctamente."
                    # Limpiar formulario
                    st.session_state.nombre_nueva_txt = ""
                    st.session_state.prof_sel_nueva = None
                    st.session_state.prof_nuevo_nueva = ""
                    st.rerun()

    with st.container(border=True):
        st.subheader(":material/list: Categorias actuales")

        if "msg_lista_exito" in st.session_state:
            st.success(st.session_state.msg_lista_exito)
            del st.session_state.msg_lista_exito
        if "msg_lista_error" in st.session_state:
            st.error(st.session_state.msg_lista_error)
            del st.session_state.msg_lista_error

        categorias = obtener_categorias_config()
        if not categorias:
            st.info("Aun no hay categorias creadas. Usa el formulario de arriba para crear la primera.")
            return

        for cat in categorias:
            etiqueta_prof = cat["profesor"] or "Sin profesor asignado"
            with st.expander(f"{cat['nombre']} · {etiqueta_prof}"):
                roster = obtener_profesores_roster()

                ec1, ec2 = st.columns([2, 1])
                with ec1:
                    nuevo_prof_sel = st.selectbox(
                        "Seleccionar profesor existente", 
                        roster, 
                        index=None,
                        placeholder="Selecciona un profesor",
                        key=f"prof_sel_{cat['nombre']}"
                    )
                    nuevo_prof_texto = st.text_input(
                        "O nuevo profesor", placeholder="Escribe aquí para asignar uno nuevo",
                        key=f"prof_txt_{cat['nombre']}"
                    )
                with ec2:
                    st.write("")
                    st.write("")
                    guardar = st.button("Guardar profesor", key=f"btn_save_{cat['nombre']}", use_container_width=True, type="primary")

                if guardar:
                    if nuevo_prof_sel and nuevo_prof_texto.strip():
                        st.error("⚠️ No puedes seleccionar un profesor y escribir uno nuevo a la vez. Por favor, deja uno en blanco.")
                    else:
                        profesor_final = nuevo_prof_texto.strip() if nuevo_prof_texto.strip() else (nuevo_prof_sel if nuevo_prof_sel else "")
                        if actualizar_profesor_categoria(cat["nombre"], profesor_final):
                            st.session_state.msg_lista_exito = f"Profesor actualizado correctamente para {cat['nombre']}."
                            # Limpiar campos tras guardar
                            st.session_state[f"prof_txt_{cat['nombre']}"] = ""
                            st.session_state[f"prof_sel_{cat['nombre']}"] = None
                            st.rerun()
                        else:
                            st.error("No se pudo actualizar el profesor")

                # Botón eliminar
                st.write("")
                if st.button("Eliminar categoria", key=f"eliminar_{cat['nombre']}", use_container_width=True, type="secondary"):
                    # Verificar si hay jugadores en la categoria antes de intentar borrar
                    jugadores_en_cat = [j for j in obtener_jugadores(cat["nombre"])]
                    if jugadores_en_cat:
                        st.error(f"No se puede eliminar: hay {len(jugadores_en_cat)} jugador(es) en esta categoría.")
                    else:
                        if eliminar_categoria(cat["nombre"]):
                            st.session_state.msg_lista_exito = f"Categoría {cat['nombre']} eliminada con éxito."
                            st.cache_data.clear()
                            st.cache_resource.clear()
                            st.rerun()
                        else:
                            st.error("Fallo al eliminar (revisa permisos o recarga la página).")