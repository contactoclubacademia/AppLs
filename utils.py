import re

import streamlit as st

# =============================================================================
# CONSTANTES COMPARTIDAS
# =============================================================================

MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]


def format_cat(cat):
    """Formatea una categoría (dict o str) para selectboxes."""
    if isinstance(cat, dict):
        return cat["nombre"]
    return cat


def validar_rut(rut: str) -> bool:
    """
    Valida un RUT chileno.
    Formato esperado: ^\d{7,8}-[\dkK]$ (ej: 12345678-9)
    """
    rut = rut.strip()
    if not re.match(r"^\d{7,8}-[\dkK]$", rut):
        return False
    
    # Validar digito verificador
    cuerpo, dv = rut.split('-')
    dv = dv.upper()
    
    suma = 0
    multiplo = 2
    for c in reversed(cuerpo):
        suma += int(c) * multiplo
        multiplo += 1
        if multiplo == 8:
            multiplo = 2
            
    esperado = 11 - (suma % 11)
    if esperado == 11:
        dv_esperado = '0'
    elif esperado == 10:
        dv_esperado = 'K'
    else:
        dv_esperado = str(esperado)
        
    return dv == dv_esperado


def verificar_permisos(nombre_modulo: str) -> bool:
    """Verifica si el usuario actual tiene permisos para acceder al módulo.
    Retorna True si tiene acceso, False si no (y muestra error)."""
    permisos = st.session_state.user.get("permisos") or []
    rol = st.session_state.user.get("rol")
    if rol != "Administrador" and nombre_modulo not in permisos:
        st.error("No tienes permisos para acceder a este módulo.", icon=":material/error:")
        return False
    return True

