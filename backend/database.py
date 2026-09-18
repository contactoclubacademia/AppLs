from datetime import date, datetime
from typing import Optional
import logging

import streamlit as st
from supabase import create_client, Client

logger = logging.getLogger(__name__)


import functools

def user_cached(ttl=60):
    """
    Decorador que envuelve @st.cache_data inyectando automáticamente
    el ID del usuario actual en la clave de caché.
    Previene fugas de datos entre sesiones.
    """
    def decorator(func):
        @st.cache_data(ttl=ttl)
        @functools.wraps(func)
        def _cached_func(user_id: str, *args, **kwargs):
            return func(*args, **kwargs)
            
        @functools.wraps(func)
        def _caller(*args, **kwargs):
            user_id = "anon"
            if "user" in st.session_state and isinstance(st.session_state.user, dict):
                user_id = st.session_state.user.get("id", "anon")
            return _cached_func(user_id, *args, **kwargs)
            
        _caller.clear = _cached_func.clear
        return _caller
    return decorator


def _normalizar_url_supabase(url_bruta: str) -> str:
    url = (url_bruta or "").strip().strip('"').strip("'")
    if url and not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    for sufijo in ("/rest/v1/", "/rest/v1", "/auth/v1/", "/auth/v1"):
        if url.endswith(sufijo):
            url = url[: -len(sufijo)]
    return url.rstrip("/")

SUPABASE_URL = _normalizar_url_supabase(st.secrets["SUPABASE_URL"])
# Clave pública para cliente general (RLS activado)
SUPABASE_KEY = st.secrets["SUPABASE_KEY"].strip().strip('"').strip("'")
# Clave privada para tareas de administración exclusivas
SUPABASE_SERVICE_KEY = st.secrets.get("SUPABASE_SERVICE_KEY", "").strip().strip('"').strip("'")

def get_supabase() -> Client:
    """Retorna un cliente Supabase enlazado a la sesión actual del usuario."""
    if "supabase_client" not in st.session_state:
        st.session_state.supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        st.session_state._supabase_session_set = False
        
    client = st.session_state.supabase_client
    
    # Inyectar sesión si existe para que RLS funcione correctamente
    # Solo se setea una vez por sesión para evitar llamadas repetidas
    if not st.session_state.get("_supabase_session_set", False):
        if "access_token" in st.session_state and "refresh_token" in st.session_state:
            try:
                client.auth.set_session(st.session_state["access_token"], st.session_state["refresh_token"])
                st.session_state._supabase_session_set = True
            except Exception as e:
                logger.warning(f"Error seteando sesión en cliente Supabase: {e}")
            
    return client


# =============================================================================
# UTILIDADES MODELO COPO DE NIEVE (SNOWFLAKE)
# =============================================================================

def _fecha_to_fk_tiempo(fecha) -> int:
    """Convierte una fecha a la clave subrogada INT de dim_tiempo (YYYYMMDD)."""
    if isinstance(fecha, (date, datetime)):
        return int(fecha.strftime("%Y%m%d"))
    return int(str(fecha).replace("-", "").split("T")[0].split(" ")[0])


# =============================================================================
# CAPA DE DATOS - JUGADORES (dim_jugador)
# =============================================================================

def guardar_jugador(datos_completos: dict) -> bool:
    try:
        # 1. Separar datos del apoderado
        apoderado_data = {
            "rut": datos_completos.pop("apoderado_rut"),
            "nombre": datos_completos.pop("apoderado_nombre"),
            "telefono": datos_completos.pop("apoderado_telefono"),
            "correo": datos_completos.pop("apoderado_correo"),
            "telefono_emergencia": datos_completos.pop("telefono_emergencia")
        }
        
        # Guardar (Upsert) el apoderado primero
        res_apo = get_supabase().table("dim_apoderado").upsert(apoderado_data, on_conflict="rut").execute()
        if not res_apo.data:
            st.error("Error al registrar el apoderado.")
            return False
            
        # 2. Guardar el jugador
        datos_completos["apoderado_id"] = res_apo.data[0]["id"]
        get_supabase().table("dim_jugador").insert(datos_completos).execute()
        return True
    except Exception as e:
        logger.error(f"Error al guardar jugador: {e}")
        st.error("No se pudo guardar el jugador. Verifica los datos e intenta de nuevo.")
        return False

def actualizar_jugador(id: str, datos_completos: dict) -> bool:
    try:
        apoderado_keys = ["apoderado_rut", "apoderado_nombre", "apoderado_telefono", "apoderado_correo", "telefono_emergencia"]
        apoderado_data = {}
        for k in apoderado_keys:
            if k in datos_completos:
                apoderado_data[k] = datos_completos.pop(k)
        
        if "apoderado_rut" in apoderado_data and apoderado_data["apoderado_rut"]:
            apoderado_upd = {
                "rut": apoderado_data["apoderado_rut"],
                "nombre": apoderado_data.get("apoderado_nombre", ""),
                "telefono": apoderado_data.get("apoderado_telefono", ""),
                "correo": apoderado_data.get("apoderado_correo", ""),
                "telefono_emergencia": apoderado_data.get("telefono_emergencia", "")
            }
            res_apo = get_supabase().table("dim_apoderado").upsert(apoderado_upd, on_conflict="rut").execute()
            if res_apo.data:
                datos_completos["apoderado_id"] = res_apo.data[0]["id"]
            
        res = get_supabase().table("dim_jugador").update(datos_completos).eq("id", id).execute()
        if not res.data:
            st.error("No se pudo actualizar (0 filas afectadas).", icon=":material/error:")
            return False
        return True
    except Exception as e:
        logger.error(f"Error al actualizar jugador: {e}")
        st.error("No se pudo actualizar el jugador. Intenta de nuevo.")
        return False

def eliminar_jugador(id: str) -> bool:
    try:
        res = get_supabase().table("dim_jugador").update({
            "estado": "Inactivo",
            "categoria_id": None
        }).eq("id", id).execute()
        if not res.data:
            st.error("No se pudo dar de baja al jugador.", icon=":material/error:")
            return False
        return True
    except Exception as e:
        logger.error(f"Error al dar de baja jugador: {e}")
        st.error("No se pudo dar de baja al jugador. Intenta de nuevo.")
        return False

