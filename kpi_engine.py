"""In-memory ingestion and KPI calculations for small e-commerce ad reports."""

from __future__ import annotations

import csv
from datetime import timedelta
from io import BytesIO, StringIO
import math
import re
import unicodedata
import zipfile
from collections.abc import Mapping
from typing import Any

from openpyxl import load_workbook
import pandas as pd


MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_ROWS = 250_000
MAX_COLUMNS = 100
MAX_XLSX_UNCOMPRESSED_BYTES = 200 * 1024 * 1024


class DataLoadError(ValueError):
    """Raised when an uploaded CSV/XLSX file is empty, unsafe, or unreadable."""


_ROLE_ALIASES: dict[str, set[str]] = {
    "spend": {
        "spend", "adspend", "advertisingspend", "amountspent", "cost", "adcost",
        "spendusd", "costusd", "gasto", "gastos", "gasto publicitario", "coste",
        "inversion", "inversionpublicitaria", "الانفاق", "الانفاقالاعلاني",
        "اجماليالانفاق", "مبلغالانفاق", "التكلفه", "التكاليف",
    },
    "revenue": {
        "revenue", "sales", "totalsales", "grosssales", "conversionvalue",
        "purchasevalue", "salesamount", "ventas", "ingresos", "facturacion",
        "المبيعات", "اجماليالمبيعات", "الايرادات", "قيمةالمبيعات", "قيمهالمبيعات",
        "قيمهالتحويلات",
    },
    "orders": {
        "orders", "order", "purchases", "purchase", "conversions", "conversion",
        "orderscount", "numberoforders", "pedidos", "compras", "الطلبات",
        "عددالطلبات", "المشتريات", "التحويلات", "عددالتحويلات",
    },
    "clicks": {"clicks", "linkclicks", "adclicks", "clics", "click", "النقرات", "عددالنقرات", "نقراتالرابط"},
    "impressions": {
        "impressions", "impression", "impressionscount", "imp", "views",
        "impresiones", "مراتالظهور", "عددمراتالظهور", "الظهور",
    },
    "date": {"date", "day", "datetime", "createdat", "datestart", "fecha", "التاريخ", "تاريخ", "اليوم"},
    "dimension": {
        "campaign", "campaignname", "campaignid", "adset", "adsetname", "adname",
        "channel", "platform", "source", "medium", "canal", "campaigns",
        "الحملة", "اسم الحملة", "القناة", "المنصة", "المصدر", "مصدر الزيارات",
    },
}


def _normalize_header(value: Any) -> str:
    text = str(value).strip().casefold()
    text = "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))
    text = text.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي"}))
    return re.sub(r"[^\w\u0600-\u06ff]+", "", text, flags=re.UNICODE)


