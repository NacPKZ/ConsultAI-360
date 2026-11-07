"""ConsultAI 360 — console de décision NexaRetail.

Lancer : python -m streamlit run app.py
Démo publique : CONSULTAI_DEMO_MODE=true (aucune base de données ni Ollama requis).
Copilote local optionnel : Ollama (OLLAMA_HOST, CONSULTAI_OLLAMA_MODEL).
Thème : copier config.toml dans .streamlit/config.toml (thème sombre natif).
"""

from __future__ import annotations

import difflib
import html
import json
import os
import re
import time
import unicodedata
import urllib.request
from datetime import date
from urllib.parse import urlparse

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from project_knowledge import correct as correct_question
from project_knowledge import profile as author_profile
from project_knowledge import project_answer

st.set_page_config(
    page_title="ConsultAI 360",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Le thème Streamlit est configuré AVANT le lancement dans .streamlit/config.toml.
# Ne pas modifier les fichiers de configuration pendant une session utilisateur.

# Chiffres de référence relevés lors des tests de l'étape 8.4. Ce n'est PAS un flux live.
REFERENCE = {
    "low": {
        "orders": 120000,
        "missing": 1200,
        "basket": 600.40,
        "deliveries": 70005,
        "late": 10333,
    },
    "medium": {
        "orders": 120000,
        "missing": 6000,
        "basket": 600.42,
        "deliveries": 70005,
        "late": 10333,
    },
    "critical": {
        "orders": 120000,
        "missing": 12000,
        "basket": 600.94,
        "deliveries": 70005,
        "late": 10333,
    },
}
SCENARIOS = ("low", "medium", "critical")
SCENARIO_LABEL = {
    "low": "Faible : 1 % de montants absents",
    "medium": "Moyen : 5 % de montants absents",
    "critical": "Critique : 10 % de montants absents",
}
PUBLIC = os.getenv("CONSULTAI_DEMO_MODE", "false").strip().lower() in (
    "true",
    "1",
    "yes",
)


def _stretch() -> dict:
    """use_container_width est déprécié dans les Streamlit récents (width="stretch")."""
    try:
        v = tuple(int(x) for x in st.__version__.split(".")[:2])
    except ValueError:
        v = (0, 0)
    return {"width": "stretch"} if v >= (1, 50) else {"use_container_width": True}  # type: ignore


STRETCH = _stretch()

TXT, COBALT, MINT, AMBER, CORAL, MIST = (
    "#e8f0fa",
    "#50a6e8",
    "#49d9b6",
    "#f0b45e",
    "#f0767b",
    "#7792ab",
)
PAGES = [
    "Mission Control",
    "Observatoire",
    "Investigation",
    "Scenario Lab",
    "Decision Gate",
    "Data Lineage",
    "AI Copilot",
]
PAGE_ICONS = {
    "Mission Control": "📊",
    "Observatoire": "📈",
    "Investigation": "🔎",
    "Scenario Lab": "🧪",
    "Decision Gate": "🛡️",
    "Data Lineage": "🧬",
    "AI Copilot": "🤖",
}

st.markdown(
    """<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
:root{color-scheme:dark}
@property --p{syntax:'<percentage>';inherits:false;initial-value:0%}
@property --n{syntax:'<integer>';inherits:false;initial-value:0}

/* base : la police n'est JAMAIS forcée sur span/div, sinon les icônes Material s'affichent en texte */
html,body,[data-testid="stAppViewContainer"],.stApp{background:#070d17!important;color:#e7eef8}
.stApp{background:radial-gradient(1100px 520px at 88% -8%,rgba(40,130,160,.22),transparent 62%),radial-gradient(900px 480px at -5% 105%,rgba(60,90,200,.14),transparent 60%),#070d17!important;font-family:'DM Sans',sans-serif}
.stApp [data-testid="stMarkdownContainer"],.stApp label,.stApp button,.stApp input,.stApp textarea,.stApp h1,.stApp h2,.stApp h3,.stApp h4{font-family:'DM Sans',sans-serif}
[data-testid="stIconMaterial"],.material-symbols-rounded,.material-icons{font-family:'Material Symbols Rounded','Material Icons'!important}
.block-container{max-width:1540px;padding-top:1.5rem;padding-bottom:4rem;overflow-x:hidden}
header[data-testid="stHeader"]{background:transparent!important}
h1,h2,h3,h4{color:#f2f6ff!important;letter-spacing:-.035em}
[data-testid="stMarkdownContainer"] p{color:inherit}
.stApp ::selection{background:#1a8d7c;color:#fff}

/* sidebar */
[data-testid="stSidebar"]{background:#0b1524!important;border-right:1px solid #1f3146}
[data-testid="stSidebar"] label,[data-testid="stSidebar"] p,[data-testid="stSidebar"] [data-testid="stCaptionContainer"]{color:#c6d6e6}
[data-testid="stSidebar"] hr{border-color:#243750}
[data-testid="stSidebar"] [role="radiogroup"]{gap:4px}
[data-testid="stSidebar"] [role="radiogroup"] label{padding:10px 13px;border-radius:9px;width:100%;cursor:pointer;transition:background .2s,transform .2s,border-color .2s;border-left:3px solid transparent}
[data-testid="stSidebar"] [role="radiogroup"] label>div:first-child{display:none}
[data-testid="stSidebar"] [role="radiogroup"] label:hover{background:#13233a;transform:translateX(3px)}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked){background:linear-gradient(90deg,#17413f,#12283a);border-left-color:#47dec1}
.brand{display:flex;gap:12px;align-items:center;font-size:1.3rem;font-weight:800;color:#fff;letter-spacing:-.045em}
.brand i{font-style:normal;display:grid;place-items:center;width:38px;height:38px;border-radius:11px;background:linear-gradient(135deg,#47dec1,#4a7cf0);color:#06121f;font-size:1.25rem;animation:spin 14s linear infinite}
.brand small{display:block;color:#7e9eb4;font:500 .68rem 'IBM Plex Mono',monospace;margin-top:3px;letter-spacing:.03em}

/* champs (dark propre, pas de blanc) */
[data-baseweb="input"],[data-baseweb="base-input"],[data-baseweb="textarea"],[data-baseweb="select"]>div{background:#12223a!important;border-color:#2c4660!important;color:#e7eef8!important;border-radius:9px!important}
div[data-baseweb="select"]>div,div[data-baseweb="input"],div[data-baseweb="base-input"],div[data-baseweb="textarea"]{background-color:#12223a!important;border:1px solid #2c4660!important}
div[data-baseweb="base-input"] input,div[data-baseweb="input"] input,[data-testid="stTextInput"] input,[data-testid="stNumberInput"] input,div[data-baseweb="select"] input{background:transparent!important;color:#e7eef8!important;-webkit-text-fill-color:#e7eef8!important;caret-color:#47dec1}
div[data-baseweb="select"] div,div[data-baseweb="select"] span{color:#e7eef8!important}
div[data-baseweb="select"] svg{fill:#9fb6c9!important}
input::placeholder,textarea::placeholder{color:#7f97ab!important;-webkit-text-fill-color:#7f97ab!important;opacity:1}
[data-testid="stWidgetLabel"],[data-testid="stWidgetLabel"] *,.stApp label,.stApp label p{color:#c6d6e6!important}
[data-testid="stExpander"] details,[data-testid="stExpander"] summary,[data-testid="stExpander"] summary:hover,[data-testid="stExpander"] summary:focus,[data-testid="stExpander"] details[open]>summary{background:#0f1c2e!important;color:#e7eef8!important}
[data-testid="stExpander"] summary *{color:#e7eef8!important}
[data-testid="stExpander"] summary:hover *{color:#74f3d4!important}
[data-testid="stExpanderDetails"]{background:#0f1c2e!important}
[data-baseweb="select"] *,[data-baseweb="input"] input,[data-baseweb="textarea"] textarea{color:#e7eef8!important;-webkit-text-fill-color:#e7eef8!important}
[data-baseweb="popover"] ul,[data-baseweb="menu"],[data-baseweb="popover"]>div{background:#12223a!important;color:#e7eef8!important;border:1px solid #2c4660}
[data-baseweb="popover"] li:hover,[data-baseweb="menu"] li:hover{background:#1c3550!important}
[data-testid="stNumberInput"] button{background:#18304a!important;color:#cfe0ee!important;border-color:#2c4660!important}
[data-testid="stSlider"] [data-testid="stTickBarMin"],[data-testid="stSlider"] [data-testid="stTickBarMax"],[data-testid="stSlider"] label{color:#9fb6c9!important}
[data-testid="stSlider"] div[role="slider"]{background:#47dec1!important;box-shadow:0 0 0 5px rgba(71,222,193,.18)}
[data-testid="stExpander"]{background:#0f1c2e;border:1px solid #243a52!important;border-radius:11px}
[data-testid="stExpander"] summary:hover{color:#74f3d4}
[data-testid="stCodeBlock"],[data-testid="stCodeBlock"] pre,pre{background:#09131f!important;border:1px solid #243a52;border-radius:9px}
code{color:#9fe8d6!important;background:rgba(71,222,193,.08)!important;border-radius:4px;padding:1px 5px}
pre code{background:transparent!important;padding:0}
[data-testid="stAlert"]{background:#12223a!important;border:1px solid #2c4660!important;color:#e7eef8!important;border-radius:10px}
[data-testid="stVerticalBlockBorderWrapper"]{border-color:#243a52!important;background:#0e1b2c;border-radius:12px}
[data-testid="stChatMessage"]{background:#0f1d30!important;border:1px solid #243a52;border-radius:14px!important;margin-bottom:12px;animation:rise .4s both}
[data-testid="stChatInput"],[data-testid="stChatInput"]>div{background:#12223a!important;border-radius:12px!important}
[data-testid="stChatInput"] textarea{color:#e7eef8!important;-webkit-text-fill-color:#e7eef8!important}
/* Barre du copilote : lisible, visible et cohérente avec le thème sombre. */
[data-testid="stChatInput"]{border:1px solid #3c617a!important;box-shadow:0 0 0 1px rgba(71,222,193,.07),0 12px 30px rgba(0,0,0,.22)!important;overflow:visible!important}
[data-testid="stChatInput"]:focus-within{border-color:#47dec1!important;box-shadow:0 0 0 3px rgba(71,222,193,.12)!important}
[data-testid="stChatInput"] textarea{background:#12223a!important;color:#e7eef8!important;min-height:48px!important;line-height:1.5!important}
[data-testid="stChatInput"] button{color:#47dec1!important}
.stButton>button,.stDownloadButton>button{background:#13243b!important;color:#dbe9f4!important;border:1px solid #33506b!important;border-radius:9px!important;min-height:42px;font-weight:600;transition:transform .18s,border-color .18s,box-shadow .18s}
.stButton>button:hover,.stDownloadButton>button:hover{border-color:#47dec1!important;color:#7af3d6!important;transform:translateY(-2px);box-shadow:0 8px 20px rgba(71,222,193,.12)}
.stButton>button[kind="primary"],.stDownloadButton>button[kind="primary"]{background:linear-gradient(135deg,#1a9a86,#2a6fd1)!important;border-color:transparent!important;color:#fff!important}
.js-plotly-plot .sankey text,.js-plotly-plot .sankey .node-label{text-shadow:none!important;stroke:none!important;paint-order:normal!important}

/* V3.1 — correction du contraste des contrôles Streamlit/BaseWeb.
   Le thème natif reste la source de vérité ; CSS de secours pour les versions récentes. */
:root { color-scheme: dark; }
.stApp [data-testid="stNumberInput"] [data-baseweb="input"],
.stApp [data-testid="stTextInput"] [data-baseweb="input"],
.stApp [data-testid="stSelectbox"] [data-baseweb="select"],
.stApp [data-testid="stMultiSelect"] [data-baseweb="select"],
.stApp [data-testid="stDateInput"] [data-baseweb="input"],
.stApp [data-testid="stTimeInput"] [data-baseweb="input"],
.stApp [data-testid="stTextArea"] [data-baseweb="textarea"],
.stApp [data-testid="stChatInput"] [data-baseweb="textarea"],
.stApp [data-baseweb="input"],
.stApp [data-baseweb="base-input"],
.stApp [data-baseweb="select"] > div,
.stApp [data-baseweb="textarea"] {
    background: #12223a !important;
    background-color: #12223a !important;
    border-color: #34516c !important;
    color: #e7eef8 !important;
    box-shadow: none !important;
}
.stApp [data-testid="stNumberInput"] input,
.stApp [data-testid="stTextInput"] input,
.stApp [data-testid="stDateInput"] input,
.stApp [data-testid="stTimeInput"] input,
.stApp [data-testid="stTextArea"] textarea,
.stApp [data-testid="stChatInput"] textarea,
.stApp [data-baseweb="input"] input,
.stApp [data-baseweb="base-input"] input,
.stApp [data-baseweb="textarea"] textarea {
    background: #12223a !important;
    background-color: #12223a !important;
    color: #e7eef8 !important;
    -webkit-text-fill-color: #e7eef8 !important;
    caret-color: #47dec1 !important;
    opacity: 1 !important;
}
.stApp input::placeholder,
.stApp textarea::placeholder {
    color: #93abc0 !important;
    -webkit-text-fill-color: #93abc0 !important;
    opacity: 1 !important;
}
.stApp [data-baseweb="select"] [role="combobox"],
.stApp [data-baseweb="select"] [aria-selected],
.stApp [data-baseweb="select"] span {
    background-color: transparent !important;
    color: #e7eef8 !important;
    -webkit-text-fill-color: #e7eef8 !important;
}
.stApp [data-testid="stNumberInput"] button,
.stApp [data-testid="stNumberInput"] button * {
    background-color: #1a304a !important;
    color: #e7eef8 !important;
    fill: #e7eef8 !important;
}
.stApp [data-testid="stNumberInput"] button:hover { background-color: #254460 !important; }
.stApp [data-baseweb="input"]:focus-within,
.stApp [data-baseweb="textarea"]:focus-within,
.stApp [data-baseweb="select"]:focus-within {
    border-color: #47dec1 !important;
    box-shadow: 0 0 0 2px rgba(71,222,193,.14) !important;
}
.stApp [data-testid="stChatInput"] { background: #12223a !important; }
.stApp [data-testid="stChatInput"] > div { background: #12223a !important; }
.stApp [data-testid="stChatInput"] textarea { min-height: 44px !important; }
.stApp [data-testid="stChatInput"] button { background: #1b3b4c !important; }
.stApp [data-testid="stProgressBar"] > div { background: #20364b !important; }
.stApp [data-testid="stProgressBar"] > div > div { background: #47dec1 !important; }
/* Les notifications de configuration ne doivent pas masquer la navigation. */
@media (max-width: 800px) {
  [data-testid="stSidebar"] { min-width: 225px; }
}

/* hero */
.hero{display:grid;grid-template-columns:1fr auto;gap:28px;align-items:center;border:1px solid #27485a;border-radius:18px;padding:36px 40px;margin-bottom:22px;
  background:linear-gradient(125deg,#0f2a3d,#0b1626 55%,#0f3d44,#0e2036);background-size:240% 240%;animation:drift 16s ease-in-out infinite;position:relative;overflow:hidden}
.hero::after{content:"";position:absolute;inset:-40% -10% auto auto;width:420px;height:420px;background:radial-gradient(circle,rgba(71,222,193,.2),transparent 65%);animation:float 9s ease-in-out infinite;pointer-events:none}
.hero>*{position:relative;z-index:1}
.hero-title{font-size:clamp(1.8rem,3vw,2.7rem);font-weight:800;line-height:1.1;letter-spacing:-.05em;margin:16px 0 12px;max-width:830px;color:#f2f6ff}
.hero-sub{color:#a9bdd0;line-height:1.7;font-size:1rem;max-width:860px;margin:0}
.chips span{display:inline-flex;align-items:center;gap:7px;font:600 .68rem 'IBM Plex Mono',monospace;text-transform:uppercase;letter-spacing:.06em;border:1px solid #355568;color:#7de6cf;background:rgba(24,58,64,.7);padding:6px 11px;margin:0 6px 4px 0;border-radius:99px}
.dot{width:7px;height:7px;border-radius:50%;background:#47dec1;animation:pulse 1.8s ease-out infinite}
.hero-score{text-align:center;min-width:170px}
.ring{--p:var(--target);width:148px;height:148px;border-radius:50%;margin:0 auto 12px;display:grid;place-items:center;background:conic-gradient(var(--c) var(--p),#2b3d52 0);animation:fill 1.4s cubic-bezier(.2,.8,.2,1) both;box-shadow:0 0 38px -8px var(--c)}
.ring-in{width:117px;height:117px;background:#0c1a2b;border-radius:50%;display:grid;place-content:center;text-align:center}
.ring-in b{--n:var(--score);counter-reset:n var(--n);animation:cnt 1.4s cubic-bezier(.2,.8,.2,1) both;font-size:2.7rem;font-weight:800;color:#fff;line-height:1}
.ring-in b::after{content:counter(n)}
.ring-in span{color:#8fa8b9;font:500 .68rem 'IBM Plex Mono',monospace}
.verdict{display:inline-block;padding:5px 11px;font-size:.73rem;font-weight:700;border-radius:99px}
.v-go{background:#123d36;color:#6ee8c3}.v-warn{background:#49391c;color:#f5c87c}.v-stop{background:#4d232d;color:#ff9d9d}
.hero-note{font:500 .68rem 'IBM Plex Mono',monospace;color:#9cb2c4;margin-top:9px}

/* titres et structure */
.pagehead{margin:6px 0 24px;animation:rise .5s both}
.pagehead h2{font-size:2.05rem!important;margin:0 0 6px!important}
.pagehead p{color:#94a9bc;margin:0;font-size:.98rem;max-width:900px}
.h3{font-size:1.1rem;font-weight:800;margin:28px 0 13px;color:#eaf2fc}
.eyebrow{font:600 .7rem 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:#5ce4c5;margin-bottom:10px}
.ledger{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));background:#0f1c2e;border:1px solid #243a52;border-radius:14px;overflow:hidden}
.cell{padding:20px 22px;border-right:1px solid #243a52;transition:background .25s}
.cell:hover{background:#13263c}.cell:last-child{border-right:0}
.cell .lab{font:500 .7rem 'IBM Plex Mono',monospace;text-transform:uppercase;letter-spacing:.04em;color:#8ca4b8}
.cell .val{font-size:clamp(1.4rem,2vw,2.05rem);font-weight:800;color:#f5f8fd;margin:9px 0 4px;letter-spacing:-.04em}
.cell .note{color:#9bb1c3;font-size:.8rem}
.bar{height:5px;background:#243649;border-radius:5px;margin-top:13px;overflow:hidden}
.bar i{display:block;height:100%;border-radius:5px;transform-origin:left;animation:grow 1.1s cubic-bezier(.2,.8,.2,1) both}
.row{display:flex;justify-content:space-between;gap:16px;background:#0f1d30;border:1px solid #243a52;border-left:4px solid #8aa4b9;border-radius:11px;padding:16px 18px;margin-bottom:10px;transition:transform .22s,border-color .22s,box-shadow .22s}
.row:hover{transform:translateX(4px);box-shadow:0 10px 26px rgba(0,0,0,.28)}
.row.high{border-left-color:#ff7777}.row.mid{border-left-color:#ffbd63}.row.low{border-left-color:#4bd9b7}
.row-title{font-weight:700;color:#f0f5fc;margin-bottom:5px}
.row-why{color:#9bb0c3;font-size:.87rem;line-height:1.6}
.pills{display:flex;gap:6px;flex-shrink:0;align-items:flex-start;flex-wrap:wrap}
.pill{background:#1c3b47;color:#7ce1c8;font-size:.7rem;padding:4px 9px;border-radius:99px;white-space:nowrap}.pill.soft{background:#243249;color:#b7c8d8}
.card{background:#0f1d30;border:1px solid #243a52;border-radius:14px;padding:20px;height:100%;transition:transform .22s,border-color .22s}
.card:hover{transform:translateY(-4px);border-color:#3b6f7b}
.card h4{font-size:1rem;margin:0 0 8px}.card p{color:#a6b9cb;line-height:1.65;font-size:.88rem;margin:0}
.card .ic{display:inline-grid;place-items:center;width:34px;height:34px;border-radius:10px;background:linear-gradient(135deg,rgba(71,222,193,.25),rgba(74,124,240,.25));margin-bottom:12px;font-size:1rem}
.callout{background:#2a271c;border:1px solid #65522f;border-radius:10px;color:#f0d6a3;padding:13px 16px;margin:12px 0;font-size:.87rem;line-height:1.6}
.ops-banner{background:#0f2231;border:1px solid #27485a;border-left:4px solid #48dfc0;border-radius:10px;padding:14px 18px;color:#c6d8e7;margin:12px 0 20px;font-size:.88rem;line-height:1.65}
.kicker{font:500 .7rem 'IBM Plex Mono',monospace;color:#73dec7;text-transform:uppercase;letter-spacing:.07em;margin-bottom:4px}
.tblwrap{overflow-x:auto;border:1px solid #243a52;border-radius:12px}
.tbl{width:100%;border-collapse:collapse;background:#0e1b2c}
.tbl th{background:#15263b;color:#9fb8c9;text-align:left;font:500 .72rem 'IBM Plex Mono',monospace;padding:13px;white-space:nowrap}
.tbl td{color:#e0eaf4;border-top:1px solid #243a52;padding:13px;font-size:.87rem}
.tbl tr.sel td{background:#143a40}
.tag{display:inline-block;font:600 .66rem 'IBM Plex Mono',monospace;text-transform:uppercase;letter-spacing:.06em;padding:4px 9px;border-radius:99px;margin:0 6px 8px 0;background:#173b45;color:#7ce1c8;border:1px solid #2b5560}
.tag.hyp{background:#3a2f18;color:#f5c87c;border-color:#65522f}.tag.info{background:#1d2b44;color:#a9c4f5;border-color:#33507d}
.mini{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:14px}
.mini div{background:#0f1d30;border:1px solid #243a52;border-radius:12px;padding:14px 16px}
.mini b{display:block;font-size:1.5rem;letter-spacing:-.04em;color:#f5f8fd}.mini span{font-size:.78rem;color:#8ca4b8}

/* pipeline animé */
.pipe{display:flex;align-items:stretch;gap:0;margin:6px 0 4px}
.pnode{background:#0f1d30;border:1px solid #2b4a63;border-radius:13px;padding:15px 16px;min-width:150px;flex:0 0 auto;max-width:190px}
.pnode b{display:block;color:#f0f5fc;margin-bottom:4px;font-size:.93rem}.pnode span{color:#93aabd;font-size:.78rem;line-height:1.5}
.plink{flex:1;min-width:34px;align-self:center;height:2px;background:#27425a;position:relative}
.plink::after{content:"";position:absolute;top:-3px;left:0;width:8px;height:8px;border-radius:50%;background:#47dec1;box-shadow:0 0 12px #47dec1;animation:flow 2.4s linear infinite}
.plink:nth-child(4)::after{animation-delay:.6s}.plink:nth-child(6)::after{animation-delay:1.2s}.plink:nth-child(8)::after{animation-delay:1.8s}
.foot{border-top:1px solid #22344a;color:#7791a7;padding-top:15px;margin-top:42px;font:400 .7rem 'IBM Plex Mono',monospace;letter-spacing:.02em}

.fx{animation:rise .55s cubic-bezier(.2,.7,.2,1) both;animation-delay:calc(var(--i,0)*70ms)}
@keyframes rise{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}
@keyframes fill{from{--p:0%}to{--p:var(--target)}}
@keyframes cnt{from{--n:0}to{--n:var(--score)}}
@keyframes drift{0%,100%{background-position:0% 50%}50%{background-position:100% 50%}}
@keyframes float{0%,100%{transform:translate(0,0)}50%{transform:translate(-40px,30px)}}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(71,222,193,.6)}100%{box-shadow:0 0 0 10px rgba(71,222,193,0)}}
@keyframes flow{from{left:0}to{left:calc(100% - 8px)}}
@keyframes spin{to{transform:rotate(360deg)}}
@media(max-width:1000px){.hero{grid-template-columns:1fr}.ledger{grid-template-columns:repeat(2,1fr)}.cell{border-bottom:1px solid #243a52}.pipe{flex-direction:column}.pnode{max-width:none}.plink{width:2px;height:30px;min-height:30px;align-self:center}.plink::after{left:-3px;top:0;animation-name:flowv}.mini{grid-template-columns:1fr}}
@keyframes flowv{from{top:0}to{top:calc(100% - 8px)}}
@media(max-width:600px){.ledger{grid-template-columns:1fr}.hero{padding:24px}.row{flex-direction:column}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important}}

/* V3.2 — lisibilité du copilote et occupation de l’espace */
.block-container{max-width:1720px!important;padding:1.05rem 2rem 2.1rem!important}
[data-testid="stSidebar"]{min-width:232px!important}
/* Le flux natif Streamlit peut hériter d’un texte sombre : imposer la lisibilité
   seulement à la zone de réponse, sans casser les icônes Material. */
.stApp [data-testid="stChatMessage"]{background:linear-gradient(130deg,#111f33,#0c192a)!important;border:1px solid #29435a!important;padding:1rem 1.2rem!important;box-shadow:0 10px 24px rgba(0,0,0,.13);animation:message-enter .34s ease-out both;transition:border-color .2s,box-shadow .2s}
.stApp [data-testid="stChatMessage"]:hover{border-color:#3b7082!important;box-shadow:0 12px 30px rgba(0,0,0,.22)}
.stApp [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"],
.stApp [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
.stApp [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li,
.stApp [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] strong,
.stApp [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] em,
.stApp [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] blockquote,
.stApp [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h1,
.stApp [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h2,
.stApp [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h3,
.stApp [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h4{color:#eaf3ff!important;-webkit-text-fill-color:#eaf3ff!important;opacity:1!important}
.stApp [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p{line-height:1.68!important;font-size:.97rem!important;margin:.4rem 0 .7rem!important}
.stApp [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] a{color:#63e9d2!important;-webkit-text-fill-color:#63e9d2!important}
.stApp [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] strong{font-weight:750!important}
.stApp [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] code{color:#a5f4e4!important;-webkit-text-fill-color:#a5f4e4!important}
.stApp [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] ul{padding-left:1.25rem!important}
/* Barre fixe : suppression de la bande claire en bas de la fenêtre */
.stApp [data-testid="stBottom"],
.stApp [data-testid="stBottom"]>div,
.stApp [data-testid="stBottomBlockContainer"],
.stApp [data-testid="stChatInputContainer"]{background:#070d17!important;background-color:#070d17!important;border-color:#21384c!important}
.stApp [data-testid="stBottomBlockContainer"]{max-width:1720px!important;padding:10px 2rem 14px!important}
.stApp [data-testid="stChatInput"]{background:#13243b!important;border:1px solid #39617a!important;box-shadow:0 6px 25px rgba(0,0,0,.22)!important;transition:box-shadow .2s,border-color .2s}
.stApp [data-testid="stChatInput"]:focus-within{border-color:#49d9b6!important;box-shadow:0 0 0 3px rgba(73,217,182,.12),0 10px 32px rgba(0,0,0,.24)!important}
/* Interactions et micro-animations légères */
.stApp .stButton>button{transition:transform .16s ease,border-color .16s ease,box-shadow .16s ease!important}
.stApp .stButton>button:active{transform:translateY(0) scale(.985)!important}
.stApp [data-testid="stExpander"]{transition:border-color .2s,background .2s}
.stApp [data-testid="stExpander"]:hover{border-color:#366178!important}
.chat-empty{border:1px dashed #2b5063;border-radius:12px;padding:1.25rem 1.4rem;background:linear-gradient(115deg,#0e1c2d,#102637);display:flex;flex-direction:column;gap:8px;margin-top:12px}
.chat-empty b{color:#ecf5ff;font-size:1rem}.chat-empty span{color:#a9bfd0;font-size:.89rem;line-height:1.5}
@keyframes message-enter{from{opacity:0;transform:translateY(9px)}to{opacity:1;transform:translateY(0)}}
@media(max-width:900px){.block-container{padding:1rem 1rem 2rem!important}.stApp [data-testid="stBottomBlockContainer"]{padding:8px 1rem!important}}
@media(prefers-reduced-motion:reduce){.stApp [data-testid="stChatMessage"]{animation:none!important}}


/* V3.3 · Mission cockpit — taille lisible, espaces maîtrisés, mouvement utile */
html{font-size:18px!important}
.stApp{background:radial-gradient(ellipse 60% 28% at 84% 0%,rgba(34,109,157,.22),transparent 80%),#080f1b!important}
.block-container{max-width:1920px!important;padding:1.25rem 2.6rem 2.8rem!important}
[data-testid="stSidebar"]{min-width:272px!important;max-width:310px!important}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] label{font-size:.88rem!important}
.stApp h1{font-size:2.65rem!important}
.stApp h2{font-size:2rem!important}
.stApp h3{font-size:1.4rem!important}
.stApp .stButton>button,.stApp .stLinkButton>a{min-height:2.65rem!important;font-size:.92rem!important;font-weight:600!important}
.stApp [data-testid="stChatMessage"]{padding:1.25rem 1.5rem!important;border-radius:18px!important;box-shadow:0 14px 40px rgba(0,0,0,.15)!important}
.stApp [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
.stApp [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li{font-size:1.04rem!important;line-height:1.8!important}
.stApp [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h3{font-size:1.25rem!important}
.stApp [data-testid="stChatInput"] textarea{font-size:1rem!important;min-height:56px!important}
.stApp [data-testid="stChatInput"]{border-radius:15px!important}
.stApp [data-testid="stBottomBlockContainer"]{max-width:1920px!important;padding:10px 2.6rem 18px!important}
.stApp [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]){background:linear-gradient(110deg,#152c42,#102337)!important;border-color:#31516b!important}
.stApp [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]){background:linear-gradient(120deg,#102238,#101b30)!important;border-color:#2b5b62!important}
.stApp [data-testid="stExpander"]{border-radius:13px!important}
.side-links-title{font:700 .69rem 'IBM Plex Mono',monospace;letter-spacing:.15em;color:#7ce5d3;margin:12px 0 8px}
.stApp .stButton>button:hover,.stApp .stLinkButton>a:hover{transform:translateY(-2px)!important;box-shadow:0 8px 24px rgba(43,155,178,.15)!important;border-color:#47dec1!important}
.stApp [data-testid="stChatMessage"]{animation:slide-reveal .36s cubic-bezier(.2,.8,.2,1) both!important}
.stApp [data-testid="stChatMessage"]:hover{transform:translateY(-1px);border-color:#3d8b91!important}
.stApp [data-testid="stMetric"]{transition:transform .2s,box-shadow .2s}
.stApp [data-testid="stMetric"]:hover{transform:translateY(-3px)}
@keyframes slide-reveal{from{opacity:0;transform:translateY(12px) scale(.995)}to{opacity:1;transform:translateY(0) scale(1)}}
@media(min-width:1400px){.stApp [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"]{max-width:100%!important}}
@media(max-width:900px){html{font-size:16px!important}.block-container{padding:1rem 1rem 2.5rem!important}.stApp [data-testid="stBottomBlockContainer"]{padding:8px 1rem!important}[data-testid="stSidebar"]{min-width:220px!important}}
@media(prefers-reduced-motion:reduce){.stApp [data-testid="stChatMessage"]{animation:none!important}.stApp *{transition:none!important}}


/* V3.4 : micro-interactions et graphiques accessibles */
[data-testid="stPlotlyChart"] { border: 1px solid rgba(111,154,191,.12); border-radius: 16px; overflow:hidden; transition: border-color .25s ease, box-shadow .25s ease; }
[data-testid="stPlotlyChart"]:hover { border-color: rgba(73,217,182,.4); box-shadow: 0 12px 36px rgba(0,0,0,.18); }
[data-testid="stMetric"] {transition: transform .24s ease;}
[data-testid="stMetric"]:hover {transform: translateY(-3px);}
@media(prefers-reduced-motion:reduce){[data-testid="stPlotlyChart"],[data-testid="stMetric"]{transition:none!important;transform:none!important;}}


/* V3.5 — continuité du thème sombre, y compris widgets et menus portails. */
html,body,.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"],[data-testid="stMainBlockContainer"]{background-color:#070d17!important;color:#e7eef8!important}
[data-testid="stSidebarContent"]{background:#0b1524!important}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{gap:.65rem}
[data-testid="stSidebar"] [role="radiogroup"] label{font-size:.9rem!important}
[data-testid="stSidebar"] .stButton>button,[data-testid="stSidebar"] .stLinkButton>a{width:100%;background:#12243a!important;color:#d7e8f5!important;border:1px solid #2d4861!important;border-radius:10px!important}
[data-testid="stSidebar"] .stLinkButton>a:hover{border-color:#49d9b6!important;color:#49d9b6!important}
[data-testid="stTabs"],[data-testid="stTabs"] [role="tablist"],[data-testid="stTabs"] [role="tabpanel"],
[data-testid="stDataFrame"],[data-testid="stDataEditor"],[data-testid="stTable"],[data-testid="stMetric"],
[data-testid="stForm"],[data-testid="stDialog"],[data-testid="stPopoverBody"],[data-testid="stPopover"],
[data-testid="stFileUploader"],[data-testid="stFileUploaderDropzone"],[data-testid="stExpanderDetails"]{background-color:#0e1b2c!important;color:#e7eef8!important;border-color:#2b455d!important}
[data-baseweb="popover"],[data-baseweb="popover"]>div,[data-baseweb="menu"],[data-baseweb="listbox"],
[data-baseweb="calendar"],[data-baseweb="datepicker"],[data-baseweb="tooltip"]{background:#12243a!important;color:#e7eef8!important;border-color:#31516c!important}
[data-baseweb="popover"] *,[data-baseweb="menu"] *,[data-baseweb="listbox"] *{color:#e7eef8!important}
[data-testid="stPlotlyChart"]{background:transparent!important}
[data-testid="stMarkdownContainer"] table{background:#0e1b2c!important;color:#e7eef8!important}
[data-testid="stMarkdownContainer"] th{background:#19304a!important;color:#e7eef8!important}
[data-testid="stMarkdownContainer"] td{background:#0e1b2c!important;color:#dce9f5!important;border-color:#28415b!important}
[data-testid="stMarkdownContainer"] blockquote{background:#102337!important;border-left:3px solid #49d9b6!important;padding:8px 15px}
[data-testid="stDownloadButton"] button{background:#14334b!important}
.side-intro{background:linear-gradient(130deg,#123043,#101c33);border:1px solid #2b5165;border-radius:11px;padding:12px 13px;color:#8debd9;font:600 .62rem 'IBM Plex Mono',monospace;letter-spacing:.06em;margin:13px 0 3px}
.side-intro b{float:right;color:#b9d2e5}.side-intro p{color:#a9bfd1;font-size:.76rem;margin:8px 0 0;font-family:'DM Sans',sans-serif;letter-spacing:0}
.live-dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:#49d9b6;box-shadow:0 0 10px rgba(73,217,182,.7);margin-right:6px}
.side-status{padding:12px 13px;background:#102338;border:1px solid #274459;border-radius:11px;font-size:.8rem;color:#d4e6f3}
.side-status small{display:block;margin-top:5px;color:#89a7bd;font-size:.7rem}
.side-author{display:flex;gap:10px;align-items:center;padding:12px 10px;background:#102036;border:1px solid #254159;border-radius:11px;margin:5px 0}
.side-author .avatar{display:grid;place-items:center;flex-shrink:0;width:35px;height:35px;border-radius:10px;background:linear-gradient(135deg,#1c7f82,#3053a3);font-weight:800;color:white}
.side-author b{display:block;color:#edf6ff;font-size:.8rem;line-height:1.4}
.side-author small{display:block;color:#9bb2c6;font-size:.7rem;line-height:1.4;margin-top:2px}
.copilot-capabilities{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}
.copilot-capabilities span{background:#122b3d;border:1px solid #2a5260;border-radius:9px;padding:7px 10px;color:#a6e4da;font-size:.75rem}
@media(max-width:680px){.copilot-capabilities span{font-size:.68rem}.side-author{padding:9px}}



/* V3.6 : mise en page plus lisible, sidebar sans gros ronds blancs */
[data-testid="stSidebar"]{min-width:310px!important;max-width:345px!important}
[data-testid="stSidebar"] [role="radiogroup"] label{font-size:1.02rem!important;min-height:46px;padding:10px 12px!important}
[data-testid="stSidebar"] [role="radiogroup"] label p{font-size:1.02rem!important;font-weight:600!important}
[data-testid="stSidebar"] [role="radiogroup"] label [data-baseweb="radio"]>div:first-child{transform:scale(.72);opacity:.65}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) [data-baseweb="radio"]>div:first-child{opacity:1}
[data-testid="stSidebar"] .side-status{margin:14px 0 16px!important;line-height:1.5!important}
[data-testid="stSidebar"] .side-author{margin-top:10px!important;margin-bottom:12px!important}
[data-testid="stSidebar"] .side-author .avatar{font-size:1.1rem!important;min-width:48px!important;min-height:48px!important}
[data-testid="stSidebar"] .side-author small{line-height:1.5!important}
[data-testid="stSidebar"] .stButton button,[data-testid="stSidebar"] [data-testid="stLinkButton"] a{min-height:44px!important}
.question-category{font-size:1.02rem;font-weight:800;color:#73ead5;letter-spacing:.02em;margin:16px 0 8px;padding:7px 0;border-bottom:1px solid #263d50}
[data-testid="stExpander"]:has(.question-category){border-color:#315b67!important;background:linear-gradient(145deg,#0f2034,#10192a)!important}
[data-testid="stExpander"]:has(.question-category) button{font-size:.98rem!important;min-height:46px!important;text-align:left!important;white-space:normal!important;transition:transform .2s,background .2s,box-shadow .2s!important}
[data-testid="stExpander"]:has(.question-category) button:hover{transform:translateY(-2px);box-shadow:0 9px 22px rgba(33,208,188,.13)!important;background:#1c3c4e!important}
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"]{font-size:1.06rem!important}
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p{line-height:1.75!important}
[data-testid="stChatInput"]{border:1px solid #2d5368!important;background:#102036!important}
[data-testid="stChatInput"]:focus-within{border-color:#48dcbf!important;box-shadow:0 0 0 3px rgba(72,220,191,.14)!important}
.stApp [data-testid="stButton"] button{transition:transform .2s ease,box-shadow .2s ease,border-color .2s ease!important}
.stApp [data-testid="stButton"] button:hover{transform:translateY(-2px);box-shadow:0 9px 24px rgba(25,150,159,.13)}
.stApp [data-testid="stMarkdownContainer"] a{color:#6de9d4!important}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{gap:.5rem!important}
@media(max-width:900px){[data-testid="stSidebar"]{min-width:unset!important;max-width:unset!important}}
@media(prefers-reduced-motion:reduce){.stApp [data-testid="stButton"] button,[data-testid="stExpander"]:has(.question-category) button{transition:none!important;transform:none!important}}

</style>""",
    unsafe_allow_html=True,
)


# ───────────────────────────── données ─────────────────────────────


def fmt(v, digits: int = 0) -> str:
    if v is None:
        return "N/D"
    return f"{v:,.{digits}f}".replace(",", " ").replace(".", ",")


def eur_m(v) -> str:
    return "N/D" if v is None else f"{fmt(v / 1e6, 1)} M€"


def esc(s) -> str:
    return html.escape(str(s))


def norm(s: str) -> str:
    return "".join(
        c
        for c in unicodedata.normalize("NFKD", s.lower())
        if not unicodedata.combining(c)
    )


def enrich(m: dict) -> dict:
    basket = m.get("basket")
    m["exposure"] = m["missing"] * basket if basket is not None else None
    m["known_rev"] = m.get(
        "known_rev", m["known"] * basket if basket is not None else None
    )
    return m


def metrics_from_reference(scenario: str) -> dict:
    r = REFERENCE[scenario]
    return enrich(
        {
            **r,
            "known": r["orders"] - r["missing"],
            "missing_pct": 100 * r["missing"] / r["orders"],
            "complete_pct": 100 * (r["orders"] - r["missing"]) / r["orders"],
            "late_pct": 100 * r["late"] / r["deliveries"],
        }
    )


def metrics_from_db(scenario: str) -> dict:
    from src.assistant.kpi import delivery, overview

    c, l = overview(scenario), delivery(scenario)
    orders, missing = int(c["commandes"]), int(c["montants_manquants"])
    deliveries, late = int(l["livraisons_evaluables"]), int(l["retards"])
    if (
        orders <= 0
        or deliveries <= 0
        or c["panier_moyen"] is None
        or c.get("chiffre_affaires_commandes") is None
        or not (0 <= missing <= orders)
        or not (0 <= late <= deliveries)
    ):
        raise ValueError(
            f"KPI incomplets ou incohérents pour le scénario {scenario} : vérifie le DWH."
        )
    return enrich(
        {
            "orders": orders,
            "missing": missing,
            "known": orders - missing,
            "basket": float(c["panier_moyen"]),
            "deliveries": deliveries,
            "late": late,
            "known_rev": float(c["chiffre_affaires_commandes"]),
            "missing_pct": 100 * missing / orders if orders else None,
            "complete_pct": 100 * (orders - missing) / orders if orders else None,
            "late_pct": 100 * late / deliveries if deliveries else None,
        }
    )


def health(d: dict) -> dict:
    """Indice pédagogique : 60 % complétude, 40 % ponctualité. Pondérations volontairement simples et visibles."""
    comp = max(0.0, 100 - 5 * d["missing_pct"])
    punct = max(0.0, 100 - 2 * d["late_pct"])
    return {
        "score": round(0.6 * comp + 0.4 * punct, 1),
        "comp": comp,
        "punct": punct,
        "lost_missing": 0.6 * (100 - comp),
        "lost_late": 0.4 * (100 - punct),
    }


def gate(d: dict, th: dict) -> dict:
    m, l = d["missing_pct"], d["late_pct"]
    checks = [
        (
            "Montants renseignés",
            f"{fmt(m, 2)} % absents",
            "go" if m <= th["m_warn"] else "warn" if m <= th["m_fail"] else "stop",
            f"Seuils : réserves au-delà de {th['m_warn']} %, blocage au-delà de {th['m_fail']} %",
        ),
        (
            "Ponctualité des livraisons",
            f"{fmt(l, 2)} % en retard",
            "go" if l <= th["l_warn"] else "warn" if l <= th["l_fail"] else "stop",
            f"Seuils : réserves au-delà de {th['l_warn']} %, blocage au-delà de {th['l_fail']} %",
        ),
    ]
    order = {"go": 0, "warn": 1, "stop": 2}
    return {
        "checks": checks,
        "overall": max((c[2] for c in checks), key=lambda s: order[s]),
    }


VERDICT = {
    "go": ("Publiable", "v-go"),
    "warn": ("Publiable avec réserves", "v-warn"),
    "stop": ("À bloquer", "v-stop"),
}


def score_color(s: float) -> str:
    return MINT if s >= 80 else AMBER if s >= 65 else CORAL


def recommendations(d: dict) -> list[dict]:
    recs = []
    if d["missing_pct"] >= 8:
        recs.append(
            dict(
                t="Suspendre la publication du chiffre d'affaires mensuel",
                sev="high",
                impact=3,
                effort=1,
                why=f"{fmt(d['missing_pct'], 1)} % des commandes n'ont pas de montant : le total publié serait trompeur tant que la complétude n'est pas rétablie.",
            )
        )
    if d["missing_pct"] >= 1:
        sev = "high" if d["missing_pct"] >= 3 else "mid"
        recs.append(
            dict(
                t="Comparer les commandes avec et sans montant",
                sev=sev,
                impact=3,
                effort=1,
                why="Magasin, canal, période, catégorie : si les montants manquent au hasard, le panier moyen reste exploitable. Sinon, il est biaisé.",
            )
        )
        recs.append(
            dict(
                t="Auditer la chaîne de collecte des montants",
                sev=sev,
                impact=3,
                effort=2,
                why="Remonter l'ETL : champ vide à la source, perte à la jointure ou transformation défaillante ?",
            )
        )
        recs.append(
            dict(
                t="Publier le chiffre d'affaires avec son taux de couverture",
                sev="mid",
                impact=2,
                effort=1,
                why="Afficher « CA sur X % des commandes » évite de présenter une estimation comme un fait.",
            )
        )
    if d["late_pct"] > 10:
        recs.append(
            dict(
                t="Segmenter les retards par transporteur et par zone",
                sev="mid",
                impact=2,
                effort=1,
                why=f"{fmt(d['late_pct'], 1)} % de retards : les agrégats ne disent pas où le problème se concentre.",
            )
        )
    if not recs:
        recs.append(
            dict(
                t="Maintenir la surveillance",
                sev="low",
                impact=1,
                effort=1,
                why="Aucun seuil dépassé : conserver les contrôles automatiques.",
            )
        )
    return sorted(recs, key=lambda r: (-r["impact"], r["effort"]))


def headline(d: dict, allm: dict) -> tuple[str, str]:
    h = f"{fmt(d['missing_pct'], 0)} % des commandes n'ont pas de montant."
    sub = (
        f"Si leur panier ressemblait au panier moyen, environ {eur_m(d['exposure'])} de chiffre d'affaires resterait impossible à vérifier. "
        "Hypothèse à tester, pas un résultat."
    )
    if len({round(m["late_pct"], 6) for m in allm.values()}) == 1:
        sub += f" Les retards ({fmt(d['late_pct'], 1)} %) sont identiques dans les trois scénarios : aucun lien causal n'est établi entre les deux indicateurs."
    return h, sub


def monte_carlo(d: dict, sigma: float, n: int = 20000, seed: int = 7) -> np.ndarray:
    """Exposition (M€) si le panier des commandes sans montant est log-normal de moyenne 1× le panier connu."""
    rng = np.random.default_rng(seed)
    ratio = rng.lognormal(mean=-0.5 * sigma**2, sigma=sigma, size=n)
    # Un tirage représente le panier moyen inconnu du groupe, pas chaque commande.
    # Cette distribution est un scénario subjectif, sans calibration statistique.
    return d["missing"] * d["basket"] * ratio / 1e6


def memo_markdown(d: dict, scenario: str, g: dict, hs: dict, recs: list[dict]) -> str:
    q = np.percentile(monte_carlo(d, 0.15), [5, 95])
    lines = [
        f"# Note de décision — ConsultAI 360 ({date.today():%d/%m/%Y})",
        "",
        f"**Scénario analysé :** {SCENARIO_LABEL[scenario]}",
        f"**Verdict :** {VERDICT[g['overall']][0]}  |  **Indice de santé :** {hs['score']:.0f}/100",
        "",
        "## Faits vérifiés",
        f"- {fmt(d['orders'])} commandes ; {fmt(d['missing'])} sans montant ({fmt(d['missing_pct'], 2)} %).",
        f"- Panier moyen sur montants connus : {fmt(d['basket'], 2)} €.",
        f"- {fmt(d['late'])} retards sur {fmt(d['deliveries'])} livraisons évaluables ({fmt(d['late_pct'], 2)} %).",
        "",
        "## Hypothèse (non mesurée)",
        f"- Exposition si panier identique : {eur_m(d['exposure'])} ; fourchette illustrative P5–P95 (hypothèse log-normale, sigma=0,15) : {fmt(q[0], 1)} à {fmt(q[1], 1)} M€.",
        "",
        "## Contrôles",
    ]
    lines += [f"- {c[0]} : {c[1]} → {VERDICT[c[2]][0]}" for c in g["checks"]]
    lines += ["", "## Actions recommandées (par priorité)"] + [
        f"{i}. **{r['t']}** — {r['why']}" for i, r in enumerate(recs, 1)
    ]
    lines += [
        "",
        "## Limites",
        "Données synthétiques. Aucun effet causal sur les ventes n'est démontré. Les chiffres viennent de calculs Python/SQL, pas d'un modèle de langage.",
    ]
    return "\n".join(lines)


# ───────────────────────────── composants visuels ─────────────────────────────


def plot_style(fig: go.Figure, height: int = 300) -> go.Figure:
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#b4c8d8", family="DM Sans", size=12),
        margin=dict(l=8, r=8, t=24, b=8),
        hoverlabel=dict(bgcolor="#14263a", font_color="#fff", bordercolor="#2c4660"),
        legend=dict(orientation="h", y=-0.18),
        transition=dict(duration=500, easing="cubic-in-out"),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor="#344b60")
    fig.update_yaxes(gridcolor="#1f3247", zeroline=False)
    return fig