def activar_jugador(id: str, categoria_id: str) -> bool:
    try:
        res = get_supabase().table("dim_jugador").update({
            "estado": "Activo",
            "categoria_id": categoria_id
        }).eq("id", id).execute()
        if not res.data:
            st.error("No se pudo activar al jugador.", icon=":material/error:")
            return False
        return True
    except Exception as e:
        logger.error(f"Error al activar jugador: {e}")
        st.error("No se pudo activar al jugador. Intenta de nuevo.")
        return False

@user_cached(ttl=60)
def obtener_jugadores(categoria_id: Optional[str] = None) -> list:
    try:
        query = get_supabase().table("dim_jugador").select("*, dim_categoria(nombre), dim_apoderado(*)")
        if categoria_id:
            query = query.eq("categoria_id", categoria_id)
        res = query.execute()
        
        jugadores_procesados = []
        if res.data:
            for j in res.data:
                apoderado = j.pop("dim_apoderado", {}) or {}
                j["apoderado_rut"] = apoderado.get("rut", "")
                j["apoderado_nombre"] = apoderado.get("nombre", "")
                j["apoderado_telefono"] = apoderado.get("telefono", "")
                j["apoderado_correo"] = apoderado.get("correo", "")
                j["telefono_emergencia"] = apoderado.get("telefono_emergencia", "")
                
                if "dim_categoria" in j and j["dim_categoria"]:
                    j["categoria"] = j["dim_categoria"]["nombre"]
                else:
                    j["categoria"] = "Sin Categoria"
                jugadores_procesados.append(j)
        return jugadores_procesados
    except Exception as e:
        logger.error(f"Error al obtener jugadores: {e}")
        st.error("No se pudieron cargar los jugadores. Intenta recargar la página.")
        return []

# =============================================================================
# CAPA DE DATOS - CATEGORÍAS (dim_categoria)
# =============================================================================

@user_cached(ttl=60)
def obtener_categorias() -> list:
    try:
        response = get_supabase().table("dim_categoria").select("*, dim_usuario(nombre)").order("nombre").execute()
        cats = response.data if response.data else []
        for c in cats:
            if "dim_usuario" in c and c["dim_usuario"]:
                c["profesor_nombre"] = c["dim_usuario"].get("nombre", "Sin Profesor")
            else:
                c["profesor_nombre"] = "Sin Profesor"
        return cats
    except Exception as e:
        logger.error(f"Error al obtener categorías: {e}")
        st.error("No se pudieron cargar las categorías. Intenta recargar la página.")
        return []

def crear_categoria(nombre: str, profesor_id: str = None) -> bool:
    nombre = nombre.strip()
    if not nombre:
        st.error("El nombre de la categoría no puede estar vacío.", icon=":material/warning:")
        return False
    try:
        data = {"nombre": nombre}
        if profesor_id:
            data["profesor_id"] = profesor_id
        get_supabase().table("dim_categoria").insert(data).execute()
        return True
    except Exception as e:
        logger.error(f"Error al crear categoría: {e}")
        st.error("No se pudo crear la categoría. Es posible que ya exista.")
        return False

def desvincular_jugadores_categoria(id: str) -> bool:
    try:
        get_supabase().table("dim_jugador").update({"categoria_id": None}).eq("categoria_id", id).execute()
        return True
    except Exception as e:
        logger.error(f"Error al desvincular jugadores: {e}")
        st.error("No se pudieron desvincular los jugadores de la categoría.")
        return False

def eliminar_categoria(id: str) -> bool:
    try:
        res = get_supabase().table("dim_categoria").delete().eq("id", id).execute()
        if not res.data:
            st.error("No se pudo eliminar la categoría.", icon=":material/error:")
            return False
        return True
    except Exception as e:
        logger.error(f"Error al eliminar categoría: {e}")
        st.error("No se pudo eliminar la categoría. Intenta de nuevo.")
        return False

def actualizar_profesor_categoria(id: str, profesor_id: str = None) -> bool:
    try:
        res = get_supabase().table("dim_categoria").update({"profesor_id": profesor_id}).eq("id", id).execute()
        if not res.data:
            return False
        return True
    except Exception as e:
        logger.error(f"Error al actualizar profesor de categoría: {e}")
        st.error("No se pudo actualizar el profesor. Intenta de nuevo.")
        return False

@user_cached(ttl=60)
def obtener_profesores() -> list:
    try:
        res = get_supabase().table("dim_usuario").select("*").eq("rol", "Profesor").order("nombre").execute()
        return res.data if res.data else []
    except Exception as e:
        logger.error(f"Error al cargar lista de profesores: {e}")
        return []

@user_cached(ttl=60)
def obtener_horarios_categoria(categoria_id: str) -> list:
    try:
        res = get_supabase().table("dim_horario_categoria").select("*").eq("categoria_id", categoria_id).order("dia_semana").order("hora_inicio").execute()
        return res.data if res.data else []
    except Exception as e:
        logger.error(f"Error al obtener horarios de categoría: {e}")
        return []

def agregar_horario_categoria(categoria_id: str, dia_semana: int, hora_inicio: str, hora_fin: str) -> bool:
    try:
        data = {
            "categoria_id": categoria_id,
            "dia_semana": dia_semana,
            "hora_inicio": hora_inicio,
            "hora_fin": hora_fin
        }
        res = get_supabase().table("dim_horario_categoria").insert(data).execute()
        return True
    except Exception as e:
        logger.error(f"Error al agregar horario: {e}")
        st.error("No se pudo agregar el horario. Es posible que el horario ya exista o se cruce.", icon=":material/error:")
        return False

def eliminar_horario_categoria(id: str) -> bool:
    try:
        res = get_supabase().table("dim_horario_categoria").delete().eq("id", id).execute()
        if not res.data:
            st.error("No se pudo eliminar el horario.", icon=":material/error:")
            return False
        return True
    except Exception as e:
        logger.error(f"Error al eliminar horario: {e}")
        st.error("Error al eliminar horario. Intenta de nuevo.")
        return False

