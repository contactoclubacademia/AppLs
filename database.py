from datetime import date, datetime
from typing import Optional

import streamlit as st
from supabase import create_client, Client

# =============================================================================
# CONFIGURACIÓN Y CLIENTE DE SUPABASE
# =============================================================================


def _normalizar_url_supabase(url_bruta: str) -> str:
    """
    Limpia y normaliza la URL de Supabase leída desde secrets.toml para
    evitar errores de red como "[Errno 11001] getaddrinfo failed", que
    ocurren cuando el hostname que se intenta resolver viene "sucio":
    con espacios/saltos de línea invisibles, con el sufijo "/rest/v1"
    pegado por error (común al copiar la URL del panel de API en vez de
    la URL base del proyecto), con una barra final duplicada, o sin el
    esquema "https://" al inicio.

    Solo la URL BASE del proyecto (https://<project-ref>.supabase.co)
    debe pasarse a create_client(); la librería supabase-py agrega
    internamente "/rest/v1" cuando corresponde.
    """
    url = (url_bruta or "").strip()

    # Elimina comillas residuales por si el valor quedó mal citado en el TOML.
    url = url.strip('"').strip("'")

    # Si falta el esquema, lo agregamos (evita que getaddrinfo reciba un
    # string sin protocolo, que también dispara este mismo error).
    if url and not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    # Elimina rutas de API que a veces se copian por error junto con el
    # dominio (la librería las agrega sola cuando corresponde).
    for sufijo in ("/rest/v1/", "/rest/v1", "/auth/v1/", "/auth/v1"):
        if url.endswith(sufijo):
            url = url[: -len(sufijo)]

    # Elimina cualquier barra final sobrante para dejar solo el dominio base.
    url = url.rstrip("/")

    return url


SUPABASE_URL = _normalizar_url_supabase(st.secrets["SUPABASE_URL"])
SUPABASE_KEY = st.secrets["SUPABASE_KEY"].strip().strip('"').strip("'")

@st.cache_resource
def get_supabase() -> Client:
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.error(f"❌ No se pudo inicializar Supabase: {e}")
        st.stop()

# Credenciales de autenticación demo (exclusivas para el login; NO son datos
# de negocio y no interactúan con las tablas de Supabase). Migrar esto a
# Supabase Auth es una tarea independiente y fuera del alcance de este fix.
USUARIOS_DEMO = {
    "admin": {"password": "admin123", "rol": "Administrador", "nombre": "Administrador"},
    "profe": {"password": "profe123", "rol": "Profesor/Entrenador", "nombre": "Profesor"},
}


# =============================================================================
# CAPA DE DATOS - JUGADORES (100% Supabase)
# =============================================================================

def guardar_jugador(jugador: dict) -> bool:
    """
    Inserta un nuevo jugador en la tabla 'jugadores' de Supabase.
    """
    try:
        get_supabase().table("jugadores").insert(jugador).execute()
        return True
    except Exception as e:
        st.error(f"❌ Error de Supabase al guardar jugador: {e}")
        return False

def actualizar_jugador(rut: str, datos: dict) -> bool:
    """
    Actualiza los datos de un jugador existente en Supabase.
    """
    try:
        res = get_supabase().table("jugadores").update(datos).eq("rut", rut).execute()
        if not res.data:
            st.error("❌ No se pudo actualizar (0 filas afectadas).")
            return False
        return True
    except Exception as e:
        st.error(f"❌ Error al actualizar jugador: {e}")
        return False

def eliminar_jugador(rut: str) -> bool:
    """
    Elimina un jugador de Supabase por su RUT.
    """
    try:
        res = get_supabase().table("jugadores").delete().eq("rut", rut).execute()
        if not res.data:
            st.error("❌ No se pudo eliminar (0 filas afectadas).")
            return False
        return True
    except Exception as e:
        st.error(f"❌ Error al eliminar jugador: {e}")
        return False


def obtener_jugadores(categoria: Optional[str] = None) -> list:
    """
    Retorna la lista de jugadores desde Supabase, opcionalmente filtrados por categoría.
    """
    try:
        query = get_supabase().table("jugadores").select("*")
        if categoria:
            query = query.eq("categoria", categoria)
        response = query.execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"❌ Error de Supabase al obtener jugadores: {e}")
        return []


# =============================================================================
# CAPA DE DATOS - CATEGORÍAS (100% Supabase)
# =============================================================================

def obtener_categorias_config() -> list:
    """
    Retorna la configuración completa de categorías haciendo un select("*")
    directamente a la tabla 'categorias' en Supabase, ordenada por nombre.
    """
    try:
        response = get_supabase().table("categorias").select("*").order("nombre").execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"❌ Error de Supabase al obtener categorías: {e}")
        return []


def obtener_categorias() -> list:
    """
    Retorna solo los nombres de las categorías configuradas, consultando
    directamente la tabla 'categorias' en Supabase (a través de obtener_categorias_config).
    """
    categorias = obtener_categorias_config()
    return [c["nombre"] for c in categorias if "nombre" in c]


