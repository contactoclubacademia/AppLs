"""
=============================================================================
 MODULO: LOGIN / AUTENTICACION
=============================================================================
Pantalla de autenticacion centrada, en formato tarjeta.
Diseño corporativo: contenedores con borde, botones primary, iconos Material.
=============================================================================
"""

import streamlit as st

from database import autenticar_usuario
from estilos import inject_css


def render_login() -> None:
    """Pantalla de autenticacion centrada, en formato tarjeta."""
    from estilos import inject_css
    inject_css()

    st.markdown('<div class="login-wrapper">', unsafe_allow_html=True)
    col_izq, col_centro, col_der = st.columns([1, 1.2, 1])

    with col_centro:
        with st.container(border=True):
            st.markdown(
                f"""
                <div class="login-card">
                    <h2 class="login-title">Academia La Serena</h2>
                    <p class="login-subtitle">Sistema de Gestion Deportiva</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            with st.form("form_login", clear_on_submit=False):
                st.subheader(":material/login: Iniciar Sesion")
                username = st.text_input("Usuario", placeholder="Ingresa tu usuario")
                password = st.text_input("Contrasena", type="password", placeholder="Ingresa tu contrasena")
                enviado = st.form_submit_button("INGRESAR", width="stretch", type="primary")

                if enviado:
                    usuario = autenticar_usuario(username.strip(), password)
                    if usuario:
                        st.session_state.authenticated = True
                        st.session_state.user = usuario
                        st.rerun()
                    else:
                        st.error("Usuario o contrasena incorrectos.")

        st.markdown(
            '<p class="login-hint">Usuarios demo &nbsp;·&nbsp; admin / admin123 &nbsp;·&nbsp; profe / profe123</p>',
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)