# =============================================================================
# CAPA DE DATOS - ASISTENCIA (fact_asistencia)
# =============================================================================

@user_cached(ttl=30)
def obtener_asistencia(fecha: date, categoria_id: str) -> list:
    try:
        fk_tiempo = _fecha_to_fk_tiempo(fecha)
        res = get_supabase().table("fact_asistencia").select("*").eq("fk_tiempo", fk_tiempo).eq("categoria_id", categoria_id).execute()
        return res.data if res.data else []
    except Exception as e:
        logger.error(f"Error al obtener asistencia: {e}")
        st.error("No se pudo cargar la asistencia. Intenta de nuevo.")
        return []

def guardar_asistencia(fecha: date, categoria_id: str, registros: list) -> bool:
    if not registros:
        return True
    try:
        fk_tiempo = _fecha_to_fk_tiempo(fecha)
        current_user_id = st.session_state.user.get("id")
        
        data_to_upsert = [
            {
                "fk_tiempo": fk_tiempo,
                "categoria_id": categoria_id,
                "jugador_id": reg["jugador_id"],
                "estado": reg["estado"],
                "profesor_id": current_user_id
            }
            for reg in registros
        ]
        get_supabase().table("fact_asistencia").upsert(data_to_upsert, on_conflict="jugador_id, fk_tiempo").execute()
        return True
    except Exception as e:
        logger.error(f"Error al guardar asistencia: {e}")
        st.error("No se pudo guardar la asistencia (posible restricción RLS o duplicado).")
        return False

@user_cached(ttl=60)
def obtener_asistencia_general(mes: Optional[int] = None, anio: Optional[int] = None) -> list:
    try:
        query = get_supabase().table("fact_asistencia").select("*, dim_jugador(nombre, rut, dim_categoria(nombre)), dim_tiempo(fecha)")
        
        if anio and mes:
            # Filtrar directamente por rango de fk_tiempo (YYYYMMDD)
            # Esto es más eficiente que filtrar por atributos embebidos de dim_tiempo
            import calendar
            ultimo_dia = calendar.monthrange(anio, mes)[1]
            fk_inicio = int(f"{anio}{mes:02d}01")
            fk_fin = int(f"{anio}{mes:02d}{ultimo_dia:02d}")
            query = query.gte("fk_tiempo", fk_inicio).lte("fk_tiempo", fk_fin)
            
        res = query.execute()
        asistencias = []
        if res.data:
            for row in res.data:
                t_obj = row.get("dim_tiempo") or {}
                jug = row.get("dim_jugador") or {}
                cat = jug.get("dim_categoria") or {}
                a_out = row.copy()
                a_out["fecha"] = t_obj.get("fecha", "")
                a_out["jugador_nombre"] = jug.get("nombre", "Desconocido")
                a_out["jugador_rut"] = jug.get("rut", "Desconocido")
                a_out["categoria"] = cat.get("nombre", "Sin Categoría")
                a_out.pop("dim_jugador", None)
                a_out.pop("dim_tiempo", None)
                asistencias.append(a_out)
        return asistencias
    except Exception as e:
        logger.error(f"Error al obtener historial de asistencia: {e}")
        st.error("No se pudo cargar el historial de asistencia. Intenta recargar la página.")
        return []

# =============================================================================
# CAPA DE DATOS - PAGOS (fact_pagos)
# =============================================================================

def guardar_pago(pago_data: dict) -> bool:
    try:
        from utils import MESES
        pago_data = pago_data.copy()
        
        fecha_str = pago_data.pop("fecha_pago")
        pago_data["fk_tiempo_pago"] = _fecha_to_fk_tiempo(fecha_str)
        
        mes = pago_data.pop("mes_correspondiente")
        anio = pago_data.pop("anio_correspondiente")
        idx_mes = MESES.index(mes) + 1
        pago_data["fk_tiempo_periodo"] = int(f"{anio}{idx_mes:02d}01")
        
        get_supabase().table("fact_pagos").insert(pago_data).execute()
        return True
    except Exception as e:
        logger.error(f"Error al guardar pago: {e}")
        st.error("No se pudo registrar el pago. Verifica los datos e intenta de nuevo.")
        return False

def actualizar_pago(id: str, datos: dict) -> bool:
    try:
        from utils import MESES
        datos = datos.copy()
        if "fecha_pago" in datos:
            datos["fk_tiempo_pago"] = _fecha_to_fk_tiempo(datos.pop("fecha_pago"))
            
        if "mes_correspondiente" in datos and "anio_correspondiente" in datos:
            mes = datos.pop("mes_correspondiente")
            anio = datos.pop("anio_correspondiente")
            idx_mes = MESES.index(mes) + 1
            datos["fk_tiempo_periodo"] = int(f"{anio}{idx_mes:02d}01")
            
        datos["actualizado_por"] = st.session_state.user.get("id")
            
        res = get_supabase().table("fact_pagos").update(datos).eq("id", id).execute()
        if not res.data:
            st.error("No se pudo actualizar el pago.", icon=":material/error:")
            return False
        return True
    except Exception as e:
        logger.error(f"Error al actualizar pago: {e}")
        st.error("No se pudo actualizar el pago. Intenta de nuevo.")
        return False

def eliminar_pago(id: str) -> bool:
    try:
        res = get_supabase().table("fact_pagos").delete().eq("id", id).execute()
        if not res.data:
            st.error("No se pudo eliminar el pago.", icon=":material/error:")
            return False
        return True
    except Exception as e:
        logger.error(f"Error al eliminar pago: {e}")
        st.error("No se pudo eliminar el pago. Intenta de nuevo.")
        return False

