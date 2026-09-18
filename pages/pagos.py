"""
=============================================================================
 MODULO: REGISTRO DE PAGOS
=============================================================================
Modulo: registro y visualizacion de pagos de mensualidades (solo Administrador).
Diseno corporativo: contenedores con borde, botones primary, iconos Material.
=============================================================================
"""

import io
import re
import urllib.parse
from datetime import date, datetime

import pandas as pd
import streamlit as st

from backend.utils import format_cat, MESES, verificar_permisos
from backend.database import (obtener_jugadores, obtener_categorias,
                      guardar_pago, obtener_pagos, actualizar_pago, eliminar_pago,
                      obtener_estado_pagos_mes, obtener_comprobantes_pendientes_admin,
                      aprobar_comprobante, rechazar_comprobante)

def render_pagos() -> None:
    """Modulo: registro y visualizacion de pagos de mensualidades (solo Administrador)."""

    # Verificación de permisos
    if not verificar_permisos("Pagos"):
        return


    st.title(":material/attach_money: Registro de Pagos")

    with st.container(border=True):
        st.subheader(":material/description: Registra y gestiona los pagos de mensualidades de los jugadores")

    jugadores = obtener_jugadores()
    if not jugadores:
        st.info("No hay jugadores registrados en el sistema. Registra un jugador primero.")
        return

    if "msg_pago_exito" in st.session_state:
        st.success(st.session_state.msg_pago_exito, icon=":material/check_circle:")
        del st.session_state.msg_pago_exito

    # Cargar datos una sola vez para todas las tabs
    lista_categorias = obtener_categorias()


    tab_registro, tab_historial, tab_modificar, tab_morosos, tab_comprobantes = st.tabs([
        "Registrar Pago", "Historial de Pagos", "Modificar / Eliminar", "Morosos", "Comprobantes Pendientes"
    ])

    with tab_registro:
        with st.container(border=True):
            st.subheader(":material/add_circle: Ingresar nuevo pago")

            c1, c2 = st.columns(2)
            with c1:
                cat_filtro = st.selectbox("Filtrar por categoria para buscar jugador", ["Todas"] + lista_categorias, key="pago_cat_filtro", format_func=format_cat)

            jugadores_filtrados = jugadores
            if cat_filtro != "Todas":
                jugadores_filtrados = [j for j in jugadores if j["categoria"] == (cat_filtro["nombre"] if isinstance(cat_filtro, dict) else cat_filtro)]

            if not jugadores_filtrados:
                st.warning("No hay jugadores en la categoria seleccionada.", icon=":material/warning:")
                opciones_jugador = []
            else:
                opciones_jugador = [f"{j.get('nombre', 'Sin Nombre')} ({j.get('rut', 'Sin RUT')}) - {j.get('categoria', 'Sin Categoría')}" for j in jugadores_filtrados]

            if opciones_jugador:
                with c2:
                    jugador_seleccionado_str = st.selectbox("Seleccionar Jugador *", opciones_jugador, key="pago_jugador_sel")

                idx_sel = opciones_jugador.index(jugador_seleccionado_str)
                jugador_sel = jugadores_filtrados[idx_sel]

                with st.container(border=True):
                    st.subheader(":material/person: Informacion del Jugador")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write(f"**Nombre:** {jugador_sel.get('nombre', 'Sin Nombre')}")
                        st.write(f"**RUT:** {jugador_sel.get('rut', 'Sin RUT')}")
                    with col_b:
                        st.write(f"**Categoria:** {jugador_sel.get('categoria', 'Sin Categoria')}")
                        st.write(f"**Apoderado:** {jugador_sel.get('apoderado_nombre', 'Sin Apoderado')} ({jugador_sel.get('apoderado_telefono', '')})")

                with st.form("form_registrar_pago", clear_on_submit=True):
                    col_m1, col_m2 = st.columns(2)
                    with col_m1:
                        mes_actual_idx = datetime.now().month - 1
                        mes_sel = st.selectbox("Mes Correspondiente *", MESES, index=mes_actual_idx)

                        anio_sel = st.selectbox("Año Correspondiente *", [datetime.now().year - 1, datetime.now().year, datetime.now().year + 1], index=1)
                        
                        monto = st.number_input(
                            "Monto pagado ($) *",
                            min_value=0, value=30000, step=5000
                        )
                    with col_m2:
                        fecha_pago = st.date_input("Fecha de pago *", value=date.today())
                        metodos_pago = ["Efectivo", "Transferencia", "Otro"]
                        metodo_pago = st.selectbox("Método de pago *", metodos_pago)

                    guardar_btn = st.form_submit_button("REGISTRAR PAGO", width="stretch", type="primary")

                    if guardar_btn:
                        pago_dict = {
                            "jugador_id": jugador_sel["id"],
                            "mes_correspondiente": mes_sel,
                            "anio_correspondiente": anio_sel,
                            "monto": int(monto),
                            "metodo_pago": metodo_pago,
                            "fecha_pago": fecha_pago.strftime("%Y-%m-%d")
                        }
                        if guardar_pago(pago_dict):
                            st.session_state.msg_pago_exito = f"Pago de ${monto:,} correspondiente a {mes_sel} para el jugador {jugador_sel['nombre']} registrado correctamente."
                            obtener_pagos.clear()
                            st.rerun()
                        else:
                            st.error("Ocurrio un error al registrar el pago.", icon=":material/error:")
            else:
                st.info("No hay jugadores elegibles para registro de pagos en este filtro.")

    with tab_historial:
        st.subheader(":material/history: Historial completo de pagos")
        
        with st.container(border=True):
            st.subheader(":material/filter_list: Filtros de Fecha")
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                mes_actual_idx = datetime.now().month - 1
                mes_hist = st.selectbox("Mes a visualizar", ["Todos"] + MESES, index=mes_actual_idx + 1, key="mes_hist")
            with col_f2:
                anio_actual = datetime.now().year
                anios = [str(a) for a in range(2024, anio_actual + 2)]
                anio_hist = st.selectbox("Año a visualizar", ["Todos"] + anios, index=anios.index(str(anio_actual)) + 1, key="anio_hist")

            mes_q_hist = None if mes_hist == "Todos" else mes_hist
            anio_q_hist = None if anio_hist == "Todos" else anio_hist
            
        pagos_lista = obtener_pagos(mes=mes_q_hist, anio=anio_q_hist)
        
        if not pagos_lista:
            st.info("Aun no se han registrado pagos en este periodo.")
        else:
            with st.container(border=True):
                st.subheader(":material/search: Filtrar y Buscar")
                
                cf1, cf2 = st.columns(2)
                with cf1:
                    filtro_hist_cat = st.selectbox("Filtrar historial por categoria", ["Todas"] + lista_categorias, key="pago_hist_cat_filtro", format_func=format_cat)
                
                pagos_mostrar = pagos_lista
                if filtro_hist_cat != "Todas":
                    pagos_mostrar = [p for p in pagos_mostrar if p.get("categoria") == (filtro_hist_cat["nombre"] if isinstance(filtro_hist_cat, dict) else filtro_hist_cat)]
                
                # Generar lista de jugadores únicos para el autocompletado
                opciones_jugadores = sorted(list(set([f"{p.get('jugador_nombre', '')} - {p.get('jugador_rut', '')}" for p in pagos_mostrar])))

                with cf2:
                    buscador_jugador = st.selectbox(
                        "Buscar Jugador (Autocompletado)", 
                        options=opciones_jugadores,
                        index=None,
                        placeholder="Empieza a escribir un nombre o RUT...",
                        key="pago_hist_buscar_autocomp"
                    )

                if buscador_jugador:
                    pagos_mostrar = [
                        p for p in pagos_mostrar 
                        if f"{p.get('jugador_nombre', '')} - {p.get('jugador_rut', '')}" == buscador_jugador
                    ]

                if not pagos_mostrar:
                    st.warning("No hay pagos registrados que coincidan con los filtros y la búsqueda actual.", icon=":material/warning:")
                else:
                    with st.container(border=True):
                        st.subheader(":material/list: Listado de Pagos")
                        df_pagos = pd.DataFrame(pagos_mostrar)[
                            ["jugador_nombre", "jugador_rut", "categoria", "mes_correspondiente", "monto", "metodo_pago", "fecha_pago"]
                        ]
                        df_pagos.columns = [
                            "Jugador", "RUT", "Categoria", "Mes", "Monto ($)", "Método", "Fecha Pago"
                        ]

                        df_pagos["Monto ($)"] = df_pagos["Monto ($)"].apply(lambda x: f"${x:,}")

                        st.dataframe(df_pagos, width="stretch", hide_index=True)
                        
                        excel_buffer = io.BytesIO()
                        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                            df_pagos.to_excel(writer, index=False, sheet_name="Pagos")
                        
                        st.write("")
                        st.download_button(
                            label=":material/download: Descargar Pagos en Excel",
                            data=excel_buffer.getvalue(),
                            file_name="Historial_Pagos.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            type="secondary"
                        )

                        total_recaudado = sum(p["monto"] for p in pagos_mostrar)
                        st.markdown(
                            f"""
                            <div class="total-recaudado">
                                Total Recaudado: <span>${total_recaudado:,}</span>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

    with tab_modificar:
        st.subheader(":material/edit: Buscar y Modificar Pagos")
        
        with st.container(border=True):
            st.subheader(":material/filter_list: Seleccionar Periodo")
            col_fm1, col_fm2 = st.columns(2)
            with col_fm1:
                mes_actual_idx = datetime.now().month - 1
                mes_mod = st.selectbox("Mes", ["Todos"] + MESES, index=mes_actual_idx + 1, key="mes_mod")
            with col_fm2:
                anio_actual = datetime.now().year
                anios = [str(a) for a in range(2024, anio_actual + 2)]
                anio_mod = st.selectbox("Año", ["Todos"] + anios, index=anios.index(str(anio_actual)) + 1, key="anio_mod")

            # We can re-use the exact same list to avoid double querying the DB if filters match
            if mes_hist == mes_mod and anio_hist == anio_mod:
                pagos_lista_mod = pagos_lista
            else:
                mes_q_mod = None if mes_mod == "Todos" else mes_mod
                anio_q_mod = None if anio_mod == "Todos" else anio_mod
                pagos_lista_mod = obtener_pagos(mes=mes_q_mod, anio=anio_q_mod)

        if not pagos_lista_mod:
            st.info("Aun no hay pagos registrados para modificar en este periodo.")
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
                            idx_mes = MESES.index(p_data["mes_correspondiente"]) if p_data["mes_correspondiente"] in MESES else 0
                            nuevo_mes = st.selectbox("Mes Correspondiente *", MESES, index=idx_mes)
                            
                            anio_db = p_data.get("anio_correspondiente")
                            if not anio_db:
                                anio_db = int(str(p_data.get("fecha_pago", datetime.now().strftime("%Y-%m-%d"))).split("-")[0])
                            
                            anios = [anio_db - 1, anio_db, anio_db + 1]
                            nuevo_anio = st.selectbox("Año Correspondiente *", anios, index=1)
                            
                            nuevo_monto = st.number_input("Monto pagado ($) *", min_value=0, value=int(p_data["monto"]), step=5000)
                        
                        with col_m2:
                            try:
                                default_date = datetime.strptime(str(p_data["fecha_pago"]).split(" ")[0].split("T")[0], "%Y-%m-%d").date()
                            except (ValueError, TypeError):
                                default_date = date.today()
                            nueva_fecha = st.date_input("Fecha de pago *", value=default_date)
                            
                            metodos_pago = ["Efectivo", "Transferencia", "Otro"]
                            idx_metodo = metodos_pago.index(p_data.get("metodo_pago", "Efectivo")) if p_data.get("metodo_pago", "Efectivo") in metodos_pago else 0
                            nuevo_metodo = st.selectbox("Método de pago *", metodos_pago, index=idx_metodo)

                        st.markdown("---")
                        st.write(":material/warning: **Confirmación requerida**")
                        confirmar = st.checkbox("Confirmo que deseo modificar o eliminar este registro de pago", key=f"conf_{p_data['id']}")
                        
                        c5, c6 = st.columns(2)
                        with c5:
                            btn_guardar = st.form_submit_button("Guardar Cambios", type="primary", width="stretch")
                        with c6:
                            btn_eliminar = st.form_submit_button("Eliminar Pago", type="secondary", width="stretch")
                            
                        if btn_guardar:
                            if not confirmar:
                                st.error("Debes marcar la casilla de confirmación para guardar.", icon=":material/error:")
                            else:
                                nuevos_datos = {
                                    "mes_correspondiente": nuevo_mes,
                                    "anio_correspondiente": nuevo_anio,
                                    "monto": int(nuevo_monto),
                                    "metodo_pago": nuevo_metodo,
                                    "fecha_pago": nueva_fecha.strftime("%Y-%m-%d")
                                }
                                if actualizar_pago(p_data["id"], nuevos_datos):
                                    st.session_state.msg_pago_exito = f"El pago de {p_data['jugador_nombre']} fue actualizado correctamente."
                                    obtener_pagos.clear()
                                    st.rerun()
                                    
                        if btn_eliminar:
                            if not confirmar:
                                st.error("Debes marcar la casilla de confirmación para eliminar el pago.", icon=":material/error:")
                            else:
                                if eliminar_pago(p_data["id"]):
                                    st.session_state.msg_pago_exito = f"El pago de {p_data['jugador_nombre']} fue eliminado del sistema."
                                    obtener_pagos.clear()
                                    st.rerun()

    # ─────────────────────────────────────────────────────────────────
    # PESTAÑA: MOROSOS
    # ─────────────────────────────────────────────────────────────────
    with tab_morosos:
        st.subheader(":material/warning: Gestion de Morosidad")

        # ── Configuracion de periodo y mensualidad ─────────────────────────
        with st.container(border=True):
            st.subheader(":material/settings: Configuracion del periodo")
            hoy = datetime.now()
            mes_def = hoy.month - 1 if hoy.month > 1 else 12
            anio_def = hoy.year if hoy.month > 1 else hoy.year - 1

            col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
            with col_cfg1:
                mes_morosos = st.selectbox(
                    "Mes a revisar",
                    options=list(range(1, 13)),
                    index=mes_def - 1,
                    format_func=lambda x: MESES[x - 1],
                    key="mor_mes"
                )
            with col_cfg2:
                anios_disp = list(range(2024, hoy.year + 1))
                idx_anio_def = anios_disp.index(anio_def) if anio_def in anios_disp else len(anios_disp) - 1
                anio_morosos = st.selectbox("Año", anios_disp, index=idx_anio_def, key="mor_anio")
            with col_cfg3:
                monto_mensualidad = st.number_input(
                    "Monto mensualidad ($)",
                    min_value=0,
                    value=st.session_state.get("mor_mensualidad", 30000),
                    step=5000,
                    key="mor_mensualidad",
                    help="Monto completo de la mensualidad. Quien pague menos que esto aparece como moroso o abonador."
                )

        # ── Carga de datos ──────────────────────────────────────────
        estado_lista = obtener_estado_pagos_mes(mes_morosos, anio_morosos)
        mes_nombre = MESES[mes_morosos - 1]

        # Clasificacion de jugadores
        sin_pago      = [j for j in estado_lista if j["total_pagado"] == 0]
        pago_parcial  = [j for j in estado_lista if 0 < j["total_pagado"] < monto_mensualidad]
        al_dia        = [j for j in estado_lista if j["total_pagado"] >= monto_mensualidad]
        total_activos = len(estado_lista)

        # ── Metricas resumen ──────────────────────────────────────────
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("Jugadores activos", total_activos)
        col_m2.metric(
            "Al dia", len(al_dia),
            delta=f"+{len(al_dia)}" if al_dia else None,
            delta_color="normal"
        )
        col_m3.metric(
            "Sin pago", len(sin_pago),
            delta=f"-{len(sin_pago)}" if sin_pago else None,
            delta_color="inverse"
        )
        col_m4.metric(
            "Abono parcial", len(pago_parcial),
            delta=f"-{len(pago_parcial)}" if pago_parcial else None,
            delta_color="inverse"
        )

        if not sin_pago and not pago_parcial:
            st.success(
                f"Todos los apoderados han completado su pago en "
                f"{mes_nombre} {anio_morosos}.",
                icon=":material/check_circle:"
            )
        else:
            # Helpers de telefono y WhatsApp
            def _normalizar_tel(tel: str) -> str:
                digits = re.sub(r"\D", "", str(tel or ""))
                if not digits:
                    return ""
                if digits.startswith("56"):
                    return digits
                if digits.startswith("9") and len(digits) == 9:
                    return "56" + digits
                if digits.startswith("0"):
                    return "56" + digits[1:]
                return "56" + digits

            def _wa_url(row: dict, plantilla: str) -> str:
                tel = _normalizar_tel(row.get("apoderado_telefono", ""))
                if not tel:
                    return ""
                falta = monto_mensualidad - row["total_pagado"]
                try:
                    msg = plantilla.format(
                        apoderado=row.get("apoderado_nombre", ""),
                        jugador=row.get("jugador_nombre", ""),
                        mes=mes_nombre,
                        anio=str(anio_morosos),
                        categoria=row.get("categoria", ""),
                        total_pagado=f"${row['total_pagado']:,.0f}",
                        falta=f"${falta:,.0f}",
                        mensualidad=f"${monto_mensualidad:,.0f}"
                    )
                except Exception:
                    msg = plantilla
                return f"https://wa.me/{tel}?text={urllib.parse.quote(msg)}"

            def _render_tabla(datos: list, plantilla: str, cols_extra: list, nombre_hoja: str, key_suffix: str):
                """Renderiza una tabla de morosos/abonadores con link WhatsApp y boton de exportar."""
                df = pd.DataFrame(datos)
                df["Contactar"] = df.apply(lambda r: _wa_url(r, plantilla), axis=1)
                cols_mostrar  = ["jugador_nombre", "jugador_rut", "categoria",
                                 "apoderado_nombre", "apoderado_telefono"] + cols_extra + ["Contactar"]
                col_cfg = {
                    "jugador_nombre":     st.column_config.TextColumn("Jugador"),
                    "jugador_rut":        st.column_config.TextColumn("RUT"),
                    "categoria":          st.column_config.TextColumn("Categoria"),
                    "apoderado_nombre":   st.column_config.TextColumn("Apoderado"),
                    "apoderado_telefono": st.column_config.TextColumn("Telefono"),
                    "Contactar":          st.column_config.LinkColumn(
                                              "Contactar por WhatsApp",
                                              display_text="Enviar mensaje"
                                          ),
                }
                if "total_pagado" in cols_extra:
                    df["total_pagado"] = df["total_pagado"].apply(lambda x: f"${x:,.0f}")
                    col_cfg["total_pagado"] = st.column_config.TextColumn("Abonado ($)")
                if "saldo_pendiente" in cols_extra:
                    df["saldo_pendiente"] = df.apply(
                        lambda r: monto_mensualidad - float(str(r["total_pagado"]).replace("$","").replace(",","") or 0)
                        if isinstance(r["total_pagado"], str)
                        else monto_mensualidad - r["total_pagado"],
                        axis=1
                    )
                    df["saldo_pendiente"] = df["saldo_pendiente"].apply(lambda x: f"${x:,.0f}")
                    col_cfg["saldo_pendiente"] = st.column_config.TextColumn("Saldo pendiente ($)")

                st.dataframe(
                    df[cols_mostrar],
                    column_config=col_cfg,
                    hide_index=True,
                    use_container_width=True
                )

                # Exportar Excel
                buf = io.BytesIO()
                df_exp = df[[c for c in cols_mostrar if c != "Contactar"]].copy()
                with pd.ExcelWriter(buf, engine="openpyxl") as w:
                    df_exp.to_excel(w, index=False, sheet_name=nombre_hoja)
                st.download_button(
                    label=":material/download: Exportar a Excel",
                    data=buf.getvalue(),
                    file_name=f"{nombre_hoja}_{mes_nombre}_{anio_morosos}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="secondary",
                    key=f"dl_{key_suffix}"
                )

            # ── Mensaje personalizable (compartido) ──────────────────────
            _msg_sin_pago = (
                "Estimado/a {apoderado}, le informamos que el pago de mensualidad "
                "del mes de {mes} {anio} correspondiente a su hijo/a {jugador} "
                "({categoria}) en Academia La Serena se encuentra PENDIENTE.\n\n"
                "El monto a cancelar es de {mensualidad}.\n"
                "Le solicitamos regularizar su situacion a la brevedad posible.\n\n"
                "Academia La Serena"
            )
            _msg_abono = (
                "Estimado/a {apoderado}, le informamos que el pago de mensualidad "
                "del mes de {mes} {anio} de su hijo/a {jugador} ({categoria}) "
                "se encuentra INCOMPLETO.\n\n"
                "Abono registrado: {total_pagado}\n"
                "Saldo pendiente: {falta} (mensualidad: {mensualidad})\n\n"
                "Le solicitamos regularizar su situacion a la brevedad posible.\n\n"
                "Academia La Serena"
            )

            with st.expander(":material/edit: Personalizar mensajes de WhatsApp", expanded=False):
                st.caption("Variables disponibles: {apoderado}, {jugador}, {mes}, {anio}, {categoria}, {total_pagado}, {falta}, {mensualidad}")
                col_msg1, col_msg2 = st.columns(2)
                with col_msg1:
                    st.write("**Mensaje para sin pago:**")
                    plantilla_sin_pago = st.text_area(
                        "sin_pago", value=_msg_sin_pago, height=180,
                        key="mor_msg_sinpago", label_visibility="collapsed"
                    )
                with col_msg2:
                    st.write("**Mensaje para abono parcial:**")
                    plantilla_abono = st.text_area(
                        "abono", value=_msg_abono, height=180,
                        key="mor_msg_abono", label_visibility="collapsed"
                    )

            # ── Tabla 1: Sin pago ─────────────────────────────────────────
            if sin_pago:
                with st.container(border=True):
                    st.subheader(
                        f":material/money_off: Sin pago registrado "
                        f"({len(sin_pago)} de {total_activos}) — {mes_nombre} {anio_morosos}"
                    )
                    _render_tabla(
                        sin_pago, plantilla_sin_pago,
                        cols_extra=[],
                        nombre_hoja="Morosos",
                        key_suffix="sinpago"
                    )

            # ── Tabla 2: Abono parcial ───────────────────────────────────
            if pago_parcial:
                # Agregar columna saldo pendiente antes de renderizar
                for row in pago_parcial:
                    row["saldo_pendiente"] = monto_mensualidad - row["total_pagado"]
                with st.container(border=True):
                    st.subheader(
                        f":material/payments: Con abono parcial "
                        f"({len(pago_parcial)} de {total_activos}) — {mes_nombre} {anio_morosos}"
                    )
                    _render_tabla(
                        pago_parcial, plantilla_abono,
                        cols_extra=["total_pagado", "saldo_pendiente"],
                        nombre_hoja="Abonadores",
                        key_suffix="abono"
                    )


    # ─────────────────────────────────────────────────────────────────
    # PESTAÑA: COMPROBANTES PENDIENTES
    # ─────────────────────────────────────────────────────────────────
    with tab_comprobantes:
        st.subheader("Comprobantes Pendientes de Aprobación")
        st.write("Revisa los comprobantes de pago enviados por los apoderados.")
        
        pendientes = obtener_comprobantes_pendientes_admin()
        
        if not pendientes:
            st.info("No hay comprobantes pendientes de revisión.")
        else:
            st.success(f"Tienes {len(pendientes)} comprobante(s) pendiente(s) de revisión.")
            
            for comp in pendientes:
                with st.container(border=True):
                    mes_nombre = MESES[comp['mes'] - 1]
                    
                    c1, c2 = st.columns([2, 1])
                    with c1:
                        st.markdown(f"#### {comp['jugador_nombre']}")
                        st.write(f"**Apoderado:** {comp['apoderado_nombre']} ({comp['apoderado_telefono']})")
                        st.write(f"**Correspondiente a:** {mes_nombre} {comp['anio']}")
                        
                        monto_sugerido = int(comp.get('monto_extraido') or 30000)
                        banco = comp.get('banco_extraido') or "Transferencia"
                        fecha_comp = comp.get('fecha_extraido') or date.today().strftime("%Y-%m-%d")
                        
                        st.write(f"**Datos extraídos del comprobante:**")
                        st.write(f"- Monto: ${comp.get('monto_extraido') or 'N/A'}")
                        st.write(f"- Banco: {comp.get('banco_extraido') or 'N/A'}")
                        st.write(f"- Fecha: {comp.get('fecha_extraido') or 'N/A'}")
                        st.write(f"- Operación: {comp.get('num_operacion') or 'N/A'}")
                        
                        with st.expander("Aprobar Pago"):
                            with st.form(f"form_aprobar_{comp['id']}"):
                                m1, m2 = st.columns(2)
                                with m1:
                                    monto_aprob = st.number_input("Monto Confirmado ($)", min_value=0, value=monto_sugerido, step=5000, key=f"ma_{comp['id']}")
                                    metodo_aprob = st.selectbox("Método de Pago", ["Transferencia", "Efectivo", "Otro"], key=f"me_{comp['id']}")
                                with m2:
                                    try:
                                        fecha_default = datetime.strptime(str(fecha_comp).split(" ")[0].split("T")[0], "%Y-%m-%d").date()
                                    except:
                                        fecha_default = date.today()
                                        
                                    fecha_aprob = st.date_input("Fecha de Pago", value=fecha_default, key=f"f_{comp['id']}")
                                
                                if st.form_submit_button("Confirmar y Aprobar Pago", type="primary"):
                                    datos_pago = {
                                        "jugador_id": comp["jugador_id"],
                                        "apoderado_id": comp["apoderado_id"],
                                        "mes_correspondiente": mes_nombre,
                                        "anio_correspondiente": comp["anio"],
                                        "monto": int(monto_aprob),
                                        "metodo_pago": metodo_aprob,
                                        "fecha_pago": fecha_aprob.strftime("%Y-%m-%d")
                                    }
                                    if aprobar_comprobante(comp['id'], datos_pago):
                                        st.session_state.msg_pago_exito = f"Comprobante aprobado y pago registrado para {comp['jugador_nombre']}."
                                        st.rerun()
                                        
                        with st.expander("Rechazar Comprobante"):
                            with st.form(f"form_rechazar_{comp['id']}"):
                                motivo = st.text_input("Motivo del rechazo", placeholder="Ej: La imagen no es clara, monto incorrecto...")
                                if st.form_submit_button("Rechazar Comprobante", type="secondary"):
                                    if not motivo.strip():
                                        st.error("Debes ingresar un motivo para rechazar.")
                                    else:
                                        if rechazar_comprobante(comp['id'], motivo):
                                            st.session_state.msg_pago_exito = f"Comprobante rechazado. El apoderado podrá subir uno nuevo."
                                            st.rerun()

                    with c2:
                        if comp.get('imagen_url'):
                            st.image(comp['imagen_url'], caption="Comprobante Subido", use_container_width=True)
                        else:
                            st.info("Sin imagen")


if __name__ == '__main__':
    import streamlit as st
    if 'authenticated' not in st.session_state or not st.session_state.authenticated:
        st.switch_page('app.py')
    else:
        render_pagos()
