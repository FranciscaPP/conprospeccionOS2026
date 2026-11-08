# Alta de Gmail para Alicia · Google Workspace (dominio gbs-logistics.cl)

La organización bloquea la descarga de claves de cuenta de servicio (política
`iam.disableServiceAccountKeyCreation`). Por eso usamos el camino **sin claves**:
**OAuth con un refresh token por casilla**. No crea ninguna clave descargable, así
que respeta la política de seguridad tal cual está.

**Casillas del piloto (GBS):**
- `sam.miller@gbs-logistics.cl` → `gbs01`
- `sammiller@gbs-logistics.cl` → `gbs02`
- `sam@gbs-logistics.cl` → `gbs03`

**Permisos (scopes):**
- `https://www.googleapis.com/auth/gmail.modify` (leer y marcar como leído)
- `https://www.googleapis.com/auth/gmail.send` (responder en el mismo hilo)

Se hace una vez por casilla (3 veces). Puede hacerlo quien tenga acceso a cada
casilla; no requiere super admin salvo el paso 1-2 de configurar la credencial.

---

## Parte A · Crear la credencial OAuth (una sola vez)

1. Entra a <https://console.cloud.google.com> con una cuenta del dominio y crea o
   elige un proyecto (p. ej. **"Alicia GBS"**). Habilita **Gmail API**
   (APIs y servicios → Biblioteca → "Gmail API" → Habilitar).
2. **APIs y servicios → Pantalla de consentimiento de OAuth**:
   - Tipo de usuario: **Interno** (Internal) — solo cuentas de `gbs-logistics.cl`.
     Así no requiere verificación de Google.
   - Completa nombre de la app (p. ej. "Alicia") y correo de contacto → Guardar.
3. **APIs y servicios → Credenciales → Crear credenciales → ID de cliente de
   OAuth**:
   - Tipo de aplicación: **Aplicación de escritorio** (Desktop app).
   - Nombre: `alicia-desktop` → **Crear**.
   - Copia el **ID de cliente** y el **secreto de cliente** (client_id / client_secret).
     Esto NO es una clave de service account: es un cliente OAuth, permitido por la
     política.

## Parte B · Generar un refresh token por casilla (3 veces)

En un equipo con navegador y Python:

```bash
pip install google-auth-oauthlib
export GMAIL_OAUTH_CLIENT_ID=...        # de la Parte A.3
export GMAIL_OAUTH_CLIENT_SECRET=...
python alicia/tools/get_gmail_refresh_token.py
```

- Se abre el navegador → **inicia sesión con la casilla objetivo** (la primera vez
  `sam.miller@gbs-logistics.cl`) → acepta los permisos.
- El script imprime la cuenta autorizada y su `GMAIL_REFRESH_TOKEN`.
- Repite iniciando sesión con cada una de las otras dos casillas.

> Consejo: hazlo en ventanas de incógnito distintas, o cierra sesión entre cada
> una, para no autorizar la casilla equivocada. El script te dice qué cuenta
> autorizaste, verifícalo.

## Parte C · Cargar como secrets (no en el repo ni por chat)

En **GitHub → repo `conprospeccionOS2026` → Settings → Secrets and variables →
Actions → New repository secret**:

| Secret | Valor |
|---|---|
| `GMAIL_OAUTH_CLIENT_ID` | client_id de la Parte A.3 |
| `GMAIL_OAUTH_CLIENT_SECRET` | client_secret de la Parte A.3 |
| `GMAIL_REFRESH_TOKEN_GBS01` | refresh token de `sam.miller@gbs-logistics.cl` |
| `GMAIL_REFRESH_TOKEN_GBS02` | refresh token de `sammiller@gbs-logistics.cl` |
| `GMAIL_REFRESH_TOKEN_GBS03` | refresh token de `sam@gbs-logistics.cl` |
| `TELEGRAM_CHAT_ID` | id del chat/grupo de Telegram para las alertas |

Avísanos cuando estén cargados. Activamos el piloto en modo prueba
(`ALICIA_DRY_RUN=true`: detecta y alerta, aún sin responder correos).

---

## Verificación (la hacemos nosotros)

- Ejecución manual del poller → **una alerta agrupada a Telegram** con las
  respuestas reales de las 3 casillas (o "sin respuestas nuevas").

## Seguridad y revocación

- Los refresh tokens son sensibles: van solo a Secrets. Se pueden **revocar** en
  cualquier momento desde la cuenta de Google (Seguridad → Accesos de terceros) o
  borrando el cliente OAuth.
- Alicia solo actúa sobre las casillas declaradas en su configuración.

> Si en el futuro se prefiere el modo service account (una sola credencial, sin
> token por cuenta), requiere levantar la política `disableServiceAccountKeyCreation`
> o usar Workload Identity Federation. El código ya soporta ambos modos.
