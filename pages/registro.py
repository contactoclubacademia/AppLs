"""
=============================================================================
 MODULO: REGISTRO DE JUGADOR
=============================================================================
Modulo: alta de un nuevo jugador y su apoderado (solo Administrador).
Diseno corporativo: contenedores con borde, botones primary, iconos Material.
=============================================================================
"""


import re
from datetime import date, datetime

import streamlit as st

from estilos import inject_css
from database import obtener_categorias, obtener_profesor_de, guardar_jugador


def validar_formato_rut(rut: str) -> bool:
    """
    Valida que el RUT tenga el formato exacto: 8 digitos + guion + 1 digito o K/k.
    Ejemplo valido: 21988505-9
    """
    if not rut:
        return False
    patron = r'^\d{8}-[\dkK]$'
    return bool(re.match(patron, rut.strip()))


def render_registro() -> None:
    """Modulo: alta de un nuevo jugador y su apoderado (solo Administrador)."""

    inject_css()

    # Verificación de permisos
    permisos = st.session_state.user.get("permisos") or []
    rol = st.session_state.user.get("rol")
    if rol != "Administrador" and "Registrar Jugador" not in permisos:
        st.error("No tienes permisos para acceder a este módulo.", icon=":material/error:")
        return

    st.title(":material/person_add: Registrar Nuevo Jugador")

    categorias_disponibles = obtener_categorias()
    if not categorias_disponibles:
        st.warning("Todavia no hay categorias creadas. Ve al modulo Categorias y crea al menos una (por ejemplo, Sub-12) antes de registrar jugadores.")
    opciones_categoria = categorias_disponibles or ["— Crea una categoria primero —"]

    # Unico formulario que envuelve todo
    with st.form("registro_form", clear_on_submit=True):
        # Seccion 1: Datos del Jugador
        with st.container(border=True):
            st.subheader(":material/sports_soccer: Datos del Jugador")
            c1, c2 = st.columns(2)
            with c1:
                rut_jugador = st.text_input("RUT del Jugador *", placeholder="21988505-9")
                nombre_jugador = st.text_input("Nombre Completo *", placeholder="Nombre y apellidos")
            with c2:
                anio_nacimiento = st.number_input(
                    "Año de Nacimiento *",
                    min_value=2005, max_value=date.today().year, value=2014, step=1,
                )
                categoria_sel = st.selectbox(
                    "Categoria *", opciones_categoria, disabled=not categorias_disponibles,
                )

        if categorias_disponibles:
            profesor_cat = obtener_profesor_de(categoria_sel)
            st.caption(f"Profesor a cargo de {categoria_sel}: {profesor_cat or 'Sin asignar'}")

        # Seccion 2: Datos del Apoderado
        with st.container(border=True):
            st.subheader(":material/family_restroom: Datos del Apoderado")
            c3, c4 = st.columns(2)
            with c3:
                rut_apoderado = st.text_input("RUT del Apoderado *", placeholder="21988505-9")
                nombre_apoderado = st.text_input("Nombre del Apoderado *", placeholder="Nombre y apellidos")
                telefono_apoderado = st.text_input("Telefono *", placeholder="+56 9 1234 5678")
            with c4:
                correo_apoderado = st.text_input("Correo Electronico (Opcional)", placeholder="correo@ejemplo.com")
                telefono_emergencia = st.text_input("Telefono de Emergencia *", placeholder="+56 9 8765 4321")

        # Boton de envio DENTRO del formulario
        enviado = st.form_submit_button("Registrar Jugador", width="stretch", type="primary")

        if enviado:
            campos_obligatorios = [
                rut_jugador, nombre_jugador, rut_apoderado, nombre_apoderado,
                telefono_apoderado, telefono_emergencia,
            ]
            if not categorias_disponibles:
                st.error("No puedes registrar jugadores sin categorias. Crealas en Categorias primero.", icon=":material/error:")
            elif not all(str(c).strip() for c in campos_obligatorios):
                st.error("Por favor completa todos los campos obligatorios (*).", icon=":material/error:")
            elif not validar_formato_rut(rut_jugador):
                st.error("El RUT del jugador debe tener formato 8 digitos + guion + 1 digito/K (ej: 21988505-9).", icon=":material/error:")
            elif not validar_formato_rut(rut_apoderado):
                st.error("El RUT del apoderado debe tener formato 8 digitos + guion + 1 digito/K (ej: 21988505-9).", icon=":material/error:")
            else:
                jugador = {
                    "rut": rut_jugador.strip(),
                    "nombre": nombre_jugador.strip(),
                    "anio_nacimiento": int(anio_nacimiento),
                    "categoria": categoria_sel,
                    "apoderado_rut": rut_apoderado.strip(),
                    "apoderado_nombre": nombre_apoderado.strip(),
                    "apoderado_telefono": telefono_apoderado.strip(),
                    "apoderado_correo": correo_apoderado.strip(),
                    "telefono_emergencia": telefono_emergencia.strip(),
                    "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M"),
                }
                if guardar_jugador(jugador):
                    st.success(f"Jugador {nombre_jugador} registrado correctamente en la categoria {jugador['categoria']}.")
                else:
                    st.error("Ocurrio un error al guardar el jugador.")