@user_cached(ttl=60)
def obtener_pagos(mes: Optional[str] = None, anio: Optional[str] = None) -> list:
    try:
        from utils import MESES
        query = get_supabase().table("fact_pagos").select(
            "*, dim_jugador(nombre, rut, dim_categoria(nombre)), "
            "tpago:dim_tiempo!fact_pagos_fk_tiempo_pago_fkey(fecha), "
            "tperiodo:dim_tiempo!fact_pagos_fk_tiempo_periodo_fkey(mes, anio)"
        )
        
        if mes and anio:
            idx_mes = MESES.index(mes) + 1
            fk_tiempo_periodo = int(f"{anio}{idx_mes:02d}01")
            query = query.eq("fk_tiempo_periodo", fk_tiempo_periodo)
            
        res = query.order("fk_tiempo_pago", desc=True).execute()
        pagos_procesados = []
        if res.data:
            for p in res.data:
                jug = p.get("dim_jugador") or {}
                cat = jug.get("dim_categoria") or {}
                t_pago = p.get("tpago") or {}
                t_per = p.get("tperiodo") or {}
                
                p_out = p.copy()
                p_out["jugador_nombre"] = jug.get("nombre", "Desconocido")
                p_out["jugador_rut"] = jug.get("rut", "Desconocido")
                p_out["categoria"] = cat.get("nombre", "Sin Categoría")
                
                p_out["fecha_pago"] = t_pago.get("fecha", "1900-01-01")
                if t_per:
                    p_out["mes_correspondiente"] = MESES[t_per.get("mes", 1) - 1]
                    p_out["anio_correspondiente"] = t_per.get("anio", 1900)
                else:
                    p_out["mes_correspondiente"] = "Desconocido"
                    p_out["anio_correspondiente"] = 0
                
                p_out.pop("dim_jugador", None)
                p_out.pop("tpago", None)
                p_out.pop("tperiodo", None)
                pagos_procesados.append(p_out)
        return pagos_procesados
    except Exception as e:
        logger.error(f"Error al obtener pagos: {e}")
        st.error("No se pudieron cargar los pagos. Intenta recargar la página.")
        return []

@user_cached(ttl=60)
def obtener_estado_pagos_mes(mes: int, anio: int) -> list:
    """Retorna todos los jugadores activos con el monto total pagado en el mes/año indicado.

    Permite al llamador determinar:
      - Sin pago:      total_pagado == 0
      - Abono parcial: 0 < total_pagado < monto_mensualidad
      - Al día:        total_pagado >= monto_mensualidad

    Args:
        mes:  Número de mes (1-12)
        anio: Año (ej: 2026)
    Returns:
        Lista de dicts ordenada por categoría, cada uno con:
        jugador_id, jugador_nombre, jugador_rut, categoria,
        apoderado_nombre, apoderado_telefono, apoderado_rut, total_pagado.
    """
    try:
        # 1. Pagos del mes: jugador_id → suma de montos abonados
        fk_tiempo_periodo = int(f"{anio}{mes:02d}01")
        res_pagos = (
            get_supabase()
            .table("fact_pagos")
            .select("jugador_id, monto")
            .eq("fk_tiempo_periodo", fk_tiempo_periodo)
            .execute()
        )
        pagos_por_jugador: dict = {}
        for p in (res_pagos.data or []):
            jid = p["jugador_id"]
            pagos_por_jugador[jid] = pagos_por_jugador.get(jid, 0.0) + float(p["monto"])

        # 2. Todos los jugadores activos con datos de apoderado y categoría
        res_jug = (
            get_supabase()
            .table("dim_jugador")
            .select(
                "id, nombre, rut, categoria_id, "
                "dim_apoderado(nombre, telefono, rut), "
                "dim_categoria(nombre)"
            )
            .eq("estado", "Activo")
            .execute()
        )

        resultado = []
        for j in (res_jug.data or []):
            if not j.get("categoria_id"):
                continue
            apo = j.get("dim_apoderado") or {}
            cat = j.get("dim_categoria") or {}
            resultado.append({
                "jugador_id":         j["id"],
                "jugador_nombre":     j.get("nombre", ""),
                "jugador_rut":        j.get("rut", ""),
                "categoria":          cat.get("nombre", "Sin Categoría"),
                "apoderado_nombre":   apo.get("nombre", "Sin apoderado"),
                "apoderado_telefono": apo.get("telefono", ""),
                "apoderado_rut":      apo.get("rut", ""),
                "total_pagado":       pagos_por_jugador.get(j["id"], 0.0),
            })

        return sorted(resultado, key=lambda x: x["categoria"])
    except Exception as e:
        logger.error(f"Error al obtener estado de pagos del mes: {e}")
        st.error("No se pudo cargar el estado de pagos. Intenta recargar la pagina.")
        return []

# =============================================================================
# AUTENTICACIÓN SUPABASE (OAuth / Email)
# =============================================================================


def autenticar_usuario(email: str, password: str) -> Optional[dict]:
    """Inicia sesión usando Supabase Auth y recupera los datos de dim_usuario.
    
    Retorna un dict con los datos del usuario si las credenciales son correctas,
    o None si falla. NO muestra mensajes de error en UI — eso le corresponde al
    llamador (pages/login.py).
    """
    try:
        res = get_supabase().auth.sign_in_with_password({"email": email, "password": password})
        if res.session:
            st.session_state["access_token"] = res.session.access_token
            st.session_state["refresh_token"] = res.session.refresh_token

            user_res = get_supabase().table("dim_usuario").select("*").eq("id", res.user.id).execute()
            if user_res.data and len(user_res.data) > 0:
                usuario = user_res.data[0]
                return {
                    "id": res.user.id,
                    "email": email,
                    "rol": usuario["rol"],
                    "nombre": usuario["nombre"],
                    "permisos": usuario.get("permisos") or [],
                    "apoderado_id": usuario.get("apoderado_id")
                }
            else:
                # Usuario existe en Auth pero no en dim_usuario — error de configuración
                logger.error(f"Usuario {email} autenticado en Supabase Auth pero sin registro en dim_usuario.")
                return None
    except Exception as e:
        # Credenciales incorrectas o error de red — log sin mostrar UI
        logger.warning(f"Intento de autenticación fallido para {email}: {type(e).__name__}")
    return None


def _get_admin_client() -> Client:
    """Retorna un cliente limpio con el Service Role Key, sin sesión de usuario para tareas administrativas."""
    if not SUPABASE_SERVICE_KEY:
        st.error("Error crítico: SUPABASE_SERVICE_KEY no configurada. Las tareas de administración fallarán.")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

