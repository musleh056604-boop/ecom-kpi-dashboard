from __future__ import annotations

from urllib.parse import quote

import streamlit as st


WHATSAPP_NUMBER = "+966559665030"
WHATSAPP_MESSAGE = "السلام عليكم، أرغب في الاستفسار عن خدمة تقرير أداء متجري."
WHATSAPP_URL = f"https://wa.me/966559665030?text={quote(WHATSAPP_MESSAGE, safe='')}"

st.set_page_config(
    page_title="تقارير أداء المتاجر",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      html, body, [class*="css"] { direction: rtl; text-align: right; }
      [data-testid="stAppViewContainer"] {
        background: linear-gradient(145deg, #f3f7fa 0%, #edf5f6 100%);
      }
      [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDeployButton"] {
        display: none !important;
        height: 0;
      }
      #MainMenu, footer { visibility: hidden; }
      [data-testid="stMainBlockContainer"] {
        max-width: 760px;
        padding-top: 1.4rem;
        padding-bottom: 1.25rem;
      }
      [data-testid="stVerticalBlockBorderWrapper"] {
        background: #fff;
        border: 1px solid #d9e4ec;
        border-radius: 22px;
        box-shadow: 0 14px 38px rgba(17, 35, 63, .09);
        padding: .55rem;
      }
      .service-eyebrow {
        display: inline-block;
        color: #176b87;
        background: #e8f5f7;
        border-radius: 999px;
        padding: .35rem .8rem;
        font-size: .92rem;
        font-weight: 700;
        margin-bottom: .45rem;
      }
      .service-title {
        color: #11233f;
        font-size: 2rem;
        line-height: 1.45;
        margin: .2rem 0 .55rem;
        font-weight: 800;
      }
      .service-description {
        color: #475569;
        font-size: 1.05rem;
        line-height: 1.8;
        margin: 0 0 1rem;
      }
      .price-box {
        background: #f1f8f8;
        border: 1px solid #d4e9e8;
        border-radius: 16px;
        padding: .9rem 1rem;
        margin: .55rem 0 .75rem;
      }
      .price-label { color: #475569; font-size: .95rem; }
      .price-amount {
        color: #0f766e;
        display: block;
        font-size: 2.45rem;
        line-height: 1.3;
        font-weight: 800;
        direction: ltr;
        text-align: right;
        margin: .12rem 0;
      }
      .price-detail { color: #334155; font-size: .98rem; }
      [data-testid="stLinkButton"] a {
        background: #0f766e !important;
        border-color: #0f766e !important;
        border-radius: 12px !important;
        color: #fff !important;
        box-shadow: none !important;
      }
      [data-testid="stLinkButton"] a:hover { background: #115e59 !important; }
      .whatsapp-contact { color: #475569; font-size: .9rem; margin: .1rem 0 .65rem; }
      .whatsapp-contact bdi { direction: ltr; unicode-bidi: isolate; display: inline-block; font-weight: 600; }
      .service-note {
        color: #334155;
        background: #f8fafc;
        border-right: 4px solid #0d9488;
        border-radius: 9px;
        padding: .75rem .9rem;
        line-height: 1.75;
        margin-top: .5rem;
      }
      @media (max-width: 600px) {
        [data-testid="stMainBlockContainer"] {
          padding: .7rem .8rem 1rem;
        }
        [data-testid="stVerticalBlockBorderWrapper"] {
          border-radius: 18px;
          padding: .25rem;
        }
        .service-title { font-size: 1.65rem; }
        .service-description { font-size: 1rem; }
        .price-amount { font-size: 2.25rem; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.container(border=True):
    st.markdown(
        """
        <div class="service-eyebrow">خدمة مخصصة لأصحاب المتاجر الإلكترونية</div>
        <h1 class="service-title">تقرير أداء يساعدك على اتخاذ الخطوة التالية</h1>
        <p class="service-description">نراجع بيانات متجرك ونعدّ لك تقرير أداء مخصصًا؛ تواصل معنا لمعرفة ما يناسب احتياجك.</p>
        <div class="price-box">
          <span class="price-label">النطاق السعري</span>
          <strong class="price-amount">$50–$150</strong>
          <span class="price-detail">للتقرير أو الاشتراك، بحسب نطاق العمل</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("يُتفق معك على نطاق العمل والسعر النهائي قبل البدء.")
    st.link_button("تواصل عبر واتساب", WHATSAPP_URL, type="primary", use_container_width=True)
    st.markdown(
        f'<div class="whatsapp-contact">واتساب: <bdi dir="ltr">{WHATSAPP_NUMBER}</bdi></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="service-note"><b>آلية الخدمة:</b> يتم التواصل والاتفاق والدفع وإعداد التقرير وتسليم التقرير يدويًا. لا يوجد دفع أو تسليم آلي داخل هذه الصفحة.</div>',
        unsafe_allow_html=True,
    )
