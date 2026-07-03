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
└── .env            # ANTHROPIC_API_KEY, SUPABASE_URL, NETLIFY_TOKEN
```

## Rutas importantes

- Clientes: `C:\Users\Admin\OneDrive\Documents\Con Prospección\CLIENTES OS\CLIENTES\`
- GitHub: https://github.com/FranciscaPP/conprospeccion-os (carpeta `mvp_setup/`)
- App corriendo en: http://localhost:8501

## Python correcto

`C:\Users\Admin\AppData\Local\Python\pythoncore-3.14-64\python.exe`

## Parte de ConprospecciónOS

Este proyecto es un módulo dentro de `ConprospeccionOS/` (el sistema operativo central de ConProspección). No edites archivos en la carpeta antigua `CLIENTES OS\ConprospeccionOS\`.
