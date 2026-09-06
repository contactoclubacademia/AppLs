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

from estilos import inject_css
from database import (obtener_categorias, obtener_jugadores, obtener_asistencia,
                      guardar_asistencia, obtener_asistencia_general)

def render_asistencia() -> None:
    """Modulo: toma de asistencia por fecha y categoria (Administrador y Profesor)."""
    inject_css()

    # Verificación de permisos
    permisos = st.session_state.user.get("permisos") or []
    rol = st.session_state.user.get("rol")
    if rol != "Administrador" and "Control de Asistencia" not in permisos:
        st.error("No tienes permisos para acceder a este módulo.", icon=":material/error:")
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
                cat_sel = st.selectbox("Seleccionar Categoría", categorias)

        if not cat_sel:
            return

        jugadores = obtener_jugadores(cat_sel)

        if not jugadores:
            st.info(f"No hay jugadores registrados en la categoría {cat_sel}.")
            return

        asistencia_previa = obtener_asistencia(fecha_sel.strftime("%Y-%m-%d"), cat_sel)

        with st.form("form_asistencia"):
            st.write(f"### Jugadores - {cat_sel}")
            st.caption(f"Fecha: {fecha_sel.strftime('%d/%m/%Y')}")
            
            nuevos_registros = {}
            for j in jugadores:
                rut = j["rut"]
                nombre = j["nombre"]
                
                estado_previo = asistencia_previa.get(rut, {}).get("estado", "Presente")
                
                opciones = ["Presente", "Ausente", "Justificado"]
                idx_default = opciones.index(estado_previo) if estado_previo in opciones else 0
                
                estado_sel = st.radio(
                    f"{nombre} ({rut})",
                    opciones,
                    index=idx_default,
                    horizontal=True,
                    key=f"ast_{rut}"
                )
                nuevos_registros[rut] = {"estado": estado_sel}
                
            st.markdown("---")
            guardar_btn = st.form_submit_button("GUARDAR ASISTENCIA", width="stretch", type="primary")
            
            if guardar_btn:
                if guardar_asistencia(fecha_sel.strftime("%Y-%m-%d"), cat_sel, nuevos_registros):
                    st.session_state.msg_asistencia_exito = f"Asistencia del {fecha_sel.strftime('%d/%m/%Y')} para {cat_sel} guardada correctamente."
                    st.cache_data.clear()
                    st.rerun()

    with tab2:
        with st.container(border=True):
            st.subheader(":material/history: Historial y Estadísticas Mensuales")
            
            historial_completo = obtener_asistencia_general()
            if not historial_completo:
                st.info("Aún no hay registros de asistencia en el sistema.")
            else:
                cat_hist = st.selectbox("Filtrar por Categoría", ["Todas"] + categorias, key="hist_cat")
                
                if cat_hist != "Todas":
                    historial_completo = [h for h in historial_completo if h["categoria"] == cat_hist]
                
                if not historial_completo:
                    st.warning("No hay registros para la categoría seleccionada.")
                else:
                    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
                    mes_actual = date.today().month
                    
                    cf1, cf2, cf3 = st.columns(3)
                    with cf1:
                        mes_str = st.selectbox("Mes", meses, index=mes_actual - 1)
                    with cf2:
                        anio_str = st.selectbox("Año", [date.today().year, date.today().year - 1])
                    
                    # Generar lista de jugadores únicos para autocompletado
                    jugadores_unicos = sorted(list(set([f"{h['jugador_nombre']} - {h['jugador_rut']}" for h in historial_completo])))
                    with cf3:
                        jugador_filtro = st.selectbox("Jugador (Opcional)", ["Todos"] + jugadores_unicos, index=0)
                    
                    mes_idx = meses.index(mes_str) + 1
                    
                    # Filtrar por fecha (Mes y Año) y Jugador
                    historial_mes = [
                        h for h in historial_completo
                        if int(h["fecha"].split("-")[1]) == mes_idx and int(h["fecha"].split("-")[0]) == int(anio_str)
                    ]
                    
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
                        total_justificados = sum(1 for h in historial_mes if h["estado"] == "Justificado")
                        total_registros = len(historial_mes)
                        tasa_asistencia = (total_presentes / total_registros * 100) if total_registros > 0 else 0
                        
                        svg_presente = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#28a745" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>'
                        svg_ausente = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#dc3545" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>'
                        svg_justif = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ffc107" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>'
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
                                    <div class="stats-item">
                                        {svg_justif} <b>Justificados:</b> {total_justificados}
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
