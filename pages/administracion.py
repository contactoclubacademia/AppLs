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

from backend.database import (obtener_jugadores, obtener_categorias, obtener_pagos,
                      obtener_usuarios, crear_usuario, actualizar_usuario, eliminar_usuario,
                      obtener_apoderados_con_estado, generar_token_registro, construir_link_wsp,
                      purgar_comprobantes_antiguos, destruir_datos_apoderado, destruir_datos_jugador)


def render_administracion() -> None:
    
    # Seguridad básica
    if st.session_state.user.get("rol") != "Administrador":
        st.error("No tienes permisos para acceder a este módulo.")
        return

    st.title(":material/shield_person: Administración y Panel de Control")
    
    if "msg_admin" in st.session_state:
        st.success(st.session_state.msg_admin)
        del st.session_state.msg_admin

    tab1, tab2, tab3, tab_apoderados, tab_legal = st.tabs(["Dashboard", "Profesores y Cuentas", "Control de Accesos", "Portal Apoderado", "Cumplimiento Legal"])

    with tab1:
        st.subheader("Data Warehouse & BI")
        
        st.success("El Dashboard se conecta directamente al Modelo Copo de Nieve (Snowflake) en tiempo real. No se requiere sincronización manual.", icon=":material/check_circle:")

        st.markdown("---")
        looker_url = st.secrets.get("LOOKER_URL", "https://datastudio.google.com/embed/reporting/59c571af-52d8-4d7d-a9ac-6ae517461b12/page/qXG8F")
        st.iframe(looker_url, width=1000, height=800)

    with tab2:
        st.subheader("Gestión de Cuentas")
        usuarios = [u for u in obtener_usuarios() if u.get("rol") != "Apoderado"]
        
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
                    return next((u.get("nombre", "Sin Nombre") for u in usuarios if u.get("id") == usr_id), usr_id)

                usr_eliminar = st.selectbox("Seleccionar cuenta a eliminar", ["-- Seleccionar --"] + lista_nombres, format_func=formato_usuario_eliminar)
                if st.button("Eliminar Cuenta Seleccionada", type="secondary") and usr_eliminar != "-- Seleccionar --":
                    if eliminar_usuario(usr_eliminar):
                        st.session_state.msg_admin = "Usuario eliminado."
                        obtener_usuarios.clear()
                        st.rerun()

    with tab3:
        st.subheader("Control de Accesos a Módulos")
        st.write("Selecciona a un Profesor para habilitar o deshabilitar sus módulos.")
        
        profesores = [u for u in usuarios if u.get("rol") == "Profesor"]
        
        if not profesores:
            st.info("No hay cuentas de profesores creadas. Crea una en la pestaña anterior.")
        else:
            def formato_profesor(usr_id):
                return next((u.get("nombre", "Sin Nombre") for u in profesores if u.get("id") == usr_id), usr_id)
            
            usr_sel = st.selectbox("Profesor", [u.get("id") for u in profesores if "id" in u], format_func=formato_profesor)
            if usr_sel:
                datos_usr = next(u for u in profesores if u.get("id") == usr_sel)
                permisos_actuales = datos_usr.get("permisos") or []
                
                st.markdown(f"**Modificando a:** {datos_usr.get('nombre', 'Sin Nombre')}")
                
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

    with tab_apoderados:
        st.subheader("Invitaciones a Apoderados")
        st.write("Genera enlaces de acceso únicos y envíalos por WhatsApp.")
        
        apoderados = obtener_apoderados_con_estado()
        
        if not apoderados:
            st.info("No hay apoderados registrados. Asegúrate de registrar jugadores primero.")
        else:
            # Diccionarios de formato
            iconos = {"activa": "[Activa]", "pendiente": "[Pendiente]", "expirada": "[Expirada]", "sin_cuenta": "[Sin Cuenta]"}
            textos = {"activa": "", "pendiente": "", "expirada": "", "sin_cuenta": ""}
            
            c_inv, c_lista_apo = st.columns([1, 1.5])
            
            with c_inv:
                with st.form("form_invitar_apoderado"):
                    st.markdown("#### Enviar Invitación")
                    
                    def format_apo(a_id):
                        a = next((x for x in apoderados if x["id"] == a_id), None)
                        if not a: return a_id
                        return f"{iconos.get(a.get('estado_cuenta', 'sin_cuenta'), '')} {a.get('nombre', 'Sin Nombre')} ({a.get('rut', 'Sin RUT')})"
                        
                    apo_sel_id = st.selectbox("Seleccionar Apoderado *", [a["id"] for a in apoderados], format_func=format_apo)
                    
                    st.info("Al enviar la invitación, se generará un enlace único válido por 7 días y se abrirá WhatsApp con un mensaje pre-escrito.")
                    
                    with st.expander(":material/edit: Personalizar mensaje de WhatsApp", expanded=False):
                        st.caption("Variables disponibles: {nombre_apoderado}, {nombre_jugador}, {link_registro}")
                        
                        import os, json
                        MSG_CONFIG_FILE = "config/config_wsp.json"
                        
                        def get_msg_default():
                            if os.path.exists(MSG_CONFIG_FILE):
                                try:
                                    with open(MSG_CONFIG_FILE, "r", encoding="utf-8") as f:
                                        return json.load(f).get("mensaje", "")
                                except:
                                    pass
                            return (
                                "Hola {nombre_apoderado}, te invitamos al *Portal Academia La Serena*.\n\n"
                                "Desde aquí podrás ver los pagos y asistencia de *{nombre_jugador}*.\n\n"
                                " Accede aquí:\n{link_registro}\n\n"
                                "¡Te esperamos!"
                            )
                            
                        _msg_invitacion_default = get_msg_default()
                        
                        plantilla_invitacion = st.text_area(
                            "Mensaje", 
                            value=_msg_invitacion_default, 
                            height=180,
                            label_visibility="collapsed"
                        )
                        
                        btn_guardar_plantilla = st.form_submit_button("Guardar como plantilla predeterminada")
                        if btn_guardar_plantilla:
                            try:
                                with open(MSG_CONFIG_FILE, "w", encoding="utf-8") as f:
                                    json.dump({"mensaje": plantilla_invitacion}, f, ensure_ascii=False)
                                st.success("Plantilla guardada correctamente. Se usará por defecto.")
                            except Exception as e:
                                logger = __import__("logging").getLogger(__name__); logger.error(f"Error al guardar plantilla: {e}"); st.error("No se pudo guardar la plantilla. Verifica los permisos del archivo local.")
                    
                    enviado_wsp = st.form_submit_button(":material/send_to_mobile: Enviar por WhatsApp", type="primary", use_container_width=True)
                    
                    if enviado_wsp and apo_sel_id:
                        apo_data = next((x for x in apoderados if x["id"] == apo_sel_id), None)
                        if apo_data:
                            if apo_data.get("estado_cuenta") == "activa":
                                st.warning(f"{apo_data.get('nombre', 'Sin Nombre')} ya tiene una cuenta activa.")
                            else:
                                if not apo_data.get("telefono"):
                                    st.error("El apoderado no tiene un teléfono registrado. Actualiza sus datos primero.")
                                else:
                                    with st.spinner("Generando enlace..."):
                                        token = generar_token_registro(apo_sel_id)
                                        if token:
                                            # TODO: URL dinámica en prod
                                            # st_app_url = st.secrets.get("APP_URL", "http://localhost:8501")
                                            # Intentar obtener la URL de producción de los secretos. 
                                            # Si no existe, usa localhost por defecto.
                                            app_url = st.secrets.get("APP_URL", "http://localhost:8501")
                                            
                                            url_wsp = construir_link_wsp(
                                                telefono=apo_data.get("telefono", ""),
                                                token=token,
                                                nombre_apoderado=apo_data.get("nombre", "Sin Nombre"),
                                                nombre_jugador="tu hijo/a", # Simplified for now, or we fetch it
                                                app_url=app_url,
                                                plantilla_msj=plantilla_invitacion
                                            )
                                            
                                            st.session_state.msg_admin = f"Invitación generada para {apo_data.get('nombre', 'Sin Nombre')}."
                                            
                                            # Mostrar el link como HTML para que al hacer clic se abra
                                            st.markdown(
                                                f'<a href="{url_wsp}" target="_blank" style="display: block; text-align: center; background-color: #25D366; color: white; padding: 10px; border-radius: 5px; text-decoration: none; font-weight: bold; margin-top: 10px;">Haz clic aquí para abrir WhatsApp</a>',
                                                unsafe_allow_html=True
                                            )
                                            
                                            obtener_apoderados_con_estado.clear()
                                            
                                        else:
                                            st.error("Error al generar el token de invitación.")
                                            
                with st.form("form_reset_clave_apo"):
                    st.markdown("#### :material/lock_reset: Restablecer Clave")
                    st.info("Si un apoderado olvidó su clave, puedes forzar una nueva clave aquí.")
                    apo_reset_id = st.selectbox("Apoderado", [a["id"] for a in apoderados], format_func=format_apo, key="reset_apo_sel")
                    nueva_clave = st.text_input("Nueva Contraseña", type="password")
                    btn_reset = st.form_submit_button("Restablecer", type="primary", use_container_width=True)
                    
                    if btn_reset and apo_reset_id and nueva_clave:
                        apo_data = next((x for x in apoderados if x["id"] == apo_reset_id), None)
                        if apo_data and apo_data.get("estado_cuenta") != "activa":
                            st.error("El apoderado no tiene una cuenta activa.")
                        elif len(nueva_clave) < 6:
                            st.warning("La contraseña debe tener al menos 6 caracteres.")
                        else:
                            from backend.database import restablecer_contrasena_admin
                            with st.spinner("Restableciendo..."):
                                if restablecer_contrasena_admin(apo_reset_id, nueva_clave):
                                    st.success(f"¡Clave restablecida con éxito para {apo_data['nombre']}!")
                                else:
                                    st.error("Hubo un problema al restablecer la clave.")
            
            with c_lista_apo:
                with st.container(border=True):
                    st.markdown("#### Estado de Cuentas")
                    
                    filtro_estado = st.selectbox(
                        "Filtrar por estado", 
                        ["Todas", "Activa", "Pendiente", "Expirada", "Sin Cuenta"],
                        index=1, # Por defecto muestra Activa
                        key="filtro_estado_apo"
                    )
                    
                    df_apo = pd.DataFrame(apoderados)
                    if not df_apo.empty:
                        if "estado_cuenta" not in df_apo.columns:
                            df_apo["estado_cuenta"] = "sin_cuenta"
                        df_apo["estado_cuenta"] = df_apo["estado_cuenta"].fillna("sin_cuenta")
                        if filtro_estado != "Todas":
                            estado_map = {"Activa": "activa", "Pendiente": "pendiente", "Expirada": "expirada", "Sin Cuenta": "sin_cuenta"}
                            df_apo = df_apo[df_apo["estado_cuenta"] == estado_map[filtro_estado]]
                        
                        if df_apo.empty:
                            st.info(f"No hay apoderados en estado: {filtro_estado}")
                        else:
                            df_apo["Estado"] = df_apo["estado_cuenta"].map(lambda x: f"{iconos.get(x, '')} {textos.get(x, x)}")
                            for col in ["nombre", "telefono", "rut"]:
                                if col not in df_apo.columns:
                                    df_apo[col] = ""
                            df_apo = df_apo.rename(columns={"nombre": "Nombre", "telefono": "Teléfono", "rut": "RUT"})
                            st.dataframe(df_apo[["Nombre", "RUT", "Teléfono", "Estado"]], hide_index=True, use_container_width=True)
                    else:
                        st.info("No hay apoderados registrados.")

        with tab_legal:
            st.subheader(":material/gavel: Cumplimiento Legal (Ley 19.628)")
            st.info("Para cumplir con el principio de Minimización de Datos, no debes almacenar las imágenes de comprobantes bancarios indefinidamente. Utiliza esta herramienta para borrar los archivos físicos de los comprobantes que ya fueron procesados (aprobados o rechazados). Se mantendrá el registro en la base de datos de que el pago existió, pero la imagen será destruida de forma irreversible.")
            
            with st.container(border=True):
                meses = st.number_input("Purgar imágenes con una antigüedad mayor a (meses):", min_value=1, max_value=24, value=3)
                
                if st.button("Ejecutar Purga de Comprobantes", type="primary"):
                    with st.spinner("Purgando comprobantes y eliminando archivos físicos del servidor..."):
                        eliminados = purgar_comprobantes_antiguos(meses=meses)
                        st.success(f"Se han destruido permanentemente {eliminados} archivos de comprobantes de la nube.", icon=":material/delete_forever:")

            st.markdown("---")
            st.subheader("Derecho al Olvido (Borrado Permanente)")
            st.warning("Esta acción aplica una **Anonimización Destructiva** al **Apoderado y a todos sus jugadores**. Se reemplazarán sus datos personales por valores genéricos y se eliminarán sus accesos permanentemente. Esta acción no se puede deshacer, pero preservará la contabilidad y estadísticas del club.")
            
            with st.container(border=True):
                apoderados_lista = [a for a in obtener_apoderados_con_estado() if "BORRADO" not in a.get("rut", "")]
                if not apoderados_lista:
                    st.info("No hay apoderados para borrar.")
                else:
                    apoderado_id = st.selectbox("Seleccionar Apoderado a destruir (incluye a sus hijos)", [a["id"] for a in apoderados_lista], format_func=lambda x: next((f"{a['nombre']} ({a.get('rut', '')})" for a in apoderados_lista if a["id"] == x), x), key="del_apo")
                    
                    confirm1 = st.checkbox("Entiendo que esta acción destruirá los datos personales y el acceso de esta familia de forma irreversible.", key="chk_apo")
                    if st.button("Ejecutar Destrucción Total de Familia", type="primary", disabled=not confirm1):
                        with st.spinner("Anonimizando familia y destruyendo accesos..."):
                            if destruir_datos_apoderado(apoderado_id):
                                st.success("Los datos de la familia han sido destruidos exitosamente.")
                                obtener_apoderados_con_estado.clear()
                                obtener_jugadores.clear()
                                st.rerun()
                            else:
                                st.error("Ocurrió un error al intentar destruir los datos.")

if __name__ == '__main__':
    import streamlit as st
    if 'authenticated' not in st.session_state or not st.session_state.authenticated:
        st.switch_page('app.py')
    else:
        render_administracion()
