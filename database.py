from datetime import date, datetime
from typing import Optional
import logging

import streamlit as st
from supabase import create_client, Client

logger = logging.getLogger(__name__)

def _normalizar_url_supabase(url_bruta: str) -> str:
    url = (url_bruta or "").strip().strip('"').strip("'")
    if url and not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    for sufijo in ("/rest/v1/", "/rest/v1", "/auth/v1/", "/auth/v1"):
        if url.endswith(sufijo):
            url = url[: -len(sufijo)]
    return url.rstrip("/")

SUPABASE_URL = _normalizar_url_supabase(st.secrets["SUPABASE_URL"])
# Usar SERVICE_ROLE_KEY si está disponible para tareas de admin, de lo contrario la anónima
SUPABASE_KEY = st.secrets.get("SUPABASE_SERVICE_KEY", st.secrets["SUPABASE_KEY"]).strip().strip('"').strip("'")

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

@st.cache_data(ttl=60)
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

@st.cache_data(ttl=60)
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

@st.cache_data(ttl=60)
def obtener_profesores() -> list:
    try:
        res = get_supabase().table("dim_usuario").select("*").eq("rol", "Profesor").order("nombre").execute()
        return res.data if res.data else []
    except Exception as e:
        logger.error(f"Error al cargar lista de profesores: {e}")
        return []

# =============================================================================
# CAPA DE DATOS - ASISTENCIA (fact_asistencia)
# =============================================================================

@st.cache_data(ttl=30)
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

@st.cache_data(ttl=60)
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

@st.cache_data(ttl=60)
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
                    "permisos": usuario.get("permisos") or []
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
    return create_client(SUPABASE_URL, SUPABASE_KEY)

@st.cache_data(ttl=60)
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
        st.error(f"No se pudo crear la cuenta: {e}", icon=":material/error:")
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
