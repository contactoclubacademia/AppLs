"""
=============================================================================
 MÓDULO: PORTAL DEL APODERADO
=============================================================================
Vista personal del apoderado: estado de pagos, subida de comprobantes con
OCR (Tesseract), historial de asistencia y datos de la categoría.

Rol requerido: Apoderado
=============================================================================
"""

import io
from datetime import date, datetime

import streamlit as st

from backend.database import (
    obtener_jugadores_de_apoderado,
    obtener_pagos_apoderado,
    obtener_comprobantes_apoderado,
    obtener_asistencia_jugador_apoderado,
    guardar_comprobante_pendiente,
    obtener_horarios_categoria
)
from backend.utils import MESES


# ---------------------------------------------------------------------------
# HELPER: OCR con Tesseract
# ---------------------------------------------------------------------------

def _extraer_datos_ocr(imagen_bytes: bytes) -> dict:
    """Intenta extraer texto del comprobante usando pytesseract.
    Retorna un dict con monto, banco, fecha y num_operacion detectados (pueden ser '').
    """
    datos = {"monto": "", "banco": "", "fecha": "", "num_operacion": ""}
    try:
        import pytesseract
        from PIL import Image
        import re
        import os
        import sys

        # Si estamos en Windows, configurar la ruta de tesseract (Streamlit Cloud usa Linux)
        if sys.platform.startswith('win'):
            tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            if os.path.exists(tesseract_path):
                pytesseract.pytesseract.tesseract_cmd = tesseract_path

        img = Image.open(io.BytesIO(imagen_bytes))
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.environ["TESSDATA_PREFIX"] = os.path.join(base_dir, "assets")
        tessdata_dir_config = f'--tessdata-dir "{os.path.join(os.getcwd(), "assets")}"'
        texto = pytesseract.image_to_string(img, lang="spa", config=tessdata_dir_config)

        # Buscar monto (ej: $25.000, Monto: 25000)
        # Prioridad 1: Buscar explícitamente con signo $
        monto_match = re.search(r"\$\s*([\d]{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)", texto)
        
        if not monto_match:
            # Prioridad 2: Buscar con la palabra Monto o Total saltando caracteres basura (ej si $ se lee como S)
            monto_match = re.search(r"(?:monto|total|pagado)[^\d]*([\d]{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)", texto, re.IGNORECASE)
            
        if not monto_match:
            # Prioridad 3: Buscar número con formato de miles (ej: 25.000) asegurándose de capturar el número completo y que NO sea RUT
            monto_match = re.search(r"(?<![.,\d])([1-9]\d{0,2}(?:[.,]\d{3})+)(?![.,\d])(?!-[0-9Kk])", texto)
        
        if monto_match:
            monto_str = monto_match.group(1).replace(".", "").replace(",", "")
            datos["monto"] = monto_str

        # Buscar banco conocido
        bancos = ["BancoEstado", "Banco Estado", "Santander", "BCI", "Chile",
                  "Scotiabank", "BICE", "Itaú", "Itau", "Falabella", "Ripley",
                  "Security", "Consorcio", "Internacional", "Coopeuch", "Mercado Pago",
                  "Mach", "Tenpo"]
        for banco in bancos:
            if banco.lower() in texto.lower():
                datos["banco"] = banco
                break

        # Buscar fecha (ej: 15/09/2026, 15-09-2026, 2026-09-15)
        fecha_match = re.search(
            r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4}[/\-]\d{2}[/\-]\d{2})", texto
        )
        if fecha_match:
            datos["fecha"] = fecha_match.group(1)

        # Buscar número de operación (varias etiquetas posibles)
        op_match = re.search(
            r"(?:(?:N[°ºo]?\s*)?(?:operaci[oó]n|transacci[oó]n|folio|comprobante)[:\s]+)(\d{4,})",
            texto, re.IGNORECASE
        )
        if op_match:
            datos["num_operacion"] = op_match.group(1)
        else:
            # Fallback: primer número largo en el texto
            num_match = re.search(r"\b(\d{8,})\b", texto)
            if num_match:
                datos["num_operacion"] = num_match.group(1)

    except ImportError:
        pass  # pytesseract no instalado — devuelve dict vacío
    except Exception:
        pass

    return datos


# ---------------------------------------------------------------------------
# HELPERS VISUALES
# ---------------------------------------------------------------------------


