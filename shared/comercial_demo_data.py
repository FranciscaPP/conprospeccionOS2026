"""Datos ficticios para la Fase 1 del modulo Comercial.

No contienen clientes reales ni datos sensibles. Sirven para validar flujo,
layout, navegacion y calculos antes de conectar Supabase/GHL.
"""
from __future__ import annotations

from datetime import date


DEMO_DATA_VERSION = "2026-08-12-nadilop-v9"


DEMO_OPPORTUNITIES = [
    {
        "id": "opp-nadilop-2026-08-12",
        "company": "Nadilop",
        "contact": "Nicole Diaz",
        "role": "Contacto comercial",
        "email": "nicole.diaz@nadilop.cl",
        "phone": "+56 2 3375 1100",
        "website": "https://nadilop.cl/",
        "linkedin_person": "",
        "linkedin_company": "https://www.linkedin.com/company/nadilop/",
        "industry": "Servicios TI / tecnologia B2B",
        "country": "Chile",
        "source": "Reunion comercial",
        "campaign": "Presentacion comercial CP",
        "owner": "Francisca",
        "scheduled_at": "2026-08-12",
        "meeting_at": "2026-08-12",
        "proposal_sent_at": "",
        "status": "Preparacion lista",
        "score": 84,
        "score_level": "Alto",
        "last_contact": "2026-08-12",
        "next_followup": "Validar foco comercial en reunion",
        "updated_at": "2026-08-12",
        "notes": (
            "Empresa chilena de servicios tecnologicos para empresas. Desde su sitio y LinkedIn aparece "
            "un foco fuerte en infraestructura critica, plataforma usuario, respaldo, continuidad "
            "operativa, licenciamiento, soporte y soluciones a medida."
        ),
        "meeting_link": "",
        "calendar_link": "",
        "recording_ref": "",
        "transcript": "",
        "meeting_summary": "",
        "preparation": {
            "state": "Aprobado para presentar",
            "generated_at": "2026-08-12 09:00",
            "content": (
                "Vemos una empresa ya validada comercialmente: mas de 14 anos, +200 proyectos y una "
                "facturacion anual declarada superior a US$2,5 millones. Su fortaleza parece estar en "
                "resolver necesidades donde la continuidad tecnologica es critica, con experiencia "
                "comprobable en grandes empresas. Nuestra hipotesis es que el desafio no esta en validar "
                "su capacidad tecnica, sino en transformar esa experiencia en un crecimiento comercial "
                "mas sistematico y predecible."
            ),
            "source_context": "Sitio web Nadilop + LinkedIn empresa + datos entregados para la reunion.",
        },
        "intro_sections": [
            ("Escala y tracción", "+14 años, +200 proyectos y +US$2,5M de facturación anual declarada. LinkedIn muestra actualmente 17 colaboradores asociados a la empresa."),
            ("Validación comercial", "Experiencia declarada en energía, minería, agroindustria, retail, medios y televisión, salud y servicios financieros."),
            ("Clientes visibles", "Entre los clientes visibles aparecen CGE, SQM, Legrand, Mega, Canal 13, TVN, Estée Lauder y Bolsa de Santiago."),
            ("Concentración observada", "Medios y TV aparece como uno de los clusters más repetidos, con Mega, Canal 13, TVN y RDF Media."),
            ("Qué activa una compra", "Sus casos apuntan a renovación de infraestructura, continuidad operacional, protección de datos, respaldo y modernización tecnológica."),
            ("Hipótesis comercial", "El mejor prospecto sería una organización donde una caída, infraestructura obsoleta o problemas de respaldo tienen impacto operacional."),
            ("A validar en la reunión", "Línea a acelerar, ticket promedio, cliente más rentable, ciclo de venta, industrias prioritarias y expansión a nuevas cuentas vs. crecimiento en cuentas actuales."),
        ],
        "diagnostic": {"state": "Sin generar", "generated_at": "", "answers": []},
        "market_research": {
            "state": "Preparacion inicial",
            "generated_at": "2026-08-12 09:10",
            "recommendation": (
                "Validar si el primer alcance sera infraestructura critica, plataforma usuario, "
                "licenciamiento/soporte o una combinacion por industrias prioritarias."
            ),
            "difficulty": "Media",
            "summary": (
                "Mercado B2B amplio y consultivo. Posibles industrias prioritarias: energia, mineria, "
                "agroindustria, retail, salud, servicios financieros, medios y television."
            ),
        },
        "proposals": [],
        "followups": [
            ("Preparar reunion", "2026-08-12", "Pendiente", "Mostrar evaluacion previa y validar preguntas clave."),
            ("Enviar propuesta", "Pendiente", "Pendiente", "Generar despues de la reunion con alcance y precio sugerido."),
        ],
        "emails": [],
        "history": [
            ("2026-08-12 09:00", "manual", "Oportunidad creada para reunion de presentacion"),
            ("2026-08-12 09:10", "manual", "Evaluacion previa preparada desde web, LinkedIn y datos entregados"),
        ],
    },
    {
        "id": "opp-demo-001",
        "company": "Andes SaaS",
        "contact": "Valentina Rojas",
        "role": "Gerenta Comercial",
        "email": "valentina.rojas@example.com",
        "phone": "+56 9 1111 2222",
        "website": "https://example.com/andes-saas",
        "linkedin_person": "https://linkedin.com/in/demo-valentina",
        "linkedin_company": "https://linkedin.com/company/demo-andes-saas",
        "industry": "Software B2B",
        "country": "Chile",
        "source": "Referido",
        "campaign": "Venta directa CP",
        "owner": "Francisca",
        "scheduled_at": "2026-07-18",
        "meeting_at": "2026-07-25",
        "proposal_sent_at": "2026-07-26",
        "status": "Propuesta enviada",
        "score": 86,
        "score_level": "Alto",
        "last_contact": "2026-07-26",
        "next_followup": "2026-07-29",
        "updated_at": "2026-07-26",
        "notes": "Busca abrir mercado en cuentas medianas de tecnologia y servicios profesionales.",
        "meeting_link": "https://meet.google.com/demo-andes",
        "calendar_link": "https://calendar.google.com/calendar/demo-andes",
        "recording_ref": "Granola demo",
        "transcript": "Transcripcion ficticia: el prospecto busca aumentar reuniones calificadas.",
        "meeting_summary": "Interes claro por externalizar prospeccion y medir conversion por mercado.",
        "preparation": {
            "state": "Aprobado para presentar",
            "generated_at": "2026-07-23 10:15",
            "content": "Andes SaaS vende software B2B a equipos comerciales. La reunion debe validar ICP, ticket promedio y ciclo de cierre.",
            "source_context": "Base interna demo + campana de venta directa.",
        },
        "diagnostic": {
            "state": "Generado",
            "generated_at": "2026-07-25 16:20",
            "answers": [
                ("Producto a prospectar", "Plataforma SaaS para gestion comercial", "Confirmado en reunion"),
                ("Cliente ideal", "Empresas B2B con equipo comercial de 8 a 50 personas", "Confirmado en reunion"),
                ("Mercados prioritarios", "Chile, Peru y Colombia", "Confirmado en reunion"),
                ("Ticket promedio", "USD 900 mensuales", "Obtenido desde campana"),
                ("Objetivo", "Generar 20 reuniones calificadas en 5 meses", "Confirmado en reunion"),
            ],
        },
        "market_research": {
            "state": "Generado",
            "generated_at": "2026-07-25 17:05",
            "recommendation": "Aceptar con alcance inicial conservador y expansion por industria tras validar mensajes.",
            "difficulty": "Media",
            "summary": "Mercado amplio, buena claridad de oferta y cargos compradores identificables.",
        },
        "proposals": [
            {
                "id": "prop-001-v1",
                "version": "Version 1",
                "status": "Enviada",
                "is_current": True,
                "setup_amount": 450000,
                "monthly_amount": 1500000,
                "total_amount": 7950000,
                "expected_margin": 40,
                "created_at": "2026-07-25",
                "sent_at": "2026-07-26",
                "valid_until": "2026-08-09",
                "pdf_ref": "demo/andes-saas-propuesta-v1.pdf",
                "summary": "Gestion de prospeccion por 5 meses con implementacion inicial.",
            }
        ],
        "followups": [
            ("Seguimiento 1", "2026-07-29", "Pendiente", "Confirmar recepcion y dudas"),
            ("Seguimiento 2", "2026-08-02", "Pendiente", "Reforzar alcance y siguiente paso"),
        ],
        "emails": [
            ("2026-07-26", "Francisca", "Propuesta comercial Andes SaaS", "Borrador revisado y enviado manualmente."),
        ],
        "history": [
            ("2026-07-18 09:10", "sistema", "Oportunidad creada desde agenda demo"),
            ("2026-07-23 10:15", "IA", "Evaluacion previa generada mediante boton"),
            ("2026-07-25 16:20", "IA", "Diagnostico de reunion procesado"),
            ("2026-07-26 12:40", "manual", "Propuesta Version 1 marcada como enviada"),
        ],
    },
    {
        "id": "opp-demo-002",
        "company": "Norte Industrial",
        "contact": "Camilo Herrera",
        "role": "Director de Desarrollo",
        "email": "camilo.herrera@example.com",
        "phone": "+56 9 3333 4444",
        "website": "https://example.com/norte-industrial",
        "linkedin_person": "",
        "linkedin_company": "https://linkedin.com/company/demo-norte-industrial",
        "industry": "Manufactura",
        "country": "Chile",
        "source": "Outbound",
        "campaign": "Prospeccion servicios industriales",
        "owner": "Francisca",
        "scheduled_at": "2026-07-20",
        "meeting_at": "2026-07-30",
        "proposal_sent_at": "",
        "status": "Preparacion lista",
        "score": 72,
        "score_level": "Medio",
        "last_contact": "2026-07-20",
        "next_followup": "2026-07-30",
        "updated_at": "2026-07-23",
        "notes": "Quiere validar si hay base suficiente de empresas industriales por zona norte.",
        "meeting_link": "https://meet.google.com/demo-norte",
        "calendar_link": "https://calendar.google.com/calendar/demo-norte",
        "recording_ref": "",
        "transcript": "",
        "meeting_summary": "",
        "preparation": {
            "state": "Generado",
            "generated_at": "2026-07-23 09:35",
            "content": "Norte Industrial vende soluciones de mantenimiento. Validar cargos tecnicos y decisores financieros.",
            "source_context": "Base demo de prospeccion + sitio web ficticio.",
        },
        "diagnostic": {"state": "Sin generar", "generated_at": "", "answers": []},
        "market_research": {
            "state": "Sin generar",
            "generated_at": "",
            "recommendation": "",
            "difficulty": "",
            "summary": "",
        },
        "proposals": [],
        "followups": [("Preparar reunion", "2026-07-29", "Pendiente", "Revisar ICP y preguntas")],
        "emails": [],
        "history": [
            ("2026-07-20 11:00", "sistema", "Reunion agendada"),
            ("2026-07-23 09:35", "IA", "Evaluacion previa generada mediante boton"),
        ],
    },
    {
        "id": "opp-demo-003",
        "company": "Pacifica Legal",
        "contact": "Daniela Fuentes",
        "role": "Socia",
        "email": "daniela.fuentes@example.com",
        "phone": "+56 9 5555 6666",
        "website": "https://example.com/pacifica-legal",
        "linkedin_person": "https://linkedin.com/in/demo-daniela",
        "linkedin_company": "",
        "industry": "Servicios profesionales",
        "country": "Peru",
        "source": "LinkedIn",
        "campaign": "CP servicios profesionales",
        "owner": "Francisca",
        "scheduled_at": "2026-07-10",
        "meeting_at": "2026-07-16",
        "proposal_sent_at": "2026-07-18",
        "status": "En seguimiento",
        "score": 64,
        "score_level": "Medio",
        "last_contact": "2026-07-22",
        "next_followup": "2026-07-28",
        "updated_at": "2026-07-22",
        "notes": "Interes en base de datos y prospeccion consultiva para empresas regionales.",
        "meeting_link": "",
        "calendar_link": "",
        "recording_ref": "Fathom demo",
        "transcript": "Transcripcion ficticia: interes moderado, presupuesto por confirmar.",
        "meeting_summary": "Quiere una propuesta escalonada con bajo riesgo inicial.",
        "preparation": {
            "state": "Aprobado para presentar",
            "generated_at": "2026-07-14 15:10",
            "content": "Firma legal con foco B2B regional. Validar industrias, ticket y objeciones de confianza.",
            "source_context": "Campana LinkedIn demo.",
        },
        "diagnostic": {
            "state": "Editado",
            "generated_at": "2026-07-16 18:30",
            "answers": [
                ("Producto a prospectar", "Servicios legales corporativos", "Confirmado en reunion"),
                ("Cliente ideal", "Empresas medianas con operaciones regionales", "Inferido por IA"),
                ("Presupuesto", "Pendiente de confirmar", "Pendiente de confirmar"),
            ],
        },
        "market_research": {
            "state": "Generado",
            "generated_at": "2026-07-17 10:00",
            "recommendation": "Ajustar alcance y partir con base comercial antes de prospeccion completa.",
            "difficulty": "Alta",
            "summary": "Oferta consultiva, ciclo largo y alta necesidad de prueba social.",
        },
        "proposals": [
            {
                "id": "prop-003-v1",
                "version": "Version 1",
                "status": "Enviada",
                "is_current": True,
                "setup_amount": 300000,
                "monthly_amount": 950000,
                "total_amount": 5050000,
                "expected_margin": 35,
                "created_at": "2026-07-17",
                "sent_at": "2026-07-18",
                "valid_until": "2026-08-01",
                "pdf_ref": "demo/pacifica-legal-propuesta-v1.pdf",
                "summary": "Base comercial + prospeccion controlada por 5 meses.",
            }
        ],
        "followups": [
            ("Seguimiento 1", "2026-07-21", "Enviado", "Resolver dudas de alcance"),
            ("Seguimiento 2", "2026-07-28", "Pendiente", "Enviar escenario ajustado"),
        ],
        "emails": [
            ("2026-07-18", "Francisca", "Propuesta comercial Pacifica Legal", "Enviada manualmente."),
            ("2026-07-22", "Prospecto", "Re: Propuesta comercial Pacifica Legal", "Solicita alternativa mas acotada."),
        ],
        "history": [
            ("2026-07-10 13:20", "sistema", "Oportunidad creada"),
            ("2026-07-16 18:30", "IA", "Diagnostico procesado y editado"),
            ("2026-07-18 09:05", "manual", "Propuesta enviada"),
            ("2026-07-22 16:12", "correo", "Respuesta recibida y registrada manualmente"),
        ],
    },
]


