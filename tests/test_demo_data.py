"""Tests de las reuniones ficticias del portal demo.

Lo critico que se protege aqui:
  1. El demo es incapaz de tocar Supabase (aislamiento por imports).
  2. Los objetos tienen la misma forma que consume el JavaScript del panel.
  3. Los estados usan el vocabulario exacto de los labels del panel interno,
     o los filtros del prospecto no encuentran nada.
  4. La plantilla HTML conserva el punto de inyeccion que la pagina demo usa.
"""

import ast
import sys
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shared import demo_data

PAGINA_DEMO = ROOT / "dashboard" / "pages" / "21_Demo_Panel_Reuniones.py"
PLANTILLA = ROOT / "dashboard" / "seguimiento_poc_template.py"

MODULOS_PROHIBIDOS = {"requests", "supabase", "shared.config", "meeting_shared"}
NOMBRES_PROHIBIDOS = {"supabase_url", "supabase_key"}

# Vocabulario que produce 1_Seguimiento_Reuniones.py. Si el demo se sale de aqui,
# los filtros y KPIs del panel quedan vacios.
STATUS = {"Reunión futura", "Reunión realizada", "Reunión cancelada", "Reagendar reunión"}
CP = {"Válida", "No válida", "Pendiente"}
CLIENT_VAL = {"Válida", "No válida", "Solicita revisión", "Pendiente"}
FINAL = {"Reunión válida", "Reunión no válida", "Reunión cancelada",
         "Reagendar reunión", "Pendiente"}
CASO = {"Cerrado", "En revisión", "En evaluación CP", "Esperando cliente", "Abierto"}


@pytest.fixture(scope="module")
def reuniones():
    return demo_data.cargar_reuniones_demo()


# ── Aislamiento ──────────────────────────────────────────────────────────────
def _imports_de(path: Path) -> set[str]:
    arbol = ast.parse(path.read_text(encoding="utf-8"))
    encontrados = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            encontrados.update(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom):
            if nodo.module:
                encontrados.add(nodo.module)
            encontrados.update(alias.name for alias in nodo.names)
    return encontrados


@pytest.mark.parametrize(
    "archivo",
    [ROOT / "shared" / "demo_data.py", PAGINA_DEMO, PLANTILLA],
    ids=["demo_data", "pagina_demo", "plantilla"],
)
def test_el_demo_no_puede_tocar_supabase(archivo):
    """Garantia dura: sin estos imports, escribir en produccion es imposible."""
    importados = _imports_de(archivo)
    assert not (importados & MODULOS_PROHIBIDOS)
    assert not (importados & NOMBRES_PROHIBIDOS)


def test_la_plantilla_solo_usa_la_libreria_estandar():
    """Debe poder importarse desde el demo sin arrastrar Supabase."""
    assert _imports_de(PLANTILLA) == {"json", "re"}


# ── Construccion del HTML del demo ───────────────────────────────────────────
@pytest.fixture(scope="module")
def html_demo(reuniones):
    sys.path.insert(0, str(ROOT / "dashboard"))
    from seguimiento_poc_template import construir_html_demo

    return construir_html_demo(reuniones, "data:image/png;base64,AAA")


def test_el_html_no_expone_la_identidad_del_equipo_interno(html_demo):
    assert "Francisca" not in html_demo
    assert "Yanina" not in html_demo
    assert "Panel interno" not in html_demo


def test_el_html_lleva_las_reuniones_ficticias_inyectadas(html_demo):
    assert "Lead Demo 1" in html_demo
    assert "Cliente Demo" in html_demo
    assert "__CP_MARK__" not in html_demo


def test_el_html_usa_su_propia_clave_de_almacenamiento(html_demo):
    """No debe compartir estado de navegador con el panel interno."""
    assert "cp_meetings_demo_v1" in html_demo
    assert "cp_meetings_v5_poc_detail_v2" not in html_demo


def test_si_la_plantilla_pierde_el_punto_de_inyeccion_falla_ruidosamente(monkeypatch):
    """Sin esto, el demo mostraria en silencio las reuniones de ejemplo de la plantilla."""
    sys.path.insert(0, str(ROOT / "dashboard"))
    import seguimiento_poc_template as plantilla

    monkeypatch.setattr(plantilla, "POC_HTML", "<html>sin bloque de meetings</html>")
    with pytest.raises(plantilla.PlantillaDesincronizada):
        plantilla.construir_html_demo([], "")


