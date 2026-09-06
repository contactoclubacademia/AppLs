# AGENTS.md — Academia La Serena (Streamlit + Supabase)

## Quick Start

```bash
# Run the app
streamlit run app.py

# Install dependencies
pip install -r requirements.txt
```

## Architecture Overview

**Monorepo structure:**
```
APPls/
├── app.py                 # Entry point, routing, sidebar, auth
├── database.py            # Supabase wrapper (ALL data access here)
├── estilos.py             # Global CSS (inject_css())
├── styles.py              # (legacy, unused)
├── requirements.txt       # 4 deps only
├── .streamlit/
│   ├── config.toml        # Theme (light, red accents, light sidebar hidden)
│   └── secrets.toml       # SUPABASE_URL, SUPABASE_KEY (anon key)
├── pages/                 # Module pages (routed from app.py)
│   ├── login.py
│   ├── registro.py
│   ├── plantillas.py
│   ├── asistencia.py
│   ├── categorias.py
│   └── pagos.py
├── database.py            # Supabase client + ALL data access
├── estilos.py             # CSS injection (inject_css())
├── models.md              # System prompt (agent behavior)
├── skill.md               # Skill registry (13 tools)
└── AGENTS.md              # This file
```

**Architecture pattern:** Streamlit multipage app with central `app.py` routing. All data access through `database.py` (Supabase client). No ORM, raw Supabase client calls.

## Key Commands

```bash
# Run app
streamlit run app.py

# Install deps
pip install -r requirements.txt

# Lint / typecheck (none configured)
# python -m py_compile app.py pages/*.py database.py estilos.py
```

## Environment & Secrets

`.streamlit/secrets.toml` (gitignored):
```toml
SUPABASE_URL = "https://<project>.supabase.co"
SUPABASE_KEY = "eyJ..."  # anon/public key (JWT), NOT service_role
```

Access in code via `st.secrets["SUPABASE_URL"]`, `st.secrets["SUPABASE_KEY"]`.

## Architecture Rules (Strict)

| Rule | Description |
|------|-------------|
| **Single data layer** | All Supabase calls in `database.py` only. No `supabase.table()` in `pages/`. |
| **CSS centralized** | All styles in `estilos.py` via `inject_css()`. No inline CSS in pages. |
| **No inline CSS in pages** | Pages call `inject_css()` once at top of render function. |
| **Forms in pages** | Use `st.form()` with `st.form_submit_button(..., type="primary")`. |
| **Containers** | Wrap logical sections in `with st.container(border=True):`. |
| **Buttons** | Primary actions: `st.form_submit_button(..., type="primary")`. |
| **Icons** | Use Material icons syntax: `:material/icon_name:` (e.g., `:material/person_add:`). |
| **No emojis in UI** | Only Material icons. No 🎉, ✅, etc. in UI text. |
| **RUT format** | `^\d{8}-[\dkK]$` (e.g., `21988505-9`). Validate before DB write. |
| **Roles** | `Administrador` (full) vs `Profesor/Entrenador` (only Asistencia). |

## Module Map (pages/)

| Page | Purpose | Key Functions |
|------|---------|---------------|
| `login.py` | Auth | `render_login()` |
| `registro.py` | Register player + apoderado | `render_registro()` |
| `plantillas.py` | Player roster + filters | `render_plantillas()` |
| `asistencia.py` | Attendance by date/category | `render_asistencia()` |
| `categorias.py` | CRUD categories + professor assign | `render_categorias()` |
| `pagos.py` | Payment register + history | `render_pagos()` |

## Data Layer (`database.py`)

All Supabase calls centralized here. **Never** call `supabase.table()` in `pages/`.

