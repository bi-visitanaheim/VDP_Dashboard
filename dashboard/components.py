"""
VDP Analytics — Interactive Visual Components
Narrative boxes, blob loaders, shader wallpapers, iridescent data cards
"""

import streamlit as st
import streamlit.components.v1 as components


def render_narrative_box(tab_id: str, sample_text: str, height: int = 400) -> None:
    """
    Render a large editable text box with canvas particle effects for keywords.
    Keywords: 'fire' → embers, 'smoke' → puffs, 'metal' → sparks, 'wind' → streaks
    """
    html_template = """
<div style="position:relative; width:100%; height:%%HEIGHT%%px; font-family:sans-serif; background:#0F1419; border-radius:12px; overflow:hidden; border:1px solid #1E293B;">
  <canvas id="particles-%%TID%%" style="position:absolute; top:0; left:0; width:100%; height:100%; z-index:3; pointer-events:none;"></canvas>
  <textarea id="narrative-%%TID%%" style="position:absolute; top:0; left:0; width:100%; height:100%; padding:16px; border:0; border-radius:12px; background:rgba(15,20,25,0.7); color:#E2E8F0; font-size:14px; font-family:'DM Sans',sans-serif; resize:none; z-index:1; outline:none; box-sizing:border-box; line-height:1.6;" placeholder="Enter narrative...">%%STEXT%%</textarea>
</div>
<script>
(function() {
  const TID = '%%TID%%';
  const canvas = document.getElementById('particles-' + TID);
  const textarea = document.getElementById('narrative-' + TID);
  if (!canvas || !textarea) return;

  const ctx = canvas.getContext('2d');
  let particles = [];
  const particleMax = 180;

  function resizeCanvas() {
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;
  }
  resizeCanvas();
  window.addEventListener('resize', resizeCanvas);

  const keywords = {
    fire: /\\b(fire|flame|blaze|heat|burn|inferno)\\b/gi,
    smoke: /\\b(smoke|fog|haze|mist|vapor)\\b/gi,
    metal: /\\b(metal|steel|iron|copper|gold|silver|aluminum)\\b/gi,
    wind: /\\b(wind|breeze|gust|air|drift)\\b/gi,
  };

  const colors = {
    fire: ['#FF6B6B', '#FF8C42', '#FFA366'],
    smoke: ['#64748B', '#475569', '#94A3B8'],
    metal: ['#CBD5E1', '#E2E8F0', '#F1F5F9'],
    wind: ['#0567C8', '#00D4C8', '#32B8C6'],
  };

  function detectKeywords(text) {
    const events = [];
    for (const [type, pattern] of Object.entries(keywords)) {
      let match;
      while ((match = pattern.exec(text)) !== null) {
        events.push({ type, pos: match.index });
      }
    }
    return events;
  }

  function emitParticles(type, count = 5) {
    const typeMap = { fire: 'e', smoke: 's', metal: 'k', wind: 'w' };
    const t = typeMap[type];
    const cols = colors[type];
    for (let i = 0; i < count; i++) {
      const p = {
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * (type === 'wind' ? 3 : 1.5),
        vy: (Math.random() - 0.5) * (type === 'wind' ? 0.5 : 2),
        life: 1,
        t: t,
        col: cols[Math.floor(Math.random() * cols.length)],
      };
      particles.push(p);
    }
  }

  textarea.addEventListener('input', function() {
    const text = this.value;
    const events = detectKeywords(text);
    for (const ev of events) {
      if (Math.random() < 0.1) emitParticles(ev.type, 2);
    }
  });

  function updateParticles() {
    for (let i = particles.length - 1; i >= 0; i--) {
      const p = particles[i];
      p.x += p.vx;
      p.y += p.vy;
      p.life -= 0.01;
      p.vy += 0.15;
      if (p.life <= 0) particles.splice(i, 1);
    }
    if (particles.length > particleMax) particles.splice(0, particles.length - particleMax);
  }

  function drawParticles() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (const p of particles) {
      ctx.globalAlpha = p.life;
      ctx.fillStyle = p.col;
      if (p.t === 'e') {
        ctx.fillRect(p.x - 3, p.y - 3, 6, 6);
      } else if (p.t === 's') {
        ctx.beginPath();
        ctx.arc(p.x, p.y, Math.max(2, 8 * p.life), 0, Math.PI * 2);
        ctx.fill();
      } else if (p.t === 'k') {
        ctx.beginPath();
        ctx.moveTo(p.x, p.y - 4);
        ctx.lineTo(p.x + 4, p.y + 4);
        ctx.lineTo(p.x - 4, p.y + 4);
        ctx.closePath();
        ctx.fill();
      } else if (p.t === 'w') {
        ctx.strokeStyle = p.col;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(p.x - 8, p.y);
        ctx.lineTo(p.x + 8, p.y);
        ctx.stroke();
      }
    }
    ctx.globalAlpha = 1;
  }

  function animate() {
    updateParticles();
    drawParticles();
    requestAnimationFrame(animate);
  }
  animate();
})();
</script>
"""

    html = html_template.replace("%%TID%%", tab_id).replace("%%HEIGHT%%", str(height)).replace("%%STEXT%%", sample_text)
    components.html(html, height=height + 40)