DEMO_SETTINGS = {
    "links": {
        "Plataforma cliente": "https://conprospeccionos2026-demo.streamlit.app/",
        "Base de datos de ejemplo": "",
    },
    "score_weights": {
        "Tamano del mercado": 12,
        "Disponibilidad de contactos": 10,
        "Ticket promedio": 10,
        "Claridad de la oferta": 12,
        "Urgencia": 10,
        "Presupuesto": 10,
        "Margen estimado": 12,
        "Complejidad": 8,
        "Probabilidad de cumplir objetivo": 16,
    },
    "cost_categories": [
        "Sueldo SDR asignado",
        "Gestion y supervision",
        "Licencias y CRM",
        "Plataforma de correo",
        "Bases de datos",
        "Herramientas de IA",
        "Telefonia y WhatsApp",
        "Dominios e infraestructura",
    ],
    "defaults": {
        "currency": "CLP",
        "margin": 40,
        "minimum_margin": 30,
        "contract_months": 5,
        "followups": ["Dia 0", "Dia 3", "Dia 7", "Dia 12", "Dia 20"],
    },
    "updated_at": date(2026, 7, 23).isoformat(),
}


LEGACY_STANDARD_PRESENTATION = [
    {
        "title": "Que hacemos",
        "headline": "Operamos la prospeccion comercial de tu empresa",
        "body": (
            "Desde la identificacion del mercado objetivo hasta el agendamiento "
            "y evaluacion de oportunidades comerciales."
        ),
        "sections": [
            ("Prospeccion", "Identificamos empresas, contactamos personas adecuadas, hacemos seguimiento y abrimos conversaciones comerciales."),
            ("Gestion de Prospeccion", "Investigacion, segmentacion, bases, contacto, seguimiento, llamadas, agendamiento, evaluacion, reportería e inteligencia comercial."),
            ("Bases de Datos Comerciales", "Empresas, industrias, paises, cargos, correos y telefonos cuando la modalidad lo incluye."),
        ],
    },
    {
        "title": "Como definimos el mercado",
        "headline": "Dos caminos que pueden operar en paralelo",
        "body": "Conprospeccion puede identificar nuevas empresas segun ICP o trabajar sobre empresas objetivo entregadas por el cliente.",
        "sections": [
            ("Cliente ideal", "Tipo de empresa con mayor probabilidad de necesitar y comprar la solucion."),
            ("Personas objetivo", "Cargos que deciden, influyen o participan en la compra."),
            ("Base de ejemplo", "Demo configurable para mostrar estructura, filtros y profundidad de datos."),
        ],
    },
    {
        "title": "Como operamos",
        "headline": "La estrategia se revisa, aprende y optimiza",
        "body": "Contacto multicanal, tareas, automatizaciones, ejecutivo responsable, llamadas consultivas y preparacion previa.",
        "sections": [
            ("Seguimiento sistematico", "Evita que prospectos con interes queden olvidados."),
            ("Ejecutivo responsable", "La automatizacion apoya al ejecutivo, no lo reemplaza."),
            ("Briefing comercial", "Antes de cada reunion entregamos contexto, antecedentes y recomendaciones."),
        ],
    },
    {
        "title": "Evaluacion e inteligencia",
        "headline": "No entregamos solamente un conteo de actividad",
        "body": "Evaluamos fit, cargo, interes, autoridad, momento comercial, objeciones y senales del mercado.",
        "sections": [
            ("BANT", "Presupuesto, autoridad, necesidad y plazo se usan como apoyo secundario."),
            ("Calidad", "Grabaciones y transcripciones pueden respaldar informacion cuando el proyecto lo permite."),
            ("Intelligence Insight", "Analizamos respuestas, objeciones, cargos, industrias, canales y aprendizajes."),
        ],
    },
    {
        "title": "Implementacion y trabajo conjunto",
        "headline": "Preparamos antes de activar la prospeccion",
        "body": "La etapa previa dura aproximadamente 2 a 4 semanas y protege reputacion, marca e infraestructura.",
        "sections": [
            ("Implementacion", "Estrategia, infraestructura, segmentacion, campanas y validaciones."),
            ("Prospeccion activa", "Lanzamiento, aprendizajes, optimizacion y consolidacion del mercado."),
            ("Playbook SDR", "Mensajes, guiones, criterios, objeciones, respuestas y aprendizajes del proyecto."),
        ],
    },
]


