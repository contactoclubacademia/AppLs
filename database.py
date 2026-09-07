from datetime import date, datetime
from typing import Optional
import hashlib
import secrets
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
SUPABASE_KEY = st.secrets["SUPABASE_KEY"].strip().strip('"').strip("'")

@st.cache_resource
def get_supabase() -> Client:
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        logger.error(f"No se pudo inicializar Supabase: {e}")
        st.error("No se pudo conectar con el servidor. Contacta al administrador.")
        st.stop()


# =============================================================================
# CAPA DE DATOS - JUGADORES (UUID)
# =============================================================================

def guardar_jugador(jugador: dict) -> bool:
    try:
        get_supabase().table("jugadores").insert(jugador).execute()
        return True
    except Exception as e:
        logger.error(f"Error al guardar jugador: {e}")
        st.error("No se pudo guardar el jugador. Verifica los datos e intenta de nuevo.")
        return False

def actualizar_jugador(id: str, datos: dict) -> bool:
    try:
        res = get_supabase().table("jugadores").update(datos).eq("id", id).execute()
        if not res.data:
            st.error("❌ No se pudo actualizar (0 filas afectadas).")
            return False
        return True
    except Exception as e:
        logger.error(f"Error al actualizar jugador: {e}")
        st.error("No se pudo actualizar el jugador. Intenta de nuevo.")
        return False

def eliminar_jugador(id: str) -> bool:
    try:
        res = get_supabase().table("jugadores").update({
            "estado": "Inactivo",
            "categoria_id": None
        }).eq("id", id).execute()
        if not res.data:
            st.error("❌ No se pudo dar de baja al jugador.")
            return False
        return True
    except Exception as e:
        logger.error(f"Error al dar de baja jugador: {e}")
        st.error("No se pudo dar de baja al jugador. Intenta de nuevo.")
        return False

def activar_jugador(id: str, categoria_id: str) -> bool:
    try:
        res = get_supabase().table("jugadores").update({
            "estado": "Activo",
            "categoria_id": categoria_id
        }).eq("id", id).execute()
        if not res.data:
            st.error("❌ No se pudo activar al jugador.")
            return False
        return True
    except Exception as e:
        logger.error(f"Error al activar jugador: {e}")
        st.error("No se pudo activar al jugador. Intenta de nuevo.")
        return False

@st.cache_data(ttl=60)
def obtener_jugadores(categoria_id: Optional[str] = None) -> list:
    try:
        query = get_supabase().table("jugadores").select("*, categorias(nombre)")
        if categoria_id:
            query = query.eq("categoria_id", categoria_id)
        response = query.execute()
        if response.data:
            jugadores = []
            for row in response.data:
                cat_obj = row.pop("categorias", None)
                row["categoria"] = cat_obj["nombre"] if cat_obj else None
                jugadores.append(row)
            return jugadores
        return []
    except Exception as e:
        logger.error(f"Error al obtener jugadores: {e}")
        st.error("No se pudieron cargar los jugadores. Intenta recargar la página.")
        return []

# =============================================================================
# CAPA DE DATOS - CATEGORÍAS (UUID)
# =============================================================================

@st.cache_data(ttl=60)
def obtener_categorias_config() -> list:
    try:
        response = get_supabase().table("categorias").select("*").order("nombre").execute()
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error al obtener categorías: {e}")
        st.error("No se pudieron cargar las categorías. Intenta recargar la página.")
        return []

def obtener_categorias() -> list:
    return obtener_categorias_config()

def crear_categoria(nombre: str, profesor: str = "") -> bool:
    nombre = nombre.strip()
    if not nombre:
        st.error("⚠️ El nombre de la categoría no puede estar vacío.")
        return False
    try:
        get_supabase().table("categorias").insert({"nombre": nombre, "profesor": profesor.strip()}).execute()
        return True
    except Exception as e:
        logger.error(f"Error al crear categoría: {e}")
        st.error("No se pudo crear la categoría. Es posible que ya exista.")
        return False

def desvincular_jugadores_categoria(id: str) -> bool:
    try:
        get_supabase().table("jugadores").update({"categoria_id": None}).eq("categoria_id", id).execute()
        return True
    except Exception as e:
        logger.error(f"Error al desvincular jugadores: {e}")
        st.error("No se pudieron desvincular los jugadores de la categoría.")
        return False