def page_head(title: str, text: str) -> None:
    st.markdown(
        f'<div class="pagehead"><h2>{esc(title)}</h2><p>{esc(text)}</p></div>',
        unsafe_allow_html=True,
    )


def h3(text: str) -> None:
    st.markdown(f'<div class="h3">{esc(text)}</div>', unsafe_allow_html=True)


def ledger(cells: list[tuple]) -> None:
    out = ""
    for i, (lab, val, note, pct, color) in enumerate(cells):
        bar = (
            f'<div class="bar"><i style="width:{min(max(pct, 0), 100):.1f}%;background:{color};animation-delay:{i * 90}ms"></i></div>'
            if pct is not None
            else ""
        )
        out += f'<div class="cell fx" style="--i:{i}"><div class="lab">{esc(lab)}</div><div class="val">{esc(val)}</div><div class="note">{esc(note)}</div>{bar}</div>'
    st.markdown(f'<div class="ledger">{out}</div>', unsafe_allow_html=True)


def mini(cells: list[tuple]) -> None:
    out = "".join(
        f'<div class="fx" style="--i:{i}"><b>{esc(v)}</b><span>{esc(l)}</span></div>'
        for i, (l, v) in enumerate(cells)
    )
    st.markdown(f'<div class="mini">{out}</div>', unsafe_allow_html=True)


