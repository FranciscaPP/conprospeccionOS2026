"""Reuniones ficticias del portal demo.

Sustituye a `meeting_shared.cargar_reuniones_reales_poc()`, que lee cinco tablas
de Supabase. Devuelve exactamente la misma forma de objeto que consume el
JavaScript del panel operativo, de modo que la interfaz que ve el prospecto es
la misma que entregamos.

AISLAMIENTO: no importa requests, supabase ni shared.config. La pagina demo es
incapaz de leer o escribir en produccion. tests/test_demo_data.py lo verifica.

Todo dato aqui es inventado. Un unico cliente, "Cliente Demo", y contactos
"Lead Demo N". Ningun nombre de cliente, empresa o persona real.

Vocabulario de estados (debe calzar con los labels que produce
1_Seguimiento_Reuniones.py, o los filtros del panel no encuentran nada):
  status     : Reunion futura | Reunion realizada | Reunion cancelada | Reagendar reunion
  cp         : Valida | No valida | Pendiente
  clientVal  : Valida | No valida | Solicita revision | Pendiente
  final      : Reunion valida | Reunion no valida | Reunion cancelada | Reagendar reunion | Pendiente
  caseStatus : Cerrado | En revision | En evaluacion CP | Esperando cliente | Abierto
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from shared.metas import meta_de

# Streamlit Cloud corre en UTC; las reuniones son hora de Chile. No se reutiliza
# _now_chile() porque vive en dashboard/ y shared/ no debe depender de dashboard/.
_CHILE_TZ = ZoneInfo("America/Santiago")

SLUG = "demo"
CLIENTE = "Cliente Demo"
SDR = "SDR Demo"


def hoy_chile() -> date:
    return datetime.now(_CHILE_TZ).date()


def _fin_de_mes(d: date) -> date:
    return (d.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)


def _reparto(desde: date, hasta: date, cuantas: int) -> list[date]:
    """Reparte `cuantas` fechas entre dos extremos, ambos incluidos."""
    if cuantas == 1 or hasta <= desde:
        return [desde] * cuantas
    tramo = (hasta - desde).days
    return [desde + timedelta(days=round(i * tramo / (cuantas - 1))) for i in range(cuantas)]


def _fechas_del_mes(pasadas: int, futuras: int) -> tuple[list[date], list[date]]:
    """Fechas repartidas dentro del mes en curso.

    El panel filtra por mes en curso por defecto. Si las reuniones cayeran en el
    mes anterior, el prospecto abriria el demo y lo veria vacio. Por eso las
    fechas se anclan al mes actual y no a un offset fijo desde hoy.

    Casos borde: el dia 1 no hay pasado dentro del mes (todas quedan hoy), y el
    ultimo dia no hay futuro (las futuras se van al mes siguiente). Es preferible
    a mostrar un panel vacio.
    """
    hoy = hoy_chile()
    inicio, fin = hoy.replace(day=1), _fin_de_mes(hoy)
    antes = _reparto(inicio, hoy, pasadas)
    if fin > hoy:
        despues = _reparto(hoy + timedelta(days=1), fin, futuras)
    else:
        despues = [hoy + timedelta(days=i + 1) for i in range(futuras)]
    return antes, despues


def _fmt_fecha(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def _fmt_hora(hora: int, minuto: int) -> str:
    sufijo = "PM" if hora >= 12 else "AM"
    return f"{hora % 12 or 12:02d}:{minuto:02d} {sufijo}"


def _sort_key(d: date, hora: int, minuto: int) -> str:
    return f"{d:%Y%m%d}{hora:02d}{minuto:02d}"


def _bant(budget=False, authority=False, need=False, timeline=False) -> dict[str, bool]:
    return {
        "Budget": budget,
        "Authority": authority,
        "Need": need,
        "Timeline": timeline,
    }


def _caso(cp: str, client_val: str, final: str) -> str:
    """Misma regla que _case_status() del panel interno."""
    if final != "Pendiente":
        return "Cerrado"
    if client_val == "Solicita revisión":
        return "En revisión"
    if cp == "Pendiente":
        return "En evaluación CP"
    if client_val == "Pendiente":
        return "Esperando cliente"
    return "Abierto"


def _evidencia(resumen: str = "", evidencia_ia: str = "") -> list[dict[str, Any]]:
    """Sin grabacion ni transcripcion: no exponemos material real en el demo."""
    ev = []
    if resumen:
        ev.append({"type": "Resumen IA", "name": "Resumen disponible",
                   "text": resumen, "valid": True})
    if evidencia_ia:
        ev.append({"type": "Evidencia IA", "name": "Evidencia detectada",
                   "text": evidencia_ia, "valid": True})
    return ev


def _historial(d: date, hora: int, eventos: tuple) -> list[dict[str, Any]]:
    """Fecha el historial a partir de la reunion, una hora despues de cada evento.

    Asi el prospecto ve una traza coherente con la fecha de la reunion, en vez de
    textos fijos que se desincronizan cuando el demo se abre otro dia.
    """
    salida = []
    for indice, (campo, desde, hasta) in enumerate(eventos):
        marca = datetime.combine(d, datetime.min.time()) + timedelta(hours=hora + 1 + indice)
        salida.append({
            "when": marca.strftime("%Y-%m-%d %H:%M"),
            "user": "Conprospección",
            "field": campo,
            "from": desde,
            "to": hasta,
            "visibility": "Solo uso interno",
        })
    return salida


# ── Las reuniones ────────────────────────────────────────────────────────────
# Cada una existe para que un estado del panel tenga contenido: si un filtro o
# un KPI queda en cero, el prospecto no ve para que sirve.
_GUION: list[dict[str, Any]] = [
    {
        "h": 10, "m": 30,
        "contacto": "Lead Demo 1", "empresa": "Empresa Demo 1",
        "cargo": "Gerente de Operaciones", "industria": "Logística y transporte",
        "status": "Reunión realizada", "cp": "Válida", "cli": "Válida",
        "final": "Reunión válida",
        "bant": _bant(True, True, True, True),
        "icp": "Cumple",
        "info": "Flota propia de 40 camiones. Controlan despachos en planillas y "
                "pierden visibilidad de cada carga. Buscan cerrar proveedor este trimestre.",
        "just": "Cumple ICP y las cuatro variables BANT confirmadas.",
        "next": "Propuesta enviada. Segunda reunión con gerencia general.",
        "resumen": "Confirmó presupuesto asignado y es quien decide. La falta de "
                   "trazabilidad es su principal dolor operativo.",
        "evidencia_ia": "Menciona presupuesto aprobado y plazo de decisión a 60 días.",
        "historial": (
            ("val_estado_cp", "Pendiente", "Válida"),
            ("val_estado_cli", "Pendiente", "Válida"),
            ("val_estado_final", "Pendiente", "Reunión válida"),
        ),
    },
    {
        "h": 16, "m": 0,
        "contacto": "Lead Demo 2", "empresa": "Empresa Demo 2",
        "cargo": "Director de Supply Chain", "industria": "Alimentos y bebidas",
        "status": "Reunión realizada", "cp": "Válida", "cli": "Válida",
        "final": "Reunión válida",
        "bant": _bant(True, True, True, False),
        "icp": "Cumple",
        "info": "Distribuyen a 180 locales. Necesitan reducir quiebres de stock. "
                "Pidieron cotización formal durante la misma reunión.",
        "just": "Interés inmediato. Traspaso al equipo comercial.",
        "next": "Cotización en preparación.",
        "resumen": "Solicitó propuesta económica en la llamada.",
        "evidencia_ia": "Solicitud explícita de cotización.",
        "historial": (
            ("val_estado_cp", "Pendiente", "Válida"),
            ("val_estado_final", "Pendiente", "Reunión válida"),
        ),
    },
    {
        "h": 11, "m": 15,
        "contacto": "Lead Demo 3", "empresa": "Empresa Demo 3",
        "cargo": "Gerente General", "industria": "Manufactura",
        "status": "Reunión realizada", "cp": "Válida", "cli": "Válida",
        "final": "Reunión válida",
        "bant": _bant(False, True, True, True),
        "icp": "Cumple",
        "info": "Planta de 240 empleados. Despachan a faenas y coordinan por teléfono. "
                "Evalúan dos proveedores este semestre.",
        "just": "Cumple ICP. Tres variables BANT confirmadas.",
        "next": "Enviar caso de éxito del rubro.",
        "resumen": "La gerencia general participó y fijó plazo de decisión a 90 días.",
        "evidencia_ia": "Autoridad de decisión confirmada. Presupuesto sin monto.",
        "historial": (
            ("val_estado_cp", "Pendiente", "Válida"),
            ("val_estado_cli", "Pendiente", "Válida"),
            ("val_estado_final", "Pendiente", "Reunión válida"),
        ),
    },
    {
        "h": 15, "m": 30,
        "contacto": "Lead Demo 4", "empresa": "Empresa Demo 4",
        "cargo": "Jefe de Abastecimiento", "industria": "Retail y consumo",
        "status": "Reunión realizada", "cp": "Válida", "cli": "Pendiente",
        "final": "Pendiente",
        "bant": _bant(True, False, True, True),
        "icp": "Cumple",
        "info": "Operación multibodega en tres regiones. Interesados en trazabilidad "
                "de última milla.",
        "just": "Cumple ICP y tres variables BANT. A la espera de confirmación del cliente.",
        "next": "Esperando validación del cliente.",
        "resumen": "Necesidad clara y plazo definido. La decisión final la toma su gerencia.",
        "evidencia_ia": "Necesidad y plazo confirmados en la conversación.",
        "historial": (
            ("val_estado_cp", "Pendiente", "Válida"),
        ),
    },
    {
        "h": 9, "m": 45,
        "contacto": "Lead Demo 5", "empresa": "Empresa Demo 5",
        "cargo": "Gerente de Logística", "industria": "Construcción",
        "status": "Reunión realizada", "cp": "Válida", "cli": "Solicita revisión",
        "final": "Pendiente",
        "bant": _bant(False, True, True, False),
        "icp": "Cumple",
        "info": "Obras simultáneas en dos regiones. Coordinan despachos a faena.",
        "just": "Cumple ICP. Dos variables BANT confirmadas.",
        "next": "Resolver solicitud de revisión del cliente.",
        "clientReason": "bant_insuficiente",
        "clientComment": "A nuestro juicio no quedó confirmado el presupuesto.",
        "resumen": "Interés declarado, sin confirmación de presupuesto.",
        "evidencia_ia": "Autoridad y necesidad presentes. Presupuesto no mencionado.",
        "historial": (
            ("val_estado_cp", "Pendiente", "Válida"),
            ("val_estado_cli", "Pendiente", "Solicita revisión"),
        ),
    },
    {
        "h": 12, "m": 0,
        "contacto": "Lead Demo 6", "empresa": "Empresa Demo 6",
        "cargo": "Socio", "industria": "Servicios profesionales",
        "status": "Reunión realizada", "cp": "No válida", "cli": "Pendiente",
        "final": "Reunión no válida",
        "bant": _bant(),
        "icp": "No cumple",
        "info": "Oficina de 12 personas, sin operación logística.",
        "just": "Fuera de ICP: industria y tamaño no corresponden al perfil acordado. "
                "No se contabiliza para la meta.",
        "next": "Descartado. No se factura al cliente.",
        "finalReason": "Fuera del perfil de cliente ideal definido en el onboarding.",
        "resumen": "Sin necesidad logística identificable.",
        "evidencia_ia": "Ninguna variable BANT detectada.",
        "historial": (
            ("val_estado_cp", "Pendiente", "No válida"),
            ("val_estado_final", "Pendiente", "Reunión no válida"),
        ),
    },
    {
        "h": 17, "m": 0,
        "contacto": "Lead Demo 7", "empresa": "Empresa Demo 7",
        "cargo": "Gerente de Operaciones", "industria": "Minería",
        "status": "Reunión realizada", "cp": "Pendiente", "cli": "Pendiente",
        "final": "Pendiente",
        "bant": _bant(False, True, True, False),
        "icp": "No evaluado",
        "info": "Contratista minero con flota mixta. Primera conversación exploratoria.",
        "just": "",
        "next": "Pendiente de evaluación interna.",
        "resumen": "Conversación exploratoria. Falta profundizar en presupuesto y plazos.",
        "evidencia_ia": "",
        "historial": (),
    },
    {
        "h": 10, "m": 0,
        "contacto": "Lead Demo 8", "empresa": "Empresa Demo 8",
        "cargo": "Gerente Comercial", "industria": "Logística y transporte",
        "status": "Reagendar reunión", "cp": "Pendiente", "cli": "Pendiente",
        "final": "Reagendar reunión",
        "bant": _bant(need=True),
        "icp": "No evaluado",
        "info": "Confirmó asistencia el día anterior y no se conectó. Pidió mover "
                "la reunión a la semana siguiente.",
        "just": "",
        "next": "Coordinar nueva fecha.",
        "rescheduleWho": "Prospecto",
        "rescheduleReason": "No asistió",
        "rescheduleComment": "Solicitó nueva fecha por WhatsApp la misma tarde.",
        "resumen": "",
        "evidencia_ia": "",
        "historial": (
            ("status_reunion", "Reunión realizada", "Reagendar reunión"),
        ),
    },
    {
        "h": 14, "m": 30,
        "contacto": "Lead Demo 9", "empresa": "Empresa Demo 9",
        "cargo": "Jefe de Operaciones", "industria": "Alimentos y bebidas",
        "status": "Reunión cancelada", "cp": "Pendiente", "cli": "Pendiente",
        "final": "Reunión cancelada",
        "bant": _bant(),
        "icp": "No evaluado",
        "info": "Cancelaron por reestructuración interna del área.",
        "just": "",
        "next": "Retomar contacto en el próximo trimestre.",
        "cancelWho": "Prospecto",
        "cancelReason": "Reestructuración interna",
        "cancelComment": "Pidieron retomar en tres meses.",
        "resumen": "",
        "evidencia_ia": "",
        "historial": (
            ("status_reunion", "Reunión futura", "Reunión cancelada"),
        ),
    },
    {
        "h": 11, "m": 0,
        "contacto": "Lead Demo 10", "empresa": "Empresa Demo 10",
        "cargo": "Director de Operaciones", "industria": "Manufactura",
        "status": "Reunión futura", "cp": "Pendiente", "cli": "Pendiente",
        "final": "Pendiente",
        "bant": _bant(need=True, timeline=True),
        "icp": "No evaluado",
        "info": "Agendada por el SDR tras dos intentos de contacto. Interesados en "
                "reducir tiempos de despacho.",
        "just": "",
        "next": "Preparar reunión.",
        "resumen": "",
        "evidencia_ia": "",
        "historial": (),
    },
    {
        "h": 9, "m": 30,
        "contacto": "Lead Demo 11", "empresa": "Empresa Demo 11",
        "cargo": "Gerente de Abastecimiento", "industria": "Retail y consumo",
        "status": "Reunión futura", "cp": "Pendiente", "cli": "Pendiente",
        "final": "Pendiente",
        "bant": _bant(need=True),
        "icp": "No evaluado",
        "info": "Solicitó reunión tras recibir el caso de éxito del rubro.",
        "just": "",
        "next": "Preparar reunión.",
        "resumen": "",
        "evidencia_ia": "",
        "historial": (),
    },
]


def _meta_demo() -> int:
    meta = meta_de(SLUG)
    return int(meta["validas"]) if meta else 0


def _reunion(indice: int, guion: dict[str, Any], d: date) -> dict[str, Any]:
    hora, minuto = guion["h"], guion["m"]
    cp, cli, final = guion["cp"], guion["cli"], guion["final"]
    numero = indice + 1
    return {
        "id": 9000 + numero,
        "clientSlug": SLUG,
        "date": _fmt_fecha(d),
        "time": _fmt_hora(hora, minuto),
        "sortKey": _sort_key(d, hora, minuto),
        "scheduledDate": _fmt_fecha(d - timedelta(days=5)),
        "client": CLIENTE,
        "company": guion["empresa"],
        "contact": guion["contacto"],
        "role": guion["cargo"],
        "sdr": SDR,
        "status": guion["status"],
        "cp": cp,
        "clientVal": cli,
        "final": final,
        "caseStatus": _caso(cp, cli, final),
        "email": f"lead{numero}@empresademo{numero}.cl",
        "phone": f"+56 9 {5000 + numero * 7:04d} {1000 + numero * 13:04d}",
        "country": "Chile",
        "industry": guion["industria"],
        "website": f"www.empresademo{numero}.cl",
        "linkedin": "",
        "linkedinCompany": "",
        "companySize": "50-199 empleados",
        "sourceChannel": "Prospección saliente",
        "companyInfo": "",
        "contactInfo": "",
        "ghlContact": "",
        "ghlOpp": "",
        "meet": "Videollamada",
        "recordingUrl": "",
        "transcriptUrl": "",
        "info": guion["info"],
        "operationalNotes": "",
        "icp": guion["icp"],
        "bant": guion["bant"],
        "just": guion["just"],
        "next": guion["next"],
        "notes": "",
        "finalReason": guion.get("finalReason", ""),
        "finalClientText": "",
        "finalInternalNote": "",
        "evidence": _evidencia(guion.get("resumen", ""), guion.get("evidencia_ia", "")),
        "clientReason": guion.get("clientReason", ""),
        "clientComment": guion.get("clientComment", ""),
        "clientDate": "",
        "clientActor": guion["contacto"],
        "clientEvidence": "",
        "cpResponse": "",
        "cancelWho": guion.get("cancelWho", ""),
        "cancelReason": guion.get("cancelReason", ""),
        "cancelComment": guion.get("cancelComment", ""),
        "rescheduleWho": guion.get("rescheduleWho", ""),
        "rescheduleReason": guion.get("rescheduleReason", ""),
        "rescheduleOld": "",
        "rescheduleNew": "",
        "rescheduleComment": guion.get("rescheduleComment", ""),
        "history": _historial(d, hora, guion["historial"]),
        "historyVisibility": {},
        "historialManual": [],
        "goal": _meta_demo(),
    }


def cargar_reuniones_demo() -> list[dict[str, Any]]:
    """Sustituto de cargar_reuniones_reales_poc(). Mismo contrato, datos falsos."""
    futuras = [i for i, g in enumerate(_GUION) if g["status"] == "Reunión futura"]
    pasadas = [i for i, g in enumerate(_GUION) if g["status"] != "Reunión futura"]

    fechas_pasadas, fechas_futuras = _fechas_del_mes(len(pasadas), len(futuras))
    calendario = {
        **dict(zip(pasadas, fechas_pasadas)),
        **dict(zip(futuras, fechas_futuras)),
    }

    reuniones = [_reunion(i, g, calendario[i]) for i, g in enumerate(_GUION)]
    return sorted(reuniones, key=lambda r: r["sortKey"], reverse=True)