def _mes_nombre(mes_num: int) -> str:
    if 1 <= mes_num <= 12:
        return MESES[mes_num - 1]
    return str(mes_num)


# ---------------------------------------------------------------------------
# RENDER PRINCIPAL
# ---------------------------------------------------------------------------

def render_portal_apoderado() -> None:
    """Portal personal del apoderado."""

    user = st.session_state.user
    if user.get("rol") != "Apoderado":
        st.error("Acceso restringido. Este módulo es solo para apoderados.")
        return

    apoderado_id = user.get("apoderado_id")
    if not apoderado_id:
        st.error("Tu cuenta no está vinculada a un perfil de apoderado. Contacta al administrador.")
        return

    # Mensajes de éxito/error de operaciones anteriores
    if "msg_portal_ok" in st.session_state:
        st.success(st.session_state.pop("msg_portal_ok"), icon=":material/check_circle:")
    if "msg_portal_err" in st.session_state:
        st.error(st.session_state.pop("msg_portal_err"), icon=":material/error:")

    st.title(f":material/shield_person: Portal del Apoderado")
    st.caption(f"Bienvenido/a, **{user['nombre']}**")

    # Cargar jugadores
    jugadores = obtener_jugadores_de_apoderado(apoderado_id)
    if not jugadores:
        st.info("No tienes jugadores activos registrados. Contacta al administrador.", icon=":material/info:")
        return

    # Selector de hijo si tiene más de uno
    if len(jugadores) > 1:
        jugador_sel = st.selectbox(
            "Seleccionar hijo/a",
            jugadores,
            format_func=lambda j: f"{j['nombre']} — {j['categoria_nombre']}",
            key="portal_jugador_sel"
        )
    else:
        jugador_sel = jugadores[0]

    tab_pagos, tab_asistencia, tab_categoria = st.tabs([
        ":material/payments: Mis Pagos",
        ":material/calendar_month: Asistencia",
        ":material/sports_soccer: Mi Categoría",
    ])

    # =========================================================================
    # TAB 1: MIS PAGOS
    # =========================================================================
    with tab_pagos:
        _render_tab_pagos(apoderado_id, jugador_sel)

    # =========================================================================
    # TAB 2: ASISTENCIA
    # =========================================================================
    with tab_asistencia:
        _render_tab_asistencia(jugador_sel)

    # =========================================================================
    # TAB 3: CATEGORÍA
    # =========================================================================
    with tab_categoria:
        _render_tab_categoria(jugador_sel)

    # =========================================================================
    # DERECHOS ARCOP / LEGAL (LEY 19.628)
    # =========================================================================
    st.markdown("---")
    st.caption("**Protección de Datos Personales (Ley 19.628)**")
    st.caption("Tienes derecho a acceder, rectificar, cancelar u oponerte al tratamiento de tus datos y los de tu pupilo/a. Para solicitar la **eliminación permanente** (Derecho al Olvido) de nuestros registros, por favor contacta a la administración de la academia.")


# ---------------------------------------------------------------------------
# TAB 1: PAGOS
# ---------------------------------------------------------------------------

