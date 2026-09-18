"""
=============================================================================
 SISTEMA DE GESTION — ACADEMIA LA SERENA
=============================================================================
Aplicacion multipage (Streamlit Multipage App) con arquitectura modular.
Interfaz corporativa en rojo y negro, con autenticacion por rol,
registro de jugadores, plantillas y control de asistencia.

INSTALACION DE DEPENDENCIAS
-----------------------------------------------------------------------------
    pip install -r requirements.txt

EJECUCION
-----------------------------------------------------------------------------
    streamlit run app.py

CREDENCIALES
-----------------------------------------------------------------------------
    Las credenciales se gestionan desde el modulo de Administracion.
    Consultar al administrador del sistema para obtener acceso.

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
from html import escape as html_escape

from backend.database import autenticar_usuario
from ui.estilos import inject_css

# =============================================================================
# CONFIGURACION GENERAL DE LA APP
# =============================================================================


def _init_session_state() -> None:
    """Inicialización UNA sola vez por sesión."""
    defaults = {
        "authenticated": False,
        "user": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _inject_global_css() -> None:
    """CSS global en cada rerun (Streamlit reconstruye el DOM)."""
    inject_css()



def _render_topbar() -> None:
    user = st.session_state.user
    nombre_safe = html_escape(str(user['nombre']))
    rol_safe = html_escape(str(user['rol']))
    st.markdown(f"""
        <div class="topbar-chip">
            <span class="topbar-dot"></span>{nombre_safe} · {rol_safe}
        </div>
    """, unsafe_allow_html=True)


def _route(seleccion: str) -> None:
    """Routing con imports al top (lazy load opcional)."""
    routes = {
        "Registrar Jugador": ("pages.registro", "render_registro"),
        "Plantillas": ("pages.plantillas", "render_plantillas"),
        "Control de Asistencia": ("pages.asistencia", "render_asistencia"),
        "Categorias": ("pages.categorias", "render_categorias"),
        "Pagos": ("pages.pagos", "render_pagos"),
        "Administración": ("pages.administracion", "render_administracion"),
        "Portal Apoderado": ("pages.portal_apoderado", "render_portal_apoderado"),
    }
    if seleccion in routes:
        module_path, func_name = routes[seleccion]
        module = __import__(module_path, fromlist=[func_name])
        getattr(module, func_name)()


def render_sidebar() -> str:
    """Renderiza el menu lateral segun el rol del usuario. Retorna la opcion elegida."""
    rol = st.session_state.user["rol"]

    with st.sidebar:
        nombre_sidebar = html_escape(str(st.session_state.user['nombre']))
        rol_sidebar = html_escape(str(rol))
        st.markdown(
            f"""
            <div class="sidebar-header">
                <div class="sidebar-brand">Academia La Serena</div>
                <div class="sidebar-user">{nombre_sidebar}</div>
                <div class="sidebar-role">{rol_sidebar}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        opciones_disponibles = st.session_state.user.get("permisos") or []
        
        # Módulos válidos del sistema
        modulos_validos = ["Registrar Jugador", "Plantillas", "Control de Asistencia", "Categorias", "Pagos", "Administración", "Portal Apoderado"]
        
        if rol == "Administrador":
            opciones = ["Registrar Jugador", "Plantillas", "Control de Asistencia", "Categorias", "Pagos", "Administración"]
        elif rol == "Apoderado":
            opciones = ["Portal Apoderado"]
        else:
            opciones = opciones_disponibles
            if not opciones:
                opciones = ["Control de Asistencia"] # Fallback

        # Filtrar solo opciones válidas
        opciones = [opt for opt in opciones if opt in modulos_validos]
        
        if not opciones:
            st.error("Tu usuario no tiene módulos asignados.")
            return None

        if "current_page" not in st.session_state or st.session_state.current_page not in opciones:
            st.session_state.current_page = opciones[0]

        # Iconos para cada opción (Material Icons nativos)
        iconos_nav = {
            "Registrar Jugador": ":material/person_add:",
            "Plantillas": ":material/table_chart:",
            "Control de Asistencia": ":material/calendar_month:",
            "Categorias": ":material/category:",
            "Pagos": ":material/payments:",
            "Administración": ":material/admin_panel_settings:",
            "Portal Apoderado": ":material/shield_person:"
        }

        seleccion = st.radio(
            "Navegación",
            opciones,
            index=opciones.index(st.session_state.current_page),
            format_func=lambda x: f"{iconos_nav.get(x, '')}\u00A0\u00A0{x}",
            label_visibility="collapsed",
            key="main_nav_radio",
        )

        st.session_state.current_page = seleccion

        st.markdown("<div class='sidebar-spacer'></div>", unsafe_allow_html=True)
        
        # Opciones extra
        st.markdown("<div style='margin-top: auto;'>", unsafe_allow_html=True)
        
        if st.button("Cerrar Sesión", type="secondary", width="stretch"):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.session_state.pop("access_token", None)
            st.session_state.pop("refresh_token", None)
            st.session_state.pop("supabase_client", None)
            st.session_state.pop("_supabase_session_set", None)
            try:
                from backend.database import get_supabase
                get_supabase().auth.sign_out()
            except Exception:
                pass
            st.rerun()

        st.markdown(
            '<p class="sidebar-footer-note">Fuente de datos: Supabase (Remota)</p>',
            unsafe_allow_html=True,
        )

    return st.session_state.current_page


def main() -> None:
    # PRIMERA instruccion de Streamlit: set_page_config con sidebar EXPANDIDO
    st.set_page_config(
        page_title="Academia La Serena - Sistema de Gestion",
        page_icon=":material/stadium:",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    _init_session_state()
    _inject_global_css()

    if not st.session_state.authenticated:
        # Check if there is a token for Apoderado registration
        query_params = st.query_params
        if "token" in query_params:
            st.markdown(
                """
                <style>
                    [data-testid="stSidebar"] { display: none !important; }
                </style>
                """,
                unsafe_allow_html=True,
            )
            from pages.registro_apoderado import render_registro_apoderado
            render_registro_apoderado(query_params["token"])
            return
            
        # Ocultar sidebar en la pantalla de login
        st.markdown(
            """
            <style>
                [data-testid="stSidebar"] { display: none !important; }
                div.block-container {
                    max-width: 440px !important;
                    padding-top: 0 !important;
                    padding-bottom: 0 !important;
                }
                div.block-container h1 { margin-top: 0 !important; }
            </style>
            """,
            unsafe_allow_html=True,
        )
        from pages.login import render_login
        render_login()
        return

    # Renderizar topbar con info de usuario
    _render_topbar()

    seleccion = render_sidebar()

    # Routing a modulos
    _route(seleccion)



if __name__ == "__main__":
    main()