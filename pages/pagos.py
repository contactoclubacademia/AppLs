"""
=============================================================================
 MODULO: REGISTRO DE PAGOS
=============================================================================
Modulo: registro y visualizacion de pagos de mensualidades (solo Administrador).
Diseño corporativo: contenedores con borde, botones primary, iconos Material.
=============================================================================
"""

from datetime import date, datetime

import pandas as pd
import streamlit as st

from database import (obtener_jugadores, obtener_categorias, obtener_profesor_de,
                      guardar_pago, obtener_pagos)


def render_pagos() -> None:
    """Modulo: registro y visualizacion de pagos de mensualidades (solo Administrador)."""

    from estilos import inject_css
    from database import (obtener_jugadores, obtener_categorias, obtener_profesor_de,
                          guardar_pago, obtener_pagos)

    st.title(":material/attach_money: Registro de Pagos")

    with st.container(border=True):
        st.subheader(":material/description: Registra y gestiona los pagos de mensualidades de los jugadores")

    jugadores = obtener_jugadores()
    if not jugadores:
        st.info("No hay jugadores registrados en el sistema. Registra un jugador primero.")
        return

    tab_registro, tab_historial = st.tabs(["Registrar Pago", "Historial de Pagos"])

    with tab_registro:
        with st.container(border=True):
            st.subheader(":material/add_circle: Ingresar nuevo pago")

            categorias = obtener_categorias()
            c1, c2 = st.columns(2)
            with c1:
                cat_filtro = st.selectbox("Filtrar por categoria para buscar jugador", ["Todas"] + categorias, key="pago_cat_filtro")

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
                            st.success(f"Pago de {monto:,} correspondiente a {mes_sel} para el jugador {jugador_sel['nombre']} registrado correctamente.")
                        else:
                            st.error("Ocurrio un error al registrar el pago.")
            else:
                st.info("No hay jugadores elegibles para registro de pagos en este filtro.")

    with tab_historial:
        st.subheader(":material/history: Historial completo de pagos")
        from database import obtener_pagos, obtener_categorias
        pagos_lista = obtener_pagos()
        if not pagos_lista:
            st.info("Aun no se han registrado pagos en el sistema.")
        else:
            with st.container(border=True):
                st.subheader(":material/filter_list: Filtros")
                categorias = obtener_categorias()
                filtro_hist_cat = st.selectbox("Filtrar historial por categoria", ["Todas"] + categorias, key="pago_hist_cat_filtro")

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