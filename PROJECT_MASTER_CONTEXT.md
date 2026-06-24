# Contexto maestro del proyecto

## Decisión vigente

El producto oficial de Conprospección OS2026 se desarrolla y mantiene únicamente en **Streamlit**.

La entrada principal es:

```text
dashboard/app.py
```

## Workspace activo

Estas son las únicas carpetas de producto que deben analizarse por defecto:

- `dashboard/`: aplicación Streamlit, páginas, autenticación y assets.
- `shared/`: configuración y lógica Python compartida.
- `sync/`: sincronización operativa con las fuentes de datos.
- `supabase/`: migraciones y funciones de infraestructura.
- `tests/`: pruebas del código Python activo.

Antes de abrir muchos archivos, consultar `graphify-out/` mediante `graphify query`, según las reglas de `AGENTS.md`.

## Archivo histórico

`archive/` contiene implementaciones descartadas, prototipos y herramientas históricas.

Regla obligatoria:

> No analizar, buscar, modificar ni usar código de `archive/` salvo que el usuario lo solicite explícitamente.

El contenido de `archive/` no forma parte de la arquitectura activa y no debe emplearse como referencia automática para implementar cambios.

## Next.js y Vercel

Next.js, React, Vercel y los despliegues asociados quedan descartados como implementación actual.

Si en el futuro se decide volver a Vercel:

- se construirá una aplicación nueva desde cero;
- solo se rescatarán reglas de negocio o decisiones de UX previamente validadas;
- no se reactivará ni copiará automáticamente el código heredado de `archive/`.

## Límites de trabajo

- No rediseñar la interfaz sin petición explícita.
- No refactorizar lógica fuera del objetivo solicitado.
- No tocar integraciones o datos externos sin autorización.
- No borrar archivos sin aprobación.
- No ampliar búsquedas a carpetas históricas para responder preguntas del producto activo.