def crear_categoria(nombre: str, profesor: str = "") -> bool:
    """
    Crea una nueva categoría en la tabla 'categorias' de Supabase.

    Verifica primero (con un SELECT exacto) si el nombre ya existe para dar
    un mensaje claro de duplicado. Si el INSERT falla por cualquier OTRO motivo
    (por ejemplo, políticas de Row Level Security sin permiso de escritura,
    problemas de red, o violación real de la restricción única en la base de
    datos), se muestra el error EXACTO devuelto por Supabase — nunca un mensaje
    genérico de "ya existe" que oculte la causa real.
    """
    nombre = nombre.strip()
    if not nombre:
        st.error("⚠️ El nombre de la categoría no puede estar vacío.")
        return False

    try:
        existente = get_supabase().table("categorias").select("nombre").eq("nombre", nombre).execute()
    except Exception as e:
        st.error(f"❌ Error de Supabase al verificar duplicados: {e}")
        return False

    if existente.data and len(existente.data) > 0:
        st.error(f"⚠️ Ya existe una categoría llamada '{nombre}'.")
        return False

    try:
        get_supabase().table("categorias").insert({
            "nombre": nombre,
            "profesor": profesor.strip()
        }).execute()
        return True
    except Exception as e:
        error_msg = str(e)
        if "23505" in error_msg:
            # Violación real de la restricción UNIQUE en la base de datos
            # (carrera entre dos inserts casi simultáneos).
            st.error(f"⚠️ Ya existe una categoría llamada '{nombre}' (restricción única en la base de datos).")
        elif "row-level security" in error_msg.lower() or "RLS" in error_msg:
            st.error(
                "❌ Supabase rechazó la operación por Row Level Security (RLS). "
                "Verifica que exista una política que permita INSERT en la tabla "
                f"'categorias' para tu rol/clave actual. Detalle: {error_msg}"
            )
        else:
            st.error(f"❌ Error de Supabase al crear categoría: {error_msg}")
        return False


def eliminar_categoria(nombre: str) -> bool:
    """
    Elimina una categoría existente de Supabase.
    """
    try:
        res = get_supabase().table("categorias").delete().eq("nombre", nombre).execute()
        if not res.data:
            st.error("❌ La base de datos bloqueó la eliminación (0 filas afectadas). Posible problema de permisos (RLS).")
            return False
        return True
    except Exception as e:
        error_msg = str(e).lower()
        if "foreign key constraint" in error_msg or "23503" in error_msg:
            st.error("❌ No se puede eliminar la categoría porque tiene registros de asistencia asociados. Borra la asistencia primero o contacta al administrador.")
        else:
            st.error(f"❌ Error de Supabase al eliminar categoría: {e}")
        return False


def actualizar_profesor_categoria(nombre: str, profesor: str) -> bool:
    """
    Actualiza el profesor a cargo de una categoría en Supabase.
    """
    try:
        get_supabase().table("categorias").update({
            "profesor": profesor.strip()
        }).eq("nombre", nombre).execute()
        return True
    except Exception as e:
        st.error(f"❌ Error de Supabase al actualizar profesor de categoría: {e}")
        return False


def obtener_profesor_de(categoria: str) -> str:
    """
    Retorna el nombre del profesor a cargo de una categoría específica.
    """
    try:
        response = get_supabase().table("categorias").select("profesor").eq("nombre", categoria).execute()
        if response.data and len(response.data) > 0:
            return response.data[0].get("profesor", "")
        return ""
    except Exception as e:
        st.error(f"❌ Error de Supabase al obtener profesor de la categoría: {e}")
        return ""


def obtener_profesores_roster() -> list:
    """
    Retorna una lista única y ordenada de todos los profesores asignados a las categorías.
    """
    categorias = obtener_categorias_config()
    profesores = set(c.get("profesor", "").strip() for c in categorias if c.get("profesor"))
    return sorted(list(profesores))


# =============================================================================
# CAPA DE DATOS - ASISTENCIA (Esquema Normalizado, 100% Supabase)
# =============================================================================

def guardar_asistencia(fecha: str, categoria: str, registros: dict) -> bool:
    """
    Guarda o actualiza la asistencia insertando/haciendo upsert de una fila
    individual por cada jugador en la tabla 'asistencia'.
    """
    try:
        for rut, info in registros.items():
            data_upsert = {
                "fecha": fecha,
                "jugador_rut": rut,
                "categoria": categoria,
                "estado": info["estado"]
            }
            get_supabase().table("asistencia").upsert(data_upsert, on_conflict="fecha,jugador_rut").execute()
        return True
    except Exception as e:
        st.error(f"❌ Error de Supabase al guardar asistencia: {e}")
        return False


