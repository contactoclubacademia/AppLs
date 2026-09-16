"""
=============================================================================
 MODULO: REGISTRO DE JUGADOR
=============================================================================
Modulo: alta de un nuevo jugador y su apoderado (solo Administrador).
Diseno corporativo: contenedores con borde, botones primary, iconos Material.
=============================================================================
"""



from datetime import date

import streamlit as st

from database import obtener_categorias, guardar_jugador


from utils import validar_rut, verificar_permisos


def render_registro() -> None:
    """Modulo: alta de un nuevo jugador y su apoderado (solo Administrador)."""

    # Verificación de permisos
    if not verificar_permisos("Registrar Jugador"):
        return


    st.title(":material/person_add: Registrar Nuevo Jugador")

    categorias_disponibles = obtener_categorias()
    if not categorias_disponibles:
        st.warning("Todavia no hay categorias creadas. Ve al modulo Categorias y crea al menos una (por ejemplo, Sub-12) antes de registrar jugadores.")
        opciones_categoria = ["— Crea una categoria primero —"]
    else:
        opciones_categoria = categorias_disponibles

    if "form_key_registro" not in st.session_state:
        st.session_state["form_key_registro"] = 0
        
    if "msg_exito_registro" in st.session_state:
        st.success(st.session_state.msg_exito_registro)
        del st.session_state.msg_exito_registro

    # Unico formulario que envuelve todo
    with st.form(f"registro_form_{st.session_state['form_key_registro']}", clear_on_submit=False):
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
                    "Categoria *", 
                    opciones_categoria, 
                    format_func=lambda x: x["nombre"] if isinstance(x, dict) else x,
                    disabled=not categorias_disponibles,
                )

        if categorias_disponibles and isinstance(categoria_sel, dict):
            st.info(f"El jugador será asignado al profesor: {categoria_sel.get('profesor_nombre', 'Sin asignar')}")

        # Seccion 2: Datos del Apoderado
        with st.container(border=True):
            st.subheader(":material/family_restroom: Datos del Apoderado")
            c3, c4 = st.columns(2)
            with c3:
                rut_apoderado = st.text_input("RUT del Apoderado *", placeholder="12345678-9")
                nombre_apoderado = st.text_input("Nombre del Apoderado *", placeholder="Nombre y apellidos")
                correo_apoderado = st.text_input("Correo Electrónico", placeholder="Opcional")
            with c4:
                telefono_apoderado = st.text_input("Teléfono del Apoderado *", placeholder="+56 9 1234 5678")
                telefono_emergencia = st.text_input("Teléfono de Emergencia *", placeholder="+56 9 8765 4321")

        enviado = st.form_submit_button("Guardar Registro Completo", type="primary", width="stretch")

        if enviado:
            campos_obligatorios = [
                rut_jugador, nombre_jugador, rut_apoderado, nombre_apoderado,
                telefono_apoderado, telefono_emergencia,
            ]
            if not categorias_disponibles:
                st.error("No puedes registrar jugadores sin categorias. Crealas en Categorias primero.", icon=":material/error:")
            elif not all(str(c).strip() for c in campos_obligatorios):
                st.error("Por favor completa todos los campos obligatorios (*).", icon=":material/error:")
            elif not validar_rut(rut_jugador):
                st.error("El RUT del jugador es inválido. Debe tener formato 8 digitos + guion + 1 digito/K (ej: 21988505-9).", icon=":material/error:")
            elif not validar_rut(rut_apoderado):
                st.error("El RUT del apoderado es inválido. Debe tener formato 8 digitos + guion + 1 digito/K (ej: 21988505-9).", icon=":material/error:")
            else:
                jugador = {
                    "rut": rut_jugador.strip(),
                    "nombre": nombre_jugador.strip(),
                    "fecha_nacimiento": f"{int(anio_nacimiento)}-01-01",
                    "categoria_id": categoria_sel["id"] if isinstance(categoria_sel, dict) else None,
                    "estado": "Activo",
                    "apoderado_rut": rut_apoderado.strip(),
                    "apoderado_nombre": nombre_apoderado.strip(),
                    "apoderado_telefono": telefono_apoderado.strip(),
                    "apoderado_correo": correo_apoderado.strip(),
                    "telefono_emergencia": telefono_emergencia.strip(),
                }
                if guardar_jugador(jugador):
                    cat_nombre = categoria_sel["nombre"] if isinstance(categoria_sel, dict) else "Sin categoría"
                    st.session_state.msg_exito_registro = f"Jugador {nombre_jugador} registrado correctamente en la categoría {cat_nombre}."
                    st.session_state.form_key_registro += 1
                    st.rerun()
                else:
                    st.error("Ocurrió un error al guardar el jugador.", icon=":material/error:")

if __name__ == '__main__':
    import streamlit as st
    if 'authenticated' not in st.session_state or not st.session_state.authenticated:
        st.switch_page('app.py')
    else:
        render_registro()
