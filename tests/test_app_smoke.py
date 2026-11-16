from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_app() -> AppTest:
    return AppTest.from_file(str(PROJECT_ROOT / "owner_app.py"), default_timeout=30).run()


def test_app_renders_start_screen_without_upload():
    app = run_app()
    assert not app.exception
    assert len(app.file_uploader) == 1
    assert any("ارفع ملفاً للبدء" in item.value for item in app.info)


def test_app_processes_sample_csv_and_renders_kpis_and_charts():
    app = run_app()
    sample = (PROJECT_ROOT / "examples" / "demo_ads.csv").read_bytes()
    app.file_uploader[0].upload("demo_ads.csv", sample, "text/csv")
    app.run()

    assert not app.exception
    assert len(app.link_button) == 1
    assert app.success[0].value == "تمت قراءة الملف: 10 صفاً و7 عموداً."
    metrics = {item.label: item.value for item in app.metric}
    assert metrics["ROAS"] == "3.83×"
    assert metrics["الإنفاق"] == "1,115.00 ر.س"
    assert metrics["الإيراد"] == "4,265.00 ر.س"
    assert metrics["الطلبات"] == "74"
    assert len(app.get("plotly_chart")) == 2


def test_app_marks_kpis_unavailable_when_two_roles_use_same_column():
    app = run_app()
    sample = (PROJECT_ROOT / "examples" / "demo_ads.csv").read_bytes()
    app.file_uploader[0].upload("demo_ads.csv", sample, "text/csv")
    app.run()
    for selector in app.selectbox:
        if selector.label.startswith("الإيراد أو المبيعات"):
            selector.select("Spend")
            break
    app.run()

    assert not app.exception
    assert any("العمود نفسه" in item.value for item in app.warning)
    metrics = {item.label: item.value for item in app.metric}
    assert metrics["ROAS"] == "غير متاح"
    assert metrics["الإيراد"] == "غير متاح"


def test_app_processes_xlsx_upload_from_memory():
    buffer = BytesIO()
    pd.DataFrame(
        {
            "Campaign": ["A", "B"],
            "Spend": [10, 20],
            "Revenue": [40, 80],
            "Orders": [1, 2],
        }
    ).to_excel(buffer, index=False)
    app = run_app()
    app.file_uploader[0].upload(
        "report.xlsx",
        buffer.getvalue(),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    app.run()

    assert not app.exception
    metrics = {item.label: item.value for item in app.metric}
    assert metrics["ROAS"] == "4.00×"
    assert metrics["الإيراد"] == "120.00 ر.س"


def test_app_shows_safe_user_facing_error_for_broken_xlsx():
    app = run_app()
    app.file_uploader[0].upload(
        "broken.xlsx",
        b"not an Excel workbook",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    app.run()

    assert not app.exception
    assert len(app.link_button) == 1
    assert any("ملف Excel تالف" in item.value for item in app.error)


def test_app_offers_whatsapp_paid_service_without_checkout():
    app = run_app()

    assert not app.exception
    assert len(app.link_button) == 1
    contact = app.link_button[0]
    assert contact.label == "تواصل عبر واتساب"
    assert contact.url.startswith("https://wa.me/966559665030?")
    assert any("50–150" in item.value for item in app.markdown)
    assert any("الدفع" in item.value and "يدوي" in item.value and "لا يوجد دفع" in item.value for item in app.caption)