def obtener_asistencia(fecha: str, categoria: str) -> dict:
    """
    Retorna la asistencia de una fecha y categoría específica convertida
    al formato de diccionario esperado por la interfaz: {rut: {"jugador": nombre, "estado": estado}}
    """
    try:
        response = get_supabase().table("asistencia") \
            .select("jugador_rut, estado, jugadores(nombre)") \
            .eq("fecha", fecha) \
            .eq("categoria", categoria) \
            .execute()

        resultado = {}
        if response.data:
            for row in response.data:
                rut = row["jugador_rut"]
                estado = row["estado"]
                jugador_info = row.get("jugadores")
                nombre = jugador_info.get("nombre", "") if isinstance(jugador_info, dict) else ""
                resultado[rut] = {"jugador": nombre, "estado": estado}
        return resultado
    except Exception as e:
        st.error(f"Error de Supabase al obtener asistencia: {e}", icon=":material/error:")
        return {}


def obtener_asistencia_general(categoria: Optional[str] = None) -> list:
    """
    Retorna el historial completo de asistencia, opcionalmente filtrado por categoría.
    Realiza un JOIN con la tabla de jugadores para obtener los nombres.
    """
    try:
        query = get_supabase().table("asistencia").select("fecha, jugador_rut, estado, categoria, jugadores(nombre)")
        if categoria:
            query = query.eq("categoria", categoria)
        response = query.execute()
        
        resultados = []
        if response.data:
            for row in response.data:
                jugador_info = row.get("jugadores")
                nombre = jugador_info.get("nombre", "") if isinstance(jugador_info, dict) else ""
                resultados.append({
                    "fecha": row["fecha"],
                    "jugador_rut": row["jugador_rut"],
                    "estado": row["estado"],
                    "categoria": row["categoria"],
                    "jugador_nombre": nombre
                })
        return resultados
    except Exception as e:
        st.error(f"Error de Supabase al obtener historial de asistencia: {e}", icon=":material/error:")
        return []


# =============================================================================
# CAPA DE DATOS - PAGOS (100% Supabase, con JOIN a jugadores)
# =============================================================================

def guardar_pago(pago: dict) -> bool:
    """
    Guarda un registro de pago en la tabla 'pagos' de Supabase.
    Esquema real: id(uuid), jugador_rut(text), monto(int4), fecha_pago(text), mes_correspondiente(text)
    """
    try:
        get_supabase().table("pagos").insert(pago).execute()
        return True
    except Exception as e:
        st.error(f"❌ Error de Supabase al guardar pago: {e}")
        return False


def actualizar_pago(id_pago: str, datos: dict) -> bool:
    """Actualiza los datos de un pago existente en Supabase."""
    try:
        res = get_supabase().table("pagos").update(datos).eq("id", id_pago).execute()
        if not res.data:
            st.error("❌ No se pudo actualizar el pago (0 filas afectadas).")
            return False
        return True
    except Exception as e:
        st.error(f"❌ Error al actualizar pago: {e}")
        return False


def eliminar_pago(id_pago: str) -> bool:
    """Elimina un pago de Supabase por su ID."""
    try:
        res = get_supabase().table("pagos").delete().eq("id", id_pago).execute()
        if not res.data:
            st.error("❌ No se pudo eliminar el pago (0 filas afectadas).")
            return False
        return True
    except Exception as e:
        st.error(f"❌ Error al eliminar pago: {e}")
        return False


def obtener_pagos(jugador_rut: Optional[str] = None) -> list:
    """
    Retorna los pagos registrados haciendo JOIN con la tabla 'jugadores'
    para traer el 'nombre' y la 'categoria' del jugador.
    Columnas reales de pagos: id, jugador_rut, monto, fecha_pago, mes_correspondiente
    """
    try:
        query = get_supabase().table("pagos").select("*, jugadores(nombre, categoria)")
        
        if jugador_rut:
            query = query.eq("jugador_rut", jugador_rut)
            
        response = query.execute()
        
        pagos_procesados = []
        if response.data:
            for p in response.data:
                pago_item = p.copy()
                jugador_rel = pago_item.pop("jugadores", None)
                if isinstance(jugador_rel, dict):
                    pago_item["jugador_nombre"] = jugador_rel.get("nombre", "")
                    pago_item["categoria"] = jugador_rel.get("categoria", "")
                else:
                    pago_item.setdefault("jugador_nombre", "")
                    pago_item.setdefault("categoria", "")
                pagos_procesados.append(pago_item)
                
        return pagos_procesados
    except Exception as e:
        st.error(f"❌ Error de Supabase al obtener pagos: {e}")
        return []


# =============================================================================
# AUTENTICACIÓN (Login demo — no interactúa con las tablas de datos)
# =============================================================================

def autenticar_usuario(username: str, password: str) -> Optional[dict]:
    """
    Valida credenciales contra el diccionario de credenciales demo.
    Al usar la llave maestra (service_role), ya no dependemos de Supabase Auth.
    """
    usuario = USUARIOS_DEMO.get(username)
    if usuario and usuario["password"] == password:
        return {"username": username, "rol": usuario["rol"], "nombre": usuario["nombre"]}
    return None