def rec_rows(recs: list[dict]) -> None:
    lvl = {1: "faible", 2: "moyen", 3: "fort"}
    for i, r in enumerate(recs):
        st.markdown(
            f'<div class="row fx {r["sev"]}" style="--i:{i}"><div><div class="row-title">{esc(r["t"])}</div><div class="row-why">{esc(r["why"])}</div></div>'
            f'<div class="pills"><span class="pill">Impact {lvl[r["impact"]]}</span><span class="pill soft">Effort {lvl[r["effort"]]}</span></div></div>',
            unsafe_allow_html=True,
        )


def table(
    headers: list[str], rows: list[list[str]], selected: int | None = None
) -> None:
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "".join(
        f'<tr class="{"sel" if i == selected else ""}">'
        + "".join(f"<td>{c}</td>" for c in r)
        + "</tr>"
        for i, r in enumerate(rows)
    )
    st.markdown(
        f'<div class="tblwrap"><table class="tbl"><tr>{head}</tr>{body}</table></div>',
        unsafe_allow_html=True,
    )


def verdict_badge(g: dict) -> str:
    label, cls = VERDICT[g["overall"]]
    return f'<span class="verdict {cls}">{label}</span>'


# ───────────────────────────── copilote : outils déterministes puis rédaction ─────────────────────────────

