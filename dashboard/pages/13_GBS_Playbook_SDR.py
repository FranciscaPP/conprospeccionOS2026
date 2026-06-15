"""Portal GBS Logistics — Playbook SDR interactivo."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_DIR = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DASHBOARD_DIR))

import streamlit as st
from portal_auth import require_auth_client, render_client_nav, img_b64
from shared.gbs_brand import GBS_PURPLE, GBS_PURPLE_BG, GBS_BORDER_2

st.set_page_config(page_title="GBS Logistics — Playbook SDR", layout="wide", page_icon="")

if not require_auth_client("gbs"):
    st.stop()

render_client_nav("13_GBS_Playbook", "gbs")

# ── Colores (paleta de marca desde shared/gbs_brand) ──────────────────────────
BLUE = GBS_PURPLE # morado de marca
DARK = "#0f172a"
LIGHT = GBS_PURPLE_BG # #f5f3ff
BORDER = GBS_BORDER_2 # #ddd6fe

# ══════════════════════════════════════════════════════════════════════════════
# DATA: 5 segmentos del ICP de GBS Logistics
# ══════════════════════════════════════════════════════════════════════════════
SEGMENTOS = [
    {
        "id": 1,
        "label": "1 — Minería, Repuestos y Proveedores Mineros",
        "industria": "Mining & Metals · Proveedores de minería · Repuestos industriales",
        "cargo": "Gerente de Logística · Supply Chain Manager · Jefe de Importaciones",
        "prioridad": "Alta",
        "contactos": 420,
        "keywords": ["Repuestos críticos", "Componentes", "Aduana minera", "FCL/LCL desde Asia", "Operación crítica"],
        "dolor": "Retrasos y falta de visibilidad en cargas críticas. Un repuesto que no llega a tiempo para la operación puede costar mucho más que el flete.",
        "cosas_hechas": "Importación de repuestos críticos para minería con coordinación puerta a puerta desde China, USA y Alemania. Manejo de carga urgente aérea cuando el marítimo falla.",
        "frase_guia": "En minería, el dolor no es el precio del flete — es la certeza. ¿Qué pasa si el repuesto no llega a tiempo? GBS da visibilidad y hace que ese problema deje de ser tuyo.",
        "apertura": "¿Ustedes importan repuestos, componentes o equipos de forma recurrente para la operación?",
        "preguntas": [
            "¿Qué repuestos o componentes importan con más frecuencia?",
            "¿Qué pasa operacionalmente cuando una carga crítica se retrasa?",
            "¿Hoy trabajan con un solo forwarder o con varios proveedores?",
            "¿Quién coordina la aduana y el transporte hasta el destino final?",
        ],
        "objeciones": [
            ("Ya tenemos forwarder", "Perfecto. La conversación no busca reemplazarlo de inmediato, sino quedar como alternativa para rutas, urgencias o puerta a puerta donde hoy pueden tener un punto débil."),
            ("Solo cotizamos por precio", "Tiene sentido. Para operaciones recurrentes normalmente el precio de flete es una parte — la otra es cuánto cuesta un retraso aduanero o una coordinación fallida. ¿Cuánto les afecta eso hoy?"),
            ("No soy la persona", "Gracias. ¿Me puede decir quién ve comercio exterior, logística internacional o abastecimiento para contactarlos directamente?"),
            ("Estamos bien", "Buenísimo. ¿Tendría sentido quedar como segunda opción para cargas urgentes o rutas donde hoy no tienen cobertura óptima?"),
        ],
        "speech1": (
            "¿Hablo con [Nombre]? Soy [SDR] de GBS Logistics. Muy breve.\n\n"
            "Trabajamos con empresas del sector minero que importan repuestos y componentes críticos de forma recurrente. "
            "En esas operaciones el problema más frecuente no es el precio del flete — es la visibilidad: saber exactamente dónde está la carga, "
            "qué pasa con la documentación en aduana y si va a llegar a tiempo cuando la operación lo necesita.\n\n"
            "GBS coordina todo: flete marítimo/aéreo, aduana, seguro, transporte local y seguimiento — un solo interlocutor de principio a fin.\n\n"
            "¿Ustedes hoy manejan importaciones de forma recurrente?\n\n"
            "PREGUNTAS SUGERIDAS: ¿Qué tan críticos son los tiempos para ustedes? / ¿Trabajan con un forwarder o con varios? / ¿Quién coordina la aduana y la entrega final?"
        ),
        "speech2": (
            "Hola [Nombre], soy [SDR] de GBS Logistics. ¿Tienen un minuto?\n\n"
            "Quería validar si [Empresa] importa repuestos o equipos de forma recurrente. "
            "Trabajamos con proveedores y operaciones del sector minero donde la certeza en los tiempos de entrega es crítica — "
            "especialmente cuando el componente está parado esperando llegar a faena.\n\n"
            "GBS actúa como socio logístico integral: flete, aduana, seguro y puerta a puerta. No tiene que coordinar con tres proveedores distintos.\n\n"
            "¿Hoy trabajan con un forwarder, coordinan directo con el proveedor o tienen equipo interno de COMEX?\n\n"
            "PREGUNTAS SUGERIDAS: ¿Desde qué países importan principalmente? / ¿FCL, LCL o aéreo? / ¿Qué parte del proceso les genera más fricción?"
        ),
        "speech3": (
            "Hola [Nombre], soy [SDR], te llamo de GBS Logistics.\n\n"
            "En empresas de minería y repuestos industriales, el desafío más común que nos llega "
            "es que tienen un forwarder para el flete pero el resto — aduana, seguro, transporte hasta el destino final, "
            "el seguimiento cuando algo se retrasa — queda en manos del equipo interno que ya tiene demasiadas cosas.\n\n"
            "GBS cubre toda esa operación como un solo proveedor, con trazabilidad y respuesta directa.\n\n"
            "¿Tienen hoy alguna ruta o tipo de carga donde sientan que falta coordinación o visibilidad?\n\n"
            "PREGUNTAS SUGERIDAS: ¿Cuántos embarques manejan al mes? / ¿Cuántas personas internas coordinan esto? / ¿Último problema que tuvieron con una carga?"
        ),
        "email": (
            "Asunto: Apoyo logístico para importaciones recurrentes en [Empresa]\n\n"
            "Hola [Nombre],\n\n"
            "Soy [SDR] de GBS Logistics. Apoyamos a empresas del sector minero y de repuestos industriales con importaciones recurrentes "
            "de componentes, maquinaria y equipos desde China, USA, España o Alemania.\n\n"
            "En operaciones donde los tiempos son críticos, el dolor no suele ser el precio del flete — es la coordinación entre "
            "el proveedor, la aduana, el seguro y el transporte final. GBS centraliza todo eso en un solo interlocutor.\n\n"
            "¿Tendría sentido una reunión breve de 20 minutos para revisar si hay algo que podamos mejorar en su operación actual?"
        ),
        "whatsapp": "Hola [Nombre], GBS apoya importaciones de repuestos críticos con flete, aduana, seguro y puerta a puerta. ¿Tú ves logística o COMEX en [Empresa]?",
    },
    {
        "id": 2,
        "label": "2 — Maquinaria y Equipamiento Industrial",
        "industria": "Industrial Machinery & Equipment · Automatización · Componentes técnicos",
        "cargo": "Encargado de Comercio Exterior · Import Manager · Jefe de Compras",
        "prioridad": "Alta",
        "contactos": 380,
        "keywords": ["Maquinaria importada", "Componentes técnicos", "FCL desde Asia", "PO Management", "Proveedor único"],
        "dolor": "Coordinación con proveedores, documentación, aduana y entrega final dispersa entre múltiples proveedores. Carga operativa en el equipo de COMEX.",
        "cosas_hechas": "Importación de maquinaria industrial y líneas de producción desde China, Alemania e Italia. Coordinación de aduana técnica y transporte hasta planta.",
        "frase_guia": "Cuando la maquinaria tiene que llegar para arrancar producción, no hay margen para errores de coordinación. GBS centraliza todo para que el equipo de COMEX no tenga que manejar 4 proveedores distintos.",
        "apertura": "¿Ustedes importan maquinaria, equipos o componentes técnicos de forma recurrente?",
        "preguntas": [
            "¿Desde qué países importan principalmente?",
            "¿FCL, LCL o mixto? ¿Tienen carga aérea también?",
            "¿Qué parte del proceso les genera más trabajo interno: la aduana, el flete o el transporte final?",
            "¿Tienen contrato fijo con su forwarder actual o van cotizando por embarque?",
        ],
        "objeciones": [
            ("Estamos bien con nuestro proveedor actual", "Tiene sentido. ¿Tendría sentido quedar como segunda opción para comparar en el próximo embarque o para rutas donde hoy no tienen la mejor cobertura?"),
            ("Mándame información", "Claro. Para enviarte algo útil: ¿qué tipo de maquinaria/componentes importan y desde qué países? Así te mando algo relevante, no genérico."),
            ("No tenemos volumen suficiente", "No necesariamente. GBS trabaja con empresas desde 1 FCL mensual. ¿Cuántos embarques manejan al año?"),
            ("El precio es lo más importante", "Totalmente. ¿Calculan también el costo de los retrasos o los errores de documentación? En maquinaria industrial eso suele ser significativo."),
        ],
        "speech1": (
            "¿Hablo con [Nombre]? Soy [SDR] de GBS Logistics. ¿Tienes un minuto?\n\n"
            "Trabajamos con empresas que importan maquinaria, equipos industriales o componentes técnicos de forma recurrente. "
            "En ese tipo de operaciones lo que más vemos es que el equipo de COMEX o de compras termina coordinando "
            "con el proveedor en origen, el forwarder, la aduana y el transporte final por separado — mucho tiempo interno gastado.\n\n"
            "GBS centraliza todo eso: flete desde origen, aduana, seguro, transporte hasta planta.\n\n"
            "¿Ustedes hoy importan maquinaria o componentes de forma regular?\n\n"
            "PREGUNTAS SUGERIDAS: ¿Desde qué países importan? / ¿FCL o LCL principalmente? / ¿Quién coordina la aduana y el transporte final?"
        ),
        "speech2": (
            "Hola [Nombre], soy [SDR] de GBS Logistics.\n\n"
            "Importar maquinaria o equipos industriales tiene una complejidad particular: "
            "documentación técnica, certificaciones, transporte especializado y aduana. "
            "Cuando todo eso no está coordinado en un solo proveedor, el equipo interno absorbe esa carga.\n\n"
            "GBS actúa como el socio logístico que maneja todo de punta a punta — "
            "incluyendo PO management si necesitan esa visibilidad desde el proveedor en origen.\n\n"
            "¿Tienen hoy alguna importación recurrente donde puedan estar pagando de más en tiempo o coordinación?\n\n"
            "PREGUNTAS SUGERIDAS: ¿Cuántas personas internamente coordinan las importaciones? / ¿Qué parte toma más tiempo? / ¿Último problema que tuvieron?"
        ),
        "speech3": (
            "Hola [Nombre], te llamo de GBS Logistics. Muy breve.\n\n"
            "Quería validar si [Empresa] importa maquinaria o componentes técnicos. "
            "Trabajamos con empresas industriales que necesitan certeza en los tiempos de entrega "
            "porque la maquinaria tiene que llegar cuando la producción lo requiere, no cuando el forwarder se organice.\n\n"
            "¿Hoy trabajan con un forwarder fijo o van cotizando embarque a embarque?\n\n"
            "PREGUNTAS SUGERIDAS: ¿Con qué frecuencia importan? / ¿Tienen seguro de carga propio? / ¿Quién decide el proveedor logístico?"
        ),
        "email": (
            "Asunto: Importaciones de maquinaria/componentes — apoyo logístico integral\n\n"
            "Hola [Nombre],\n\n"
            "Soy [SDR] de GBS Logistics. Apoyamos a empresas industriales con importaciones de maquinaria, equipos y componentes técnicos, "
            "centralizando flete, aduana, seguro y transporte final en un solo proveedor.\n\n"
            "En operaciones donde los tiempos son importantes y la carga técnica requiere coordinación específica, "
            "tener un solo interlocutor reduce errores y libera al equipo interno de COMEX.\n\n"
            "¿Tiene sentido una llamada breve para revisar si hay fit con su operación actual?"
        ),
        "whatsapp": "Hola [Nombre], GBS apoya a importadores de maquinaria/componentes con flete, aduana y puerta a puerta. ¿Quién ve COMEX o logística internacional en [Empresa]?",
    },
    {
        "id": 3,
        "label": "3 — Salud y Equipamiento Médico",
        "industria": "Medical Devices · Health Care · Insumos clínicos",
        "cargo": "Gerente de Abastecimiento · Jefe de Compras · Encargado de Importaciones",
        "prioridad": "Media-Alta",
        "contactos": 201,
        "keywords": ["Equipamiento médico", "Carga sensible", "Documentación técnica", "Aduana médica", "Tiempos críticos"],
        "dolor": "Carga sensible con tiempos críticos y documentación exigente. Los errores aduaneros o los retrasos pueden afectar directamente la operación clínica.",
        "cosas_hechas": "Importación de equipamiento médico y dispositivos clínicos con coordinación de documentación técnica para aduana y transporte controlado hasta destino.",
        "frase_guia": "En salud, un retraso logístico no es un problema comercial — puede ser un problema clínico. GBS da visibilidad y certeza en la coordinación de equipamiento médico.",
        "apertura": "¿Ustedes importan equipamiento médico, dispositivos o insumos clínicos de forma recurrente?",
        "preguntas": [
            "¿Qué tipo de equipamiento importan y desde qué países?",
            "¿Qué tan críticos son los tiempos de entrega para la operación?",
            "¿Tienen problemas frecuentes con documentación en aduana?",
            "¿Quién evalúa y decide el proveedor logístico?",
        ],
        "objeciones": [
            ("Ya tenemos proveedor logístico", "Entendido. ¿Tendría sentido quedar como alternativa para cargas urgentes o para rutas donde hoy tienen más fricción?"),
            ("No soy la persona", "Gracias. ¿Me puede indicar quién ve las compras o la importación de equipamiento médico?"),
            ("Llámame más adelante", "De acuerdo. ¿Hay alguna temporada o período donde sea mejor retomar? ¿Tienen importaciones planificadas para los próximos meses?"),
            ("Es muy caro", "Para equipamiento médico el costo total de un error — retraso en aduana, carga dañada, documentación incompleta — suele superar la diferencia de precio. ¿Lo han medido?"),
        ],
        "speech1": (
            "¿Hablo con [Nombre]? Soy [SDR] de GBS Logistics. ¿Tienen un minuto?\n\n"
            "Trabajamos con empresas del sector salud y equipamiento médico que importan dispositivos, equipos e insumos clínicos. "
            "En ese segmento la complejidad no es solo el flete — es la documentación técnica para aduana, "
            "el manejo de carga sensible y la certeza de que va a llegar cuando la operación lo necesita.\n\n"
            "GBS coordina toda la importación: flete, documentación, aduana, seguro y transporte hasta destino final.\n\n"
            "¿Ustedes importan equipamiento o insumos médicos de forma recurrente?\n\n"
            "PREGUNTAS SUGERIDAS: ¿Qué tipo de equipos importan? / ¿Desde qué países? / ¿Han tenido problemas con documentación aduanera?"
        ),
        "speech2": (
            "Hola [Nombre], soy [SDR] de GBS Logistics.\n\n"
            "Importar equipamiento médico tiene un nivel de complejidad mayor que otras cargas: "
            "documentación técnica específica para aduana chilena, manejo de carga sensible "
            "y tiempos de entrega que muchas veces no pueden fallar.\n\n"
            "GBS trabaja con empresas del sector salud para manejar esa coordinación de punta a punta, "
            "incluyendo seguimiento en tiempo real y respuesta directa cuando algo no va según lo planeado.\n\n"
            "¿Tienen hoy alguna importación recurrente donde sientan que la coordinación o la visibilidad puede mejorar?\n\n"
            "PREGUNTAS SUGERIDAS: ¿Cuántos embarques manejan al año? / ¿FCL, LCL o aéreo principalmente? / ¿Qué parte del proceso genera más trabajo interno?"
        ),
        "speech3": (
            "Hola [Nombre], te llamo de GBS Logistics. Muy breve.\n\n"
            "Quería validar si [Empresa] importa equipamiento médico o insumos clínicos de forma recurrente. "
            "Trabajamos con distribuidores e importadores del sector salud que necesitan certeza documental y tiempos controlados — "
            "donde un error en aduana tiene consecuencias directas.\n\n"
            "¿Tienen alguna importación planificada para los próximos meses donde valga la pena evaluar alternativas?\n\n"
            "PREGUNTAS SUGERIDAS: ¿Desde qué países importan principalmente? / ¿Quién decide el forwarder? / ¿Último problema con aduana o documentación?"
        ),
        "email": (
            "Asunto: Logística internacional para equipamiento médico — GBS Logistics\n\n"
            "Hola [Nombre],\n\n"
            "Soy [SDR] de GBS Logistics. Apoyamos a empresas del sector salud con la importación de equipamiento médico y dispositivos clínicos, "
            "coordinando documentación técnica para aduana, transporte especializado y seguimiento de carga sensible.\n\n"
            "En un sector donde los tiempos son críticos y los errores documentales son costosos, "
            "tener un forwarder que entiende la complejidad específica hace la diferencia.\n\n"
            "¿Podemos revisar si hay fit con su operación actual en una llamada de 20 minutos?"
        ),
        "whatsapp": "Hola [Nombre], GBS apoya importaciones de equipamiento médico con flete, documentación aduanera y transporte controlado. ¿Tú ves compras o logística internacional?",
    },
    {
        "id": 4,
        "label": "4 — Tecnología, Electrónica y Retail",
        "industria": "Electronics · Information Technology · Retail importador",
        "cargo": "Supply Chain Manager · Gerente de Operaciones · Gerente de Abastecimiento",
        "prioridad": "Media-Alta",
        "contactos": 440,
        "keywords": ["Abastecimiento recurrente", "Quiebres de stock", "Electrónica importada", "Retail multimarca", "LCL desde Asia"],
        "dolor": "Abastecimiento recurrente con presión de inventario, quiebres de stock y necesidad de visibilidad para planificar. El flete spot sin continuidad genera incertidumbre.",
        "cosas_hechas": "Importación regular de productos electrónicos, tecnología y bienes de retail desde China, Corea y USA con seguimiento en tiempo real y manejo de múltiples SKUs.",
        "frase_guia": "En retail e importación de tecnología, la visibilidad no es un lujo — es lo que permite planificar. GBS da trazabilidad de punta a punta para que no haya sorpresas.",
        "apertura": "¿Hoy manejan importaciones frecuentes de productos electrónicos o tecnología?",
        "preguntas": [
            "¿Con qué frecuencia importan? ¿Mensual, trimestral?",
            "¿El dolor principal es el costo, los tiempos o la visibilidad?",
            "¿Tienen seguro de carga propio o va incluido con el forwarder?",
            "¿Coordinan el transporte desde el puerto hasta la bodega o lo gestiona otro proveedor?",
        ],
        "objeciones": [
            ("Solo vemos precio", "Tiene sentido. ¿Calculan también el costo de un quiebre de stock por retraso? Para abastecimiento recurrente, la predictibilidad suele valer más que ahorrar unos USD en flete."),
            ("Estamos cubiertos", "Perfecto. ¿Tendría sentido igual comparar en el próximo embarque para tener un benchmark y una segunda opción?"),
            ("Mándame información", "Claro. Para enviarte algo relevante: ¿qué tipo de productos importan y desde qué países principalmente?"),
            ("No me interesa", "Entiendo. ¿Es porque el proceso ya está optimizado, porque no es el momento o porque prefieren otro canal de contacto?"),
        ],
        "speech1": (
            "¿Hablo con [Nombre]? Soy [SDR] de GBS Logistics.\n\n"
            "Trabajamos con empresas de retail e importación de tecnología y electrónica que necesitan abastecimiento recurrente con visibilidad real. "
            "En esos negocios el problema más frecuente es que el flete llega cuando llega — y cuando hay un retraso, "
            "el quiebre de stock tiene un costo que va mucho más allá del precio del embarque.\n\n"
            "GBS coordina flete marítimo y aéreo, aduana, seguro y entrega final, con seguimiento en tiempo real.\n\n"
            "¿Ustedes hoy manejan importaciones frecuentes de productos electrónicos o tecnología?\n\n"
            "PREGUNTAS SUGERIDAS: ¿Con qué frecuencia importan? / ¿Desde China principalmente? / ¿FCL o LCL?"
        ),
        "speech2": (
            "Hola [Nombre], soy [SDR] de GBS Logistics. ¿Tienen un minuto?\n\n"
            "Quería validar si [Empresa] importa productos de electrónica o tecnología de forma recurrente. "
            "En empresas de retail e importación, lo que más nos llega es que tienen el flete resuelto pero "
            "la visibilidad, el seguro y el transporte final quedan en el aire — especialmente cuando hay múltiples SKUs y fechas críticas.\n\n"
            "GBS consolida todo: flete, aduana, seguro, transporte hasta bodega.\n\n"
            "¿Tienen hoy algún embarque donde sientan que la coordinación puede ser más eficiente?\n\n"
            "PREGUNTAS SUGERIDAS: ¿Cuántos embarques mensuales manejan? / ¿Quién coordina internamente? / ¿Usan LCL o FCL?"
        ),
        "speech3": (
            "Hola [Nombre], te llamo de GBS Logistics. Muy breve.\n\n"
            "Importar electrónica y tecnología de forma recurrente tiene un reto particular: "
            "los tiempos de reposición no pueden fallar porque el stock no espera. "
            "GBS trabaja con importadores y distribuidores de tecnología ayudando a predecir mejor los tiempos "
            "y a tener un solo proveedor que responda de punta a punta.\n\n"
            "¿Hoy trabajan con un forwarder fijo o cotizan embarque a embarque?\n\n"
            "PREGUNTAS SUGERIDAS: ¿Qué problemas han tenido con retrasos o documentación? / ¿Tienen carga de diferentes proveedores consolidada? / ¿Destinatario final es bodega propia?"
        ),
        "email": (
            "Asunto: Importaciones recurrentes de tecnología/electrónica — GBS Logistics\n\n"
            "Hola [Nombre],\n\n"
            "Soy [SDR] de GBS Logistics. Apoyamos a empresas de retail y distribución de electrónica con abastecimiento internacional recurrente, "
            "coordinando flete, aduana, seguro y entrega final con visibilidad de punta a punta.\n\n"
            "En negocios donde la planificación de inventario depende de los tiempos de entrega, "
            "tener un forwarder confiable y transparente hace diferencia.\n\n"
            "¿Tiene sentido una llamada de 20 minutos para revisar si podemos mejorar algo en su operación actual?"
        ),
        "whatsapp": "Hola [Nombre], GBS apoya importaciones recurrentes de tecnología/electrónica con flete, aduana y puerta a puerta. ¿Quién ve logística internacional?",
    },
    {
        "id": 5,
        "label": "5 — Vino, Alimentos Secos y Carga Sensible",
        "industria": "Wine & Spirits · Food & Beverages · Carga sensible no perecible",
        "cargo": "Gerente de Comercio Exterior · Gerente de Exportaciones · Gerente General",
        "prioridad": "Media",
        "contactos": 199,
        "keywords": ["Thermoliner", "Linerbag", "Logger temperatura", "Exportación vino", "Carga sensible"],
        "dolor": "Riesgo de humedad, condensación y temperatura en carga de vino y alimentos. El daño a la carga afecta directamente la calidad del producto en destino.",
        "cosas_hechas": "Exportaciones de vino chileno con thermoliner a mercados de USA, UK, Brasil y México. Control de temperatura y humedad con logger. Coordinación de carga temperada puerta a puerta.",
        "frase_guia": "GBS es el único forwarder con especialización real en carga temperada para vino y alimentos. Thermoliner, logger, linerbag y seguimiento de temperatura no son extras — son parte del servicio.",
        "apertura": "¿Ustedes exportan vino, alimentos secos o carga sensible que requiera control de temperatura?",
        "preguntas": [
            "¿A qué destinos exportan principalmente?",
            "¿Han tenido problemas de humedad, condensación o temperatura en algún embarque?",
            "¿Usan thermoliner o logger de temperatura actualmente?",
            "¿Quién coordina la exportación: tienen equipo propio de COMEX o delegan todo al forwarder?",
        ],
        "objeciones": [
            ("No tenemos problemas con nuestra carga", "Buenísimo. ¿Usan logger de temperatura para confirmar eso? Muchos daños se descubren en destino, no en origen."),
            ("Ya lo ve otro forwarder", "Entiendo. ¿Ese forwarder tiene thermoliner propio o lo subcontrata? La especialización en carga temperada para vino marca una diferencia grande en la calidad de llegada."),
            ("No exportamos con suficiente frecuencia", "¿Sus exportaciones son estacionales? Para carga sensible, la especialización del forwarder importa aunque el volumen sea bajo."),
            ("El precio es clave", "Totalmente. ¿Han calculado el costo de un embarque rechazado por daño de temperatura en destino? Eso suele ser mucho más costoso que la diferencia en el flete."),
        ],
        "speech1": (
            "¿Hablo con [Nombre]? Soy [SDR] de GBS Logistics.\n\n"
            "Trabajamos con bodegas, viñas e importadores de alimentos con una especialización que pocos forwarders tienen: "
            "carga temperada para vino y alimentos sensibles. Thermoliner, linerbag, logger de temperatura y control de humedad — "
            "coordinado desde origen en Chile hasta el destino final en USA, UK, Brasil o México.\n\n"
            "El problema más común que vemos es que la carga llega con daño de condensación que se detecta en destino, "
            "cuando ya es tarde y el reclamo al seguro es complejo.\n\n"
            "¿Ustedes exportan vino o alimentos que requieran control de temperatura?\n\n"
            "PREGUNTAS SUGERIDAS: ¿A qué mercados exportan principalmente? / ¿Usan thermoliner actualmente? / ¿Han tenido problemas de condensación o temperatura?"
        ),
        "speech2": (
            "Hola [Nombre], soy [SDR] de GBS Logistics. ¿Tienen un minuto?\n\n"
            "Quería validar si [Empresa] exporta vino, alimentos secos o carga sensible. "
            "GBS tiene una especialización particular en este segmento: "
            "thermoliner certificado, logger de temperatura por embarque y coordinación de punta a punta "
            "para que la carga llegue en las mismas condiciones que salió de la bodega.\n\n"
            "¿Hoy trabajan con un forwarder que tenga esa especialización en carga temperada, o es algo que no han necesitado todavía?\n\n"
            "PREGUNTAS SUGERIDAS: ¿Qué destinos manejan? / ¿Qué tipos de contenedor usan? / ¿Tienen seguro de carga incluido?"
        ),
        "speech3": (
            "Hola [Nombre], te llamo de GBS Logistics. Muy breve.\n\n"
            "Para exportaciones de vino y alimentos sensibles, el mayor riesgo no suele estar en el precio del flete "
            "sino en lo que pasa con la carga durante el tránsito: humedad, cambios de temperatura, condensación. "
            "Un contenedor sin control termina con producto rechazado en destino.\n\n"
            "GBS tiene la especialización en thermoliner, linerbag y logger que la mayoría de los forwarders generalistas no tienen.\n\n"
            "¿Tienen alguna exportación próxima donde valga la pena revisar cómo están protegiendo la carga?\n\n"
            "PREGUNTAS SUGERIDAS: ¿A qué mercados exportan con más frecuencia? / ¿Han tenido reclamos por daño de carga? / ¿Quién decide el forwarder?"
        ),
        "email": (
            "Asunto: Exportaciones de vino/alimentos con thermoliner y control de temperatura — GBS\n\n"
            "Hola [Nombre],\n\n"
            "Soy [SDR] de GBS Logistics. Tenemos una especialización particular en exportaciones de vino y alimentos sensibles: "
            "thermoliner certificado, logger de temperatura, linerbag y coordinación puerta a puerta hasta el distribuidor en destino.\n\n"
            "La diferencia con un forwarder generalista es que el control de temperatura no es un extra — "
            "es parte del servicio estándar, porque sabemos que en vino y alimentos de calidad la condición de llegada es tan importante como el precio.\n\n"
            "¿Tendría sentido una llamada breve para revisar sus próximas exportaciones?"
        ),
        "whatsapp": "Hola [Nombre], GBS tiene thermoliner, logger y linerbag para exportaciones de vino/alimentos sensibles. ¿Exportan carga que requiera control de temperatura?",
    },
]

GLOSARIO = [
    ("FCL", "Full Container Load — contenedor completo para un solo cliente."),
    ("LCL", "Less than Container Load — carga consolidada con otros clientes."),
    ("Freight Forwarder", "Agente que coordina el transporte internacional de carga. GBS es un freight forwarder."),
    ("DUA / Declaración", "Documento de declaración aduanera que GBS coordina con el agente de aduana."),
    ("Aduana", "Control oficial del ingreso/salida de mercancías. GBS coordina la tramitación completa."),
    ("Thermoliner", "Revestimiento térmico de contenedor para control de temperatura. Especialidad GBS para vino."),
    ("Logger", "Dispositivo que registra temperatura y humedad durante todo el tránsito del embarque."),
    ("Linerbag", "Bolsa plástica interna del contenedor para proteger carga de humedad y condensación."),
    ("PO Management", "Gestión de Purchase Orders — GBS puede hacer seguimiento desde el proveedor en origen."),
    ("Puerta a puerta", "Servicio completo desde el proveedor en origen hasta el destino final del cliente."),
    ("GAA / WCA", "Redes internacionales de freight forwarders que dan respaldo global a GBS."),
    ("Seguro de carga", "Cobertura para daño o pérdida. GBS lo gestiona como parte de la operación."),
]

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
g = img_b64("gbs_logo.png", 52) or (
    f'<div style="background:{BLUE};color:#fff;padding:10px 22px;border-radius:8px;'
    f'font-size:18px;font-weight:800;letter-spacing:2px">GBS</div>')
c = img_b64("conprospeccion_logo.png", 42) or (
    f'<div style="background:#111827;padding:8px 18px;border-radius:8px;'
    f'font-size:13px;font-weight:700;color:#fbbf24">Conprospección</div>')

st.markdown(
    f'<div style="display:flex;align-items:center;justify-content:space-between;'
    f'background:linear-gradient(135deg,#faf5ff,#ede9fe);padding:18px 28px;'
    f'border-radius:14px;border:1px solid {BORDER};margin-bottom:24px;'
    f'box-shadow:0 2px 8px rgba(0,0,0,.06)">'
    f'<div style="display:flex;align-items:center;gap:18px">{g}'
    f'<div><div style="font-size:22px;font-weight:800;color:#1e293b">Playbook de llamada SDR</div>'
    f'<div style="font-size:13px;color:#64748b;margin-top:3px">'
    f'Freight forwarder integral · Flete · Aduana · Seguro · Transporte local · Puerta a puerta</div>'
    f'</div></div>{c}</div>',
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════════════════════
# FILTROS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    f'<div style="background:#fff;border:1px solid {BORDER};border-radius:12px;'
    f'padding:16px 20px;margin-bottom:24px">'
    f'<div style="font-size:12px;font-weight:700;color:{BLUE};margin-bottom:10px;text-transform:uppercase;letter-spacing:.5px">'
    f'Segmento Playbook</div></div>',
    unsafe_allow_html=True,
)

col_seg, col_limpiar = st.columns([5, 1])
with col_seg:
    opciones = [s["label"] for s in SEGMENTOS]
    seg_label = st.selectbox("Seleccionar segmento", opciones, label_visibility="collapsed", key="seg_sel")
with col_limpiar:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Limpiar", key="btn_limpiar"):
        st.rerun()

seg = next(s for s in SEGMENTOS if s["label"] == seg_label)

st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 1 — TIPS ANTES DE LLAMAR
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    f'<div style="background:{DARK};color:#fff;border-radius:12px;padding:20px 24px;margin-bottom:20px">'
    f'<div style="font-size:17px;font-weight:800;margin-bottom:6px">Tips antes de llamar</div>'
    f'<div style="font-size:13px;color:#c4b5fd">'
    f'Objetivo: abrir conversación con empresas de <b style="color:#fff">{seg["industria"]}</b>, '
    f'validar si <b style="color:#fff">{seg["cargo"]}</b> es el área correcta '
    f'y dejar una reunión bien preparada.</div></div>',
    unsafe_allow_html=True,
)

st.markdown(
    f'<div style="background:#4c1d95;border:1px solid #7c3aed;border-radius:10px;'
    f'padding:14px 18px;margin-bottom:16px;color:#ddd6fe;font-size:13px;font-weight:600">'
    f'Escucha señales de: {seg["dolor"]}</div>',
    unsafe_allow_html=True,
)

tips_generales = [
    ("No vender todavía", "Primero validar si hay dolor, si es la persona correcta y si hay recurrencia. GBS se explica mejor en reunión."),
    ("Buscar reunión", "La llamada no cierra un contrato — abre una conversación de 20 minutos. Ese es el único objetivo."),
    ("Buscar a la persona correcta", "Aunque parezca el contacto correcto, validar quién ve COMEX, logística internacional o abastecimiento."),
    ("Hablar de impacto, no de servicio", "No listar características. Preguntar por el dolor y conectar con lo que GBS resuelve."),
    ("Validar recurrencia", "GBS funciona mejor con operaciones recurrentes. ¿Cuántos embarques al mes/año? Es la pregunta clave."),
    ("Glosario COMEX disponible", "Si no conoces un término del prospecto, no improvises. Consultá el glosario al final de esta página."),
]

cols_t = st.columns(3)
for i, (titulo, desc) in enumerate(tips_generales):
    with cols_t[i % 3]:
        st.markdown(
            f'<div style="background:{LIGHT};border:1px solid {BORDER};border-radius:10px;'
            f'padding:14px;margin-bottom:12px;min-height:80px">'
            f'<div style="font-size:12px;font-weight:800;color:{BLUE};margin-bottom:5px">{titulo}</div>'
            f'<div style="font-size:11px;color:#475569;line-height:1.5">{desc}</div></div>',
            unsafe_allow_html=True,
        )

# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 2 — CONTEXTO GBS + FOCO DE ESTA LLAMADA
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
col_ctx, col_foco = st.columns(2)

with col_ctx:
    st.markdown(
        f'<div style="font-size:16px;font-weight:800;color:#1e293b;margin-bottom:12px">Contexto GBS Logistics</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div style="background:{LIGHT};border:1px solid {BORDER};border-radius:10px;padding:16px;margin-bottom:10px">'
        f'<div style="font-size:12px;font-weight:800;color:{BLUE};margin-bottom:8px">Resumen simple</div>'
        f'<div style="font-size:13px;color:#334155;line-height:1.7">'
        f'GBS Logistics es un freight forwarder chileno que ayuda a importadores y exportadores '
        f'a coordinar fletes, aduana, seguros, transporte local y puerta a puerta — '
        f'todo con un solo interlocutor. Para empresas sin departamento logístico robusto, '
        f'GBS actúa como el equipo de COMEX externo que opera de punta a punta.'
        f'</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div style="background:#4c1d95;border-left:4px solid {BLUE};border-radius:8px;padding:14px 16px">'
        f'<div style="font-size:12px;font-weight:800;color:#c4b5fd;margin-bottom:6px">Frase guía — {seg["label"][:30]}...</div>'
        f'<div style="font-size:13px;color:#e2e8f0;line-height:1.6;font-style:italic">"{seg["frase_guia"]}"</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

with col_foco:
    st.markdown(
        f'<div style="font-size:16px;font-weight:800;color:#1e293b;margin-bottom:12px">Foco de esta llamada</div>',
        unsafe_allow_html=True,
    )
    pills = "".join(
        f'<span style="background:{BLUE}22;color:{BLUE};border:1px solid {BLUE}44;'
        f'border-radius:20px;padding:3px 10px;font-size:11px;font-weight:600;display:inline-block;margin:2px">'
        f'{k}</span>' for k in seg["keywords"]
    )
    st.markdown(
        f'<div style="background:#fff;border:1px solid {BORDER};border-radius:10px;padding:16px">'
        f'<div style="margin-bottom:8px"><span style="font-size:12px;font-weight:700;color:#1e293b">Industria:</span> '
        f'<span style="font-size:12px;color:#475569">{seg["industria"]}</span></div>'
        f'<div style="margin-bottom:8px"><span style="font-size:12px;font-weight:700;color:#1e293b">Cargo objetivo:</span> '
        f'<span style="font-size:12px;color:#475569">{seg["cargo"]}</span></div>'
        f'<div style="margin-bottom:8px"><span style="font-size:12px;font-weight:700;color:#1e293b">Dolor probable:</span> '
        f'<span style="font-size:12px;color:#475569">{seg["dolor"]}</span></div>'
        f'<div style="margin-bottom:8px"><span style="font-size:12px;font-weight:700;color:#1e293b">Cosas que hemos hecho:</span> '
        f'<span style="font-size:12px;color:#475569">{seg["cosas_hechas"]}</span></div>'
        f'<div style="margin-bottom:8px"><span style="font-size:12px;font-weight:700;color:#1e293b">Prioridad comercial:</span> '
        f'<span style="font-size:12px;font-weight:700">{seg["prioridad"]}</span> '
        f'<span style="font-size:12px;color:#64748b">| Contactos: <b>{seg["contactos"]}</b></span></div>'
        f'<div style="margin-top:10px">{pills}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 3 — SPEECHES
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
with st.expander("Speech recomendado", expanded=True):
    apertura_html = (
        f'<div style="background:{LIGHT};border:1px solid {BORDER};border-radius:8px;'
        f'padding:10px 14px;margin-bottom:14px;font-size:13px;color:{BLUE};font-weight:600">'
        f'Apertura: <span style="color:#334155;font-weight:400;font-style:italic">"{seg["apertura"]}"</span></div>'
    )
    st.markdown(apertura_html, unsafe_allow_html=True)

    for i, speech_text in enumerate([seg["speech1"], seg["speech2"], seg["speech3"]], 1):
        st.markdown(
            f'<div style="font-size:12px;font-weight:800;color:{BLUE};margin:8px 0 6px;'
            f'text-transform:uppercase;letter-spacing:.5px">Ejemplo de speech {i}</div>',
            unsafe_allow_html=True,
        )
        lines = speech_text.split("\n\n")
        for line in lines:
            if line.startswith("PREGUNTAS SUGERIDAS"):
                qs = line.replace("PREGUNTAS SUGERIDAS: ", "").split(" / ")
                st.markdown(
                    f'<div style="background:{DARK};border-left:4px solid {BLUE};border-radius:6px;'
                    f'padding:12px 14px;margin-top:8px">'
                    f'<div style="font-size:11px;font-weight:800;color:#c4b5fd;margin-bottom:6px">PREGUNTAS SUGERIDAS</div>'
                    + "".join(f'<div style="font-size:12px;color:#e2e8f0;margin-bottom:4px">• {q}</div>' for q in qs)
                    + '</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div style="font-size:13.5px;color:#1e293b;line-height:1.7;margin-bottom:8px">{line}</div>',
                    unsafe_allow_html=True,
                )
        if i < 3:
            st.markdown('<div style="border-top:1px dashed #ddd6fe;margin:6px 0 14px"></div>',
                        unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 4 — MANEJO DE RESPUESTAS (taxonomía uniforme con Indicadores / Validación)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")

todas_objeciones = [
    ("No me interesa", "Entiendo. ¿Es porque no manejan comercio exterior, porque ya está cubierto o porque ahora no es prioridad?"),
    ("Ya trabajamos con otro forwarder", "Perfecto. La conversación no busca reemplazarlo de inmediato, sino quedar como alternativa para rutas, urgencias o puerta a puerta."),
    ("Mándame información", "Claro. Para enviarte algo útil: ¿importan, exportan o ambas? ¿Marítimo, aéreo o ambos?"),
    ("No soy la persona", "Gracias. ¿Quién ve comercio exterior, logística internacional o abastecimiento?"),
    ("No tenemos volumen", "¿Sus operaciones son esporádicas o tienen embarques durante el año? GBS calza mejor cuando hay recurrencia, no necesariamente grandes volúmenes."),
    ("Estamos bien", "Buenísimo. Puede tener sentido quedar como alternativa para contingencias, cargas urgentes o servicios complementarios."),
    ("Llámame más adelante", "De acuerdo. ¿Te parece retomarlo en [mes]? ¿Hay temporada alta que convenga considerar?"),
] + seg["objeciones"]

# Guía del SDR por TIPO DE RESPUESTA (mismas opciones que Indicadores y Validación)
RESP_POSITIVAS = [
    ("Solicita reunión",
     "Quiere reunirse: confirmar día y hora en el momento y dejar la reunión agendada con todos los datos. Validar que sea quien decide.",
     ["¿Qué los motivó a buscar apoyo logístico ahora?",
      "¿Quién más participa de la decisión?",
      "¿Qué les gustaría resolver en la reunión?"]),
    ("Solicita cotización",
     "No cotizar en frío: primero levantar los datos mínimos y proponer una reunión breve para cotizar bien.",
     ["¿Qué importan o exportan y desde qué países?",
      "¿FCL, LCL o aéreo?",
      "¿Volumen mensual aproximado e Incoterm?"]),
    ("Solicita reunión + cotización",
     "Agendar la reunión y usarla para levantar datos y cotizar. Confirmar día y hora y enviar la invitación.",
     ["¿Qué rutas u operaciones quieren cotizar?",
      "¿Quién decide el proveedor logístico?",
      "¿Para cuándo necesitan la propuesta?"]),
    ("Solicita más información",
     "Calificar antes de enviar material: entender qué les interesa para mandar algo relevante (no genérico) y proponer una reunión de 15 minutos.",
     ["¿Qué les interesa puntualmente?",
      "¿Importan, exportan o ambas?",
      "¿Marítimo, aéreo o ambos?"]),
]
RESP_NEGATIVAS = [
    ("No interesado",
     "Indagar el porqué real y registrarlo como motivo. Si ya está cubierto, ofrecer quedar como alternativa para contingencias.",
     ["¿Es porque no manejan comercio exterior, porque ya está cubierto o porque ahora no es prioridad?"]),
    ("Ya tiene proveedor",
     "No buscar reemplazar de inmediato; posicionarse como segunda opción para rutas, urgencias o puerta a puerta.",
     ["¿Dónde su operador actual les falla o podría mejorar?",
      "¿Tienen rutas o urgencias sin cobertura óptima?"]),
    ("No es la persona",
     "Pedir la referencia correcta y conseguir los datos para contactar a quien decide.",
     ["¿Quién ve comercio exterior, logística internacional o abastecimiento?",
      "¿Me puede compartir su nombre y contacto?"]),
    ("Sin respuesta",
     "Activar una secuencia de seguimiento multicanal, variando canal y horario, con un máximo de toques. Registrar como «Sin respuesta» al agotarla.",
     ["Reintentar: llamada email WhatsApp",
      "Variar horario (mañana / tarde)",
      "Máximo 4–5 toques antes de cerrar"]),
]
RESP_GUIA = {}
for _t, _g, _p in RESP_POSITIVAS:
    RESP_GUIA[_t] = ("", "#16a34a", _g, _p)
for _t, _g, _p in RESP_NEGATIVAS:
    RESP_GUIA[_t] = ("", "#dc2626", _g, _p)
_POS_NOMBRES = [t for t, _, _2 in RESP_POSITIVAS]
_NEG_NOMBRES = [t for t, _, _2 in RESP_NEGATIVAS]

with st.expander("Manejo de respuestas", expanded=False):
    st.markdown(
        f'<div style="font-size:13px;color:#334155;line-height:1.6;margin-bottom:12px">'
        f'Identificar el <b>tipo de respuesta</b> del lead y actuar en consecuencia. En los casos '
        f'negativos, registrar el <b>porqué</b> (alimenta el reporte «Indicadores»). '
        f'Seleccionar un tipo para ver la guía.</div>',
        unsafe_allow_html=True)

    if "pb_resp" not in st.session_state:
        st.session_state["pb_resp"] = _POS_NOMBRES[0]

    st.markdown('<div style="font-size:12px;font-weight:800;color:#16a34a;margin:2px 0 6px">Respuestas positivas</div>',
                unsafe_allow_html=True)
    cpos = st.columns(4)
    for i, t in enumerate(_POS_NOMBRES):
        if cpos[i].button(t, key=f"rp_{i}", use_container_width=True):
            st.session_state["pb_resp"] = t

    st.markdown('<div style="font-size:12px;font-weight:800;color:#dc2626;margin:10px 0 6px">Respuestas negativas</div>',
                unsafe_allow_html=True)
    cneg = st.columns(4)
    for i, t in enumerate(_NEG_NOMBRES):
        if cneg[i].button(t, key=f"rn_{i}", use_container_width=True):
            st.session_state["pb_resp"] = t

    sel = st.session_state["pb_resp"]
    active_key = f"rp_{_POS_NOMBRES.index(sel)}" if sel in _POS_NOMBRES else f"rn_{_NEG_NOMBRES.index(sel)}"
    st.markdown(
        f'<style>[class*="st-key-{active_key}"] button{{background:{GBS_PURPLE}!important;'
        f'color:#fff!important;border:none!important;font-weight:700!important}}</style>',
        unsafe_allow_html=True)

    signo, color, guia, preg = RESP_GUIA[sel]
    preg_html = "".join(f'<li style="margin-bottom:4px">{q}</li>' for q in preg)
    st.markdown(
        f'<div style="background:#fff;border:1px solid {BORDER};border-left:4px solid {color};'
        f'border-radius:10px;padding:14px 16px;margin-top:10px">'
        f'<div style="font-size:14px;font-weight:800;color:{color};margin-bottom:6px">{signo} {sel}</div>'
        f'<div style="font-size:13px;color:#334155;line-height:1.6;margin-bottom:8px">{guia}</div>'
        f'<div style="font-size:12px;font-weight:700;color:#1e293b;margin-bottom:4px">Qué preguntar / decir:</div>'
        f'<ul style="font-size:12px;color:#475569;line-height:1.5;margin:0;padding-left:18px">{preg_html}</ul>'
        f'</div>',
        unsafe_allow_html=True)

    st.markdown(
        '<div style="font-size:13px;font-weight:800;color:#1e293b;margin:18px 0 8px">'
        'Banco de respuestas a objeciones frecuentes</div>',
        unsafe_allow_html=True)
    col_ob1, col_ob2 = st.columns(2)
    for i, (obj, resp) in enumerate(todas_objeciones):
        with (col_ob1 if i % 2 == 0 else col_ob2):
            st.markdown(
                f'<div style="background:#fff;border:1px solid {BORDER};border-radius:10px;'
                f'padding:14px;margin-bottom:10px">'
                f'<div style="font-size:12px;font-weight:800;color:#dc2626;margin-bottom:6px">"{obj}"</div>'
                f'<div style="font-size:12px;color:#334155;line-height:1.5">{resp}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 5 — EMAIL Y WHATSAPP
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")

def _texto_box(texto, accent):
    safe = texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        f'<div style="background:#ffffff;border:1px solid {GBS_BORDER_2};border-left:4px solid {accent};'
        f'border-radius:10px;padding:14px 16px;font-size:13.5px;line-height:1.7;color:#1e293b;'
        f'white-space:pre-wrap;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif">'
        f'{safe}</div>'
    )

with st.expander("Templates de contacto (email · WhatsApp · pitch)", expanded=False):
    col_em, col_wa = st.columns(2)
    with col_em:
        st.markdown(f'<div style="font-size:13px;font-weight:700;color:{BLUE};margin-bottom:8px">Email de primer contacto</div>',
                    unsafe_allow_html=True)
        st.markdown(_texto_box(seg["email"], BLUE), unsafe_allow_html=True)

    with col_wa:
        st.markdown(f'<div style="font-size:13px;font-weight:700;color:#16a34a;margin-bottom:8px">WhatsApp de prospección</div>',
                    unsafe_allow_html=True)
        st.markdown(_texto_box(seg["whatsapp"], "#16a34a"), unsafe_allow_html=True)
        st.markdown(f'<div style="font-size:13px;font-weight:700;color:{BLUE};margin:14px 0 8px">Pitch 15 segundos (llamada fría)</div>',
                    unsafe_allow_html=True)
        st.markdown(_texto_box(
            "Te llamo desde GBS Logistics. Trabajamos con empresas que importan o exportan de forma recurrente "
            "y suelen tener dolores de visibilidad, documentación o coordinación. "
            "Quería entender si hoy manejan comercio exterior y si tendría sentido una reunión breve.", BLUE),
            unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 6 — GLOSARIO COMEX
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
with st.expander("Glosario COMEX — Términos que puede usar el prospecto"):
    cols_g = st.columns(3)
    for i, (term, defn) in enumerate(GLOSARIO):
        with cols_g[i % 3]:
            st.markdown(
                f'<div style="background:{LIGHT};border:1px solid {BORDER};border-radius:8px;'
                f'padding:12px;margin-bottom:8px">'
                f'<div style="font-size:12px;font-weight:800;color:{BLUE};margin-bottom:4px">{term}</div>'
                f'<div style="font-size:11px;color:#475569;line-height:1.4">{defn}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

# ── Footer ─────────────────────────────────────────────────────────────────────
cp = img_b64("conprospeccion_logo.png", 18) or ""
st.markdown(
    f'<div style="text-align:center;color:#94a3b8;font-size:11px;margin-top:32px;padding:16px">'
    f'{cp}&nbsp;Playbook SDR — <b style="color:{BLUE}">GBS Logistics</b> · '
    f'Conprospección · Confidencial · Uso interno</div>',
    unsafe_allow_html=True,
)
