from __future__ import annotations

from time import perf_counter

from kpi_engine import calculate_kpis, read_uploaded_data


def test_processes_100k_csv_rows_within_upload_limits():
    row_count = 100_000
    header = b"Campaign,Spend,Revenue,Orders,Clicks,Impressions\n"
    row = b"Campaign A,1.25,3.75,1,10,100\n"
    payload = header + row * row_count
    started = perf_counter()

    frame = read_uploaded_data("load-test.csv", payload)
    result = calculate_kpis(
        frame,
        {"spend": "Spend", "revenue": "Revenue", "orders": "Orders", "clicks": "Clicks", "impressions": "Impressions"},
    )
    elapsed = perf_counter() - started

    assert len(frame) == row_count
    assert result["totals"]["spend"] == 125_000
    assert result["totals"]["revenue"] == 375_000
    assert result["totals"]["orders"] == row_count
    assert result["kpis"]["roas"] == 3
    assert len(payload) < 20 * 1024 * 1024
    assert elapsed < 15