SC_WORDS = {
    "low": r"\b(low|faible|bas)\b",
    "medium": r"\b(medium|moyen|median)\b",
    "critical": r"\b(critical|critique|pire)\b",
}
INTENTS = {
    "greet": ["bonjour", "salut", "hello", "coucou", "merci"],
    "help": [
        "aide",
        "que sais-tu",
        "que peux-tu",
        "tu sais faire",
        "capacite",
        "qui es-tu",
        "presente",
    ],
    "compare": ["compar", "scenarios", "difference", "versus", " vs ", "ecart entre"],
    "solve": [
        "a partir de quel",
        "quel taux",
        "pour atteindre",
        "point de bascule",
        "tolere",
        "quel seuil",
        "jusqu'ou",
        "combien de montants",
        "limite acceptable",
    ],
    "simulate": [
        "simul",
        "et si",
        "passe a",
        "passait",
        "manquaient",
        "manquait",
        "augmente",
        "baisse",
        "hypothe",
        "scenario catastrophe",
    ],
    "exposure": [
        " ca ",
        "revenu",
        "perte",
        "perdu",
        "expos",
        "euros",
        "argent",
        "incertitude",
        "intervalle",
        "fourchette",
    ],
    "basket": ["panier"],
    "late": ["retard", "livraison", "transporteur", "logisti", "ponctualite"],
    "risk": ["risque", "qualite", "probleme", "priorite", "gravite", "danger"],
    "actions": [
        "action",
        "recommand",
        "que faire",
        "plan",
        "conseil",
        "ameliorer",
        "corriger",
        "prochaine etape",
    ],
    "score": ["score", "sante", "indice"],
    "gate": [
        "publier",
        "publication",
        "valider",
        "decision",
        "bloquer",
        "fiable",
        "se fier",
        "utilisable",
        "verdict",
    ],
    "why": ["pourquoi", "explique", "justifie", "d'ou vient", "comment est calcule"],
    "glossary": [
        "c'est quoi",
        "definition",
        "signifie",
        "completude",
        "evaluable",
        "mnar",
        "mcar",
        "mar ",
    ],
    "memo": [
        "memo",
        "synthese",
        "resume",
        "rapport",
        "brief",
        "note de decision",
        "redige",
        "ecris",
    ],
    "method": [
        "methode",
        "hallucin",
        "limite",
        "llm",
        "ollama",
        "modele",
        "comment tu",
        "tu calcules",
        "source",
    ],
}
KIND = {
    "compare": "Calcul vérifié",
    "basket": "Calcul vérifié",
    "late": "Calcul vérifié",
    "risk": "Calcul vérifié",
    "actions": "Règles de priorisation",
    "score": "Calcul vérifié",
    "gate": "Règle de décision",
    "why": "Calcul vérifié",
    "simulate": "Hypothèse",
    "exposure": "Hypothèse",
    "solve": "Hypothèse",
    "memo": "Note générée",
    "glossary": "Définition",
    "method": "Information",
    "help": "Information",
    "greet": "Information",
}
FOLLOWUPS = {
    "compare": [
        "Et si 15 % des montants manquaient ?",
        "À partir de quel taux faut-il bloquer le chiffre d'affaires ?",
        "Que faire en priorité ?",
    ],
    "simulate": [
        "Et avec un panier manquant à 1,3× ?",
        "Quel taux pour atteindre 10 M€ d'exposition ?",
        "Peut-on publier le chiffre d'affaires ?",
    ],
    "exposure": [
        "Compare les trois scénarios",
        "Et si 15 % des montants manquaient ?",
        "Rédige une note de décision",
    ],
    "solve": [
        "Et pour le scénario critique ?",
        "Peut-on publier le chiffre d'affaires ?",
        "Que faire en priorité ?",
    ],
    "basket": [
        "Combien de chiffre d'affaires est exposé ?",
        "C'est quoi MCAR et MNAR ?",
        "Que faire en priorité ?",
    ],
    "late": [
        "Les retards dépendent-ils du scénario ?",
        "Que faire en priorité ?",
        "Rédige une note de décision",
    ],
    "risk": [
        "Que faire en priorité ?",
        "Pourquoi ce verdict ?",
        "Combien de chiffre d'affaires est exposé ?",
    ],
    "actions": [
        "Rédige une note de décision",
        "Peut-on publier le chiffre d'affaires ?",
        "Compare les trois scénarios",
    ],
    "score": [
        "Pourquoi ce verdict ?",
        "Compare les trois scénarios",
        "Que faire en priorité ?",
    ],
    "gate": [
        "Pourquoi ce verdict ?",
        "À partir de quel taux faut-il bloquer le chiffre d'affaires ?",
        "Rédige une note de décision",
    ],
    "why": [
        "Que faire en priorité ?",
        "Et pour le scénario critique ?",
        "Rédige une note de décision",
    ],
}
DEFAULT_FOLLOW = [
    "Compare les trois scénarios",
    "Combien de chiffre d'affaires est exposé ?",
    "Peut-on publier le chiffre d'affaires ?",
]
CATALOG = [
    "Compare les trois scénarios",
    "Et si 15 % des montants manquaient ?",
    "Combien de chiffre d'affaires est exposé ?",
    "Peut-on publier le chiffre d'affaires ?",
    "Que faire en priorité ?",
    "Rédige une note de décision",
    "Le panier moyen est-il fiable ?",
    "Que sait-on des retards de livraison ?",
    "À partir de quel taux faut-il bloquer ?",
    "Pourquoi ce score de santé ?",
]


def _num(m: re.Match | None) -> float | None:
    return float(m.group(1).replace(",", ".")) if m else None


