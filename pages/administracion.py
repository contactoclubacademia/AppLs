"""
=============================================================================
 MODULO: ADMINISTRACION
=============================================================================
Dashboard de resumen y gestión de usuarios (profesores) y sus permisos.
Solo accesible por Administradores.
=============================================================================
"""


import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime

from estilos import inject_css
from database import (obtener_jugadores, obtener_categorias, obtener_pagos,
                      obtener_usuarios, crear_usuario, actualizar_usuario, eliminar_usuario)

def render_administracion() -> None:
    inject_css()
    
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
        
        # Cooldown para el ETL
        from datetime import timedelta
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info("El Dashboard se actualiza automáticamente cada 24 hrs. Si los datos no coinciden, puedes forzar la actualización aquí.", icon=":material/info:")
        with col2:
            ahora = datetime.now()
            if "ultimo_etl" not in st.session_state:
                st.session_state.ultimo_etl = None
                
            en_cooldown = st.session_state.ultimo_etl and (ahora - st.session_state.ultimo_etl) < timedelta(minutes=5)
            
            if en_cooldown:
                restante = 5 - int((ahora - st.session_state.ultimo_etl).total_seconds() / 60)
                st.button(f"Sincronizando (Espera {restante}m)", disabled=True, use_container_width=True)
            else:
                if st.button("Forzar Actualización (ETL)", type="primary", use_container_width=True):
                    import subprocess
                    import sys
                    with st.spinner("Sincronizando Base de Datos..."):
                        try:
                            subprocess.check_call([sys.executable, "etl.py"])
                            st.session_state.ultimo_etl = datetime.now()
                            st.success("¡Sincronización exitosa!")
                            st.rerun()
                        except subprocess.CalledProcessError as e:
                            st.error(f"Error en el proceso ETL. Detalle: {e}")
                        except Exception as e:
                            st.error(f"Error al ejecutar ETL: {e}")

        st.markdown("---")
        looker_url = "https://datastudio.google.com/embed/reporting/59c571af-52d8-4d7d-a9ac-6ae517461b12/page/qXG8F"
        components.iframe(looker_url, width=1000, height=800, scrolling=True)

    with tab2:
        st.subheader("Gestión de Cuentas")
        usuarios = obtener_usuarios()
        
        c_form, c_lista = st.columns([1, 1.5])
        with c_form:
            with st.form("form_crear_usuario", clear_on_submit=True):
                st.markdown("#### Nuevo Profesor")
                n_user = st.text_input("Usuario (Login) *")
                n_pass = st.text_input("Contraseña *", type="password")
                n_pass2 = st.text_input("Confirmar Contraseña *", type="password")
                n_nombre = st.text_input("Nombre Completo *")
                n_telefono = st.text_input("Teléfono de Contacto *", placeholder="+56 9 1234 5678")
                
                # Por defecto un profesor solo verá Asistencia
                permisos_defecto = ["Control de Asistencia"]
                
                submitted = st.form_submit_button("Crear Cuenta", type="primary", use_container_width=True)
                if submitted:
                    if not n_user.strip() or not n_pass.strip() or not n_nombre.strip() or not n_pass2.strip() or not n_telefono.strip():
                        st.error("Completa los campos obligatorios (*).", icon=":material/error:")
                    elif n_pass != n_pass2:
                        st.error("Las contraseñas no coinciden.", icon=":material/error:")
                    elif any(u["username"] == n_user.strip() for u in usuarios):
                        st.error("El nombre de usuario ya existe.", icon=":material/error:")
                    else:
                        nuevo = {
                            "username": n_user.strip(),
                            "password": n_pass.strip(),
                            "nombre": n_nombre.strip(),
                            "telefono": n_telefono.strip(),
                            "rol": "Profesor",
                            "permisos": permisos_defecto
                        }
                        if crear_usuario(nuevo):
                            st.session_state.msg_admin = f"Cuenta '{n_user}' creada con éxito."
                            st.cache_data.clear()
                            st.rerun()

        with c_lista:
            with st.container(border=True):
                st.markdown("#### Cuentas Existentes")
                if usuarios:
                    # Ocultar contraseñas para la vista
                    df_usr = pd.DataFrame(usuarios)
                    df_usr["password"] = "*****"
                    df_usr["permisos"] = df_usr["permisos"].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x))
                    
                    if "telefono" not in df_usr.columns:
                        df_usr["telefono"] = ""
                    df_usr["telefono"] = df_usr["telefono"].fillna("")
                    
                    columnas = ["username", "nombre", "telefono", "rol", "permisos"]
                    st.dataframe(df_usr[[c for c in columnas if c in df_usr.columns]], hide_index=True, use_container_width=True)
                
                st.markdown("---")
                st.markdown("#### Eliminar Cuenta")
                lista_nombres = [u["username"] for u in usuarios if u["username"] != st.session_state.user.get("username")]
                
                def formato_usuario_eliminar(usr_id):
                    if usr_id == "-- Seleccionar --": return usr_id
                    return next((u["nombre"] for u in usuarios if u["username"] == usr_id), usr_id)

                usr_eliminar = st.selectbox("Seleccionar cuenta a eliminar", ["-- Seleccionar --"] + lista_nombres, format_func=formato_usuario_eliminar)
                if st.button("Eliminar Cuenta Seleccionada", type="secondary") and usr_eliminar != "-- Seleccionar --":
                    if eliminar_usuario(usr_eliminar):
                        st.session_state.msg_admin = f"Usuario '{usr_eliminar}' eliminado."
                        st.cache_data.clear()
                        st.rerun()

    with tab3:
        st.subheader("Control de Accesos a Módulos")
        st.write("Selecciona a un Profesor para habilitar o deshabilitar sus módulos.")
        
        profesores = [u for u in usuarios if u["rol"] != "Administrador"]
        
        if not profesores:
            st.info("No hay cuentas de profesores creadas. Crea una en la pestaña anterior.")
        else:
            def formato_profesor(usr_id):
                return next((u["nombre"] for u in profesores if u["username"] == usr_id), usr_id)
            
            usr_sel = st.selectbox("Profesor", [u["username"] for u in profesores], format_func=formato_profesor)
            if usr_sel:
                datos_usr = next(u for u in profesores if u["username"] == usr_sel)
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
                            st.session_state.msg_admin = f"Permisos actualizados para '{usr_sel}'."
                            st.cache_data.clear()
                            st.rerun()


if __name__ == '__main__':
    import streamlit as st
    if 'authenticated' not in st.session_state or not st.session_state.authenticated:
        st.switch_page('app.py')
    else:
        render_administracion()
