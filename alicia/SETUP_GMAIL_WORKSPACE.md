# Alta de Gmail para Alicia · Google Workspace (dominio gbs-logistics.cl)

Guía paso a paso para habilitar que Alicia lea y responda las respuestas de
campañas Snov en las casillas del dominio, usando **una sola credencial**
(cuenta de servicio con delegación en todo el dominio). No hay que autorizar
casilla por casilla.

**Quién lo hace:** un **super administrador** de Google Workspace de
`gbs-logistics.cl` (los pasos de la Parte B requieren la consola de administración).

**Casillas del piloto:**
- `sam.miller@gbs-logistics.cl`
- `sammiller@gbs-logistics.cl`
- `sam@gbs-logistics.cl`

**Permisos (scopes) que se otorgarán:**
- `https://www.googleapis.com/auth/gmail.modify` (leer y marcar como leído)
- `https://www.googleapis.com/auth/gmail.send` (responder en el mismo hilo)

---

## Parte A · Google Cloud (crear la credencial)

1. Entra a <https://console.cloud.google.com> con una cuenta del dominio.
2. Arriba, crea o selecciona un proyecto (p. ej. **"Alicia GBS"**).
3. Menú **APIs y servicios → Biblioteca** → busca **"Gmail API"** → **Habilitar**.
4. Menú **APIs y servicios → Credenciales** → **Crear credenciales → Cuenta de
   servicio**.
   - Nombre: `alicia-gmail` (o el que prefieras) → **Crear y continuar** →
     puedes omitir roles → **Listo**.
5. Abre la cuenta de servicio recién creada → pestaña **Claves** → **Agregar
   clave → Crear clave nueva → JSON** → se descarga un archivo `.json`.
   **Ese archivo es la credencial: guárdalo seguro, no lo compartas por chat.**
6. En la misma cuenta de servicio, copia el **"ID único"** (Unique ID): es un
   número largo (p. ej. `1234567890...`). Es el **Client ID** que se usa en la
   Parte B. También aparece dentro del JSON como `"client_id"`.

---

## Parte B · Consola de administración (autorizar el dominio)

> Requiere super admin. <https://admin.google.com>

1. **Seguridad → Controles de API → Delegación de todo el dominio**
   (Security → API controls → Domain-wide delegation).
2. **Agregar nuevo** (Add new).
3. **ID de cliente** (Client ID): pega el **ID único** de la cuenta de servicio
   (paso A.6).
4. **Ámbitos de OAuth** (OAuth scopes): pega EXACTAMENTE, separados por coma:
   ```
   https://www.googleapis.com/auth/gmail.modify,https://www.googleapis.com/auth/gmail.send
   ```
5. **Autorizar** (Authorize).

Con esto, la credencial queda habilitada para actuar sobre las casillas del
dominio que Alicia tenga declaradas (solo esas tres del piloto).

---

## Parte C · Entregar a Conprospección (para conectar Alicia)

Cargar como **secrets** (no en el repositorio ni por chat):

1. En **GitHub → repo `conprospeccionOS2026` → Settings → Secrets and variables
   → Actions → New repository secret**:
   - `GMAIL_SERVICE_ACCOUNT_JSON` = **el contenido completo del archivo JSON** de
     la Parte A.5.
   - `TELEGRAM_CHAT_ID` = el id del chat/grupo de Telegram donde llegan las alertas.
2. Avísanos cuando estén cargados. Nosotros activamos el piloto en modo prueba
   (`ALICIA_DRY_RUN=true`: detecta y alerta, todavía sin responder correos).

---

## Verificación (la hacemos nosotros)

- Ejecución manual del poller → debe llegar **una alerta agrupada a Telegram**
  con las respuestas reales de las 3 casillas (o "sin respuestas nuevas").
- Si algo falla, el error más común es que la delegación (Parte B) tarde unos
  minutos en propagarse, o que falte alguno de los dos scopes.

## Notas de seguridad

- El JSON de la cuenta de servicio es sensible: va solo a Secrets. Se puede
  **revocar** en cualquier momento borrando la clave (Parte A.5) o la delegación
  (Parte B).
- Alicia solo actúa sobre las casillas declaradas explícitamente en su
  configuración, no sobre todo el dominio.
