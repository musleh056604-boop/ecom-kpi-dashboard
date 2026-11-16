from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlparse

from streamlit.testing.v1 import AppTest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_customer_service_page_shows_offer_and_manual_process_without_upload_or_analytics():
    service = AppTest.from_file(str(PROJECT_ROOT / "service_app.py"), default_timeout=30).run()

    assert not service.exception
    assert len(service.file_uploader) == 0
    assert len(service.metric) == 0
    assert len(service.get("plotly_chart")) == 0
    assert len(service.link_button) == 1

    contact = service.link_button[0]
    assert contact.label == "تواصل عبر واتساب"
    parsed = urlparse(contact.url)
    assert parsed.scheme == "https"
    assert parsed.netloc == "wa.me"
    assert parsed.path == "/966559665030"
    assert "تقرير أداء" in parse_qs(parsed.query)["text"][0]

    visible_text = [item.value for item in service.markdown] + [item.value for item in service.caption]
    assert any("$50–$150" in value for value in visible_text)
    assert any("+966559665030" in value for value in visible_text)
    assert any("الدفع" in value and "تسليم" in value and "يدويًا" in value for value in visible_text)


def test_configured_public_app_entrypoint_is_customer_service_only():
    public = AppTest.from_file(str(PROJECT_ROOT / "app.py"), default_timeout=30).run()

    assert not public.exception
    assert len(public.file_uploader) == 0
    assert len(public.metric) == 0
    assert len(public.get("plotly_chart")) == 0
    assert len(public.link_button) == 1
    assert public.link_button[0].url.startswith("https://wa.me/966559665030?")
    assert any("$50–$150" in item.value for item in public.markdown)


def test_owner_analyzer_remains_a_separate_upload_app():
    owner = AppTest.from_file(str(PROJECT_ROOT / "owner_app.py"), default_timeout=30).run()

    assert not owner.exception
    assert len(owner.file_uploader) == 1
    assert any("ارفع ملفاً للبدء" in item.value for item in owner.info)
