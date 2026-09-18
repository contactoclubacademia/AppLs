"""
=============================================================================
 MODULO: LOGIN / AUTENTICACION
=============================================================================
Pantalla de login de pantalla completa.
Estrategia CSS: el bloque contenedor de Streamlit (block-container) es la
tarjeta blanca; el fondo rojo con pinceladas SVG se aplica al .stApp.
No se usa position:fixed para envolver widgets de Streamlit (incompatible).
=============================================================================
"""

import streamlit as st
from datetime import datetime, timedelta

from backend.database import autenticar_usuario


# ---------------------------------------------------------------------------
# CSS DE PANTALLA COMPLETA – estrategia: block-container = tarjeta blanca
# ---------------------------------------------------------------------------
_LOGIN_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:ital,wght@0,400;0,500;0,600;0,700;0,800;0,900;1,400&display=swap');

/* ── Tipografía global en login ── */
html, body, [class*="css"], .stApp * {
    font-family: 'Poppins', sans-serif !important;
}

/* ── Fondo rojo de pantalla completa con pinceladas SVG ── */
.stApp {
    min-height: 100vh;
    background:
        url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1200' height='900' viewBox='0 0 1200 900'%3E%3Cpath d='M-50 200 Q200 130 420 240 Q640 350 860 180 Q1080 10 1280 140' stroke='%23000000' stroke-width='90' fill='none' stroke-linecap='round' opacity='0.22'/%3E%3Cpath d='M-80 420 Q250 340 500 460 Q750 580 1000 400 Q1150 290 1280 370' stroke='%23000000' stroke-width='55' fill='none' stroke-linecap='round' opacity='0.13'/%3E%3Cpath d='M800 -60 Q780 220 840 440 Q900 660 790 860 Q700 980 760 1000' stroke='%23FFFFFF' stroke-width='65' fill='none' stroke-linecap='round' opacity='0.07'/%3E%3Cpath d='M920 -20 Q900 160 940 340 Q980 520 920 700' stroke='%23FFFFFF' stroke-width='35' fill='none' stroke-linecap='round' opacity='0.05'/%3E%3Cpath d='M-60 700 Q220 620 440 730 Q660 840 900 700 Q1080 590 1280 680' stroke='%23000000' stroke-width='75' fill='none' stroke-linecap='round' opacity='0.18'/%3E%3Cpath d='M-30 860 Q300 790 550 870 Q800 950 1100 820 Q1200 780 1280 810' stroke='%23FFFFFF' stroke-width='42' fill='none' stroke-linecap='round' opacity='0.05'/%3E%3Cpath d='M100 -40 Q130 100 80 260 Q30 420 120 560' stroke='%23000000' stroke-width='50' fill='none' stroke-linecap='round' opacity='0.1'/%3E%3C/svg%3E")
        center center / cover no-repeat,
        radial-gradient(ellipse at 15% 45%, #7A0015 0%, transparent 55%),
        radial-gradient(ellipse at 85% 15%, #D41030 0%, transparent 50%),
        linear-gradient(145deg, #8B0000 0%, #C8102E 45%, #960018 100%) !important;
    background-attachment: fixed !important;
}

/* ── Ocultar chrome de Streamlit ── */
[data-testid="stHeader"]       { display: none !important; }
#MainMenu                       { visibility: hidden !important; }
footer                          { visibility: hidden !important; }
[data-testid="stToolbar"]       { visibility: hidden !important; height: 0 !important; }
[data-testid="stDecoration"]    { display: none !important; }

/* ── El block-container SE CONVIERTE en la tarjeta blanca ── */
div.block-container {
    max-width: 440px !important;
    width: 440px !important;
    margin-top: 60px !important;
    margin-bottom: 80px !important;
    margin-left: auto !important;
    margin-right: auto !important;
    padding: 42px 44px 40px 44px !important;
    background: rgba(255, 255, 255, 0.97) !important;
    border-radius: 22px !important;
    box-shadow:
        0 30px 70px rgba(0, 0, 0, 0.5),
        0 0 0 1px rgba(255,255,255,0.12) !important;
    backdrop-filter: blur(10px) !important;
    animation: cardIn 0.55s cubic-bezier(0.16, 1, 0.3, 1) both !important;
    position: relative;
    z-index: 10;
}

@keyframes cardIn {
    from { opacity: 0; transform: translateY(28px) scale(0.96); }
    to   { opacity: 1; transform: translateY(0) scale(1); }
}

/* ── Logo: círculo rojo centrado ── */
.login-logo-wrap {
    display: flex;
    justify-content: center;
    margin-bottom: 18px;
}
.login-logo-ring {
    width: 86px;
    height: 86px;
    border-radius: 50%;
    background: linear-gradient(135deg, #C8102E 0%, #8B0000 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 8px 28px rgba(200, 16, 46, 0.5);
    font-size: 40px;
    line-height: 1;
    border: 3px solid rgba(255,255,255,0.2);
}

/* ── Tipografía del encabezado ── */
.login-academy-name {
    font-size: 21px !important;
    font-weight: 900 !important;
    color: #1A1A1A !important;
    letter-spacing: 0.5px !important;
    line-height: 1.2 !important;
    margin: 0 0 8px 0 !important;
    text-align: center !important;
    text-transform: uppercase !important;
}
.login-subtitle-text {
    font-size: 13px !important;
    color: #6B7280 !important;
    font-weight: 500 !important;
    margin: 0 0 0 0 !important;
    text-align: center !important;
}
.login-divider {
    width: 50px;
    height: 3px;
    background: linear-gradient(90deg, #C8102E, #FF4D6D);
    border-radius: 2px;
    margin: 18px auto 26px auto;
}

/* ── Labels de los inputs ── */
div.block-container .stTextInput > label,
div.block-container [data-testid="stTextInput"] > label {
    font-size: 11px !important;
    font-weight: 700 !important;
    color: #C8102E !important;
    text-transform: uppercase !important;
    letter-spacing: 0.8px !important;
    margin-bottom: 4px !important;
}

/* ── Inputs ── */
div.block-container .stTextInput > div > div > input {
    border: 2px solid #E5E7EB !important;
    border-radius: 10px !important;
    padding: 12px 16px !important;
    font-size: 14px !important;
    color: #1A1A1A !important;
    background: #F9FAFB !important;
    font-family: 'Poppins', sans-serif !important;
    transition: all 0.2s ease !important;
    height: 48px !important;
}
div.block-container .stTextInput > div > div > input:focus {
    border-color: #C8102E !important;
    box-shadow: 0 0 0 3px rgba(200, 16, 46, 0.13) !important;
    background: #FFFFFF !important;
    outline: none !important;
}
div.block-container .stTextInput > div > div > input::placeholder {
    color: #9CA3AF !important;
    font-weight: 400 !important;
}

/* ── Ocultar "Press Enter to submit form" de Streamlit ── */
[data-testid="InputInstructions"] {
    display: none !important;
}
/* Por si cambia de selector en futuras versiones de Streamlit */
.stTextInput small,
.stTextInput [class*="instructions"],
.stTextInput [class*="InputInstructions"] {
    display: none !important;
}

/* ── Ícono del ojo (campo contraseña): alineación correcta ── */
div.block-container .stTextInput > div {
    position: relative !important;
}
div.block-container .stTextInput > div > div {
    align-items: center !important;
}
/* El botón/ícono del ojo que Streamlit pone dentro del input */
div.block-container .stTextInput > div > div > button[kind="icon"],
div.block-container .stTextInput > div > div > div > button {
    position: absolute !important;
    right: 12px !important;
    top: 50% !important;
    transform: translateY(-50%) !important;
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    color: #6B7280 !important;
    cursor: pointer !important;
    z-index: 2 !important;
}


/* ── Botón Terciario (Enlace de texto) ── */
div.block-container button[kind="tertiary"] {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    height: auto !important;
    color: #6B7280 !important;
    box-shadow: none !important;
    min-height: 0 !important;
    text-transform: none !important;
    letter-spacing: normal !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    text-decoration: none !important;
    justify-content: center !important;
    margin-top: 5px !important;
}
div.block-container button[kind="tertiary"]:hover {
    color: #C8102E !important;
    background: transparent !important;
    text-decoration: underline !important;
}
div.block-container button[kind="tertiary"]:active {
    color: #8B0000 !important;
}

/* ── Botón de submit ── */
div.block-container .stFormSubmitButton > button {
    background: linear-gradient(135deg, #C8102E 0%, #8E0B20 100%) !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0 22px !important;
    height: 50px !important;
    font-size: 14px !important;
    font-weight: 700 !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    width: 100% !important;
    margin-top: 10px !important;
    box-shadow: 0 6px 22px rgba(200, 16, 46, 0.45) !important;
    transition: all 0.22s ease !important;
    font-family: 'Poppins', sans-serif !important;
}
div.block-container .stFormSubmitButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 12px 30px rgba(200, 16, 46, 0.6) !important;
}
div.block-container .stFormSubmitButton > button:active {
    transform: translateY(0) !important;
}

/* ── Alertas dentro del card: aspecto limpio y profesional ── */
div.block-container [data-testid="stAlert"] {
    border-radius: 10px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    margin-top: 10px !important;
    padding: 10px 14px !important;
    font-family: 'Poppins', sans-serif !important;
    line-height: 1.5 !important;
}
/* Error: borde sutil rojo */
div.block-container [data-testid="stAlert"][data-baseweb="notification"][kind="error"],
div.block-container [data-testid="stAlert"].st-emotion-cache-1k5yxzy {
    border-left: none !important;
}
/* Quitar el borde izquierdo grueso de todos los alerts en el card */
div.block-container [data-testid="stAlert"] > div {
    border-left: none !important;
}

/* ── Ocultar borde del stForm ── */
div.block-container [data-testid="stForm"] {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    box-shadow: none !important;
}

/* ── Textos del pie de tarjeta ── */
.login-footer-hint {
    font-size: 12px;
    color: #9CA3AF;
    text-align: center;
    margin-top: 20px;
    line-height: 1.6;
}
.login-founded {
    font-size: 11px;
    color: #B0B7C3;
    text-align: center;
    margin-top: 6px;
    font-style: italic;
}

/* ── Barra de pie de página (fuera de la tarjeta) ── */
.login-page-footer {
    position: fixed;
    bottom: 0; left: 0; right: 0;
    background: rgba(0, 0, 0, 0.55);
    color: rgba(255, 255, 255, 0.65);
    font-size: 11.5px;
    text-align: center;
    padding: 11px 20px;
    z-index: 9999;
    backdrop-filter: blur(6px);
    font-family: 'Poppins', sans-serif;
    letter-spacing: 0.2px;
}

/* ── Quitar márgenes extra de Streamlit dentro del card ── */
div.block-container .element-container {
    gap: 0 !important;
}
div.block-container [data-testid="stVerticalBlock"]:not(:has([data-testid="stExpander"])) {
    gap: 0 !important;
}
div.block-container .stTextInput {
    margin-bottom: 14px !important;
}

/* ── Estilos para el Expander de Recuperación ── */
div.block-container [data-testid="stExpander"] details summary {
    justify-content: center !important;
}
div.block-container [data-testid="stExpander"] details summary p {
    font-size: 13px !important;
    font-weight: 600 !important;
    color: #6B7280 !important;
}

/* ── Responsive móvil ── */
@media (max-width: 520px) {
    div.block-container {
        width: 92vw !important;
        max-width: 92vw !important;
        padding: 28px 24px 32px 24px !important;
        margin-top: 30px !important;
    }
    .login-academy-name { font-size: 18px !important; }
}
</style>
"""
_FOOTER_HTML = ""


# ---------------------------------------------------------------------------
# CACHE de intentos fallidos
# ---------------------------------------------------------------------------
@st.cache_resource
def obtener_registro_bloqueos():
    """Almacena los intentos fallidos a nivel de servidor (sobrevive a recargas de página)."""
    return {}


# ---------------------------------------------------------------------------
# RENDER PRINCIPAL
# ---------------------------------------------------------------------------
def render_login() -> None:
    """Pantalla de login de pantalla completa. El block-container es la tarjeta."""

    bloqueos = obtener_registro_bloqueos()

    # 1) Inyectar CSS
    st.markdown(_LOGIN_CSS, unsafe_allow_html=True)

    # 2) Logo + encabezado
    st.markdown(
        """
        <div class="login-logo-wrap">
            <div class="login-logo-ring">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
                     width="46" height="46" fill="white" aria-hidden="true">
                    <!-- Escudo deportivo -->
                    <path d="M12 1 L3 5 L3 11 C3 16.55 6.84 21.74 12 23
                             C17.16 21.74 21 16.55 21 11 L21 5 Z"/>
                </svg>
            </div>
        </div>
        <p class="login-academy-name">Academia Deportiva<br>La Serena</p>
        <p class="login-subtitle-text">Ingreso al Portal de Gesti&#243;n</p>
        <div class="login-divider"></div>
        """,
        unsafe_allow_html=True,
    )

    # Mensaje de éxito si viene de registro o recuperación
    if st.session_state.pop("registro_exitoso", False):
        st.success("¡Cuenta creada exitosamente! Ingresa con tu nueva contraseña.", icon=":material/check_circle:")
    if st.session_state.pop("recuperacion_exitosa", False):
        st.success("¡Contraseña actualizada! Ya puedes iniciar sesión con tu nueva clave.", icon=":material/check_circle:")

    # 3) Flujo de Estado: 0=Login, 1=Pedir Correo, 2=Pedir OTP
    if "recuperacion_fase" not in st.session_state:
        st.session_state.recuperacion_fase = 0

    if st.session_state.recuperacion_fase == 0:
        # --- FORMULARIO DE LOGIN NORMAL ---
        with st.form("form_login", clear_on_submit=False):
            email = st.text_input("Correo Electrónico", placeholder="tucorreo@ejemplo.com", key="login_email")
            password = st.text_input("Contraseña", type="password", placeholder="••••••••", key="login_password")
            enviado = st.form_submit_button("INICIAR SESIÓN", use_container_width=True)
            
            if enviado:
                email_limpio = email.strip().lower()
                if not email_limpio:
                    st.warning("Ingresa tu correo electrónico para continuar.")
                else:
                    if email_limpio not in bloqueos:
                        bloqueos[email_limpio] = {"intentos": 0, "bloqueado_hasta": None, "ultimo_intento": None}
                    
                    estado = bloqueos[email_limpio]
                    ahora = datetime.now()
                    
                    if estado["intentos"] > 0 and estado.get("ultimo_intento") and not estado["bloqueado_hasta"]:
                        if (ahora - estado["ultimo_intento"]).total_seconds() > 600:
                            estado["intentos"] = 0
                            estado["ultimo_intento"] = None
                            
                    if estado["bloqueado_hasta"] and ahora < estado["bloqueado_hasta"]:
                        restante = int((estado["bloqueado_hasta"] - ahora).total_seconds())
                        st.error(f"Acceso bloqueado. Intenta de nuevo en {restante // 60}m {restante % 60}s.")
                    else:
                        if estado["bloqueado_hasta"] and ahora >= estado["bloqueado_hasta"]:
                            estado["intentos"] = 0
                            estado["bloqueado_hasta"] = None
                            estado["ultimo_intento"] = None
                            
                        if not password:
                            st.warning("Ingresa tu contraseña para continuar.")
                        else:
                            from backend.database import obtener_jugadores_de_apoderado
                            usuario = autenticar_usuario(email_limpio, password)
                            if usuario:
                                # Verificar si el apoderado quedó inactivo (sin jugadores activos)
                                if usuario.get("rol") == "Apoderado":
                                    jugadores_activos = obtener_jugadores_de_apoderado(usuario["apoderado_id"])
                                    if not jugadores_activos:
                                        st.error("Tu cuenta está desactivada porque no tienes jugadores activos en la academia.")
                                        return  # Detenemos la ejecución sin iniciar sesión
                                
                                estado["intentos"] = 0
                                estado["bloqueado_hasta"] = None
                                estado["ultimo_intento"] = None
                                st.session_state.authenticated = True
                                st.session_state.user = usuario
                                st.rerun()
                            else:
                                estado["intentos"] += 1
                                estado["ultimo_intento"] = ahora
                                intentos_restantes = 5 - estado["intentos"]
                                if intentos_restantes <= 0:
                                    estado["bloqueado_hasta"] = ahora + timedelta(minutes=5)
                                    st.error("Demasiados intentos fallidos. Cuenta bloqueada por 5 minutos.")
                                else:
                                    plural = "s" if intentos_restantes != 1 else ""
                                    st.error(f"Correo o contraseña incorrectos. ({intentos_restantes} intento{plural} restante{plural}).")
        
        # Botón para ir a recuperar contraseña
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("¿Problemas para ingresar? Restablecer contraseña", type="tertiary", use_container_width=True):
            st.session_state.recuperacion_fase = 1
            st.rerun()
            
    elif st.session_state.recuperacion_fase == 1:
        # --- FASE 1: CONTACTAR ADMIN ---
        st.markdown("<h4 style='text-align:center; color:#C8102E; margin-bottom:5px;'>Recuperar Contraseña</h4>", unsafe_allow_html=True)
        st.markdown(
            "<p style='font-size:13px; color:#4B5563; text-align:center;'>"
            "Por motivos de seguridad, para restablecer tu contraseña debes "
            "comunicarte directamente con la administración de la academia. Ellos te asignarán una nueva clave provisional de inmediato.</p>", 
            unsafe_allow_html=True
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Volver al inicio", type="primary", use_container_width=True):
            st.session_state.recuperacion_fase = 0
            st.rerun()

    # 4) Pie de tarjeta original
    st.markdown(
        """
        <p class="login-founded" style="margin-top: 30px;">Fundada el 21 de Agosto de 1987 · Chile</p>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    import streamlit as st
    st.switch_page("app.py")
