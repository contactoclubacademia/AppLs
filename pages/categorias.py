"""
=============================================================================
 MODULO: GESTION DE CATEGORIAS
=============================================================================
Modulo: crear, eliminar y asignar profesor a las categorias (solo Administrador).
Diseno corporativo: contenedores con borde, botones primary, iconos Material.
=============================================================================
"""


import streamlit as st

from database import (obtener_categorias, obtener_profesores,
                      crear_categoria, actualizar_profesor_categoria,
                      eliminar_categoria, obtener_jugadores, desvincular_jugadores_categoria)
from utils import verificar_permisos


def render_categorias() -> None:
    """Modulo: crear, eliminar y asignar profesor a las categorias (solo Administrador)."""

    # Verificación de permisos
    if not verificar_permisos("Categorias"):
        return


    st.title(":material/category: Categorias")

    # Cargar profesores una sola vez para usar en combos
    profesores = obtener_profesores()
    nombres_profesores = [p["nombre"] for p in profesores]
    mapa_profesores = {p["nombre"]: p["id"] for p in profesores}

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
                    nombres_profesores, 
                    index=None,
                    placeholder="Selecciona un profesor"
                )

            st.write("")
            crear = st.form_submit_button("CREAR CATEGORIA", width="stretch", type="primary")

            if crear:
                if not nombre_nueva.strip():
                    st.error("Ingresa un nombre para la categoria.", icon=":material/error:")
                else:
                    profesor_final = mapa_profesores.get(prof_sel) if prof_sel else None
                    if crear_categoria(nombre_nueva, profesor_final):
                        st.session_state.msg_crear_exito = f"Categoria {nombre_nueva.strip()} creada correctamente."
                        obtener_categorias.clear()
                        st.rerun()

    with st.container(border=True):
        st.subheader(":material/list: Categorias actuales")

        if "msg_lista_exito" in st.session_state:
            st.success(st.session_state.msg_lista_exito, icon=":material/check_circle:")
            del st.session_state.msg_lista_exito
        if "msg_lista_error" in st.session_state:
            st.error(st.session_state.msg_lista_error, icon=":material/error:")
            del st.session_state.msg_lista_error

        categorias = obtener_categorias()
        if not categorias:
            st.info("Aun no hay categorias creadas. Usa el formulario de arriba para crear la primera.")
            return

        for cat in categorias:
            etiqueta_prof = cat.get("profesor_nombre", "Sin profesor asignado")
            with st.expander(f"{cat['nombre']} · {etiqueta_prof}"):
                # roster ya fue cargado arriba

                with st.form(f"form_actualizar_prof_{cat['id']}", clear_on_submit=True):
                    ec1, ec2 = st.columns([2, 1])
                    with ec1:
                        nuevo_prof_sel = st.selectbox(
                            "Seleccionar profesor asignado", 
                            nombres_profesores, 
                            index=None,
                            placeholder="Selecciona un profesor"
                        )
                    with ec2:
                        st.write("")
                        st.write("")
                        guardar = st.form_submit_button("Guardar profesor", width="stretch", type="primary")

                    if guardar:
                        profesor_final = mapa_profesores.get(nuevo_prof_sel) if nuevo_prof_sel else None
                        if actualizar_profesor_categoria(cat["id"], profesor_final):
                            st.session_state.msg_lista_exito = f"Profesor actualizado correctamente para {cat['nombre']}."
                            obtener_categorias.clear()
                            st.rerun()
                        else:
                            st.error("No se pudo actualizar el profesor", icon=":material/error:")

                # Botón eliminar
                st.write("")
                # Estado para la confirmación de eliminación
                if f"confirmar_eliminar_{cat['id']}" not in st.session_state:
                    st.session_state[f"confirmar_eliminar_{cat['id']}"] = False

                if not st.session_state[f"confirmar_eliminar_{cat['id']}"]:
                    if st.button("Eliminar categoria", key=f"eliminar_{cat['id']}", width="stretch", type="secondary"):
                        jugadores_en_cat = obtener_jugadores(cat["id"])
                        if jugadores_en_cat:
                            st.session_state[f"confirmar_eliminar_{cat['id']}"] = True
                            st.rerun()
                        else:
                            if eliminar_categoria(cat["id"]):
                                st.session_state.msg_lista_exito = f"Categoría {cat['nombre']} eliminada con éxito."
                                obtener_categorias.clear()
                                obtener_jugadores.clear()
                                st.rerun()
                            else:
                                st.error("Fallo al eliminar (revisa permisos o recarga la página).", icon=":material/error:")
                else:
                    jugadores_en_cat = obtener_jugadores(cat["id"])
                    st.warning(f"Hay {len(jugadores_en_cat)} jugador(es) vinculados a esta categoría. ¿Estás seguro de eliminarla? Se desvincularán todos los jugadores de ella.", icon=":material/warning:")
                    
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        if st.button("Sí, eliminar", key=f"confirm_eliminar_{cat['id']}", width="stretch", type="primary"):
                            desvincular_jugadores_categoria(cat["id"])
                            if eliminar_categoria(cat["id"]):
                                st.session_state.msg_lista_exito = f"Categoría {cat['nombre']} eliminada y {len(jugadores_en_cat)} jugador(es) desvinculados."
                            else:
                                st.error("Fallo al eliminar la categoría.", icon=":material/error:")
                            
                            st.session_state[f"confirmar_eliminar_{cat['id']}"] = False
                            obtener_categorias.clear()
                            obtener_jugadores.clear()
                            st.rerun()
                    with cc2:
                        if st.button("Cancelar", key=f"cancel_eliminar_{cat['id']}", width="stretch"):
                            st.session_state[f"confirmar_eliminar_{cat['id']}"] = False
                            st.rerun()

if __name__ == '__main__':
    import streamlit as st
    if 'authenticated' not in st.session_state or not st.session_state.authenticated:
        st.switch_page('app.py')
    else:
        render_categorias()
