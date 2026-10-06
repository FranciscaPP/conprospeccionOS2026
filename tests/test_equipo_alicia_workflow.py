from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "equipo-alicia-cloud.yml"


def test_cloud_workflow_contract():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert 'cron: "*/15 * * * *"' in text
    assert "workflow_dispatch:" in text
    assert "update_id:" in text
    assert 'python-version: "3.12"' in text
    assert "timeout-minutes:" in text
    assert "concurrency:" in text
    assert "permissions:" in text and "contents: read" in text
    assert "pip install -r sync/requirements.txt" in text

    required_secrets = (
        "SUPABASE_URL",
        "SUPABASE_SECRET_KEY",
        "GHL_AGENCY_TOKEN",
        "GHL_TOKEN_BAMBUTECH",
        "GHL_TOKEN_GBS_LOGISTICS",
        "GHL_TOKEN_BALIA",
        "GHL_LOCATION_BALIA",
        "TELEGRAM_SDR_TOKEN",
        "TELEGRAM_SDR_CHAT_ID",
    )
    for name in required_secrets:
        assert f"secrets.{name}" in text

    assert "report_sdr_telegram.py --operational --cloud-scheduled --send" in text
    assert "report_sdr_bot.py --cloud-update-id" in text
    assert "TELEGRAM_REUNIONES_" not in text
    assert "TELEGRAM_BOT_" not in text


def test_cloud_runtime_includes_image_dependency():
    requirements = (ROOT / "sync" / "requirements.txt").read_text(encoding="utf-8").lower()
    assert "pillow" in requirements