def read_uploaded_data(
    filename: str,
    content: bytes,
    *,
    max_upload_bytes: int = MAX_UPLOAD_BYTES,
    max_rows: int = MAX_ROWS,
    max_columns: int = MAX_COLUMNS,
) -> pd.DataFrame:
    """Parse user-supplied CSV/XLSX bytes without writing them to disk."""
    if not isinstance(filename, str) or not filename.strip():
        raise DataLoadError("تعذر تحديد اسم الملف.")
    if not isinstance(content, (bytes, bytearray)):
        raise DataLoadError("تعذر قراءة محتوى الملف.")
    payload = bytes(content)
    if not payload.strip():
        raise DataLoadError("الملف فارغ أو لا يحتوي على بيانات.")
    if len(payload) > max_upload_bytes:
        raise DataLoadError(f"حجم الملف يتجاوز الحجم الأقصى المسموح ({max_upload_bytes // (1024 * 1024)} ميجابايت).")

    suffix = filename.rsplit(".", 1)[-1].casefold() if "." in filename else ""
    if suffix not in {"csv", "xlsx"}:
        raise DataLoadError("صيغة الملف غير مدعومة؛ استخدم CSV أو XLSX فقط.")

    try:
        if suffix == "csv":
            csv_text = payload.decode("utf-8-sig")
            header = next(csv.reader(StringIO(csv_text)), [])
            if len(header) > max_columns:
                raise DataLoadError(f"عدد الأعمدة يتجاوز الحد المسموح ({max_columns}).")
            frame = pd.read_csv(StringIO(csv_text), on_bad_lines="error", nrows=max_rows + 1)
        else:
            buffer = BytesIO(payload)
            if not zipfile.is_zipfile(buffer):
                raise DataLoadError("ملف Excel تالف أو ليس بصيغة XLSX صالحة.")
            buffer.seek(0)
            with zipfile.ZipFile(buffer) as archive:
                members = archive.infolist()
                expanded_size = sum(item.file_size for item in members)
                if len(members) > 5_000:
                    raise DataLoadError("ملف Excel يحتوي مكونات أكثر من المسموح؛ تم رفضه للحماية.")
                if expanded_size > MAX_XLSX_UNCOMPRESSED_BYTES:
                    raise DataLoadError("ملف Excel كبير جداً بعد فك الضغط؛ تم رفضه للحماية.")
            workbook = load_workbook(BytesIO(payload), read_only=True, data_only=True)
            try:
                worksheet = workbook.worksheets[0]
                if worksheet.max_column and worksheet.max_column > max_columns:
                    raise DataLoadError(f"عدد الأعمدة يتجاوز الحد المسموح ({max_columns}).")
                if worksheet.max_row and worksheet.max_row > max_rows + 1:
                    raise DataLoadError(f"عدد الصفوف يتجاوز الحد المسموح ({max_rows}).")
            finally:
                workbook.close()
            frame = pd.read_excel(BytesIO(payload), engine="openpyxl", nrows=max_rows + 1)
    except DataLoadError:
        raise
    except (UnicodeDecodeError, csv.Error, pd.errors.ParserError, pd.errors.EmptyDataError, ValueError, OSError, zipfile.BadZipFile) as exc:
        raise DataLoadError(f"تعذر قراءة الملف. تحقق من سلامة CSV/XLSX وترميز UTF-8: {exc}") from exc
    except Exception as exc:  # library-specific XLSX parsing failures
        raise DataLoadError(f"تعذر قراءة ملف Excel/CSV: {exc}") from exc

    if frame.empty:
        raise DataLoadError("الملف لا يحتوي على صفوف بيانات بعد العناوين.")
    if frame.shape[1] == 0:
        raise DataLoadError("الملف لا يحتوي على أعمدة قابلة للقراءة.")
    if frame.shape[1] > max_columns:
        raise DataLoadError(f"عدد الأعمدة يتجاوز الحد المسموح ({max_columns}).")
    if len(frame) > max_rows:
        raise DataLoadError(f"عدد الصفوف يتجاوز الحد المسموح ({max_rows}).")

    cleaned_columns: list[str] = []
    seen: dict[str, int] = {}
    for index, name in enumerate(frame.columns, start=1):
        base = str(name).strip() or f"عمود {index}"
        occurrence = seen.get(base, 0) + 1
        seen[base] = occurrence
        cleaned_columns.append(base if occurrence == 1 else f"{base} ({occurrence})")
    frame.columns = cleaned_columns
    return frame


def infer_column_map(frame: pd.DataFrame) -> dict[str, str | None]:
    """Suggest semantic columns using exact, accent-insensitive header aliases."""
    normalized_columns = {_normalize_header(column): str(column) for column in frame.columns}
    suggestions: dict[str, str | None] = {role: None for role in _ROLE_ALIASES}
    for role, aliases in _ROLE_ALIASES.items():
        normalized_aliases = {_normalize_header(alias) for alias in aliases}
        for normalized, original in normalized_columns.items():
            if normalized in normalized_aliases:
                suggestions[role] = original
                break
    return suggestions