def _render_tab_pagos(apoderado_id: str, jugador: dict) -> None:
    st.subheader(f":material/payments: Pagos de {jugador['nombre']}")

    # Cargar pagos aprobados y comprobantes enviados
    pagos_ok    = obtener_pagos_apoderado(apoderado_id)
    comprobantes = obtener_comprobantes_apoderado(apoderado_id)

    # Filtrar los del jugador seleccionado
    pagos_jug = [p for p in pagos_ok if p["jugador_id"] == jugador["id"]]
    comp_jug  = [c for c in comprobantes if c["jugador_id"] == jugador["id"]]

    # Vista del año actual
    anio_actual = date.today().year
    mes_actual  = date.today().month

    # Construir mapa mes→estado para el jugador agrupando por mes y sumando montos
    pagos_agrupados = {}
    for p in pagos_jug:
        key = (p["mes_nombre"], p["anio"])
        pagos_agrupados[key] = pagos_agrupados.get(key, 0.0) + float(p["monto"])

    pendiente_set = {(_mes_nombre(c["mes"]), c["anio"]) for c in comp_jug if c["estado"] == "pendiente"}
    rechazado_map = {(_mes_nombre(c["mes"]), c["anio"]): c for c in comp_jug if c["estado"] == "rechazado"}

    VALOR_MENSUALIDAD = 30000.0  # Valor base de la mensualidad (coincide con defecto de admin)

    with st.container(border=True):
        st.markdown("#### Estado de pagos — año actual")
        cols = st.columns(4)
        for idx, mes_name in enumerate(MESES):
            col = cols[idx % 4]
            key = (mes_name, anio_actual)
            total_mes = pagos_agrupados.get(key, 0.0)
            
            with col:
                if total_mes >= VALOR_MENSUALIDAD:
                    st.markdown(f"**{mes_name}**\n\n:material/check_circle: Pagado")
                elif total_mes > 0:
                    st.markdown(f"**{mes_name}**\n\n:material/payments: Abono (${total_mes:,.0f})")
                elif key in pendiente_set:
                    st.markdown(f"**{mes_name}**\n\n:material/pending: En revisión")
                elif key in rechazado_map:
                    st.markdown(f"**{mes_name}**\n\n:material/cancel: Rechazado")
                elif idx + 1 <= mes_actual:
                    st.markdown(f"**{mes_name}**\n\n:material/error: Sin pagar")
                else:
                    st.markdown(f"**{mes_name}**\n\n:material/radio_button_unchecked: Pendiente")

    # Mostrar motivo de rechazo si hay alguno este mes
    mes_actual_nombre = MESES[mes_actual - 1]
    if (mes_actual_nombre, anio_actual) in rechazado_map:
        comp_rech = rechazado_map[(mes_actual_nombre, anio_actual)]
        st.warning(
            f"Tu comprobante de **{mes_actual_nombre}** fue rechazado. "
            f"Motivo: _{comp_rech.get('motivo_rechazo', 'Sin especificar')}_\n\n"
            "Puedes subir uno nuevo abajo.",
            icon=":material/warning:"
        )

    st.markdown("---")

    # ---------- Formulario de subida de comprobante ----------
    _render_form_comprobante(apoderado_id, jugador)

    # ---------- Historial de comprobantes enviados ----------
    if comp_jug:
        st.markdown("#### Comprobantes enviados")
        for c in comp_jug:
            with st.expander(
                f"{_mes_nombre(c['mes'])} {c['anio']} — "
                f"${c.get('monto_extraido') or '?'} — "
                f"{c.get('estado', '').capitalize()}",
                expanded=False
            ):
                col1, col2 = st.columns(2)
                col1.markdown(f"**Estado:** {c['estado'].capitalize()}")
                col1.markdown(f"**Banco:** {c.get('banco_extraido') or '—'}")
                col1.markdown(f"**N° operación:** {c.get('num_operacion') or '—'}")
                col2.markdown(f"**Fecha comprobante:** {c.get('fecha_extraido') or '—'}")
                col2.markdown(f"**Enviado el:** {str(c.get('creado_en', ''))[:10]}")
                if c.get("motivo_rechazo"):
                    st.error(f"Motivo de rechazo: {c['motivo_rechazo']}")
                if c.get("imagen_url"):
                    col_img, _ = st.columns([1, 2])
                    with col_img:
                        st.image(c["imagen_url"], caption="Comprobante", width=250)

    # ---------- Historial de pagos aprobados ----------
    if pagos_jug:
        st.markdown("#### Historial de pagos aprobados")
        for p in pagos_jug:
            st.markdown(
                f":material/check_circle: **{p['mes_nombre']} {p['anio']}** — "
                f"${p['monto']:,.0f} — {p['metodo_pago'] or 'Sin método'} — "
                f"Pagado el {p['fecha_pago']}"
            )


