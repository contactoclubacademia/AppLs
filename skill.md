# skill.md — Manual de Herramientas (Skills) del Agente

> Generado a partir del análisis del código base de **Academia La Serena** (Streamlit + Supabase).
> Cada skill corresponde a una función real de `database.py`, envuelta con las reglas de
> validación que hoy viven en los formularios de `pages/*.py`. El agente de IA debe usar
> este documento como única fuente de verdad sobre qué herramientas existen, qué datos
> exigen y qué hacer cuando esos datos faltan o son inválidos.

## Convenciones generales (aplican a todas las skills)

| Convención | Regla |
|---|---|
| Fechas | Formato `YYYY-MM-DD`. Si el usuario dice "hoy", usar la fecha actual solo cuando lo confirme o lo pida explícitamente. |
| RUT | Debe cumplir el patrón `8 dígitos + guion + 1 dígito o K` (regex `^\d{8}-[\dkK]$`, ej. `21988505-9`). Nunca ejecutar una escritura con un RUT que no cumpla este formato. |
| Roles | `Administrador` (acceso a todo) y `Profesor/Entrenador` (solo Asistencia). Cada ficha indica el rol requerido. |
| Dato faltante | Nunca se completa con un valor inventado, de ejemplo o "razonable". Se pregunta puntualmente por el/los campo(s) faltantes, sin volver a pedir los que ya se entregaron. |
| Dato inválido | No se ejecuta la herramienta. Se explica al usuario la regla incumplida (formato, rango, opción no válida) y se solicita la corrección. |
| Categoría inexistente | Antes de usar cualquier skill que reciba una categoría como parámetro, se valida su existencia contra `consultar_categorias`. Si no existe, no se ejecuta la acción: se informa y se sugieren las categorías válidas o se ofrece crearla (si el rol lo permite). |

---

## Categoría: Autenticación

### 1. `autenticar_usuario`
- **Propósito:** validar el acceso de una persona al sistema (usuario + contraseña) al inicio de una sesión de trabajo.
- **Parámetros requeridos:**
  - `username` (str)
  - `password` (str)
- **Reglas de ejecución:**
  - Si falta `username` o `password`, solicitarlos explícitamente antes de intentar autenticar.
  - Nunca inferir, autocompletar o "adivinar" una contraseña.
  - Nunca registrar la contraseña en texto plano en resúmenes, memoria conversacional persistente o logs generados por la IA.
  - Si la autenticación falla, informar el fallo sin precisar si el error estuvo en el usuario o en la contraseña (buena práctica de seguridad).
  - Esta herramienta identifica **a la persona que opera el sistema**, no permite "iniciar sesión en nombre de" un tercero.

---

## Categoría: Jugadores

### 2. `registrar_jugador`
*(envuelve `guardar_jugador`, aplicando las validaciones de `pages/registro.py`)*

- **Propósito:** dar de alta a un nuevo jugador y su apoderado en la academia.
- **Parámetros requeridos:**
  - `rut_jugador`, `nombre_jugador`, `anio_nacimiento` (entero entre 2005 y el año actual)
  - `categoria` (debe existir en `consultar_categorias`)
  - `posicion` (una de: `Arquero`, `Defensa`, `Mediocampista`, `Delantero`)
  - `rut_apoderado`, `nombre_apoderado`, `telefono_apoderado`, `correo_apoderado`, `telefono_emergencia`
- **Reglas de ejecución:**
  - Todos los campos son obligatorios. Si falta alguno, pedir específicamente los faltantes.
  - Validar el formato de `rut_jugador` y `rut_apoderado` (ver tabla de convenciones) **antes** de llamar a la herramienta; si no cumple, pedir corrección con un ejemplo.
  - Validar que `categoria` exista; si no hay ninguna categoría creada todavía, informar que deben crearse primero (requiere `crear_categoria`, rol Administrador) y no continuar.
  - Validar `posicion` contra la lista cerrada de 4 opciones; si el usuario da un valor libre o ambiguo, preguntar cuál de las 4 corresponde.
  - **Rol requerido:** Administrador.

### 3. `consultar_jugadores`
- **Propósito:** listar jugadores registrados (plantilla general o filtrada por categoría), por ejemplo para revisar inscritos, datos de apoderados o resolver a qué jugador se refiere el usuario en otra operación (pagos, asistencia).
- **Parámetros requeridos:**
  - `categoria` (opcional)
- **Reglas de ejecución:**
  - Si no se especifica categoría, se listan todos los jugadores.
  - Si se pide una categoría que no existe, no ejecutar con ese valor: avisar y mostrar las categorías válidas.

---

## Categoría: Categorías

### 4. `crear_categoria`
- **Propósito:** dar de alta una nueva categoría de edad (ej. Sub-14) con o sin profesor asignado.
- **Parámetros requeridos:**
  - `nombre` (obligatorio, no vacío)
  - `profesor` (opcional)
- **Reglas de ejecución:**
  - Si falta `nombre`, pedirlo.
  - Si el usuario no menciona profesor, crear la categoría igualmente como "Sin asignar" — este campo nunca bloquea la operación.
  - El sistema valida duplicados por nombre exacto; si ya existe, comunicar el error devuelto tal cual, sin reintentar automáticamente con un nombre alternativo inventado.
  - **Rol requerido:** Administrador.

