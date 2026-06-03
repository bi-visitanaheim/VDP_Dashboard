#!/usr/bin/env python3
"""
patch_streamlit_splash.py — Brand Streamlit's static index.html at build time.

Streamlit serves a static index.html before any app code runs. By default the
browser shows the "Streamlit" title, the Streamlit favicon, and a generic
loading state for a beat before the Dana Point PULSE app mounts. That flash of
Streamlit branding is what users see "first."

This script patches that static template once, during the Docker build, so the
very first paint is already Dana Point PULSE:
  1. <title>           -> "Dana Point PULSE"
  2. favicon <link>    -> embedded data-URI of dashboard/static/favicon.png
                          (no network request, shows instantly, never pops in)
  3. a branded splash  -> full-screen ocean-gradient overlay with the PULSE
                          wordmark + spinner, injected as the first child of
                          <body>. A tiny inline script fades it out as soon as
                          the React root has mounted real content.

Idempotent: re-running is a no-op (guard marker check). Safe to call on every
build. Locates Streamlit's static dir via the installed package, so it tracks
whatever version requirements.txt pins.

Usage:  python scripts/patch_streamlit_splash.py
"""

from __future__ import annotations

import base64
import os
import sys

MARKER = "dp-pulse-splash"  # guard so we never double-patch
APP_TITLE = "Dana Point PULSE"


def _find_index_html() -> str | None:
    try:
        import streamlit  # noqa: WPS433 (runtime import by design)
    except ImportError:
        print("[patch] streamlit not importable — skipping (non-fatal)")
        return None
    path = os.path.join(os.path.dirname(streamlit.__file__), "static", "index.html")
    return path if os.path.isfile(path) else None


