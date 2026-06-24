# Archive Report

Fecha: 2026-06-18

## Objetivo

Separar del contexto activo el código Next.js, artefactos de despliegue y prototipos visuales, manteniendo intacta la aplicación Streamlit y sin eliminar archivos.

## Resumen

- Archivos movidos: 72
- Tamaño movido: 1.554.726 bytes
- Archivos eliminados: 0
- Destino: `archive/`

## Directorios movidos

| Origen | Destino | Archivos | Contenido |
|---|---|---:|---|
| `app/` | `archive/app/` | 15 | Next.js App Router, páginas y API routes |
| `components/` | `archive/components/` | 22 | Componentes React y componentes UI |
| `lib/` | `archive/lib/` | 7 | Tipos, reglas y acceso a datos de Next.js |
| `public/` | `archive/public/` | 15 | Assets y prototipos públicos de Next.js |
| `netlify-preview/` | `archive/netlify-preview/` | 6 | Preview estático de Netlify |
| `whatsapp_check/` | `archive/whatsapp_check/` | 3 | Script y exportaciones locales de WhatsApp |

Los cambios locales que existían dentro de `app/`, `components/` y `lib/` fueron movidos junto con sus archivos, sin descartarlos.

## Prototipos visuales movidos

| Origen | Destino |
|---|---|
| `docs/meeting-validation-interactive-flow.html` | `archive/prototypes/docs/meeting-validation-interactive-flow.html` |
| `docs/meeting-validation-option-1-full.html` | `archive/prototypes/docs/meeting-validation-option-1-full.html` |
| `docs/meeting-validation-visual-examples.html` | `archive/prototypes/docs/meeting-validation-visual-examples.html` |
| `preview-premium.html` | `archive/prototypes/root/preview-premium.html` |

## Inventario auxiliar

### `archive/netlify-preview/`

- `docs/data/gbs-manual-meetings.json`
- `docs/data/gbs-meeting-evidence.json`
- `docs/data/gbs-meetings.json`
- `docs/meeting-validation-interactive-flow.html`
- `index.html`
- `public/conprospeccion-isotype.png`

### `archive/whatsapp_check/`

- `BAMBUTECH_EXPORTADOS.csv`
- `BAMBUTECH_EXPORTADOS_whatsapp.csv`
- `check_whatsapp_bambutech.py`

## Elementos preservados

No se movió ni eliminó contenido de:

- `dashboard/`
- `shared/`
- `sync/`
- `supabase/`
- `tests/`

Los mockups `dashboard/mockup_portal.html` y `dashboard/mockup_portal_template.html` permanecen en su ubicación porque la fase indicó expresamente no tocar `dashboard/`.

## Observaciones

- Fue necesario detener el servidor local `next dev`, ya que mantenía bloqueada la carpeta `app/`.
- Los archivos de configuración y dependencias Node de la raíz no se movieron porque no estaban incluidos en las acciones autorizadas.
- El contenido archivado permanece disponible para consulta o restauración.