def _parse_number(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else None

    text = str(value).strip().replace("\u00a0", "").replace("−", "-")
    if not text:
        return None
    negative_parentheses = text.startswith("(") and text.endswith(")")
    if negative_parentheses:
        text = text[1:-1]
    # Common currency symbols and ISO currency codes are formatting, not part of the value.
    text = re.sub(r"(?i)\b(?:SAR|USD|EUR|GBP|AED|CAD|AUD|JPY|CNY)\b", "", text)
    text = re.sub(r"[$€£¥₹₩₽₺₪₫₴₱₦฿]", "", text)
    text = re.sub(r"[\s'’]", "", text)
    if not text:
        return None

    if "," in text and "." in text:
        # The last separator is treated as the decimal marker (e.g. 1,234.50 or 1.234,50).
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        if text.count(",") == 1 and re.search(r",\d{1,2}$", text):
            text = text.replace(",", ".")
        else:
            text = text.replace(",", "")

    try:
        number = float(text)
    except ValueError:
        return None
    if not math.isfinite(number):
        return None
    return -number if negative_parentheses else number


def _numeric_column(frame: pd.DataFrame, column: str) -> tuple[pd.Series, int]:
    if column not in frame.columns:
        raise ValueError(f"العمود المحدد غير موجود: {column}")
    source = frame[column]
    parsed_values = [_parse_number(value) for value in source.tolist()]
    parsed = pd.Series(parsed_values, index=frame.index, dtype="float64")
    nonempty = source.map(lambda value: not (value is None or (isinstance(value, str) and not value.strip()) or pd.isna(value)))
    invalid_count = int((nonempty & parsed.isna()).sum())
    return parsed, invalid_count


def calculate_kpis(frame: pd.DataFrame, columns: Mapping[str, str | None]) -> dict[str, dict[str, float | int | None]]:
    """Return aggregate totals, standard ad KPIs, and counts of ignored bad cells."""
    roles = ("spend", "revenue", "orders", "clicks", "impressions")
    totals: dict[str, float | None] = {}
    invalid_values: dict[str, int] = {}
    for role in roles:
        column = columns.get(role)
        if not column:
            totals[role] = None
            invalid_values[role] = 0
            continue
        parsed, invalid = _numeric_column(frame, column)
        total = parsed.sum(min_count=1)
        totals[role] = float(total) if pd.notna(total) else None
        invalid_values[role] = invalid

    spend, revenue = totals["spend"], totals["revenue"]
    orders, clicks, impressions = totals["orders"], totals["clicks"], totals["impressions"]
    kpis: dict[str, float | None] = {
        "roas": revenue / spend if revenue is not None and spend is not None and spend > 0 else None,
        "cpa": spend / orders if spend is not None and orders is not None and orders > 0 else None,
        "cpc": spend / clicks if spend is not None and clicks is not None and clicks > 0 else None,
        "ctr_pct": clicks / impressions * 100 if clicks is not None and impressions is not None and impressions > 0 else None,
        "conversion_rate_pct": orders / clicks * 100 if orders is not None and clicks is not None and clicks > 0 else None,
        "aov": revenue / orders if revenue is not None and orders is not None and orders > 0 else None,
    }
    return {"totals": totals, "kpis": kpis, "invalid_values": invalid_values}


def group_metric(frame: pd.DataFrame, dimension: str, measure: str) -> pd.DataFrame:
    """Sum a numeric measure by a categorical column; return the largest groups first."""
    if dimension not in frame.columns or measure not in frame.columns:
        raise ValueError("اختر عموداً موجوداً للتقسيم وعموداً موجوداً للمقياس.")
    if dimension == measure:
        raise ValueError("يجب أن يكون عمود التقسيم وعمود المقياس مختلفين.")
    values, _ = _numeric_column(frame, measure)
    work = pd.DataFrame({dimension: frame[dimension].fillna("غير محدد").astype(str), measure: values}, index=frame.index)
    grouped = work.groupby(dimension, dropna=False, sort=False)[measure].sum(min_count=1).reset_index()
    return grouped.sort_values(measure, ascending=False, na_position="last", kind="stable").reset_index(drop=True)


def filter_by_date_range(frame: pd.DataFrame, date_column: str, start: Any, end: Any) -> pd.DataFrame:
    """Filter rows inclusively by calendar date; rows with invalid dates are excluded."""
    if date_column not in frame.columns:
        raise ValueError(f"عمود التاريخ غير موجود: {date_column}")
    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    if start_ts > end_ts:
        raise ValueError("يجب أن يكون تاريخ البدء قبل تاريخ النهاية أو مساوياً له.")
    parsed = pd.to_datetime(frame[date_column], errors="coerce", utc=True).dt.normalize()
    start_ts = start_ts.tz_localize("UTC") if start_ts.tzinfo is None else start_ts.tz_convert("UTC")
    end_ts = end_ts.tz_localize("UTC") if end_ts.tzinfo is None else end_ts.tz_convert("UTC")
    end_exclusive = end_ts.normalize() + timedelta(days=1)
    mask = parsed.notna() & (parsed >= start_ts.normalize()) & (parsed < end_exclusive)
    return frame.loc[mask].copy()
