"""
=============================================================================
 MODULO: REGISTRO DE PAGOS
=============================================================================
Modulo: registro y visualizacion de pagos de mensualidades (solo Administrador).
Diseno corporativo: contenedores con borde, botones primary, iconos Material.
=============================================================================
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date, datetime

import pandas as pd
import streamlit as st

from estilos import inject_css
from database import (obtener_jugadores, obtener_categorias, obtener_profesor_de,
                      guardar_pago, obtener_pagos)


def render_pagos() -> None:
    """Modulo: registro y visualizacion de pagos de mensualidades (solo Administrador)."""
    inject_css()

    st.title(":material/attach_money: Registro de Pagos")

    with st.container(border=True):
        st.subheader(":material/description: Registra y gestiona los pagos de mensualidades de los jugadores")

    jugadores = obtener_jugadores()
    if not jugadores:
        st.info("No hay jugadores registrados en el sistema. Registra un jugador primero.")
        return

    if "msg_pago_exito" in st.session_state:
        st.success(st.session_state.msg_pago_exito)
        del st.session_state.msg_pago_exito

    tab_registro, tab_historial, tab_modificar = st.tabs(["Registrar Pago", "Historial de Pagos", "Modificar / Eliminar"])

    with tab_registro:
        with st.container(border=True):
            st.subheader(":material/add_circle: Ingresar nuevo pago")

            lista_categorias = obtener_categorias()
            c1, c2 = st.columns(2)
            with c1:
                cat_filtro = st.selectbox("Filtrar por categoria para buscar jugador", ["Todas"] + lista_categorias, key="pago_cat_filtro")

            jugadores_filtrados = jugadores
            if cat_filtro != "Todas":
                jugadores_filtrados = [j for j in jugadores if j["categoria"] == cat_filtro]

            if not jugadores_filtrados:
                st.warning("No hay jugadores en la categoria seleccionada.")
                opciones_jugador = []
            else:
                opciones_jugador = [f"{j['nombre']} ({j['rut']}) - {j['categoria']}" for j in jugadores_filtrados]

            if opciones_jugador:
                with c2:
                    jugador_seleccionado_str = st.selectbox("Seleccionar Jugador *", opciones_jugador, key="pago_jugador_sel")

                idx_sel = opciones_jugador.index(jugador_seleccionado_str)
                jugador_sel = jugadores_filtrados[idx_sel]

                with st.container(border=True):
                    st.subheader(":material/person: Informacion del Jugador")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write(f"**Nombre:** {jugador_sel['nombre']}")
                        st.write(f"**RUT:** {jugador_sel['rut']}")
                    with col_b:
                        st.write(f"**Categoria:** {jugador_sel['categoria']}")
                        st.write(f"**Apoderado:** {jugador_sel['apoderado_nombre']} ({jugador_sel['apoderado_telefono']})")

                with st.form("form_registrar_pago", clear_on_submit=True):
                    col_m1, col_m2 = st.columns(2)
                    with col_m1:
                        meses = [
                            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
                        ]
                        mes_actual_idx = datetime.now().month - 1
                        mes_sel = st.selectbox("Mes Correspondiente *", meses, index=mes_actual_idx)

                        monto = st.number_input(
                            "Monto pagado ($) *",
                            min_value=0, value=30000, step=5000
                        )
                    with col_m2:
                        fecha_pago = st.date_input("Fecha de pago *", value=date.today())

                    guardar_btn = st.form_submit_button("REGISTRAR PAGO", width="stretch", type="primary")

                    if guardar_btn:
                        from database import guardar_pago
                        pago_dict = {
                            "jugador_rut": jugador_sel["rut"],
                            "mes_correspondiente": mes_sel,
                            "monto": int(monto),
                            "fecha_pago": fecha_pago.strftime("%Y-%m-%d")
                        }
                        if guardar_pago(pago_dict):
                            st.session_state.msg_pago_exito = f"Pago de ${monto:,} correspondiente a {mes_sel} para el jugador {jugador_sel['nombre']} registrado correctamente."
                            st.cache_data.clear()
                            st.cache_resource.clear()
                            st.rerun()
                        else:
                            st.error("Ocurrio un error al registrar el pago.")
            else:
                st.info("No hay jugadores elegibles para registro de pagos en este filtro.")

    with tab_historial:
        st.subheader(":material/history: Historial completo de pagos")
        from database import obtener_pagos
        pagos_lista = obtener_pagos()
        if not pagos_lista:
            st.info("Aun no se han registrado pagos en el sistema.")
        else:
            with st.container(border=True):
                st.subheader(":material/filter_list: Filtros")
                lista_categorias = obtener_categorias()
                filtro_hist_cat = st.selectbox("Filtrar historial por categoria", ["Todas"] + lista_categorias, key="pago_hist_cat_filtro")

                pagos_mostrar = pagos_lista
                if filtro_hist_cat != "Todas":
                    pagos_mostrar = [p for p in pagos_lista if p.get("categoria") == filtro_hist_cat]

                if not pagos_mostrar:
                    st.warning("No hay pagos registrados para la categoria seleccionada.")
                else:
                    with st.container(border=True):
                        st.subheader(":material/list: Listado de Pagos")
                        df_pagos = pd.DataFrame(pagos_mostrar)[
                            ["jugador_nombre", "jugador_rut", "categoria", "mes_correspondiente", "monto", "fecha_pago"]
                        ]
                        df_pagos.columns = [
                            "Jugador", "RUT", "Categoria", "Mes", "Monto ($)", "Fecha Pago"
                        ]

                        df_pagos["Monto ($)"] = df_pagos["Monto ($)"].apply(lambda x: f"${x:,}")

                        st.dataframe(df_pagos, width="stretch", hide_index=True)

                        total_recaudado = sum(p["monto"] for p in pagos_mostrar)
                        st.markdown(
                            f"""
                            <div style="background-color: #FFFFFF; padding: 12px; border-radius: 8px; border: 1px solid #E2E4E8; text-align: right; font-weight: bold; font-size: 16px; margin-top: 15px; color: #1A1A1A;">
                                Total Recaudado: <span style="color: #C8102E;">${total_recaudado:,}</span>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

    with tab_modificar:
        st.subheader(":material/edit: Buscar y Modificar Pagos")
        from database import obtener_pagos, actualizar_pago, eliminar_pago
        pagos_lista_mod = obtener_pagos()
        if not pagos_lista_mod:
            st.info("Aun no hay pagos registrados para modificar.")
        else:
            opciones_pagos = {f"{p['jugador_nombre']} - {p['mes_correspondiente']} ({str(p['fecha_pago']).split('T')[0]}) - ${p['monto']:,}": p for p in pagos_lista_mod}
            pago_sel_str = st.selectbox(
                "Buscar Pago a Modificar", 
                options=list(opciones_pagos.keys()), 
                index=None, 
                placeholder="Escribe el nombre del jugador o el mes..."
            )
            
            if pago_sel_str:
                p_data = opciones_pagos[pago_sel_str]
                
                with st.container(border=True):
                    st.write(f"**Modificando pago de:** {p_data['jugador_nombre']} ({p_data['jugador_rut']})")
                    
                    with st.form(f"form_editar_pago_{p_data['id']}"):
                        col_m1, col_m2 = st.columns(2)
                        with col_m1:
                            meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
                            idx_mes = meses.index(p_data["mes_correspondiente"]) if p_data["mes_correspondiente"] in meses else 0
                            nuevo_mes = st.selectbox("Mes Correspondiente *", meses, index=idx_mes)
                            nuevo_monto = st.number_input("Monto pagado ($) *", min_value=0, value=int(p_data["monto"]), step=5000)
                        
                        with col_m2:
                            try:
                                default_date = datetime.strptime(str(p_data["fecha_pago"]).split(" ")[0].split("T")[0], "%Y-%m-%d").date()
                            except:
                                default_date = date.today()
                            nueva_fecha = st.date_input("Fecha de pago *", value=default_date)

                        st.markdown("---")
                        st.write("⚠️ **Confirmación requerida**")
                        confirmar = st.checkbox("Confirmo que deseo modificar o eliminar este registro de pago", key=f"conf_{p_data['id']}")
                        
                        c5, c6 = st.columns(2)
                        with c5:
                            btn_guardar = st.form_submit_button("Guardar Cambios", type="primary", width="stretch")
                        with c6:
                            btn_eliminar = st.form_submit_button("Eliminar Pago", type="secondary", width="stretch")
                            
                        if btn_guardar:
                            if not confirmar:
                                st.error("❌ Debes marcar la casilla de confirmación para guardar.")
                            else:
                                nuevos_datos = {
                                    "mes_correspondiente": nuevo_mes,
                                    "monto": int(nuevo_monto),
                                    "fecha_pago": nueva_fecha.strftime("%Y-%m-%d")
                                }
                                if actualizar_pago(p_data["id"], nuevos_datos):
                                    st.session_state.msg_pago_exito = f"El pago de {p_data['jugador_nombre']} fue actualizado correctamente."
                                    st.cache_data.clear()
                                    st.cache_resource.clear()
                                    st.rerun()
                                    
                        if btn_eliminar:
                            if not confirmar:
                                st.error("❌ Debes marcar la casilla de confirmación para eliminar el pago.")
                            else:
                                if eliminar_pago(p_data["id"]):
                                    st.session_state.msg_pago_exito = f"El pago de {p_data['jugador_nombre']} fue eliminado del sistema."
                                    st.cache_data.clear()
                                    st.cache_resource.clear()
                                    st.rerun()