def respond(question: str, scenario: str, allm: dict, th: dict, ctx: dict) -> dict:
    """Agent à outils : détecte les intentions et entités, appelle des outils Python, trace chaque appel."""
    question, corrections = correct_question(question)
    qn = " " + norm(question) + " "
    trace: list[str] = []
    if corrections:
        trace.append(
            "Correction de saisie : " + ", ".join(f"{a} → {b}" for a, b in corrections)
        )
    project = project_answer(question)
    if project is not None:
        return {
            "text": project["text"],
            "evidence": trace + project["evidence"],
            "intent": "projet_" + project["topic"].lower(),
            "kind": "Documentation",
            "followups": project["followups"],
            "scenario": scenario,
        }

    def T(call: str, result: str) -> None:
        trace.append(f"`{call}` → {result}")

    named = [s for s, rx in SC_WORDS.items() if re.search(rx, qn)]
    sc = named[0] if len(named) == 1 else scenario
    d = allm[sc]
    pct = _num(re.search(r"(\d+(?:[.,]\d+)?)\s*%", qn))
    mult = _num(re.search(r"(\d+(?:[.,]\d+)?)\s*(?:x|×|fois)(?:\s|$|\?)", qn))
    target = _num(re.search(r"(\d+(?:[.,]\d+)?)\s*(?:m€|meur|millions?|m\s)", qn))

    scores = {k: sum(1 for w in ws if w in qn) for k, ws in INTENTS.items()}
    if len(named) >= 2:
        scores["compare"] += 3
    if target is not None:
        scores["solve"] += 3
    if mult is not None:
        scores["simulate"] += 2
    if (
        pct is not None
        and scores["solve"] == 0
        and not any(w in qn for w in ("seuil", "bloqu"))
    ):
        scores["simulate"] += 2
    # Les formules ne doivent pas être supplantées par des mots génériques.
    if "panier" in qn and ("fiable" in qn or "biais" in qn):
        scores["basket"] += 4
    if "note de decision" in qn or "redige" in qn:
        scores["memo"] += 4
    if "priorite" in qn or "en premier" in qn:
        scores["actions"] += 4
    if "bloquer" in qn and ("quel taux" in qn or "partir" in qn):
        scores["solve"] += 4
    ranked = [k for k in sorted(scores, key=lambda k: -scores[k]) if scores[k] > 0]
    if not ranked and (named or pct or mult or target) and ctx.get("intent"):
        ranked = [ctx["intent"]]
        trace.append(
            f"Question de suivi : intention reprise de la réponse précédente ({ctx['intent']})"
        )
    # Les questions sur l'identité et le fonctionnement du copilote ne sont pas
    # des demandes de KPI : elles ont une réponse dédiée, même hors Ollama.
    identity_patterns = (
        r"\bqui es[ -]?tu\b",
        r"\btu es qui\b",
        r"\bqui etes[ -]?vous\b",
        r"\bpresente[ -]?toi\b",
        r"\bton role\b",
        r"\bque fais[ -]?tu\b",
        r"\bc.est quoi consultai\b",
        r"\bwhat are you\b",
    )
    if any(re.search(pattern, qn) for pattern in identity_patterns):
        return {
            "text": (
                "### Je suis le copilote d'analyse ConsultAI 360\n\n"
                "J'accompagne une **mission fictive de conseil Data & IA pour NexaRetail**. "
                "Je transforme les indicateurs vérifiés en diagnostics, scénarios et pistes d'action.\n\n"
                "**Ce que je peux faire**\n"
                "- Comparer les trois niveaux de qualité des données.\n"
                "- Simuler l'effet des montants manquants sur le chiffre d'affaires.\n"
                "- Expliquer les règles de publication et leurs seuils.\n"
                "- Proposer un plan d'investigation et une note de décision.\n\n"
                "**Mes limites :** les calculs viennent de SQL/Python, pas d'une génération de texte. "
                "Je ne connais pas les causes réelles des anomalies et je n'exécute aucune décision. "
                "Ollama, lorsqu'il est activé, peut reformuler les résultats, mais ne remplace pas les contrôles."
            ),
            "evidence": ["Réponse de présentation : aucune requête SQL nécessaire."],
            "intent": "identite",
            "kind": "Information",
            "followups": [
                "Compare les trois scénarios",
                "Que faire en priorité ?",
                "Rédige une note de décision",
            ],
            "scenario": sc,
        }
    if not ranked:
        close = (
            difflib.get_close_matches(question.strip(), CATALOG, n=3, cutoff=0.2)
            or CATALOG[:3]
        )
        return {
            "text": (
                "Je n'ai pas reconnu de question sur les données NexaRetail. Je sais comparer les scénarios, simuler un taux de montants absents, "
                "chiffrer l'exposition et son incertitude, trouver à partir de quel taux bloquer, expliquer un verdict et rédiger une note.\n\n"
                "Tu voulais peut-être demander :"
            ),
            "evidence": [],
            "intent": "aucune",
            "kind": "Information",
            "followups": close,
            "scenario": sc,
        }
    picks = ranked[:1] + [
        k for k in ranked[1:2] if scores[k] >= 2 and scores[k] >= scores[ranked[0]] - 1
    ]
    hs, g, recs = health(d), gate(d, th), recommendations(d)
    formulas: list[str] = []
    parts: list[str] = []

    for intent in picks:
        if intent == "greet":
            parts.append(
                "Bonjour. Pose-moi une question sur la qualité des données NexaRetail, ou clique sur une suggestion."
            )
        elif intent == "help":
            parts.append(
                "Je fonctionne en deux temps : des outils Python calculent les chiffres, puis je les assemble. Je sais :\n"
                "- **comparer** les scénarios ;\n- **simuler** (« et si 15 % manquaient ? », « avec un panier à 1,3× ») ;\n"
                "- **chiffrer l'exposition** et son intervalle d'incertitude ;\n- trouver **à partir de quel taux bloquer**, ou quel taux atteint X M€ ;\n"
                "- **expliquer** un score ou un verdict, classer les **actions**, rédiger une **note de décision**.\n\n"
                "Je comprends les questions de suivi (« et pour critique ? »)."
            )
        elif intent == "compare":
            rows = [
                "| Scénario | Montants absents | Panier moyen | CA non vérifiable | Verdict | Indice |",
                "|---|---|---|---|---|---|",
            ]
            for s in SCENARIOS:
                m = allm[s]
                rows.append(
                    f"| {s.capitalize()} | {fmt(m['missing_pct'], 1)} % | {fmt(m['basket'], 2)} € | {eur_m(m['exposure'])} | {VERDICT[gate(m, th)['overall']][0]} | {health(m)['score']:.0f} |"
                )
                T(
                    f"kpis('{s}')",
                    f"{fmt(m['missing'])} absents, panier {fmt(m['basket'], 2)} €",
                )
            spread = allm["critical"]["basket"] - allm["low"]["basket"]
            ratio = allm["critical"]["exposure"] / allm["low"]["exposure"]
            parts.append(
                "\n".join(rows)
                + f"\n\nEntre faible et critique, le panier moyen ne bouge que de {fmt(spread, 2)} € mais l'exposition est multipliée par {fmt(ratio, 1)}. "
                "L'enjeu est la couverture des données, pas la valeur du panier. Les retards sont identiques : aucun effet logistique n'est démontré."
            )
        elif intent == "simulate":
            p = pct if pct is not None else ctx.get("pct", d["missing_pct"])
            r = mult if mult is not None else 1.0
            if not 0 <= p <= 100:
                parts.append("Le taux simulé doit être compris entre 0 et 100 %.")
                continue
            n = round(d["orders"] * p / 100)
            expo = n * d["basket"] * r
            documented = (d["orders"] - n) * d["basket"]
            share = 100 * expo / (expo + documented) if expo + documented else 0
            T(
                "simulate(taux, multiplicateur)",
                f"{fmt(p, 1)} %, {fmt(r, 2)}× → {fmt(n)} commandes, {eur_m(expo)}",
            )
            formulas.append(
                "exposition = commandes sans montant × panier connu × multiplicateur"
            )
            parts.append(
                f"À **{fmt(p, 1)} %** de montants absents (scénario {sc}), **{fmt(n)} commandes** n'auraient pas de montant, soit {fmt(n - d['missing'])} de plus que l'observé. "
                f"Avec un panier à {fmt(r, 2)}× le panier connu ({fmt(d['basket'], 2)} €), l'exposition est d'environ **{eur_m(expo)}**, "
                f"soit {fmt(share, 1)} % du chiffre d'affaires total hypothétique.\n\nC'est une hypothèse : la page Scenario Lab ajoute une simulation Monte Carlo."
            )
            ctx["pct"] = p
        elif intent == "exposure":
            q5, q50, q95 = np.percentile(monte_carlo(d, 0.15), [5, 50, 95])
            T(
                f"kpis('{sc}')",
                f"{fmt(d['missing'])} × {fmt(d['basket'], 2)} € = {eur_m(d['exposure'])}",
            )
            T(
                "monte_carlo(sigma=15 %, n=20 000)",
                f"P5 {fmt(q5, 1)} / P50 {fmt(q50, 1)} / P95 {fmt(q95, 1)} M€",
            )
            formulas.append(
                "panier des commandes sans montant ~ log-normale de moyenne 1× et dispersion 15 %"
            )
            parts.append(
                f"Dans le scénario {sc}, {fmt(d['missing'])} commandes n'ont pas de montant. À panier moyen, le chiffre d'affaires non vérifiable est d'environ **{eur_m(d['exposure'])}**. "
                f"Sous une hypothèse log-normale non calibrée (sigma=0,15), la fourchette P5–P95 va de **{fmt(q5, 1)} à {fmt(q95, 1)} M€**. Le CA documenté est de {eur_m(d['known_rev'])}.\n\n"
                "Ce n'est pas une perte : ces commandes existent, leur montant est absent."
            )
        elif intent == "solve":
            if target is not None:
                denom = d["orders"] * d["basket"] * (mult or 1.0)
                p = 100 * target * 1e6 / denom
                T(
                    "solve_rate(cible_M€)",
                    f"{fmt(target, 1)} M€ → {fmt(p, 2)} % de montants absents",
                )
                formulas.append(
                    "taux = cible ÷ (commandes × panier connu × multiplicateur)"
                )
                parts.append(
                    f"Pour atteindre **{fmt(target, 1)} M€** d'exposition dans le scénario {sc}, il faudrait environ **{fmt(p, 1)} %** de commandes sans montant"
                    + (
                        f", soit {fmt(d['orders'] * p / 100)} commandes."
                        if p <= 100
                        else ". C'est supérieur à 100 % : la cible dépasse le chiffre d'affaires total."
                    )
                    + f" Le scénario {sc} est à {fmt(d['missing_pct'], 1)} %."
                )
            else:
                nb = d["orders"] * th["m_fail"] / 100
                T(
                    "gate_threshold()",
                    f"blocage à {th['m_fail']} %, réserves à {th['m_warn']} %",
                )
                margin = th["m_fail"] - d["missing_pct"]
                parts.append(
                    f"Avec la politique actuelle, le blocage se déclenche **au-delà de {fmt(th['m_fail'], 1)} %** de montants absents, soit {fmt(nb)} commandes et {eur_m(nb * d['basket'])} d'exposition. "
                    f"Les réserves commencent à {fmt(th['m_warn'], 1)} %. Le scénario {sc} est à {fmt(d['missing_pct'], 1)} % : "
                    + (
                        f"il reste {fmt(margin, 1)} point(s) de marge avant le blocage."
                        if margin >= 0
                        else f"il dépasse le seuil de {fmt(-margin, 1)} point(s)."
                    )
                )
                formulas.append("seuils réglables dans Decision Gate")
        elif intent == "basket":
            T(
                f"kpis('{sc}')",
                f"AVG(order_total) = {fmt(d['basket'], 2)} € sur {fmt(d['known'])} commandes",
            )
            parts.append(
                f"Le panier moyen de **{fmt(d['basket'], 2)} €** est calculé sur {fmt(d['known'])} commandes avec montant ({fmt(d['complete_pct'], 1)} % du total). "
                "On ne peut pas l'étendre aux autres sans savoir pourquoi leurs montants manquent. Si l'absence est indépendante des valeurs (MCAR), l'estimation reste utilisable sous conditions ; "
                "si elle dépend de la valeur (MNAR), un biais est possible.\n\nTest à faire : comparer magasin, canal, période et catégorie entre commandes avec et sans montant."
            )
            formulas.append("AVG(order_total) hors NULL")
        elif intent == "late":
            T(
                f"kpis('{sc}')",
                f"{fmt(d['late'])} retards / {fmt(d['deliveries'])} évaluables",
            )
            same = len({round(m["late_pct"], 6) for m in allm.values()}) == 1
            parts.append(
                f"{fmt(d['late'])} livraisons sont en retard sur {fmt(d['deliveries'])} évaluables, soit **{fmt(d['late_pct'], 2)} %**. Le dénominateur n'est pas le nombre de commandes : "
                "seules les livraisons où date prévue et date réelle sont comparables comptent."
                + (
                    " Ce taux est identique dans les trois scénarios : aucun effet causal n'est démontré."
                    if same
                    else ""
                )
                + " Aucune cause n'est identifiable avec des agrégats : découper par transporteur, zone et période."
            )
            formulas.append("retards ÷ livraisons évaluables")
        elif intent == "risk":
            r = recs[0]
            parts.append(
                f"Le risque principal est l'absence de montants ({fmt(d['missing_pct'], 2)} % des commandes). Priorité : **{r['t'].lower()}**. {r['why']}\n\nIndice de santé : {hs['score']:.0f}/100."
            )
            T(f"recommendations('{sc}')", f"{len(recs)} actions, première : {r['t']}")
        elif intent == "actions":
            parts.append(
                "Actions classées par impact puis effort :\n\n"
                + "\n".join(
                    f"{i}. **{r['t']}** : {r['why']}" for i, r in enumerate(recs, 1)
                )
            )
            T(f"recommendations('{sc}')", f"{len(recs)} actions")
            formulas.append("tri : impact décroissant, effort croissant")
        elif intent in ("score", "why"):
            label = VERDICT[g["overall"]][0]
            T(
                f"health('{sc}')",
                f"{hs['score']:.0f}/100 (−{fmt(hs['lost_missing'], 1)} pts montants, −{fmt(hs['lost_late'], 1)} pts retards)",
            )
            T(f"gate('{sc}')", label)
            bad = [c for c in g["checks"] if c[2] != "go"]
            parts.append(
                f"Indice de santé **{hs['score']:.0f}/100** : en partant de 100, les montants absents coûtent **{fmt(hs['lost_missing'], 1)} points** et les retards **{fmt(hs['lost_late'], 1)} points**. "
                f"Verdict : **{label}**."
                + (
                    "\n\nPoints qui pèsent sur le verdict :\n"
                    + "\n".join(f"- {c[0]} : {c[1]} ({c[3].lower()})" for c in bad)
                    if bad
                    else " Aucun seuil n'est dépassé."
                )
                + "\n\nL'indice est pédagogique : 60 % complétude, 40 % ponctualité."
            )
            formulas += [
                "complétude = 100 − 5 × % absents",
                "ponctualité = 100 − 2 × % retards",
            ]
        elif intent == "gate":
            label = VERDICT[g["overall"]][0]
            T(f"gate('{sc}')", label)
            parts.append(
                f"Verdict de la porte qualité : **{label}**.\n\n"
                + "\n".join(
                    f"- {c[0]} : {c[1]}, {VERDICT[c[2]][0].lower()}. {c[3]}."
                    for c in g["checks"]
                )
            )
            formulas += [c[3] for c in g["checks"]]
        elif intent == "glossary":
            parts.append(
                "- **Complétude** : part des commandes dont le montant est renseigné.\n- **Livraison évaluable** : livraison où date prévue et date réelle sont comparables.\n"
                "- **MCAR** : l'absence ne dépend d'aucune valeur ; l'estimation peut rester non biaisée sous conditions.\n- **MAR** : l'absence dépend de variables observées (magasin, canal).\n"
                "- **MNAR** : l'absence dépend de la valeur manquante elle-même ; biais possible.\n- **CA non vérifiable** : commandes sans montant × panier connu, hypothèse de travail."
            )
        elif intent == "memo":
            parts.append(memo_markdown(d, sc, g, hs, recs))
            T(
                "memo_markdown()",
                "note générée à partir des KPI, du verdict et des actions",
            )
        elif intent == "method":
            parts.append(
                "Les chiffres viennent de Python/SQL ou d'une référence figée, jamais d'un modèle de langage. Ma réponse suit trois étapes : 1) détecter intention et paramètres ; "
                "2) appeler des outils déterministes (KPI, simulation, Monte Carlo, règles) ; 3) rédiger. Chaque appel est listé dans « Preuves et méthode ». "
                "Avec Ollama, le modèle reformule les résultats des outils et chaque nombre est recoupé : ceux qu'on ne retrouve pas sont signalés. Aucun mode ne prouve de causalité."
            )

    ctx.update(intent=picks[0], scenario=sc)
    return {
        "text": "\n\n---\n\n".join(parts),
        "evidence": trace + formulas,
        "intent": " + ".join(picks),
        "kind": KIND.get(picks[0], "Information"),
        "followups": FOLLOWUPS.get(picks[0], DEFAULT_FOLLOW),
        "scenario": sc,
    }


def _tokens(s: str) -> set[str]:
    return {
        re.sub(r"\D", "", t) for t in re.findall(r"\d[\d\s\u202f]*(?:[.,]\d+)?", s)
    } - {""}


