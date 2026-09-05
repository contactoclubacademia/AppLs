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


def _init_session_state() -> None:
    """Inicialización UNA sola vez por sesión."""
    defaults = {
        "authenticated": False,
        "user": None,
        "_css_injected": False,
        "_css_auth_hidden": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _inject_global_css() -> None:
    """CSS global UNA sola vez."""
    if not st.session_state._css_injected:
        from estilos import inject_css
        inject_css()

        # CSS para ocultar controles de Streamlit
        st.markdown("""
            <style>
                [data-testid="collapsedControl"] { display: none !important; }
            </style>
        """, unsafe_allow_html=True)
        st.session_state._css_injected = True


def _inject_conditional_css() -> None:
    """CSS condicional SOLO si cambia estado auth."""
    if not st.session_state.authenticated and not st.session_state._css_auth_hidden:
        st.markdown("""
            <style>[data-testid="stSidebar"] { display: none !important; }</style>
        """, unsafe_allow_html=True)
        st.session_state._css_auth_hidden = True
    elif st.session_state.authenticated and st.session_state._css_auth_hidden:
        st.session_state._css_auth_hidden = False


def _render_topbar() -> None:
    user = st.session_state.user
    st.markdown(f"""
        <div class="topbar-chip">
            <span class="topbar-dot"></span>{user['nombre']} · {user['rol']}
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
    }
    if seleccion in routes:
        module_path, func_name = routes[seleccion]
        module = __import__(module_path, fromlist=[func_name])
        getattr(module, func_name)()


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

        opciones_disponibles = st.session_state.user.get("permisos") or []
        
        # Diccionario maestro de iconos
        iconos_maestros = {
            "Registrar Jugador": "person-plus-fill",
            "Plantillas": "table",
            "Control de Asistencia": "calendar-check",
            "Categorias": "diagram-3",
            "Pagos": "cash-coin",
            "Administración": "shield-lock-fill"
        }
        
        if rol == "Administrador":
            # El administrador ve todo, o forzamos sus opciones
            opciones = ["Registrar Jugador", "Plantillas", "Control de Asistencia", "Categorias", "Pagos", "Administración"]
        else:
            opciones = opciones_disponibles
            if not opciones:
                opciones = ["Control de Asistencia"] # Fallback

        # Asegurarse de no mostrar opciones que no esten en el diccionario maestro o rutas (por si un nombre esta mal)
        opciones = [opt for opt in opciones if opt in iconos_maestros]
        
        if not opciones:
            st.error("Tu usuario no tiene módulos asignados.")
            return None

        iconos = [iconos_maestros.get(op, "circle") for op in opciones]

        if "current_page" not in st.session_state or st.session_state.current_page not in opciones:
            st.session_state.current_page = opciones[0]

        seleccion = option_menu(
            menu_title=None,
            options=opciones,
            icons=iconos,
            default_index=opciones.index(st.session_state.current_page),
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
            try:
                from database import get_supabase
                get_supabase().auth.sign_out()
            except Exception:
                pass
            st.rerun()

        st.markdown(
            '<p class="sidebar-footer-note">Fuente de datos: Supabase (Remota)</p>',
            unsafe_allow_html=True,
        )

    # Actualizacion segura
    if seleccion != st.session_state.current_page:
        st.session_state.current_page = seleccion
        st.rerun()

    return st.session_state.current_page


def main() -> None:
    # PRIMERA instruccion de Streamlit: set_page_config con sidebar EXPANDIDO
    st.set_page_config(
        page_title="Academia La Serena - Sistema de Gestion",
        page_icon=":material/stadium:",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Ocultar el control de colapso (flechita) SOLO en PC, en celular lo necesitamos para abrir el menú nativo
    st.markdown(
        """
        <style>
            @media (min-width: 769px) {
                [data-testid="collapsedControl"] { display: none !important; }
            }
            @media (max-width: 768px) {
                [data-testid="collapsedControl"] { 
                    display: flex !important; 
                    z-index: 999999 !important; 
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    _init_session_state()
    _inject_global_css()
    _inject_conditional_css()

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

    # Renderizar topbar con info de usuario
    _render_topbar()

    seleccion = render_sidebar()

    # Routing a modulos
    _route(seleccion)





if __name__ == "__main__":
    main()