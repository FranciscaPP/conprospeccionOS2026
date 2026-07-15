# MVP Setup CP — Contexto del proyecto

App Streamlit (puerto 8501) para onboarding operativo de clientes B2B en ConprospecciónOS.

## Estructura

```
mvp_setup/
├── app.py          # Entry point Streamlit
├── config.py       # Configuración y rutas
├── modules/
│   ├── estructura.py   # Crea carpetas del cliente
│   ├── archivos.py     # Genera 47 archivos base
│   ├── firma.py        # Genera firma HTML de email
│   ├── estado.py       # Estado JSON del proyecto
│   └── templates.py    # Plantillas de contenido
└── .env            # ANTHROPIC_API_KEY, SUPABASE_URL
```

## Rutas importantes

- Repo oficial ÚNICO: https://github.com/FranciscaPP/conprospeccionOS2026 (carpeta `mvp_setup/`)
- App corriendo en: http://localhost:8501

> El repo antiguo `conprospeccion-os` (sin `2026`) quedó obsoleto. No usarlo.
> La única fuente de verdad es `conprospeccionOS2026` y el documento
> `PROJECT_MASTER_CONTEXT.md` en su raíz.

## Python correcto

`C:\Users\Admin\AppData\Local\Python\pythoncore-3.14-64\python.exe`

## Parte de ConprospecciónOS

Este proyecto es un módulo dentro del repo oficial `conprospeccionOS2026` (el
sistema operativo central de ConProspección). La fuente única de verdad es
`PROJECT_MASTER_CONTEXT.md` en la raíz del repo. No trabajar sobre el repo ni
las carpetas antiguas `conprospeccion-os` / `CLIENTES OS\ConprospeccionOS\`.
