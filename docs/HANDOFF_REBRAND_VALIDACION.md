# Handoff — Rebrand premium "Validación de reuniones" (Conprospección OS)

Re-skin visual (sin tocar lógica) de la vista cliente `app/client/meeting-validation` y de los
componentes/tokens compartidos, con la marca oficial de Conprospección.

## Marca oficial (brand guidelines)
- Colores: Gold `#ffd700` · Carbon `#333333` · White `#ffffff`.
- Regla del oro: SOLO acento (logo, nav activo, barra de progreso de meta). Nunca texto dorado
  sobre blanco ni texto blanco sobre dorado. Botón primario = Carbon `#333` con texto blanco.
- Neutros: `--canvas #f6f6f4 · card #fff · line #ececea · ink #1a1a1a · ink-2 #6a6a64 · ink-3 #9a9a92`.
- Estados: válida `#0e9f6e` (bg `#e7f6f0`/ink `#0a6e4d`) · pendiente `#b06a00` (bg `#fbf1df`/ink `#8a5300`)
  · no válida `#c0362c` (bg `#fbeae8`/ink `#962a22`) · en revisión `#cf7320` (bg `#fdf0e6`/ink `#9a5418`).
- Sombra de tarjeta: `0 1px 2px rgba(20,20,20,.05), 0 1px 3px rgba(20,20,20,.04)`.

## Tipografía
- Display + números: **Saira Condensed** (500/600/700) vía `next/font/google` (`--font-saira`),
  sustituta legal de TT Lakes Condensed. Números con `tabular-nums` (clase `.tnum`).
- Cuerpo/UI: **Inter**.

## Archivos tocados
- `app/layout.tsx` — Space_Grotesk → Saira_Condensed (`--font-saira`).
- `app/globals.css` — tokens de marca, `--background #f6f6f4`, `--primary #333`, `--font-display` = Saira,
  barra de progreso dorada, utilidades `.font-display/.tnum/.shadow-card`, `body` font-feature-settings.
- `components/company-avatar.tsx` — NUEVO (iniciales + color por hash de nombre).
- `components/kpi-card.tsx` — tarjeta blanca + chip de ícono por estado + número condensado (API intacta).
- `components/status-badge.tsx` — pill con punto de color por estado (mapeo de estado conservado).
- `components/sidebar.tsx` — fondo carbón `#2b2b2b`, isotipo + wordmark + subtítulo, nav activo dorado.
- `app/client/meeting-validation/page.tsx` — avatares de empresa, título/números en `font-display tnum`,
  botón "Validar" carbón, progreso dorado, violeta neutralizado.
- `public/conprospeccion-isotype.png` + `public/conprospeccion-logo-dark.png` — extraídos del manual de marca.

## Replicación
Todo vive en componentes + tokens compartidos: `performance-overview` e `intelligence-insight`
heredan KPI/badges/sidebar/tipografía sin editarlas.

## Verificación
- `npx tsc --noEmit`: 0 errores. `npm run build`: OK (9 rutas).
- `npm run lint`: el binario `eslint` NO está instalado como dependencia del repo (pre-existente);
  el chequeo de TypeScript del build cubre tipos. Pendiente: agregar eslint si se quiere lint dedicado.

## Pendiente (siguiente paso acotado)
- `components/meeting-drawer.tsx` (panel de detalle) aún usa acentos violeta (~20 usos:
  botones de footer, pills de "Tu validación", íconos de secciones, chips BANT). Falta el mismo
  pase de marca para que el panel quede 100% on-brand.