def render_kpi_blob_loaders(height: int = 560) -> None:
    """Render 50 unique CSS blob loading indicators in a wrapping grid."""

    html = f"""
<div style="width:100%; padding:16px; background:rgba(10,20,30,0.5); border-radius:12px;">
  <style>
    .blob-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(64px, 1fr));
      gap: 16px;
      padding: 16px;
      background: linear-gradient(135deg, rgba(0,212,200,0.05) 0%, rgba(167,139,250,0.05) 100%);
      border-radius: 8px;
    }}
    .blob {{
      width: 64px;
      height: 64px;
      border-radius: 60% 40% 30% 70% / 60% 30% 70% 40%;
      animation: blob-anim 3s infinite;
      position: relative;
    }}
    @keyframes blob-breathe {{
      0%, 100% {{ border-radius: 60% 40% 30% 70% / 60% 30% 70% 40%; }}
      50% {{ border-radius: 30% 60% 70% 40% / 40% 60% 30% 70%; }}
    }}
    @keyframes blob-morph {{
      0%, 100% {{ border-radius: 60% 40% 30% 70% / 60% 30% 70% 40%; }}
      25% {{ border-radius: 40% 60% 70% 30% / 70% 60% 40% 30%; }}
      50% {{ border-radius: 70% 30% 60% 40% / 30% 70% 60% 40%; }}
      75% {{ border-radius: 40% 70% 40% 60% / 60% 40% 70% 30%; }}
    }}
    @keyframes blob-pulse {{
      0%, 100% {{ transform: scale(1); }}
      50% {{ transform: scale(1.1); }}
    }}
    @keyframes blob-squish {{
      0%, 100% {{ transform: scaleY(1); }}
      50% {{ transform: scaleY(1.2) scaleX(0.9); }}
    }}
    @keyframes blob-spin {{
      0% {{ transform: rotate(0deg); }}
      100% {{ transform: rotate(360deg); }}
    }}
    .blob1 {{ background: #00D4C8; animation-name: blob-breathe; animation-duration: 4s; }}
    .blob2 {{ background: #0567C8; animation-name: blob-morph; animation-duration: 5s; }}
    .blob3 {{ background: #21808D; animation-name: blob-pulse; animation-duration: 3s; }}
    .blob4 {{ background: #10B981; animation-name: blob-squish; animation-duration: 3.5s; }}
    .blob5 {{ background: #FF8C42; animation-name: blob-spin; animation-duration: 6s; }}
    .blob6 {{ background: #00D4C8; animation-name: blob-morph; animation-duration: 4.5s; }}
    .blob7 {{ background: #0567C8; animation-name: blob-breathe; animation-duration: 3.8s; }}
    .blob8 {{ background: #21808D; animation-name: blob-squish; animation-duration: 4.2s; }}
    .blob9 {{ background: #10B981; animation-name: blob-pulse; animation-duration: 3.2s; }}
    .blob10 {{ background: #FF8C42; animation-name: blob-morph; animation-duration: 5.5s; }}
    .blob-set2 {{ opacity: 0.8; }}
    .blob-set3 {{ opacity: 0.6; }}
    .blob-set4 {{ opacity: 0.7; }}
    .blob-set5 {{ opacity: 0.9; }}
  </style>
  <div class="blob-grid">
    {"".join(f'<div class="blob blob{(i%10)+1}" style="animation-delay: {i*0.1}s;"></div>' for i in range(50))}
  </div>
</div>
"""
    components.html(html, height=height)