Key functions:
| Function | Purpose |
|----------|---------|
| `guardar_jugador(jugador)` | Insert player |
| `obtener_jugadores(categoria?)` | List players |
| `crear_categoria(nombre, profesor)` | Create category |
| `eliminar_categoria(nombre)` | Delete category |
| `actualizar_profesor_categoria(nombre, profesor)` | Update professor |
| `obtener_categorias()` | List category names |
| `obtener_categorias_config()` | Full config (name + profesor) |
| `guardar_asistencia(fecha, categoria, registros)` | Upsert attendance |
| `obtener_asistencia(fecha, categoria)` | Fetch attendance |
| `guardar_pago(pago)` | Insert payment |
| `obtener_pagos(jugador_rut?)` | List payments (JOIN jugadores) |
| `autenticar_usuario(username, password)` | Auth against demo dict |

## Database Schema (Supabase)

```sql
categorias(nombre PK, profesor, created_at)
jugadores(rut PK, nombre, anio_nacimiento, categoria FK, estado, apoderado_nombre, apoderado_telefono, apoderado_rut, apoderado_correo, telefono_emergencia, fecha_registro)
asistencia(id, fecha, categoria FK, jugador_rut FK, estado, created_at, UNIQUE(fecha, jugador_rut))
pagos(id UUID PK, jugador_rut FK, mes_correspondiente, monto, fecha_pago, metodo, observaciones, created_at)
usuarios(id UUID PK, username, password, salt, rol, nombre, permisos, created_at, UNIQUE(username))
```

### Base de Datos — Optimizaciones (Fase 6)
Para asegurar el rendimiento óptimo y seguridad a largo plazo, se recomiendan las siguientes configuraciones en Supabase:

1. **Índices de Rendimiento (Verificar/Crear):**
   - `CREATE INDEX idx_jugadores_categoria ON jugadores(categoria);`
   - `CREATE INDEX idx_asistencia_fecha_cat ON asistencia(fecha, categoria);`
   - `CREATE INDEX idx_pagos_rut_fecha ON pagos(jugador_rut, fecha_pago);`

2. **Políticas de Seguridad (RLS):**
   - Actualmente RLS permite `anon` SELECT y `authenticated` ALL.
   - **Recomendación:** Activar RLS estricto y validar roles desde el JWT en Supabase para evitar accesos no autorizados si la API key anónima es expuesta.

3. **Migración de Autenticación:**
   - Actualmente se usa una tabla personalizada `usuarios` con hash PBKDF2 (SHA-256).
   - **Recomendación:** Considerar migrar a **Supabase Auth (GoTrue)** en el futuro para delegar la seguridad, manejo de sesiones, reseteo de contraseñas y MFA a la plataforma nativa.

## Testing / Verification

```bash
# Compile check
python -m py_compile app.py pages/*.py database.py estilos.py

# Run app
streamlit run app.py
```

## Common Pitfalls

| Issue | Solution |
|-------|----------|
| `ImportError: cannot import 'aplicar_estilos_globales'` | Remove import, use only `inject_css()` |
| `UnboundLocalError: obtener_categorias` | Don't shadow imported function with local variable (use `lista_categorias = obtener_categorias()`) |
| `getaddrinfo failed` | Check `SUPABASE_URL` in secrets (no trailing `/rest/v1/`) |
| `401 Invalid API key` | Verify `SUPABASE_KEY` is anon key (JWT), not `sb_publishable_...` |
| Sidebar shows on login | CSS hides `[data-testid="stSidebar"]` in login; `app.py` injects CSS conditionally |
| Sidebar missing after login | `initial_sidebar_state="expanded"` + no global `stSidebar` hide CSS |

## File Ownership

| File | Owner | Purpose |
|------|-------|---------|
| `app.py` | Entry, routing, auth, sidebar | App shell |
| `database.py` | All Supabase CRUD | Data layer |
| `estilos.py` | All CSS (`inject_css`) | Styling |
| `pages/*.py` | Feature modules | UI + forms |

## References

- `models.md` — System prompt (agent behavior)
- `skill.md` — 13 tool definitions for agent
- `.streamlit/config.toml` — Official theme
- `.streamlit/secrets.toml` — Supabase credentials

## Quick Verification

```bash
python -m py_compile app.py pages/*.py database.py estilos.py
# No output = OK
```