# ── Anonimato ────────────────────────────────────────────────────────────────
def test_ningun_cliente_real_aparece_en_el_demo(reuniones):
    prohibidos = ("gbs", "bambutech", "clickie", "tiresias", "ecosmart", "just4u")
    blob = str(reuniones).lower()
    for nombre in prohibidos:
        assert nombre not in blob


def test_hay_un_solo_cliente_y_se_llama_cliente_demo(reuniones):
    assert {r["client"] for r in reuniones} == {"Cliente Demo"}
    assert {r["clientSlug"] for r in reuniones} == {"demo"}


def test_los_contactos_son_leads_demo(reuniones):
    for r in reuniones:
        assert r["contact"].startswith("Lead Demo ")
        assert r["company"].startswith("Empresa Demo ")


# ── Forma de los datos ───────────────────────────────────────────────────────
def test_los_ids_son_unicos(reuniones):
    ids = [r["id"] for r in reuniones]
    assert len(ids) == len(set(ids))


def test_cada_reunion_trae_las_claves_que_el_javascript_consume(reuniones):
    requeridas = {
        "id", "clientSlug", "date", "time", "sortKey", "client", "company",
        "contact", "role", "sdr", "status", "cp", "clientVal", "final",
        "caseStatus", "email", "phone", "country", "industry", "icp", "bant",
        "evidence", "history", "goal",
    }
    for r in reuniones:
        assert requeridas <= set(r)


def test_el_bant_tiene_las_cuatro_variables(reuniones):
    for r in reuniones:
        assert set(r["bant"]) == {"Budget", "Authority", "Need", "Timeline"}
        assert all(isinstance(v, bool) for v in r["bant"].values())


def test_los_estados_usan_el_vocabulario_del_panel(reuniones):
    for r in reuniones:
        assert r["status"] in STATUS
        assert r["cp"] in CP
        assert r["clientVal"] in CLIENT_VAL
        assert r["final"] in FINAL
        assert r["caseStatus"] in CASO


def test_la_meta_del_demo_son_doce_reuniones(reuniones):
    assert {r["goal"] for r in reuniones} == {12}


# ── Que la historia se entienda ──────────────────────────────────────────────
def test_todos_los_estados_de_agenda_tienen_al_menos_una_reunion(reuniones):
    """Si un filtro queda vacio, el prospecto no ve para que sirve."""
    presentes = {r["status"] for r in reuniones}
    assert presentes == STATUS


def test_hay_reuniones_validas_no_validas_y_pendientes(reuniones):
    finales = [r["final"] for r in reuniones]
    assert finales.count("Reunión válida") == 3
    assert finales.count("Reunión no válida") == 1
    assert finales.count("Reunión cancelada") == 1
    assert finales.count("Reagendar reunión") == 1


def test_hay_una_reunion_en_revision_del_cliente(reuniones):
    en_revision = [r for r in reuniones if r["clientVal"] == "Solicita revisión"]
    assert len(en_revision) == 1
    assert en_revision[0]["caseStatus"] == "En revisión"
    assert en_revision[0]["clientComment"]


def test_la_reunion_no_valida_explica_por_que(reuniones):
    no_valida = next(r for r in reuniones if r["final"] == "Reunión no válida")
    assert no_valida["icp"] == "No cumple"
    assert "ICP" in no_valida["just"]
    assert not any(no_valida["bant"].values())


# ── Fechas ───────────────────────────────────────────────────────────────────
def test_las_reuniones_futuras_estan_en_el_futuro_y_el_resto_en_el_pasado(reuniones):
    hoy = demo_data.hoy_chile()
    for r in reuniones:
        fecha = datetime.strptime(r["date"], "%d/%m/%Y").date()
        if r["status"] == "Reunión futura":
            assert fecha > hoy
        else:
            assert fecha <= hoy


def test_no_se_exponen_grabaciones_ni_transcripciones(reuniones):
    for r in reuniones:
        assert r["recordingUrl"] == ""
        assert r["transcriptUrl"] == ""
        tipos = {e["type"] for e in r["evidence"]}
        assert not (tipos & {"Grabación", "Transcripción"})