@user_cached(ttl=60)
def obtener_usuarios() -> list:
    try:
        # Esto requiere permisos de Administrador vía RLS
        response = get_supabase().table("dim_usuario").select("id, nombre, telefono, rol, permisos").order("nombre").execute()
        usuarios = response.data if response.data else []
        
        # Obtener los correos desde auth.users (requiere admin_client)
        try:
            admin = _get_admin_client()
            auth_users = admin.auth.admin.list_users()
            email_map = {u.id: u.email for u in auth_users}
            for u in usuarios:
                u["correo"] = email_map.get(u["id"], "Sin correo")
        except Exception as e_auth:
            logger.warning(f"No se pudieron cargar los correos: {e_auth}")
            for u in usuarios:
                u["correo"] = "Desconocido"
                
        return usuarios
    except Exception as e:
        logger.error(f"Error al obtener usuarios: {e}")
        st.error("No se pudieron cargar los usuarios. Intenta recargar la página.")
        return []

# Para crear usuarios desde la app, usaremos el admin api
# Requiere SUPABASE_SERVICE_KEY
def crear_usuario(datos: dict) -> bool:
    try:
        email = datos.pop("username") # En la interfaz antigua era username, ahora será email
        password = datos.pop("password")
        
        # 1. Crear en auth.users usando el cliente administrador (que mantiene los privilegios)
        admin_client = _get_admin_client()
        new_user = admin_client.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True
        })
        
        if new_user.user:
            try:
                # 2. Actualizar en dim_usuario (la base de datos tiene un trigger que ya inserta el id inicial)
                datos_guardado = datos.copy()
                res = get_supabase().table("dim_usuario").update(datos_guardado).eq("id", new_user.user.id).execute()
                
                if not res.data:
                    raise Exception("No se pudo confirmar la actualización en la base de datos.")
                    
                return True
            except Exception as e_update:
                # ROLLBACK: Si la actualización falla, eliminamos la cuenta recién creada
                logger.error(f"Error actualizando usuario, haciendo rollback: {e_update}")
                admin_client.auth.admin.delete_user(new_user.user.id)
                raise Exception(f"Error al guardar los datos del profesor: {e_update}")
                
        return False
    except Exception as e:
        logger.error(f"Error al crear usuario: {e}")
        st.error("No se pudo crear la cuenta. Revisa los registros del sistema para más detalles.", icon=":material/error:")
        return False

def actualizar_usuario(user_id: str, datos: dict) -> bool:
    try:
        # Si incluye password, actualizar en auth.users
        if "password" in datos and datos["password"]:
            password = datos.pop("password")
            _get_admin_client().auth.admin.update_user_by_id(user_id, {"password": password})
        else:
            datos.pop("password", None)
            
        datos.pop("username", None) # Ignorar email por ahora en actualizaciones
            
        res = get_supabase().table("dim_usuario").update(datos).eq("id", user_id).execute()
        if not res.data:
            st.error("No se pudo actualizar el usuario.", icon=":material/error:")
            return False
        return True
    except Exception as e:
        logger.error(f"Error al actualizar usuario: {e}")
        st.error("No se pudo actualizar el usuario. Intenta de nuevo.")
        return False

def eliminar_usuario(user_id: str) -> bool:
    try:
        # Al eliminar de auth.users, el ON DELETE CASCADE elimina de dim_usuario
        res = _get_admin_client().auth.admin.delete_user(user_id)
        return True
    except Exception as e:
        logger.error(f"Error al eliminar usuario: {e}")
        st.error("No se pudo eliminar el usuario. Intenta de nuevo.")
        return False


def purgar_comprobantes_antiguos(meses: int) -> int:
    """Elimina archivos físicos de comprobantes antiguos y marca la URL como PURGADA."""
    from datetime import datetime
    from dateutil.relativedelta import relativedelta
    import urllib.parse
    
    fecha_limite = (datetime.now() - relativedelta(months=meses)).strftime("%Y-%m-%d")
    
    try:
        res = get_supabase().table("fact_pagos").select("id_pago, comprobante_url").lt("fecha_pago", fecha_limite).neq("comprobante_url", "").neq("comprobante_url", "PURGADO").execute()
        pagos = [p for p in res.data if p.get("comprobante_url") and p.get("comprobante_url") != "PURGADO"]
        if not pagos:
            return 0
            
        archivos, ids = [], []
        for pago in pagos:
            url = pago["comprobante_url"]
            if "/comprobantes/" in url:
                archivos.append(urllib.parse.unquote(url.split("/comprobantes/")[-1]))
            ids.append(pago["id_pago"])
            
        if archivos:
            get_supabase().storage.from_("comprobantes").remove(archivos)
            
        for id_pago in ids:
            get_supabase().table("fact_pagos").update({"comprobante_url": "PURGADO"}).eq("id_pago", id_pago).execute()
            
        return len(ids)
    except Exception as e:
        logger.error(f"Error al purgar comprobantes: {e}")
        return 0

def destruir_datos_apoderado(apoderado_id: str) -> bool:
    """Aplica el Derecho al Olvido (Anonimización destructiva) para un apoderado."""
    try:
        admin = _get_admin_client()
        # 1. Eliminar al usuario de auth.users si existe (esto borra dim_usuario en cascada)
        res_usr = admin.table("dim_usuario").select("id").eq("apoderado_id", apoderado_id).execute()
        for usr in (res_usr.data or []):
            try:
                admin.auth.admin.delete_user(usr["id"])
            except Exception:
                pass
        
        # 2. Borrar comprobantes físicos asociados al apoderado
        res_comp = admin.table("fact_comprobantes_pendientes").select("imagen_path").eq("apoderado_id", apoderado_id).execute()
        paths_to_delete = [c["imagen_path"] for c in (res_comp.data or []) if c.get("imagen_path")]
        if paths_to_delete:
            try:
                admin.storage.from_("comprobantes").remove(paths_to_delete)
            except Exception as e:
                logger.error(f"Error borrando imágenes de comprobantes: {e}")
        
        admin.table("fact_comprobantes_pendientes").delete().eq("apoderado_id", apoderado_id).execute()

        # 2.5 Buscar a todos sus jugadores y destruirlos también
        res_jug = admin.table("dim_jugador").select("id").eq("apoderado_id", apoderado_id).execute()
        for jug in (res_jug.data or []):
            destruir_datos_jugador(jug["id"])

        # 3. Anonimizar el registro en dim_apoderado
        import uuid
        fake_rut = f"BORRADO-{uuid.uuid4().hex[:8]}"
        admin.table("dim_apoderado").update({
            "nombre": "Apoderado Eliminado",
            "rut": fake_rut,
            "telefono": None,
            "correo": None,
            "telefono_emergencia": None,
            "token_registro": None,
            "token_expira": None,
            "usuario_id": None
        }).eq("id", apoderado_id).execute()

        return True
    except Exception as e:
        logger.error(f"Error al destruir datos de apoderado: {e}")
        return False

