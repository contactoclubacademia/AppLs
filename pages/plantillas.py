"""
=============================================================================
 MODULO: PLANTILLAS Y REGISTROS
=============================================================================
Modulo: listado general de jugadores inscritos (solo Administrador).
Diseño corporativo: contenedores con borde, botones primary, iconos Material.
=============================================================================
"""

import pandas as pd
import streamlit as st

from database import obtener_jugadores, obtener_categorias, obtener_profesor_de


def render_plantillas() -> None:
    """Modulo: listado general de jugadores inscritos (solo Administrador)."""
    from estilos import inject_css
    from database import obtener_jugadores, obtener_categorias, obtener_profesor_de

    st.title(":material/table: Plantillas y Registros")

    with st.container(border=True):
        st.subheader(":material/description: Listado general de jugadores inscritos en la academia")

    jugadores = obtener_jugadores()
    if not jugadores:
        st.info("Aun no hay jugadores registrados. Ve a Registrar Jugador para comenzar.")
        return

    categorias = obtener_categorias()

    with st.container(border=True):
        st.subheader(":material/analytics: Resumen")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Jugadores", len(jugadores))
        m2.metric("Categorias activas", len(categorias))
        m3.metric("Ultimo registro", jugadores[-1]["fecha_registro"].split(" ")[0])

        filtro_categoria = st.selectbox("Filtrar por categoria", ["Todas"] + categorias)

    if filtro_categoria != "Todas":
        jugadores = obtener_jugadores(filtro_categoria)
        profesor_cat = obtener_profesor_de(filtro_categoria)
        st.caption(f"Profesor a cargo de {filtro_categoria}: {profesor_cat or 'Sin asignar'}")

    if not jugadores:
        st.warning("No hay jugadores registrados en esta categoria todavia.")
        return

    with st.container(border=True):
        st.subheader(":material/list: Listado de Jugadores")
        df = pd.DataFrame(jugadores)[
            ["nombre", "rut", "categoria", "posicion", "apoderado_nombre",
             "apoderado_telefono", "fecha_registro"]
        ]
        df.columns = ["Nombre", "RUT", "Categoria", "Posicion", "Apoderado",
                      "Telefono Apoderado", "Fecha Registro"]

        st.dataframe(df, width="stretch", hide_index=True)