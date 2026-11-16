from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from kpi_engine import (
    MAX_UPLOAD_BYTES,
    DataLoadError,
    calculate_kpis,
    filter_by_date_range,
    group_metric,
    infer_column_map,
    read_uploaded_data,
)


st.set_page_config(
    page_title="لوحة مؤشرات المتجر",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      html, body, [class*="css"] { direction: rtl; text-align: right; }
      [data-testid="stAppViewContainer"] { background: #f6f8fb; }
      [data-testid="stHeader"] { background: rgba(246,248,251,0.9); }
      .hero { padding: 1.35rem 1.6rem; border-radius: 18px; color: #fff;
              background: linear-gradient(115deg,#11233f 0%,#176b87 100%); margin-bottom: 1rem; }
      .hero h1 { color: #fff; margin: 0 0 .35rem 0; font-size: 2rem; }
      .hero p { color: #e3f4f7; margin: 0; font-size: 1rem; }
      .privacy-note { border-right: 4px solid #0d9488; background: #eaf8f5;
                      border-radius: 8px; padding: .8rem 1rem; color: #164e4a; }
      div[data-testid="stMetric"] { background:#fff; border:1px solid #e2e8f0;
        padding:.85rem 1rem; border-radius:14px; box-shadow:0 2px 8px rgba(15,23,42,.04); }
      @media (max-width: 700px) {
        .hero { padding: 1rem; }
        .hero h1 { font-size: 1.45rem; }
      }
    </style>
    <div class="hero">
      <h1>لوحة أداء المتجر والإعلانات</h1>
      <p>ارفع تقرير CSV أو Excel، وطابق الأعمدة، وشاهد مؤشرات الأداء والاتجاهات فوراً.</p>
    </div>
    <div class="privacy-note"><b>الخصوصية:</b> تتم قراءة الملف وتحليله في ذاكرة جلسة التطبيق فقط؛ لا ينشئ هذا التطبيق ملفاً محلياً ولا يرسل البيانات إلى خدمة تحليل خارجية. عند استضافته سحابياً، تصل بيانات الرفع إلى خادم التطبيق أثناء المعالجة، لذا لا ترفع بيانات حساسة قبل مراجعة سياسة الاستضافة.</div>
    """,
    unsafe_allow_html=True,
)

st.write("")
upload_controls = st.columns([2, 1])
with upload_controls[0]:
    uploaded_file = st.file_uploader(
        "ارفع ملف البيانات",
        type=["csv", "xlsx"],
        help="CSV بترميز UTF-8 أو أول ورقة في ملف Excel بصيغة XLSX؛ الحد الأقصى 20 ميجابايت.",
    )
with upload_controls[1]:
    currency_label = st.selectbox("عملة عرض المبالغ", ["ر.س (SAR)", "دولار (USD)", "يورو (EUR)", "درهم (AED)", "بدون رمز"], index=0)
currency_symbol = {"ر.س (SAR)": "ر.س", "دولار (USD)": "$", "يورو (EUR)": "€", "درهم (AED)": "د.إ", "بدون رمز": ""}[currency_label]
st.caption("رمز العملة يغيّر العرض فقط ولا يحوّل المبالغ. حدود الحماية: 20MB، و250 ألف صف، و100 عمود؛ CSV بترميز UTF-8 أو ورقة Excel الأولى بصيغة XLSX.")

if uploaded_file is None:
    st.info("ارفع ملفاً للبدء. يمكنك تجربة الملف الاصطناعي `examples/demo_ads.csv` الموجود مع المشروع.")
    st.markdown("### المؤشرات التي يحسبها التطبيق")
    st.write("ROAS، تكلفة اكتساب العميل (CPA)، تكلفة النقرة (CPC)، معدل النقر (CTR)، معدل التحويل، ومتوسط قيمة الطلب (AOV)، إضافةً إلى إجمالي الإنفاق والإيراد والطلبات.")
    st.caption("يعرض التطبيق المؤشر فقط عندما تتوفر أعمدته ومقام صالح للحساب؛ لا يستنتج هامش الربح ولا صافي ROI.")
    st.stop()

if uploaded_file.size > MAX_UPLOAD_BYTES:
    st.error("حجم الملف يتجاوز الحد الأقصى البالغ 20 ميجابايت.")
    st.stop()

try:
    raw_bytes = uploaded_file.getvalue()
    data = read_uploaded_data(uploaded_file.name, raw_bytes)
except DataLoadError as exc:
    st.error(str(exc))
    st.stop()

st.success(f"تمت قراءة الملف: {len(data):,} صفاً و{len(data.columns):,} عموداً.")
with st.expander("معاينة البيانات", expanded=False):
    st.dataframe(data.head(20), width="stretch", hide_index=True)

st.subheader("1. طابق أعمدة ملفك")
st.caption("يكتشف التطبيق أسماء شائعة تلقائياً، ويمكنك تغيير الاختيارات. أدخل أعمدة رقمية تمثل إجماليات قابلة للجمع.")
inferred = infer_column_map(data)
roles = [
    ("spend", "الإنفاق الإعلاني (مطلوب لحساب ROAS/CPA)"),
    ("revenue", "الإيراد أو المبيعات (مطلوب لحساب ROAS/AOV)"),
    ("orders", "الطلبات أو التحويلات"),
    ("clicks", "النقرات"),
    ("impressions", "مرات الظهور"),
    ("date", "التاريخ (اختياري للترشيح والاتجاه)"),
    ("dimension", "الحملة أو القناة (اختياري للتقسيم)"),
]
options = ["— غير محدد —", *[str(column) for column in data.columns]]
column_map: dict[str, str | None] = {}
cols = st.columns(2)
for index, (role, label) in enumerate(roles):
    suggestion = inferred.get(role)
    default_index = options.index(suggestion) if suggestion in options else 0
    with cols[index % 2]:
        selected = st.selectbox(label, options, index=default_index, key=f"mapping_{role}")
    column_map[role] = None if selected == options[0] else selected

metric_roles = ("spend", "revenue", "orders", "clicks", "impressions")
selected_metric_columns = [column_map[key] for key in metric_roles if column_map.get(key)]
duplicate_metric_columns = {column for column in selected_metric_columns if selected_metric_columns.count(column) > 1}
if duplicate_metric_columns:
    st.warning("تم تعيين العمود نفسه لأكثر من مقياس؛ ستظهر المقاييس المتأثرة كغير متاحة حتى تصحح المطابقة.")
calculation_columns = column_map.copy()
for role in metric_roles:
    if calculation_columns.get(role) in duplicate_metric_columns:
        calculation_columns[role] = None

analysis_data = data
if column_map.get("date"):
    parsed_dates = pd.to_datetime(data[column_map["date"]], errors="coerce", utc=True)
    valid_dates = parsed_dates.dropna()
    if not valid_dates.empty:
        min_date = valid_dates.min().date()
        max_date = valid_dates.max().date()
        st.subheader("2. نطاق التاريخ")
        selected_dates = st.date_input(
            "اختر فترة التحليل (شاملة للطرفين)",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key="analysis_date_range",
        )
        if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
            try:
                analysis_data = filter_by_date_range(data, column_map["date"], selected_dates[0], selected_dates[1])
            except ValueError as exc:
                st.warning(str(exc))
        else:
            st.caption("اختر تاريخ البداية والنهاية لتطبيق المرشح.")
    else:
        st.warning("لم تُقرأ قيم صالحة من عمود التاريخ؛ سيُعرض الملف كاملاً.")

if analysis_data.empty:
    st.warning("لا توجد صفوف ضمن النطاق المحدد.")
    st.stop()

result = calculate_kpis(analysis_data, calculation_columns)
invalid_total = sum(result["invalid_values"].values())
if invalid_total:
    st.warning(f"تجاهل التحليل {invalid_total:,} قيمة غير رقمية في أعمدة المقاييس؛ راجع البيانات أو الأعمدة المطابقة.")


def amount(value: float | None) -> str:
    if value is None or not pd.notna(value):
        return "غير متاح"
    return f"{value:,.2f} {currency_symbol}".strip()


def ratio(value: float | None, suffix: str = "") -> str:
    if value is None or not pd.notna(value):
        return "غير متاح"
    return f"{value:,.2f}{suffix}"


def count(value: float | None) -> str:
    if value is None or not pd.notna(value):
        return "غير متاح"
    return f"{value:,.0f}" if float(value).is_integer() else f"{value:,.2f}"


st.subheader("3. مؤشرات الأداء")
metrics = [
    ("ROAS", ratio(result["kpis"]["roas"], "×"), "الإيراد ÷ الإنفاق الإعلاني؛ ليس صافي ربح"),
    ("CPA", amount(result["kpis"]["cpa"]), "الإنفاق ÷ الطلبات"),
    ("AOV", amount(result["kpis"]["aov"]), "الإيراد ÷ الطلبات"),
    ("CTR", ratio(result["kpis"]["ctr_pct"], "%"), "النقرات ÷ مرات الظهور"),
    ("معدل التحويل", ratio(result["kpis"]["conversion_rate_pct"], "%"), "الطلبات ÷ النقرات"),
    ("CPC", amount(result["kpis"]["cpc"]), "الإنفاق ÷ النقرات"),
]
for start in (0, 3):
    metric_cols = st.columns(3)
    for col, item in zip(metric_cols, metrics[start : start + 3]):
        label, value, help_text = item
        col.metric(label, value, help=help_text)

st.subheader("الإجماليات ضمن الفترة المختارة")
summary_cols = st.columns(4)
summary_cols[0].metric("الإنفاق", amount(result["totals"]["spend"]))
summary_cols[1].metric("الإيراد", amount(result["totals"]["revenue"]))
summary_cols[2].metric("الطلبات", count(result["totals"]["orders"]))
summary_cols[3].metric("الصفوف المحللة", f"{len(analysis_data):,}")

st.subheader("4. مقارنة الحملات أو الأعمدة")
numeric_columns = [
    str(column)
    for column in analysis_data.columns
    if pd.api.types.is_numeric_dtype(analysis_data[column]) or column in selected_metric_columns
]
dimension_columns = [str(column) for column in analysis_data.columns]
if numeric_columns and len(dimension_columns) > 1:
    chart_controls = st.columns(2)
    with chart_controls[0]:
        default_dimension = column_map.get("dimension")
        dimension_index = dimension_columns.index(default_dimension) if default_dimension in dimension_columns else 0
        chosen_dimension = st.selectbox("قسّم حسب", dimension_columns, index=dimension_index, key="chart_dimension")
    with chart_controls[1]:
        suggested_measure = column_map.get("revenue") if column_map.get("revenue") in numeric_columns else numeric_columns[0]
        measure_index = numeric_columns.index(suggested_measure)
        chosen_measure = st.selectbox("المقياس المراد جمعه", numeric_columns, index=measure_index, key="chart_measure")
    if chosen_dimension == chosen_measure:
        st.info("اختر عمود تقسيم مختلفاً عن المقياس.")
    else:
        grouped = group_metric(analysis_data, chosen_dimension, chosen_measure).head(20)
        fig = px.bar(
            grouped,
            x=chosen_dimension,
            y=chosen_measure,
            title=f"{chosen_measure} حسب {chosen_dimension} — أعلى 20 فئة",
            text_auto=".2s",
            color_discrete_sequence=["#0f766e"],
        )
        fig.update_layout(template="plotly_white", xaxis_title=chosen_dimension, yaxis_title=chosen_measure, margin=dict(l=20, r=20, t=60, b=20))
        st.plotly_chart(fig, width="stretch")
        st.dataframe(grouped, width="stretch", hide_index=True)
else:
    st.info("أضف عموداً رقمياً وعمود تقسيم مختلفاً لإنشاء مقارنة مرئية.")

if column_map.get("date") and column_map.get("revenue"):
    trend_frame = pd.DataFrame(
        {
            "_analysis_date": pd.to_datetime(analysis_data[column_map["date"]], errors="coerce", utc=True).dt.date,
            "_analysis_revenue": analysis_data[column_map["revenue"]],
        },
        index=analysis_data.index,
    ).dropna(subset=["_analysis_date"])
    trend_frame = group_metric(trend_frame, "_analysis_date", "_analysis_revenue").sort_values("_analysis_date")
    if not trend_frame.empty:
        with st.expander("اتجاه الإيراد اليومي", expanded=False):
            trend = px.line(trend_frame, x="_analysis_date", y="_analysis_revenue", markers=True, title="الإيراد حسب اليوم", color_discrete_sequence=["#176b87"])
            trend.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=60, b=20))
        st.plotly_chart(trend, width="stretch")

report_rows = [
    ("إجمالي الإنفاق", result["totals"]["spend"]),
    ("إجمالي الإيراد", result["totals"]["revenue"]),
    ("إجمالي الطلبات", result["totals"]["orders"]),
    ("ROAS", result["kpis"]["roas"]),
    ("CPA", result["kpis"]["cpa"]),
    ("CPC", result["kpis"]["cpc"]),
    ("CTR (%)", result["kpis"]["ctr_pct"]),
    ("معدل التحويل (%)", result["kpis"]["conversion_rate_pct"]),
    ("متوسط قيمة الطلب", result["kpis"]["aov"]),
]
report_csv = pd.DataFrame(report_rows, columns=["المؤشر", "القيمة"]).to_csv(index=False).encode("utf-8-sig")
st.download_button("تنزيل ملخص المؤشرات CSV", data=report_csv, file_name="kpi_summary.csv", mime="text/csv")
st.caption("طريقة الحساب: تُجمع القيم في الأعمدة المختارة ثم تُحسب النسب من الإجماليات. القيم غير الرقمية تُتجاهل مع تنبيه. لا يحسب التطبيق الربح أو ROI لعدم توفر تكلفة البضاعة والمرتجعات والرسوم.")