STANDARD_PRESENTATION = [
    {
        "layout": "cover",
        "title": "Prospección B2B que abre mercado y genera oportunidades",
        "headline": "Estrategia, inteligencia comercial y activacion multicanal",
        "body": (
            "Operamos la prospección para que tu equipo comercial se concentre en cerrar ventas."
        ),
        "sections": [
            ("Presentación comercial 2026", "Confidencial - Conprospección"),
        ],
    },
    {
        "layout": "challenge",
        "title": "El desafío: crecer exige un sistema",
        "headline": "Abrir mercado requiere coordinar cuatro preguntas clave",
        "body": (
            "Abrir un nuevo mercado o industria requiere un sistema coordinado que responda "
            "preguntas fundamentales de forma integrada, no como esfuerzos aislados."
        ),
        "sections": [
            ("¿Dónde existe una oportunidad real?", "Identificación de mercados, países e industrias con alta demanda y potencial de apertura."),
            ("¿Qué empresas tienen potencial?", "Definición del cliente ideal para filtrar solo las cuentas con valor estratégico."),
            ("¿Quién es el decisor correcto?", "Localización de las personas con autoridad o influencia para avanzar comercialmente."),
            ("¿Cómo generar una reunión?", "Activación de canales, mensajes y seguimiento para convertir interés en una oportunidad agendada."),
        ],
        "flow": ["Mercado", "Prospectos", "Conversaciones", "Oportunidades"],
    },
    {
        "layout": "services",
        "title": "Dos servicios. Un mismo objetivo.",
        "headline": "Conprospección 2026 | Estrategia de crecimiento",
        "body": (
            "Ofrecemos la gestión completa del proceso de prospección o construimos la inteligencia comercial "
            "para que el equipo del cliente la ejecute internamente."
        ),
        "sections": [
            ("Gestión de prospección", "Diseñamos, implementamos y gestionamos campañas para abrir mercado, generar conversaciones y agendar reuniones calificadas directamente en tu calendario."),
            ("Inteligencia y bases", "Construimos universos de empresas y decisores segmentados, enriquecidos y validados según tu ICP, listos para ser activados por tu fuerza de ventas."),
        ],
    },
    {
        "layout": "operation",
        "title": "Cómo operamos",
        "headline": "De la estrategia de datos a campañas multicanal",
        "body": (
            "No solo implementamos campañas. Primero definimos desde dónde extraer oportunidades "
            "y luego activamos correo, WhatsApp, llamadas y seguimiento para convertirlas en reuniones."
        ),
        "sections": [
            ("Señales de intención de compra", "Detectamos publicaciones, frases, problemas o requerimientos que muestran una posible necesidad concreta. Luego identificamos empresa, decisores y datos de contacto."),
            ("ICP + Buyer Persona", "Definimos país, industria, tamaño, facturación si aplica, tecnologías y cargos que participan en la decisión. Con eso construimos la base."),
            ("Cuentas objetivo del cliente", "El cliente puede entregar solo nombres de empresas. Conprospección identifica los buyer personas adecuados, obtiene sus datos y ejecuta la prospección."),
            ("Empresas similares o lookalike", "Partimos de clientes actuales, históricos o casos de éxito y buscamos empresas con características similares de industria, tamaño, modelo, ubicación o necesidad."),
        ],
        "flow": ["Estrategia", "Datos", "Campañas multicanal", "Seguimiento", "Reunión"],
    },
    {
        "layout": "next",
        "title": "Cómo seguimos después de esta reunión",
        "headline": "De la conversacion a una propuesta personalizada",
        "body": (
            "Con la información conversada, evaluamos mercado, definimos alcance y enviamos una propuesta "
            "personalizada junto al brochure comercial."
        ),
        "sections": [
            ("Propuesta personalizada", "Resumen del caso, oportunidad de mercado, alcance recomendado, inversión y próximos pasos."),
            ("Lectura de mercado", "Insights clave, oportunidades, riesgos e industrias o segmentos sugeridos."),
            ("Alcance recomendado", "Enfoque, fuentes, cobertura, canales y condiciones para alcanzar el objetivo."),
            ("Seguimiento comercial", "Despues del envio, dejamos programado el seguimiento de propuesta para no perder continuidad."),
        ],
        "flow": ["Validamos foco", "Investigamos mercado", "Definimos alcance", "Enviamos propuesta", "Activamos seguimiento"],
    },
]


BRIEFING_DEMO = {
    "company": "Nadilop",
    "contact": "Nicole Diaz",
    "role": "Contacto comercial",
    "industry": "Servicios TI / tecnologia B2B",
    "origin": "Reunion comercial",
    "context": "Empresa de servicios tecnologicos B2B con foco en infraestructura, soporte, licenciamiento y continuidad operativa.",
    "topics": "Linea comercial a priorizar, industrias objetivo, cargos compradores, cuentas definidas y objetivo de prospeccion.",
    "interest": "Validar si Conprospeccion puede abrir conversaciones con empresas y cargos tecnicos/comerciales relevantes.",
    "need": "Ordenar prospeccion y agendamiento sin depender solo de referidos o ventas internas.",
    "objections": "Validar calidad de contactos, proteccion de marca, foco de mercado y capacidad de seguimiento.",
    "recommendations": "Comenzar mostrando lo investigado, validar el servicio a prospectar y preguntar si trabajaremos por cliente ideal, cuentas definidas o ambas rutas.",
    "owner": "Francisca",
}