def _render_form_comprobante(apoderado_id: str, jugador: dict) -> None:
    """Formulario para subir un comprobante con OCR."""
    with st.container(border=True):
        st.subheader(":material/upload_file: Subir comprobante de pago")

        anio_actual = date.today().year
        mes_actual  = date.today().month

        # Hacemos el uploader principal al inicio y que ocupe todo el ancho
        st.markdown("#### Paso 1: Sube la foto del comprobante")
        st.write("Sube una foto clara del comprobante. El sistema intentará leer los datos automáticamente.")
        
        st.markdown(
            """
            <style>
            [data-testid="stFileUploaderDropzone"] {
                padding: 3.5rem 1rem !important;
                min-height: 200px !important;
            }
            [data-testid="stFileUploaderDropzone"] button {
                transform: scale(1.3);
                margin-right: 15px;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        
        archivo = st.file_uploader(
            "Foto del comprobante (JPG, PNG, WEBP) *",
            type=["jpg", "jpeg", "png", "webp"],
            key="comp_archivo",
            label_visibility="collapsed"
        )

        if not archivo:
            # Limpiar el estado si no hay archivo
            if "last_archivo_id" in st.session_state:
                st.session_state.pop("last_archivo_id", None)
                st.session_state.pop("ocr_exitoso", None)
                st.session_state.pop("comp_monto", None)
                st.session_state.pop("comp_banco", None)
                st.session_state.pop("comp_fecha", None)
                st.session_state.pop("comp_num_op", None)
                st.rerun()
            
            # Opción para rellenar manualmente si hay error al subir
            st.write("")
            ingresar_manual = st.checkbox("¿Tienes problemas al subir la foto? Rellenar datos manualmente")
            if not ingresar_manual:
                return
        else:
            ingresar_manual = False

        st.markdown("---")
        st.markdown("#### Paso 2: Revisa y completa los datos")

        if archivo:
            img_bytes = archivo.read()
            
            # Mostrar la imagen más pequeña centrada en una columna
            col_img, _ = st.columns([1, 2])
            with col_img:
                st.image(img_bytes, caption="Vista previa del comprobante", width=250)

            if st.session_state.get("last_archivo_id") != archivo.file_id:
                with st.spinner("Leyendo datos del comprobante..."):
                    datos_ocr = _extraer_datos_ocr(img_bytes)
                
                st.session_state["comp_monto"] = datos_ocr.get("monto", "")
                st.session_state["comp_banco"] = datos_ocr.get("banco", "")
                st.session_state["comp_fecha"] = datos_ocr.get("fecha", "")
                st.session_state["comp_num_op"] = datos_ocr.get("num_operacion", "")
                st.session_state["ocr_exitoso"] = any([datos_ocr.get("monto"), datos_ocr.get("banco"), datos_ocr.get("fecha")])
                st.session_state["last_archivo_id"] = archivo.file_id
                st.rerun()
                
            if st.session_state.get("ocr_exitoso"):
                st.success("Datos extraídos automáticamente. Revisa y corrige si es necesario.", icon=":material/auto_fix_high:")
            else:
                st.info("No se pudieron extraer datos automáticamente. Completa los campos manualmente.", icon=":material/info:")

        c1, c2 = st.columns(2)
        with c1:
            mes_sel = st.selectbox(
                "Mes a pagar *",
                MESES,
                index=mes_actual - 1,
                key="comp_mes"
            )
        with c2:
            anio_sel = st.number_input(
                "Año *",
                min_value=2020,
                max_value=anio_actual + 1,
                value=anio_actual,
                key="comp_anio"
            )

        st.markdown("##### Detalles del pago")
        c3, c4 = st.columns(2)
        with c3:
            monto_inp = st.text_input("Monto ($) *", key="comp_monto", placeholder="Ej: 25000")
            banco_inp = st.text_input("Banco / Plataforma", key="comp_banco", placeholder="Ej: BancoEstado, Mercado Pago...")
        with c4:
            fecha_inp = st.text_input("Fecha del comprobante", key="comp_fecha", placeholder="Ej: 15/09/2026")
            num_op_inp = st.text_input("N° Operación / Folio", key="comp_num_op", placeholder="Ej: 00012345678")

        btn_enviar = st.button(
            ":material/send: Enviar comprobante al administrador",
            type="primary",
            use_container_width=True,
            key="btn_enviar_comp"
        )

        if btn_enviar:
            if not archivo and not ingresar_manual:
                st.error("Debes subir la foto del comprobante.", icon=":material/error:")
            elif not monto_inp.strip():
                st.error("Ingresa el monto del comprobante.", icon=":material/error:")
            else:
                mes_num = MESES.index(mes_sel) + 1

                try:
                    monto_num = float(monto_inp.strip().replace(".", "").replace(",", "."))
                except ValueError:
                    monto_num = None

                # Parsear fecha si es posible
                fecha_dt = None
                if fecha_inp.strip():
                    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y"):
                        try:
                            fecha_dt = datetime.strptime(fecha_inp.strip(), fmt).date().isoformat()
                            break
                        except ValueError:
                            continue

                # Subir imagen
                img_url, img_path = None, None
                if archivo:
                    # Usamos getvalue() en lugar de read() por si ya se leyó
                    from backend.database import subir_comprobante_imagen
                    img_url, img_path = subir_comprobante_imagen(archivo.getvalue(), archivo.name, apoderado_id)

                datos = {
                    "apoderado_id":  apoderado_id,
                    "jugador_id":    jugador["id"],
                    "mes":           mes_num,
                    "anio":          int(anio_sel),
                    "monto_extraido": monto_num,
                    "banco_extraido": banco_inp.strip() or None,
                    "fecha_extraido": fecha_dt,
                    "num_operacion":  num_op_inp.strip() or None,
                    "imagen_url":    img_url,
                    "imagen_path":   img_path,
                    "estado":        "pendiente",
                }

                if guardar_comprobante_pendiente(datos):
                    obtener_comprobantes_apoderado.clear()
                    st.session_state["msg_portal_ok"] = (
                        f"Comprobante de {mes_sel} {int(anio_sel)} enviado correctamente. "
                        "El administrador lo revisará pronto."
                    )
                    st.session_state.pop("comp_monto", None)
                    st.session_state.pop("comp_banco", None)
                    st.session_state.pop("comp_fecha", None)
                    st.session_state.pop("comp_num_op", None)
                    st.session_state.pop("last_archivo_id", None)
                    st.session_state.pop("ocr_exitoso", None)
                    st.rerun()
                else:
                    st.error(
                        "No se pudo enviar el comprobante. "
                        "Es posible que ya hayas enviado uno para este mes.",
                        icon=":material/error:"
                    )


# ---------------------------------------------------------------------------
# TAB 2: ASISTENCIA
# ---------------------------------------------------------------------------

def _render_tab_asistencia(jugador: dict) -> None:
    st.subheader(f":material/calendar_month: Asistencia de {jugador['nombre']}")

    asistencias = obtener_asistencia_jugador_apoderado(jugador["id"])
    if not asistencias:
        st.info("No hay registros de asistencia aún.", icon=":material/info:")
        return

    total     = len(asistencias)
    presentes = sum(1 for a in asistencias if a["estado"] == "Presente")
    pct       = (presentes / total * 100) if total else 0

    # Métricas de resumen
    c1, c2, c3 = st.columns(3)
    c1.metric("Total clases", total)
    c2.metric("Presentes", presentes)
    c3.metric("% Asistencia", f"{pct:.1f}%")

    st.progress(pct / 100)

    # Tabla de asistencias
    import pandas as pd
    df = pd.DataFrame(asistencias)
    df["estado_icon"] = df["estado"].map({"Presente": "Presente", "Ausente": "Ausente"})
    df = df.rename(columns={"fecha": "Fecha", "estado_icon": "Estado"})[["Fecha", "Estado"]]
    st.dataframe(df, hide_index=True, use_container_width=True)


# ---------------------------------------------------------------------------
# TAB 3: CATEGORÍA
# ---------------------------------------------------------------------------

def _render_tab_categoria(jugador: dict) -> None:
    st.subheader(f":material/sports_soccer: {jugador['categoria_nombre']}")

    with st.container(border=True):
        col1, col2 = st.columns(2)
        col1.markdown(f"**Jugador:** {jugador['nombre']}")
        col1.markdown(f"**Categoría:** {jugador['categoria_nombre']}")
        col2.markdown(f"**Entrenador/a:** {jugador['profesor_nombre']}")
        if jugador.get("fecha_nacimiento"):
            col2.markdown(f"**Fecha nacimiento:** {jugador['fecha_nacimiento']}")

    st.markdown("#### Horario Semanal")
    horarios = obtener_horarios_categoria(jugador["categoria_id"])
    if horarios:
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
    else:
        st.info("Esta categoría no tiene un horario configurado aún.")

    st.write("")
    st.info(
        "Para consultas sobre horarios o actividades, contacta al administrador.",
        icon=":material/info:"
    )


if __name__ == "__main__":
    import streamlit as st
    st.switch_page("../app.py")
