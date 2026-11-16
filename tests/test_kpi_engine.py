from __future__ import annotations

import builtins
from io import BytesIO

import pandas as pd
import pytest

from kpi_engine import (
    DataLoadError,
    calculate_kpis,
    filter_by_date_range,
    group_metric,
    infer_column_map,
    read_uploaded_data,
)


def test_reads_csv_from_memory_and_normalizes_headers():
    frame = read_uploaded_data(
        "ads.csv",
        b"Campaign,Spend,Revenue,Orders\nA,10,50,2\nB,20,80,4\n",
    )
    assert list(frame.columns) == ["Campaign", "Spend", "Revenue", "Orders"]
    assert len(frame) == 2
    assert frame.loc[0, "Spend"] == 10


def test_reads_xlsx_from_memory():
    source = BytesIO()
    pd.DataFrame({"Ad Spend": [15.5], "Sales": [60]}).to_excel(source, index=False)
    frame = read_uploaded_data("report.xlsx", source.getvalue())
    assert frame.to_dict(orient="records") == [{"Ad Spend": 15.5, "Sales": 60}]


def test_reader_never_needs_a_filesystem_path(monkeypatch):
    def forbidden_open(*_args, **_kwargs):
        raise AssertionError("uploaded content must be processed from memory")

    monkeypatch.setattr(builtins, "open", forbidden_open)
    frame = read_uploaded_data("in-memory.csv", b"spend,revenue\n4,9\n")
    assert frame.loc[0, "revenue"] == 9


@pytest.mark.parametrize(
    ("filename", "content", "message"),
    [
        ("report.txt", b"a,b\n1,2\n", "صيغة الملف"),
        ("empty.csv", b"", "فارغ"),
        ("blank.csv", b"   \n", "فارغ"),
        ("header-only.csv", b"spend,revenue\n", "صفوف بيانات"),
        ("broken.xlsx", b"not an excel file", "Excel"),
    ],
)
def test_rejects_unsupported_or_unreadable_files(filename, content, message):
    with pytest.raises(DataLoadError, match=message):
        read_uploaded_data(filename, content)


def test_rejects_upload_over_size_limit():
    with pytest.raises(DataLoadError, match="الحجم الأقصى"):
        read_uploaded_data("large.csv", b"x" * 11, max_upload_bytes=10)


def test_rejects_row_and_column_limits():
    csv = b"a,b\n1,2\n3,4\n"
    with pytest.raises(DataLoadError, match="عدد الصفوف"):
        read_uploaded_data("rows.csv", csv, max_rows=1)
    with pytest.raises(DataLoadError, match="عدد الأعمدة"):
        read_uploaded_data("columns.csv", csv, max_columns=1)


def test_rejects_xlsx_row_and_column_limits_before_dataframe_load(monkeypatch):
    source = BytesIO()
    pd.DataFrame({"a": [1, 2], "b": [3, 4]}).to_excel(source, index=False)

    def should_not_read_full_workbook(*_args, **_kwargs):
        raise AssertionError("out-of-limit XLSX should be rejected before pandas loads it")

    monkeypatch.setattr(pd, "read_excel", should_not_read_full_workbook)
    with pytest.raises(DataLoadError, match="عدد الصفوف"):
        read_uploaded_data("rows.xlsx", source.getvalue(), max_rows=1)
    with pytest.raises(DataLoadError, match="عدد الأعمدة"):
        read_uploaded_data("columns.xlsx", source.getvalue(), max_columns=1)


def test_xlsx_reads_first_sheet_even_when_another_sheet_is_active():
    source = BytesIO()
    with pd.ExcelWriter(source, engine="openpyxl") as writer:
        pd.DataFrame({"spend": [10], "revenue": [20]}).to_excel(writer, sheet_name="Data", index=False)
        pd.DataFrame({"extra": [1, 2, 3]}).to_excel(writer, sheet_name="Other", index=False)
        writer.book.active = 1

    frame = read_uploaded_data("multi-sheet.xlsx", source.getvalue(), max_rows=1)
    assert frame.to_dict(orient="records") == [{"spend": 10, "revenue": 20}]


def test_reads_xlsx_without_opening_a_filesystem_path(monkeypatch):
    source = BytesIO()
    pd.DataFrame({"spend": [4], "revenue": [9]}).to_excel(source, index=False)

    def forbidden_open(*_args, **_kwargs):
        raise AssertionError("uploaded workbook must be processed from memory")

    monkeypatch.setattr(builtins, "open", forbidden_open)
    frame = read_uploaded_data("in-memory.xlsx", source.getvalue())
    assert frame.loc[0, "revenue"] == 9


