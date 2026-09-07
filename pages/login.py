"""
=============================================================================
 MODULO: LOGIN / AUTENTICACION
=============================================================================
Pantalla de autenticacion centrada, en formato tarjeta.
Diseno corporativo: contenedores con borde, botones primary, iconos Material.
=============================================================================
"""


import streamlit as st
from datetime import datetime, timedelta

from database import autenticar_usuario
from estilos import inject_css


def render_login() -> None:
    """Pantalla de autenticacion centrada, en formato tarjeta."""
    inject_css()

    # Protección contra fuerza bruta
    if "login_intentos" not in st.session_state:
        st.session_state.login_intentos = 0
    if "login_bloqueado_hasta" not in st.session_state:
        st.session_state.login_bloqueado_hasta = None

    # Espaciadores físicos infalibles para empujar el login hacia abajo
    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    
    # Hacer la columna central un poco más ancha (de 1.2 a 1.6)
    col_izq, col_centro, col_der = st.columns([1, 1.6, 1])

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

                ahora = datetime.now()
                if st.session_state.login_bloqueado_hasta and ahora < st.session_state.login_bloqueado_hasta:
                    restante = int((st.session_state.login_bloqueado_hasta - ahora).total_seconds())
                    st.error(f"Demasiados intentos fallidos. Intenta de nuevo en {restante} segundos.")
                elif enviado:
                    # Si el bloqueo ya expiró, resetear el contador
                    if st.session_state.login_bloqueado_hasta and ahora >= st.session_state.login_bloqueado_hasta:
                        st.session_state.login_intentos = 0
                        st.session_state.login_bloqueado_hasta = None
                    usuario = autenticar_usuario(username.strip(), password)
                    if usuario:
                        st.session_state.login_intentos = 0
                        st.session_state.login_bloqueado_hasta = None
                        st.session_state.authenticated = True
                        st.session_state.user = usuario
                        st.rerun()
                    else:
                        st.session_state.login_intentos += 1
                        intentos_restantes = 5 - st.session_state.login_intentos
                        if intentos_restantes <= 0:
                            st.session_state.login_bloqueado_hasta = ahora + timedelta(minutes=5)
                            st.error("Demasiados intentos. Cuenta bloqueada por 5 minutos.")
                        else:
                            st.error(f"Usuario o contrasena incorrectos. ({intentos_restantes} intentos restantes)")

if __name__ == '__main__':
    import streamlit as st
    st.switch_page('app.py')
