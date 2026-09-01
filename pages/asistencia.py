"""
=============================================================================
 MODULO: CONTROL DE ASISTENCIA
=============================================================================
Modulo: toma de asistencia por fecha y categoria (Administrador y Profesor).
Diseno corporativo: contenedores con borde, botones primary, iconos Material.
=============================================================================
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date

import streamlit as st

from estilos import inject_css
from database import obtener_categorias, obtener_jugadores, obtener_asistencia, obtener_profesor_de, guardar_asistencia


def render_asistencia() -> None:
    """Modulo: toma de asistencia por fecha y categoria (Administrador y Profesor)."""
    inject_css()

    st.title(":material/calendar_check: Control de Asistencia")

    with st.container(border=True):
        st.subheader(":material/description: Registra la asistencia diaria por categoria")

    categorias = obtener_categorias()
    if not categorias:
        st.info("No hay categorias disponibles todavia. Pide al Administrador que cree una en Categorias.")
        return

    with st.container(border=True):
        st.subheader(":material/filter_list: Filtros")
        c1, c2 = st.columns(2)
        with c1:
            fecha_sel = st.date_input("Fecha", value=date.today())
        with c2:
            categoria_sel = st.selectbox("Categoria", categorias)

    profesor_cat = obtener_profesor_de(categoria_sel)
    st.caption(f"Profesor a cargo de {categoria_sel}: {profesor_cat or 'Sin asignar'}")

    jugadores = obtener_jugadores(categoria_sel)
    if not jugadores:
        st.warning("No hay jugadores en esta categoria.")
        return

    fecha_str = fecha_sel.strftime("%Y-%m-%d")
    registros_previos = obtener_asistencia(fecha_str, categoria_sel)
    opciones_estado = ["Presente", "Ausente", "Justificado/Lesionado"]
    registros_actuales = {}

    with st.container(border=True):
        st.subheader(":material/check_circle: Registro de Asistencia")
        st.markdown(
            '<div class="asistencia-header-row"><span>Jugador</span><span>Estado</span></div>',
            unsafe_allow_html=True,
        )

        for jugador in jugadores:
            col_nombre, col_estado = st.columns([1.3, 2])

            with col_nombre:
                st.markdown(
                    f"""<div class="jugador-row"><strong>{jugador['nombre']}</strong><br>
                    <span class="jugador-sub">RUT: {jugador['rut']}</span></div>""",
                    unsafe_allow_html=True,
                )

            with col_estado:
                estado_previo = registros_previos.get(jugador["rut"], {}).get("estado", opciones_estado[0])
                idx = opciones_estado.index(estado_previo) if estado_previo in opciones_estado else 0
                estado = st.radio(
                    f"Estado de {jugador['nombre']}",
                    opciones_estado,
                    index=idx,
                    horizontal=True,
                    key=f"radio_{jugador['rut']}_{fecha_str}_{categoria_sel}",
                    label_visibility="collapsed",
                )
                registros_actuales[jugador["rut"]] = {"jugador": jugador["nombre"], "estado": estado}

            st.markdown('<hr class="asistencia-divider">', unsafe_allow_html=True)

    if st.button("GUARDAR ASISTENCIA", width="stretch", type="primary", key="guardar_asistencia_btn"):
        if guardar_asistencia(fecha_str, categoria_sel, registros_actuales):
            st.success(f"Asistencia guardada correctamente para {categoria_sel} el {fecha_sel.strftime('%d-%m-%Y')}.")
        else:
            st.error("Ocurrio un error al guardar la asistencia.")