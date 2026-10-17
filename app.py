
"""
Horizon Shift — Walk Through Earth's Time and Under Other Suns
Enhanced version: Streamlit + Plotly + Three.js 3D scenes + optional Gemini AI.

Run:
    pip install -U streamlit plotly google-genai
    streamlit run app.py

Optional Gemini key:
    Set GEMINI_API_KEY in your environment, or add it to .streamlit/secrets.toml:
    GEMINI_API_KEY = "your-key-here"

Three.js and planet textures load from public CDNs, so the 3D scenes need internet.
The climate/habitability calculations are educational approximations, not scientific forecasts.
"""
from __future__ import annotations

import base64
import html
import json
import math
import os
import re
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

ASSETS = Path(__file__).parent / "assets"
THREE_CDN = "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"
TEXTURE_CDN = "https://cdn.jsdelivr.net/gh/mrdoob/three.js@r128/examples/textures/planets/"

st.set_page_config(
    page_title="NOVA | Mission Control",
    page_icon="✧",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# DATA
# ---------------------------------------------------------------------------
ERAS = [
    dict(key="dino", title="65 Million Years Ago", sub="Dinosaurs", file="era_dinosaurs",
         grad="linear-gradient(160deg,#3b5a2a,#a4562b 60%,#2a1a14)", emoji="🦖",
         tint="#b6e8a8", temp="≈ 25 °C (about +10 °C vs today)", co2="≈ 1,000 ppm",
         blurb="Greenhouse Earth: no polar ice caps, shallow inland seas and lush forests reaching the poles."),
    dict(key="ice", title="10,000 BCE", sub="Last Ice Age", file="era_iceage",
         grad="linear-gradient(160deg,#9fd4ff,#3d6fa8 60%,#0e1f3a)", emoji="🧊",
         tint="#e4f4ff", temp="≈ 9 °C (about −6 °C vs today)", co2="≈ 190–260 ppm",
         blurb="Ice sheets covered vast areas; sea level was roughly 120 metres lower than today."),
    dict(key="now", title="Present Day", sub="Modern Earth", file="era_present",
         grad="linear-gradient(160deg,#2b4a7a,#e0884a 70%,#1a1230)", emoji="🏙️",
         tint="#ffffff", temp="≈ 15 °C (baseline)", co2="≈ 420 ppm",
         blurb="Our current world: a warming climate, dense cities and an atmosphere changing quickly."),
    dict(key="fut", title="2100", sub="Hypothetical", file="era_future",
         grad="linear-gradient(160deg,#3b2a6e,#18a0c8 60%,#0a0f26)", emoji="🌆",
         tint="#ffd9b8", temp="≈ 16.5–19 °C (+1.5 to +4 °C)", co2="≈ 450–900 ppm",
         blurb="Future warming depends strongly on emissions and choices made in the coming decades."),
]
EXTRA_ERAS = [
    dict(key="snow", title="650 Million Years Ago", sub="Snowball Earth", file="era_snowball",
         grad="linear-gradient(160deg,#eaf6ff,#7fb2d9 60%,#14233d)", emoji="🥶",
         tint="#f2f9ff", temp="Far below freezing (hypothesis)", co2="Debated; built up before thaw",
         blurb="A hypothesised global glaciation in which ice may have reached the tropics."),
    dict(key="dying", title="252 Million Years Ago", sub="Great Dying", file="era_greatdying",
         grad="linear-gradient(160deg,#5a1d12,#d9531e 60%,#1a0d0a)", emoji="🌋",
         tint="#ffb28a", temp="≈ 30 °C+ (extreme hothouse)", co2="≈ 2,000+ ppm (estimates vary)",
         blurb="Massive volcanism contributed to warming, ocean stress and Earth's largest known mass extinction."),
    dict(key="medieval", title="1000 CE", sub="Medieval Climate Anomaly", file="era_medieval",
         grad="linear-gradient(160deg,#4a7a3a,#d8c27a 60%,#1a2410)", emoji="🏰",
         tint="#e8ffd9", temp="Regionally warm", co2="≈ 280 ppm",
         blurb="A regionally variable warm interval, especially around the North Atlantic, before industrialisation."),
    dict(key="far", title="2500", sub="Hypothetical Future", file="era_2500",
         grad="linear-gradient(160deg,#2a1a4a,#c8501e 60%,#0a0612)", emoji="🚀",
         tint="#ffb98c", temp="Highly scenario-dependent", co2="Depends on emissions path",
         blurb="Beyond 2100, outcomes depend on long-lived emissions, feedbacks and human choices."),
]
ALL_ERAS = ERAS + EXTRA_ERAS

STAR_TYPES = {
    "G-type (Sun-like)": {"lum": 1.0, "color": "#ffd27a"},
    "K-type (Orange dwarf)": {"lum": 0.40, "color": "#ffa04d"},
    "M-type (Red dwarf)": {"lum": 0.05, "color": "#ff6a4d"},
    "F-type (Yellow-white)": {"lum": 2.50, "color": "#fff2c0"},
    "A-type (White)": {"lum": 15.0, "color": "#d6e4ff"},
}
PLANETS = {
    "Terrestrial": {"albedo": 0.30, "ghe": 33, "atm": "O₂, CO₂, N₂", "glow": "#4aa3ff", "name": "Kepler-452b", "amp": 1.0},
    "Ocean World": {"albedo": 0.25, "ghe": 28, "atm": "N₂, O₂, H₂O", "glow": "#3b8bff", "name": "Kepler-22b", "amp": 0.5},
    "Desert World": {"albedo": 0.35, "ghe": 15, "atm": "CO₂, N₂, Ar", "glow": "#ff9a55", "name": "Gliese-667Cc", "amp": 2.4},
    "Ice World": {"albedo": 0.65, "ghe": 10, "atm": "N₂, CH₄", "glow": "#bfe6ff", "name": "TRAPPIST-1h", "amp": 0.8},
    "Gas Giant": {"albedo": 0.50, "ghe": 0, "atm": "H₂, He, CH₄", "glow": "#ffcf9a", "name": "HD-209458b", "amp": 0.3},
}
DEFAULT_SIM = {"ptype": "Terrestrial", "suns": 2, "star": "G-type (Sun-like)", "dist": 1.2, "tilt": 23}
SEED_CHAT = [
    {"role": "user", "text": "How does having two suns affect the planet's climate?"},
    {"role": "bot", "text": "Two suns can change the total energy reaching a planet and create complex light and seasonal patterns.\n- More total stellar energy can raise average temperatures.\n- The effect depends on each star's brightness and distance.\n- Stable orbits are not guaranteed in every two-star system.\n\nThis app uses a simplified educational model."},
]

# ---------------------------------------------------------------------------
# SIMULATION MODEL
# ---------------------------------------------------------------------------
def habitability(p: dict, t_c: float, day: float) -> tuple[int, str]:
    temp_s = math.exp(-((t_c - 15) / 20) ** 2)
    star_s = {"G-type (Sun-like)": 1.0, "K-type (Orange dwarf)": 0.95, "M-type (Red dwarf)": 0.55,
              "F-type (Yellow-white)": 0.8, "A-type (White)": 0.25}[p["star"]]
    tilt_s = 1.0 if p["tilt"] <= 40 else max(0.35, 1 - (p["tilt"] - 40) / 80)
    suns_s = 1 - 0.1 * (p["suns"] - 1)
    type_s = {"Terrestrial": 1.0, "Ocean World": 0.9, "Desert World": 0.5, "Ice World": 0.35, "Gas Giant": 0.02}[p["ptype"]]
    day_s = 1.0 if 10 <= day <= 40 else 0.7
    score = max(0, min(100, round(100 * temp_s * star_s * tilt_s * suns_s * type_s * day_s)))
    label = "Highly habitable" if score >= 70 else "Marginal" if score >= 40 else "Harsh" if score >= 15 else "Hostile"
    return score, label


def simulate(p: dict) -> dict:
    planet, star = PLANETS[p["ptype"]], STAR_TYPES[p["star"]]
    effective_suns = 1 + 0.5 * (p["suns"] - 1)
    flux = star["lum"] * effective_suns * (1 - planet["albedo"]) / 0.7
    t_eq = 255.0 * (flux ** 0.25) / math.sqrt(p["dist"])
    t_c = t_eq + planet["ghe"] - 273.15
    day = max(8.0, 24 + (p["dist"] - 1) * 10)
    hab, hab_label = habitability(p, t_c, day)
    return dict(temp=t_c, day=day, atm=planet["atm"], name=planet["name"],
                amp=5 + 0.25 * day * planet["amp"], hab=hab, hab_label=hab_label, **p)


def season_series(sim: dict):
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    amp = (sim["tilt"] / 23.5) * 6 * max(0.4, PLANETS[sim["ptype"]]["amp"])
    planet = [sim["temp"] + amp * math.sin(2 * math.pi * (m - 3) / 12) for m in range(12)]
    earth = [15 + 7 * math.sin(2 * math.pi * (m - 3) / 12) for m in range(12)]
    return months, planet, earth


def temp_series(sim: dict):
    hours = list(range(25))
    planet = [sim["temp"] + sim["amp"] * math.sin(2 * math.pi * (h - 9) / sim["day"]) for h in hours]
    earth = [15 + 6 * math.sin(2 * math.pi * (h - 9) / 24) for h in hours]
    return hours, planet, earth


def cur_era() -> dict:
    idx = int(st.session_state.get("era", 2))
    return ALL_ERAS[max(0, min(len(ALL_ERAS) - 1, idx))]


def build_report(sim: dict) -> str:
    era = cur_era()
    lines = ["# Horizon Shift — Simulation Report", "",
             f"Earth era selected: {era['title']} ({era['sub']})",
             f"- Avg. temperature: {era['temp']}", f"- CO₂: {era['co2']}", f"- {era['blurb']}", "",
             f"## Planet: {sim['name']} ({sim['ptype']})", "",
             f"- Suns: {sim['suns']} × {sim['star']}", f"- Orbital distance: {sim['dist']} AU",
             f"- Axial tilt: {sim['tilt']}°", f"- Average surface temperature: {sim['temp']:.1f} °C",
             f"- Day length: {sim['day']:.0f} hours", f"- Atmosphere: {sim['atm']}",
             f"- Habitability: {sim['hab']}/100 ({sim['hab_label']})", ""]
    if st.session_state.runs:
        lines += ["## Saved runs", "", "| # | Type | Suns | Star | AU | Tilt | Temp °C | Habitability |",
                  "|---|---|---|---|---|---|---|---|"]
        for i, r in enumerate(st.session_state.runs, 1):
            lines.append(f"| {i} | {r['ptype']} | {r['suns']} | {r['star']} | {r['dist']} | {r['tilt']} | {r['temp']:.1f} | {r['hab']} |")
        lines.append("")
    if st.session_state.chat:
        lines += ["## AI Science Guide conversation", ""]
        for m in st.session_state.chat:
            lines.append(("You: " if m["role"] == "user" else "Guide: ") + m["text"].replace("\n", " "))
        lines.append("")
    lines.append("Educational approximation: equilibrium temperature plus a simplified greenhouse offset.")
    return "\n".join(lines)


def sun_label(n: int) -> str:
    return {1: "One Sun", 2: "Two Suns", 3: "Three Suns"}[n] + " Simulation"


# ---------------------------------------------------------------------------
# GEMINI
# ---------------------------------------------------------------------------
def _api_key():
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        try:
            key = st.secrets.get("GEMINI_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
        except Exception:
            key = None
    return key


def ask_gemini(question: str, sim: dict, era: dict) -> str:
    key = _api_key()
    context = (f"Current simulation: {sim['ptype']} planet '{sim['name']}', {sim['suns']} sun(s) of "
               f"{sim['star']}, orbital distance {sim['dist']} AU, axial tilt {sim['tilt']}°, "
               f"average surface temperature {sim['temp']:.1f} °C, day length {sim['day']:.0f} h, "
               f"atmosphere {sim['atm']}, habitability score {sim['hab']}/100 ({sim['hab_label']}). "
               f"Selected Earth era: {era['title']} ({era['sub']}).")
    if not key:
        return ("**Offline mode:** Add `GEMINI_API_KEY` to enable live answers.\n\n"
                f"For the current setup ({sim['suns']} sun(s), {sim['dist']} AU, tilt {sim['tilt']}°), "
                f"the simplified model estimates about {sim['temp']:.1f} °C. More incoming stellar energy "
                "usually raises temperature; a wider orbit generally reduces it. This is an educational model.")
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            contents=question,
            config=types.GenerateContentConfig(
                system_instruction=(
                    "You are Horizon Shift's concise, accurate science guide about Earth's climate history "
                    "and exoplanets. Answer in under 130 words, explain uncertainty, avoid presenting the app's "
                    "simplified simulation as a validated scientific prediction. Use short bullets when useful. "
                    + context
                ),
                temperature=0.5,
            ),
        )
        return (response.text or "").strip() or "I couldn't generate an answer. Please try again."
    except Exception as exc:
        return f"Gemini request failed: {exc}. Check the API key, network connection, and installed `google-genai` package."


def md_to_html(text: str) -> str:
    out, in_list = [], False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith(("- ", "* ")):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append("<li>" + html.escape(s[2:]) + "</li>")
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
            if s:
                safe = html.escape(s)
                safe = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", safe)
                out.append("<p>" + safe + "</p>")
    if in_list:
        out.append("</ul>")
    return "".join(out)


# ---------------------------------------------------------------------------
# STATE
# ---------------------------------------------------------------------------
ss = st.session_state
ss.setdefault("page", "Home")
ss.setdefault("era", 2)
ss.setdefault("sim", dict(DEFAULT_SIM))
ss.setdefault("chat", list(SEED_CHAT))
ss.setdefault("runs", [])

# ---------------------------------------------------------------------------
# CSS — existing dark space aesthetic retained, with extra depth and polish
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html,body,[class*="css"],.stApp{font-family:Inter,sans-serif}
.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"],.main{background:transparent!important;color:#e8edff}
#MainMenu,header,footer,[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important}
.block-container{padding:.6rem 1.2rem .4rem!important;max-width:1600px}
[data-testid="stVerticalBlock"]{gap:.55rem}
[class*="st-key-panel_"]{background:linear-gradient(145deg,rgba(12,22,52,.82),rgba(5,11,28,.72));border:1px solid #26396f;border-radius:14px;padding:13px 14px;backdrop-filter:blur(16px);box-shadow:0 14px 38px #0005,inset 0 1px #ffffff0c;transition:.25s}
[class*="st-key-panel_"]:hover{border-color:#536cff;box-shadow:0 14px 40px #273ed833,inset 0 1px #ffffff14}
.hdr{display:flex;align-items:center;justify-content:space-between;padding:2px 0 7px}
.brand{display:flex;align-items:center;gap:10px}.brand h1{margin:0;font-size:24px;font-weight:800;color:#fff;line-height:1.1}
.brand h1 span,.grad{background:linear-gradient(90deg,#6d7bff,#bf63ff,#58caff);background-size:200% 100%;animation:shine 6s linear infinite;-webkit-background-clip:text;color:transparent}
.brand small{color:#9fb0e6;font-size:10.5px}.brand svg{filter:drop-shadow(0 0 9px #7b8cff88);animation:floaty 4s ease-in-out infinite}
.badges{display:flex;border:1px solid #223263;border-radius:9px;background:#0a153499;overflow:hidden;backdrop-filter:blur(10px)}
.badges div{padding:7px 12px;font-size:11px;color:#cfd8ff}.badges div+div{border-left:1px solid #223263}
.panel-h{display:flex;gap:10px;align-items:center;margin-bottom:7px}.panel-h .ic{width:32px;height:32px;border-radius:10px;background:linear-gradient(145deg,#1c3470,#101b40);display:flex;align-items:center;justify-content:center;font-size:16px;box-shadow:0 0 16px #526dff22}
.panel-h b{font-size:13px;color:#fff;display:block}.panel-h i{font-style:normal;font-size:10px;color:#8fa2d8}
.stButton>button{width:100%;border-radius:9px;border:1px solid #26396c;background:#0a153880;color:#d5ddff;font-size:12px;font-weight:500;padding:.4rem .6rem;min-height:0;transition:all .22s}
.stButton>button:hover{border-color:#7184ff;color:#fff;background:#172a59;box-shadow:0 0 16px #526dff35;transform:translateY(-1px)}
.stButton>button[kind="primary"],.stFormSubmitButton>button{background:linear-gradient(100deg,#3657e8,#7652ee);border:0;color:#fff;font-weight:700}
.st-key-navbox .stButton>button{border-color:transparent;background:transparent;padding:.58rem .7rem;text-align:left}
.st-key-navbox .stButton>button[kind="primary"]{background:linear-gradient(100deg,#2f56d9,#4a6cf2);box-shadow:0 6px 18px #3459e644}
.st-key-runsim .stButton>button{justify-content:center;padding:.55rem}
.stFormSubmitButton>button{width:42px;min-width:42px;justify-content:center}
.stDownloadButton>button{width:100%;border-radius:9px;border:1px solid #2b3f86;background:#0c1738;color:#cfd8ff;font-size:12px;padding:.48rem;justify-content:center}
label,.stSlider label,.stSelectbox label{font-size:10.5px!important;color:#aab8e8!important}
[data-baseweb="select"]>div,.stTextInput input{background:#0c1738!important;border-color:#26396c!important;font-size:12px;min-height:34px;color:#fff!important}
.stTabs [data-baseweb="tab-list"]{gap:7px}.stTabs [data-baseweb="tab"]{font-size:11px;height:30px;padding:0 10px}
.era{position:relative;height:84px;border-radius:9px;overflow:hidden;border:1px solid #26396c;background-size:cover;background-position:center;transition:transform .25s,box-shadow .25s,border-color .25s;box-shadow:inset 0 -35px 30px #0005}
.era.sel{border:2px solid #56a8ff;box-shadow:0 0 18px #2a7cff77, inset 0 -35px 30px #0005}
.era .cap{position:absolute;left:0;right:0;bottom:0;padding:16px 7px 5px;font-size:10px;color:#fff;line-height:1.15;background:linear-gradient(transparent,#000d)}
.era .em{position:absolute;top:7px;left:8px;font-size:23px;filter:drop-shadow(0 2px 6px #0008)}
[class*="st-key-eracard"]:hover .era{transform:perspective(600px) rotateX(4deg) translateY(-3px) scale(1.025);border-color:#7184ff}
.eradet{font-size:11px;color:#b4c2f0;background:#0b1634;border:1px solid #26396c;border-radius:8px;padding:8px 10px;line-height:1.5}.eradet b{color:#fff}
.met{display:flex;gap:8px;flex-wrap:wrap}.met>div{flex:1;min-width:130px;background:linear-gradient(145deg,#101e43,#09132c);border:1px solid #26396c;border-radius:9px;padding:8px 10px;display:flex;gap:9px;align-items:center;transition:.22s}
.met>div:hover{transform:translateY(-2px);border-color:#526dff;box-shadow:0 8px 20px #1e3c9e2b}.met .ico{font-size:20px}.met small{display:block;font-size:9px;color:#8fa2d8}.met b{font-size:13px;color:#fff;font-weight:700}
.bar{height:4px;border-radius:3px;background:#14234f;margin-top:4px;overflow:hidden}.bar i{display:block;height:100%;border-radius:3px}
.chat{display:flex;flex-direction:column;gap:10px;padding:4px 2px}.u{align-self:flex-end;background:linear-gradient(120deg,#2f6bf5,#7652ee);color:#fff;padding:8px 11px;border-radius:12px 12px 3px 12px;font-size:11px;max-width:85%;box-shadow:0 5px 14px #0002}
.b{display:flex;gap:8px;align-items:flex-start}.b .av{width:29px;height:29px;min-width:29px;border-radius:50%;background:#13244f;border:1px solid #2a3c78;display:flex;align-items:center;justify-content:center;font-size:15px}.b .msg{background:#122046;border:1px solid #1e2f62;border-radius:4px 12px 12px 12px;padding:9px 11px;font-size:11px;color:#d6defa;line-height:1.5}.b .msg p{margin:0 0 6px}.b .msg ul{margin:0 0 6px;padding-left:17px}.b .msg em{display:block;font-style:normal;font-size:9px;color:#8193cc;margin-top:5px}
.qf{display:flex;align-items:center;gap:10px;padding:7px 0;border-bottom:1px solid #15244d;font-size:10.5px;color:#b4c2f0}.qf:last-child{border:0}.qf span:nth-child(2){flex:1}.qf b{color:#fff;font-weight:600}
.quote{font-style:italic;color:#a9b8ea;font-size:11px;line-height:1.6;margin-top:28px}.galaxy{height:90px;border-radius:50%;margin-top:8px;opacity:.9;background:radial-gradient(ellipse 45% 14% at 50% 50%,#ffe9c0 0%,#7a8cff 40%,transparent 75%),radial-gradient(circle at 50% 50%,#3a2a7a55,transparent 70%);transform:rotate(-30deg)}
.foot{text-align:center;font-size:9.5px;color:#7587c0;padding:7px 0;border-top:1px solid #101c3f;margin-top:5px}
.dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:#38d39f;margin-right:5px;box-shadow:0 0 9px #38d39f99;animation:pulse 1.8s infinite}
@keyframes shine{to{background-position:200% 50%}}@keyframes floaty{50%{transform:translateY(-3px)}}@keyframes pulse{70%{box-shadow:0 0 0 6px #38d39f00}}
::-webkit-scrollbar{width:6px}::-webkit-scrollbar-thumb{background:#243670;border-radius:3px}
@media(max-width:900px){.hdr{align-items:flex-start;gap:8px;flex-wrap:wrap}.brand h1{font-size:21px}.badges div{padding:6px 8px}.era{height:76px}}

/* Reference-matched Horizon Shift cockpit: midnight space, cyan + mint accents */
:root{--hs-bg:#030711;--hs-panel:#07101d;--hs-line:#1c2d46;--hs-muted:#94a6c0;--hs-mint:#b9f4d6;--hs-cyan:#a6edff}
.stApp{background:radial-gradient(ellipse at 60% 12%,rgba(30,52,78,.48),transparent 35%),radial-gradient(ellipse at 90% 60%,rgba(8,39,55,.28),transparent 32%),linear-gradient(130deg,#02050b,#050b16 58%,#02060d) fixed!important;color:#f3f7ff}
.block-container{max-width:1900px;padding:.5rem .8rem .45rem!important}
[class*="st-key-panel_"]{background:linear-gradient(145deg,rgba(10,20,34,.94),rgba(4,9,17,.94));border:1px solid #ffffff20;border-radius:15px;box-shadow:0 14px 38px #0005,inset 0 1px #ffffff08;backdrop-filter:blur(15px)}
[class*="st-key-panel_"]:hover{border-color:#79c7dc66;box-shadow:0 14px 40px #153a4d55,inset 0 1px #ffffff12}
.hdr.reference-hdr{display:grid;grid-template-columns:1fr auto 1fr;gap:12px;align-items:center;padding:5px 10px 9px;margin-bottom:5px;border-bottom:1px solid #ffffff10}
.reference-hdr .brand h1{font-size:13px;font-weight:500;letter-spacing:.26em;color:#f3f7ff;white-space:nowrap}
.reference-hdr .brand svg{width:35px;height:35px;filter:grayscale(1) brightness(1.8);animation:none}
.reference-hdr .brand small{display:none}
.topnav{display:flex;gap:2px;padding:4px;border:1px solid #ffffff18;border-radius:26px;background:#07101bbd;white-space:nowrap}
.topnav-item{font-size:9px;color:#afbdd0;padding:8px 12px;border-radius:22px}
.topnav-item.active{background:linear-gradient(120deg,#1c3a59,#0b1d30);color:#fff;box-shadow:inset 0 0 0 1px #7acbff30}
.reference-hdr .badges{border:0;background:transparent;gap:5px;overflow:visible}
.reference-hdr .badges div{width:34px;height:34px;padding:0;display:grid;place-items:center;border:1px solid #ffffff1b;border-radius:50%;background:#07101d;color:#dce9f6;font-size:12px}
.panel-h .ic{background:linear-gradient(145deg,#12314b,#0a1828);border:1px solid #2b5870;box-shadow:0 0 16px #3dc4e822}
.panel-h b{font-size:12px}.panel-h i{color:#9baec3}
.stButton>button{border-color:#ffffff20;background:linear-gradient(145deg,#101c2b,#060d17);color:#dce6f3;border-radius:9px;font-size:10px}
.stButton>button:hover{border-color:#9de8ff;color:white;background:#14283a;box-shadow:0 0 16px #42c7e522}
.stButton>button[kind="primary"],.stFormSubmitButton>button{background:linear-gradient(100deg,#f4f8ff,#b9eaff);color:#091522;border:0;font-weight:700}
.st-key-navbox .stButton>button{border-color:transparent;background:transparent;padding:.65rem .55rem;text-align:left;color:#c4d1e1}
.st-key-navbox .stButton>button[kind="primary"]{background:linear-gradient(100deg,#164b86,#0b2447);border:1px solid #4c8bda55;box-shadow:0 6px 18px #1261ba22;color:#fff}
[data-baseweb="select"]>div,.stTextInput input{background:#07111e!important;border-color:#ffffff20!important;color:#f1f4f8!important}
label,.stSlider label,.stSelectbox label{color:#aab9cc!important}
.era{border-color:#ffffff26;box-shadow:inset 0 -35px 30px #0006}.era.sel{border:2px solid #68d8bd;box-shadow:0 0 18px #2acbba44,inset 0 -35px 30px #0005}
.eradet{background:#091827;border-color:#254057;color:#bdccdc}.met>div{background:linear-gradient(145deg,#0d1e2c,#07111d);border-color:#223b4b}.met small{color:#9aafc2}.bar{background:#1a2d3d}
.chat .u{background:linear-gradient(120deg,#174c85,#10305a);box-shadow:none}.b .msg{background:#0b1727;border-color:#ffffff17;color:#dbe5f1}.b .av{background:#0b2236;border-color:#25516b}
.qf{border-bottom-color:#ffffff12;color:#b8c8da}.qf b{color:#f4f7fb}.foot{border-top-color:#ffffff12;color:#71869f}
.dot{background:#42e0ad;box-shadow:0 0 9px #38d39f99}
@media(max-width:1050px){.hdr.reference-hdr{grid-template-columns:1fr auto}.topnav{grid-column:1/-1;grid-row:2;justify-content:center;flex-wrap:wrap}.reference-hdr .badges{grid-column:2;grid-row:1}.topnav-item{padding:7px 8px;font-size:8px}}


/* NOVA cockpit styling override — based on the user's supplied reference */
.stApp{background:radial-gradient(ellipse at 68% 10%,rgba(85,112,133,.18),transparent 38%),radial-gradient(ellipse at 95% 70%,rgba(17,50,67,.18),transparent 34%),linear-gradient(145deg,#02050a,#050b13 62%,#02050a) fixed!important}
.block-container{max-width:1900px;padding:.5rem .75rem .5rem!important}
.hdr.reference-hdr{border:1px solid #ffffff1c;border-radius:24px;background:linear-gradient(110deg,#05080de8,#0b1420dc);padding:7px 13px;margin:0 0 10px;box-shadow:0 14px 40px #0005}
.reference-hdr .brand h1{font-size:14px;letter-spacing:.42em;font-weight:500}
.reference-hdr .brand svg{filter:grayscale(1) brightness(2);width:36px;height:36px}
.topnav{background:#0a111bbf;border-color:#ffffff1b}
.topnav-item.active{background:linear-gradient(120deg,#1a2a3a,#0c1724);box-shadow:inset 0 0 0 1px #d0e7f51f}
[class*="st-key-panel_"]{background:linear-gradient(145deg,rgba(8,16,27,.96),rgba(3,8,14,.97));border:1px solid #ffffff22;border-radius:17px;box-shadow:0 12px 32px #0005,inset 0 1px #ffffff08}
.panel-h .ic{background:linear-gradient(145deg,#122330,#08131c);border-color:#29414c;box-shadow:0 0 15px #a6edff0b}
.stButton>button{background:linear-gradient(145deg,#101820,#060b11);border-color:#ffffff24;color:#e2e9ef}
.stButton>button:hover{background:#13222c;border-color:#a6edff;color:#fff;box-shadow:0 0 14px #a6edff18}
.stButton>button[kind="primary"],.stFormSubmitButton>button{background:linear-gradient(100deg,#f5f8fb,#c9e8f2);color:#071018}
.st-key-navbox .stButton>button[kind="primary"]{background:linear-gradient(100deg,#1b4d7d,#0c2a46);border-color:#4e819e66}
.era.sel{border-color:#b9f4d6;box-shadow:0 0 16px #b9f4d622,inset 0 -35px 30px #0005}
.met>div{background:linear-gradient(145deg,#0d1b25,#071019);border-color:#203642}
.qf{border-bottom-color:#ffffff13;color:#b8c8d4}.qf b{color:#f3f7fb}
@media(max-width:900px){.reference-hdr .brand h1{font-size:11px;letter-spacing:.25em}.topnav-item{padding:6px 7px}.cd{min-width:100px}}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# THREE.JS SCENES — animated starfield, rotating planet, atmospheric glow,
# cloud shell, orbiting moon/suns, drag-to-rotate and interactive controls.
# ---------------------------------------------------------------------------
COMMON_JS = r"""
const cv=document.getElementById('c');
const renderer=new THREE.WebGLRenderer({canvas:cv,antialias:true,alpha:true});
renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,2));
renderer.setClearColor(0x000000,0);
const scene=new THREE.Scene();
const camera=new THREE.PerspectiveCamera(42,1,0.1,200);
function resize(){const w=Math.max(1,cv.clientWidth),h=Math.max(1,cv.clientHeight);renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();}
new ResizeObserver(resize).observe(cv);
(function(){const g=new THREE.BufferGeometry(),p=[];for(let i=0;i<1700;i++){const r=55,t=Math.random()*Math.PI*2,f=Math.acos(2*Math.random()-1);p.push(r*Math.sin(f)*Math.cos(t),r*Math.sin(f)*Math.sin(t),r*Math.cos(f));}g.setAttribute('position',new THREE.Float32BufferAttribute(p,3));scene.add(new THREE.Points(g,new THREE.PointsMaterial({color:0xffffff,size:.14,transparent:true,opacity:.82})));})();
function loadTex(name,ok,fail){const urls=["__TEXTURE_CDN__"+name];let i=0;(function next(){if(i>=urls.length){if(fail)fail();return;}new THREE.TextureLoader().load(urls[i++],ok,undefined,next);})();}
function glowTex(color){const c=document.createElement('canvas');c.width=c.height=128;const x=c.getContext('2d'),g=x.createRadialGradient(64,64,0,64,64,64);g.addColorStop(0,'#fff');g.addColorStop(.15,color);g.addColorStop(.42,color+'55');g.addColorStop(1,color+'00');x.fillStyle=g;x.fillRect(0,0,128,128);return new THREE.CanvasTexture(c);}
function atmosphere(r,color){const m=new THREE.MeshBasicMaterial({color:color,transparent:true,opacity:.12,side:THREE.BackSide,blending:THREE.AdditiveBlending,depthWrite:false});return new THREE.Mesh(new THREE.SphereGeometry(r,64,64),m);}
function makeStars(){const group=new THREE.Group();for(let i=0;i<CFG.suns;i++){const col=new THREE.Color(CFG.sunColors[i]||CFG.sunColor||'#ffd27a');const sprite=new THREE.Sprite(new THREE.SpriteMaterial({map:glowTex(CFG.sunColors[i]||CFG.sunColor||'#ffd27a'),blending:THREE.AdditiveBlending,transparent:true,depthWrite:false}));sprite.scale.set(1.2,1.2,1);group.add(sprite);}return group;}
"""
BOOT_JS = r"""
const CFG=__CFG__;
const TEXTURE_CDN='https://cdn.jsdelivr.net/gh/mrdoob/three.js@r128/examples/textures/planets/';
(function boot(){const s=document.createElement('script');s.src='__THREE__';s.onload=()=>{if(typeof THREE!=='undefined')main();else fail();};s.onerror=fail;function fail(){document.getElementById('err').style.display='block';}document.head.appendChild(s);})();
"""

SIM_HTML = r"""<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;width:100%;height:100%;overflow:hidden;background:transparent;font-family:Inter,Arial}
#c{width:100%;height:100%;display:block;cursor:grab;border-radius:12px}
#pill{position:absolute;top:9px;right:10px;background:#0a142ddd;border:1px solid #2a3a6a;border-radius:14px;padding:5px 10px;color:#dbe3ff;font-size:10px;backdrop-filter:blur(8px)}
#ctl{position:absolute;left:9px;bottom:9px;display:flex;gap:5px}
#ctl button{width:29px;height:29px;border-radius:9px;border:1px solid #2a3a6a;background:#0a142ddd;color:#dbe3ff;font-size:13px;cursor:pointer}
#ctl button:hover{border-color:#7184ff;box-shadow:0 0 12px #4b6fff88}#ctl button.off{opacity:.42}
#hint{position:absolute;right:10px;bottom:12px;font-size:9px;color:#9aabe0;pointer-events:none}
#err{display:none;position:absolute;inset:0;color:#b9c6f4;font-size:12px;padding:20px;text-align:center;background:#060b1a}
</style></head><body><canvas id="c"></canvas><div id="pill"></div>
<div id="ctl"><button id="bSpin" title="Pause/resume rotation">Ⅱ</button><button id="bCld" title="Toggle clouds">☁</button><button id="bOrb" title="Pause orbit">☀</button><button id="bRst" title="Reset view">⟲</button></div><div id="hint">drag to rotate · interactive 3D</div><div id="err">The 3D engine could not load. Check your internet connection and refresh.</div>
<script>
__BOOT__
function main(){
document.getElementById('pill').textContent=CFG.label;
__COMMON__
camera.position.set(0,0,6.6);resize();
scene.add(new THREE.AmbientLight(0x4b639c,.72));
const keyLight=new THREE.DirectionalLight(0xffedcf,2.0);keyLight.position.set(5,3,5);scene.add(keyLight);
const planet=new THREE.Group();scene.add(planet);
const R=1.55;let body,clouds=null;
if(CFG.gas){const cv2=document.createElement('canvas');cv2.width=512;cv2.height=256;const cx=cv2.getContext('2d');const colors=['#d9a066','#b9783f','#f0d2a0','#9c5f32','#e6bd86','#c98a52'];for(let y=0;y<256;y+=7){cx.fillStyle=colors[Math.floor(Math.random()*colors.length)];cx.fillRect(0,y,512,7);}body=new THREE.Mesh(new THREE.SphereGeometry(R,96,96),new THREE.MeshPhongMaterial({map:new THREE.CanvasTexture(cv2),shininess:8}));}
else{body=new THREE.Mesh(new THREE.SphereGeometry(R,96,96),new THREE.MeshPhongMaterial({color:CFG.tint,shininess:45,specular:0x345577}));loadTex('earth_atmos_2048.jpg',t=>{body.material.map=t;body.material.color.set(CFG.tint);body.material.needsUpdate=true;},()=>{});}
planet.add(body);const atm=atmosphere(R*1.12,CFG.glow);planet.add(atm);
if(CFG.clouds>0&&!CFG.gas){clouds=new THREE.Mesh(new THREE.SphereGeometry(R*1.018,64,64),new THREE.MeshPhongMaterial({color:0xdceeff,transparent:true,opacity:.18,depthWrite:false}));loadTex('earth_clouds_1024.png',t=>{clouds.material.map=t;clouds.material.opacity=.58;clouds.material.needsUpdate=true;},()=>{});planet.add(clouds);}
planet.rotation.z=CFG.tilt*Math.PI/180*.45;
const sunGroup=new THREE.Group();scene.add(sunGroup);const suns=[];
for(let i=0;i<CFG.suns;i++){const color=(CFG.sunColors&&CFG.sunColors[i])||CFG.sunColor||'#ffd27a';const sprite=new THREE.Sprite(new THREE.SpriteMaterial({map:glowTex(color),blending:THREE.AdditiveBlending,depthWrite:false}));sprite.scale.set(1.5,1.5,1);scene.add(sprite);const light=new THREE.PointLight(color,1.7/Math.sqrt(CFG.suns),30);scene.add(light);suns.push({sprite,light,a:i*2*Math.PI/CFG.suns});}
let moon=null,ma=1.2;if(!CFG.gas){moon=new THREE.Mesh(new THREE.SphereGeometry(.22,40,40),new THREE.MeshPhongMaterial({color:0xc7c7c7,shininess:4}));loadTex('moon_1024.jpg',t=>{moon.material.map=t;moon.material.needsUpdate=true;},()=>{});scene.add(moon);}
let dragging=false,lastX=0,lastY=0,spin=true,orbit=true,rotX=0;
cv.addEventListener('pointerdown',e=>{dragging=true;lastX=e.clientX;lastY=e.clientY;cv.setPointerCapture(e.pointerId);cv.style.cursor='grabbing';});
cv.addEventListener('pointerup',()=>{dragging=false;cv.style.cursor='grab';});
cv.addEventListener('pointermove',e=>{if(dragging){body.rotation.y+=(e.clientX-lastX)*.009;rotX+=(e.clientY-lastY)*.006;body.rotation.x=Math.max(-.8,Math.min(.8,rotX));lastX=e.clientX;lastY=e.clientY;}});
function toggle(id,fn){const b=document.getElementById(id);b.onclick=()=>{b.classList.toggle('off');fn(!b.classList.contains('off'));};}
toggle('bSpin',v=>spin=v);toggle('bOrb',v=>orbit=v);toggle('bCld',v=>{if(clouds)clouds.visible=v;});
document.getElementById('bRst').onclick=()=>{body.rotation.set(0,0,0);rotX=0;};
const orbitLines=[];for(let i=0;i<CFG.suns;i++){const curve=new THREE.EllipseCurve(0,0,2.6+i*.35,1.15+i*.2,0,Math.PI*2,false,0);const pts=curve.getPoints(100).map(p=>new THREE.Vector3(p.x,p.y,-.2));const geo=new THREE.BufferGeometry().setFromPoints(pts);const line=new THREE.LineLoop(geo,new THREE.LineBasicMaterial({color:CFG.sunColor||'#ffd27a',transparent:true,opacity:.18}));scene.add(line);orbitLines.push(line);}
let t=0;
function loop(){requestAnimationFrame(loop);t+=.01;if(spin&&!dragging)body.rotation.y+=.0017;if(clouds)clouds.rotation.y=body.rotation.y*1.08+.25;
suns.forEach((s,i)=>{if(orbit)s.a+=.003;const radius=2.6+i*.35;s.sprite.position.set(Math.cos(s.a)*radius,Math.sin(s.a)*1.15,Math.sin(s.a)*.7);s.light.position.copy(s.sprite.position);});
if(moon){if(orbit)ma+=.008;moon.position.set(Math.cos(ma)*2.05,Math.sin(ma)*.7,Math.sin(ma)*2.05);}
atm.rotation.y=-body.rotation.y*.2;renderer.render(scene,camera);}
loop();
}
</script></body></html>"""

HERO_HTML = r"""<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#03070d;font-family:Inter,Arial;border-radius:12px}
#bg{position:absolute;inset:0;background:radial-gradient(ellipse at 76% 40%,#26384a 0,transparent 38%),radial-gradient(ellipse at 30% 90%,#122332 0,transparent 40%),linear-gradient(130deg,#03070c,#08131f 65%,#050910)}
#c{position:absolute;inset:0;width:100%;height:100%;z-index:1;cursor:grab}
.txt{position:absolute;left:20px;top:16px;color:#fff;max-width:58%;z-index:2;pointer-events:none}
.txt small{font-size:12px;color:#dfe6ff}.txt h1{margin:0;font-size:clamp(29px,3.1vw,48px);font-weight:300;line-height:1.08;letter-spacing:-.035em;text-shadow:0 2px 20px #0009}
.txt h1 span{background:linear-gradient(90deg,#d8f6e4,#a6edff,#d8f6e4);background-size:200% 100%;-webkit-background-clip:text;color:transparent;animation:shine 5s linear infinite}
.txt p{margin:8px 0 0;font-size:11px;color:#d3dcff;line-height:1.5}
.cards{position:absolute;left:12px;bottom:10px;display:flex;gap:8px;z-index:2;flex-wrap:wrap}
.cd{display:flex;gap:8px;align-items:center;min-width:125px;background:#07111dcc;border:1px solid #ffffff20;border-radius:9px;padding:8px 10px;color:#fff;backdrop-filter:blur(8px);transition:.22s}
.cd:hover{border-color:#7b8cff;transform:translateY(-3px);box-shadow:0 8px 20px #3c5aff44}
.cd .i{min-width:28px;height:28px;border-radius:50%;background:#0d2534;border:1px solid #2d5a66;display:flex;align-items:center;justify-content:center;font-size:14px}
.cd b{font-size:10px;display:block}.cd span{font-size:8.5px;color:#a9b8ea;line-height:1.3;display:block}
#err{display:none;position:absolute;right:10px;top:10px;color:#b9c6f4;font-size:10px;z-index:3}
@keyframes shine{to{background-position:200% 50%}}
</style></head><body><div id="bg"></div><canvas id="c"></canvas><div id="err">3D unavailable — check internet.</div>
<div class="txt"><small>● SYSTEM STATUS &nbsp; <span style="color:#5ee5b2">NOMINAL</span></small><h1>EXPLORE.<br>DISCOVER.<br><span>ENDURE.</span></h1><p>Navigate the unknown, catalog new worlds,<br>and expand the boundaries of human presence.</p></div>
<div class="cards"><div class="cd"><div class="i">⌘</div><div><b>NSS VOYAGER</b><span>● READY<br>Fleet status · 82%</span></div></div><div class="cd"><div class="i">🌘</div><div><b>KEPLER-186F</b><span>Next mission<br>ETA 2D 14H</span></div></div><div class="cd"><div class="i">◎</div><div><b>SYSTEM SCAN</b><span>7 signals detected<br>Live telemetry</span></div></div></div>
<script>
__BOOT__
function main(){
__COMMON__
camera.position.set(0,0,8.6);resize();scene.add(new THREE.AmbientLight(0x52689c,.7));
const sun=new THREE.DirectionalLight(0xffedcf,2.2);sun.position.set(8,5,6);scene.add(sun);
const earth=new THREE.Group();earth.position.set(2.55,-2.7,0);scene.add(earth);
const globe=new THREE.Mesh(new THREE.SphereGeometry(3.6,128,128),new THREE.MeshPhongMaterial({color:CFG.tint,shininess:55,specular:0x345577}));
loadTex('earth_atmos_2048.jpg',t=>{globe.material.map=t;globe.material.color.set(CFG.tint);globe.material.needsUpdate=true;},()=>{});
earth.add(globe);const atm=atmosphere(3.83,'#398bff');earth.add(atm);
const cloud=new THREE.Mesh(new THREE.SphereGeometry(3.65,96,96),new THREE.MeshPhongMaterial({color:0xeaf5ff,transparent:true,opacity:.2,depthWrite:false}));
loadTex('earth_clouds_1024.png',t=>{cloud.material.map=t;cloud.material.opacity=.5;cloud.material.needsUpdate=true;},()=>{});earth.add(cloud);
const moon=new THREE.Mesh(new THREE.SphereGeometry(.16,32,32),new THREE.MeshBasicMaterial({color:0xe8edf9}));scene.add(moon);
let mx=0,my=0,tx=0,ty=0,drag=false,lx=0,t=0;
cv.addEventListener('pointerdown',e=>{drag=true;lx=e.clientX;cv.style.cursor='grabbing';});
addEventListener('pointerup',()=>{drag=false;cv.style.cursor='grab';});
addEventListener('pointermove',e=>{tx=e.clientX/innerWidth-.5;ty=e.clientY/innerHeight-.5;if(drag){globe.rotation.y+=(e.clientX-lx)*.006;lx=e.clientX;}});
function loop(){requestAnimationFrame(loop);t+=.01;if(!drag)globe.rotation.y+=.0012;cloud.rotation.y=globe.rotation.y*1.08+.25;atm.rotation.y=-globe.rotation.y*.15;mx+=(tx-mx)*.03;my+=(ty-my)*.03;camera.position.x+=(mx*.7-camera.position.x)*.025;camera.position.y+=(-my*.35-camera.position.y)*.025;camera.lookAt(0,0,0);moon.position.set(2.55+Math.cos(t)*4,-2.7+Math.sin(t)*1.6,Math.sin(t)*2);renderer.render(scene,camera);}
loop();
}
</script></body></html>"""

# ---------------------------------------------------------------------------
# HELPERS / BACKGROUND
# ---------------------------------------------------------------------------
def render_three(template: str, cfg: dict, height: int):
    boot = BOOT_JS.replace("__CFG__", json.dumps(cfg)).replace("__THREE__", THREE_CDN)
    common = COMMON_JS.replace("__TEXTURE_CDN__", TEXTURE_CDN)
    page = template.replace("__BOOT__", boot).replace("__COMMON__", common)
    components.html(page, height=height, scrolling=False)


def img_css(era: dict) -> tuple[str, str]:
    for ext in ("jpg", "jpeg", "png", "webp"):
        f = ASSETS / f"{era['file']}.{ext}"
        if f.exists():
            mime = "jpeg" if ext in ("jpg", "jpeg") else ext
            b64 = base64.b64encode(f.read_bytes()).decode()
            return f"background-image:url(data:image/{mime};base64,{b64})", ""
    return f"background:{era['grad']}", era["emoji"]


def panel(name: str):
    return st.container(key=f"panel_{name}")


def panel_header(icon: str, title: str, sub: str):
    st.markdown(
        f'<div class="panel-h"><div class="ic">{icon}</div><div><b>{title}</b><i>{sub}</i></div></div>',
        unsafe_allow_html=True,
    )


LOGO = ('<svg width="40" height="40" viewBox="0 0 48 48" aria-hidden="true">'
        '<path d="M24 5 L37 18 L24 31 L11 18 Z" fill="none" stroke="#eaf2f8" stroke-width="2.6" stroke-linejoin="round"/>'
        '<path d="M24 31 L24 42" fill="none" stroke="#eaf2f8" stroke-width="2.6" stroke-linecap="round"/>'
        '<circle cx="24" cy="5" r="2.5" fill="#eaf2f8"/></svg>')


def header():
    nav = [("Dashboard", "Home"), ("Missions", "Earth Time Travel"), ("Star Map", "Planet Simulator"), ("Fleet", "Home"), ("Research", "AI Science Guide"), ("Logs", "About")]
    nav_html = "".join(
        f'<span class="topnav-item {"active" if ss.page == target else ""}">{label}</span>'
        for label, target in nav
    )
    st.markdown(
        f'<div class="hdr reference-hdr"><div class="brand">{LOGO}<div><h1>N O V A</h1>'
        '</div></div><div class="topnav">' + nav_html + '</div>'
        '<div class="badges"><div>⌕</div><div>♧</div><div>🌍　⌄</div></div></div>',
        unsafe_allow_html=True,
    )


def inject_background():
    # Keep the desktop NOVA cockpit composition, while making the same visual
    # language usable on phones instead of allowing Streamlit columns to create
    # huge empty gaps or push the navigation above the hero.
    st.markdown("""
    <style>
    .stApp{background:
      radial-gradient(ellipse at 76% 12%,rgba(42,55,130,.28),transparent 38%),
      radial-gradient(ellipse at 10% 72%,rgba(75,25,115,.18),transparent 36%),
      linear-gradient(145deg,#050a18,#02040d 80%) fixed!important}

    /* Desktop cockpit: compact rails and a consistent hero-to-cards rhythm. */
    @media(min-width:901px){
      .block-container{max-width:1600px!important;padding:.55rem 1rem .5rem!important}
      .hdr.reference-hdr{position:relative;z-index:5}
      .reference-hdr .topnav-item{cursor:default}
      [data-testid="stHorizontalBlock"]{gap:.55rem!important}
      .st-key-panel_nova_fleet,.st-key-panel_nova_next,.st-key-panel_nova_scan,.st-key-panel_nova_timeline{min-height:255px}
    }

    /* Phone/tablet: no oversized left rail, blank space, or off-screen controls.
       Sections remain in the same dark, rounded NOVA visual style. */
    @media(max-width:900px){
      .block-container{padding:.35rem .55rem .6rem!important;max-width:100%!important}
      .hdr.reference-hdr{display:flex!important;flex-wrap:wrap!important;gap:7px!important;padding:4px 3px 9px!important;margin-bottom:8px!important}
      .reference-hdr .brand{flex:1 1 100%!important;justify-content:center!important}
      .reference-hdr .brand h1{font-size:13px!important;letter-spacing:.34em!important}
      .reference-hdr .brand svg{width:28px!important;height:28px!important}
      .reference-hdr .topnav{order:3;width:100%;display:flex!important;overflow-x:auto!important;justify-content:flex-start!important;scrollbar-width:none;white-space:nowrap!important}
      .reference-hdr .topnav::-webkit-scrollbar{display:none}
      .reference-hdr .topnav-item{flex:0 0 auto!important;padding:8px 10px!important;font-size:9px!important}
      .reference-hdr .badges{margin-left:auto!important}
      /* Main Streamlit navigation rail is redundant on narrow screens. */
      .block-container > div > div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:first-child{display:none!important}
      .block-container > div > div[data-testid="stHorizontalBlock"] > div[data-testid="column"]{min-width:0!important}
      [data-testid="stHorizontalBlock"]{gap:.45rem!important;flex-wrap:wrap!important}
      [data-testid="stHorizontalBlock"] > [data-testid="column"]{min-width:0!important;flex:1 1 100%!important;width:100%!important}
      /* Keep card groups as 2-column tiles on phones; the timeline can span full width. */
      .st-key-panel_nova_fleet,.st-key-panel_nova_next,.st-key-panel_nova_scan{min-height:205px}
      .st-key-panel_nova_timeline{min-height:190px}
      .era{height:96px!important}
      .txt{left:14px!important;top:14px!important;max-width:72%!important}
      .txt h1{font-size:clamp(25px,7vw,39px)!important;line-height:1.02!important}
      .txt p{font-size:10px!important;max-width:235px!important}
      .txt small{font-size:9px!important}
      .cards{left:8px!important;right:8px!important;bottom:8px!important;gap:5px!important}
      .cd{min-width:0!important;flex:1 1 30%!important;padding:6px!important;gap:5px!important}
      .cd .i{min-width:23px!important;height:23px!important;font-size:12px!important}
      .cd b{font-size:8px!important}.cd span{font-size:7px!important}
      .foot{font-size:8px!important}
      [data-testid="stPlotlyChart"]{overflow:hidden!important}
      [data-testid="stMetricValue"]{font-size:18px!important}
    }

    @media(max-width:480px){
      .block-container{padding:.25rem .4rem .5rem!important}
      .reference-hdr .badges div{width:29px!important;height:29px!important}
      .reference-hdr .topnav-item{padding:7px 8px!important;font-size:8px!important}
      /* Hero keeps the headline on the left and the 3D globe behind it. */
      iframe[title*="streamlit.components"]{max-width:100%!important}
      [data-testid="stVerticalBlock"]{gap:.45rem!important}
      .st-key-panel_nova_fleet,.st-key-panel_nova_next,.st-key-panel_nova_scan,.st-key-panel_nova_timeline{padding:10px!important}
      .era{height:82px!important}
      .era .em{font-size:19px!important}
      .era .cap{font-size:9px!important}
    }
    </style>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# SECTIONS
# ---------------------------------------------------------------------------
def section_hero():
    era = cur_era()
    render_three(HERO_HTML, {"tint": era["tint"]}, 370)


def section_mission_overview():
    """Four compact mission cards inspired by the supplied NOVA cockpit image."""
    cards = st.columns([1.0, 1.0, 1.0, 1.22], gap="small")
    with cards[0]:
        with panel("nova_fleet"):
            panel_header("⌘", "FLEET STATUS", "3/5 operational")
            st.markdown('<div style="height:86px;display:grid;place-items:center;font-size:44px;color:#d8f7ef;text-shadow:0 0 22px #9de7ff">⌘</div><b style="font-size:11px">NSS VOYAGER</b><div style="font-size:9px;color:#5ee5b2;margin-top:4px">● READY</div><div class="bar"><i style="width:82%;background:#b8f4d6"></i></div><div style="text-align:right;font-size:9px;color:#b6c5d6">82%</div>', unsafe_allow_html=True)
    with cards[1]:
        with panel("nova_next"):
            panel_header("◒", "NEXT MISSION", "ETA 2D 14H")
            st.markdown('<div style="height:86px;border-radius:9px;background:radial-gradient(ellipse at 50% 80%,#e5e9ef,#8799ac 23%,transparent 55%),linear-gradient(160deg,#0a111c,#344252 60%,#070b12);display:grid;place-items:center;font-size:28px">🌑</div><b style="font-size:11px">KEPLER-186F</b><div style="font-size:9px;color:#9aafc2">SURVEY MISSION</div>', unsafe_allow_html=True)
            if st.button("↗ Open mission", key="nova_open_mission", use_container_width=True):
                ss.page = "Planet Simulator"; st.rerun()
    with cards[2]:
        with panel("nova_scan"):
            panel_header("◎", "SYSTEM SCAN", "LIVE")
            st.markdown('<div style="height:86px;display:grid;place-items:center;font-size:46px;color:#c5f4dd;text-shadow:0 0 18px #8de9bd">◎</div><b style="font-size:19px">7</b><div style="font-size:9px;color:#9aafc2">SIGNALS DETECTED</div>', unsafe_allow_html=True)
            if st.button("View scan →", key="nova_scan_btn", use_container_width=True):
                ss.page = "Planet Simulator"; st.rerun()
    with cards[3]:
        with panel("nova_timeline"):
            panel_header("│", "MISSION TIMELINE", "UPCOMING")
            st.markdown('<div class="qf"><span style="color:#5ee5b2">●</span><span>Engine Calibration</span><b style="color:#5ee5b2">COMPLETE</b></div><div class="qf"><span style="color:#5ee5b2">●</span><span>Gravity Assist</span><b>T-6:40</b></div><div class="qf"><span style="color:#b9dfff">●</span><span>Arrival: Kepler-186F</span><b>ETA 2D 14H</b></div><div class="qf"><span>○</span><span>Surface Survey</span><b>QUEUED</b></div>', unsafe_allow_html=True)


def section_time_travel():
    with panel("time"):
        panel_header("🌍", "Earth Time Travel", "Explore Earth's past and possible future")
        cols = st.columns(4)
        for i, (col, era) in enumerate(zip(cols, ERAS)):
            with col:
                with st.container(key=f"eracard{i}"):
                    css, emoji = img_css(era)
                    sel = " sel" if i == ss.era else ""
                    st.markdown(
                        f'<div class="era{sel}" style="{css}"><div class="em">{emoji}</div>'
                        f'<div class="cap"><b>{era["title"]}</b><br>{era["sub"]}</div></div>',
                        unsafe_allow_html=True,
                    )
                    if st.button("Explore era", key=f"eb{i}", help=f"Travel to {era['title']}"):
                        ss.era = i
                        st.rerun()
        e = cur_era()
        st.markdown(
            f'<div class="eradet"><b>{e["title"]} · {e["sub"]}</b> — {e["blurb"]}<br>'
            f'🌡️ Average temperature: <b>{e["temp"]}</b> &nbsp;•&nbsp; CO₂: <b>{e["co2"]}</b></div>',
            unsafe_allow_html=True,
        )
        titles = [f"{x['title']} ({x['sub']})" for x in ALL_ERAS]
        current_title = titles[ss.era]

        def on_jump():
            ss.era = titles.index(ss.jump)

        st.selectbox("More eras: Snowball Earth, Great Dying, Medieval Climate Anomaly, year 2500",
                     titles, index=titles.index(current_title), key="jump", on_change=on_jump)


def section_simulator():
    cur = ss.sim
    with panel("sim"):
        panel_header("🪐", "Planet Simulator", "Customize a world and explore its environment in interactive 3D.")
        left, right = st.columns([1, 2.6], gap="medium")
        with left:
            st.markdown('<div style="font-size:12px;font-weight:700;color:#fff;margin-bottom:4px">Planet Parameters</div>', unsafe_allow_html=True)
            ptype = st.selectbox("Planet Type", list(PLANETS), index=list(PLANETS).index(cur["ptype"]), key="w_ptype")
            suns = st.slider("Number of Suns", 1, 3, int(cur["suns"]), key="w_suns")
            star = st.selectbox("Star Type", list(STAR_TYPES), index=list(STAR_TYPES).index(cur["star"]), key="w_star")
            dist = st.slider("Orbital Distance (AU)", 0.3, 3.0, float(cur["dist"]), 0.1, key="w_dist")
            tilt = st.slider("Axial Tilt (°)", 0, 90, int(cur["tilt"]), key="w_tilt")
            ss.sim = {"ptype": ptype, "suns": suns, "star": star, "dist": dist, "tilt": tilt}
            sim = simulate(ss.sim)
            with st.container(key="runsim"):
                if st.button("▶  Run Simulation", type="primary", key="run"):
                    ss.runs.append({"ptype": ptype, "suns": suns, "star": star, "dist": dist, "tilt": tilt,
                                    "temp": sim["temp"], "hab": sim["hab"]})
                    st.toast(f"Run #{len(ss.runs)} saved: {sim['temp']:.1f}°C · habitability {sim['hab']}/100", icon="🪐")
                st.download_button("⬇  Download report", data=build_report(sim),
                                   file_name="horizon_shift_report.md", mime="text/markdown", key="dl")
            if ss.runs:
                with st.expander(f"Run history ({len(ss.runs)})"):
                    for i, r in enumerate(ss.runs, 1):
                        st.markdown(f'<div style="font-size:10.5px;color:#b4c2f0">#{i} · {r["ptype"]} · {r["suns"]}☀ · {r["dist"]} AU · {r["temp"]:.1f}°C · {r["hab"]}/100</div>', unsafe_allow_html=True)
                    if st.button("Clear history", key="clr"):
                        ss.runs = []
                        st.rerun()
        with right:
            era = cur_era()
            tint = era["tint"] if ptype == "Terrestrial" else {
                "Ocean World": "#6fb4ff", "Desert World": "#ffb070", "Ice World": "#dff2ff",
                "Gas Giant": "#e3b17d"}.get(ptype, "#ffffff")
            render_three(SIM_HTML, {
                "label": sun_label(sim["suns"]), "suns": sim["suns"],
                "sunColor": STAR_TYPES[sim["star"]]["color"],
                "sunColors": [STAR_TYPES[sim["star"]]["color"], "#ff8c55", "#b7d7ff"],
                "tint": tint, "glow": PLANETS[ptype]["glow"], "tilt": sim["tilt"],
                "gas": ptype == "Gas Giant", "clouds": 0.0 if ptype == "Desert World" else 0.55,
            }, 285)
        hc = "#38d39f" if sim["hab"] >= 70 else "#f5a623" if sim["hab"] >= 40 else "#ff7a3d" if sim["hab"] >= 15 else "#ff4d5e"
        st.markdown(
            '<div class="met">'
            f'<div><span class="ico">🌡️</span><span><small>Average Temperature</small><b>{sim["temp"]:.1f}°C</b></span></div>'
            f'<div><span class="ico">☀️</span><span><small>Day Length</small><b>{sim["day"]:.0f} hours</b></span></div>'
            f'<div><span class="ico">🌿</span><span><small>Atmosphere</small><b>{sim["atm"]}</b></span></div>'
            f'<div><span class="ico">🌱</span><span style="flex:1;min-width:0"><small>Habitability (heuristic)</small>'
            f'<b style="color:{hc}">{sim["hab"]}/100 · {sim["hab_label"]}</b><div class="bar"><i style="width:{sim["hab"]}%;background:{hc}"></i></div></span></div></div>',
            unsafe_allow_html=True,
        )
        tab1, tab2 = st.tabs(["Temperature Over Time", "Seasons"])
        layout = dict(height=165, margin=dict(l=30, r=8, t=8, b=28), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(size=10, color="#9fb0e6"),
                      legend=dict(x=.99, xanchor="right", y=1, bgcolor="rgba(0,0,0,0)"), hovermode="x unified")
        with tab1:
            hrs, pl, ea = temp_series(sim)
            fig = go.Figure()
            fig.add_scatter(x=hrs, y=pl, name="Planet Surface", line=dict(color="#f5a623", width=2.5))
            fig.add_scatter(x=hrs, y=ea, name="Earth Reference", line=dict(color="#4aa3ff", width=1.7, dash="dot"))
            fig.add_hline(y=0, line=dict(color="#5a6fb0", width=1, dash="dash"))
            fig.update_layout(**layout, xaxis=dict(title="Time (hours)", gridcolor="#12204a", title_font_size=10),
                              yaxis=dict(title="°C", gridcolor="#12204a", title_font_size=10))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key="ch_day")
        with tab2:
            mo, pl2, ea2 = season_series(sim)
            fig2 = go.Figure()
            fig2.add_scatter(x=mo, y=pl2, name=f"Planet (tilt {sim['tilt']}°)", line=dict(color="#f5a623", width=2.5))
            fig2.add_scatter(x=mo, y=ea2, name="Earth Reference", line=dict(color="#4aa3ff", width=1.7, dash="dot"))
            fig2.add_hline(y=0, line=dict(color="#5a6fb0", width=1, dash="dash"))
            fig2.update_layout(**layout, xaxis=dict(title="Month", gridcolor="#12204a", title_font_size=10),
                               yaxis=dict(title="°C", gridcolor="#12204a", title_font_size=10))
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False}, key="ch_season")


def section_ai_panel():
    sim = simulate(ss.sim)
    with panel("ai"):
        status = "Connected" if _api_key() else "Offline mode"
        color = "#38d39f" if _api_key() else "#f5a623"
        st.markdown(
            '<div class="panel-h" style="justify-content:space-between"><div style="display:flex;gap:10px;align-items:center">'
            '<div class="ic">🤖</div><b>AI Science Guide</b></div>'
            f'<i style="font-style:normal;font-size:9px;color:{color}"><span class="dot" style="background:{color}"></span>{status}</i></div>',
            unsafe_allow_html=True,
        )
        box = st.container(height=330, border=False)
        with box:
            parts = ['<div class="chat">']
            for m in ss.chat:
                if m["role"] == "user":
                    parts.append(f'<div class="u">{html.escape(m["text"])}</div>')
                else:
                    parts.append('<div class="b"><div class="av">🤖</div><div class="msg">' + md_to_html(m["text"]) +
                                 "<em>Horizon Shift Science Guide</em></div></div>")
            parts.append("</div>")
            st.markdown("".join(parts), unsafe_allow_html=True)
        with st.form("chat_form", clear_on_submit=True, border=False):
            c1, c2 = st.columns([6, 1])
            q = c1.text_input("q", placeholder="Ask about this planet, Earth's past, or alien life…", label_visibility="collapsed")
            sent = c2.form_submit_button("➤")
        if sent and q.strip():
            ss.chat.append({"role": "user", "text": q.strip()})
            with st.spinner("Science Guide is thinking…"):
                ss.chat.append({"role": "bot", "text": ask_gemini(q.strip(), sim, cur_era())})
            st.rerun()


def section_facts():
    sim = simulate(ss.sim)
    with panel("facts"):
        panel_header("🔥", "Quick Facts", "Live values from the current simulation")
        rows = [("🪐", "Planet Name", sim["name"]), ("🌿", "Atmosphere", sim["atm"]),
                ("🌡️", "Surface Temperature", f'{sim["temp"]:.1f}°C'), ("🕒", "Day Length", f'{sim["day"]:.0f} hours'),
                ("🧭", "Orbital Distance", f'{sim["dist"]} AU'), ("📐", "Axial Tilt", f'{sim["tilt"]}°'),
                ("🌱", "Habitability", f'{sim["hab"]}/100')]
        st.markdown("".join(f'<div class="qf"><span>{i}</span><span>{k}</span><b>{v}</b></div>' for i, k, v in rows), unsafe_allow_html=True)


def page_about():
    with panel("about"):
        panel_header("ℹ️", "About Horizon Shift", "A visual science exploration app")
        st.markdown(
            "Horizon Shift lets you explore Earth's climate history, build hypothetical worlds with one to three suns, "
            "and ask an AI science guide about the results.\n\n"
            "- **Earth Time Travel:** compare four featured eras plus four additional time periods.\n"
            "- **Planet Simulator:** adjust planet type, star type, number of suns, orbital distance and axial tilt.\n"
            "- **Interactive 3D:** rotating planets, cloud layers, atmospheric glow, orbiting bodies and starfield.\n"
            "- **AI Science Guide:** context-aware answers using Gemini when an API key is configured.\n"
            "- **Reports and charts:** download a Markdown report and compare temperature patterns.\n\n"
            "**Important:** The temperature and habitability values are simplified teaching approximations, not validated climate predictions."
        )


SUGGESTIONS = [
    "How does having two suns affect a planet's climate?",
    "Could life exist around a red dwarf star?",
    "Why did the last Ice Age end?",
    "How would a 90° axial tilt change seasons?",
]


def page_ai_prompts():
    with panel("prompts"):
        panel_header("✨", "Try asking the AI Science Guide", "Choose a question to send it to the guide")
        for i, question in enumerate(SUGGESTIONS):
            if st.button(question, key=f"sug{i}"):
                ss.chat.append({"role": "user", "text": question})
                ss.chat.append({"role": "bot", "text": ask_gemini(question, simulate(ss.sim), cur_era())})
                ss.page = "AI Science Guide"
                st.rerun()


# ---------------------------------------------------------------------------
# LAYOUT — original navigation + main content + right-side AI panel retained
# ---------------------------------------------------------------------------
header()
nav_col, main_col, right_col = st.columns([1.05, 5.2, 2.35], gap="small")

with nav_col:
    with st.container(key="navbox"):
        for label, icon in [("Home", "🏠"), ("Earth Time Travel", "🕒"), ("Planet Simulator", "🪐"),
                            ("AI Science Guide", "✨"), ("About", "ℹ️")]:
            if st.button(f"{icon}  {label}", key=f"nav_{label}",
                         type="primary" if ss.page == label else "secondary"):
                ss.page = label
                st.rerun()
    st.markdown('<div class="quote">“Same sky,<br>different worlds,<br>endless possibilities.”</div><div class="galaxy"></div>',
                unsafe_allow_html=True)

with main_col:
    if ss.page == "Home":
        section_hero()
        section_mission_overview()
        section_time_travel()
        section_simulator()
    elif ss.page == "Earth Time Travel":
        section_hero()
        section_time_travel()
    elif ss.page == "Planet Simulator":
        section_simulator()
    elif ss.page == "AI Science Guide":
        page_ai_prompts()
    else:
        page_about()

with right_col:
    section_ai_panel()
    if ss.page in ("Home", "Planet Simulator"):
        section_facts()

inject_background()
st.markdown('<div class="foot">NOVA · MISSION CONTROL · EXPLORE. DISCOVER. ENDURE.</div>',
            unsafe_allow_html=True)
