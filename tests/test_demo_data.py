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

APP_DEMO = ROOT / "demo"
PAGINA_DEMO = APP_DEMO / "pages" / "demo_reuniones.py"
PAGINA_ONBOARDING = APP_DEMO / "pages" / "demo.py"
ENTRADA_DEMO = APP_DEMO / "app.py"
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
    [ROOT / "shared" / "demo_data.py", PAGINA_DEMO, PAGINA_ONBOARDING, PLANTILLA],
    ids=["demo_data", "pagina_demo", "pagina_onboarding", "plantilla"],
)
def test_el_demo_no_puede_tocar_supabase(archivo):
    """Garantia dura: sin estos imports, escribir en produccion es imposible."""
    importados = _imports_de(archivo)
    assert not (importados & MODULOS_PROHIBIDOS)
    assert not (importados & NOMBRES_PROHIBIDOS)


# ── Separacion entre la app demo y el panel interno ──────────────────────────
def test_la_app_demo_solo_contiene_las_dos_paginas_del_demo():
    """Streamlit expone por URL TODAS las paginas de una app.

    Mientras el demo vivia en dashboard/pages, un prospecto que escribiera
    /Seguimiento_Reuniones aterrizaba en el login del equipo. Aqui esas paginas
    no existen: no hay URL que adivinar.
    """
    paginas = sorted(p.name for p in (APP_DEMO / "pages").glob("*.py"))
    assert paginas == ["demo.py", "demo_intelligence.py", "demo_reuniones.py"]


def test_ninguna_pagina_interna_quedo_dentro_de_la_app_demo():
    internas = {"1_Seguimiento_Reuniones", "2_Clientes", "9_SDRs",
                "16_Client_Setup_OS", "19_BambuTech_Intelligence_Insight",
                "20_GBS_Intelligence_Insight"}
    nombres = {p.stem for p in APP_DEMO.rglob("*.py")}
    assert not (nombres & internas)


def test_el_panel_interno_ya_no_expone_las_paginas_demo():
    """Tampoco al reves: el equipo no ve el demo mezclado con su trabajo."""
    paginas_internas = {p.stem for p in (ROOT / "dashboard" / "pages").glob("*.py")}
    assert not any(nombre.lower().startswith("demo") or "_demo_" in nombre.lower()
                   for nombre in paginas_internas)


def test_la_entrada_del_demo_exige_autenticacion_antes_de_cualquier_pagina():
    entrada = ENTRADA_DEMO.read_text(encoding="utf-8")
    assert 'require_auth_client("demo")' in entrada
    # El st.stop() debe ir antes del switch_page, o el gate no sirve de nada.
    assert entrada.index("st.stop()") < entrada.index("st.switch_page")


# ── Registro de componentes ──────────────────────────────────────────────────
def _nombre_de_componente(archivo: Path) -> str | None:
    """Extrae el `name=` que la pagina pasa a render_meeting_component."""
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    for nodo in ast.walk(arbol):
        if (
            isinstance(nodo, ast.Call)
            and isinstance(nodo.func, ast.Name)
            and nodo.func.id == "render_meeting_component"
        ):
            for kw in nodo.keywords:
                if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                    return kw.value.value
            return None  # usa el nombre por defecto
    return None


def test_el_demo_registra_su_componente_con_nombre_propio():
    """El registro de componentes de Streamlit es global a la aplicacion.

    Si el panel interno y el demo declaran el mismo nombre con directorios
    distintos, el segundo sobrescribe al primero y una pagina termina sirviendo
    el HTML de la otra. Con datos reales de por medio, eso es una fuga.
    """
    panel_interno = ROOT / "dashboard" / "pages" / "1_Seguimiento_Reuniones.py"
    nombre_demo = _nombre_de_componente(PAGINA_DEMO)

    assert nombre_demo is not None, "la pagina demo debe pasar un name explicito"
    assert nombre_demo != _nombre_de_componente(panel_interno)
    assert nombre_demo != "seguimiento_reuniones_operativo"


def test_el_demo_escribe_su_componente_en_su_propio_directorio():
    """Dos directorios distintos, o una pagina pisaria el index.html de la otra."""
    demo = PAGINA_DEMO.read_text(encoding="utf-8")
    interno = (ROOT / "dashboard" / "pages" / "1_Seguimiento_Reuniones.py").read_text(
        encoding="utf-8"
    )
    assert "cp_demo_panel_reuniones_component" in demo
    assert "cp_demo_panel_reuniones_component" not in interno


# ── Formulario de onboarding ─────────────────────────────────────────────────
@pytest.fixture(scope="module")
def onboarding() -> str:
    return PAGINA_ONBOARDING.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def onboarding_visible(onboarding) -> str:
    """El codigo sin docstring de modulo ni comentarios.

    El docstring documenta de que archivo viene la pagina, y ese nombre incluye a
    un cliente real. Es texto para quien lee el codigo, no para el prospecto.
    """
    arbol = ast.parse(onboarding)
    doc = ast.get_docstring(arbol)
    src = onboarding.replace(doc, "", 1) if doc else onboarding
    return "\n".join(l for l in src.split("\n") if not l.strip().startswith("#"))


def test_el_onboarding_no_menciona_a_ningun_cliente_real(onboarding_visible):
    """El original venia lleno de referencias a GBS: dominio, ejecutivo, nicho."""
    prohibidos = ("gbs", "bambutech", "clickie", "tiresias", "Sam Miller",
                  "thermoliner", "DHL", "freight forwarder", "COMEX")
    minusculas = onboarding_visible.lower()
    for termino in prohibidos:
        assert termino.lower() not in minusculas, termino


def test_el_onboarding_no_trae_datos_precargados(onboarding):
    """El original traia defaults del ICP de GBS. Aqui todo empieza en blanco."""
    assert "default=[]" in onboarding
    assert "default=[\"" not in onboarding
    # Ni valores iniciales en campos de texto o numero.
    assert 'value="' not in onboarding
    assert "value=None" in onboarding


def test_el_onboarding_deja_las_listas_desplegables_sin_seleccion(onboarding):
    """index=None obliga al prospecto a elegir; sin eso Streamlit preselecciona."""
    assert onboarding.count("index=None") >= 4


def test_el_onboarding_usa_la_paleta_de_conprospeccion(onboarding):
    """Misma marca que el panel de Seguimiento de Reuniones."""
    assert "from shared.cp_design import" in onboarding
    # Sin rastros del morado de GBS.
    for morado in ("#7c3aed", "#4c1d95", "#5b21b6", "#ede9fe"):
        assert morado not in onboarding


def test_el_envio_del_onboarding_avisa_que_no_guarda_nada(onboarding):
    assert "nada de lo que escribas se almacena" in onboarding
    assert "upsert" not in onboarding
    assert "_notify_telegram" not in onboarding


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
    """No debe pisar el localStorage del panel interno."""
    assert "cp_meetings_demo_v1" in html_demo
    assert "cp_meetings_v5_poc_detail_v2" not in html_demo


def test_los_cambios_del_prospecto_no_sobreviven_a_una_recarga(html_demo):
    """El HTML escribe en localStorage pero no restaura las reuniones desde ahi.

    Si alguien reintrodujera esa restauracion, el demo arrastraria los cambios de
    un prospecto al siguiente. Es la unica razon por la que el portal no necesita
    limpieza entre demos.
    """
    assert "meetings=savedMeetings" not in html_demo


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
