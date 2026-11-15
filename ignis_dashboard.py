"""IGNIS UY · Premium control center (dashboard) and shared design system.

Everything shown here is computed from the records loaded in the session.
No demonstration figures are ever injected: empty states say so explicitly.
"""
from __future__ import annotations

import json
from html import escape
from typing import Callable, Dict, Optional

import pandas as pd
import streamlit as st

from ignis_scene3d import PALETTE, render_uruguay_scene

PLOT_FONT = dict(family="Inter, Segoe UI, sans-serif", color="#dbe9f3", size=12)
MONTHS = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]


# --------------------------------------------------------------------------
# Design system
# --------------------------------------------------------------------------
def design_system_css() -> str:
    """Global tokens + component polish layered over ignis_visual's base theme."""
    return """<style>
    :root{
      --ig-navy:#06101D;--ig-midnight:#091827;--ig-cyan:#00D9F5;--ig-ice:#7DEBFF;--ig-orange:#FF6A1A;
      --ig-ember:#FF3B30;--ig-slate:#91A8BA;--ig-white:#F4FAFF;
      --ig-panel:rgba(9,24,39,.78);--ig-line:rgba(125,235,255,.16);--ig-line-strong:rgba(125,235,255,.34);
      --ig-radius:6px;--ig-shadow:0 18px 44px rgba(0,0,0,.38);
    }
    .stApp{background:
      radial-gradient(1200px 520px at 18% -8%,rgba(0,217,245,.07),transparent 60%),
      radial-gradient(900px 420px at 92% 0%,rgba(255,106,26,.05),transparent 55%),
      linear-gradient(170deg,#0a1a2c 0%,#06101d 48%,#050d18 100%)!important;color:var(--ig-white)}
    .block-container,[data-testid="stMainBlockContainer"]{padding-top:.55rem!important}
    h1,h2,h3,h4{letter-spacing:-.015em}
    /* premium top bar */
    .ig-topbar{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;
      padding:10px 16px;margin:0 0 14px;background:var(--ig-panel);border:1px solid var(--ig-line);border-radius:var(--ig-radius);
      backdrop-filter:blur(12px);box-shadow:var(--ig-shadow)}
    .ig-brand{display:flex;align-items:center;gap:12px;font-weight:800;font-size:1.05rem;letter-spacing:.02em}
    .ig-brand img{width:38px;height:38px;object-fit:contain}
    .ig-brand small{display:block;color:var(--ig-slate);font-size:.68rem;font-weight:600;letter-spacing:.14em;text-transform:uppercase}
    .ig-brand b{color:var(--ig-ice)}
    .ig-topmeta{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
    .ig-chip{display:inline-flex;align-items:center;gap:7px;padding:6px 11px;border-radius:4px;font-size:.74rem;font-weight:700;letter-spacing:.06em;
      border:1px solid var(--ig-line);background:rgba(13,42,68,.5);color:#dbe9f3;text-transform:uppercase}
    .ig-chip span{color:var(--ig-slate);font-weight:600;letter-spacing:0;text-transform:none}
    .ig-chip.hist{border-color:rgba(0,217,245,.4);color:var(--ig-ice);background:rgba(0,217,245,.08)}
    .ig-chip.live{border-color:rgba(255,106,26,.5);color:#ffb38a;background:rgba(255,106,26,.1)}
    .ig-chip.live i{width:7px;height:7px;border-radius:50%;background:var(--ig-orange);box-shadow:0 0 8px var(--ig-orange)}
    .ig-chip.ok{border-color:rgba(109,214,154,.35);color:#9fe6bd}
    .ig-chip.warn{border-color:rgba(255,195,155,.35);color:#ffc39b}
    .ig-icon-btn{width:34px;height:34px;display:inline-flex;align-items:center;justify-content:center;border-radius:50%;border:1px solid var(--ig-line);color:var(--ig-ice);background:rgba(0,217,245,.06)}
    .ig-icon-btn svg{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
    /* section headings */
    .ig-section{display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin:18px 0 8px}
    .ig-section h3{margin:0;font-size:1.05rem;font-weight:800;color:var(--ig-white)}
    .ig-section h3::before{content:"";display:inline-block;width:3px;height:.95em;background:var(--ig-cyan);margin-right:10px;vertical-align:-2px;border-radius:1px}
    .ig-section span{color:var(--ig-slate);font-size:.78rem}
    /* panels */
    .ig-panel{background:var(--ig-panel);border:1px solid var(--ig-line);border-radius:var(--ig-radius);padding:14px 16px;box-shadow:var(--ig-shadow);backdrop-filter:blur(10px)}
    .ig-panel h4{margin:0 0 6px;font-size:.78rem;letter-spacing:.14em;text-transform:uppercase;color:var(--ig-slate)}
    .ig-note{color:var(--ig-slate);font-size:.78rem;line-height:1.55}
    .ig-empty{border:1px dashed var(--ig-line-strong);border-radius:var(--ig-radius);padding:22px 18px;text-align:center;color:var(--ig-slate);background:rgba(9,24,39,.45)}
    .ig-empty b{display:block;color:var(--ig-white);font-size:1rem;margin-bottom:4px}
    /* Streamlit widget polish */
    [data-testid="stVerticalBlockBorderWrapper"]>div{border-radius:var(--ig-radius)!important}
    [data-testid="stVerticalBlockBorderWrapper"]{border-color:var(--ig-line)!important;background:rgba(9,24,39,.55)!important;transition:border-color .2s}
    [data-testid="stVerticalBlockBorderWrapper"]:hover{border-color:var(--ig-line-strong)!important}
    .stButton>button,.stDownloadButton>button,.stLinkButton>a,.stFormSubmitButton>button{
      border-radius:5px!important;border:1px solid var(--ig-line-strong)!important;background:rgba(0,217,245,.07)!important;color:var(--ig-white)!important;
      transition:transform .15s ease,background-color .2s ease,border-color .2s ease,box-shadow .2s ease!important}
    .stButton>button:hover,.stDownloadButton>button:hover,.stLinkButton>a:hover,.stFormSubmitButton>button:hover{
      transform:translateY(-1px);border-color:var(--ig-cyan)!important;background:rgba(0,217,245,.16)!important;box-shadow:0 8px 22px rgba(0,217,245,.12)!important}
    .stButton>button[kind="primary"],.stDownloadButton>button[kind="primary"],.stFormSubmitButton>button[kind="primary"]{
      background:linear-gradient(100deg,#00bfd8,#0b6fd6)!important;border-color:rgba(125,235,255,.55)!important;color:#fff!important}
    .stButton>button:focus-visible,.stDownloadButton>button:focus-visible{outline:2px solid var(--ig-ice)!important;outline-offset:2px!important}
    [data-testid="stMetric"]{background:linear-gradient(140deg,rgba(13,42,68,.85),rgba(9,24,39,.9))!important;border:1px solid var(--ig-line)!important;border-radius:var(--ig-radius)!important}
    [data-testid="stMetricLabel"]{color:var(--ig-slate)!important;letter-spacing:.06em;text-transform:uppercase;font-size:.7rem!important}
    .stTabs [data-baseweb="tab-list"]{gap:4px;border-bottom:1px solid var(--ig-line)}
    .stTabs [data-baseweb="tab"]{border-radius:4px 4px 0 0;padding:8px 14px;color:var(--ig-slate);font-weight:600}
    .stTabs [aria-selected="true"]{color:var(--ig-ice)!important;background:rgba(0,217,245,.08)}
    .stTabs [data-baseweb="tab-highlight"]{background:var(--ig-cyan)!important}
    [data-testid="stDataFrame"]{border:1px solid var(--ig-line);border-radius:var(--ig-radius);overflow:hidden}
    .stAlert{border-radius:var(--ig-radius)!important}
    div[data-baseweb="select"]>div,div[data-baseweb="input"]>div,.stTextInput input,.stTextArea textarea{border-radius:5px!important;border-color:var(--ig-line-strong)!important;background:rgba(9,24,39,.8)!important}
    .stTextInput input:focus,.stTextArea textarea:focus{border-color:var(--ig-cyan)!important;box-shadow:0 0 0 1px var(--ig-cyan)!important}
    .stSlider [data-baseweb="slider"] div[role="slider"]{background:var(--ig-white)!important;border:2px solid var(--ig-cyan)!important;box-shadow:0 0 10px rgba(0,217,245,.5)!important}
    [data-testid="stExpander"] details{border:1px solid var(--ig-line)!important;border-radius:var(--ig-radius)!important;background:rgba(9,24,39,.5)!important}
    [data-testid="stExpander"] summary:hover{color:var(--ig-ice)!important}
    .stProgress>div>div{background:linear-gradient(90deg,var(--ig-cyan),#0b6fd6)!important}
    [data-testid="stChatMessage"]{background:rgba(9,24,39,.6)!important;border:1px solid var(--ig-line)!important;border-radius:var(--ig-radius)!important}
    /* sidebar: thin cyan details */
    section[data-testid="stSidebar"]{background:linear-gradient(180deg,#0a1a2d 0%,#07131f 100%)!important;border-right:1px solid rgba(0,217,245,.14)!important}
    section[data-testid="stSidebar"] div[class*="st-key-ignis_nav_"] button{font-size:.83rem!important;min-height:36px!important;border-radius:4px!important}
    section[data-testid="stSidebar"] div[class*="st-key-ignis_nav_"] button[kind="primary"]{
      background:linear-gradient(90deg,rgba(0,217,245,.22),rgba(11,111,214,.14))!important;border:1px solid rgba(0,217,245,.55)!important;box-shadow:inset 3px 0 var(--ig-cyan),0 0 16px rgba(0,217,245,.12)!important}
    section[data-testid="stSidebar"] div[class*="st-key-ignis_nav_"] button[kind="primary"]::before{background:var(--ig-cyan)!important}
    .ignis-side-brand-copy strong span{color:var(--ig-cyan)!important}
    .ignis-side-project{border-color:rgba(0,217,245,.25)!important}
    /* ask panel */
    .ig-ask-head{display:flex;align-items:center;gap:12px;margin-bottom:8px}
    .ig-ask-emblem{width:40px;height:40px;border-radius:50%;position:relative;flex:none;
      background:radial-gradient(circle at 50% 50%,rgba(0,217,245,.35),rgba(0,217,245,.05) 60%,transparent 70%);border:1px solid rgba(0,217,245,.4)}
    .ig-ask-emblem::before,.ig-ask-emblem::after{content:"";position:absolute;inset:6px;border-radius:50%;border:1px solid rgba(125,235,255,.55);border-right-color:transparent;border-bottom-color:transparent;animation:igspin 6s linear infinite}
    .ig-ask-emblem::after{inset:12px;animation-duration:9s;animation-direction:reverse;border-color:rgba(255,106,26,.6);border-left-color:transparent;border-top-color:transparent}
    @keyframes igspin{to{transform:rotate(360deg)}}
    @media (prefers-reduced-motion:reduce){.ig-ask-emblem::before,.ig-ask-emblem::after{animation:none}}
    .ig-ask-head b{display:block;font-size:1rem}
    .ig-ask-head small{color:var(--ig-slate);font-size:.74rem}
    .ig-msg{padding:10px 12px;border-radius:6px;margin:6px 0;font-size:.86rem;line-height:1.5;animation:igfade .35s ease}
    .ig-msg.u{background:rgba(13,42,68,.75);border:1px solid var(--ig-line);margin-left:18px}
    .ig-msg.a{background:rgba(255,106,26,.07);border:1px solid rgba(255,106,26,.25);margin-right:18px}
    .ig-msg small{display:block;color:var(--ig-slate);margin-top:5px;font-size:.72rem}
    @keyframes igfade{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
    @media (prefers-reduced-motion:reduce){.ig-msg{animation:none}.stButton>button:hover{transform:none}}
    .ig-ask-sugg .stButton>button{font-size:.76rem!important;min-height:32px!important;padding:4px 10px!important;text-align:left!important;justify-content:flex-start!important;background:rgba(9,24,39,.6)!important}
    @media (max-width:900px){.ig-topbar{padding:9px 12px}.ig-topmeta{gap:6px}.ig-chip{font-size:.66rem;padding:5px 8px}}
    </style>"""