### 5. `eliminar_categoria`
- **Propósito:** eliminar una categoría existente.
- **Parámetros requeridos:**
  - `nombre` (obligatorio, debe existir)
- **Reglas de ejecución:**
  - **Acción destructiva/irreversible.** Siempre confirmar explícitamente con el usuario antes de ejecutar (ej.: *"¿Confirmas eliminar la categoría Sub-14? Esta acción no se puede deshacer y no reasigna automáticamente a los jugadores que estén en ella."*).
  - Si el nombre es ambiguo (coincide parcialmente con más de una categoría), pedir precisión.
  - **Rol requerido:** Administrador.

### 6. `actualizar_profesor_categoria`
- **Propósito:** cambiar o asignar el profesor a cargo de una categoría.
- **Parámetros requeridos:**
  - `nombre` (categoría existente)
  - `profesor`
- **Reglas de ejecución:**
  - Si falta el nombre de la categoría, pedirlo.
  - `profesor` puede quedar vacío únicamente si el usuario indica de forma explícita que desea dejarla sin profesor asignado.
  - **Rol requerido:** Administrador.

### 7. `consultar_categorias`
- **Propósito:** obtener el listado de nombres de categorías (o su configuración completa, incluyendo profesor a cargo).
- **Parámetros requeridos:** ninguno.
- **Reglas de ejecución:** usar como paso previo obligatorio antes de cualquier skill que reciba una categoría como parámetro.

### 8. `consultar_profesor_de_categoria`
- **Propósito:** saber quién es el profesor a cargo de una categoría específica.
- **Parámetros requeridos:**
  - `categoria` (obligatorio)
- **Reglas de ejecución:** si la categoría no existe, no inventar un profesor; responder que la categoría no existe y ofrecer crearla.

### 9. `consultar_roster_profesores`
- **Propósito:** obtener el listado único de todos los profesores ya asignados a alguna categoría (útil para reutilizar un nombre existente en vez de crear uno nuevo por variación de escritura).
- **Parámetros requeridos:** ninguno.

---

## Categoría: Asistencia

### 10. `registrar_asistencia`
- **Propósito:** guardar el estado de asistencia de los jugadores de una categoría en una fecha determinada.
- **Parámetros requeridos:**
  - `fecha` (`YYYY-MM-DD`)
  - `categoria` (obligatoria, existente)
  - `registros`: lista de pares `{rut_jugador, estado}`, donde `estado` ∈ {`Presente`, `Ausente`, `Justificado/Lesionado`}
- **Reglas de ejecución:**
  - Antes de registrar, obtener el listado de jugadores de esa categoría (`consultar_jugadores` filtrado) para no aceptar un RUT que no pertenezca a ella.
  - Si el usuario no indica el estado de algún jugador, **no asumir "Presente" por defecto**: preguntar explícitamente, o bien informar que se conservará el último estado registrado para esa fecha (comportamiento real del sistema: la herramienta de consulta recupera el estado previo si ya existía).
  - **Rol requerido:** Administrador o Profesor/Entrenador.

### 11. `consultar_asistencia`
- **Propósito:** revisar la asistencia ya registrada para una fecha y categoría.
- **Parámetros requeridos:**
  - `fecha`, `categoria` (ambos obligatorios)
- **Reglas de ejecución:** si falta la fecha, usar la fecha actual solo si el usuario lo confirma o dice "hoy" explícitamente; de lo contrario, preguntar.
- **Rol requerido:** Administrador o Profesor/Entrenador.

---

## Categoría: Pagos

### 12. `registrar_pago`
- **Propósito:** registrar el pago de una mensualidad de un jugador.
- **Parámetros requeridos:**
  - Identificación del jugador (RUT, o nombre + categoría para desambiguar)
  - `mes_correspondiente` (uno de los 12 meses del año)
  - `monto` (entero ≥ 0)
  - `fecha_pago` (`YYYY-MM-DD`)
- **Reglas de ejecución:**
  - Resolver primero al jugador con `consultar_jugadores`; si hay coincidencias ambiguas por nombre, pedir el RUT o la categoría antes de registrar.
  - Si falta el monto o el mes, pedirlos explícitamente. **No asumir un monto por defecto** aunque la interfaz original sugiera uno: es solo un valor de referencia visual, no una regla de negocio.
  - **Rol requerido:** Administrador.

### 13. `consultar_pagos`
- **Propósito:** revisar el historial de pagos, opcionalmente filtrado por jugador o categoría, y calcular totales recaudados.
- **Parámetros requeridos:**
  - `jugador_rut` (opcional)
  - `categoria` (opcional, aplicado como filtro sobre el resultado)
- **Reglas de ejecución:** si se pide un "total recaudado", sumar únicamente los montos de los registros efectivamente devueltos por la herramienta; nunca estimar o redondear cifras.
- **Rol requerido:** Administrador.

---

## Notas finales

- Todas las escrituras (`crear_*`, `registrar_*`, `actualizar_*`, `eliminar_*`) dependen de la conectividad con Supabase. Si el resultado indica un error de red, de política de seguridad (RLS) o de duplicado, ese mensaje debe traducirse a lenguaje natural y claro para el usuario, sin ocultar la causa si esta se solicita.
- Ninguna herramienta se ejecuta especulativamente "para probar": toda ejecución debe estar motivada por una intención explícita y completa del usuario, validada según las reglas de esta ficha.