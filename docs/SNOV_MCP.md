# Snov.io MCP

Servidor MCP remoto de Snov.io conectado como herramienta para el asistente de
IA (Claude Code / Claude Desktop). Complementa —no reemplaza— la integracion por
API Pro que ya alimenta Supabase (`sync/scripts/snov_client.py`,
`sync/scripts/sync_snov.py` y las migraciones `010`→`013`).

## Diferencia con el sync por API

- **API Pro (batch):** corre en el workflow `sync-commercial-data.yml`, escribe
  campanas, metricas, eventos y prospectos en Supabase. Es la fuente para las
  reporterias del dashboard. No cambia.
- **MCP (interactivo):** deja que el asistente consulte y opere Snov.io en vivo
  (busqueda/enriquecimiento de prospectos, CRM, LinkedIn, +100 acciones) durante
  una conversacion. No persiste en Supabase por si mismo.

## Configuracion (ya versionada)

El servidor esta declarado en `.mcp.json` en la raiz del repo:

```json
{
  "mcpServers": {
    "snovio": {
      "type": "http",
      "url": "https://mcp.snov.io/mcp"
    }
  }
}
```

- Endpoint: `https://mcp.snov.io/mcp` (Streamable HTTP).
- Auth: OAuth 2.0 (authorization server `https://app.snov.io`, scope `mcp`,
  PKCE S256 + Dynamic Client Registration). No se guardan API keys en el repo;
  la autorizacion es por login del usuario.

## Conectar (paso interactivo, una sola vez)

La autorizacion OAuth es interactiva y **no** puede hacerse en un entorno
remoto/CI sin navegador. En tu cliente:

- **Claude Code (CLI):** al abrir el repo, aprueba el servidor `snovio` del
  `.mcp.json`, luego corre `/mcp` y elige **Authenticate** para el login de Snov.
- **Claude Desktop:** Settings → Conectores → Anadir conector personalizado →
  nombre `Snovio MCP`, URL `https://mcp.snov.io/mcp` → Connect with Snov.io →
  autorizar.

Referencia oficial: https://snov.io/knowledgebase/es/como-utilizar-snov-io-mcp-con-tu-asistente-de-ia/