def eliminar_categoria(id: str) -> bool:
    try:
        res = get_supabase().table("categorias").delete().eq("id", id).execute()
        if not res.data:
            st.error("❌ No se pudo eliminar la categoría.")
            return False
        return True
    except Exception as e:
        logger.error(f"Error al eliminar categoría: {e}")
        st.error("No se pudo eliminar la categoría. Intenta de nuevo.")
        return False

def actualizar_profesor_categoria(id: str, profesor: str) -> bool:
    try:
        res = get_supabase().table("categorias").update({"profesor": profesor.strip()}).eq("id", id).execute()
        if not res.data:
            return False
        return True
    except Exception as e:
        logger.error(f"Error al actualizar profesor de categoría: {e}")
        st.error("No se pudo actualizar el profesor. Intenta de nuevo.")
        return False

def obtener_profesor_de(categoria_id: str) -> str:
    try:
        res = get_supabase().table("categorias").select("profesor").eq("id", categoria_id).execute()
        if res.data and len(res.data) > 0:
            return res.data[0].get("profesor", "Profesor no asignado")
        return "Profesor no asignado"
    except Exception as e:
        logger.error(f"Error al obtener profesor: {e}")
        return "Profesor no asignado"

# =============================================================================
# CAPA DE DATOS - ASISTENCIA (UUID)
# =============================================================================

def obtener_asistencia(fecha: date, categoria_id: str) -> list:
    try:
        res = get_supabase().table("asistencia").select("*").eq("fecha", str(fecha)).eq("categoria_id", categoria_id).execute()
        return res.data if res.data else []
    except Exception as e:
        logger.error(f"Error al obtener asistencia: {e}")
        st.error("No se pudo cargar la asistencia. Intenta de nuevo.")
        return []

def guardar_asistencia(fecha: date, categoria_id: str, registros: list) -> bool:
    if not registros:
        return True
    try:
        # Upsert atómico: si ya existe (fecha + jugador_id), actualiza. Si no, inserta.
        data_to_upsert = [
            {"fecha": str(fecha), "categoria_id": categoria_id, "jugador_id": reg["jugador_id"], "estado": reg["estado"]}
            for reg in registros
        ]
        get_supabase().table("asistencia").upsert(data_to_upsert).execute()
        return True
    except Exception as e:
        logger.error(f"Error al guardar asistencia: {e}")
        st.error("No se pudo guardar la asistencia. Intenta de nuevo.")
        return False

@st.cache_data(ttl=60)
def obtener_asistencia_general() -> list:
    try:
        res = get_supabase().table("asistencia").select("*, jugadores(nombre, rut, categorias(nombre))").execute()
        asistencias = []
        if res.data:
            for row in res.data:
                jug = row.get("jugadores") or {}
                cat = jug.get("categorias") or {}
                a_out = row.copy()
                a_out["jugador_nombre"] = jug.get("nombre", "Desconocido")
                a_out["jugador_rut"] = jug.get("rut", "Desconocido")
                a_out["categoria"] = cat.get("nombre", "Sin Categoría")
                a_out.pop("jugadores", None)
                asistencias.append(a_out)
        return asistencias
    except Exception as e:
        logger.error(f"Error al obtener historial de asistencia: {e}")
        st.error("No se pudo cargar el historial de asistencia. Intenta recargar la página.")
        return []

# =============================================================================
# CAPA DE DATOS - PAGOS (UUID)
# =============================================================================

def guardar_pago(pago_data: dict) -> bool:
    try:
        get_supabase().table("pagos").insert(pago_data).execute()
        return True
    except Exception as e:
        logger.error(f"Error al guardar pago: {e}")
        st.error("No se pudo registrar el pago. Verifica los datos e intenta de nuevo.")
        return False

def actualizar_pago(id: str, datos: dict) -> bool:
    try:
        res = get_supabase().table("pagos").update(datos).eq("id", id).execute()
        if not res.data:
            st.error("❌ No se pudo actualizar el pago.")
            return False
        return True
    except Exception as e:
        logger.error(f"Error al actualizar pago: {e}")
        st.error("No se pudo actualizar el pago. Intenta de nuevo.")
        return False

def eliminar_pago(id: str) -> bool:
    try:
        res = get_supabase().table("pagos").delete().eq("id", id).execute()
        if not res.data:
            st.error("❌ No se pudo eliminar el pago.")
            return False
        return True
    except Exception as e:
        logger.error(f"Error al eliminar pago: {e}")
        st.error("No se pudo eliminar el pago. Intenta de nuevo.")
        return False