def _favicon_data_uri() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    fav = os.path.join(here, "..", "dashboard", "static", "favicon.png")
    fav = os.path.normpath(fav)
    if not os.path.isfile(fav):
        print(f"[patch] favicon not found at {fav} — using empty icon")
        return ""
    with open(fav, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _splash_html(data_uri: str) -> str:
    """Full-screen branded overlay + self-removing script. Paints before React.

    The logo is an inline animated SVG pulse wave (two teal waves flowing
    through a breathing tile) — matches the PULSE brand mark and needs no image
    request, so it animates instantly on first paint.
    """
    return f"""
<style id="{MARKER}-style">
  #{MARKER} {{
    position:fixed; inset:0; z-index:2147483647;
    background:
      radial-gradient(1200px 600px at 70% -10%, rgba(0,200,224,0.18), transparent 60%),
      linear-gradient(160deg, #0B1E38 0%, #0E2C44 45%, #123A5E 100%);
    background-color:#0B1E38;
    display:flex; flex-direction:column; align-items:center; justify-content:center;
    gap:22px; font-family:'Outfit','Segoe UI',system-ui,sans-serif;
    transition:opacity .55s ease, visibility .55s ease; opacity:1;
  }}
  #{MARKER}.dp-hide {{ opacity:0; visibility:hidden; pointer-events:none; }}

  /* Breathing tile */
  #{MARKER} .dp-logo {{ animation:dp-breathe 2.8s ease-in-out infinite; }}
  #{MARKER} .dp-tile {{
    filter:drop-shadow(0 10px 30px rgba(0,200,224,0.28));
    animation:dp-glow 2.8s ease-in-out infinite;
  }}
  @keyframes dp-breathe {{
    0%,100% {{ transform:translateY(0) scale(1); }}
    50%     {{ transform:translateY(-3px) scale(1.03); }}
  }}
  @keyframes dp-glow {{
    0%,100% {{ filter:drop-shadow(0 10px 24px rgba(0,200,224,0.22)); }}
    50%     {{ filter:drop-shadow(0 14px 40px rgba(0,200,224,0.45)); }}
  }}

  /* Flowing waves — two parallax layers translating one full period, seamless */
  #{MARKER} .dp-wave1 {{ animation:dp-flow1 2.4s linear infinite; }}
  #{MARKER} .dp-wave2 {{ animation:dp-flow2 3.6s linear infinite; }}
  @keyframes dp-flow1 {{ to {{ transform:translateX(-96px); }} }}
  @keyframes dp-flow2 {{ to {{ transform:translateX(96px); }} }}

  /* Pulse dot riding the crest */
  #{MARKER} .dp-pulsedot {{ animation:dp-pulse 1.4s ease-out infinite; transform-origin:center; }}
  @keyframes dp-pulse {{
    0%   {{ opacity:.9; r:3; }}
    70%  {{ opacity:0;  r:13; }}
    100% {{ opacity:0;  r:13; }}
  }}

  #{MARKER} .dp-wordmark {{
    font-size:30px; font-weight:900; letter-spacing:-0.02em; color:#FFFFFF;
    text-align:center; line-height:1.1;
    animation:dp-rise .7s ease both;
  }}
  #{MARKER} .dp-wordmark span {{ color:#00C8E0; }}
  #{MARKER} .dp-sub {{
    font-size:12px; font-weight:600; letter-spacing:.22em; text-transform:uppercase;
    color:rgba(196,219,247,0.7); animation:dp-rise .7s .1s ease both;
  }}
  @keyframes dp-rise {{ from {{ opacity:0; transform:translateY(8px); }} to {{ opacity:1; transform:translateY(0); }} }}

  /* Loading track */
  #{MARKER} .dp-track {{
    width:148px; height:3px; border-radius:3px; overflow:hidden;
    background:rgba(255,255,255,0.10); margin-top:4px;
  }}
  #{MARKER} .dp-track i {{
    display:block; height:100%; width:40%; border-radius:3px;
    background:linear-gradient(90deg,transparent,#00C8E0,transparent);
    animation:dp-slide 1.2s ease-in-out infinite;
  }}
  @keyframes dp-slide {{ 0% {{ transform:translateX(-120%); }} 100% {{ transform:translateX(320%); }} }}

  @media (prefers-reduced-motion: reduce) {{
    #{MARKER} .dp-logo, #{MARKER} .dp-tile, #{MARKER} .dp-wave1,
    #{MARKER} .dp-wave2, #{MARKER} .dp-pulsedot, #{MARKER} .dp-track i {{ animation:none !important; }}
  }}
</style>
<div id="{MARKER}">
  <div class="dp-logo">
    <svg width="100" height="100" viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Dana Point PULSE">
      <defs>
        <linearGradient id="dpTileGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="#13314F"/>
          <stop offset="1" stop-color="#0B2138"/>
        </linearGradient>
        <linearGradient id="dpWaveGrad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stop-color="#0EA5C4"/>
          <stop offset="0.5" stop-color="#00C8E0"/>
          <stop offset="1" stop-color="#6EE7F0"/>
        </linearGradient>
        <clipPath id="dpClip"><rect x="6" y="6" width="84" height="84" rx="22"/></clipPath>
      </defs>
      <rect class="dp-tile" x="6" y="6" width="84" height="84" rx="22"
            fill="url(#dpTileGrad)" stroke="rgba(0,200,224,0.35)" stroke-width="1.5"/>
      <g clip-path="url(#dpClip)">
        <path class="dp-wave dp-wave2" d="M -96 52 Q -72 62 -48 52 T 0 52 T 48 52 T 96 52 T 144 52 T 192 52"
              stroke="#1E6E86" stroke-width="3" stroke-linecap="round" fill="none" opacity="0.55"/>
        <path class="dp-wave dp-wave1" d="M -96 46 Q -72 36 -48 46 T 0 46 T 48 46 T 96 46 T 144 46 T 192 46"
              stroke="url(#dpWaveGrad)" stroke-width="3.5" stroke-linecap="round" fill="none"/>
        <circle class="dp-pulsedot" cx="48" cy="46" r="3" fill="#9DF2FA"/>
      </g>
    </svg>
  </div>
  <div class="dp-wordmark">Dana Point <span>PULSE</span></div>
  <div class="dp-sub">Tourism Intelligence</div>
  <div class="dp-track"><i></i></div>
</div>
<script id="{MARKER}-js">
(function(){{
  var SEL = '#{MARKER}';
  function ready(){{
    var root = document.getElementById('root');
    if(!root || root.children.length === 0) return false;
    // NOTE: the app shell (.stApp) is position:absolute + height:100vh, so
    // #root's own bounding height stays 0 even after the app mounts. Measuring
    // #root here would never satisfy the height check and the splash would hang
    // on its failsafe. Detect the real rendered content inside the main block
    // container instead.
    var main = document.querySelector('[data-testid="stMain"]') ||
               document.querySelector('[data-testid="stAppViewContainer"]') ||
               document.querySelector('.stApp');
    if(!main) return false;
    var content = main.querySelector(
      '[data-testid="stMainBlockContainer"], .block-container, [data-testid="stVerticalBlock"]');
    return !!(content && content.getBoundingClientRect().height > 80);
  }}
  function hide(){{
    var el = document.querySelector(SEL);
    if(!el) return;
    el.classList.add('dp-hide');
    setTimeout(function(){{ if(el && el.parentNode) el.parentNode.removeChild(el); }}, 650);
  }}
  var start = Date.now();
  var iv = setInterval(function(){{
    // Hold a 400ms minimum so the brand reads, then leave as soon as app is up.
    if((ready() && Date.now()-start > 400) || Date.now()-start > 12000){{
      clearInterval(iv); hide();
    }}
  }}, 80);
  window.addEventListener('load', function(){{ setTimeout(function(){{ if(ready()) hide(); }}, 600); }});
}})();
</script>
"""


def patch() -> int:
    index_path = _find_index_html()
    if not index_path:
        print("[patch] no index.html located — skipping (non-fatal)")
        return 0

    with open(index_path, "r", encoding="utf-8") as fh:
        html = fh.read()

    if MARKER in html:
        print("[patch] already patched — no-op")
        return 0

    data_uri = _favicon_data_uri()

    # 1) Title
    import re
    html = re.sub(r"<title>.*?</title>", f"<title>{APP_TITLE}</title>", html, count=1, flags=re.S)
    if f"<title>{APP_TITLE}</title>" not in html:
        # No <title> present — add one inside <head>
        html = html.replace("</head>", f"<title>{APP_TITLE}</title></head>", 1)

    # 2) Favicon — replace any existing icon links, then inject ours
    if data_uri:
        html = re.sub(
            r'<link[^>]*rel=["\'][^"\']*icon[^"\']*["\'][^>]*>',
            "",
            html,
            flags=re.I,
        )
        icon_link = f'<link rel="icon" type="image/png" href="{data_uri}"/>'
        html = html.replace("</head>", f"{icon_link}</head>", 1)

    # 3) Splash overlay — first child of <body> so it paints before the bundle
    splash = _splash_html(data_uri)
    if "<body>" in html:
        html = html.replace("<body>", "<body>" + splash, 1)
    else:
        # Some builds add attributes to <body>; match the opening tag generically
        html = re.sub(r"(<body[^>]*>)", r"\1" + splash.replace("\\", "\\\\"), html, count=1)

    with open(index_path, "w", encoding="utf-8") as fh:
        fh.write(html)

    print(f"[patch] branded splash + favicon + title injected into {index_path}")
    return 0


if __name__ == "__main__":
    sys.exit(patch())
