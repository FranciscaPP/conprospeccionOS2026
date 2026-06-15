"""Script maestro de sincronización GHL → Supabase.
Corre todos los syncs en orden: pipelines, usuarios, contactos, reuniones, oportunidades.
"""
from __future__ import annotations

import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
PYTHON = sys.executable

STEPS = [
    ("sync_pipelines",    ["sync_pipelines.py"]),
    ("sync_users",        ["sync_users.py"]),
    ("sync_contacts",     ["sync_ghl.py", "--entity", "contactos"]),
    ("sync_meetings",     ["sync_meetings.py"]),
    ("sync_oportunidades",["sync_ghl.py", "--entity", "oportunidades"]),
    ("sync_snov",         ["sync_snov.py"]),
]


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S,%f",
    )


def main() -> None:
    setup_logging()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    logging.info("=== SYNC GHL → SUPABASE | %s ===", now)

    errors = []
    for name, cmd in STEPS:
        script = SCRIPTS_DIR / cmd[0]
        full_cmd = [PYTHON, str(script)] + cmd[1:]
        logging.info("▶ Iniciando %s...", name)
        result = subprocess.run(full_cmd, cwd=SCRIPTS_DIR)
        if result.returncode != 0:
            logging.error("✗ %s falló con código %s", name, result.returncode)
            errors.append(name)
        else:
            logging.info("✓ %s completado", name)

    if errors:
        logging.warning("Sync terminado con errores en: %s", ", ".join(errors))
        sys.exit(1)
    else:
        logging.info("✓ Sync completo sin errores")


if __name__ == "__main__":
    main()
