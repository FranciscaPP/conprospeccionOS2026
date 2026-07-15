# Dashboard — App Streamlit (producto oficial)

Esta carpeta es la aplicación Streamlit oficial de Conprospección OS 2026.

- Entrada principal: `app.py`
- Panel maestro interno: `pages/1_Seguimiento_Reuniones.py`
- Portales de cliente: `client_meeting_portal.py` + `pages/12_GBS.py` (GBS en `/GBS`)
- URL pública: https://conprospeccion-os2026.streamlit.app

## Fuente única de verdad

Toda la orientación del proyecto (mapa, reglas, deploy, ramas) vive en
**`PROJECT_MASTER_CONTEXT.md`** en la raíz del repo. Léelo primero.

Repo oficial ÚNICO: `FranciscaPP/conprospeccionOS2026`, rama `main`. Streamlit
Cloud despliega desde ahí. El repo antiguo `conprospeccion-os` (sin `2026`)
quedó obsoleto y no debe usarse.
