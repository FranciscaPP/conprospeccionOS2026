"""Contratos mínimos del portal BambuTech."""
from pathlib import Path


def test_modulos_bambutech_estan_registrados():
    nav = Path("dashboard/portal_auth.py").read_text(encoding="utf-8")
    for page in (
        "17_BambuTech_Onboarding.py",
        "18_BambuTech_Validacion_Reuniones.py",
        "19_BambuTech_Intelligence_Insight.py",
        "20_BambuTech_Playbook_SDR.py",
    ):
        assert page in nav


def test_validacion_usa_solo_reuniones_reales_bambutech():
    page = Path("dashboard/pages/18_BambuTech_Validacion_Reuniones.py").read_text(encoding="utf-8")
    assert "cliente_slug=eq.bambutech&excluida=eq.false" in page
    assert "PROSPECCION_INICIO = date(2026, 5, 18)" in page
    assert '"bambutech"' in page
    assert '"gbs"' not in page


def test_insight_relaciona_modelo_y_avance_real():
    page = Path("dashboard/pages/19_BambuTech_Intelligence_Insight.py").read_text(encoding="utf-8")
    assert "CONTACTOS, EMPRESAS, RESPUESTAS, POSITIVAS = 526, 176, 14, 5" in page
    assert "flag_meta_countable" in page
    assert "5 reuniones" not in page
    assert "cliente_slug=eq.bambutech" in page