def destruir_datos_jugador(jugador_id: str) -> bool:
    """Aplica el Derecho al Olvido (Anonimización destructiva) para un jugador."""
    try:
        admin = _get_admin_client()
        
        # Eliminar comprobantes pendientes asociados a este jugador
        res_comp = admin.table("fact_comprobantes_pendientes").select("imagen_path").eq("jugador_id", jugador_id).execute()
        paths_to_delete = [c["imagen_path"] for c in (res_comp.data or []) if c.get("imagen_path")]
        if paths_to_delete:
            try:
                admin.storage.from_("comprobantes").remove(paths_to_delete)
            except Exception as e:
                pass
        admin.table("fact_comprobantes_pendientes").delete().eq("jugador_id", jugador_id).execute()

        import uuid
        fake_rut = f"BORRADO-{uuid.uuid4().hex[:8]}"
        admin.table("dim_jugador").update({
            "nombre": "Jugador Eliminado",
            "rut": fake_rut,
            "fecha_nacimiento": None,
            "estado": "Inactivo"
        }).eq("id", jugador_id).execute()
        return True
    except Exception as e:
        logger.error(f"Error al destruir datos de jugador: {e}")
        return False

def restablecer_contrasena_admin(apoderado_id: str, nueva_clave: str) -> bool:
    """Permite a un administrador forzar el cambio de contraseña de un apoderado."""
    try:
        # 1. Obtener el auth.user.id vinculado a este apoderado
        res = get_supabase().table("dim_usuario").select("id").eq("apoderado_id", apoderado_id).execute()
        if not res.data:
            return False
        
        user_id = res.data[0]["id"]
        
        # 2. Forzar actualización de clave con admin_client
        _get_admin_client().auth.admin.update_user_by_id(user_id, {"password": nueva_clave})
        return True
    except Exception as e:
        logger.error(f"Error al forzar restablecimiento de clave: {e}")
        return False

# =============================================================================
# PORTAL DEL APODERADO — CAPA DE DATOS
# =============================================================================

import uuid as _uuid
import urllib.parse as _urllib_parse
from datetime import timedelta


def generar_token_registro(apoderado_id: str) -> Optional[str]:
    """Genera un token UUID único para el apoderado y lo guarda en dim_apoderado.
    El token expira en 7 días. Retorna el token o None si falla."""
    try:
        token = str(_uuid.uuid4())
        expira = datetime.utcnow() + timedelta(days=7)
        get_supabase().table("dim_apoderado").update({
            "token_registro": token,
            "token_expira": expira.isoformat()
        }).eq("id", apoderado_id).execute()
        return token
    except Exception as e:
        logger.error(f"Error al generar token de registro: {e}")
        return None


def construir_link_wsp(telefono: str, token: str, nombre_apoderado: str,
                       nombre_jugador: str, app_url: str, plantilla_msj: str = None) -> str:
    """Construye un enlace wa.me con mensaje pre-escrito en español (Chile).

    Args:
        telefono: Número del apoderado. Se normaliza a formato internacional (56XXXXXXXXX).
        token: Token único de registro.
        nombre_apoderado: Nombre del apoderado para personalizar el mensaje.
        nombre_jugador: Nombre del hijo/jugador.
        app_url: URL base de la app (ej: https://tuapp.streamlit.app).
        plantilla_msj: Plantilla opcional. Si no se pasa, se usa una por defecto.

    Returns:
        URL wa.me lista para abrir en navegador.
    """
    # Normalizar teléfono: quitar +, espacios, guiones; agregar 56 si falta
    tel = telefono.strip().replace(" ", "").replace("-", "").replace("+", "")
    if tel.startswith("56") and len(tel) >= 11:
        pass  # Ya tiene código de país
    elif tel.startswith("9") and len(tel) == 9:
        tel = "56" + tel
    elif tel.startswith("0"):
        tel = "56" + tel[1:]
    else:
        tel = "56" + tel  # Asumir Chile

    link_registro = f"{app_url.rstrip('/')}/?token={token}"
    
    if plantilla_msj:
        mensaje = plantilla_msj.format(
            nombre_apoderado=nombre_apoderado,
            nombre_jugador=nombre_jugador,
            link_registro=link_registro
        )
    else:
        mensaje = (
        f"Hola {nombre_apoderado} 👋, te invitamos al *Portal Academia La Serena*.\n\n"
        f"Desde aquí podrás ver los pagos y asistencia de *{nombre_jugador}*.\n\n"
        f"🔗 Accede aquí:\n{link_registro}\n\n"
        f"⏰ Este link vence en *7 días*.\n"
        f"_Si tienes problemas, contacta al administrador._"
    )
    encoded = _urllib_parse.quote(mensaje)
    return f"https://wa.me/{tel}?text={encoded}"


def validar_token_apoderado(token: str) -> Optional[dict]:
    """Verifica que el token sea válido y no haya expirado.
    Retorna el dict del apoderado o None."""
    try:
        res = get_supabase().table("dim_apoderado").select("*").eq("token_registro", token).execute()
        if not res.data:
            return None
        apoderado = res.data[0]
        # Verificar expiración
        if apoderado.get("token_expira"):
            expira = datetime.fromisoformat(apoderado["token_expira"].replace("Z", "+00:00"))
            from datetime import timezone
            if datetime.now(timezone.utc) > expira:
                return None  # Token expirado
        # Verificar que no tenga ya una cuenta creada
        if apoderado.get("usuario_id"):
            return None  # Ya tiene cuenta
        return apoderado
    except Exception as e:
        logger.error(f"Error al validar token: {e}")
        return None


