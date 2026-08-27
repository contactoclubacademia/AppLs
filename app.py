"""
=============================================================================
 SISTEMA DE GESTION — ACADEMIA LA SERENA
=============================================================================
Aplicacion multipage (Streamlit Multipage App) con arquitectura modular.
Interfaz corporativa en rojo y negro, con autenticacion por rol,
registro de jugadores, plantillas y control de asistencia.

INSTALACION DE DEPENDENCIAS
-----------------------------------------------------------------------------
    pip install streamlit streamlit-option-menu pandas

EJECUCION
-----------------------------------------------------------------------------
    streamlit run app.py

CREDENCIALES DE DEMOSTRACION
-----------------------------------------------------------------------------
    Administrador   ->  usuario: admin   | contraseña: admin123
    Profesor/Entren.->  usuario: profe   | contraseña: profe123

ARQUITECTURA MODULAR
-----------------------------------------------------------------------------
    app.py                 -> Punto de entrada, config, sidebar, routing
    pages/login.py         -> Pantalla de autenticacion
    pages/registro.py      -> Registrar Jugador
    pages/plantillas.py    -> Plantillas y Registros
    pages/asistencia.py    -> Control de Asistencia
    pages/categorias.py    -> Categorias
    pages/pagos.py         -> Registro de Pagos
    database.py            -> Capa de datos (Supabase)
    estilos.py             -> Estilos CSS corporativos
=============================================================================
"""

import streamlit as st
from streamlit_option_menu import option_menu

from database import autenticar_usuario
from estilos import inject_css

# =============================================================================
# CONFIGURACION GENERAL DE LA APP
# =============================================================================
NOMBRE_ACADEMIA = "Academia La Serena"


def render_sidebar() -> str:
    """Renderiza el menu lateral segun el rol del usuario. Retorna la opcion elegida."""
    rol = st.session_state.user["rol"]

    with st.sidebar:
        st.markdown(
            f"""
            <div class="sidebar-header">
                <div class="sidebar-brand">Academia La Serena</div>
                <div class="sidebar-user">{st.session_state.user['nombre']}</div>
                <div class="sidebar-role">{rol}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if rol == "Administrador":
            opciones = ["Registrar Jugador", "Plantillas", "Control de Asistencia", "Categorias", "Pagos"]
            iconos = ["person-plus-fill", "table", "calendar-check", "diagram-3", "cash-coin"]
        else:
            opciones = ["Control de Asistencia"]
            iconos = ["calendar-check"]

        seleccion = option_menu(
            menu_title=None,
            options=opciones,
            icons=iconos,
            default_index=0,
            styles={
                "container": {"padding": "0", "background-color": "#111111"},
                "icon": {"color": "#CCCCCC", "font-size": "18px"},
                "nav-link": {
                    "font-size": "15px",
                    "text-align": "left",
                    "margin": "4px 0",
                    "padding": "12px 14px",
                    "border-radius": "8px",
                    "color": "#CCCCCC",
                    "font-weight": "500",
                    "opacity": "1",
                    "--hover-color": "#222222",
                },
                "nav-link-selected": {
                    "background-color": "#D32F2F",
                    "color": "#FFFFFF",
                    "font-weight": "700",
                },
            },
        )

        st.markdown('<div class="sidebar-spacer"></div>', unsafe_allow_html=True)
        if st.button("Cerrar Sesion", width="stretch", key="logout_btn"):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()

        st.markdown(
            '<p class="sidebar-footer-note">Fuente de datos: Supabase (Remota)</p>',
            unsafe_allow_html=True,
        )

    return seleccion


def main() -> None:
    # PRIMERA instruccion de Streamlit: set_page_config con sidebar EXPANDIDO
    st.set_page_config(
        page_title="Academia La Serena - Sistema de Gestion",
        page_icon=":material/stadium:",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Ocultar SIEMPRE el control de colapso (flechita) - no queremos que se pueda colapsar
    st.markdown(
        """
        <style>
            [data-testid="collapsedControl"] { display: none !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user = None

    from estilos import inject_css
    inject_css()

    if not st.session_state.authenticated:
        # Ocultar sidebar SOLO en pagina de login
        st.markdown(
            """
            <style>
                [data-testid="stSidebar"] { display: none !important; }
            </style>
            """,
            unsafe_allow_html=True,
        )
        from pages.login import render_login
        render_login()
        return

    inject_css()

    # Renderizar topbar con info de usuario
    st.markdown(
        f"""
        <div class="topbar-chip">
            <span class="topbar-dot"></span>{st.session_state.user['nombre']} · {st.session_state.user['rol']}
        </div>
        """,
        unsafe_allow_html=True,
    )

    seleccion = render_sidebar()

    # Routing a modulos
    if seleccion == "Registrar Jugador":
        from pages.registro import render_registro
        render_registro()
    elif seleccion == "Plantillas":
        from pages.plantillas import render_plantillas
        render_plantillas()
    elif seleccion == "Control de Asistencia":
        from pages.asistencia import render_asistencia
        render_asistencia()
    elif seleccion == "Categorias":
        from pages.categorias import render_categorias
        render_categorias()
    elif seleccion == "Pagos":
        from pages.pagos import render_pagos
        render_pagos()


if __name__ == "__main__":
    main()