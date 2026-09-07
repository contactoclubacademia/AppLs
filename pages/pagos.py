"""
=============================================================================
 MODULO: REGISTRO DE PAGOS
=============================================================================
Modulo: registro y visualizacion de pagos de mensualidades (solo Administrador).
Diseno corporativo: contenedores con borde, botones primary, iconos Material.
=============================================================================
"""

import io
from datetime import date, datetime

import pandas as pd
import streamlit as st

from estilos import inject_css
from database import (obtener_jugadores, obtener_categorias,
                      guardar_pago, obtener_pagos, actualizar_pago, eliminar_pago)


def format_cat(cat):
    if isinstance(cat, dict):
        return cat["nombre"]
    return cat

def render_pagos() -> None:
    """Modulo: registro y visualizacion de pagos de mensualidades (solo Administrador)."""
    inject_css()

    # Verificación de permisos
    permisos = st.session_state.user.get("permisos") or []
    rol = st.session_state.user.get("rol")
    if rol != "Administrador" and "Pagos" not in permisos:
        st.error("No tienes permisos para acceder a este módulo.", icon=":material/error:")
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


    tab_registro, tab_historial, tab_modificar = st.tabs(["Registrar Pago", "Historial de Pagos", "Modificar / Eliminar"])

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
                        metodos_pago = ["Efectivo", "Transferencia", "Otro"]
                        metodo_pago = st.selectbox("Método de pago *", metodos_pago)

                    guardar_btn = st.form_submit_button("REGISTRAR PAGO", width="stretch", type="primary")

                    if guardar_btn:
                        pago_dict = {
                            "jugador_id": jugador_sel["id"],
                            "mes_correspondiente": mes_sel,
                            "monto": int(monto),
                            "metodo": metodo_pago,
                            "fecha_pago": fecha_pago.strftime("%Y-%m-%d")
                        }
                        if guardar_pago(pago_dict):
                            st.session_state.msg_pago_exito = f"Pago de ${monto:,} correspondiente a {mes_sel} para el jugador {jugador_sel['nombre']} registrado correctamente."
                            st.cache_data.clear()
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
                meses_todos = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
                mes_actual_idx = datetime.now().month - 1
                mes_hist = st.selectbox("Mes a visualizar", ["Todos"] + meses_todos, index=mes_actual_idx + 1, key="mes_hist")
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
                            ["jugador_nombre", "jugador_rut", "categoria", "mes_correspondiente", "monto", "metodo", "fecha_pago"]
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
                meses_todos = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
                mes_actual_idx = datetime.now().month - 1
                mes_mod = st.selectbox("Mes", ["Todos"] + meses_todos, index=mes_actual_idx + 1, key="mes_mod")
            with col_fm2:
                anio_actual = datetime.now().year
                anios = [str(a) for a in range(2024, anio_actual + 2)]
                anio_mod = st.selectbox("Año", ["Todos"] + anios, index=anios.index(str(anio_actual)) + 1, key="anio_mod")

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
                            meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
                            idx_mes = meses.index(p_data["mes_correspondiente"]) if p_data["mes_correspondiente"] in meses else 0
                            nuevo_mes = st.selectbox("Mes Correspondiente *", meses, index=idx_mes)
                            nuevo_monto = st.number_input("Monto pagado ($) *", min_value=0, value=int(p_data["monto"]), step=5000)
                        
                        with col_m2:
                            try:
                                default_date = datetime.strptime(str(p_data["fecha_pago"]).split(" ")[0].split("T")[0], "%Y-%m-%d").date()
                            except (ValueError, TypeError):
                                default_date = date.today()
                            nueva_fecha = st.date_input("Fecha de pago *", value=default_date)
                            
                            metodos_pago = ["Efectivo", "Transferencia", "Otro"]
                            idx_metodo = metodos_pago.index(p_data.get("metodo", "Efectivo")) if p_data.get("metodo", "Efectivo") in metodos_pago else 0
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
                                    "monto": int(nuevo_monto),
                                    "metodo": nuevo_metodo,
                                    "fecha_pago": nueva_fecha.strftime("%Y-%m-%d")
                                }
                                if actualizar_pago(p_data["id"], nuevos_datos):
                                    st.session_state.msg_pago_exito = f"El pago de {p_data['jugador_nombre']} fue actualizado correctamente."
                                    st.cache_data.clear()
                                    st.rerun()
                                    
                        if btn_eliminar:
                            if not confirmar:
                                st.error("Debes marcar la casilla de confirmación para eliminar el pago.", icon=":material/error:")
                            else:
                                if eliminar_pago(p_data["id"]):
                                    st.session_state.msg_pago_exito = f"El pago de {p_data['jugador_nombre']} fue eliminado del sistema."
                                    st.cache_data.clear()
                                    st.rerun()

if __name__ == '__main__':
    import streamlit as st
    if 'authenticated' not in st.session_state or not st.session_state.authenticated:
        st.switch_page('app.py')
    else:
        render_pagos()
