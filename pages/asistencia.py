"""
=============================================================================
 MODULO: CONTROL DE ASISTENCIA
=============================================================================
Modulo: toma de asistencia por fecha y categoria (Administrador y Profesor).
Diseno corporativo: contenedores con borde, botones primary, iconos Material.
=============================================================================
"""

import io
from datetime import date

import pandas as pd
import streamlit as st

from backend.database import (obtener_categorias, obtener_jugadores, obtener_asistencia,
                      guardar_asistencia, obtener_asistencia_general, obtener_horarios_categoria)
from backend.utils import MESES, verificar_permisos

def render_asistencia() -> None:
    """Modulo: toma de asistencia por fecha y categoria (Administrador y Profesor)."""

    # Verificación de permisos
    if not verificar_permisos("Control de Asistencia"):
        return


    st.title(":material/calendar_check: Control de Asistencia")

    if "msg_asistencia_exito" in st.session_state:
        st.success(st.session_state.msg_asistencia_exito, icon=":material/check_circle:")
        del st.session_state.msg_asistencia_exito

    tab1, tab2 = st.tabs(["Tomar Asistencia", "Historial de Asistencia"])

    with tab1:
        with st.container(border=True):
            st.subheader(":material/event_available: Tomar lista por categoría")
            
            categorias = obtener_categorias()
            if not categorias:
                st.warning("No hay categorías creadas. Ve a 'Categorías' para crear una.")
                return

            c1, c2 = st.columns(2)
            with c1:
                fecha_sel = st.date_input("Fecha de asistencia", value=date.today())
            with c2:
                cat_sel = st.selectbox("Seleccionar Categoría", categorias, format_func=lambda x: x["nombre"] if isinstance(x, dict) else x)

        if not cat_sel:
            return

        cat_id = cat_sel["id"] if isinstance(cat_sel, dict) else None

        with st.expander("Ver Horario Semanal de la Categoría"):
            horarios = obtener_horarios_categoria(cat_id)
            if not horarios:
                st.info("Esta categoría no tiene un horario configurado.")
            else:
                dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                cols_dias = st.columns(7)
                for i, col in enumerate(cols_dias):
                    dia_num = i + 1
                    with col:
                        st.markdown(f"<div style='text-align: center;'><b>{dias_semana[i][:3]}</b></div>", unsafe_allow_html=True)
                        horarios_dia = [h for h in horarios if h["dia_semana"] == dia_num]
                        if not horarios_dia:
                            st.caption("<div style='text-align: center; font-size: 11px;'>Libre</div>", unsafe_allow_html=True)
                        else:
                            for h in horarios_dia:
                                h_inicio = str(h["hora_inicio"])[:5]
                                h_fin = str(h["hora_fin"])[:5]
                                with st.container(border=True):
                                    st.markdown(f"<div style='text-align: center; font-size: 13px;'>{h_inicio}<br>{h_fin}</div>", unsafe_allow_html=True)

        jugadores = obtener_jugadores(cat_id)

        if not jugadores:
            st.info(f"No hay jugadores registrados en la categoría {cat_sel['nombre']}.")
            return

        asistencia_previa_list = obtener_asistencia(fecha_sel.strftime("%Y-%m-%d"), cat_sel["id"] if isinstance(cat_sel, dict) else None)
        asistencia_previa = {a["jugador_id"]: a for a in asistencia_previa_list}

        with st.form("form_asistencia"):
            st.write(f"### Jugadores - {cat_sel['nombre']}")
            st.caption(f"Fecha: {fecha_sel.strftime('%d/%m/%Y')}")
            
            nuevos_registros = []
            for j in jugadores:
                rut = j["rut"]
                jid = j["id"]
                nombre = j["nombre"]
                
                estado_previo = asistencia_previa.get(jid, {}).get("estado", "Presente")
                
                opciones = ["Presente", "Ausente"]
                idx_default = opciones.index(estado_previo) if estado_previo in opciones else 0
                
                estado_sel = st.radio(
                    f"{nombre} ({rut})",
                    opciones,
                    index=idx_default,
                    horizontal=True,
                    key=f"ast_{rut}"
                )
                nuevos_registros.append({"jugador_id": jid, "estado": estado_sel})
                
            st.markdown("---")
            guardar_btn = st.form_submit_button("GUARDAR ASISTENCIA", width="stretch", type="primary")
            
            if guardar_btn:
                if guardar_asistencia(fecha_sel.strftime("%Y-%m-%d"), cat_sel["id"], nuevos_registros):
                    st.session_state.msg_asistencia_exito = f"Asistencia del {fecha_sel.strftime('%d/%m/%Y')} para {cat_sel['nombre']} guardada correctamente."
                    obtener_asistencia_general.clear()
                    st.rerun()

    with tab2:
        with st.container(border=True):
            st.subheader(":material/history: Historial y Estadísticas Mensuales")
            
            mes_actual = date.today().month
            
            cf1, cf2, cf3 = st.columns(3)
            with cf1:
                mes_str = st.selectbox("Mes", MESES, index=mes_actual - 1)
            with cf2:
                anio_str = st.selectbox("Año", [date.today().year, date.today().year - 1])
                
            mes_idx = MESES.index(mes_str) + 1
            
            # Traer solo los registros de este mes y año desde el servidor
            historial_mes = obtener_asistencia_general(mes=mes_idx, anio=int(anio_str))
            
            if not historial_mes:
                st.info("No hay registros de asistencia en el mes seleccionado.")
            else:
                cat_hist = st.selectbox("Filtrar por Categoría", ["Todas"] + categorias, format_func=lambda x: x["nombre"] if isinstance(x, dict) else x, key="hist_cat")
                
                if cat_hist != "Todas":
                    historial_mes = [h for h in historial_mes if h["categoria"] == cat_hist["nombre"]]
                
                if not historial_mes:
                    st.warning("No hay registros para la categoría seleccionada.")
                else:
                    # Generar lista de jugadores únicos para autocompletado
                    jugadores_unicos = sorted(list(set([f"{h['jugador_nombre']} - {h['jugador_rut']}" for h in historial_mes])))
                    with cf3:
                        jugador_filtro = st.selectbox("Jugador (Opcional)", ["Todos"] + jugadores_unicos, index=0)
                    
                    if jugador_filtro != "Todos":
                        historial_mes = [h for h in historial_mes if f"{h['jugador_nombre']} - {h['jugador_rut']}" == jugador_filtro]
                    
                    if not historial_mes:
                        st.warning("No hay registros que coincidan con estos filtros en el mes seleccionado.", icon=":material/warning:")
                    else:
                        df_historial = pd.DataFrame(historial_mes)[
                            ["fecha", "jugador_nombre", "jugador_rut", "categoria", "estado"]
                        ]
                        df_historial.columns = ["Fecha", "Jugador", "RUT", "Categoría", "Estado"]
                        df_historial = df_historial.sort_values(by=["Fecha", "Jugador"], ascending=[False, True])
                        
                        st.write("")
                        st.dataframe(df_historial, width="stretch", hide_index=True)
                        
                        excel_buffer = io.BytesIO()
                        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                            df_historial.to_excel(writer, index=False, sheet_name="Asistencia")
                        
                        st.write("")
                        st.download_button(
                            label=":material/download: Descargar Historial en Excel",
                            data=excel_buffer.getvalue(),
                            file_name=f"Historial_Asistencia_{mes_str}_{anio_str}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            type="secondary"
                        )
                        
                        # Resumen Estadístico Mensual con iconos SVG en línea
                        total_presentes = sum(1 for h in historial_mes if h["estado"] == "Presente")
                        total_ausentes = sum(1 for h in historial_mes if h["estado"] == "Ausente")
                        total_registros = len(historial_mes)
                        tasa_asistencia = (total_presentes / total_registros * 100) if total_registros > 0 else 0
                        
                        svg_presente = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#28a745" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>'
                        svg_ausente = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#dc3545" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>'
                        svg_tasa = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#17a2b8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="5" x2="5" y2="19"></line><circle cx="6.5" cy="6.5" r="2.5"></circle><circle cx="17.5" cy="17.5" r="2.5"></circle></svg>'
                        
                        st.markdown(
                            f"""
                            <div class="stats-card">
                                <h4>Estadísticas del Mes ({mes_str} {anio_str})</h4>
                                <div class="stats-row">
                                    <div class="stats-item">
                                        {svg_presente} <b>Presentes:</b> {total_presentes}
                                    </div>
                                    <div class="stats-item">
                                        {svg_ausente} <b>Ausentes:</b> {total_ausentes}
                                    </div>
                                    <div class="stats-item" style="color: #17a2b8;">
                                        {svg_tasa} <b>Tasa de Asistencia:</b> {tasa_asistencia:.1f}%
                                    </div>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

if __name__ == '__main__':
    import streamlit as st
    if 'authenticated' not in st.session_state or not st.session_state.authenticated:
        st.switch_page('app.py')
    else:
        render_asistencia()
