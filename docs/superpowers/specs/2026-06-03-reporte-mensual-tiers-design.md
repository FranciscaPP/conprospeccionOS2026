# Reporte Mensual + Modelo por Tiers — System Design

**Fecha:** 2026-06-03 · **Autor:** Francisca Polanco · Conprospección
**Estado:** Diseño — listo para plan de implementación

## 1. Requisitos

**Funcionales**
- Página cliente **"Generar Reporte Mensual"**: elegir **5 de 15 KPIs**, guardar la selección, generar y **descargar un PDF branded** del mes (respetando período).
- Renombrar **Indicadores → "Intelligence Insight"**, premium/interno (no visible al cliente base).
- **Control de acceso por tier**: cada cliente tiene un plan (`base` / `premium`) que define qué páginas ve.

**No funcionales**
- Streamlit Cloud: Plotly/Altair fallan → UI en HTML/CSS; **PDF con `fpdf2`** (Python puro, funciona en Cloud).
- Escala chica (pocos clientes), cadencia mensual. Un solo `.env`, Supabase.
- Español neutro, paleta GBS, sin nombres de plataformas.

## 2. Diseño de alto nivel

```
                 shared/kpis.py  (catálogo único de 15 KPIs)
                        │  cada KPI = {id, label, grupo, fn(df,periodo)->valor/render}
                        ▼
  pages/15_GBS_Reporte_Mensual.py        shared/planes.py (tier por cliente)
   ├─ multiselect 5 de 15 (del catálogo)        │
   ├─ guardar selección → reporte_config        ▼
   └─ "Generar PDF" → shared/pdf_report.py → bytes → st.download_button
                                  │ fpdf2: header GBS + logos + 5 KPIs + footer CP
  portal_auth.render_client_nav  ──filtra páginas por plan──> base: Validación + Reporte
                                                              premium: + Intelligence Insight
```

## 3. Componentes (una responsabilidad c/u)

- **`shared/kpis.py`** — catálogo de los 15 KPIs. Cada uno: `id`, `label`, `grupo` (Volumen/Resultados/Estratégicos), `compute(df, periodo)`. Fuente única que usan tanto Intelligence Insight como el PDF (DRY).
- **`shared/planes.py`** — `PLANES = {"gbs": "base", ...}` + `plan_de(slug)`. Constante versionada (como `metas.py`). *(Trade-off abajo.)*
- **`shared/pdf_report.py`** — `construir_pdf(cliente, periodo, kpis_sel, df) -> bytes` con fpdf2. Branded (logo GBS + Conprospección, período, tarjetas KPI, footer).
- **`pages/15_GBS_Reporte_Mensual.py`** — UI: selección (máx 5), guardar (upsert), generar/exportar PDF.
- **`portal_auth.py`** — `render_client_nav` filtra `cfg["nav"]` por plan; guard opcional en páginas premium.
- **`dashboard/pages/11_GBS.py`** — rename de cabecera/nav a "Intelligence Insight".

## 4. Modelo de datos

Tabla **`reporte_config`** (selección de KPIs por cliente):
```sql
CREATE TABLE public.reporte_config (
  cliente_slug text PRIMARY KEY,
  kpis         text,          -- csv de hasta 5 ids de KPI, ej "contactos,respuestas,positivas,validas,proximos_pasos"
  updated_at   timestamptz DEFAULT now()
);
```
Plan/tier: **`shared/planes.py`** (constante). Migrable a `clientes.tier` más adelante si se quiere editar sin deploy.

## 5. Catálogo de 15 KPIs (cliente elige 5)

| Grupo | id | Label |
|---|---|---|
| Volumen | `contactos` | Contactos trabajados |
| Volumen | `empresas` | Empresas impactadas |
| Volumen | `respuestas` | Respuestas |
| Volumen | `tasa_respuesta` | Tasa de respuesta |
| Volumen | `cobertura_pais` | Cobertura por país |
| Resultados | `positivas` | Respuestas positivas |
| Resultados | `agendadas` | Reuniones agendadas |
| Resultados | `validas` | Reuniones válidas |
| Resultados | `avance_meta` | % avance de meta |
| Resultados | `conversion` | Conversión (reuniones/contactos) |
| Estratégico | `top_industria` | Top industria |
| Estratégico | `top_cargo` | Top cargo |
| Estratégico | `top_canal` | Top canal |
| Estratégico | `motivos` | Motivos de rechazo (resumen) |
| Estratégico | `proximos_pasos` | Próximos pasos sugeridos |

Numéricos → valor + sub; estratégicos → texto corto. El PDF renderiza cada uno como tarjeta.

## 6. Flujo de datos

1. Cliente abre Reporte Mensual → carga catálogo + selección guardada (`reporte_config`).
2. Ajusta selección (máx 5) → **Guardar** (upsert a `reporte_config`).
3. **Generar PDF**: se computa cada KPI seleccionado desde el dataset del período (mismo origen que Intelligence Insight) → `pdf_report.construir_pdf(...)` → bytes → `st.download_button`.

## 7. Control de acceso por tier

- `render_client_nav` recibe el plan (`plan_de(slug)`) y arma la nav:
  - **base** → `Validación de Reuniones`, `Generar Reporte Mensual`, `Onboarding`.
  - **premium** → + `Intelligence Insight`.
- Guard defensivo opcional: cada página premium verifica el plan al inicio (evita acceso por URL directa). Para Streamlit, basta ocultar de la nav + un `st.stop()` con aviso si el plan no corresponde.

## 8. Trade-offs

- **Plan como constante (`shared/planes.py`) vs columna `clientes.tier`:** constante = simple, versionado, requiere deploy para cambiar; columna = editable en vivo. → **Constante ahora**, migrar a columna si crece la operación.
- **KPIs computados on-demand vs snapshot mensual:** on-demand = simple, siempre fresco; snapshot = consistencia/velocidad y "sello mensual". → **On-demand ahora**; el snapshot mensual es la Fase 2c (cuando haya volumen real).
- **`fpdf2` vs HTML→print:** fpdf2 da un PDF real descargable y controlado, sin depender del navegador. → **fpdf2** (agregar a `requirements.txt`).
- **Catálogo KPIs compartido vs duplicado:** compartido (`shared/kpis.py`) evita que el PDF y el dashboard diverjan. → **Compartido**.

## 9. Qué revisaría al crecer

- Mover el dataset GBS demo a un loader compartido (`shared/`) para que KPIs/PDF/dashboard usen exactamente la misma fuente (hoy el dataset vive en `11_GBS`).
- Plan/tier a columna en `clientes` + UI interna para cambiarlo.
- Snapshot mensual (`indicadores_semanal`/`reporte_mensual`) para "congelar" el período entregado.