def ollama_answer(question: str, allm: dict, history: list[dict], base: dict) -> dict:
    """Le modèle local ne calcule rien : il rédige à partir des résultats d'outils, puis chaque nombre est recoupé."""
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    model = os.getenv("CONSULTAI_OLLAMA_MODEL", "llama3.2:1b")
    facts = "\n".join(
        f"- {s}: commandes {fmt(m['orders'])}, montants absents {fmt(m['missing'])} ({fmt(m['missing_pct'], 2)} %), panier moyen {fmt(m['basket'], 2)} €, "
        f"retards {fmt(m['late'])} sur {fmt(m['deliveries'])} ({fmt(m['late_pct'], 2)} %), CA non vérifiable {eur_m(m['exposure'])}"
        for s, m in allm.items()
    )
    if base["intent"] == "aucune":
        return {
            **base,
            "evidence": base["evidence"]
            + [
                "Aucun outil vérifié pour cette question : reformulation LLM désactivée."
            ],
        }
    verified = base["text"]
    system = (
        "Tu es l'analyste de ConsultAI 360 (entreprise fictive NexaRetail, données synthétiques). Réponds en français, en 5 phrases maximum, avec un ton direct. "
        "Appuie-toi UNIQUEMENT sur les KPI et les RÉSULTATS VÉRIFIÉS ci-dessous. Ne change aucun chiffre, n'en invente aucun, ne conclus jamais à une causalité. "
        "Si les résultats ne répondent pas à la question, dis ce qui manque.\n\nKPI :\n"
        + facts
        + "\n\nRÉSULTATS VÉRIFIÉS :\n"
        + verified
    )
    msgs = (
        [{"role": "system", "content": system}]
        + [{"role": h["role"], "content": h["content"]} for h in history[-4:]]
        + [{"role": "user", "content": question}]
    )
    parsed = urlparse(host)
    if parsed.scheme not in ("http", "https") or parsed.hostname not in (
        "localhost",
        "127.0.0.1",
        "::1",
    ):
        raise ValueError(
            "Ollama doit utiliser une adresse locale (localhost ou 127.0.0.1)."
        )
    req = urllib.request.Request(
        host.rstrip("/") + "/api/chat",
        headers={"Content-Type": "application/json"},
        data=json.dumps(
            {
                "model": model,
                "stream": False,
                "options": {"temperature": 0.2},
                "messages": msgs,
            }
        ).encode(),
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        text = json.load(r)["message"]["content"]
    allowed = _tokens(facts + " " + verified)
    unknown = sorted(t for t in _tokens(text) if len(t) > 2 and t not in allowed)
    ev = base["evidence"] + [f"rédaction par le modèle local : {model}"]
    if unknown:
        ev.append(
            "nombres non retrouvés dans les résultats d'outils : " + ", ".join(unknown)
        )
        text = base["text"]
        ev.append("Reformulation rejetée : réponse déterministe utilisée à la place.")
    return {
        **base,
        "text": text,
        "evidence": ev,
        "intent": base["intent"] + " + ollama",
    }


def typing(text: str):
    for tok in re.split(r"(\s+)", text):
        yield tok
        if tok.strip():
            time.sleep(0.012)


# ───────────────────────────── barre latérale ─────────────────────────────

with st.sidebar:
    st.markdown(
        '<div class="brand"><i>◆</i><div>ConsultAI 360<small>INTELLIGENCE · DECISION · DATA</small></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="side-intro"><span class="live-dot"></span> ENVIRONNEMENT ANALYTIQUE <b>V3.6</b><p>Mission NexaRetail · cas fictif</p></div>',
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown(
        '<div class="side-links-title">◉ CONTEXTE DE LA MISSION</div>',
        unsafe_allow_html=True,
    )
    scenario = st.selectbox(
        "Scénario de données",
        SCENARIOS,
        index=1,
        format_func=lambda s: SCENARIO_LABEL[s],
    )
    demo = (
        True
        if PUBLIC
        else st.toggle(
            "Mode démonstration",
            value=False,
            help="Utilise les chiffres de référence, sans PostgreSQL.",
        )
    )
    st.caption(
        "Chiffres de référence figés" if demo else "PostgreSQL local, lecture seule"
    )
    st.divider()
    st.markdown(
        '<div class="side-links-title">✦ EXPLORER LA MISSION</div>',
        unsafe_allow_html=True,
    )
    page = st.radio(
        "Navigation",
        PAGES,
        format_func=lambda p: f"{PAGE_ICONS[p]}   {p}",
        label_visibility="collapsed",
    )
    st.divider()
    st.markdown(
        '<div class="side-status"><div><span class="live-dot"></span> <b>Lecture analytique</b></div><small>Calculs SQL/Python · aucune écriture en base</small><small>Cas fictif · données synthétiques · décisions non exécutées</small></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="side-links-title">✦ PROJET & PROFIL</div>', unsafe_allow_html=True
    )
    author = author_profile()
    st.markdown(
        f'<div class="side-author"><span class="avatar">CP</span><div><b>{esc(author["name"])}</b><small>{esc(author["role"])}</small></div></div>',
        unsafe_allow_html=True,
    )
    st.link_button("💻 Code source du GitHub", author["github"], **STRETCH)
    linkedin_url = author["linkedin"]
    if linkedin_url.startswith("https://www.linkedin.com/") or linkedin_url.startswith(
        "https://linkedin.com/"
    ):
        st.link_button(" 👔 LinkedIn | Profil", linkedin_url, **STRETCH)
    else:
        st.caption(" 📷 LinkedIn : https://www.linkedin.com/in/can-pekgoz/")
    if st.get_option("theme.base") != "dark":
        with st.expander("Réglage d’affichage (optionnel)"):
            st.caption(
                "Le thème natif est clair. Pour un rendu homogène, copier le fichier .streamlit/config.toml fourni, arrêter Streamlit et relancer l’application."
            )

try:
    allm = {
        s: (metrics_from_reference(s) if demo else metrics_from_db(s))
        for s in SCENARIOS
    }
except Exception as exc:
    st.error(
        "Connexion PostgreSQL indisponible. Active le mode démonstration dans le menu latéral."
    )
    with st.expander("Détail technique"):
        st.code(f"{type(exc).__name__}: {exc}")
    st.stop()

d = allm[scenario]
hs = health(d)
TH = st.session_state.setdefault(
    "th", {"m_warn": 3, "m_fail": 8, "l_warn": 10, "l_fail": 20}
)
g = gate(d, TH)
recs = recommendations(d)
source_chip = "Chiffres de référence" if demo else "PostgreSQL en direct"


# ───────────────────────────── modules ─────────────────────────────


def evidence_payload(d: dict, scenario: str, demo: bool, th: dict) -> dict:
    return {
        "scenario": scenario,
        "source": "reference_frozen" if demo else "postgresql_read_only",
        "observed": {
            k: d[k]
            for k in (
                "orders",
                "missing",
                "known",
                "basket",
                "deliveries",
                "late",
                "missing_pct",
                "late_pct",
                "known_rev",
            )
        },
        "hypothesis": {
            "unverified_revenue": d["exposure"],
            "method": "missing_orders * observed_basket",
            "not_measured": True,
        },
        "policy": dict(th),
        "verdict": gate(d, th)["overall"],
        "limits": [
            "synthetic_data",
            "no_causal_inference",
            "missing_values_not_recovered",
        ],
    }


def action_registry(scenario: str, recs: list[dict]) -> None:
    st.markdown(
        '<div class="ops-banner"><b>Plan d’action proposé, non exécuté.</b> Choisis un statut et un responsable pour chaque investigation. Les modifications restent dans cette session et peuvent être exportées ; elles ne modifient pas PostgreSQL.</div>',
        unsafe_allow_html=True,
    )
    rows = []
    for i, r in enumerate(recs, 1):
        with st.container(border=True):
            st.markdown(
                f'<div class="kicker">TASK-{i:02d} · {esc(scenario)}</div><b>{esc(r["t"])}</b><br><span style="color:#9bb0c3;font-size:.86rem">{esc(r["why"])}</span>',
                unsafe_allow_html=True,
            )
            a, b, c = st.columns([1, 1, 1.6])
            status = a.selectbox(
                "Statut",
                ["À instruire", "En cours", "Bloqué", "Terminé"],
                key=f"act_{scenario}_{i}",
            )
            owner = b.text_input(
                "Responsable", value="À attribuer", key=f"owner_{scenario}_{i}"
            )
            note = c.text_input(
                "Preuve / prochaine étape",
                placeholder="Ex. requête de contrôle à créer",
                key=f"note_{scenario}_{i}",
            )
        rows.append(
            {
                "id": f"TASK-{i:02d}",
                "scenario": scenario,
                "action": r["t"],
                "status": status,
                "owner": owner,
                "note": note,
                "impact": r["impact"],
                "effort": r["effort"],
            }
        )
    done = sum(1 for x in rows if x["status"] == "Terminé")
    st.progress(
        done / len(rows) if rows else 0,
        text=f"{done} action(s) terminée(s) sur {len(rows)}",
    )
    st.download_button(
        "Exporter le registre d’actions (CSV)",
        pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig"),
        file_name=f"consultai_actions_{scenario}.csv",
        mime="text/csv",
        type="primary",
    )


def plot_matrix(allm: dict, scenario: str) -> go.Figure:
    fig = go.Figure()
    for s in SCENARIOS:
        m = allm[s]
        fig.add_trace(
            go.Scatter(
                x=[m["missing_pct"]],
                y=[m["exposure"] / 1e6],
                mode="markers+text",
                name=s.capitalize(),
                text=[s.capitalize()],
                textposition="top center",
                textfont=dict(color="#dbe7f3"),
                marker=dict(
                    size=26 if s == scenario else 16,
                    color=MINT if s == scenario else MIST,
                    line=dict(width=2, color="#d8eaf3"),
                ),
                hovertemplate="%{text}<br>Montants absents : %{x:.1f} %<br>Exposition hypothétique : %{y:.2f} M€<extra></extra>",
            )
        )
    plot_style(fig, 320).update_layout(
        xaxis_title="Commandes sans montant (%)",
        yaxis_title="Exposition hypothétique (M€)",
        showlegend=False,
    )
    fig.update_xaxes(range=[0, 14]).update_yaxes(
        range=[0, max(allm[s]["exposure"] for s in SCENARIOS) / 1e6 * 1.3]
    )
    return fig


# ───────────────────── observatoire : comparaisons vérifiables ─────────────────────


def chart_exposure_waterfall(d: dict) -> go.Figure:
    """Pont entre CA documenté et CA hypothétique, sans présenter une estimation comme un fait."""
    known = d["known_rev"] / 1e6
    assumed = d["exposure"] / 1e6
    fig = go.Figure(
        go.Waterfall(
            x=["CA documenté", "Montants absents (hypothèse)", "Total hypothétique"],
            y=[known, assumed, 0],
            measure=["absolute", "relative", "total"],
            connector={"line": {"color": "#486077", "dash": "dot"}},
            increasing={"marker": {"color": MINT}},
            totals={"marker": {"color": COBALT}},
            text=[
                f"{known:.2f} M€",
                f"+ {assumed:.2f} M€",
                f"{known + assumed:.2f} M€",
            ],
            textposition="outside",
            textfont={"color": "#e7eef8"},
            hovertemplate="%{x}<br>%{y:.2f} M€<extra></extra>",
        )
    )
    plot_style(fig, 380).update_layout(
        showlegend=False,
        yaxis_title="Millions d'euros",
        margin=dict(t=40, b=28, l=8, r=8),
    )
    return fig


def chart_coverage(allm: dict, scenario: str) -> go.Figure:
    names = [x.capitalize() for x in SCENARIOS]
    known = [allm[x]["complete_pct"] for x in SCENARIOS]
    missing = [allm[x]["missing_pct"] for x in SCENARIOS]
    fig = go.Figure()
    fig.add_bar(
        y=names,
        x=known,
        orientation="h",
        name="Montants renseignés",
        marker_color=MINT,
        text=[f"{x:.0f} %" for x in known],
        textposition="inside",
    )
    fig.add_bar(
        y=names,
        x=missing,
        orientation="h",
        name="Montants absents",
        marker_color=AMBER,
        text=[f"{x:.0f} %" for x in missing],
        textposition="inside",
    )
    plot_style(fig, 330).update_layout(
        barmode="stack",
        xaxis_title="Part des commandes (%)",
        legend=dict(orientation="h", y=-0.3),
    )
    fig.update_xaxes(range=[0, 100], ticksuffix=" %")
    fig.update_yaxes(autorange="reversed")
    return fig


def chart_sensitivity(
    allm: dict, scenario: str, low_ratio: float, high_ratio: float
) -> go.Figure:
    """Fourchettes hypothétiques, sans probabilités inventées."""
    fig = go.Figure()
    for name in SCENARIOS:
        m = allm[name]
        x = np.linspace(low_ratio, high_ratio, 35)
        y = (m["missing"] * m["basket"] * x) / 1e6
        color = MINT if name == scenario else (AMBER if name == "medium" else CORAL)
        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                mode="lines",
                name=name.capitalize(),
                line=dict(color=color, width=5 if name == scenario else 2.5),
                hovertemplate=f"{name.capitalize()}<br>Panier relatif : %{{x:.2f}}×<br>CA non vérifiable : %{{y:.2f}} M€<extra></extra>",
            )
        )
    fig.add_vline(
        x=1, line_dash="dot", line_color="#8ca6bd", annotation_text="Panier connu × 1"
    )
    plot_style(fig, 380).update_layout(
        xaxis_title="Panier hypothétique / panier connu",
        yaxis_title="CA non vérifiable (M€)",
    )
    return fig


def chart_quality_radar(allm: dict, scenario: str) -> go.Figure:
    """Profil comparatif : score pédagogique et taux de complétude, pas une certification."""
    categories = [
        "Complétude des montants",
        "Commandes avec montant",
        "Livraisons à l'heure",
        "Indice pédagogique",
    ]
    fig = go.Figure()
    for name in SCENARIOS:
        m = allm[name]
        vals = [
            m["complete_pct"],
            100 * m["known"] / m["orders"],
            100 - m["late_pct"],
            health(m)["score"],
        ]
        fig.add_trace(
            go.Scatterpolar(
                r=vals + vals[:1],
                theta=categories + categories[:1],
                fill="toself" if name == scenario else "none",
                name=name.capitalize(),
                line=dict(width=4 if name == scenario else 2),
                opacity=1 if name == scenario else 0.58,
            )
        )
    plot_style(fig, 410).update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                range=[0, 100],
                showline=False,
                gridcolor="#304357",
                tickfont=dict(size=10),
            ),
            angularaxis=dict(gridcolor="#304357"),
        ),
        legend=dict(orientation="h", y=-0.16),
        margin=dict(l=50, r=50, t=40, b=50),
    )
    return fig


# ───────────────────────────── pages ─────────────────────────────