def crear_cuenta_apoderado(apoderado_id: str, email: str, password: str, nombre: str) -> bool:
    """Crea una cuenta Supabase Auth para el apoderado y la vincula en dim_usuario.

    Usa la Service Role Key (admin) para crear el usuario.
    Retorna True si se creó correctamente.
    """
    try:
        admin_client = _get_admin_client()
        new_user = admin_client.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"nombre": nombre, "rol": "Apoderado"}
        })

        if not new_user.user:
            return False

        user_id = new_user.user.id
        # Actualizar dim_usuario: el trigger ya crea la fila, solo actualizamos
        get_supabase().table("dim_usuario").update({
            "rol": "Apoderado",
            "nombre": nombre,
            "apoderado_id": apoderado_id
        }).eq("id", user_id).execute()

        # Marcar el apoderado como vinculado y limpiar el token
        get_supabase().table("dim_apoderado").update({
            "usuario_id": user_id,
            "token_registro": None,
            "token_expira": None
        }).eq("id", apoderado_id).execute()

        return True
    except Exception as e:
        logger.error(f"Error al crear cuenta de apoderado: {e}")
        return False


@user_cached(ttl=60)
def obtener_apoderados_con_estado() -> list:
    """Retorna todos los apoderados con su estado de cuenta: activa / pendiente / sin cuenta."""
    try:
        res = get_supabase().table("dim_apoderado").select(
            "id, nombre, telefono, correo, rut, token_registro, token_expira, usuario_id, dim_usuario(id)"
        ).order("nombre").execute()
        apoderados = res.data or []
        from datetime import timezone
        ahora = datetime.now(timezone.utc)
        for a in apoderados:
            tiene_usuario = a.get("usuario_id") or (a.get("dim_usuario") and len(a["dim_usuario"]) > 0)
            if tiene_usuario:
                a["estado_cuenta"] = "activa"
            elif a.get("token_registro") and a.get("token_expira"):
                expira = datetime.fromisoformat(a["token_expira"].replace("Z", "+00:00"))
                a["estado_cuenta"] = "pendiente" if ahora < expira else "expirada"
            else:
                a["estado_cuenta"] = "sin_cuenta"
        return apoderados
    except Exception as e:
        logger.error(f"Error al obtener apoderados con estado: {e}")
        return []


@user_cached(ttl=60)
def obtener_jugadores_de_apoderado(apoderado_id: str) -> list:
    """Retorna los jugadores vinculados a un apoderado con info de categoría."""
    try:
        res = get_supabase().table("dim_jugador").select(
            "id, nombre, rut, fecha_nacimiento, estado, dim_categoria(id, nombre, dim_usuario(nombre))"
        ).eq("apoderado_id", apoderado_id).eq("estado", "Activo").execute()
        jugadores = []
        for j in (res.data or []):
            cat = j.pop("dim_categoria", None) or {}
            prof = cat.pop("dim_usuario", None) or {}
            j["categoria_id"] = cat.get("id", "")
            j["categoria_nombre"] = cat.get("nombre", "Sin Categoría")
            j["profesor_nombre"] = prof.get("nombre", "Sin Profesor")
            jugadores.append(j)
        return jugadores
    except Exception as e:
        logger.error(f"Error al obtener jugadores del apoderado: {e}")
        return []


@user_cached(ttl=60)
def obtener_asistencia_jugador_apoderado(jugador_id: str) -> list:
    """Retorna el historial de asistencia de un jugador para el portal del apoderado."""
    try:
        res = get_supabase().table("fact_asistencia").select(
            "estado, dim_tiempo(fecha)"
        ).eq("jugador_id", jugador_id).order("fk_tiempo", desc=True).limit(60).execute()
        resultado = []
        for row in (res.data or []):
            t = row.get("dim_tiempo") or {}
            resultado.append({
                "fecha": t.get("fecha", ""),
                "estado": row.get("estado", "")
            })
        return resultado
    except Exception as e:
        logger.error(f"Error al obtener asistencia del jugador: {e}")
        return []


@user_cached(ttl=60)
def obtener_pagos_apoderado(apoderado_id: str) -> list:
    """Retorna el historial de pagos aprobados del apoderado (de fact_pagos)."""
    try:
        from utils import MESES
        res = get_supabase().table("fact_pagos").select(
            "id, monto, metodo_pago, jugador_id, "
            "tpago:dim_tiempo!fact_pagos_fk_tiempo_pago_fkey(fecha), "
            "tperiodo:dim_tiempo!fact_pagos_fk_tiempo_periodo_fkey(mes, anio), "
            "dim_jugador(nombre)"
        ).eq("apoderado_id", apoderado_id).order("fk_tiempo_pago", desc=True).execute()

        pagos = []
        for p in (res.data or []):
            t_pago = p.get("tpago") or {}
            t_per = p.get("tperiodo") or {}
            jug = p.get("dim_jugador") or {}
            pagos.append({
                "id": p["id"],
                "jugador_nombre": jug.get("nombre", ""),
                "jugador_id": p.get("jugador_id"),
                "fecha_pago": t_pago.get("fecha", ""),
                "mes_nombre": MESES[t_per.get("mes", 1) - 1] if t_per else "",
                "anio": t_per.get("anio", 0),
                "monto": p.get("monto", 0),
                "metodo_pago": p.get("metodo_pago", ""),
            })
        return pagos
    except Exception as e:
        logger.error(f"Error al obtener pagos del apoderado: {e}")
        return []


@user_cached(ttl=60)
def obtener_comprobantes_apoderado(apoderado_id: str) -> list:
    """Retorna los comprobantes enviados por el apoderado."""
    try:
        res = get_supabase().table("fact_comprobantes_pendientes").select(
            "*, dim_jugador(nombre)"
        ).eq("apoderado_id", apoderado_id).order("creado_en", desc=True).execute()
        result = []
        for r in (res.data or []):
            jug = r.pop("dim_jugador", None) or {}
            r["jugador_nombre"] = jug.get("nombre", "")
            result.append(r)
        return result
    except Exception as e:
        logger.error(f"Error al obtener comprobantes del apoderado: {e}")
        return []


