"""
Dana Point PULSE — Weekly Report Viewer
-----------------------------------------
Minimal app. Its only job: generate the weekly report PDF from live STR /
CoStar / Datafy data and display it in full.
"""

import base64
import os
import sys
from datetime import datetime

import streamlit as st

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts"))

LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
PDF_PATH = os.path.join(LOGS_DIR, "weekly_report_latest.pdf")
LOGO_PATH = os.path.join(BASE_DIR, "assets", "vdp_logo.svg")

st.set_page_config(
    page_title="Dana Point PULSE — Weekly Report",
    page_icon="📄",
    layout="wide",
)


def _logo_data_uri() -> str:
    try:
        with open(LOGO_PATH, "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode("ascii")
        return f"data:image/svg+xml;base64,{b64}"
    except FileNotFoundError:
        return ""

st.markdown(
    """
    <style>
      #MainMenu {visibility: hidden;}
      footer {visibility: hidden;}
      .block-container { padding-top: 1.5rem; max-width: 1400px; }
      .pulse-header { display:flex; align-items:center; justify-content:space-between;
                      padding-bottom: 12px; border-bottom: 1px solid #E2E8F0; margin-bottom: 18px; }
      .pulse-header-left { display:flex; align-items:center; gap:14px; }
      .pulse-logo-badge { background:#0E7490; border-radius:10px; width:52px; height:44px;
                           display:flex; align-items:center; justify-content:center; flex-shrink:0; }
      .pulse-logo-badge img { width:36px; height:auto; }
      .pulse-title { font-size: 22px; font-weight: 800; color: #0F172A; }
      .pulse-sub { font-size: 13px; color: #64748B; margin-top:2px; }

      /* Whale-watching loading splash */
      .whale-splash {
        position:relative; height:340px; border-radius:14px; overflow:hidden;
        background: linear-gradient(180deg, #BEE3F0 0%, #7FC4D9 35%, #1B6E8C 70%, #0E4A5F 100%);
        display:flex; align-items:center; justify-content:center; flex-direction:column;
        margin: 10px 0 24px 0;
      }
      .whale-splash .sun { position:absolute; top:26px; right:60px; width:46px; height:46px;
        border-radius:50%; background:#FFE9A8; box-shadow:0 0 40px 10px rgba(255,233,168,0.5); }
      .whale-splash .wave-row { position:absolute; left:0; right:0; height:26px; opacity:.55; }
      .whale-splash .wave-row svg { width:200%; height:100%; animation: wave-drift 9s linear infinite; }
      .whale-splash .wave1 { bottom:64px; }
      .whale-splash .wave2 { bottom:34px; opacity:.4; }
      .whale-splash .wave2 svg { animation-duration: 13s; animation-direction: reverse; }
      @keyframes wave-drift { from { transform: translateX(0); } to { transform: translateX(-50%); } }

      .whale-splash .scene { position:relative; width:220px; height:170px; }
      .whale-splash .tail {
        position:absolute; bottom:18px; left:50%; width:150px; height:150px;
        transform-origin: bottom center; transform: translateX(-50%) rotate(0deg);
        animation: whale-dive 4.5s ease-in-out infinite;
      }
      @keyframes whale-dive {
        0%   { transform: translateX(-50%) translateY(20px) rotate(0deg); opacity:0; }
        12%  { opacity:1; }
        30%  { transform: translateX(-50%) translateY(-58px) rotate(-6deg); opacity:1; }
        45%  { transform: translateX(-50%) translateY(-64px) rotate(4deg); opacity:1; }
        60%  { transform: translateX(-50%) translateY(-40px) rotate(-2deg); opacity:1; }
        78%  { transform: translateX(-50%) translateY(30px) rotate(0deg); opacity:0.4; }
        100% { transform: translateX(-50%) translateY(30px) rotate(0deg); opacity:0; }
      }
      .whale-splash .splash-ring {
        position:absolute; bottom:18px; left:50%; width:120px; height:18px; margin-left:-60px;
        border-radius:50%; background:radial-gradient(ellipse at center, rgba(255,255,255,0.75) 0%, rgba(255,255,255,0) 72%);
        animation: splash-pulse 4.5s ease-in-out infinite;
      }
      @keyframes splash-pulse {
        0%, 68% { opacity:0; transform: translateX(-50%) scale(0.6); }
        74% { opacity:1; transform: translateX(-50%) scale(1); }
        90% { opacity:0; transform: translateX(-50%) scale(1.5); }
        100% { opacity:0; }
      }
      .whale-splash .boat { position:absolute; bottom:78px; left:26px; width:54px;
        animation: boat-bob 3.2s ease-in-out infinite; }
      @keyframes boat-bob { 0%,100% { transform: translateY(0px) rotate(-2deg); } 50% { transform: translateY(-6px) rotate(2deg); } }
      .whale-splash .caption { color:#F0FAFF; font-size:13px; font-weight:600; letter-spacing:.02em;
        margin-top:14px; text-shadow:0 1px 4px rgba(0,0,0,0.25); }
      .whale-splash .caption-sub { color:#CFEFF9; font-size:11px; margin-top:2px; }
    </style>
    """,
    unsafe_allow_html=True,
)

_WAVE_SVG = (
    '<svg viewBox="0 0 200 20" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">'
    '<path d="M0 10 Q 12.5 0, 25 10 T 50 10 T 75 10 T 100 10 T 125 10 T 150 10 T 175 10 T 200 10 V20 H0 Z" fill="#F0FAFF"/>'
    '</svg>'
)

WHALE_SPLASH_HTML = f"""
<div class="whale-splash">
  <div class="sun"></div>
  <div class="wave-row wave1">{_WAVE_SVG}{_WAVE_SVG}</div>
  <div class="wave-row wave2">{_WAVE_SVG}{_WAVE_SVG}</div>
  <div class="scene">
    <svg class="boat" viewBox="0 0 60 30" xmlns="http://www.w3.org/2000/svg">
      <path d="M4 22 L56 22 L48 29 L12 29 Z" fill="#0F172A"/>
      <rect x="27" y="4" width="2.4" height="18" fill="#0F172A"/>
      <path d="M29.4 6 L44 20 L29.4 20 Z" fill="#F8FAFB"/>
    </svg>
    <div class="splash-ring"></div>
    <svg class="tail" viewBox="0 0 150 150" xmlns="http://www.w3.org/2000/svg">
      <path d="M75 150 C 60 100, 40 90, 10 70 C 45 78, 60 65, 75 40 C 90 65, 105 78, 140 70 C 110 90, 90 100, 75 150 Z"
            fill="#0E4A5F" stroke="#0A2F3D" stroke-width="2"/>
    </svg>
  </div>
  <div class="caption">Heading out for this week&rsquo;s numbers&hellip;</div>
  <div class="caption-sub">Building the Dana Point PULSE report from live STR, CoStar &amp; Datafy data</div>
</div>
"""


@st.cache_data(ttl=3600, show_spinner=False)
def _generate(_cache_key: str):
    from generate_weekly_report import build_report
    return build_report()


def _pdf_generated_at() -> str:
    if os.path.exists(PDF_PATH):
        return datetime.fromtimestamp(os.path.getmtime(PDF_PATH)).strftime("%b %d, %Y at %I:%M %p")
    return "not yet generated"


col1, col2 = st.columns([5, 1])
with col1:
    st.markdown(
        f"""
        <div class="pulse-header">
          <div class="pulse-header-left">
            <div class="pulse-logo-badge"><img src="{_logo_data_uri()}"></div>
            <div>
              <div class="pulse-title">Dana Point PULSE — Weekly Report</div>
              <div class="pulse-sub">Prepared by GloCon Solutions LLC for Visit Dana Point &nbsp;|&nbsp; Last generated: {_pdf_generated_at()}</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col2:
    regenerate = st.button("🔄 Regenerate", use_container_width=True)

if regenerate:
    _generate.clear()

splash = st.empty()
splash.markdown(WHALE_SPLASH_HTML, unsafe_allow_html=True)

try:
    cache_key = datetime.now().strftime("%Y-%m-%d-%H") if not regenerate else datetime.now().isoformat()
    pdf_path = _generate(cache_key)
except Exception as exc:  # noqa: BLE001
    splash.empty()
    st.error(f"Report generation failed: {exc}")
    st.stop()

splash.empty()

if not os.path.exists(pdf_path):
    st.error("Report file was not created. Check logs for details.")
    st.stop()

with open(pdf_path, "rb") as f:
    pdf_bytes = f.read()

st.download_button(
    "⬇ Download PDF",
    data=pdf_bytes,
    file_name=f"dana_point_pulse_weekly_report_{datetime.now().strftime('%Y-%m-%d')}.pdf",
    mime="application/pdf",
)

b64 = base64.b64encode(pdf_bytes).decode("utf-8")
st.markdown(
    f"""
    <iframe src="data:application/pdf;base64,{b64}"
            width="100%" height="900px" style="border:1px solid #E2E8F0; border-radius:8px;">
    </iframe>
    """,
    unsafe_allow_html=True,
)
