"""
=============================================================================
 MÓDULO: REGISTRO DE APODERADO (vía token WhatsApp)
=============================================================================
Permite al apoderado crear su contraseña usando el token enviado por WA.
Esta pantalla se muestra cuando la URL contiene ?token=<uuid>.
=============================================================================
"""

import streamlit as st
from backend.database import validar_token_apoderado, crear_cuenta_apoderado


def render_registro_apoderado(token: str) -> None:
    """Pantalla de creación de cuenta para el apoderado."""

    # CSS compacto reutilizando estilo del login
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0');
    html, body, [class*="css"] { font-family: 'Poppins', sans-serif !important; }
    .stApp p, .stApp h1, .stApp h2, .stApp h3, .stApp label, .stApp input, .stApp button { font-family: 'Poppins', sans-serif !important; }
    .stApp {
        background: linear-gradient(145deg, #8B0000 0%, #C8102E 45%, #960018 100%) !important;
    }
    [data-testid="stHeader"], #MainMenu, footer,
    [data-testid="stToolbar"], [data-testid="stDecoration"] { display: none !important; }
    div.block-container {
        max-width: 480px !important;
        margin: 60px auto 80px auto !important;
        padding: 42px 44px 40px 44px !important;
        background: rgba(255,255,255,0.97) !important;
        border-radius: 22px !important;
        box-shadow: 0 30px 70px rgba(0,0,0,0.5) !important;
    }
    [data-testid="stSidebar"] { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

    # Logo + título
    st.markdown("""
    <div style="text-align:center;margin-bottom:24px;">
        <div style="width:80px;height:80px;border-radius:50%;
             background:linear-gradient(135deg,#C8102E,#8B0000);
             display:inline-flex;align-items:center;justify-content:center;
             box-shadow:0 8px 28px rgba(200,16,46,0.5);font-size:36px;color:white;">
            <span style="font-family: 'Material Symbols Outlined', sans-serif;">shield_person</span>
        </div>
        <h2 style="margin:16px 0 4px;color:#1A1A1A;font-weight:800;font-size:20px;text-transform:uppercase;">
            Academia La Serena
        </h2>
        <p style="color:#6B7280;font-size:13px;margin:0;">Crear tu cuenta de apoderado</p>
        <div style="width:50px;height:3px;background:linear-gradient(90deg,#C8102E,#FF4D6D);
             border-radius:2px;margin:16px auto;"></div>
    </div>
    """, unsafe_allow_html=True)

    # Validar token
    apoderado = validar_token_apoderado(token)

    if apoderado is None:
        st.error(
            "El link de invitación no es válido o ya expiró. "
            "Solicita al administrador que te envíe uno nuevo.",
            icon=":material/error:"
        )
        st.stop()

    nombre_apoderado = apoderado.get("nombre", "")
    st.success(f"¡Hola, **{nombre_apoderado}**! Crea tu contraseña para acceder al portal.", icon=":material/waving_hand:")

    with st.form("form_registro_apoderado", clear_on_submit=False):
        email = st.text_input(
            "Correo electrónico *",
            placeholder="tucorreo@ejemplo.com",
            help="Este será tu usuario para iniciar sesión."
        )
        pw1 = st.text_input("Contraseña *", type="password", placeholder="Mínimo 8 caracteres")
        pw2 = st.text_input("Confirmar contraseña *", type="password", placeholder="Repite la contraseña")

        st.markdown("---")
        privacidad_aceptada = st.checkbox("Declaro que soy el tutor legal del menor y **acepto la Política de Privacidad**. Autorizo el tratamiento de mis datos personales y los de mi pupilo/a para fines de gestión de la academia (Ley 19.628).")

        enviado = st.form_submit_button(
            "CREAR MI CUENTA",
            use_container_width=True,
            type="primary"
        )

        if enviado:
            if not email.strip():
                st.error("Ingresa tu correo electrónico.", icon=":material/error:")
            elif not pw1:
                st.error("Ingresa una contraseña.", icon=":material/error:")
            elif len(pw1) < 8:
                st.error("La contraseña debe tener al menos 8 caracteres.", icon=":material/error:")
            elif pw1 != pw2:
                st.error("Las contraseñas no coinciden.", icon=":material/error:")
            elif not privacidad_aceptada:
                st.error("Debes aceptar la Política de Privacidad para crear tu cuenta.", icon=":material/gavel:")
            else:
                with st.spinner("Creando tu cuenta..."):
                    ok = crear_cuenta_apoderado(
                        apoderado_id=apoderado["id"],
                        email=email.strip().lower(),
                        password=pw1,
                        nombre=nombre_apoderado
                    )
                if ok:
                    st.session_state["registro_exitoso"] = True
                    st.query_params.clear()
                    st.rerun()
                else:
                    st.error(
                        "No se pudo crear la cuenta. Es posible que el correo ya esté registrado. "
                        "Contacta al administrador.",
                        icon=":material/error:"
                    )

    st.markdown(
        '<p style="font-size:12px;color:#9CA3AF;text-align:center;margin-top:20px;">'
        "¿Problemas? Contacta al administrador de la academia.</p>",
        unsafe_allow_html=True
    )
