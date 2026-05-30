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
    """Full-screen branded overlay + self-removing script. Paints before React."""
    logo = (
        f'<img src="{data_uri}" alt="" '
        f'style="width:60px;height:60px;border-radius:14px;'
        f'box-shadow:0 8px 28px rgba(0,200,224,0.35);" />'
        if data_uri else ""
    )
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
  #{MARKER} .dp-wordmark {{
    font-size:30px; font-weight:900; letter-spacing:-0.02em; color:#FFFFFF;
    text-align:center; line-height:1.1;
  }}
  #{MARKER} .dp-wordmark span {{ color:#00C8E0; }}
  #{MARKER} .dp-sub {{
    font-size:12px; font-weight:600; letter-spacing:.22em; text-transform:uppercase;
    color:rgba(196,219,247,0.7);
  }}
  #{MARKER} .dp-ring {{
    width:34px; height:34px; border-radius:50%;
    border:3px solid rgba(255,255,255,0.15); border-top-color:#00C8E0;
    animation:dp-spin .8s linear infinite; margin-top:6px;
  }}
  @keyframes dp-spin {{ to {{ transform:rotate(360deg); }} }}
</style>
<div id="{MARKER}">
  {logo}
  <div class="dp-wordmark">Dana Point <span>PULSE</span></div>
  <div class="dp-sub">Tourism Intelligence</div>
  <div class="dp-ring"></div>
</div>
<script id="{MARKER}-js">
(function(){{
  var SEL = '#{MARKER}';
  function ready(){{
    var root = document.getElementById('root');
    // App has mounted once #root holds real, sized content.
    return root && root.children.length > 0 && root.getBoundingClientRect().height > 80;
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