def test_infers_common_arabic_and_english_column_names():
    frame = pd.DataFrame(
        columns=["تاريخ", "الحملة", "الإنفاق الإعلاني", "المبيعات", "الطلبات", "النقرات", "مرات الظهور"]
    )
    inferred = infer_column_map(frame)
    assert inferred["date"] == "تاريخ"
    assert inferred["dimension"] == "الحملة"
    assert inferred["spend"] == "الإنفاق الإعلاني"
    assert inferred["revenue"] == "المبيعات"
    assert inferred["orders"] == "الطلبات"
    assert inferred["clicks"] == "النقرات"
    assert inferred["impressions"] == "مرات الظهور"


def test_calculates_aggregate_commerce_kpis_and_ignores_invalid_cells():
    frame = pd.DataFrame(
        {
            "Cost": [100, "50.00", "bad"],
            "Sales": [400, 200, 50],
            "Purchases": [10, 5, 1],
            "Clicks": [500, 250, 50],
            "Impressions": [10000, 5000, 1000],
        }
    )
    result = calculate_kpis(
        frame,
        {"spend": "Cost", "revenue": "Sales", "orders": "Purchases", "clicks": "Clicks", "impressions": "Impressions"},
    )
    assert result["totals"]["spend"] == 150
    assert result["totals"]["revenue"] == 650
    assert result["totals"]["orders"] == 16
    assert result["kpis"]["roas"] == pytest.approx(650 / 150)
    assert result["kpis"]["cpa"] == pytest.approx(150 / 16)
    assert result["kpis"]["cpc"] == pytest.approx(150 / 800)
    assert result["kpis"]["ctr_pct"] == pytest.approx(800 / 16000 * 100)
    assert result["kpis"]["conversion_rate_pct"] == pytest.approx(16 / 800 * 100)
    assert result["kpis"]["aov"] == pytest.approx(650 / 16)
    assert result["invalid_values"]["spend"] == 1


def test_parses_currency_and_european_decimal_strings():
    frame = pd.DataFrame({"cost": ["€1.234,50", "$20.25"], "sales": ["2.000,00", "100.00"]})
    result = calculate_kpis(frame, {"spend": "cost", "revenue": "sales"})
    assert result["totals"]["spend"] == pytest.approx(1254.75)
    assert result["totals"]["revenue"] == pytest.approx(2100.0)
    assert result["kpis"]["roas"] == pytest.approx(2100 / 1254.75)


def test_zero_or_missing_denominators_return_unavailable_not_infinity():
    frame = pd.DataFrame({"Cost": [0, 0], "Sales": [10, 20], "Orders": [0, 0], "Clicks": [0, 0], "Impressions": [0, 0]})
    result = calculate_kpis(
        frame,
        {"spend": "Cost", "revenue": "Sales", "orders": "Orders", "clicks": "Clicks", "impressions": "Impressions"},
    )
    assert result["kpis"]["roas"] is None
    assert result["kpis"]["cpa"] is None
    assert result["kpis"]["cpc"] is None
    assert result["kpis"]["ctr_pct"] is None
    assert result["kpis"]["conversion_rate_pct"] is None
    assert result["kpis"]["aov"] is None


def test_missing_optional_columns_do_not_break_required_kpis():
    frame = pd.DataFrame({"Spend": [40], "Revenue": [100]})
    result = calculate_kpis(frame, {"spend": "Spend", "revenue": "Revenue"})
    assert result["kpis"]["roas"] == pytest.approx(2.5)
    assert result["totals"]["orders"] is None
    assert result["kpis"]["cpa"] is None


def test_group_metric_sums_values_and_handles_missing_dimension_labels():
    frame = pd.DataFrame({"Channel": ["Search", "Search", None, "Social"], "Revenue": [20, 30, 5, 10]})
    grouped = group_metric(frame, "Channel", "Revenue")
    assert grouped.to_dict(orient="records") == [
        {"Channel": "Search", "Revenue": 50.0},
        {"Channel": "Social", "Revenue": 10.0},
        {"Channel": "غير محدد", "Revenue": 5.0},
    ]


def test_group_metric_rejects_same_dimension_and_measure():
    frame = pd.DataFrame({"Cost": [10]})
    with pytest.raises(ValueError, match="مختلفين"):
        group_metric(frame, "Cost", "Cost")


def test_date_filter_is_inclusive_and_ignores_invalid_dates():
    frame = pd.DataFrame({"date": ["2025-01-01", "2025-01-02", "invalid", "2025-01-03"], "value": [1, 2, 3, 4]})
    filtered = filter_by_date_range(frame, "date", "2025-01-02", "2025-01-03")
    assert filtered["value"].tolist() == [2, 4]


def test_date_filter_rejects_reversed_range():
    frame = pd.DataFrame({"date": ["2025-01-01"], "value": [1]})
    with pytest.raises(ValueError, match="البدء"):
        filter_by_date_range(frame, "date", "2025-01-02", "2025-01-01")
