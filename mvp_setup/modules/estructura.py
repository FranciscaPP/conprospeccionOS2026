from pathlib import Path

CARPETAS = [
    "00_INPUT_CLIENTE/documentos",
    "00_INPUT_CLIENTE/logos",
    "00_INPUT_CLIENTE/bases",
    "00_INPUT_CLIENTE/imagenes",
    "00_INPUT_CLIENTE/minutas",
    "00_INPUT_CLIENTE/otros",
    "01_ADMIN_CLIENTE",
    "02_BRANDING_Y_ACTIVOS/logos_cliente",
    "02_BRANDING_Y_ACTIVOS/logos_encontrados_web",
    "02_BRANDING_Y_ACTIVOS/assets_para_playbook",
    "03_ANALISIS_CLIENTE",
    "04_ICP_ESTRATEGIA",
    "05_MENSAJERIA_COMERCIAL",
    "06_PLAYBOOK_SDR/version_aprobada",
    "07_APOLLO_Y_BUSQUEDAS",
    "08_BASES_DE_DATOS/01_originales",
    "08_BASES_DE_DATOS/02_calificadas",
    "08_BASES_DE_DATOS/03_para_ghl",
    "08_BASES_DE_DATOS/04_para_snov",
    "08_BASES_DE_DATOS/05_para_whatsapp",
    "08_BASES_DE_DATOS/06_por_sdr",
    "08_BASES_DE_DATOS/99_descartados",
    "09_CAMPAÑAS_EMAIL",
    "10_CAMPAÑAS_WHATSAPP/bases_por_sdr",
    "11_SCRIPTS_Y_AUTOMATIZACIONES/crear_estructura_cliente",
    "11_SCRIPTS_Y_AUTOMATIZACIONES/clasificar_base_csv",
    "11_SCRIPTS_Y_AUTOMATIZACIONES/exportar_para_ghl",
    "11_SCRIPTS_Y_AUTOMATIZACIONES/exportar_para_snov",
    "11_SCRIPTS_Y_AUTOMATIZACIONES/generar_whatsapp_links",
    "11_SCRIPTS_Y_AUTOMATIZACIONES/generar_playbook",
    "12_REPORTERIA",
    "13_BRIEF_CLIENTE_INTERACTIVO/respuestas_cliente",
    "14_SUPABASE_METABASE",
    "99_HISTORICO/versiones_anteriores",
    "99_HISTORICO/descartes",
    "99_HISTORICO/respaldos",
]


def crear_estructura_carpetas(cliente_dir: Path) -> list:
    creadas = []
    for carpeta in CARPETAS:
        path = cliente_dir / carpeta
        path.mkdir(parents=True, exist_ok=True)
        creadas.append(carpeta)
    return creadas


def contar_carpetas(cliente_dir: Path) -> int:
    if not cliente_dir.exists():
        return 0
    return sum(1 for p in cliente_dir.rglob("*") if p.is_dir())


def contar_archivos(cliente_dir: Path) -> int:
    if not cliente_dir.exists():
        return 0
    return sum(1 for p in cliente_dir.rglob("*") if p.is_file())


def listar_estructura(cliente_dir: Path) -> dict:
    if not cliente_dir.exists():
        return {}
    estructura = {}
    for carpeta in CARPETAS:
        path = cliente_dir / carpeta
        if path.exists():
            archivos = [f.name for f in path.iterdir() if f.is_file()]
            estructura[carpeta] = archivos
    return estructura