if page == "Mission Control":
    title, sub = headline(d, allm)
    vlabel, vcls = VERDICT[g["overall"]]
    st.markdown(
        f"""<div class="hero"><div>
        <div class="chips"><span><i class="dot"></i>{esc(source_chip)}</span><span>Scénario {esc(scenario)}</span><span>Lecture seule</span></div>
        <h1 class="hero-title">{esc(title)}</h1><p class="hero-sub">{esc(sub)}</p></div>
        <div class="hero-score"><div class="ring" style="--target:{hs["score"]}%;--score:{round(hs["score"])};--c:{score_color(hs["score"])}" role="img" aria-label="Indice {hs["score"]:.0f} sur 100">
        <div class="ring-in"><b></b><span>sur 100</span></div></div>
        <span class="verdict {vcls}">{esc(vlabel)}</span><div class="hero-note">Indice de santé des données</div></div></div>""",
        unsafe_allow_html=True,
    )

    ledger(
        [
            (
                "Commandes",
                fmt(d["orders"]),
                "Toutes existent, avec ou sans montant",
                None,
                COBALT,
            ),
            (
                "Montants absents",
                fmt(d["missing"]),
                f"{fmt(d['missing_pct'], 2)} % des commandes",
                d["missing_pct"] * 5,
                AMBER,
            ),
            (
                "Panier moyen connu",
                fmt(d["basket"], 2) + " €",
                f"Calculé sur {fmt(d['known'])} commandes",
                d["complete_pct"],
                MINT,
            ),
            (
                "Livraisons en retard",
                fmt(d["late_pct"], 1) + " %",
                f"{fmt(d['late'])} sur {fmt(d['deliveries'])} évaluables",
                d["late_pct"] * 2,
                CORAL,
            ),
        ]
    )

    left, right = st.columns([1.1, 1], gap="large")
    with left:
        h3("À traiter en priorité")
        rec_rows(recs[:4])
    with right:
        h3("Ce que le scénario change")
        fig = go.Figure(
            go.Bar(
                x=[s.capitalize() for s in SCENARIOS],
                y=[allm[s]["exposure"] / 1e6 for s in SCENARIOS],
                marker_color=[MINT if s == scenario else MIST for s in SCENARIOS],
                text=[eur_m(allm[s]["exposure"]) for s in SCENARIOS],
                textposition="outside",
                textfont=dict(color="#dbe7f3"),
                hovertemplate="%{x} : %{y:.1f} M€ non vérifiables<extra></extra>",
            )
        )
        plot_style(fig, 300).update_yaxes(
            title="CA non vérifiable (M€)",
            range=[0, max(allm[s]["exposure"] for s in SCENARIOS) / 1e6 * 1.25],
        )
        st.plotly_chart(fig, **STRETCH)
        st.caption(
            "Commandes sans montant × panier moyen connu. Une hypothèse de travail, pas une perte mesurée."
        )

    h3("Décomposition du chiffre d'affaires · observé vs hypothèse")
    st.plotly_chart(chart_exposure_waterfall(d), **STRETCH)
    st.caption(
        "Le CA documenté est issu des montants connus. L'ajout orange est une hypothèse calculée à partir du panier connu, et non du chiffre d'affaires observé."
    )

    h3("Comparaison des trois scénarios")
    table(
        [
            "Scénario",
            "Montants absents",
            "Panier moyen",
            "Retards",
            "CA non vérifiable",
            "Porte qualité",
            "Indice",
        ],
        [
            [
                f"<b>{s.capitalize()}</b>",
                f"{fmt(allm[s]['missing'])} ({fmt(allm[s]['missing_pct'], 1)} %)",
                f"{fmt(allm[s]['basket'], 2)} €",
                f"{fmt(allm[s]['late_pct'], 2)} %",
                eur_m(allm[s]["exposure"]),
                verdict_badge(gate(allm[s], TH)),
                f"{health(allm[s])['score']:.0f}",
            ]
            for s in SCENARIOS
        ],
        selected=SCENARIOS.index(scenario),
    )

    h3("Périmètre de la mission et livrables")
    skills = [
        (
            "01",
            "Diagnostic",
            "Mesurer la couverture des commandes et les retards, en identifiant les limites.",
        ),
        (
            "02",
            "Investigation",
            "Documenter les anomalies, désigner les responsables et suivre les actions.",
        ),
        (
            "03",
            "Scénarios",
            "Quantifier les conséquences possibles sans confondre hypothèses et faits.",
        ),
        (
            "04",
            "Arbitrage",
            "Préparer une note de décision et un dossier de preuves pour validation métier.",
        ),
    ]
    cols = st.columns(4)
    for i, (ic, t, p) in enumerate(skills):
        cols[i].markdown(
            f'<div class="card fx" style="--i:{i}"><div class="ic">{ic}</div><h4>{t}</h4><p>{p}</p></div>',
            unsafe_allow_html=True,
        )

elif page == "Observatoire":
    page_head(
        "Observatoire des risques",
        "Une salle d'analyse interactive : comparer les scénarios, explorer les incertitudes et distinguer mesures, hypothèses et décisions.",
    )
    st.markdown(
        '<div class="eyebrow">MISSION NEXARETAIL / ANALYTICAL OBSERVATORY</div>',
        unsafe_allow_html=True,
    )
    ledger(
        [
            (
                "Commandes étudiées",
                fmt(d["orders"]),
                "Périmètre du scénario sélectionné",
                None,
                COBALT,
            ),
            (
                "Couverture des montants",
                fmt(d["complete_pct"], 1) + " %",
                "Montants renseignés",
                d["complete_pct"],
                MINT,
            ),
            (
                "CA documenté",
                eur_m(d["known_rev"]),
                "Somme des montants connus",
                None,
                COBALT,
            ),
            (
                "CA non vérifiable",
                eur_m(d["exposure"]),
                "Hypothèse : panier connu × montants absents",
                None,
                AMBER,
            ),
        ]
    )
    a, b = st.columns([1.15, 1], gap="large")
    with a:
        h3("Pont de chiffre d'affaires")
        st.plotly_chart(chart_exposure_waterfall(d), **STRETCH)
        st.caption(
            "Le total est hypothétique : il ne doit pas être présenté comme un CA mesuré."
        )
    with b:
        h3("Couverture des montants par scénario")
        st.plotly_chart(chart_coverage(allm, scenario), **STRETCH)
        st.caption(
            "Comparaison des trois jeux de données : commandes existantes, montants partiellement absents."
        )
    st.divider()
    h3("Laboratoire de sensibilité · hypothèses explicites")
    st.caption(
        "Aucune distribution de probabilité n'est supposée. Déplace les bornes pour tester la valeur possible des commandes sans montant."
    )
    c1, c2 = st.columns(2)
    with c1:
        low_ratio = st.slider(
            "Panier relatif minimal", 0.1, 1.0, 0.5, 0.05, key="obs_low"
        )
    with c2:
        high_ratio = st.slider(
            "Panier relatif maximal", 1.0, 2.5, 1.5, 0.05, key="obs_high"
        )
    st.plotly_chart(chart_sensitivity(allm, scenario, low_ratio, high_ratio), **STRETCH)
    band_low = d["missing"] * d["basket"] * low_ratio
    band_high = d["missing"] * d["basket"] * high_ratio
    st.info(
        f"Scénario {scenario} : sous ces hypothèses, le CA non vérifiable se situe entre {eur_m(band_low)} et {eur_m(band_high)}. Ce n'est pas un intervalle de confiance statistique."
    )
    l, r = st.columns([1, 1], gap="large")
    with l:
        h3("Empreinte de qualité")
        st.plotly_chart(chart_quality_radar(allm, scenario), **STRETCH)
        st.caption(
            "Deux axes de couverture sont volontairement redondants ; le radar est une vue descriptive, pas un indicateur supplémentaire."
        )
    with r:
        h3("Décision et points d'attention")
        st.markdown(
            f'<div class="ops-banner"><b>Statut simulé :</b> {esc(VERDICT[gate(d, TH)["overall"]][0])}<br><br>Les seuils restent configurables dans Decision Gate. La part de montants absents varie entre scénarios ; le taux de retard reste identique dans les références utilisées.</div>',
            unsafe_allow_html=True,
        )
        st.markdown("**Questions à instruire avant restitution au client**")
        st.markdown(
            "- Les valeurs manquantes sont-elles concentrées sur certains canaux, magasins ou périodes ?\n- La moyenne des commandes renseignées est-elle représentative des montants absents ?\n- Les retards se concentrent-ils sur des segments logistiques précis ?"
        )
        st.download_button(
            "Exporter les indicateurs de l'observatoire (CSV)",
            pd.DataFrame(
                [
                    {
                        "scenario": x,
                        "orders": allm[x]["orders"],
                        "missing": allm[x]["missing"],
                        "missing_pct": allm[x]["missing_pct"],
                        "known_revenue": allm[x]["known_rev"],
                        "hypothetical_exposure": allm[x]["exposure"],
                        "late_pct": allm[x]["late_pct"],
                    }
                    for x in SCENARIOS
                ]
            ).to_csv(index=False),
            file_name="consultai_observatoire.csv",
            mime="text/csv",
        )

elif page == "Investigation":
    page_head(
        "Investigation Workspace",
        "Explorer les anomalies, formuler des hypothèses, documenter les contrôles et préparer des actions vérifiables.",
    )
    st.markdown(
        '<div class="eyebrow">Diagnostic · observation ≠ causalité</div>',
        unsafe_allow_html=True,
    )
    l, r = st.columns([1.2, 1], gap="large")
    with l:
        h3("Carte de risques des scénarios")
        st.plotly_chart(plot_matrix(allm, scenario), **STRETCH)
        st.caption(
            "Exposition = commandes sans montant × panier connu. Ni perte mesurée, ni chiffre d’affaires retrouvé."
        )
    with r:
        h3("Constats vérifiés")
        mini(
            [
                ("Montants absents", f"{fmt(d['missing_pct'], 2)} %"),
                ("Commandes sans montant", fmt(d["missing"])),
                ("Retards évaluables", f"{fmt(d['late_pct'], 2)} %"),
            ]
        )
        st.markdown(
            '<div class="callout">Les données agrégées ne permettent pas de démontrer si les valeurs manquantes sont aléatoires, ni d’attribuer les retards à un transporteur.</div>',
            unsafe_allow_html=True,
        )
    h3("Protocole d’investigation")
    with st.expander(
        "H1 · Les montants manquants sont concentrés sur certains canaux ou magasins",
        expanded=True,
    ):
        st.write(
            "**À vérifier :** calculer la part de montants NULL par magasin, canal, période et catégorie, comparer chaque taux au taux global, puis tester les écarts."
        )
        st.code(
            "SELECT scenario, COUNT(*) AS orders, COUNT(*) FILTER (WHERE order_total IS NULL) AS missing FROM dw.fact_orders GROUP BY scenario ORDER BY scenario;",
            language="sql",
        )
        st.caption(
            "Cette requête vérifie les taux globaux. Pour segmenter, contrôle d'abord les colonnes et jointures disponibles dans le DWH."
        )
    with st.expander("H2 · Les commandes sans montant ont un panier différent"):
        st.write(
            "**À vérifier :** confronter les caractéristiques observables des commandes complètes et incomplètes. La valeur réelle des commandes manquantes reste inconnue : le simulateur teste des hypothèses, pas une imputation prouvée."
        )
    with st.expander("H3 · Les retards sont concentrés sur un segment logistique"):
        st.write(
            "**À vérifier :** calculer le taux de retard par transporteur, zone et mois sur les expéditions évaluables, avec des effectifs minimums. Ne pas attribuer de cause avant cette analyse."
        )
    h3("Registre des investigations")
    action_registry(scenario, recs)

elif page == "Scenario Lab":
    page_head(
        "Scenario Lab",
        "Combien de chiffre d'affaires repose sur des commandes sans montant ? Fais varier les hypothèses, puis lis la fourchette d'incertitude.",
    )
    c1, c2 = st.columns([1, 1.7], gap="large")
    with c1:
        rate = st.slider(
            "Part de commandes sans montant (%)", 0, 30, int(round(d["missing_pct"]))
        )
        ratio = st.slider(
            "Panier des commandes sans montant, par rapport au panier connu",
            0.5,
            1.5,
            1.0,
            0.05,
            format="%.2f×",
        )
        st.markdown(
            '<div class="callout">Hypothèses : volume de commandes constant et panier connu inchangé. Les curseurs recalculent un total hypothétique cohérent : ce n’est ni une prévision ni un total observé.</div>',
            unsafe_allow_html=True,
        )
    n_miss = round(d["orders"] * rate / 100)
    # La valeur observée ne change pas quand on déplace le curseur.
    observed_rev = d["known_rev"]
    modeled_known_rev = (d["orders"] - n_miss) * d["basket"]
    miss_rev = n_miss * d["basket"] * ratio
    total = modeled_known_rev + miss_rev
    share = 100 * miss_rev / total if total else 0
    with c2:
        ledger(
            [
                (
                    "CA réellement documenté",
                    eur_m(observed_rev),
                    f"{fmt(d['known'])} commandes renseignées",
                    None,
                    COBALT,
                ),
                (
                    "CA hypothétique",
                    eur_m(miss_rev),
                    f"{fmt(n_miss)} commandes à {fmt(ratio, 2)}×",
                    share * 4,
                    AMBER,
                ),
                (
                    "Part non vérifiable",
                    fmt(share, 1) + " %",
                    "du total hypothétique",
                    share * 4,
                    CORAL,
                ),
                (
                    "Écart à l'observé",
                    fmt(n_miss - d["missing"]),
                    "commandes sans montant en plus ou en moins",
                    None,
                    MIST,
                ),
            ]
        )
        fig = go.Figure(
            go.Waterfall(
                x=[
                    "CA renseigné simulé",
                    "Montants hypothétiques",
                    "Total hypothétique",
                ],
                measure=["absolute", "relative", "total"],
                y=[modeled_known_rev / 1e6, miss_rev / 1e6, 0],
                text=[eur_m(modeled_known_rev), "+ " + eur_m(miss_rev), eur_m(total)],
                textposition="outside",
                textfont=dict(color="#dbe7f3"),
                increasing_marker_color=AMBER,
                totals_marker_color=COBALT,
                connector_line_color=MIST,
            )
        )
        plot_style(fig, 300).update_yaxes(title="M€")
        st.plotly_chart(fig, **STRETCH)

    h3("Sensibilité : quel panier pour les commandes sans montant ?")
    xs = [0.5 + i * 0.05 for i in range(21)]
    fig2 = go.Figure()
    for s, col in zip(SCENARIOS, (MINT, AMBER, CORAL)):
        fig2.add_trace(
            go.Scatter(
                x=xs,
                y=[allm[s]["missing"] * allm[s]["basket"] * x / 1e6 for x in xs],
                name=s.capitalize(),
                mode="lines",
                line=dict(color=col, width=3),
            )
        )
    fig2.add_vline(x=ratio, line_dash="dot", line_color=TXT)
    plot_style(fig2, 320).update_layout(
        xaxis_title="Panier des commandes sans montant (× panier connu)",
        yaxis_title="CA non vérifiable (M€)",
    )
    st.plotly_chart(fig2, **STRETCH)
    st.caption(
        "Plus il manque de montants, plus l'hypothèse de panier pèse sur le total."
    )

    h3("Monte Carlo : une fourchette plutôt qu'un chiffre")
    sigma = (
        st.slider(
            "Incertitude sur le panier des commandes sans montant (± %)", 5, 50, 15, 5
        )
        / 100
    )
    sims = monte_carlo(d, sigma)
    p5, p50, p95 = (float(x) for x in np.percentile(sims, [5, 50, 95]))
    mini(
        [
            ("Borne basse (P5)", f"{fmt(p5, 1)} M€"),
            ("Médiane", f"{fmt(p50, 1)} M€"),
            ("Borne haute (P95)", f"{fmt(p95, 1)} M€"),
        ]
    )
    fig3 = go.Figure(
        go.Histogram(
            x=sims,
            nbinsx=60,
            marker=dict(color=COBALT, line=dict(width=0)),
            opacity=0.85,
            hovertemplate="%{x:.2f} M€<extra></extra>",
        )
    )
    fig3.add_vrect(x0=p5, x1=p95, fillcolor=MINT, opacity=0.12, line_width=0)
    fig3.add_vline(x=p50, line_dash="dash", line_color=TXT)
    plot_style(fig3, 300).update_layout(
        xaxis_title="CA non vérifiable (M€)",
        yaxis_title="Tirages",
        showlegend=False,
        bargap=0.03,
    )
    st.plotly_chart(fig3, **STRETCH)
    st.caption(
        f"20 000 tirages illustratifs, sigma={sigma:.2f} (paramètre log-normal). La zone P5–P95 reflète les hypothèses, pas un intervalle de confiance statistique."
    )

    simulation = {
        "scenario": scenario,
        "source": "reference_frozen" if demo else "postgresql_read_only",
        "observed_missing_orders": d["missing"],
        "observed_revenue_eur": d["known_rev"],
        "hypothetical_missing_rate_pct": rate,
        "hypothetical_missing_orders": n_miss,
        "basket_multiplier": ratio,
        "hypothetical_unverified_revenue": miss_rev,
        "hypothetical_total": total,
        "monte_carlo": {
            "sigma": sigma,
            "p5_m_eur": p5,
            "p50_m_eur": p50,
            "p95_m_eur": p95,
            "draws": len(sims),
        },
        "not_observed": True,
    }
    st.download_button(
        "Exporter les hypothèses (JSON)",
        json.dumps(simulation, indent=2, ensure_ascii=False),
        file_name=f"consultai_simulation_{scenario}.json",
        mime="application/json",
    )

