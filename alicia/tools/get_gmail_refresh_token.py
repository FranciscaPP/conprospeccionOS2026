#!/usr/bin/env python3
"""Genera un refresh token de Gmail para UNA casilla. Se ejecuta localmente.

Evita las claves de cuenta de servicio (bloqueadas por política de la
organización): usa el flujo OAuth de aplicación instalada. Abres el navegador,
inicias sesión con la casilla objetivo, y el script imprime su refresh token.
Ese token se guarda como secret (nunca en el repo ni por chat).

Requisitos (solo en tu equipo, una vez):
    pip install google-auth-oauthlib

Uso (repetir por cada casilla, iniciando sesión con la casilla correcta):
    export GMAIL_OAUTH_CLIENT_ID=...        # de la credencial OAuth (Desktop app)
    export GMAIL_OAUTH_CLIENT_SECRET=...
    python alicia/tools/get_gmail_refresh_token.py

Al terminar imprime:
    Cuenta autorizada: sam@gbs-logistics.cl
    GMAIL_REFRESH_TOKEN = 1//0g....
"""
from __future__ import annotations

import os
import sys

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",  # leer + marcar como leído
    "https://www.googleapis.com/auth/gmail.send",    # responder en el hilo
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]


def main() -> int:
    client_id = os.environ.get("GMAIL_OAUTH_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GMAIL_OAUTH_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        print(
            "Falta GMAIL_OAUTH_CLIENT_ID / GMAIL_OAUTH_CLIENT_SECRET en el entorno.",
            file=sys.stderr,
        )
        return 1

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("Instala primero: pip install google-auth-oauthlib", file=sys.stderr)
        return 1

    config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    flow = InstalledAppFlow.from_client_config(config, SCOPES)
    # access_type=offline + prompt=consent garantizan que Google devuelva un
    # refresh token reutilizable (no solo uno de acceso de corta duración).
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

    if not creds.refresh_token:
        print(
            "No se recibió refresh token. Reintenta; asegúrate de aceptar el consentimiento.",
            file=sys.stderr,
        )
        return 1

    account = ""
    try:  # el email autorizado ayuda a no confundir casillas
        import google.auth.transport.requests
        import urllib.request
        import json

        req = urllib.request.Request(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {creds.token}"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            account = json.loads(resp.read()).get("email", "")
    except Exception:
        account = "(no se pudo leer el email)"

    print("\n===================================================")
    print(f"Cuenta autorizada: {account}")
    print(f"GMAIL_REFRESH_TOKEN = {creds.refresh_token}")
    print("===================================================")
    print("Guarda ese valor como secret (p. ej. GMAIL_REFRESH_TOKEN_GBS01).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