@st.cache_data(ttl=60)
def obtener_pagos(mes: Optional[str] = None, anio: Optional[str] = None) -> list:
    try:
        query = get_supabase().table("pagos").select("*, jugadores(nombre, rut, categorias(nombre))")
        if mes:
            query = query.eq("mes_correspondiente", mes)
        if anio:
            query = query.gte("fecha_pago", f"{anio}-01-01").lte("fecha_pago", f"{anio}-12-31")
            
        res = query.order("fecha_pago", desc=True).execute()
        pagos_procesados = []
        if res.data:
            for p in res.data:
                jug = p.get("jugadores") or {}
                cat = jug.get("categorias") or {}
                p_out = p.copy()
                p_out["jugador_nombre"] = jug.get("nombre", "Desconocido")
                p_out["jugador_rut"] = jug.get("rut", "Desconocido")
                p_out["categoria"] = cat.get("nombre", "Sin Categoría")
                p_out.pop("jugadores", None)
                pagos_procesados.append(p_out)
        return pagos_procesados
    except Exception as e:
        logger.error(f"Error al obtener pagos: {e}")
        st.error("No se pudieron cargar los pagos. Intenta recargar la página.")
        return []

# =============================================================================
# AUTENTICACIÓN (Sin cambios)
# =============================================================================
def _hash_password(password: str, salt: str = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()
    return pw_hash, salt

def _verify_password(password: str, stored_hash: str, salt: str) -> bool:
    pw_hash, _ = _hash_password(password, salt)
    return pw_hash == stored_hash

def autenticar_usuario(username: str, password: str) -> Optional[dict]:
    try:
        response = get_supabase().table("usuarios").select("*").eq("username", username).execute()
        if response.data and len(response.data) > 0:
            usuario = response.data[0]
            stored_pw = usuario.get("password", "")
            salt = usuario.get("salt", "")
            if salt:
                password_ok = _verify_password(password, stored_pw, salt)
            else:
                # No permitir login sin hash — forzar reset de contraseña
                password_ok = False
            if password_ok:
                return {"username": usuario["username"], "rol": usuario["rol"], "nombre": usuario["nombre"], "permisos": usuario.get("permisos") or []}
    except Exception as e:
        logger.error(f"Error de autenticación: {e}")
        st.error("Error al verificar las credenciales. Intenta de nuevo.", icon=":material/error:")
    return None

@st.cache_data(ttl=60)
def obtener_usuarios() -> list:
    try:
        response = get_supabase().table("usuarios").select("username, nombre, telefono, rol, permisos").order("username").execute()
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error al obtener usuarios: {e}")
        st.error("No se pudieron cargar los usuarios. Intenta recargar la página.")
        return []

def crear_usuario(datos: dict) -> bool:
    try:
        pw_hash, salt = _hash_password(datos["password"])
        datos_guardado = datos.copy()
        datos_guardado["password"] = pw_hash
        datos_guardado["salt"] = salt
        get_supabase().table("usuarios").insert(datos_guardado).execute()
        return True
    except Exception as e:
        logger.error(f"Error al crear usuario: {e}")
        st.error("No se pudo crear la cuenta. Es posible que el nombre de usuario ya exista.", icon=":material/error:")
        return False

def actualizar_usuario(username: str, datos: dict) -> bool:
    try:
        datos_guardado = datos.copy()
        if "password" in datos_guardado:
            pw_hash, salt = _hash_password(datos_guardado["password"])
            datos_guardado["password"] = pw_hash
            datos_guardado["salt"] = salt
        res = get_supabase().table("usuarios").update(datos_guardado).eq("username", username).execute()
        if not res.data:
            st.error("❌ No se pudo actualizar el usuario.")
            return False
        return True
    except Exception as e:
        logger.error(f"Error al actualizar usuario: {e}")
        st.error("No se pudo actualizar el usuario. Intenta de nuevo.")
        return False

def eliminar_usuario(username: str) -> bool:
    try:
        res = get_supabase().table("usuarios").delete().eq("username", username).execute()
        if not res.data:
            st.error("❌ No se pudo eliminar el usuario.")
            return False
        return True
    except Exception as e:
        logger.error(f"Error al eliminar usuario: {e}")
        st.error("No se pudo eliminar el usuario. Intenta de nuevo.")
        return False
