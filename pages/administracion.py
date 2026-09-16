"""
=============================================================================
 MODULO: ADMINISTRACION
=============================================================================
Dashboard de resumen y gestión de usuarios (profesores) y sus permisos.
Solo accesible por Administradores.
=============================================================================
"""


import streamlit as st
import pandas as pd

from database import (obtener_jugadores, obtener_categorias, obtener_pagos,
                      obtener_usuarios, crear_usuario, actualizar_usuario, eliminar_usuario)

def render_administracion() -> None:
    
    # Seguridad básica
    if st.session_state.user.get("rol") != "Administrador":
        st.error("No tienes permisos para acceder a este módulo.")
        return

    st.title(":material/shield_person: Administración y Panel de Control")
    
    if "msg_admin" in st.session_state:
        st.success(st.session_state.msg_admin)
        del st.session_state.msg_admin

    tab1, tab2, tab3 = st.tabs(["Dashboard", "Profesores y Cuentas", "Control de Accesos"])

    with tab1:
        st.subheader("Data Warehouse & BI")
        
        st.success("El Dashboard se conecta directamente al Modelo Copo de Nieve (Snowflake) en tiempo real. No se requiere sincronización manual.", icon=":material/check_circle:")

        st.markdown("---")
        looker_url = st.secrets.get("LOOKER_URL", "https://datastudio.google.com/embed/reporting/59c571af-52d8-4d7d-a9ac-6ae517461b12/page/qXG8F")
        st.iframe(looker_url, width=1000, height=800)

    with tab2:
        st.subheader("Gestión de Cuentas")
        usuarios = obtener_usuarios()
        
        c_form, c_lista = st.columns([1, 1.5])
        with c_form:
            if "form_key_admin" not in st.session_state:
                st.session_state["form_key_admin"] = 0
                
            with st.form(f"form_crear_usuario_{st.session_state['form_key_admin']}", clear_on_submit=False):
                st.markdown("#### Nuevo Profesor")
                n_email = st.text_input("Correo (Login) *")
                n_pass = st.text_input("Contraseña *", type="password")
                n_pass2 = st.text_input("Confirmar Contraseña *", type="password")
                n_nombre = st.text_input("Nombre Completo *")
                n_telefono = st.text_input("Teléfono de Contacto *", placeholder="+56 9 1234 5678")
                
                # Por defecto un profesor solo verá Asistencia
                permisos_defecto = ["Control de Asistencia"]
                
                submitted = st.form_submit_button("Crear Cuenta", type="primary", width="stretch")
                if submitted:
                    if not n_email.strip() or not n_pass.strip() or not n_nombre.strip() or not n_pass2.strip() or not n_telefono.strip():
                        st.error("Completa los campos obligatorios (*).", icon=":material/error:")
                    elif n_pass != n_pass2:
                        st.error("Las contraseñas no coinciden.", icon=":material/error:")
                    else:
                        nuevo = {
                            "username": n_email.strip(),
                            "password": n_pass.strip(),
                            "nombre": n_nombre.strip(),
                            "telefono": n_telefono.strip(),
                            "rol": "Profesor",
                            "permisos": permisos_defecto
                        }
                        if crear_usuario(nuevo):
                            st.session_state.msg_admin = f"Cuenta '{n_email}' creada con éxito."
                            obtener_usuarios.clear()
                            st.session_state.form_key_admin += 1
                            st.rerun()

        with c_lista:
            with st.container(border=True):
                st.markdown("#### Cuentas Existentes")
                if usuarios:
                    # Ocultar contraseñas para la vista
                    df_usr = pd.DataFrame(usuarios)
                    if "password" in df_usr.columns:
                        df_usr["password"] = "*****"
                    if "permisos" in df_usr.columns:
                        df_usr["permisos"] = df_usr["permisos"].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x))
                    
                    if "telefono" not in df_usr.columns:
                        df_usr["telefono"] = ""
                    df_usr["telefono"] = df_usr["telefono"].fillna("")
                    
                    if "correo" not in df_usr.columns:
                        df_usr["correo"] = "Sin correo"
                    
                    columnas = ["nombre", "correo", "telefono", "rol", "permisos"]
                    # use_container_width habilita el scroll horizontal automático cuando es necesario
                    st.dataframe(df_usr[[c for c in columnas if c in df_usr.columns]], hide_index=True, use_container_width=True)
                
                st.markdown("---")
                st.markdown("#### Eliminar Cuenta")
                lista_nombres = [u["id"] for u in usuarios if u["id"] != st.session_state.user.get("id")]
                
                def formato_usuario_eliminar(usr_id):
                    if usr_id == "-- Seleccionar --": return usr_id
                    return next((u["nombre"] for u in usuarios if u["id"] == usr_id), usr_id)

                usr_eliminar = st.selectbox("Seleccionar cuenta a eliminar", ["-- Seleccionar --"] + lista_nombres, format_func=formato_usuario_eliminar)
                if st.button("Eliminar Cuenta Seleccionada", type="secondary") and usr_eliminar != "-- Seleccionar --":
                    if eliminar_usuario(usr_eliminar):
                        st.session_state.msg_admin = "Usuario eliminado."
                        obtener_usuarios.clear()
                        st.rerun()

    with tab3:
        st.subheader("Control de Accesos a Módulos")
        st.write("Selecciona a un Profesor para habilitar o deshabilitar sus módulos.")
        
        profesores = [u for u in usuarios if u["rol"] != "Administrador"]
        
        if not profesores:
            st.info("No hay cuentas de profesores creadas. Crea una en la pestaña anterior.")
        else:
            def formato_profesor(usr_id):
                return next((u["nombre"] for u in profesores if u["id"] == usr_id), usr_id)
            
            usr_sel = st.selectbox("Profesor", [u["id"] for u in profesores], format_func=formato_profesor)
            if usr_sel:
                datos_usr = next(u for u in profesores if u["id"] == usr_sel)
                permisos_actuales = datos_usr.get("permisos") or []
                
                st.markdown(f"**Modificando a:** {datos_usr['nombre']}")
                
                modulos_disponibles = ["Registrar Jugador", "Plantillas", "Control de Asistencia", "Categorias", "Pagos"]
                
                with st.form("form_permisos"):
                    nuevos_permisos = []
                    for mod in modulos_disponibles:
                        # Checkbox premarcado si ya tiene el permiso
                        tiene = st.checkbox(mod, value=(mod in permisos_actuales))
                        if tiene:
                            nuevos_permisos.append(mod)
                            
                    if st.form_submit_button("Guardar Permisos", type="primary"):
                        if actualizar_usuario(usr_sel, {"permisos": nuevos_permisos}):
                            st.session_state.msg_admin = "Permisos actualizados."
                            obtener_usuarios.clear()
                            st.rerun()


if __name__ == '__main__':
    import streamlit as st
    if 'authenticated' not in st.session_state or not st.session_state.authenticated:
        st.switch_page('app.py')
    else:
        render_administracion()