def subir_comprobante_imagen(archivo_bytes: bytes, nombre_archivo: str, apoderado_id: str) -> Optional[str]:
    """Sube la imagen del comprobante a Supabase Storage y retorna la URL pública firmada."""
    try:
        import mimetypes
        ext = nombre_archivo.rsplit(".", 1)[-1].lower() if "." in nombre_archivo else "jpg"
        path = f"{apoderado_id}/{_uuid.uuid4()}.{ext}"
        content_type = mimetypes.guess_type(nombre_archivo)[0] or "image/jpeg"
        get_supabase().storage.from_("comprobantes").upload(
            path=path,
            file=archivo_bytes,
            file_options={"content-type": content_type}
        )
        # URL firmada válida por 1 año
        signed = get_supabase().storage.from_("comprobantes").create_signed_url(path, 31536000)
        return signed.get("signedURL") or signed.get("signed_url"), path
    except Exception as e:
        logger.error(f"Error al subir comprobante: {e}")
        return None, None


def guardar_comprobante_pendiente(datos: dict) -> bool:
    """Inserta o actualiza un comprobante pendiente.
    Si ya existe uno rechazado para el mismo apoderado/jugador/mes/año, lo reemplaza."""
    try:
        # Usamos un cliente limpio (service_role) para saltar el RLS,
        # ya que el Apoderado no tiene permisos de DELETE en la política de base de datos.
        from supabase import create_client
        admin_client = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Eliminar rechazados anteriores para permitir re-envío
        admin_client.table("fact_comprobantes_pendientes").delete()\
            .eq("apoderado_id", datos["apoderado_id"])\
            .eq("jugador_id", datos["jugador_id"])\
            .eq("mes", datos["mes"])\
            .eq("anio", datos["anio"])\
            .eq("estado", "rechazado").execute()

        get_supabase().table("fact_comprobantes_pendientes").insert(datos).execute()
        return True
    except Exception as e:
        logger.error(f"Error al guardar comprobante: {e}")
        return False


@user_cached(ttl=30)
def obtener_comprobantes_pendientes_admin() -> list:
    """Para el admin: retorna todos los comprobantes en estado 'pendiente'."""
    try:
        res = get_supabase().table("fact_comprobantes_pendientes").select(
            "*, dim_apoderado(nombre, telefono), dim_jugador(nombre, rut)"
        ).eq("estado", "pendiente").order("creado_en").execute()
        result = []
        for r in (res.data or []):
            apo = r.pop("dim_apoderado", None) or {}
            jug = r.pop("dim_jugador", None) or {}
            r["apoderado_nombre"] = apo.get("nombre", "")
            r["apoderado_telefono"] = apo.get("telefono", "")
            r["jugador_nombre"] = jug.get("nombre", "")
            r["jugador_rut"] = jug.get("rut", "")
            result.append(r)
        return result
    except Exception as e:
        logger.error(f"Error al obtener comprobantes pendientes: {e}")
        return []


def aprobar_comprobante(comprobante_id: str, datos_pago: dict) -> bool:
    """Aprueba un comprobante: crea el pago en fact_pagos y actualiza el estado."""
    try:
        # 1. Guardar el pago real
        ok = guardar_pago(datos_pago)
        if not ok:
            return False
        # 2. Marcar el comprobante como aprobado
        user_id = st.session_state.user.get("id")
        get_supabase().table("fact_comprobantes_pendientes").update({
            "estado": "aprobado",
            "revisado_por": user_id,
            "revisado_en": datetime.utcnow().isoformat()
        }).eq("id", comprobante_id).execute()
        # Limpiar caché
        obtener_comprobantes_pendientes_admin.clear()
        return True
    except Exception as e:
        logger.error(f"Error al aprobar comprobante: {e}")
        st.error("No se pudo aprobar el comprobante. Intenta de nuevo.")
        return False


def rechazar_comprobante(comprobante_id: str, motivo: str) -> bool:
    """Rechaza un comprobante de pago."""
    try:
        user_id = st.session_state.user.get("id")
        get_supabase().table("fact_comprobantes_pendientes").update({
            "estado": "rechazado",
            "motivo_rechazo": motivo,
            "revisado_por": user_id,
            "revisado_en": datetime.utcnow().isoformat()
        }).eq("id", comprobante_id).execute()
        obtener_comprobantes_pendientes_admin.clear()
        return True
    except Exception as e:
        logger.error(f"Error al rechazar comprobante: {e}")
        st.error("No se pudo rechazar el comprobante. Intenta de nuevo.")
        return False
    """Borra físicamente las imágenes de comprobantes antiguos aprobados/rechazados para cumplimiento legal (ARCOP)."""
    try:
        from datetime import datetime, timedelta
        fecha_limite = datetime.utcnow() - timedelta(days=30 * meses)
        fecha_str = fecha_limite.isoformat()
        
        admin_client = _get_admin_client()
        res = admin_client.table("fact_comprobantes_pendientes")\
            .select("id, imagen_url")\
            .in_("estado", ["aprobado", "rechazado"])\
            .lt("creado_en", fecha_str)\
            .execute()
            
        comprobantes = res.data
        if not comprobantes:
            return 0
            
        paths_a_borrar = []
        ids_a_actualizar = []
        
        for c in comprobantes:
            url = c.get("imagen_url")
            if not url: continue
            
            if "/comprobantes/" in url:
                path = url.split("/comprobantes/")[-1]
            else:
                path = url
                
            paths_a_borrar.append(path)
            ids_a_actualizar.append(c["id"])
            
        if paths_a_borrar:
            admin_client.storage.from_("comprobantes").remove(paths_a_borrar)
            
            for c_id in ids_a_actualizar:
                admin_client.table("fact_comprobantes_pendientes").update({
                    "imagen_url": None
                }).eq("id", c_id).execute()
                
        return len(paths_a_borrar)
    except Exception as e:
        logger.error(f"Error al purgar comprobantes: {e}")
        return 0