def inject_shader_wallpaper() -> None:
    """Inject a full-page interactive shader wallpaper that reacts to mouse position."""

    shader_html = """
<canvas id="vdp-bg-shader" style="position:fixed; top:0; left:0; width:100%; height:100%; z-index:-1; pointer-events:none;"></canvas>
<script>
(function() {
  if (window.__vdpBgInit) return;
  window.__vdpBgInit = true;

  const canvas = document.getElementById('vdp-bg-shader');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }
  resize();
  window.addEventListener('resize', resize);

  let mouseX = canvas.width / 2;
  let mouseY = canvas.height / 2;
  document.addEventListener('mousemove', (e) => {
    mouseX = e.clientX;
    mouseY = e.clientY;
  });

  const colors = [
    { r: 0, g: 212, b: 200 },   // #00D4C8
    { r: 10, g: 61, b: 84 },    // #0A3D54
    { r: 33, g: 128, b: 141 },  // #21808D
    { r: 5, g: 103, b: 200 },   // #0567C8
  ];

  function drawGradient() {
    const grd = ctx.createRadialGradient(mouseX, mouseY, 0, mouseX, mouseY, 800);
    grd.addColorStop(0, 'rgba(0, 212, 200, 0.15)');
    grd.addColorStop(0.5, 'rgba(10, 61, 84, 0.08)');
    grd.addColorStop(1, 'rgba(33, 128, 141, 0.02)');
    ctx.fillStyle = grd;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }

  function animate() {
    ctx.fillStyle = 'rgba(8, 12, 18, 0.05)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    drawGradient();
    requestAnimationFrame(animate);
  }
  animate();
})();
</script>
"""

    st.markdown(shader_html, unsafe_allow_html=True)


def render_mono_cards(cards_data: list, tab_id: str, height: int = 280) -> None:
    """
    Render iridescent monochromatic data cards with 3D perspective hover effect.
    cards_data: list of dicts with keys 'label', 'value', 'unit'
    """

    card_html_items = []
    for i, card in enumerate(cards_data):
        label = card.get('label', f'Card {i}')
        value = card.get('value', '0')
        unit = card.get('unit', '')

        card_html_items.append(f"""
<div class="mono-card" style="animation-delay: {i*0.05}s;">
  <div class="mono-card-inner">
    <div class="mono-card-content">
      <div class="mono-label">{label}</div>
      <div class="mono-value">{value}</div>
      <div class="mono-unit">{unit}</div>
    </div>
  </div>
</div>
""")

    html = f"""
<div style="width:100%; padding:16px; background:rgba(10,20,30,0.3); border-radius:12px;">
  <style>
    .mono-cards-container {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 12px;
      perspective: 1000px;
    }}
    .mono-card {{
      aspect-ratio: 1;
      background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
      border-radius: 12px;
      padding: 16px;
      border: 1px solid rgba(226, 232, 240, 0.1);
      cursor: pointer;
      transform-style: preserve-3d;
      transition: all 0.4s cubic-bezier(0.23, 1, 0.320, 1);
      position: relative;
      overflow: hidden;
    }}
    .mono-card::before {{
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: radial-gradient(circle at var(--mouse-x, 50%) var(--mouse-y, 50%),
                                  rgba(226, 232, 240, 0.2) 0%,
                                  transparent 50%);
      opacity: 0;
      transition: opacity 0.3s;
      pointer-events: none;
    }}
    .mono-card:hover {{
      transform: perspective(1000px) rotateX(5deg) rotateY(5deg) translateZ(10px);
      border-color: rgba(226, 232, 240, 0.3);
      box-shadow: 0 20px 40px rgba(0, 212, 200, 0.1);
    }}
    .mono-card:hover::before {{
      opacity: 1;
    }}
    .mono-card-inner {{
      width: 100%;
      height: 100%;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      text-align: center;
    }}
    .mono-label {{
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: rgba(226, 232, 240, 0.6);
      margin-bottom: 8px;
    }}
    .mono-value {{
      font-size: 20px;
      font-weight: 700;
      color: #E2E8F0;
      font-family: 'Helvetica Neue', Helvetica, sans-serif;
      letter-spacing: -0.02em;
    }}
    .mono-unit {{
      font-size: 10px;
      color: rgba(226, 232, 240, 0.5);
      margin-top: 4px;
    }}
  </style>
  <div class="mono-cards-container">
    {"".join(card_html_items)}
  </div>
</div>
<script>
document.querySelectorAll('.mono-card').forEach(card => {{
  card.addEventListener('mousemove', (e) => {{
    const rect = card.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width * 100;
    const y = (e.clientY - rect.top) / rect.height * 100;
    card.style.setProperty('--mouse-x', x + '%');
    card.style.setProperty('--mouse-y', y + '%');
  }});
}});
</script>
"""

    components.html(html, height=height + 40)
