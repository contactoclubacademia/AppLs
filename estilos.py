import streamlit as st


def inject_css() -> None:
    """Inyecta el CSS corporativo (rojo/negro) y oculta el chrome de Streamlit."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] { font-family: 'Poppins', sans-serif; }

        /* -------- Ocultar elementos por defecto de Streamlit --------
           IMPORTANTE: NO ocultamos el <header> completo. El botón que
           colapsa/expande el sidebar vive dentro de ese header; si se
           oculta entero (visibility:hidden), ese botón deja de poder
           usarse y el sidebar queda "atascado". En su lugar, ocultamos
           solo las piezas puntuales (menú hamburguesa, botón Deploy,
           barra de herramientas, franja decorativa, indicador de
           estado) y dejamos el header transparente. */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        .stDeployButton {display: none;}
        [data-testid="stToolbar"] {visibility: hidden; height: 0;}
        [data-testid="stDecoration"] {visibility: hidden; height: 0;}
        [data-testid="stStatusWidget"] {visibility: hidden; height: 0;}

        /* -------- FIX: flechita para abrir/cerrar el sidebar --------
           `visibility` se hereda en CSS: al ocultar stToolbar/stDecoration
           con `visibility: hidden`, cualquier elemento que Streamlit haya
           anidado ahí adentro se oculta también, aunque no lo hayamos
           apuntado directamente. El botón para reabrir el sidebar es
           justamente uno de esos elementos, y Streamlit le ha cambiado
           el nombre (data-testid) varias veces entre versiones
           (collapsedControl -> stSidebarCollapseButton ->
           stSidebarCollapsedControl -> stExpandSidebarButton). Como un
           hijo SIEMPRE puede sobreescribir la visibilidad heredada de su
           padre, aquí lo forzamos a visible cubriendo todos los nombres
           posibles, sin importar en qué versión de Streamlit corra la
           app ni dónde haya quedado anidado. */
        [data-testid="stExpandSidebarButton"],
        [data-testid="stSidebarCollapseButton"],
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="collapsedControl"] {
            visibility: visible !important;
            opacity: 1 !important;
            height: auto !important;
            width: auto !important;
            display: flex !important;
            z-index: 999999 !important;
            margin-top: 25px !important;
            margin-left: 10px !important;
        }
        [data-testid="stExpandSidebarButton"] *,
        [data-testid="stSidebarCollapseButton"] *,
        [data-testid="stSidebarCollapsedControl"] *,
        [data-testid="collapsedControl"] * {
            visibility: visible !important;
        }

        /* -------- Forzar tema claro y texto legible --------
           Streamlit define el color de texto real vía variables CSS
           (--text-color). Si el navegador/SO está en modo oscuro,
           ese texto sale blanco y se vuelve invisible sobre nuestros
           fondos claros. Fijamos ambas cosas: la variable y el color
           heredado, como respaldo. La forma oficial y más robusta de
           fijar esto es el archivo .streamlit/config.toml (ver README
           al final de este archivo). */
        :root {
            --text-color: #1A1A1A;
            --background-color: #FFFFFF;
            --secondary-background-color: #F4F5F7;
            --primary-color: #C8102E;
        }

        .stApp { background-color: #F4F5F7; color: #1A1A1A; }

        /* Ojo: usamos ".main" (NO ".stApp") para no pisar el color
           claro del texto del sidebar oscuro, que vive más abajo. */
        .main p, .main span, .main label,
        .main h1, .main h2, .main h3, .main h4, .main h5, .main h6 {
            color: #1A1A1A;
        }

        /* En versiones modernas, el header fantasma ocupa 60px. Lo hacemos invisible pero SIN borrarlo del DOM para no perder el botón del sidebar. */
        [data-testid="stHeader"], .stApp > header {
            background: transparent !important;
            height: 0px !important;
            min-height: 0px !important;
        }

        div.block-container {
            padding-top: 1rem !important;
            padding-bottom: 0rem !important;
            margin-top: 0 !important;
            max-width: 1200px;
        }
        
        /* Ajustar el primer título para que alinee perfecto con el botón */
        div.block-container h1 {
            margin-top: -1rem !important;
            padding-top: 0 !important;
        }

        /* ==================== SIDEBAR ==================== */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1A1A1A 0%, #0D0D0D 100%);
            border-right: 3px solid #C8102E;
        }
        [data-testid="stSidebarNav"] {display: none !important;}
        [data-testid="stSidebar"] * { color: #EAEAEA; }

        .sidebar-header {
            text-align: center;
            padding: 6px 0 22px 0;
            border-bottom: 1px solid #333333;
            margin-bottom: 18px;
        }
        .sidebar-logo { font-size: 40px; line-height: 1; }
        .sidebar-brand {
            font-size: 19px; font-weight: 800; letter-spacing: 1px;
            color: #FFFFFF; margin-top: 6px;
        }
        .sidebar-brand span { color: #C8102E; }
        .sidebar-user { margin-top: 16px; font-size: 14px; font-weight: 600; color: #FFFFFF; }
        .sidebar-role {
            display: inline-block; margin-top: 5px; font-size: 11px;
            padding: 3px 12px; background-color: #C8102E; color: white;
            border-radius: 12px; letter-spacing: .4px; font-weight: 600;
        }
        .sidebar-spacer { margin-top: 30px; }
        .sidebar-footer-note { font-size: 11px; color: #7A7A7A; text-align: center; margin-top: 10px; }

        [data-testid="stSidebar"] .stButton>button {
            background-color: transparent;
            color: #FF7A7A;
            border: 1.5px solid #C8102E;
            border-radius: 8px;
            font-weight: 600;
            padding: 10px 0;
            width: 100%;
            transition: all .2s ease;
        }
        [data-testid="stSidebar"] .stButton>button:hover {
            background-color: #C8102E;
            color: #FFFFFF;
            border-color: #C8102E;
        }

        /* ==================== HEADERS DE PÁGINA ==================== */
        .page-header {
            border-left: 6px solid #C8102E;
            padding: 4px 0 4px 18px;
            margin-bottom: 26px;
        }
        .page-header h1 { margin: 0; font-size: 25px; font-weight: 700; color: #1A1A1A; }
        .page-header p  { margin: 2px 0 0 0; color: #6B7280; font-size: 14px; }

        .topbar-chip {
            display: inline-block; float: right; background: #FFFFFF;
            padding: 7px 16px; border-radius: 20px; border: 1px solid #E2E4E8;
            font-size: 12px; color: #374151; font-weight: 500;
        }
        .topbar-dot {
            display: inline-block; width: 8px; height: 8px; border-radius: 50%;
            background: #22C55E; margin-right: 6px;
        }

        /* ==================== LOGIN ==================== */
        .login-wrapper { padding-top: 130px; }
        .login-card {
            text-align: center; background: #FFFFFF;
            padding: 42px 30px 12px 30px; border-radius: 16px 16px 0 0;
        }
        .login-logo { font-size: 50px; line-height: 1; }
        .login-title { font-weight: 800; letter-spacing: 1px; color: #1A1A1A; margin: 10px 0 0 0; }
        .login-subtitle { color: #6B7280; font-size: 14px; margin-top: 3px; }
        .login-hint { text-align: center; color: #9CA3AF; font-size: 12px; margin-top: 12px; }

        div[data-testid="stForm"] {
            background: #FFFFFF;
            padding: 26px 35px 30px 35px;
            border-radius: 0 0 16px 16px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.08);
            border: 1px solid #E2E4E8;
            border-top: none;
        }

        /* ==================== BOTONES ==================== */
        .stButton>button, .stFormSubmitButton>button {
            background: linear-gradient(135deg, #C8102E 0%, #8E0B20 100%);
            color: #FFFFFF; border: none; border-radius: 8px;
            padding: 10px 22px; font-weight: 600; letter-spacing: .3px;
            transition: all .2s ease;
            box-shadow: 0 4px 12px rgba(200,16,46,0.25);
        }
        .stButton>button:hover, .stFormSubmitButton>button:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 18px rgba(200,16,46,0.35);
        }

        /* ==================== INPUTS ==================== */
        .stTextInput>div>div>input,
        .stNumberInput>div>div>input,
        .stDateInput>div>div>input {
            border-radius: 8px; border: 1.5px solid #E2E4E8;
        }
        .stTextInput>div>div>input:focus,
        .stNumberInput>div>div>input:focus {
            border-color: #C8102E; box-shadow: 0 0 0 1px #C8102E;
        }
        div[data-baseweb="select"] > div { border-radius: 8px; border: 1.5px solid #E2E4E8; }

        /* ==================== DATAFRAME / MÉTRICAS ==================== */
        [data-testid="stDataFrame"] {
            border-radius: 12px; overflow: hidden;
            border: 1px solid #E2E4E8; box-shadow: 0 2px 10px rgba(0,0,0,0.04);
        }
        [data-testid="stMetric"] {
            background: #FFFFFF; padding: 14px 16px; border-radius: 12px;
            border: 1px solid #E2E4E8; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }
        [data-testid="stMetricLabel"] { color: #6B7280; }

        /* ==================== ASISTENCIA ==================== */
        .jugador-row { padding: 8px 0; }
        .jugador-sub { color: #9CA3AF; font-size: 12px; }
        .asistencia-header-row {
            display: flex; justify-content: space-between;
            font-weight: 700; color: #1A1A1A; font-size: 12px;
            text-transform: uppercase; letter-spacing: .6px;
            padding-bottom: 8px; border-bottom: 2px solid #1A1A1A; margin-bottom: 4px;
        }
        .asistencia-divider { border: none; border-top: 1px solid #EDEDED; margin: 2px 0 4px 0; }

        div[data-testid="stAlert"] { border-radius: 10px; }

        /* ==================== RESPONSIVE (TELÉFONO) ====================
           Ajustes seguros de Streamlit nativo para no romper la interfaz */
        @media (max-width: 768px) {
            /* Asegurar que el botón para abrir el menú en celular se vea bien */
            [data-testid="collapsedControl"] {
                top: 15px !important;
                left: 10px !important;
                background-color: #FFFFFF !important;
                border: 1px solid #E2E4E8 !important;
                border-radius: 8px !important;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important;
            }
            [data-testid="collapsedControl"] svg {
                fill: #C8102E !important;
            }

            .main .block-container,
            [data-testid="stAppViewBlockContainer"] {
                padding-top: 3.5rem !important; /* Más espacio arriba para que el contenido no tape el botón */
                padding-left: 1rem;
                padding-right: 1rem;
                padding-bottom: 2rem;
            }
            .main .block-container h1,
            [data-testid="stAppViewBlockContainer"] h1 {
                margin-top: 0 !important;
            }
            .topbar-chip {
                float: none;
                display: inline-block;
                margin: 0 0 12px 0;
                font-size: 11px;
                padding: 6px 12px;
            }
            .page-header { margin-bottom: 15px; }
            .page-header h1 { font-size: 17px !important; }
            .page-header p { font-size: 11.5px !important; }
            
            /* Títulos generales de Streamlit (Markdown) reducidos para celular */
            h1, .stMarkdown h1 { font-size: 18px !important; }
            h2, .stMarkdown h2 { font-size: 16px !important; }
            h3, .stMarkdown h3 { font-size: 15px !important; }
            h4, .stMarkdown h4 { font-size: 14px !important; }
            
            /* Pestañas (Tabs) más pequeñas */
            .stTabs button p { font-size: 13px !important; }

            .login-wrapper { padding-top: 50px; }
            .login-card { padding: 25px 15px 10px 15px; }
            .login-title { font-size: 18px !important; margin-top: 5px; }
            .login-subtitle { font-size: 12px !important; }
            
            div[data-testid="stForm"] { padding: 15px 15px 20px 15px; }
            .asistencia-header-row { display: none; }
            div[data-testid="stRadio"] label p { font-size: 12.5px !important; }
            .sidebar-brand { font-size: 16px; }
        }


        /* ==================== STATS CARDS ==================== */
        .stats-card {
            background-color: #FFFFFF; padding: 15px; border-radius: 8px;
            border: 1px solid #E2E4E8; margin-top: 20px;
        }
        .stats-card h4 { margin-top: 0; color: #1A1A1A; }
        .stats-row {
            display: flex; justify-content: space-between; flex-wrap: wrap; gap: 10px;
        }
        .stats-item {
            display: flex; align-items: center; gap: 8px; font-size: 16px;
        }
        .total-recaudado {
            background-color: #FFFFFF; padding: 12px; border-radius: 8px;
            border: 1px solid #E2E4E8; text-align: right; font-weight: bold;
            font-size: 16px; margin-top: 15px; color: #1A1A1A;
        }
        .total-recaudado span { color: #C8102E; }

        </style>
        """,
        unsafe_allow_html=True,
    )



