import re

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