elif page == "Decision Gate":
    page_head(
        "Decision Gate",
        "Le chiffre d'affaires peut-il être publié tel quel ? Règle les seuils, la décision se recalcule pour chaque scénario.",
    )
    t1, t2, t3, t4 = st.columns(4)
    TH["m_warn"] = t1.number_input(
        "Montants absents : réserves dès (%)", 0.0, 50.0, float(TH["m_warn"]), 0.5
    )
    TH["m_fail"] = t2.number_input(
        "Montants absents : blocage dès (%)", 0.0, 50.0, float(TH["m_fail"]), 0.5
    )
    TH["l_warn"] = t3.number_input(
        "Retards : réserves dès (%)", 0.0, 100.0, float(TH["l_warn"]), 1.0
    )
    TH["l_fail"] = t4.number_input(
        "Retards : blocage dès (%)", 0.0, 100.0, float(TH["l_fail"]), 1.0
    )
    if TH["m_warn"] > TH["m_fail"] or TH["l_warn"] > TH["l_fail"]:
        st.error(
            "Seuils incohérents : le seuil de réserve doit être inférieur ou égal au seuil de blocage."
        )
    else:
        g = gate(d, TH)
        h3(f"Contrôles du scénario {scenario}")
        for i, (name, val, st_, rule) in enumerate(g["checks"]):
            sev = {"go": "low", "warn": "mid", "stop": "high"}[st_]
            st.markdown(
                f'<div class="row fx {sev}" style="--i:{i}"><div><div class="row-title">{esc(name)} : {esc(val)}</div><div class="row-why">{esc(rule)}</div></div>'
                f'<div class="pills"><span class="verdict {VERDICT[st_][1]}">{VERDICT[st_][0]}</span></div></div>',
                unsafe_allow_html=True,
            )
        h3("Verdict par scénario")
        table(
            ["Scénario", "Montants absents", "Retards", "Décision"],
            [
                [
                    f"<b>{s.capitalize()}</b>",
                    f"{fmt(allm[s]['missing_pct'], 1)} %",
                    f"{fmt(allm[s]['late_pct'], 1)} %",
                    verdict_badge(gate(allm[s], TH)),
                ]
                for s in SCENARIOS
            ],
            selected=SCENARIOS.index(scenario),
        )
        st.markdown(
            '<div class="ops-banner" style="margin-top:20px">Ces seuils sont des <b>paramètres de simulation</b>, non une politique officiellement validée. La décision finale appartient au responsable métier et au propriétaire des données.</div>',
            unsafe_allow_html=True,
        )
        st.download_button(
            "Télécharger la note de décision (Markdown)",
            data=memo_markdown(d, scenario, g, hs, recs),
            file_name=f"note_decision_{scenario}.md",
            mime="text/markdown",
            type="primary",
        )

elif page == "Data Lineage":
    page_head(
        "Data Lineage",
        "D'où vient chaque chiffre, et par quelle étape passe-t-il avant d'arriver à l'écran ?",
    )
    st.markdown(
        """<div class="pipe">
      <div class="pnode"><b>Source</b><span>PostgreSQL en lecture seule, ou référence figée</span></div><div class="plink"></div>
      <div class="pnode"><b>Calcul</b><span>kpi.py : overview() et delivery()</span></div><div class="plink"></div>
      <div class="pnode"><b>Règles</b><span>Seuils, verdict, priorisation des actions</span></div><div class="plink"></div>
      <div class="pnode"><b>Outils IA</b><span>Simulation, Monte Carlo, résolution de seuils</span></div><div class="plink"></div>
      <div class="pnode"><b>Décision</b><span>Note exportable, hypothèses séparées des faits</span></div></div>""",
        unsafe_allow_html=True,
    )
    n_ok, n_ko, on_time = d["known"], d["missing"], d["deliveries"] - d["late"]
    labels = [
        "Référence des KPI",
        "Commandes",
        "Montant renseigné",
        "Montant absent",
        "Livraisons évaluables",
        "À l'heure",
        "En retard",
    ]
    fig = go.Figure(
        go.Sankey(
            arrangement="snap",
            textfont=dict(color="#dbe7f3", size=12),
            node=dict(
                label=labels,
                pad=22,
                thickness=18,
                color=[TXT, COBALT, MINT, AMBER, COBALT, MINT, CORAL],
                line=dict(width=0),
            ),
            link=dict(
                source=[0, 1, 1, 0, 4, 4],
                target=[1, 2, 3, 4, 5, 6],
                value=[d["orders"], n_ok, n_ko, d["deliveries"], on_time, d["late"]],
                color=[
                    "rgba(80,166,232,.22)",
                    "rgba(73,217,182,.28)",
                    "rgba(240,180,94,.4)",
                    "rgba(80,166,232,.22)",
                    "rgba(73,217,182,.28)",
                    "rgba(240,118,123,.4)",
                ],
            ),
        )
    )
    plot_style(fig, 380)
    st.plotly_chart(fig, **STRETCH)
    st.caption(
        "Vue conceptuelle des volumes : commandes et livraisons sont deux populations distinctes. Ce diagramme n'est pas une lignée technique automatisée."
    )
    h3("Dictionnaire des indicateurs")
    table(
        ["Indicateur", "Définition", "Source (mode PostgreSQL)"],
        [
            [
                "Commandes",
                "Nombre de commandes du scénario",
                "dw.fact_orders · overview()",
            ],
            [
                "Montants absents",
                "Commandes dont order_total est NULL",
                "dw.fact_orders · overview()",
            ],
            [
                "Panier moyen connu",
                "AVG(order_total) hors NULL",
                "dw.fact_orders · overview()",
            ],
            ["Livraisons évaluables", "Dénominateur du taux de retard", "delivery()"],
            ["Taux de retard", "Retards ÷ livraisons évaluables", "delivery()"],
            [
                "CA non vérifiable",
                "Commandes sans montant × panier connu (hypothèse)",
                "calcul dans l'application",
            ],
            [
                "Indice de santé",
                "60 % × (100 − 5 × % absents) + 40 % × (100 − 2 × % retards)",
                "calcul dans l'application",
            ],
        ],
    )
    st.markdown(
        '<div class="ops-banner" style="margin-top:20px"><b>Chaîne de preuve :</b> PostgreSQL (ou valeurs de référence) → calculs SQL/Python → indicateurs → règles → note de décision. Simulations et interprétations sont identifiées séparément.</div>',
        unsafe_allow_html=True,
    )
    with st.expander("Preuves exportables du scénario"):
        st.code(
            json.dumps(
                evidence_payload(d, scenario, demo, TH),
                indent=2,
                ensure_ascii=False,
                default=float,
            ),
            language="json",
        )
        st.download_button(
            "Exporter les KPI (JSON)",
            data=pd.Series(d).to_json(indent=2, force_ascii=False),
            file_name=f"consultai_{scenario}_kpis.json",
            mime="application/json",
        )

else:
    page_head(
        "AI Copilot",
        "Interrogez les KPI, comparez les scénarios et obtenez des décisions justifiées par des preuves.",
    )
    engine = (
        st.radio(
            "Moteur",
            ["Outils vérifiés", "Outils + rédaction Ollama"],
            horizontal=True,
            label_visibility="collapsed",
        )
        if not PUBLIC
        else "Outils vérifiés"
    )
    with st.expander("Méthode et garde-fous · SQL → Python → IA", expanded=False):
        st.caption(
            "Les calculs sont réalisés par des fonctions autorisées. Les réponses indiquent leurs preuves et les hypothèses. Ollama est optionnel et ne calcule pas les KPI."
        )
    chat = st.session_state.setdefault("chat", [])
    ctx = st.session_state.setdefault("ctx", {})
    suggestions = [
        "Compare les trois scénarios",
        "Où trouver les graphiques ?",
        "Qui a créé le projet ?",
        "Comment fonctionne le projet ?",
        "Et si 15 % des montants manquaient ?",
        "Rédige une note de décision",
    ]
    question_groups = {
        "👤 Projet & auteur": [
            "Qui es-tu ?",
            "Qui suis-je ?",
            "Donne-moi mon GitHub et mon LinkedIn",
            "Comment fonctionne ConsultAI 360 ?",
        ],
        "📊 KPI & qualité": [
            "Compare les trois scénarios",
            "Combien de chiffre d'affaires est exposé ?",
            "Et si 15 % des montants manquaient ?",
            "Que sait-on des retards de livraison ?",
        ],
        "🧭 Navigation & méthode": [
            "Où trouver les graphiques ?",
            "Où se trouve le Decision Gate ?",
            "À quoi sert PostgreSQL dans le projet ?",
            "Comment fonctionne le copilote ?",
        ],
        "🛡️ Décision & risques": [
            "Que faire en priorité ?",
            "À partir de quel taux faut-il bloquer ?",
            "Rédige une note de décision",
            "Quelles sont les limites des simulations ?",
        ],
    }
    st.markdown(
        '<div class="copilot-capabilities"><span>✦ Comprend les fautes de frappe</span><span>◈ Connaît les pages du projet</span><span>⌕ Cite ses preuves</span><span>◇ Simule sans inventer</span></div>',
        unsafe_allow_html=True,
    )
    st.caption(
        f"Périmètre : {SCENARIO_LABEL[scenario]} · {'référence de démonstration' if demo else 'PostgreSQL lecture seule'} · aucun SQL généré par l'IA"
    )
    if not chat:
        st.markdown("**Démarrer une analyse**")
        cols = st.columns(3)
        for i, s in enumerate(suggestions):
            cols[i % 3].button(
                s,
                key=f"sg{i}",
                **STRETCH,
                on_click=lambda s=s: st.session_state.update(pending_q=s),
            )
    with st.expander(
        "🧠 Bibliothèque de questions · 16 idées à explorer", expanded=not bool(chat)
    ):
        st.caption(
            "Sélectionne un thème et clique sur une question : elle est envoyée directement au copilote."
        )
        for category, questions in question_groups.items():
            st.markdown(
                f'<div class="question-category">{esc(category)}</div>',
                unsafe_allow_html=True,
            )
            question_cols = st.columns(2)
            for j, question in enumerate(questions):
                question_cols[j % 2].button(
                    question,
                    key=f"library_{category}_{j}",
                    **STRETCH,
                    on_click=lambda question=question: st.session_state.update(
                        pending_q=question
                    ),
                )
    # La question suggérée est prioritaire, sinon une ancienne suggestion peut resurgir.
    typed_q = st.chat_input(
        "Posez une question sur les KPI, les risques ou les décisions…",
        key="consultai_question",
    )
    pending_q = st.session_state.pop("pending_q", None)
    q = pending_q or typed_q
    if q:
        q = q.strip()[:1000]
        chat.append({"role": "user", "content": q})
        res = respond(q, scenario, allm, TH, ctx)
        if (
            engine.startswith("Outils + ")
            and not res["intent"].startswith("projet_")
            and res["intent"] != "identite"
        ):
            try:
                with st.spinner("Rédaction locale en cours..."):
                    res = ollama_answer(q, allm, chat[:-1], res)
            except Exception as exc:
                res["text"] = (
                    f"Ollama n'a pas répondu ({type(exc).__name__}). Voici les résultats des outils, sans rédaction :\n\n"
                    + res["text"]
                )
        chat.append(
            {
                "role": "assistant",
                "content": res["text"],
                "evidence": res["evidence"],
                "intent": res["intent"],
                "kind": res["kind"],
                "scenario": res["scenario"],
                "followups": res["followups"],
                "fresh": True,
            }
        )
    if not chat:
        st.markdown(
            '<div class="chat-empty fx"><b>Prêt pour une investigation</b><span>Sélectionnez une question ci-dessus ou utilisez la barre de saisie. Les réponses distinguent faits, simulations et recommandations.</span></div>',
            unsafe_allow_html=True,
        )
    for idx, m in enumerate(chat):
        with st.chat_message(m["role"]):
            if m["role"] == "assistant":
                cls = {
                    "Hypothèse": "hyp",
                    "Information": "info",
                    "Définition": "info",
                }.get(m.get("kind", ""), "")
                st.markdown(
                    f'<span class="tag {cls}">{esc(m.get("kind", ""))}</span><span class="tag info">scénario {esc(m.get("scenario", ""))}</span>',
                    unsafe_allow_html=True,
                )
                # Markdown rendu directement : évite le texte invisible du flux
                # st.write_stream dans certaines versions de Streamlit.
                m.pop("fresh", None)
                st.markdown(m["content"])
                if m.get("evidence"):
                    with st.expander("Preuves et méthode · " + m.get("intent", "")):
                        for e in m["evidence"]:
                            st.markdown(f"- {e}")
            else:
                st.markdown(m["content"])
    if chat and chat[-1]["role"] == "assistant":
        st.markdown(
            '<div class="kicker" style="margin-top:6px">Pour aller plus loin</div>',
            unsafe_allow_html=True,
        )
        fu = chat[-1].get("followups", DEFAULT_FOLLOW)
        cols = st.columns(len(fu))
        for i, s in enumerate(fu):
            cols[i].button(
                s,
                key=f"fu{len(chat)}_{i}",
                **STRETCH,
                on_click=lambda s=s: st.session_state.update(pending_q=s),
            )
        st.button(
            "Effacer la conversation",
            on_click=lambda: st.session_state.update(chat=[], ctx={}, pending_q=None),
        )

st.markdown(
    '<div class="foot">CONSULTAI 360 / NEXARETAIL · ENVIRONNEMENT SYNTHÉTIQUE · SQL → PYTHON → CONTRÔLES → IA OPTIONNELLE · AUCUNE DÉCISION AUTOMATIQUE</div>',
    unsafe_allow_html=True,
)
