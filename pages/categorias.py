"""
=============================================================================
 MODULO: GESTION DE CATEGORIAS
=============================================================================
Modulo: crear, eliminar y asignar profesor a las categorias (solo Administrador).
Diseño corporativo: contenedores con borde, botones primary, iconos Material.
=============================================================================
"""

import streamlit as st

from database import (obtener_categorias_config, obtener_profesores_roster,
                      crear_categoria, actualizar_profesor_categoria,
                      eliminar_categoria)


def render_categorias() -> None:
    """Modulo: crear, eliminar y asignar profesor a las categorias (solo Administrador)."""

    from estilos import inject_css
    from database import (obtener_categorias_config, obtener_profesores_roster,
                          crear_categoria, actualizar_profesor_categoria,
                          eliminar_categoria)

    st.title(":material/category: Categorias")

    with st.container(border=True):
        st.subheader(":material/description: La academia se organiza por categorias de edad (Sub-6, Sub-8... hasta Sub-12 como categoria maxima por defecto). Crea, elimina o cambia el profesor a cargo de cada una cuando quieras — nada aqui es fijo.")

    with st.container(border=True):
        st.subheader(":material/add_circle: Crear nueva categoria")
        with st.form("form_nueva_categoria", clear_on_submit=True):
            cc1, cc2 = st.columns([1.1, 1.4])
            with cc1:
                nombre_nueva = st.text_input("Nombre de la categoria *", placeholder="Ej: Sub-14")
            with cc2:
                roster = obtener_profesores_roster()
                opciones_prof = ["— Nuevo profesor —"] + roster
                prof_sel = st.selectbox("Profesor a cargo", opciones_prof, key="prof_sel_nueva")
                prof_nuevo = ""
                if prof_sel == "— Nuevo profesor —":
                    prof_nuevo = st.text_input(
                        "Nombre del nuevo profesor", placeholder="Nombre y apellidos",
                        key="prof_nuevo_nueva",
                    )

            crear = st.form_submit_button("CREAR CATEGORIA", width="stretch", type="primary")

            if crear:
                profesor_final = prof_nuevo if prof_sel == "— Nuevo profesor —" else prof_sel
                if not nombre_nueva.strip():
                    st.error("Ingresa un nombre para la categoria.")
                elif crear_categoria(nombre_nueva, profesor_final):
                    st.success(f"Categoria {nombre_nueva.strip()} creada correctamente.")
                    st.rerun()

    with st.container(border=True):
        st.subheader(":material/list: Categorias actuales")

        categorias = obtener_categorias_config()
        if not categorias:
            st.info("Aun no hay categorias creadas. Usa el formulario de arriba para crear la primera.")
            return

        for cat in categorias:
            etiqueta_prof = cat["profesor"] or "Sin profesor asignado"
            with st.expander(f"{cat['nombre']} · {etiqueta_prof}"):
                roster = obtener_profesores_roster()
                opciones_prof = ["— Nuevo profesor —"] + roster
                idx = opciones_prof.index(cat["profesor"]) if cat["profesor"] in opciones_prof else 0

                ec1, ec2 = st.columns([2, 1])
                with ec1:
                    nuevo_prof_sel = st.selectbox(
                        "Profesor a cargo", opciones_prof, index=idx,
                        key=f"prof_sel_{cat['nombre']}",
                    )
                    nuevo_prof_texto = ""
                    if nuevo_prof_sel == "— Nuevo profesor —":
                        nuevo_prof_texto = st.text_input(
                            "Nombre del nuevo profesor", placeholder="Nombre y apellidos",
                            key=f"prof_txt_{cat['nombre']}",
                        )
                with ec2:
                    st.write("")
                    if st.button("Guardar profesor", key=f"guardar_{cat['nombre']}", width="stretch", type="primary"):
                        profesor_final = (
                            nuevo_prof_texto if nuevo_prof_sel == "— Nuevo profesor —" else nuevo_prof_sel
                        )
                        from database import actualizar_profesor_categoria
                        actualizar_profesor_categoria(cat["nombre"], profesor_final)
                        st.success("Profesor actualizado")
                        st.rerun()
                    if st.button("Eliminar categoria", key=f"eliminar_{cat['nombre']}", width="stretch"):
                        from database import eliminar_categoria
                        eliminar_categoria(cat["nombre"])
                        st.success(f"Categoria {cat['nombre']} eliminada")
                        st.rerun()