def apply_design_system() -> None:
    st.markdown(design_system_css(), unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Top bar
# --------------------------------------------------------------------------
def render_topbar(logo_uri: str, selected_year: Optional[int], stats: Dict, live: bool = False,
                  period: Optional[str] = None) -> None:
    """Minimal top navigation. 'Live' appears only with an actual NRT connection."""
    if live:
        status = '<span class="ig-chip live"><i></i>Live NRT connection</span>'
    elif stats.get("latest"):
        status = f'<span class="ig-chip hist">Historical data <span>· latest {escape(str(stats["latest"]))}</span></span>'
    else:
        status = '<span class="ig-chip hist">Historical data <span>· no records loaded</span></span>'
    period_txt = period or (f"{stats['first_year']}–{stats['last_year']}" if stats.get("first_year") else "—")
    year_txt = str(selected_year) if selected_year is not None else "—"
    logo = f'<img src="{logo_uri}" alt="IGNIS UY logo">' if logo_uri else ""
    st.markdown(
        '<div class="ig-topbar">'
        f'<div class="ig-brand">{logo}<div>IGNIS <b>UY</b><small>Historical archive · NASA FIRMS 2000–2026</small></div></div>'
        '<div class="ig-topmeta">'
        f'<span class="ig-chip">Period <span>{escape(period_txt)}</span></span>'
        f'<span class="ig-chip">Selected year <span>{escape(year_txt)}</span></span>'
        f'{status}'
        '<span class="ig-icon-btn" title="Notifications: none — this platform does not issue alerts" aria-label="Notifications">'
        '<svg viewBox="0 0 24 24"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9M10 21a2 2 0 0 0 4 0"/></svg></span>'
        '<span class="ig-icon-btn" title="Settings live in the sidebar filters and the scene control panel" aria-label="Settings">'
        '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></svg></span>'
        '<span class="ig-icon-btn" title="Full screen: use the radial menu inside the 3D scene" aria-label="Full screen">'
        '<svg viewBox="0 0 24 24"><path d="M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5"/></svg></span>'
        '</div></div>',
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------
# Animated statistics strip (isolated component; numbers come from Python)
# --------------------------------------------------------------------------
def dashboard_stats(combined: pd.DataFrame, sample: pd.DataFrame, selected: Optional[int],
                    cases: int, associations: int) -> Dict[str, Dict]:
    """Compact scientific metrics computed only from the loaded records."""
    def fam(series):
        s = series.astype(str).str.upper()
        return int(s.str.contains("MODIS").sum()), int(s.str.contains("VIIRS").sum())
    has = isinstance(sample, pd.DataFrame) and not sample.empty
    modis, viirs = fam(sample["instrumento"]) if has else (0, 0)
    years = int(sample["anio"].nunique()) if has else 0
    span = f"{int(sample['anio'].min())}–{int(sample['anio'].max())}" if has else "no records"
    months = int(sample.groupby(["anio", "mes"]).ngroups) if has else 0
    possible = years * 12 if years else 0
    return {
        "obs": {"value": int(len(sample)) if has else 0, "label": "Imported FIRMS observations", "sub": "selected region & sensors" if has else "import data to begin", "icon": "fire"},
        "years": {"value": years, "label": "Years represented", "sub": span, "icon": "clock"},
        "modis": {"value": modis, "label": "MODIS observations", "sub": "Terra / Aqua", "icon": "sat"},
        "viirs": {"value": viirs, "label": "VIIRS observations", "sub": "S-NPP / NOAA-20 / NOAA-21", "icon": "sat"},
        "cover": {"value": months, "label": "Months with imported records", "sub": f"of {possible} calendar months" if possible else "coverage not verified", "icon": "layers"},
        "cases": {"value": int(cases), "label": "Documented reference cases", "sub": "locality references, not perimeters", "icon": "pin"},
        "assoc": {"value": int(associations), "label": "Satellite–ground associations", "sub": "from the fusion tab" if associations else "run the fusion tab", "icon": "link"},
    }


_ICONS = {
    "fire": '<path d="M12 22c4.4 0 7-3 7-6.8 0-3.2-2-5.4-3.5-7.2-.5 2-1.5 3-2.5 3.5C13.5 9 12 6 12.5 2 9 4.5 5 9 5 15.2 5 19 7.6 22 12 22z"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "sat": '<rect x="9" y="9" width="6" height="6" rx="1"/><path d="M3 5l4 4M21 5l-4 4M3 19l4-4M21 19l-4-4M2 2l3 3M22 2l-3 3M2 22l3-3M22 22l-3-3"/>',
    "layers": '<path d="M12 3l9 5-9 5-9-5 9-5zM3 13l9 5 9-5M3 17l9 5 9-5"/>',
    "pin": '<path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 0 1 16 0z"/><circle cx="12" cy="10" r="2.5"/>',
    "link": '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
}


def stats_strip_html(stats: Dict[str, Dict]) -> str:
    cards = []
    for key, c in stats.items():
        cards.append(
            f'<div class="card" data-key="{escape(key)}"><div class="ico"><svg viewBox="0 0 24 24">{_ICONS[c["icon"]]}</svg></div>'
            f'<div class="val" data-v="{int(c["value"])}">0</div><div class="lbl">{escape(c["label"])}</div><div class="sub">{escape(c["sub"])}</div></div>'
        )
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
    :root{{--cyan:#00D9F5;--ice:#7DEBFF;--slate:#91A8BA;--white:#F4FAFF;--orange:#FF6A1A}}
    body{{margin:0;background:transparent;font-family:Inter,"Segoe UI",system-ui,sans-serif;color:var(--white)}}
    .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}}
    .card{{position:relative;overflow:hidden;background:linear-gradient(140deg,rgba(13,42,68,.85),rgba(9,24,39,.92));border:1px solid rgba(125,235,255,.16);border-radius:6px;
      padding:13px 14px 12px;min-height:108px;transition:transform .2s ease,border-color .2s ease,box-shadow .2s ease}}
    .card:hover{{transform:translateY(-2px);border-color:rgba(125,235,255,.42);box-shadow:0 14px 30px rgba(0,0,0,.35)}}
    .card::after{{content:"";position:absolute;left:0;right:0;bottom:0;height:2px;background:linear-gradient(90deg,var(--cyan),transparent 70%);opacity:.6}}
    .card[data-key="obs"]::after,.card[data-key="modis"]::after,.card[data-key="viirs"]::after{{background:linear-gradient(90deg,var(--orange),transparent 70%)}}
    .ico{{position:absolute;right:12px;top:12px;width:28px;height:28px;border-radius:6px;border:1px solid rgba(125,235,255,.22);display:flex;align-items:center;justify-content:center;background:rgba(0,217,245,.06)}}
    .ico svg{{width:15px;height:15px;fill:none;stroke:var(--ice);stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}}
    .val{{font-size:1.75rem;font-weight:800;letter-spacing:-.02em;font-variant-numeric:tabular-nums;line-height:1.05;margin-top:2px}}
    .lbl{{font-size:.7rem;letter-spacing:.09em;text-transform:uppercase;color:var(--slate);margin-top:6px;font-weight:700}}
    .sub{{font-size:.72rem;color:#b9cddb;margin-top:3px}}
    @media (prefers-reduced-motion:reduce){{.card:hover{{transform:none}}}}
    </style></head><body><div class="grid">{''.join(cards)}</div>
    <script>
    (function(){{
      const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      const fmt = n => n.toLocaleString('en-US');
      document.querySelectorAll('.val').forEach((el,i)=>{{
        const target = +el.dataset.v; if (reduce || target===0) {{ el.textContent = fmt(target); return; }}
        const dur = 900 + i*80, t0 = performance.now();
        const step = now => {{ const k = Math.min(1,(now-t0)/dur), e = 1-Math.pow(1-k,3); el.textContent = fmt(Math.round(target*e)); if (k<1) requestAnimationFrame(step); }};
        requestAnimationFrame(step);
      }});
    }})();
    </script></body></html>"""


def render_stats_strip(stats: Dict[str, Dict], height: int = 152) -> None:
    import streamlit.components.v1 as components
    components.html(stats_strip_html(stats), height=height, scrolling=False)


# --------------------------------------------------------------------------
# Ask IGNIS side panel
# --------------------------------------------------------------------------
SUGGESTED = [
    "How many observations are there in Uruguay?",
    "Compare MODIS and VIIRS detections.",
    "Show the historical evolution by year.",
    "What are the FRP values?",
]


def render_ask_panel(sample: pd.DataFrame, navigate: Optional[Callable] = None, full_page=None) -> None:
    """Compact, integrated Ask IGNIS. Reuses the rule-based engine unchanged."""
    from ignis_ask import responder_ignis
    st.markdown(
        '<div class="ig-ask-head"><div class="ig-ask-emblem" aria-hidden="true"></div>'
        '<div><b>Ask IGNIS</b><small>Rule-based analysis assistant · no generative AI · answers only from the loaded records</small></div></div>',
        unsafe_allow_html=True,
    )
    key = "ignis_dash_chat"
    st.session_state.setdefault(key, [])
    pending = st.session_state.pop("ignis_dash_pending", None)
    with st.form("ignis_dash_ask", clear_on_submit=True, border=False):
        q = st.text_input("Ask about the loaded FIRMS records", placeholder="Ask a question about the imported observations…",
                          label_visibility="collapsed")
        sent = st.form_submit_button("Ask", type="primary", use_container_width=True)
    if sent and q.strip():
        pending = q.strip()
    if pending:
        result = responder_ignis(sample if isinstance(sample, pd.DataFrame) else pd.DataFrame(), pending)
        st.session_state[key].append({"q": pending, "a": result["answer"], "chart": result.get("chart"), "sources": result.get("sources", [])})
        st.session_state[key] = st.session_state[key][-6:]
    st.markdown('<div class="ig-ask-sugg">', unsafe_allow_html=True)
    cols = st.columns(2)
    for i, s in enumerate(SUGGESTED):
        if cols[i % 2].button(s, key=f"ignis_dash_sugg_{i}", use_container_width=True):
            st.session_state["ignis_dash_pending"] = s
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    history = st.session_state[key]
    if not history:
        st.markdown('<p class="ig-note">Try a suggested question. Answers are computed with Pandas rules over the records you imported; '
                    'ASK IGNIS never invents statistics, verifications or external data.</p>', unsafe_allow_html=True)
    for m in reversed(history[-3:]):
        st.markdown(f'<div class="ig-msg u">{escape(m["q"])}</div>', unsafe_allow_html=True)
        src = (" · ".join(escape(s) for s in m["sources"])) if m.get("sources") else ""
        st.markdown(f'<div class="ig-msg a">{escape(m["a"])}{f"<small>Provenance: {src}</small>" if src else ""}</div>', unsafe_allow_html=True)
        chart = m.get("chart")
        if isinstance(chart, pd.DataFrame) and not chart.empty and len(chart) <= 60:
            if chart.shape[1] == 2:
                st.bar_chart(chart.set_index(chart.columns[0]), height=160, color="#FF6A1A")
            else:
                st.dataframe(chart, use_container_width=True, hide_index=True, height=160)
    c1, c2 = st.columns(2)
    if c1.button("Clear", key="ignis_dash_clear", use_container_width=True):
        st.session_state[key] = []
        st.rerun()
    if navigate is not None and full_page is not None:
        c2.button("Open full Ask IGNIS", key="ignis_dash_full", use_container_width=True, on_click=navigate, args=(full_page,))


# --------------------------------------------------------------------------
# Analytics
# --------------------------------------------------------------------------
def _layout(fig, height):
    fig.update_layout(height=height, margin=dict(l=12, r=12, t=28, b=30), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=PLOT_FONT, legend=dict(orientation="h", y=1.12, x=0, bgcolor="rgba(0,0,0,0)"),
                      hoverlabel=dict(bgcolor="#0b1f33", bordercolor="#2a5a74", font=dict(color="#f4faff")),
                      transition=dict(duration=450, easing="cubic-in-out"))
    fig.update_xaxes(gridcolor="rgba(125,235,255,.08)", zeroline=False, linecolor="rgba(125,235,255,.2)")
    fig.update_yaxes(gridcolor="rgba(125,235,255,.08)", zeroline=False)
    return fig


def _family_col(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.upper()
    return pd.Series(["MODIS" if "MODIS" in v else "VIIRS" if "VIIRS" in v else "Other" for v in s], index=series.index)


def render_analytics(sample: pd.DataFrame, selected: Optional[int], map_fn: Callable,
                     associations: Optional[pd.DataFrame], navigate: Optional[Callable], fusion_page) -> None:
    import plotly.graph_objects as go
    st.markdown('<div class="ig-section"><h3>Scientific analytics</h3><span>computed from the loaded records · thermal anomalies are not confirmed fires</span></div>', unsafe_allow_html=True)
    if sample is None or sample.empty:
        st.markdown('<div class="ig-empty"><b>No data to analyze yet</b>Import an IGNIS Master or NASA FIRMS ZIP/CSV files to populate the charts.</div>', unsafe_allow_html=True)
        return
    tabs = st.tabs(["Historical activity", "Spatial density", "Monthly calendar", "Sensor comparison", "Satellite–ground fusion"])
    fam = _family_col(sample["instrumento"])
    colors = {"MODIS": PALETTE["ember"], "VIIRS": PALETTE["orange"], "Other": PALETTE["slate"]}

    with tabs[0]:
        yearly = sample.groupby([sample["anio"], fam]).size().unstack(fill_value=0).sort_index()
        fig = go.Figure()
        for col in yearly.columns:
            fig.add_bar(x=yearly.index.astype(int), y=yearly[col], name=col, marker_color=colors.get(col, PALETTE["slate"]),
                        hovertemplate="%{x} · %{y:,} " + col + " observations<extra></extra>")
        if selected is not None and int(selected) in yearly.index:
            fig.add_vrect(x0=int(selected) - .5, x1=int(selected) + .5, fillcolor="rgba(0,217,245,.08)", line_width=1, line_color="rgba(0,217,245,.5)")
        fig.update_layout(barmode="stack", title=dict(text="FIRMS observations per year and instrument family", font=dict(size=13)))
        st.plotly_chart(_layout(fig, 330), use_container_width=True, key="ig_an_yearly")
        st.markdown('<p class="ig-note">Counts are not normalized by satellite coverage, revisits or sensor sensitivity. They are not a climate trend or a fire-incidence rate.</p>', unsafe_allow_html=True)

    with tabs[1]:
        view = sample[sample.anio == selected] if selected is not None else sample
        if view.empty:
            st.markdown('<div class="ig-empty"><b>No observations for the selected year</b>Pick another year in the sidebar; absence of records is not absence of fire.</div>', unsafe_allow_html=True)
        else:
            map_fn(view, "ig_an_density")

    with tabs[2]:
        cal = sample.groupby(["anio", "mes"]).size().unstack(fill_value=0).reindex(columns=range(1, 13), fill_value=0).sort_index()
        fig = go.Figure(go.Heatmap(z=cal.values, x=MONTHS, y=cal.index.astype(str), colorscale=[[0, "#0b1f33"], [.25, "#143a63"], [.55, "#c75a2a"], [1, "#ffd166"]],
                                   hovertemplate="%{y} · month %{x}<br>%{z:,} records<extra></extra>", colorbar=dict(title="Records", thickness=10)))
        fig.update_layout(title=dict(text="Monthly observation calendar", font=dict(size=13)), yaxis=dict(autorange="reversed"))
        st.plotly_chart(_layout(fig, max(300, 22 * len(cal) + 90)), use_container_width=True, key="ig_an_calendar")
        st.markdown('<p class="ig-note">Dark cells mean no imported records for that month, which does not prove the absence of thermal activity or complete satellite coverage.</p>', unsafe_allow_html=True)

    with tabs[3]:
        both = sample.assign(fam=fam)
        per = both.groupby(["anio", "fam"]).size().unstack(fill_value=0)
        coex = per[(per.get("MODIS", 0) > 0) & (per.get("VIIRS", 0) > 0)].index.tolist() if {"MODIS", "VIIRS"} <= set(per.columns) else []
        c1, c2, c3 = st.columns(3)
        c1.metric("MODIS observations", f"{int((fam == 'MODIS').sum()):,}")
        c2.metric("VIIRS observations", f"{int((fam == 'VIIRS').sum()):,}")
        c3.metric("Years with both families", str(len(coex)))
        fig = go.Figure()
        for col in [c for c in ("MODIS", "VIIRS") if c in per.columns]:
            fig.add_scatter(x=per.index.astype(int), y=per[col], mode="lines+markers", name=col, line=dict(color=colors[col], width=2.4), marker=dict(size=7))
        fig.update_layout(title=dict(text="Observations per instrument family (descriptive, not harmonized)", font=dict(size=13)))
        st.plotly_chart(_layout(fig, 300), use_container_width=True, key="ig_an_sensors")
        st.markdown('<p class="ig-note">MODIS (1 km) and VIIRS (375 m) have different sensitivity and overpass times; their counts must not be added as equivalent fires. '
                    'The exploratory cell-day coincidence method is documented in the MODIS–VIIRS Harmonization page.</p>', unsafe_allow_html=True)

    with tabs[4]:
        if isinstance(associations, pd.DataFrame) and not associations.empty:
            n_match = int((associations.get("n_firms", pd.Series(dtype=int)) > 0).sum())
            sim = associations.get("simulado", pd.Series(dtype=str)).astype(str).str.upper().str.startswith("YES").any()
            a1, a2 = st.columns(2)
            a1.metric("External events analyzed", f"{len(associations):,}")
            a2.metric("With nearby FIRMS observation", f"{n_match:,}")
            if sim:
                st.warning("Includes SIMULATED test records from the fusion tab. They are not evidence.")
            cols = [c for c in ("fecha_utc", "fuentes", "resultado", "n_firms", "distancia_km", "minutos") if c in associations.columns]
            st.dataframe(associations[cols].head(200), use_container_width=True, hide_index=True, height=260)
            st.markdown('<p class="ig-note">Spatial and temporal proximity for review; it does not confirm a fire or validate an institutional report.</p>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="ig-empty"><b>No satellite–ground associations yet</b>Upload Firefighters/PAIF or SINAE/MIRA records in the Satellite–Ground Fusion page; the associations will appear here and in the 3D scene.</div>', unsafe_allow_html=True)
            if navigate is not None and fusion_page is not None:
                st.button("Open Satellite–Ground Fusion", key="ig_an_fusion_btn", on_click=navigate, args=(fusion_page,))


# --------------------------------------------------------------------------
# Page
# --------------------------------------------------------------------------
def render_premium_dashboard(combined: pd.DataFrame, sample: pd.DataFrame, selected: Optional[int], base, map_fn: Callable,
                             pages, navigate: Callable, logo_uri: str = "", live: bool = False) -> None:
    """Control center: top bar · metric strip · 3D Uruguay (≈65%) + Ask IGNIS · analytics."""
    from ignis_scene3d import build_scene_payload, documented_cases
    associations = st.session_state.get("ignis_fusion_results")
    if not isinstance(associations, pd.DataFrame):
        associations = None
    has = isinstance(sample, pd.DataFrame) and not sample.empty
    payload_stats = build_scene_payload(sample if has else None, selected, associations)["stats"]
    render_topbar(logo_uri, selected, payload_stats, live=live)
    stats = dashboard_stats(combined, sample, selected, len(documented_cases()), len(associations) if associations is not None else 0)
    render_stats_strip(stats)

    left, right = st.columns([1.9, 1], gap="medium")
    with left:
        st.markdown('<div class="ig-section"><h3>Interactive 3D Uruguay</h3><span>drag to orbit · scroll to zoom · click a marker · Space plays the timeline</span></div>', unsafe_allow_html=True)
        if has:
            render_uruguay_scene(sample, selected, associations, height=700, live_connection=live)
        else:
            render_uruguay_scene(None, None, None, height=560, live_connection=False)
            st.markdown('<div class="ig-empty" style="margin-top:10px"><b>No observations loaded</b>The scene shows the national outline only. Import an IGNIS Master or NASA FIRMS ZIP/CSV files to display thermal observations.</div>', unsafe_allow_html=True)
            st.button("Go to Data upload", key="ig_dash_upload", type="primary", on_click=navigate, args=(pages[2],))
    with right:
        with st.container(border=True):
            render_ask_panel(sample if has else pd.DataFrame(), navigate, pages[12])
        with st.container(border=True):
            st.markdown("#### Quick access")
            q1, q2 = st.columns(2)
            q1.button("Uruguay Map", key="ig_dash_atlas", use_container_width=True, on_click=navigate, args=(pages[6],))
            q2.button("Harmonization", key="ig_dash_harm", use_container_width=True, on_click=navigate, args=(pages[5],))
            q1.button("Alerts & Traceability", key="ig_dash_alerts", use_container_width=True, on_click=navigate, args=(pages[7],))
            q2.button("PDF Report", key="ig_dash_pdf", use_container_width=True, on_click=navigate, args=(pages[9],))
            q1.button("3D Earth & Satellites", key="ig_dash_space", use_container_width=True, on_click=navigate, args=(pages[11],))
            q2.button("Sky–ground fusion", key="ig_dash_fusion", use_container_width=True, on_click=navigate, args=(pages[13],))
    render_analytics(sample if has else pd.DataFrame(), selected, map_fn, associations, navigate, pages[13])
    st.markdown('<p class="ig-note" style="margin-top:14px">IGNIS UY is a research platform, not an operational emergency service. The absence of records does not mean the absence of fires, '
                'nor does it confirm complete satellite coverage. Relief and orbits in the 3D scene are illustrative; every marker is an imported NASA FIRMS record.</p>', unsafe_allow_html=True)
