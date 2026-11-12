"""ConsultAI 360 — console de décision NexaRetail.

Lancer : python -m streamlit run app.py
Démo publique : CONSULTAI_DEMO_MODE=true (aucune base de données ni Ollama requis).
Copilote local optionnel : Ollama (OLLAMA_HOST, CONSULTAI_OLLAMA_MODEL).
"""

from __future__ import annotations

import difflib
import html
import json
import os
import re
import unicodedata
import urllib.request
from datetime import date
from functools import lru_cache
from urllib.parse import urlparse

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from project_knowledge import correct as correct_question
from project_knowledge import profile as author_profile
from project_knowledge import project_answer
from src.assistant.decision_rules import gate, safe_th
from src.assistant.health_score import health

st.set_page_config(
    page_title="ConsultAI 360",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ───────────────────────────── constantes ─────────────────────────────

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
SCENARIO_NAME = {"low": "Faible", "medium": "Moyen", "critical": "Critique"}
SCENARIO_LABEL = {
    "low": "Scénario faible",
    "medium": "Scénario moyen",
    "critical": "Scénario critique",
}
DEFAULT_TH = {"m_warn": 3.0, "m_fail": 8.0, "l_warn": 10.0, "l_fail": 20.0}
TH_WIDGETS = {k: f"th_{k}" for k in DEFAULT_TH}
MAX_CHAT = 40

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
PLOT_CONFIG = {"displayModeBar": False, "responsive": True}

TXT, COBALT, MINT, AMBER, CORAL, MIST = (
    "#17304d",
    "#2563eb",
    "#0d9488",
    "#d99000",
    "#e44560",
    "#8495ab",
)
SCENARIO_COLORS = {"low": "#0d9488", "medium": "#d99000", "critical": "#e44560"}
PAGES = [
    "Atelier d’analyse",
    "Mission Control",
    "Observatoire",
    "Investigation",
    "Scenario Lab",
    "Decision Gate",
    "Data Lineage",
    "AI Copilot",
]
PAGE_LABELS = {
    "Atelier d’analyse": "Atelier d’analyse",
    "Mission Control": "Vue d’ensemble",
    "Observatoire": "Observatoire",
    "Investigation": "Investigation",
    "Scenario Lab": "Laboratoire de scénarios",
    "Decision Gate": "Porte de décision",
    "Data Lineage": "Traçabilité des données",
    "AI Copilot": "Assistant IA",
}
# Un emoji = un concept (aucun doublon avec les catégories de la bibliothèque de questions).
PAGE_ICONS = {
    "Atelier d’analyse": "📊",
    "Mission Control": "🎯",
    "Observatoire": "📈",
    "Investigation": "🔎",
    "Scenario Lab": "🧪",
    "Decision Gate": "🛡️",
    "Data Lineage": "🧬",
    "AI Copilot": "🤖",
}

# ───────────────────────────── styles (un seul bloc cohérent) ─────────────────────────────

CSS = """<style>
:root{--bg:#f4f6f9;--surface:#fff;--surface-soft:#f8f9fb;--navy:#142b46;--navy-2:#203f61;--gold:#c49a3a;--gold-soft:#f5ecd7;--txt:#1d2d40;--muted:#586b80;--line:#dce3eb;--line-2:#c7d1dc;--green:#28765e;--red:#a33e47;color-scheme:light}
@property --p{syntax:'<percentage>';inherits:false;initial-value:0%}
@property --n{syntax:'<integer>';inherits:false;initial-value:0}
html{font-size:16px;background:var(--bg)}
html,body,.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"]{background:var(--bg)!important;color:var(--txt)!important}
.stApp{font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif}
.stApp [data-testid="stMarkdownContainer"],.stApp label,.stApp button,.stApp input,.stApp textarea,.stApp h1,.stApp h2,.stApp h3,.stApp h4{font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif}
[data-testid="stIconMaterial"],.material-symbols-rounded,.material-icons{font-family:'Material Symbols Rounded','Material Icons'!important}
.block-container{max-width:1500px!important;padding:2rem clamp(1rem,3vw,3rem) 4rem!important;overflow-x:hidden}
header[data-testid="stHeader"]{background:rgba(244,246,249,.92)!important}
.stApp h1,.stApp h2,.stApp h3,.stApp h4{color:var(--navy)!important;letter-spacing:-.025em}
.stApp h2{font-size:1.85rem!important}.stApp h3{font-size:1.3rem!important}
.stApp p,.stApp li,.stApp [data-testid="stCaptionContainer"]{color:var(--txt)}
.stApp [data-testid="stCaptionContainer"]{color:var(--muted)!important}
.stApp ::selection{background:#ead9ad;color:var(--navy)}
:focus-visible{outline:3px solid var(--gold)!important;outline-offset:2px}

/* Navigation : panneau bleu marine, sélection dorée */
[data-testid="stSidebar"],[data-testid="stSidebarContent"]{background:var(--navy)!important}
[data-testid="stSidebar"]{border-right:1px solid #0e2238;min-width:clamp(245px,22vw,310px)!important}
[data-testid="stSidebar"] label,[data-testid="stSidebar"] p,[data-testid="stSidebar"] [data-testid="stCaptionContainer"],[data-testid="stSidebar"] [data-testid="stWidgetLabel"]{color:#e6edf4!important}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"]{color:#b6c5d4!important}
[data-testid="stSidebar"] hr{border-color:#3b526c}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{gap:.55rem}
[data-testid="stSidebar"] [role="radiogroup"]{gap:5px}
[data-testid="stSidebar"] [role="radiogroup"] label{padding:10px 12px;min-height:44px;border-radius:9px;width:100%;cursor:pointer;border-left:3px solid transparent;transition:background .18s,border-color .18s}
[data-testid="stSidebar"] [role="radiogroup"] label>div:first-child{display:none}
[data-testid="stSidebar"] [role="radiogroup"] label p{font-size:.91rem!important;font-weight:600!important;margin:0!important}
[data-testid="stSidebar"] [role="radiogroup"] label:hover{background:#203b58}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked){background:#2a4058;border-left-color:#e2bb62}
.side-title{font-size:.68rem;font-weight:800;letter-spacing:.14em;color:#e2bb62;margin:10px 0 6px;text-transform:uppercase}
.brand{display:flex;gap:12px;align-items:center;font-size:1.22rem;font-weight:800;color:#fff;letter-spacing:-.035em}
.brand i{font-style:normal;display:grid;place-items:center;width:40px;height:40px;border-radius:12px;background:var(--gold);color:var(--navy);font-size:1.3rem}
.brand small{display:block;color:#bdcada;font-size:.64rem;font-weight:600;margin-top:3px;letter-spacing:.08em}
.live-dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:#74c6a5;margin-right:6px}
.side-intro{background:#203b58;border:1px solid #3e5874;border-radius:11px;padding:12px 13px;color:#f2dfb0;font-size:.65rem;font-weight:700;letter-spacing:.04em;margin:12px 0 3px}
.side-intro b{float:right;color:#f1d48d}.side-intro p{color:#d1dce6;font-size:.76rem;margin:8px 0 0;letter-spacing:0}
.side-status{padding:12px 13px;background:#203b58;border:1px solid #3e5874;border-radius:11px;font-size:.8rem;color:#f1f5f8;line-height:1.5}
.side-status small{display:block;margin-top:5px;color:#c1cfdb;font-size:.7rem}
.side-author{display:flex;gap:10px;align-items:center;padding:12px 10px;background:#203b58;border:1px solid #3e5874;border-radius:11px}
.side-author .avatar{display:grid;place-items:center;flex-shrink:0;width:42px;height:42px;border-radius:12px;background:var(--gold);font-weight:800;color:var(--navy)}
.side-author b{display:block;color:#fff;font-size:.85rem;line-height:1.4}.side-author small{display:block;color:#c1cfdb;font-size:.72rem;line-height:1.5;margin-top:2px}

/* Formulaires et composants natifs : champs clairs et texte foncé */
[data-baseweb="input"],[data-baseweb="base-input"],[data-baseweb="textarea"],[data-baseweb="select"]>div,[data-testid="stChatInput"]{background:#fff!important;border:1px solid var(--line-2)!important;color:var(--txt)!important;border-radius:9px!important;box-shadow:none!important}
.stApp input,.stApp textarea,[data-baseweb="select"] *{background:transparent!important;color:var(--txt)!important;-webkit-text-fill-color:var(--txt)!important;caret-color:var(--navy)}
.stApp input::placeholder,.stApp textarea::placeholder{color:#697b8e!important;-webkit-text-fill-color:#697b8e!important;opacity:1}
[data-baseweb="input"]:focus-within,[data-baseweb="textarea"]:focus-within,[data-baseweb="select"]:focus-within{border-color:var(--gold)!important;box-shadow:0 0 0 2px rgba(196,154,58,.18)!important}
[data-baseweb="select"] svg{fill:#50657a!important}
[data-baseweb="popover"],[data-baseweb="popover"]>div,[data-baseweb="popover"] ul,[data-baseweb="menu"],[data-baseweb="listbox"],[data-baseweb="calendar"],[data-baseweb="tooltip"]{background:#fff!important;color:var(--txt)!important;border-color:var(--line)!important}
[data-baseweb="popover"] *,[data-baseweb="menu"] *{color:var(--txt)!important}
[data-baseweb="popover"] li:hover,[data-baseweb="menu"] li:hover{background:#f0f3f7!important}
[data-testid="stNumberInput"] button,[data-testid="stNumberInput"] button *{background-color:#edf1f5!important;color:var(--navy)!important;fill:var(--navy)!important}
[data-testid="stWidgetLabel"],[data-testid="stWidgetLabel"] *,.stApp label p{color:var(--txt)!important}
[data-testid="stSlider"] div[role="slider"]{background:var(--gold)!important;box-shadow:0 0 0 4px rgba(196,154,58,.18)}
[data-testid="stExpander"]{background:#fff;border:1px solid var(--line)!important;border-radius:12px!important;transition:border-color .18s}
[data-testid="stExpander"]:hover{border-color:#c4a45b!important}
[data-testid="stExpander"] details,[data-testid="stExpander"] summary,[data-testid="stExpanderDetails"]{background:#fff!important;color:var(--txt)!important}
[data-testid="stExpander"] summary *{color:var(--navy)!important}
[data-testid="stCodeBlock"],[data-testid="stCodeBlock"] pre,pre{background:#f1f4f7!important;color:#26394d!important;border:1px solid var(--line);border-radius:9px}
code{color:#264a6a!important;background:#eaf0f5!important;border-radius:4px;padding:1px 5px}pre code{background:transparent!important;padding:0}
[data-testid="stAlert"]{background:#fff!important;border:1px solid var(--line)!important;color:var(--txt)!important;border-radius:10px}
[data-testid="stVerticalBlockBorderWrapper"]{border-color:var(--line)!important;background:#fff;border-radius:12px}
[data-testid="stPlotlyChart"]{background:#fff!important;border:1px solid var(--line);border-radius:14px;overflow:hidden;transition:border-color .2s,box-shadow .2s}
[data-testid="stPlotlyChart"]:hover{border-color:#c9a755;box-shadow:0 8px 24px rgba(25,45,68,.08)}
[data-testid="stProgressBar"]>div{background:#e8edf2!important}[data-testid="stProgressBar"]>div>div{background:var(--gold)!important}
[data-testid="stMarkdownContainer"] table{background:#fff!important}[data-testid="stMarkdownContainer"] th{background:#edf1f5!important;color:var(--navy)!important}[data-testid="stMarkdownContainer"] td{background:#fff!important;color:var(--txt)!important;border-color:var(--line)!important}
[data-testid="stMarkdownContainer"] blockquote{background:#f7f4ec!important;border-left:3px solid var(--gold)!important;padding:8px 15px}
.stApp [data-testid="stMarkdownContainer"] a{color:#285b84!important}

/* Boutons */
.stButton>button,.stDownloadButton>button,.stLinkButton>a{background:#fff!important;color:var(--navy)!important;border:1px solid #bdc9d5!important;border-radius:9px!important;min-height:2.55rem;font-size:.9rem;font-weight:650;transition:transform .15s,border-color .15s,box-shadow .15s}
.stButton>button:hover,.stDownloadButton>button:hover,.stLinkButton>a:hover{border-color:var(--gold)!important;color:var(--navy)!important;background:#fbf8f0!important;transform:translateY(-1px);box-shadow:0 5px 15px rgba(25,45,68,.1)}
.stButton>button:active{transform:none}
.stButton>button[kind="primary"],.stDownloadButton>button[kind="primary"]{background:var(--navy)!important;border-color:var(--navy)!important;color:#fff!important}
.stButton>button[kind="primary"]:hover,.stDownloadButton>button[kind="primary"]:hover{background:#203f61!important;border-color:var(--gold)!important}
[data-testid="stSidebar"] .stButton>button,[data-testid="stSidebar"] .stLinkButton>a{width:100%}

/* Assistant conversation */
[data-testid="stChatMessage"]{border:1px solid var(--line)!important;border-radius:15px!important;padding:1rem 1.2rem!important;margin-bottom:10px;box-shadow:0 4px 14px rgba(25,45,68,.05);animation:rise .28s ease both}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]){background:#f1f4f7!important}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]){background:#fff!important;border-left:3px solid var(--gold)!important}
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] *{color:var(--txt)!important;-webkit-text-fill-color:var(--txt)!important;opacity:1!important}
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li{font-size:.98rem!important;line-height:1.7!important}
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] a{color:#285b84!important;-webkit-text-fill-color:#285b84!important}
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] code{color:#264a6a!important;-webkit-text-fill-color:#264a6a!important}
[data-testid="stBottom"],[data-testid="stBottom"]>div,[data-testid="stBottomBlockContainer"]{background:var(--bg)!important;border-color:var(--line)!important}
[data-testid="stBottomBlockContainer"]{max-width:1500px!important;padding:10px 2rem 18px!important}
[data-testid="stChatInput"]{border:1px solid var(--line-2)!important;box-shadow:0 4px 14px rgba(25,45,68,.06)!important;transition:border-color .18s,box-shadow .18s}
[data-testid="stChatInput"]:focus-within{border-color:var(--gold)!important;box-shadow:0 0 0 3px rgba(196,154,58,.14)!important}
[data-testid="stChatInput"] textarea{min-height:50px!important;font-size:.98rem!important}
[data-testid="stChatInput"] button{color:var(--navy)!important;background:#f1f4f7!important}
.chat-empty{border:1px dashed #c8d2dc;border-radius:12px;padding:1.2rem 1.35rem;background:#fff;display:flex;flex-direction:column;gap:8px;margin-top:12px}
.chat-empty b{color:var(--navy);font-size:1rem}.chat-empty span{color:var(--muted);font-size:.88rem;line-height:1.55}
.copilot-capabilities{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}
.copilot-capabilities span{background:#f5f1e6;border:1px solid #e3d5b1;border-radius:8px;padding:7px 10px;color:#604d24;font-size:.76rem}
.question-category{font-size:.95rem;font-weight:800;color:var(--navy);margin:15px 0 7px;padding:7px 0;border-bottom:1px solid var(--line)}

/* Titres, indicateurs et cartes */
.hero{display:grid;grid-template-columns:1fr auto;gap:28px;align-items:center;border:1px solid #d8c694;border-radius:16px;padding:32px 36px;margin-bottom:20px;background:linear-gradient(115deg,#fff 0%,#fbfaf6 68%,#f5efdf 100%);position:relative;overflow:hidden;box-shadow:0 8px 24px rgba(25,45,68,.05)}
.hero::after{content:"";position:absolute;inset:-35% -5% auto auto;width:360px;height:360px;background:radial-gradient(circle,rgba(196,154,58,.14),transparent 68%);pointer-events:none}
.hero>*{position:relative;z-index:1}
.hero-title{font-size:clamp(1.7rem,3vw,2.45rem);font-weight:800;line-height:1.15;letter-spacing:-.04em;margin:14px 0 10px;max-width:830px;color:var(--navy)}
.hero-sub{color:#4f6275;line-height:1.65;font-size:.98rem;max-width:860px;margin:0}
.chips span{display:inline-flex;align-items:center;gap:7px;font-size:.65rem;font-weight:750;text-transform:uppercase;letter-spacing:.06em;border:1px solid #e1d3ae;color:#5d4a20;background:#fbf7eb;padding:6px 10px;margin:0 6px 4px 0;border-radius:99px}
.dot{width:7px;height:7px;border-radius:50%;background:var(--green)}
.hero-score{text-align:center;min-width:155px}
.ring{--p:var(--target);width:138px;height:138px;border-radius:50%;margin:0 auto 10px;display:grid;place-items:center;background:conic-gradient(var(--c) var(--p),#e5e9ee 0);animation:fill 1s ease both}
.ring-in{width:109px;height:109px;background:#fff;border-radius:50%;display:grid;place-content:center;text-align:center}
.ring-in b{--n:var(--score);counter-reset:n var(--n);animation:cnt 1s ease both;font-size:2.5rem;font-weight:800;color:var(--navy);line-height:1}
.ring-in b::after{content:counter(n)}.ring-in span{color:var(--muted);font-size:.66rem;font-weight:700}
.verdict{display:inline-block;padding:5px 10px;font-size:.72rem;font-weight:750;border-radius:99px}
.v-go{background:#e5f2ec;color:#23694f}.v-warn{background:#f7efd9;color:#755817}.v-stop{background:#f7e8e9;color:#8e3039}
.hero-note{font-size:.67rem;font-weight:650;color:var(--muted);margin-top:8px}
.pagehead{margin:3px 0 22px;animation:rise .35s both}.pagehead h2{margin:0 0 5px!important}.pagehead p{color:var(--muted);margin:0;font-size:.96rem;max-width:920px;line-height:1.55}
.h3{font-size:1.08rem;font-weight:800;margin:25px 0 11px;color:var(--navy)}
.eyebrow{font-size:.67rem;font-weight:800;letter-spacing:.11em;text-transform:uppercase;color:#86681f;margin-bottom:9px}
.kicker{font-size:.68rem;font-weight:750;color:#80621c;text-transform:uppercase;letter-spacing:.07em;margin-bottom:4px}
.ledger{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));background:#fff;border:1px solid var(--line);border-radius:13px;overflow:hidden;box-shadow:0 4px 16px rgba(25,45,68,.035)}
.cell{padding:18px 20px;border-right:1px solid var(--line);transition:background .18s}.cell:hover{background:#fbfaf6}.cell:last-child{border-right:0}
.cell .lab{font-size:.66rem;font-weight:750;text-transform:uppercase;letter-spacing:.045em;color:var(--muted)}
.cell .val{font-size:clamp(1.25rem,2vw,1.9rem);font-weight:800;color:var(--navy);margin:8px 0 4px;letter-spacing:-.035em;white-space:nowrap}
.cell .note{color:var(--muted);font-size:.78rem;line-height:1.4}.bar{height:5px;background:#e8edf1;border-radius:5px;margin-top:12px;overflow:hidden}.bar i{display:block;height:100%;border-radius:5px;transform-origin:left;animation:grow .8s ease both}
.row{display:flex;justify-content:space-between;gap:14px;background:#fff;border:1px solid var(--line);border-left:4px solid #aab8c5;border-radius:10px;padding:14px 16px;margin-bottom:9px;transition:box-shadow .18s}
.row:hover{box-shadow:0 5px 16px rgba(25,45,68,.07)}.row.high{border-left-color:#bd4f57}.row.mid{border-left-color:#d2a33c}.row.low{border-left-color:#43866c}
.row-title{font-weight:750;color:var(--navy);margin-bottom:4px}.row-why{color:#53667a;font-size:.85rem;line-height:1.55}
.pills{display:flex;gap:6px;flex-shrink:0;align-items:flex-start;flex-wrap:wrap}.pill{background:#f5efdE;color:#604d24;font-size:.68rem;font-weight:650;padding:4px 8px;border-radius:99px;white-space:nowrap}.pill.soft{background:#eef1f4;color:#526579}
.card{background:#fff;border:1px solid var(--line);border-radius:13px;padding:18px;height:100%;transition:transform .18s,border-color .18s,box-shadow .18s}.card:hover{transform:translateY(-2px);border-color:#d3bd81;box-shadow:0 7px 18px rgba(25,45,68,.06)}
.card h4{font-size:.98rem;margin:0 0 7px}.card p{color:#53667a;line-height:1.6;font-size:.85rem;margin:0}.card .ic{display:inline-grid;place-items:center;width:33px;height:33px;border-radius:9px;background:var(--gold-soft);margin-bottom:10px;font-size:.75rem;font-weight:800;color:#72591d}
.callout{background:#fbf7eb;border:1px solid #e4d6b3;border-radius:10px;color:#57491f;padding:12px 15px;margin:11px 0;font-size:.85rem;line-height:1.55}
.ops-banner{background:#f0f4f7;border:1px solid #d9e1e8;border-left:4px solid var(--gold);border-radius:9px;padding:13px 16px;color:#34495e;margin:11px 0 18px;font-size:.86rem;line-height:1.6}
.tblwrap{overflow-x:auto;border:1px solid var(--line);border-radius:11px;background:#fff}.tbl{width:100%;border-collapse:collapse;background:#fff}
.tbl th{background:#edf1f5;color:#344a60;text-align:left;font-size:.68rem;font-weight:750;padding:12px;white-space:nowrap}.tbl td{color:var(--txt);border-top:1px solid var(--line);padding:12px;font-size:.84rem}.tbl tr.sel td{background:#f8f3e7}
.tag{display:inline-block;font-size:.63rem;font-weight:750;text-transform:uppercase;letter-spacing:.05em;padding:4px 8px;border-radius:99px;margin:0 5px 7px 0;background:#f5efdf;color:#66521e;border:1px solid #e7d9b7}.tag.hyp{background:#fbf2df;color:#755817;border-color:#e8d6aa}.tag.info{background:#edf2f7;color:#365775;border-color:#d2dce6}
.mini{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:13px}.mini div{background:#fff;border:1px solid var(--line);border-radius:11px;padding:13px 14px}.mini b{display:block;font-size:1.35rem;letter-spacing:-.035em;color:var(--navy)}.mini span{font-size:.75rem;color:var(--muted)}
.pipe{display:flex;align-items:stretch;gap:0;margin:6px 0 4px}.pnode{background:#fff;border:1px solid var(--line);border-radius:11px;padding:13px 14px;min-width:140px;flex:0 0 auto;max-width:185px}.pnode b{display:block;color:var(--navy);margin-bottom:4px;font-size:.9rem}.pnode span{color:var(--muted);font-size:.75rem;line-height:1.45}
.plink{flex:1;min-width:28px;align-self:center;height:2px;background:#d7dfe7;position:relative}.plink::after{content:"";position:absolute;top:-3px;left:0;width:7px;height:7px;border-radius:50%;background:var(--gold);animation:flow 2.4s linear infinite}.plink:nth-child(4)::after{animation-delay:.6s}.plink:nth-child(6)::after{animation-delay:1.2s}.plink:nth-child(8)::after{animation-delay:1.8s}
.foot{border-top:1px solid var(--line);color:#687b8e;padding-top:13px;margin-top:38px;font-size:.66rem;letter-spacing:.025em}.fx{animation:rise .4s ease both;animation-delay:calc(var(--i,0)*55ms)}
.js-plotly-plot .sankey text,.js-plotly-plot .sankey .node-label{text-shadow:none!important;stroke:none!important;paint-order:normal!important}
@keyframes rise{from{opacity:0;transform:translateY(7px)}to{opacity:1;transform:none}}@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}@keyframes fill{from{--p:0%}to{--p:var(--target)}}@keyframes cnt{from{--n:0}to{--n:var(--score)}}@keyframes flow{from{left:0}to{left:calc(100% - 7px)}}
@media(max-width:1000px){.hero{grid-template-columns:1fr}.ledger{grid-template-columns:repeat(2,1fr)}.cell{border-bottom:1px solid var(--line)}.pipe{flex-direction:column}.pnode{max-width:none}.plink{width:2px;height:24px;min-height:24px;align-self:center}.plink::after{left:-3px;top:0;animation-name:flowv}.mini{grid-template-columns:1fr}}
@keyframes flowv{from{top:0}to{top:calc(100% - 7px)}}
@media(max-width:900px){html{font-size:15px}.block-container{padding:1rem 1rem 2.5rem!important}[data-testid="stBottomBlockContainer"]{padding:8px 1rem!important}[data-testid="stSidebar"]{min-width:unset!important}}
@media(max-width:600px){.ledger{grid-template-columns:1fr}.hero{padding:22px}.row{flex-direction:column}.copilot-capabilities span{font-size:.69rem}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important}}
</style>"""
st.markdown(CSS, unsafe_allow_html=True)

# Correctifs de contraste et animations. Ces règles sont chargées après le thème
# afin de garder les textes lisibles malgré les styles internes de Streamlit.
ACCESSIBILITY_AND_MOTION = """<style>
/* Contrastes forcés : certains composants Streamlit stylent leurs enfants séparément. */
[data-testid="stSidebar"] [data-testid="stWidgetLabel"],
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] *,
[data-testid="stSidebar"] [role="radiogroup"] label,
[data-testid="stSidebar"] [role="radiogroup"] label * {
  color:#f2f5f8!important;-webkit-text-fill-color:#f2f5f8!important;opacity:1!important
}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] * {
  color:#c2cfdb!important;-webkit-text-fill-color:#c2cfdb!important;opacity:1!important
}
[data-testid="stSidebar"] [data-baseweb="select"],
[data-testid="stSidebar"] [data-baseweb="select"] * {
  color:#20364c!important;-webkit-text-fill-color:#20364c!important
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] .side-title,
[data-testid="stSidebar"] .side-title {color:#f0c75e!important;-webkit-text-fill-color:#f0c75e!important}
[data-testid="stSidebar"] .brand,
[data-testid="stSidebar"] .brand * {color:#fff!important;-webkit-text-fill-color:#fff!important}
[data-testid="stSidebar"] .brand i {color:#142b46!important;-webkit-text-fill-color:#142b46!important}
[data-testid="stSidebar"] .side-intro,
[data-testid="stSidebar"] .side-intro * {color:#f3e4bd!important;-webkit-text-fill-color:#f3e4bd!important}
[data-testid="stSidebar"] .side-intro b {color:#f0c75e!important;-webkit-text-fill-color:#f0c75e!important}
[data-testid="stSidebar"] .side-intro p {color:#e0e8ef!important;-webkit-text-fill-color:#e0e8ef!important}
[data-testid="stSidebar"] .side-status,
[data-testid="stSidebar"] .side-status * {color:#f2f5f8!important;-webkit-text-fill-color:#f2f5f8!important}
[data-testid="stSidebar"] .side-status small {color:#c2cfdb!important;-webkit-text-fill-color:#c2cfdb!important}
[data-testid="stSidebar"] .side-author b {color:#fff!important;-webkit-text-fill-color:#fff!important}
[data-testid="stSidebar"] .side-author small {color:#d2dce5!important;-webkit-text-fill-color:#d2dce5!important}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked),
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) * {
  color:#fff!important;-webkit-text-fill-color:#fff!important
}
[data-testid="stMain"] h1,[data-testid="stMain"] h1 *,
[data-testid="stMain"] h2,[data-testid="stMain"] h2 *,
[data-testid="stMain"] h3,[data-testid="stMain"] h3 *,
[data-testid="stMain"] .h3,
[data-testid="stMain"] .pagehead h2 {
  color:#142b46!important;-webkit-text-fill-color:#142b46!important;opacity:1!important
}
[data-testid="stMain"] [data-testid="stWidgetLabel"],
[data-testid="stMain"] [data-testid="stWidgetLabel"] * {
  color:#20364c!important;-webkit-text-fill-color:#20364c!important;opacity:1!important
}
[data-testid="stMain"] .stButton>button,
[data-testid="stMain"] .stDownloadButton>button,
[data-testid="stSidebar"] .stButton>button,
[data-testid="stSidebar"] .stDownloadButton>button,
.stLinkButton>a {
  color:#142b46!important;-webkit-text-fill-color:#142b46!important
}
[data-testid="stMain"] .stButton>button[kind="primary"],
[data-testid="stMain"] .stButton>button[kind="primary"] *,
[data-testid="stMain"] .stDownloadButton>button[kind="primary"],
[data-testid="stMain"] .stDownloadButton>button[kind="primary"] *,
[data-testid="stSidebar"] .stButton>button[kind="primary"],
[data-testid="stSidebar"] .stButton>button[kind="primary"] * {
  color:#fff!important;-webkit-text-fill-color:#fff!important
}

/* Mouvement plus présent, en restant fluide et sans gêner la lecture. */
.stApp {
  background-image:radial-gradient(ellipse at 90% 0%,rgba(196,154,58,.08),transparent 34%),
                   radial-gradient(ellipse at 0% 80%,rgba(49,95,140,.07),transparent 38%);
  background-size:140% 140%;animation:ambientDrift 22s ease-in-out infinite alternate
}
[data-testid="stMain"]>.block-container{animation:pageArrival .55s cubic-bezier(.2,.75,.25,1) both}
[data-testid="stSidebar"] [role="radiogroup"] label{position:relative;overflow:hidden;transition:background .22s ease,transform .22s ease,box-shadow .22s ease}
[data-testid="stSidebar"] [role="radiogroup"] label:hover{transform:translateX(5px);box-shadow:inset 3px 0 0 #e2bb62}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked){animation:navSelect .45s ease both;box-shadow:inset 3px 0 0 #e2bb62,0 5px 18px rgba(0,0,0,.14)}
[data-testid="stSidebar"] .side-intro,[data-testid="stSidebar"] .side-status,[data-testid="stSidebar"] .side-author{animation:softReveal .55s ease both}
[data-testid="stSidebar"] .side-intro{animation-delay:.08s}
[data-testid="stSidebar"] .side-status{animation-delay:.18s}
[data-testid="stSidebar"] .side-author{animation-delay:.25s}
.hero{background-size:190% 190%;animation:heroReveal .7s cubic-bezier(.2,.75,.25,1) both,heroTint 16s ease-in-out infinite alternate}
.hero::after{animation:goldHalo 8s ease-in-out infinite alternate}
.hero-score{animation:scoreReveal .8s .15s cubic-bezier(.2,.75,.25,1) both}
.ring{animation:ringFill 1.15s cubic-bezier(.2,.7,.25,1) both,ringBreath 4s 1.2s ease-in-out infinite}
.ring-in b{animation:numberReveal 1s .2s cubic-bezier(.2,.75,.25,1) both}
.chips span{animation:chipReveal .45s ease both}
.chips span:nth-child(2){animation-delay:.08s}.chips span:nth-child(3){animation-delay:.16s}
.ledger{animation:softReveal .45s .12s ease both}
.ledger .cell{animation:metricReveal .55s cubic-bezier(.2,.75,.25,1) both;animation-delay:calc(var(--i,0)*90ms)}
.card,.mini div,.row,.pnode,.tblwrap,.ops-banner,.callout,.chat-empty,[data-testid="stExpander"]{animation:softReveal .5s cubic-bezier(.2,.75,.25,1) both}
.card:hover{transform:translateY(-5px) scale(1.012);box-shadow:0 12px 26px rgba(25,45,68,.11)}
.row:hover{transform:translateX(5px);box-shadow:0 8px 20px rgba(25,45,68,.1)}
.stButton>button,.stDownloadButton>button,.stLinkButton>a{position:relative;overflow:hidden;transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease}
.stButton>button::after,.stDownloadButton>button::after,.stLinkButton>a::after{content:"";position:absolute;top:-60%;left:-80%;width:45%;height:220%;transform:rotate(22deg);background:linear-gradient(90deg,transparent,rgba(196,154,58,.2),transparent);transition:left .55s ease;pointer-events:none}
.stButton>button:hover::after,.stDownloadButton>button:hover::after,.stLinkButton>a:hover::after{left:140%}
.stButton>button:hover,.stDownloadButton>button:hover,.stLinkButton>a:hover{transform:translateY(-2px);box-shadow:0 8px 18px rgba(25,45,68,.12)}
.stButton>button:active,.stDownloadButton>button:active{transform:scale(.975)}
[data-testid="stPlotlyChart"]{animation:chartReveal .7s cubic-bezier(.2,.75,.25,1) both}
[data-testid="stPlotlyChart"]:hover{transform:translateY(-3px);box-shadow:0 12px 26px rgba(25,45,68,.1)}
[data-testid="stExpander"] summary:hover{background:#fbf8f0!important}
[data-testid="stProgressBar"]>div>div{background-image:linear-gradient(90deg,#b78b2e,#dfbd64,#b78b2e)!important;background-size:200% 100%;animation:goldFlow 3s linear infinite}
.plink::after{animation:flow 2.1s linear infinite,goldPulse 1.8s ease-in-out infinite alternate}
.live-dot{animation:statusPulse 2s ease-out infinite}
.foot{animation:softReveal .75s .3s ease both}
@keyframes ambientDrift{0%{background-position:0% 0%,100% 100%}100%{background-position:100% 20%,0% 80%}}
@keyframes pageArrival{from{opacity:0;transform:translateY(9px)}to{opacity:1;transform:translateY(0)}}
@keyframes softReveal{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
@keyframes heroReveal{from{opacity:0;transform:translateY(14px) scale(.99)}to{opacity:1;transform:translateY(0) scale(1)}}
@keyframes heroTint{0%{background-position:0% 40%}100%{background-position:100% 65%}}
@keyframes goldHalo{0%{transform:translate(-10px,5px) scale(.9);opacity:.45}100%{transform:translate(18px,-10px) scale(1.12);opacity:.9}}
@keyframes scoreReveal{from{opacity:0;transform:scale(.85) rotate(-5deg)}to{opacity:1;transform:scale(1) rotate(0)}}
@keyframes ringFill{from{--p:0%;transform:rotate(-35deg)}to{--p:var(--target);transform:rotate(0)}}
@keyframes ringBreath{0%,100%{filter:drop-shadow(0 0 0 rgba(196,154,58,0))}50%{filter:drop-shadow(0 0 8px rgba(196,154,58,.24))}}
@keyframes numberReveal{from{opacity:.2;transform:scale(.7)}to{opacity:1;transform:scale(1)}}
@keyframes chipReveal{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:translateY(0)}}
@keyframes metricReveal{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
@keyframes chartReveal{from{opacity:0;transform:translateY(10px) scale(.995)}to{opacity:1;transform:translateY(0) scale(1)}}
@keyframes navSelect{from{background:#203b58}to{background:#2a4058}}
@keyframes goldFlow{from{background-position:100% 0}to{background-position:-100% 0}}
@keyframes goldPulse{from{filter:brightness(.9)}to{filter:brightness(1.25)}}
@keyframes statusPulse{0%{box-shadow:0 0 0 0 rgba(116,198,165,.55)}70%,100%{box-shadow:0 0 0 8px rgba(116,198,165,0)}}
.consultant-brief{position:relative;overflow:hidden;margin:0 0 17px;padding:17px 19px 19px;border:1px solid #d8c694;border-left:5px solid var(--gold);border-radius:13px;background:linear-gradient(110deg,#fff 0%,#fbfaf6 68%,#f5efdf 100%);box-shadow:0 6px 18px rgba(25,45,68,.05);animation:briefArrival .7s .08s both}
.consultant-brief::after{content:"";position:absolute;top:0;bottom:0;left:-35%;width:20%;background:linear-gradient(90deg,transparent,rgba(255,255,255,.7),transparent);transform:skewX(-18deg);animation:briefSweep 7s 1.1s ease-in-out infinite}
.brief-top{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:13px}.brief-eyebrow{color:#71591f;font-size:.68rem;font-weight:850;letter-spacing:.1em;text-transform:uppercase}.brief-scenario{padding:5px 9px;border:1px solid #e4d5ae;border-radius:99px;background:#fbf6e9;color:#624d1c;font-size:.72rem;font-weight:750}
.brief-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:0}.brief-grid article{padding:4px 17px;border-right:1px solid #e4e8ed;min-width:0}.brief-grid article:first-child{padding-left:0}.brief-grid article:last-child{border-right:0;padding-right:0}.brief-grid small{display:block;margin-bottom:6px;color:#607286;font-size:.63rem;font-weight:850;letter-spacing:.08em}.brief-grid strong{display:block;color:var(--navy);font-size:.98rem;line-height:1.35}.brief-grid span{display:block;margin-top:5px;color:#586b80;font-size:.78rem;line-height:1.4}
.mission-path{margin:10px 0 15px;padding:11px 9px 9px;border:1px solid #3b5570;border-radius:10px;background:rgba(8,24,42,.38);display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}
.mission-step{display:flex;align-items:center;gap:6px;min-width:0;padding:6px 4px;border-radius:7px;color:#b7c6d4;animation:stepIn .45s both;animation-delay:calc(var(--step,0)*70ms)}
.mission-step span{display:grid;place-items:center;flex:0 0 22px;height:22px;border:1px solid #60738a;border-radius:50%;color:#dbe4ec;font-size:.58rem;font-weight:800}.mission-step b{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#c5d0db;font-size:.63rem;font-weight:650}
.mission-step.done span{border-color:#9ccbb2;background:#254d43;color:#fff}.mission-step.done b{color:#e0eee7}.mission-step.active{background:#304760;box-shadow:0 0 0 1px rgba(226,187,98,.45),0 4px 14px rgba(0,0,0,.13);animation:stepIn .45s both,stepGlow 2.8s .5s ease-in-out infinite}.mission-step.active span{border-color:#e2bb62;background:#e2bb62;color:#142b46}.mission-step.active b{color:#fff;font-weight:800}
.decision-meter{margin:11px 0;padding:16px 17px 13px;border:1px solid var(--line);border-left:4px solid var(--meter-color);border-radius:11px;background:#fff;box-shadow:0 4px 15px rgba(25,45,68,.045);animation:meterArrival .55s both}
.meter-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:16px}.meter-head>div{display:flex;flex-direction:column;gap:4px}.meter-kicker{color:#435a71;font-size:.9rem;font-weight:800}.meter-head strong{color:var(--navy);font-size:1.45rem;letter-spacing:-.025em}
.meter-track{position:relative;height:13px;margin:0 5px 11px;border-radius:99px;background:linear-gradient(90deg,#e7f1eb 0 var(--meter-warn),#fbf1d7 var(--meter-warn) var(--meter-fail),#f6e6e8 var(--meter-fail) 100%);box-shadow:inset 0 1px 2px rgba(25,45,68,.12);overflow:visible}
.meter-marker{position:absolute;top:-4px;width:2px;height:21px;border-radius:2px;background:#344a60;opacity:.72}.warn-marker{left:var(--meter-warn)}.fail-marker{left:var(--meter-fail);background:#9a3d46}
.meter-current{position:absolute;top:50%;left:var(--meter-value);width:17px;height:17px;border:3px solid #fff;border-radius:50%;background:var(--meter-color);box-shadow:0 0 0 2px var(--meter-color),0 2px 7px rgba(25,45,68,.25);transform:translate(-50%,-50%);animation:markerPop .7s cubic-bezier(.2,.8,.2,1) both,meterPulse 2.2s 1s ease-out infinite}
.meter-legend{display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;color:#53677b;font-size:.68rem;font-weight:650}.meter-legend span:nth-child(2){color:#72591d}.meter-legend span:nth-child(3){color:#913c43}
[data-testid="stSidebar"] label,[data-testid="stSidebar"] label *{color:#f2f5f8!important;-webkit-text-fill-color:#f2f5f8!important;opacity:1!important}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"],[data-testid="stSidebar"] [data-testid="stCaptionContainer"] *{color:#c2cfdb!important;-webkit-text-fill-color:#c2cfdb!important;opacity:1!important}
[data-testid="stSidebar"] [data-baseweb="select"],[data-testid="stSidebar"] [data-baseweb="select"] *{color:#20364c!important;-webkit-text-fill-color:#20364c!important}
[data-testid="stSidebar"] .side-title{color:#f0c75e!important;-webkit-text-fill-color:#f0c75e!important}
[data-testid="stSidebar"] .brand,[data-testid="stSidebar"] .brand *{color:#fff!important;-webkit-text-fill-color:#fff!important}[data-testid="stSidebar"] .brand i{color:#142b46!important;-webkit-text-fill-color:#142b46!important}
[data-testid="stSidebar"] .side-intro,[data-testid="stSidebar"] .side-intro *{color:#f3e4bd!important;-webkit-text-fill-color:#f3e4bd!important}[data-testid="stSidebar"] .side-intro p{color:#e0e8ef!important;-webkit-text-fill-color:#e0e8ef!important}
[data-testid="stSidebar"] .side-status,[data-testid="stSidebar"] .side-status *{color:#f2f5f8!important;-webkit-text-fill-color:#f2f5f8!important}[data-testid="stSidebar"] .side-status small,[data-testid="stSidebar"] .side-author small{color:#cbd6df!important;-webkit-text-fill-color:#cbd6df!important}[data-testid="stSidebar"] .side-author b{color:#fff!important;-webkit-text-fill-color:#fff!important}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked),[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) *{color:#fff!important;-webkit-text-fill-color:#fff!important}
[data-testid="stMain"] .h3,[data-testid="stMain"] h1,[data-testid="stMain"] h2,[data-testid="stMain"] h3{color:#142b46!important;-webkit-text-fill-color:#142b46!important;opacity:1!important}
[data-testid="stMain"] .stButton>button[kind="primary"],[data-testid="stMain"] .stButton>button[kind="primary"] *,[data-testid="stMain"] .stDownloadButton>button[kind="primary"],[data-testid="stMain"] .stDownloadButton>button[kind="primary"] *{color:#fff!important;-webkit-text-fill-color:#fff!important}
@keyframes briefArrival{from{opacity:0;transform:translateY(12px) scale(.99)}to{opacity:1;transform:translateY(0) scale(1)}}@keyframes briefSweep{0%,70%{left:-35%}100%{left:130%}}
@keyframes stepIn{from{opacity:0;transform:translateX(-7px)}to{opacity:1;transform:translateX(0)}}@keyframes stepGlow{0%,100%{box-shadow:0 0 0 1px rgba(226,187,98,.35),0 4px 14px rgba(0,0,0,.1)}50%{box-shadow:0 0 0 2px rgba(226,187,98,.75),0 5px 20px rgba(226,187,98,.14)}}
@keyframes meterArrival{from{opacity:0;transform:translateY(9px)}to{opacity:1;transform:translateY(0)}}@keyframes markerPop{from{opacity:0;scale:.4}to{opacity:1;scale:1}}@keyframes meterPulse{0%,100%{box-shadow:0 0 0 2px var(--meter-color),0 2px 7px rgba(25,45,68,.25)}50%{box-shadow:0 0 0 6px rgba(196,154,58,.25),0 2px 8px rgba(25,45,68,.22)}}
@media(max-width:650px){.brief-grid{grid-template-columns:1fr;gap:10px}.brief-grid article,.brief-grid article:first-child,.brief-grid article:last-child{border-right:0;border-bottom:1px solid #e4e8ed;padding:9px 0}.brief-grid article:last-child{border-bottom:0}.meter-head{align-items:flex-start;flex-direction:column}.mission-path{grid-template-columns:repeat(2,minmax(0,1fr))}.meter-legend{font-size:.62rem}}
@media(prefers-reduced-motion:reduce){.stApp,[data-testid="stMain"]>.block-container,*,*::before,*::after{animation:none!important;transition:none!important;scroll-behavior:auto!important}}
</style>"""
st.markdown(ACCESSIBILITY_AND_MOTION, unsafe_allow_html=True)


# ───────────────────────────── données ─────────────────────────────


def fmt(v, digits: int = 0) -> str:
    """Format français ; espace fine insécable pour que « 120 000 » ne se coupe jamais."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "N/D"
    return f"{v:,.{digits}f}".replace(",", "\u202f").replace(".", ",")


def eur_m(v) -> str:
    return "N/D" if v is None else f"{fmt(v / 1e6, 1)}\u00a0M€"


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
    if not all(
        np.isfinite(float(v)) and float(v) >= 0
        for v in (c["panier_moyen"], c["chiffre_affaires_commandes"])
    ):
        raise ValueError("Panier moyen ou chiffre d’affaires négatif ou non fini.")
    return enrich(
        {
            "orders": orders,
            "missing": missing,
            "known": orders - missing,
            "basket": float(c["panier_moyen"]),
            "deliveries": deliveries,
            "late": late,
            "known_rev": float(c["chiffre_affaires_commandes"]),
            "missing_pct": 100 * missing / orders,
            "complete_pct": 100 * (orders - missing) / orders,
            "late_pct": 100 * late / deliveries,
        }
    )


@st.cache_data(ttl=300, show_spinner="Chargement des indicateurs…")
def load_metrics(demo: bool) -> dict:
    """Mis en cache 5 min : avant, 3 requêtes SQL partaient à chaque interaction."""
    return {
        s: (metrics_from_reference(s) if demo else metrics_from_db(s))
        for s in SCENARIOS
    }


VERDICT = {
    "go": ("Publiable", "v-go"),
    "warn": ("Publiable avec réserves", "v-warn"),
    "stop": ("À bloquer", "v-stop"),
}


def score_color(s: float) -> str:
    return MINT if s >= 80 else AMBER if s >= 65 else CORAL


def recommendations(d: dict, th: dict | None = None) -> list[dict]:
    """Les seuils sont réglables dans la Porte de décision."""
    th = th or DEFAULT_TH
    recs = []
    if d["missing_pct"] > th["m_fail"]:
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
        sev = "high" if d["missing_pct"] > th["m_warn"] else "mid"
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
    if d["late_pct"] > th["l_warn"]:
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


@lru_cache(maxsize=64)
def _mc(
    missing: int, basket: float, sigma: float, n: int = 20000, seed: int = 7
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    ratio = rng.lognormal(mean=-0.5 * sigma**2, sigma=sigma, size=n)
    return missing * basket * ratio / 1e6


def monte_carlo(d: dict, sigma: float) -> np.ndarray:
    """Exposition (M€) si le panier des commandes sans montant est log-normal de moyenne 1× le panier connu.
    Mis en cache : 20 000 tirages n'étaient plus recalculés qu'une fois par jeu de paramètres.
    Un tirage représente le panier moyen inconnu du groupe, pas chaque commande (scénario subjectif, non calibré)."""
    return _mc(int(d["missing"]), float(d["basket"]), round(float(sigma), 4))


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
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(color="#344a60", family="Arial, sans-serif", size=12),
        margin=dict(l=12, r=12, t=28, b=12),
        hoverlabel=dict(bgcolor="#142b46", font_color="#ffffff", bordercolor="#c49a3a"),
        legend=dict(orientation="h", y=-0.18, font=dict(color="#344a60")),
        transition=dict(duration=250, easing="cubic-in-out"),
    )
    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        linecolor="#d5dde5",
        tickfont=dict(color="#53677b"),
    )
    fig.update_yaxes(
        gridcolor="#e7ecf1", zeroline=False, tickfont=dict(color="#53677b")
    )
    return fig


def show(fig: go.Figure) -> None:
    """Un seul point d'affichage : barre d'outils Plotly masquée, largeur adaptative."""
    st.plotly_chart(fig, config=PLOT_CONFIG, **STRETCH)


def page_head(title: str, text: str) -> None:
    st.markdown(
        f'<div class="pagehead"><h2 style="color:#142b46!important;opacity:1">{esc(title)}</h2>'
        f'<p style="color:#40566d!important;opacity:1">{esc(text)}</p></div>',
        unsafe_allow_html=True,
    )


def h3(text: str) -> None:
    st.markdown(
        f'<div class="h3" style="color:#142b46!important;-webkit-text-fill-color:#142b46!important;opacity:1">{esc(text)}</div>',
        unsafe_allow_html=True,
    )


def decision_meter(
    name: str, value: float, warn: float, fail: float, status: str
) -> None:
    """Jauge lisible des valeurs et seuils, sans modifier le calcul de décision."""
    scale = max(float(fail) * 1.25, float(value) * 1.15, 1.0)
    warn_pos = min(max(100 * float(warn) / scale, 0), 100)
    fail_pos = min(max(100 * float(fail) / scale, 0), 100)
    value_pos = min(max(100 * float(value) / scale, 0), 100)
    indicator = {"go": "#28765e", "warn": "#b7831e", "stop": "#a33e47"}[status]
    label, css_class = VERDICT[status]
    st.markdown(
        f'<section class="decision-meter" style="--meter-value:{value_pos:.2f}%;--meter-warn:{warn_pos:.2f}%;--meter-fail:{fail_pos:.2f}%;--meter-color:{indicator}">'
        f'<div class="meter-head"><div><span class="meter-kicker">{esc(name)}</span><strong>{fmt(value, 2)} %</strong></div>'
        f'<span class="verdict {css_class}">{esc(label)}</span></div>'
        f'<div class="meter-track" role="img" aria-label="Valeur {fmt(value, 2)} pour cent ; seuil de réserve {fmt(warn, 1)} ; seuil de blocage {fmt(fail, 1)}">'
        f'<span class="meter-marker warn-marker"></span><span class="meter-marker fail-marker"></span><span class="meter-current"></span></div>'
        f'<div class="meter-legend"><span>0 %</span><span>Réserve au-delà de {fmt(warn, 1)} %</span><span>Blocage au-delà de {fmt(fail, 1)} %</span><span>{fmt(scale, 1)} %</span></div></section>',
        unsafe_allow_html=True,
    )


def consultant_brief(d: dict, scenario: str, g: dict, recs: list[dict]) -> None:
    """Synthèse de mission courte, alimentée uniquement par les KPI et actions existants."""
    label, status_class = VERDICT[g["overall"]]
    first_action = recs[0]["t"] if recs else "Maintenir la surveillance"
    st.markdown(
        f'<section class="consultant-brief {status_class}"><div class="brief-top"><span class="brief-eyebrow">Brief consultant · 30 secondes</span>'
        f'<span class="brief-scenario">Scénario {SCENARIO_NAME[scenario]}</span></div>'
        f'<div class="brief-grid"><article><small>DÉCISION SIMULÉE</small><strong>{esc(label)}</strong><span>À valider par le responsable métier.</span></article>'
        f"<article><small>FAIT OBSERVÉ</small><strong>{fmt(d['missing_pct'], 2)} % de montants absents</strong><span>{fmt(d['missing'])} commandes sur {fmt(d['orders'])}.</span></article>"
        f"<article><small>PROCHAINE ACTION</small><strong>{esc(first_action)}</strong><span>Exposition calculée = hypothèse, pas une perte mesurée.</span></article></div></section>",
        unsafe_allow_html=True,
    )


def ledger(cells: list[tuple]) -> None:
    out = ""
    for i, (lab, val, note, pct, color) in enumerate(cells):
        bar = (
            f'<div class="bar" aria-hidden="true"><i style="width:{min(max(pct, 0), 100):.1f}%;background:{color};animation-delay:{i * 90}ms"></i></div>'
            if pct is not None
            else ""
        )
        out += f'<div class="cell fx" style="--i:{i};--accent:{color}"><div class="lab">{esc(lab)}</div><div class="val">{esc(val)}</div><div class="note">{esc(note)}</div>{bar}</div>'
    st.markdown(f'<div class="ledger" role="group">{out}</div>', unsafe_allow_html=True)


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
    head = "".join(f'<th scope="col">{esc(h)}</th>' for h in headers)
    body = "".join(
        f'<tr class="{"sel" if i == selected else ""}"'
        + (' aria-current="true"' if i == selected else "")
        + ">"
        + "".join(f"<td>{c}</td>" for c in r)
        + "</tr>"
        for i, r in enumerate(rows)
    )
    st.markdown(
        f'<div class="tblwrap"><table class="tbl"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>',
        unsafe_allow_html=True,
    )


def verdict_badge(g: dict) -> str:
    label, cls = VERDICT[g["overall"]]
    return f'<span class="verdict {cls}">{label}</span>'


def link_btn(label: str, url: str, icon: str) -> None:
    """Icône Material si la version de Streamlit le permet, sinon bouton simple."""
    try:
        st.link_button(label, url, icon=icon, **STRETCH)
    except TypeError:
        st.link_button(label, url, **STRETCH)


def initials(name: str) -> str:
    return "".join(w[0] for w in re.findall(r"[^\W\d_]+", name)[:2]).upper() or "?"


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
IDENTITY_PATTERNS = (
    r"\bqui es[ -]?tu\b",
    r"\btu es qui\b",
    r"\bqui etes[ -]?vous\b",
    r"\bpresente[ -]?toi\b",
    r"\bton role\b",
    r"\bque fais[ -]?tu\b",
    r"\bc.est quoi consultai\b",
    r"\bwhat are you\b",
)


def _num(m: re.Match | None) -> float | None:
    return float(m.group(1).replace(",", ".")) if m else None


def respond(question: str, scenario: str, allm: dict, th: dict, ctx: dict) -> dict:
    """Agent à outils : détecte les intentions et entités, appelle des outils Python, trace chaque appel."""
    question, corrections = correct_question(question)
    # La ponctuation collée ("CA?") ne doit pas empêcher la détection des mots-clés (" ca ").
    qn = " " + re.sub(r"[?!;:]", " ", norm(question)) + " "
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
    sc = (
        named[0]
        if len(named) == 1
        else (
            ctx.get("scenario", scenario)
            if re.search(r"\b(et|encore|aussi|pourquoi|pareil|ce|celui)\b", qn)
            else scenario
        )
    )
    d = allm[sc]
    pct = _num(re.search(r"(-?\d+(?:[.,]\d+)?)\s*%", qn))
    mult = _num(re.search(r"(-?\d+(?:[.,]\d+)?)\s*(?:x|×|fois)(?:\s|$)", qn))
    target = _num(re.search(r"(-?\d+(?:[.,]\d+)?)\s*(?:m€|meur|millions?|m\s)", qn))

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
    if any(re.search(p, qn) for p in IDENTITY_PATTERNS):
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
    hs, g, recs = health(d), gate(d, th), recommendations(d, th)
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
                    f"| {SCENARIO_NAME[s]} | {fmt(m['missing_pct'], 1)} % | {fmt(m['basket'], 2)} € | {eur_m(m['exposure'])} | {VERDICT[gate(m, th)['overall']][0]} | {health(m)['score']:.0f} |"
                )
                T(
                    f"kpis('{s}')",
                    f"{fmt(m['missing'])} absents, panier {fmt(m['basket'], 2)} €",
                )
            spread = allm["critical"]["basket"] - allm["low"]["basket"]
            ratio = (
                allm["critical"]["exposure"] / allm["low"]["exposure"]
                if allm["low"]["exposure"]
                else None
            )
            parts.append(
                "\n".join(rows)
                + f"\n\nEntre faible et critique, le panier moyen ne bouge que de {fmt(spread, 2)} € mais l'exposition est multipliée par {fmt(ratio, 1)} (N/D si la référence est nulle). "
                + (
                    "Les retards sont identiques ; aucun effet causal n’est démontré."
                    if len({round(m["late_pct"], 6) for m in allm.values()}) == 1
                    else "Les taux de retard diffèrent ; une segmentation est nécessaire pour comprendre les écarts."
                )
            )
        elif intent == "simulate":
            p = pct if pct is not None else ctx.get("pct", d["missing_pct"])
            r = mult if mult is not None else ctx.get("mult", 1.0)
            if not 0 <= p <= 100:
                parts.append("Le taux simulé doit être compris entre 0 et 100 %.")
                continue
            if r <= 0 or not np.isfinite(r):
                parts.append(
                    "Le multiplicateur de panier doit être strictement positif et fini."
                )
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
                f"À **{fmt(p, 1)} %** de montants absents (scénario {SCENARIO_NAME[sc]}), **{fmt(n)} commandes** n'auraient pas de montant, soit {fmt(n - d['missing'])} de plus que l'observé. "
                f"Avec un panier à {fmt(r, 2)}× le panier connu ({fmt(d['basket'], 2)} €), l'exposition est d'environ **{eur_m(expo)}**, "
                f"soit {fmt(share, 1)} % du chiffre d'affaires total hypothétique.\n\nC'est une hypothèse : le Laboratoire de scénarios propose aussi une simulation Monte Carlo."
            )
            ctx.update(pct=p, mult=r)
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
                f"Dans le scénario {SCENARIO_NAME[sc]}, {fmt(d['missing'])} commandes n'ont pas de montant. À panier moyen, le chiffre d'affaires non vérifiable est d'environ **{eur_m(d['exposure'])}**. "
                f"Sous une hypothèse log-normale non calibrée (sigma=0,15), la fourchette P5–P95 va de **{fmt(q5, 1)} à {fmt(q95, 1)} M€**. Le CA documenté est de {eur_m(d['known_rev'])}.\n\n"
                "Ce n'est pas une perte : ces commandes existent, leur montant est absent."
            )
        elif intent == "solve":
            if target is not None:
                if target <= 0 or (mult is not None and mult <= 0):
                    parts.append(
                        "La cible d’exposition et le multiplicateur doivent être strictement positifs."
                    )
                    continue
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
                    f"Pour atteindre **{fmt(target, 1)} M€** d'exposition dans le scénario {SCENARIO_NAME[sc]}, il faudrait environ **{fmt(p, 1)} %** de commandes sans montant"
                    + (
                        f", soit {fmt(d['orders'] * p / 100)} commandes."
                        if p <= 100
                        else ". C'est supérieur à 100 % : la cible dépasse le chiffre d'affaires total."
                    )
                    + f" Le scénario {SCENARIO_NAME[sc]} est à {fmt(d['missing_pct'], 1)} %."
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
                    f"Les réserves commencent à {fmt(th['m_warn'], 1)} %. Le scénario {SCENARIO_NAME[sc]} est à {fmt(d['missing_pct'], 1)} % : "
                    + (
                        f"il reste {fmt(margin, 1)} point(s) de marge avant le blocage."
                        if margin >= 0
                        else f"il dépasse le seuil de {fmt(-margin, 1)} point(s)."
                    )
                )
                formulas.append("seuils réglables dans la Porte de décision")
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


def _local_ollama_host() -> str:
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    parsed = urlparse(host)
    if parsed.scheme not in ("http", "https") or parsed.hostname not in (
        "localhost",
        "127.0.0.1",
        "::1",
    ):
        raise ValueError(
            "Ollama doit utiliser une adresse locale (localhost ou 127.0.0.1)."
        )
    return host.rstrip("/")


def ollama_answer(question: str, allm: dict, history: list[dict], base: dict) -> dict:
    """Le modèle local ne calcule rien : il rédige à partir des résultats d'outils, puis chaque nombre est recoupé."""
    host = _local_ollama_host()  # validé AVANT toute construction de requête
    model = st.session_state.get("chat_model") or os.getenv(
        "CONSULTAI_OLLAMA_MODEL", "llama3.2:1b"
    )
    facts = "\n".join(
        f"- {SCENARIO_NAME[s]}: commandes {fmt(m['orders'])}, montants absents {fmt(m['missing'])} ({fmt(m['missing_pct'], 2)} %), panier moyen {fmt(m['basket'], 2)} €, "
        f"retards {fmt(m['late'])} sur {fmt(m['deliveries'])} ({fmt(m['late_pct'], 2)} %), CA non vérifiable {eur_m(m['exposure'])}"
        for s, m in allm.items()
    )
    verified = base["text"]
    style = st.session_state.get("response_style", "Conversation")
    system = (
        "Tu es l'analyste de ConsultAI 360 (entreprise fictive NexaRetail, données synthétiques). Réponds en français, avec un ton naturel de collègue analyste. Réponds directement, rebondis sur la demande et pose une seule question précise si le besoin est ambigu. Adapte la longueur au besoin. Évite les formules répétitives, les longues listes systématiques et le jargon. Utilise le contexte des échanges, mais les chiffres actuels ci-dessous priment sur les anciens messages. Si la demande porte sur une méthode, explique-la avec les connaissances générales en la distinguant des résultats observés. Ne prétends jamais avoir exécuté une requête ou une action métier.  "
        "Appuie-toi UNIQUEMENT sur les KPI et les RÉSULTATS VÉRIFIÉS ci-dessous. Ne change aucun chiffre, n'en invente aucun, ne conclus jamais à une causalité. "
        "Évite les listes numérotées et tout chiffre nouveau, y compris coûts, délais et pourcentages supposés. Si les résultats ne répondent pas à la question, demande une précision. Format demandé : "
        + style
        + ".\n\nKPI :\n"
        + facts
        + "\n\nRÉSULTATS VÉRIFIÉS :\n"
        + verified
    )
    msgs = (
        [{"role": "system", "content": system}]
        + [{"role": h["role"], "content": h["content"]} for h in history[-12:]]
        + [{"role": "user", "content": question}]
    )
    req = urllib.request.Request(
        host + "/api/chat",
        headers={"Content-Type": "application/json"},
        data=json.dumps(
            {
                "model": model,
                "stream": False,
                "options": {"temperature": 0.25, "num_predict": 900},
                "messages": msgs,
            }
        ).encode(),
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        text = json.load(r)["message"]["content"]
    allowed = _tokens(facts + " " + verified)
    unknown = sorted(t for t in _tokens(text) if t not in allowed)
    ev = base["evidence"] + [f"rédaction par le modèle local : {model}"]
    accepted = bool(text.strip()) and not unknown
    if not accepted:
        ev.append(
            "nombres non retrouvés dans les résultats d'outils : " + ", ".join(unknown)
        )
        text = base["text"]
        ev.append("Reformulation rejetée : réponse déterministe utilisée à la place.")
    return {
        **base,
        "text": text,
        "evidence": ev,
        "intent": base["intent"] + (" + ollama" if accepted else ""),
    }


# ── Expérience enrichie : analyse, conversation et mouvement ──
EXPERIENCE_CSS = """<style>
:root{--gold:#c49a3a;--navy:#142b46;--txt:#1d2d40}
html{font-size:17px!important}.ledger{grid-template-columns:repeat(auto-fit,minmax(min(100%,190px),1fr))!important}.cell{position:relative;border-top:4px solid var(--accent,#2563eb);background:linear-gradient(135deg,#fff 65%,color-mix(in srgb,var(--accent,#2563eb) 10%,white))!important}
.cell .val{color:var(--accent,#142b46)!important;font-size:clamp(1.5rem,2.3vw,2.2rem)!important;font-variant-numeric:tabular-nums}.cell .lab{color:#344b62!important}.cell .note{color:#40566d!important}.cell:hover{transform:translateY(-3px)}
.mini>div:nth-child(3n+1){border-top:3px solid #2563eb}.mini>div:nth-child(3n+2){border-top:3px solid #d99000}.mini>div:nth-child(3n){border-top:3px solid #0d9488}
.stApp [data-testid="stButton"] button:disabled{opacity:.55!important;transform:none!important;cursor:not-allowed!important}
[data-testid="stSidebar"] label,[data-testid="stSidebar"] label *{color:#f2f5f8!important;-webkit-text-fill-color:#f2f5f8!important}
[data-testid="stSidebar"] [data-baseweb="select"] *{color:#142b46!important;-webkit-text-fill-color:#142b46!important}
[data-testid="stMain"] .stButton button[kind="primary"] *,[data-testid="stMain"] .stDownloadButton button[kind="primary"] *{color:white!important;-webkit-text-fill-color:white!important}
[data-testid="stMain"] [data-testid="stWidgetLabel"] *{color:#20364c!important;-webkit-text-fill-color:#20364c!important}
[data-baseweb="tab"]{color:#142b46!important;font-weight:700!important;padding:12px!important}[aria-selected="true"][data-baseweb="tab"]{background:#f5ecd7!important;border-radius:9px 9px 0 0}
.h3{position:relative;padding-left:13px;color:#142b46!important}.h3::before{content:"";position:absolute;left:0;top:5px;bottom:5px;width:4px;border-radius:8px;background:linear-gradient(#2563eb,#d99000);animation:sectionPulse 3s ease-in-out infinite}
.decision-meter,.consultant-brief{transition:transform .3s,box-shadow .3s}.decision-meter:hover{transform:translateY(-3px);box-shadow:0 12px 30px #142b4618}
[data-testid="stChatMessage"]{animation:messageArrival .45s cubic-bezier(.2,.9,.3,1) both!important}[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]){border-left:4px solid #2563eb!important}
[data-testid="stChatInput"]:focus-within{animation:inputHalo 2s ease-in-out infinite}.bar i{animation:barLaunch 1.3s cubic-bezier(.15,.9,.25,1) both!important}
.card .ic{transition:transform .4s,background .4s}.card:hover .ic{transform:rotate(-12deg) scale(1.18);background:#f0dca6}
.tbl tr{transition:background .2s}.tbl tr:hover td{background:#edf5ff!important}.tbl tr.sel td:first-child{box-shadow:inset 4px 0 #2563eb}
.stButton button[kind="primary"],.stDownloadButton button[kind="primary"]{animation:primaryGlow 4s ease-in-out infinite}
@keyframes sectionPulse{50%{filter:brightness(1.25);transform:scaleY(.7)}}@keyframes messageArrival{from{opacity:0;transform:translateY(12px) scale(.99)}to{opacity:1;transform:none}}
@keyframes inputHalo{50%{box-shadow:0 0 0 5px #2563eb16}}@keyframes barLaunch{from{transform:scaleX(0)}to{transform:scaleX(1)}}@keyframes primaryGlow{50%{box-shadow:0 4px 18px #2563eb32}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important}}
</style>"""
st.markdown(EXPERIENCE_CSS, unsafe_allow_html=True)


@st.cache_data(ttl=30, show_spinner=False)
def local_models() -> tuple[list[str], str]:
    if PUBLIC:
        return [], "Démo : réponses calculées, modèle local désactivé"
    try:
        with urllib.request.urlopen(
            _local_ollama_host() + "/api/tags", timeout=2
        ) as response:
            names = sorted(
                {str(item["name"]) for item in json.load(response).get("models", [])}
            )
        return names, (
            "Modèle local disponible"
            if names
            else "Ollama accessible, aucun modèle installé"
        )
    except Exception:
        return [], "Modèle local indisponible · outils de calcul disponibles"


def conversational_answer(question, scenario, allm, th, ctx, history, style):
    """Suit les reprises de conversation et fournit une analyse vérifiable."""
    raw = norm(question).strip(" ?!. ")
    last = next((m for m in reversed(history) if m["role"] == "assistant"), None)
    if (
        raw
        in ("plus court", "resume", "resume ca", "en bref", "synthetise", "plus simple")
        and last
    ):
        paragraphs = [
            x.strip()
            for x in last["content"].split("\n\n")
            if x.strip() and not x.startswith("#")
        ]
        text = "\n\n".join(paragraphs[:2]) or last["content"]
        return {
            "text": text,
            "intent": "reformulation",
            "kind": "Synthèse",
            "scenario": last.get("scenario", scenario),
            "evidence": last.get("evidence", []),
            "followups": ["Développe l’analyse", "Que faire en priorité ?"],
        }
    if (
        raw
        in (
            "developpe",
            "detaille",
            "developpe l'analyse",
            "explique davantage",
            "et pourquoi",
            "pourquoi",
        )
        and last
    ):
        question = "Explique le diagnostic et les actions du scénario " + ctx.get(
            "scenario", scenario
        )
    if raw in ("merci", "merci beaucoup", "ok merci", "parfait"):
        return {
            "text": "Avec plaisir. Tu peux poursuivre avec une simulation, examiner les actions prioritaires ou préparer ta restitution.",
            "intent": "conversation",
            "kind": "Échange",
            "scenario": scenario,
            "evidence": [],
            "followups": ["Prépare ma restitution", "Que faire en priorité ?"],
        }
    normalized = raw.replace("’", "'")
    if any(
        t in normalized
        for t in (
            "analyse complete",
            "analyse approfondie",
            "analyse globale",
            "diagnostic complet",
            "prepare ma restitution",
        )
    ):
        m = allm[scenario]
        decision = gate(m, th)
        actions = recommendations(m, th)
        gap = th["m_fail"] - m["missing_pct"]
        text = (
            f"### Ce que je retiens\n\nLe scénario **{SCENARIO_NAME[scenario]}** est **{VERDICT[decision['overall']][0].lower()}** selon tes seuils. "
            f"Il manque le montant de **{fmt(m['missing'])} commandes**, soit **{fmt(m['missing_pct'], 2)} %**. "
            f"Le taux de retard est de **{fmt(m['late_pct'], 2)} %** sur les livraisons évaluables.\n\n"
            f"### Ce que cela implique\n\nLe CA documenté est **{eur_m(m['known_rev'])}**. L’exposition estimée de **{eur_m(m['exposure'])}** repose sur l’hypothèse du panier moyen connu. "
            f"La distance au seuil de blocage des montants est de **{fmt(gap, 2)} points de pourcentage**.\n\n"
            "### Ce que je te propose\n\n"
            + "\n".join(
                f"{i}. **{a['t']}** — {a['why']}" for i, a in enumerate(actions[:3], 1)
            )
            + "\n\n**À vérifier ensuite :** répartition des montants absents par magasin, canal et période. Les agrégats disponibles ne permettent pas de localiser les causes."
        )
        ctx.update(scenario=scenario, intent="risk")
        return {
            "text": text,
            "intent": "diagnostic_complet",
            "kind": "Analyse vérifiée",
            "scenario": scenario,
            "evidence": [
                "KPI du scénario actif",
                "gate() : seuils actifs",
                "recommendations() : priorité impact/effort",
                "Exposition : montants absents × panier connu",
            ],
            "followups": [
                "Et pour le scénario critique ?",
                "Et si 15 % des montants manquaient ?",
                "Rédige une note de décision",
            ],
        }
    result = respond(question, scenario, allm, th, ctx)
    if result["intent"] == "aucune":
        result["text"] = (
            "Pour t’aider précisément, quel angle veux-tu examiner : les montants absents, les retards, la publication du CA ou la méthode d’analyse ? Tu peux aussi me décrire la décision que tu prépares."
        )
    result["text"] = result["text"].replace(
        "Bonjour. Pose-moi une question sur la qualité des données NexaRetail, ou clique sur une suggestion.",
        "Bonjour. On peut partir de ton objectif : comprendre les risques, décider quoi publier ou préparer les actions. Quel point veux-tu creuser ?",
    )
    if (
        style == "Synthèse"
        and result["intent"] not in ("compare", "memo")
        and not result["intent"].startswith("projet_")
    ):
        result["text"] = "\n\n".join(result["text"].split("\n\n")[:3])
    elif style == "Analyse détaillée" and result["intent"] in (
        "risk",
        "actions",
        "gate",
    ):
        result["text"] += (
            "\n\n**Pour vérifier ce diagnostic :** rapprocher les montants avec la source, contrôler les jointures et comparer les taux par magasin, canal et période avant d’attribuer une cause."
        )
    ctx["last_question"] = question
    return result


def render_signal_console(d, scenario):
    import streamlit.components.v1 as components

    motion = st.session_state.get("motion_level", "Intenses")
    values = json.dumps(
        [
            int(d["orders"]),
            int(d["missing"]),
            round(float(d["complete_pct"]), 1),
            round(float(d["late_pct"]), 1),
        ]
    )
    document = r"""<!doctype html><html lang="fr"><meta charset="utf-8"><style>
    *{box-sizing:border-box}body{margin:0;color:#f6f9ff;font:14px Arial;background:#142b46}section{position:relative;overflow:hidden;border-radius:14px;padding:20px;background:radial-gradient(ellipse at 90% 20%,#23527c,transparent 65%),#142b46;min-height:185px}.top{display:flex;justify-content:space-between;align-items:center}.top span{color:#f0c75e;font-size:11px;letter-spacing:2px;font-weight:bold}button{border:1px solid #8aa1b7;border-radius:6px;background:#ffffff0d;color:white;padding:5px 9px;cursor:pointer}.flow{display:flex;align-items:center;margin:19px 0}.node{border:1px solid #7295b1;border-radius:9px;padding:9px 12px;background:#ffffff0b;z-index:1}.link{height:3px;flex:1;position:relative;background:#42607c;overflow:hidden}.link:before{content:'';position:absolute;width:24px;height:3px;background:#f0c75e;box-shadow:0 0 10px #f0c75e;animation:packet 1.6s linear infinite}.link:nth-child(4):before{animation-delay:.5s}.link:nth-child(6):before{animation-delay:1s}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.stats b{display:block;font-size:23px;color:#fff;font-variant-numeric:tabular-nums}.stats small{color:#c6d6e4;font-size:11px}.note{margin-top:10px;color:#b6c9da;font-size:10px}.paused *,.paused *:before{animation-play-state:paused!important}@keyframes packet{from{left:-24px}to{left:100%}}@media(max-width:600px){section{padding:12px}.node{padding:8px 5px;font-size:11px}.stats b{font-size:18px}}@media(prefers-reduced-motion:reduce){*,:before{animation:none!important}}
    </style><section id="signal"><div class="top"><span>PARCOURS DES DONNÉES · __SCENARIO__</span><button id="pause" aria-pressed="false">Pause</button></div><div class="flow"><div class="node">Source</div><div class="link"></div><div class="node">Contrôles</div><div class="link"></div><div class="node">Analyse</div><div class="link"></div><div class="node">Décision</div></div><div class="stats"><div><b id="n0"></b><small>commandes</small></div><div><b id="n1"></b><small>montants absents</small></div><div><b id="n2"></b><small>complétude</small></div><div><b id="n3"></b><small>retards</small></div></div><div class="note">Animation illustrative · valeurs du scénario sélectionné · aucune activité en temps réel représentée</div></section><script>
    const vals=__VALUES__;const stopped=__STOP__;let pause=stopped;const root=document.getElementById('signal'),btn=document.getElementById('pause');if(stopped){root.classList.add('paused');btn.textContent='Reprendre';btn.setAttribute('aria-pressed','true')}btn.onclick=()=>{pause=!pause;root.classList.toggle('paused',pause);btn.textContent=pause?'Reprendre':'Pause';btn.setAttribute('aria-pressed',String(pause))};const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;let start=null;function frame(t){start??=t;const p=reduce||stopped?1:Math.min((t-start)/1100,1);vals.forEach((v,i)=>document.getElementById('n'+i).textContent=(i<2?Math.round(v*p):Math.round(v*p*10)/10).toLocaleString('fr-FR')+(i>1?' %':''));if(p<1)requestAnimationFrame(frame)}requestAnimationFrame(frame);
    </script></html>"""
    content = (
        document.replace("__VALUES__", values)
        .replace("__STOP__", "true" if motion == "Arrêt" else "false")
        .replace("__SCENARIO__", esc(SCENARIO_NAME[scenario]))
    )
    if motion == "Douces":
        content = content.replace(
            "</style>",
            ".link:before{animation-iteration-count:1!important;animation-duration:3s!important}</style>",
            1,
        )
    if hasattr(st, "iframe"):
        from urllib.parse import quote

        st.iframe(
            "data:text/html;charset=utf-8," + quote(content),
            height=205,
            alt="Parcours animé des données du scénario",
        )
    else:
        components.html(content, height=205, scrolling=False)


def render_workshop(d, allm, th, scenario):
    page_head(
        "Atelier d’analyse",
        "Relier la qualité des données à une décision, mesurer les écarts et préparer une restitution.",
    )
    a, b, c, dtab = st.tabs(
        ["Diagnostic", "Comparaison", "Plan de fiabilisation", "Restitution"]
    )
    with a:
        consultant_brief(d, scenario, gate(d, th), recommendations(d, th))
        left, right = st.columns(2)
        with left:
            h3("Pourquoi cet indice ?")
            hs = health(d)
            fig = go.Figure(
                go.Waterfall(
                    x=["Base", "Montants absents", "Retards", "Indice"],
                    y=[100, -hs["lost_missing"], -hs["lost_late"], 0],
                    measure=["absolute", "relative", "relative", "total"],
                    decreasing_marker_color=CORAL,
                    totals_marker_color=COBALT,
                    text=[
                        "100",
                        f"−{fmt(hs['lost_missing'], 1)}",
                        f"−{fmt(hs['lost_late'], 1)}",
                        fmt(hs["score"], 1),
                    ],
                    textposition="outside",
                )
            )
            show(plot_style(fig, 340))
            st.caption(
                "Indice pédagogique : contribution de chaque pénalité, sans interprétation causale."
            )
        with right:
            h3("Séparer volumes et dénominateurs")
            st.dataframe(
                pd.DataFrame(
                    {
                        "Population": [
                            "Commandes avec montant",
                            "Commandes sans montant",
                            "Livraisons à l’heure",
                            "Livraisons en retard",
                        ],
                        "Effectif": [
                            d["known"],
                            d["missing"],
                            d["deliveries"] - d["late"],
                            d["late"],
                        ],
                        "Périmètre": [
                            "Commandes",
                            "Commandes",
                            "Livraisons évaluables",
                            "Livraisons évaluables",
                        ],
                    }
                ),
                hide_index=True,
                **STRETCH,
            )
            st.info(
                "Les commandes et les livraisons évaluables sont deux populations distinctes. Leurs volumes ne s’additionnent pas."
            )
        h3("Distance aux seuils")
        rows = [
            {
                "Contrôle": "Montants absents",
                "Observé (%)": d["missing_pct"],
                "Réserves au-delà (%)": th["m_warn"],
                "Blocage au-delà (%)": th["m_fail"],
            },
            {
                "Contrôle": "Retards",
                "Observé (%)": d["late_pct"],
                "Réserves au-delà (%)": th["l_warn"],
                "Blocage au-delà (%)": th["l_fail"],
            },
        ]
        for row in rows:
            row["Marge avant blocage (points)"] = (
                row["Blocage au-delà (%)"] - row["Observé (%)"]
            )
        st.dataframe(pd.DataFrame(rows).round(2), hide_index=True, **STRETCH)
    with b:
        selected = st.selectbox(
            "Comparer au scénario",
            SCENARIOS,
            format_func=lambda x: SCENARIO_NAME[x],
            key="benchmark",
        )
        ref = allm[selected]
        mini(
            [
                (
                    "Écart de montants absents",
                    f"{fmt(d['missing_pct'] - ref['missing_pct'], 2)} points",
                ),
                ("Écart de CA documenté", eur_m(d["known_rev"] - ref["known_rev"])),
                (
                    "Écart de retards",
                    f"{fmt(d['late_pct'] - ref['late_pct'], 2)} points",
                ),
            ]
        )
        comparison = pd.DataFrame(
            [
                {
                    "Scénario": SCENARIO_NAME[k],
                    "Montants absents (%)": m["missing_pct"],
                    "Complétude (%)": m["complete_pct"],
                    "Retards (%)": m["late_pct"],
                    "CA documenté (€)": m["known_rev"],
                    "Exposition hypothétique (€)": m["exposure"],
                    "Indice": health(m)["score"],
                }
                for k, m in allm.items()
            ]
        )
        st.dataframe(comparison.round(2), hide_index=True, **STRETCH)
        st.download_button(
            "Exporter la comparaison",
            comparison.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
            "comparaison_scenarios.csv",
            "text/csv",
        )
        st.caption(
            "Écarts descriptifs entre jeux de données. Un écart entre scénarios n’établit pas de causalité."
        )
    with c:
        target = (
            st.slider(
                "Objectif de complétude (%)",
                float(d["complete_pct"]),
                100.0,
                100.0,
                0.1,
                key="recovery_target",
            )
            if d["complete_pct"] < 100
            else 100.0
        )
        required = max(0, int(np.ceil(d["orders"] * target / 100 - d["known"])))
        mini(
            [
                ("Commandes à renseigner", fmt(required)),
                ("Montants encore absents", fmt(d["missing"] - required)),
                ("Complétude cible", f"{fmt(target, 1)} %"),
            ]
        )
        rate = st.number_input(
            "Capacité de correction par jour (commandes)",
            min_value=1,
            value=500,
            step=50,
            key="daily_capacity",
        )
        st.info(
            f"À capacité constante, il faudrait environ {int(np.ceil(required / rate))} jours de traitement. C’est un scénario de charge : disponibilité des sources et validation métier ne sont pas modélisées."
        )
        xs = np.linspace(0, d["missing"], 30)
        fig = go.Figure(
            go.Scatter(
                x=xs,
                y=(d["known"] + xs) / d["orders"] * 100,
                mode="lines",
                fill="tozeroy",
                line=dict(color=MINT, width=4),
                fillcolor="rgba(13,148,136,.1)",
            )
        )
        fig.add_hline(
            y=target, line_color=AMBER, line_dash="dash", annotation_text="Objectif"
        )
        show(
            plot_style(fig, 320).update_layout(
                xaxis_title="Commandes dont le montant serait renseigné",
                yaxis_title="Complétude (%)",
            )
        )
        st.caption(
            "Renseigner un montant exige une preuve source ; ce graphique n’impute aucune valeur."
        )
    with dtab:
        audience = st.selectbox(
            "Destinataire de la restitution",
            ["Direction", "Responsable Data", "Responsable logistique"],
        )
        focus = {
            "Direction": "Décision de publication et risque de mauvaise interprétation.",
            "Responsable Data": "Sources, complétude, jointures et contrôles reproductibles.",
            "Responsable logistique": "Dénominateur des retards et segmentation transporteur/zone/période.",
        }[audience]
        st.info(focus)
        memo = memo_markdown(
            d, scenario, gate(d, th), health(d), recommendations(d, th)
        )
        st.markdown(memo)
        st.download_button(
            "Télécharger le brief",
            f"Destinataire : {audience}\nFocus : {focus}\n\n{memo}",
            f"brief_{scenario}.md",
            "text/markdown",
        )
        st.caption(
            "La restitution réutilise les calculs et les seuils actifs. Aucune décision n’est exécutée."
        )


# ───────────────────────────── barre latérale ─────────────────────────────

# Corriger l'etat du toggle avant de creer le widget.
if st.session_state.pop("force_demo_on_next_run", False):
    st.session_state["demo_mode"] = True

with st.sidebar:
    st.markdown(
        '<div class="brand"><i>◆</i><div>ConsultAI 360<small>INTELLIGENCE · DECISION · DATA</small></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="side-intro"><span class="live-dot"></span> ENVIRONNEMENT ANALYTIQUE <b>V4</b><p>Mission NexaRetail · cas fictif</p></div>',
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown(
        '<div class="side-title">Contexte de la mission</div>', unsafe_allow_html=True
    )
    scenario = st.selectbox(
        "Scénario de données",
        SCENARIOS,
        index=1,
        format_func=lambda s: SCENARIO_LABEL[s],
    )
    demo = st.toggle(
        "Mode démonstration",
        value=True,
        key="demo_mode",
        help="Activé : données de référence. Désactivé : PostgreSQL en local, ou explication sur le cloud.",
    )
    if PUBLIC and not demo:
        st.caption("PostgreSQL : disponible en local uniquement")
    else:
        st.caption(
            "Chiffres de référence figés" if demo else "PostgreSQL local, lecture seule"
        )
    st.divider()
    st.markdown(
        '<div class="side-title">Explorer la mission</div>', unsafe_allow_html=True
    )
    page = st.radio(
        "Navigation",
        PAGES,
        index=1,
        key="navigation",
        format_func=lambda p: f"{PAGE_ICONS[p]}  {PAGE_LABELS[p]}",
        label_visibility="collapsed",
    )
    phase_map = {
        "Atelier d’analyse": 0,
        "Mission Control": 0,
        "Observatoire": 0,
        "Investigation": 1,
        "Scenario Lab": 2,
        "Decision Gate": 3,
        "Data Lineage": 4,
        "AI Copilot": 5,
    }
    mission_steps = [
        "Observer",
        "Enquêter",
        "Simuler",
        "Décider",
        "Tracer",
        "Expliquer",
    ]
    active_phase = phase_map[page]
    st.markdown(
        '<div class="mission-path" aria-label="Étapes de la mission">'
        + "".join(
            f'<div class="mission-step {"active" if i == active_phase else "done" if i < active_phase else ""}" style="--step:{i}">'
            f"<span>{i + 1:02d}</span><b>{label}</b></div>"
            for i, label in enumerate(mission_steps)
        )
        + "</div>",
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown(
        '<div class="side-status"><div><span class="live-dot"></span> <b>Lecture analytique</b></div><small>Calculs SQL/Python · aucune écriture en base</small><small>Cas fictif · données synthétiques · décisions non exécutées</small></div>',
        unsafe_allow_html=True,
    )
    motion = st.selectbox(
        "Animations",
        ["Intenses", "Douces", "Arrêt"],
        key="motion_level",
        help="Les préférences d’accessibilité du navigateur restent prioritaires.",
    )
    if motion == "Arrêt":
        st.markdown(
            "<style>*,*::before,*::after{animation:none!important;transition:none!important}</style>",
            unsafe_allow_html=True,
        )
    elif motion == "Douces":
        st.markdown(
            "<style>*,*::before,*::after{animation-iteration-count:1!important;animation-duration:.45s!important}</style>",
            unsafe_allow_html=True,
        )
    st.markdown(
        '<div class="side-title">Projet &amp; profil</div>', unsafe_allow_html=True
    )
    author = author_profile() or {}
    a_name = str(author.get("name") or "Auteur du projet")
    a_role = str(author.get("role") or "")
    st.markdown(
        f'<div class="side-author"><span class="avatar" aria-hidden="true">{esc(initials(a_name))}</span><div><b>{esc(a_name)}</b><small>{esc(a_role)}</small></div></div>',
        unsafe_allow_html=True,
    )
    gh, li = str(author.get("github") or ""), str(author.get("linkedin") or "")
    if gh.startswith("https://github.com/"):
        link_btn("Code source (GitHub)", gh, ":material/code:")
    if li.startswith(("https://www.linkedin.com/", "https://linkedin.com/")):
        link_btn("Profil LinkedIn", li, ":material/work:")
    elif li:
        st.caption("Profil LinkedIn : lien non valide dans la configuration.")
# Sur le deploiement public, le mode PostgreSQL reste explicatif :
# ne jamais essayer de joindre une base locale depuis le cloud.
public_postgres_preview = PUBLIC and not demo
if public_postgres_preview:
    st.info(
        "**PostgreSQL en direct ? Pas encore sur cette version publique !** "
        "Pour financer un serveur PostgreSQL disponible 24 h/24, "
        "il me manque juste un petit détail : un stage ou un CDI. "
        "Recruteurs, vous savez ce qu'il vous reste à faire. 😉\n\n"
        "**En attendant :** le dashboard reste consultable avec les données de démonstration. "
        "Pour tester les vraies requêtes SQL, récupérez le projet sur "
        "[GitHub](https://github.com/NacPKZ/ConsultAI-360), configurez "
        "votre PostgreSQL local et lancez l'application chez vous."
    )
try:
    allm = load_metrics(True if public_postgres_preview else demo)
except Exception as exc:
    if demo:
        # Une erreur dans les données de référence doit rester visible.
        st.error("Impossible de charger les données de démonstration.")
        with st.expander("Détail technique"):
            st.code(f"{type(exc).__name__}: {exc}")
        st.stop()

    # PostgreSQL est optionnel : une base locale inaccessible ne doit pas
    # bloquer la consultation publique du portfolio.
    # Le widget existe deja : changer son etat seulement au prochain run.
    st.session_state["force_demo_on_next_run"] = True
    st.rerun()

d = allm[scenario]
hs = health(d)
st.session_state.setdefault("th", dict(DEFAULT_TH))
TH = safe_th(st.session_state["th"])
g = gate(d, TH)
recs = recommendations(d, TH)
source_chip = (
    "Référence figée · démo"
    if (demo or public_postgres_preview)
    else "PostgreSQL · cache de 5 min"
)


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
                f'<div class="kicker">ACTION {i:02d} · {esc(SCENARIO_NAME[scenario])}</div><b>{esc(r["t"])}</b><br><span style="color:#40566d;font-size:.86rem">{esc(r["why"])}</span>',
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
        pd.DataFrame(rows)
        .to_csv(index=False, sep=";")
        .encode("utf-8-sig"),  # « ; » : s'ouvre correctement dans Excel FR
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
                name=SCENARIO_NAME[s],
                text=[SCENARIO_NAME[s]],
                textposition="top center",
                textfont=dict(color=TXT),
                marker=dict(
                    size=26 if s == scenario else 16,
                    color=SCENARIO_COLORS[s],
                    line=dict(width=2, color="#ffffff"),
                ),
                hovertemplate="%{text}<br>Montants absents : %{x:.1f} %<br>Exposition hypothétique : %{y:.2f} M€<extra></extra>",
            )
        )
    plot_style(fig, 320).update_layout(
        xaxis_title="Commandes sans montant (%)",
        yaxis_title="Exposition hypothétique (M€)",
        showlegend=False,
    )
    fig.update_xaxes(
        range=[0, max(14, max(m["missing_pct"] for m in allm.values()) * 1.2)]
    ).update_yaxes(range=[0, max(allm[s]["exposure"] for s in SCENARIOS) / 1e6 * 1.3])
    return fig


def chart_exposure_waterfall(d: dict) -> go.Figure:
    """Pont entre CA documenté et CA hypothétique, sans présenter une estimation comme un fait."""
    known, assumed = d["known_rev"] / 1e6, d["exposure"] / 1e6
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
            textfont={"color": TXT},
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
    names = [SCENARIO_NAME[x] for x in SCENARIOS]
    known = [allm[x]["complete_pct"] for x in SCENARIOS]
    missing = [allm[x]["missing_pct"] for x in SCENARIOS]
    fig = go.Figure()
    fig.add_bar(
        y=names,
        x=known,
        orientation="h",
        name="Montants renseignés",
        marker_color=MINT,
        text=[f"{x:.1f} %" for x in known],
        textposition="inside",
        insidetextfont=dict(color="white"),
        hovertemplate="%{y} : %{x:.2f} % renseignés<extra></extra>",
    )
    fig.add_bar(
        y=names,
        x=missing,
        orientation="h",
        name="Montants absents",
        marker_color=AMBER,
        text=[f"{x:.1f} %" if x >= 3 else "" for x in missing],
        textposition="inside",
        insidetextfont=dict(color="#142b46"),
        hovertemplate="%{y} : %{x:.2f} % absents<extra></extra>",
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
        color = SCENARIO_COLORS[name]
        fig.add_trace(
            go.Scatter(
                x=x,
                y=(m["missing"] * m["basket"] * x) / 1e6,
                mode="lines",
                name=SCENARIO_NAME[name],
                line=dict(color=color, width=5 if name == scenario else 2.5),
                hovertemplate=f"{SCENARIO_NAME[name]}<br>Panier relatif : %{{x:.2f}}×<br>CA non vérifiable : %{{y:.2f}} M€<extra></extra>",
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
    """Profil comparatif. L'axe « Commandes avec montant » était identique à « Complétude » : supprimé."""
    categories = [
        "Complétude des montants",
        "Livraisons à l'heure",
        "Indice pédagogique",
    ]
    fig = go.Figure()
    for name in SCENARIOS:
        m = allm[name]
        vals = [m["complete_pct"], 100 - m["late_pct"], health(m)["score"]]
        fig.add_trace(
            go.Scatterpolar(
                r=vals + vals[:1],
                theta=categories + categories[:1],
                fill="toself" if name == scenario else "none",
                name=SCENARIO_NAME[name],
                line=dict(
                    color=SCENARIO_COLORS[name], width=4 if name == scenario else 2
                ),
                opacity=1 if name == scenario else 0.58,
            )
        )
    plot_style(fig, 410).update_layout(
        polar=dict(
            bgcolor="#ffffff",
            radialaxis=dict(
                range=[0, 100],
                showline=False,
                gridcolor="#e5eaf0",
                tickfont=dict(size=10, color="#53677b"),
            ),
            angularaxis=dict(gridcolor="#dce3eb", tickfont=dict(color="#344a60")),
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
        <div class="chips"><span><i class="dot"></i>{esc(source_chip)}</span><span>Scénario {esc(SCENARIO_NAME[scenario])}</span><span>Lecture seule</span></div>
        <h1 class="hero-title">{esc(title)}</h1><p class="hero-sub">{esc(sub)}</p></div>
        <div class="hero-score"><div class="ring" style="--target:{hs["score"]}%;--score:{round(hs["score"])};--c:{score_color(hs["score"])}" role="img" aria-label="Indice {hs["score"]:.0f} sur 100">
        <div class="ring-in"><b></b><span>sur 100</span></div></div>
        <span class="verdict {vcls}">{esc(vlabel)}</span><div class="hero-note">Indice de santé des données</div></div></div>""",
        unsafe_allow_html=True,
    )
    consultant_brief(d, scenario, g, recs)
    render_signal_console(d, scenario)
    # Les barres sont à l'échelle de leur seuil de référence (×5 et ×2 : même pondération que l'indice).
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
                x=[SCENARIO_NAME[s] for s in SCENARIOS],
                y=[allm[s]["exposure"] / 1e6 for s in SCENARIOS],
                marker_color=[SCENARIO_COLORS[s] for s in SCENARIOS],
                text=[eur_m(allm[s]["exposure"]) for s in SCENARIOS],
                textposition="outside",
                textfont=dict(color=TXT),
                hovertemplate="%{x} : %{y:.1f} M€ non vérifiables<extra></extra>",
            )
        )
        plot_style(fig, 300).update_yaxes(
            title="CA non vérifiable (M€)",
            range=[0, max(allm[s]["exposure"] for s in SCENARIOS) / 1e6 * 1.25],
        )
        show(fig)
        st.caption(
            "Commandes sans montant × panier moyen connu. Une hypothèse de travail, pas une perte mesurée."
        )

    with st.expander("Décomposition du chiffre d'affaires · observé vs hypothèse"):
        show(chart_exposure_waterfall(d))
        st.caption(
            "Le CA documenté est issu des montants connus. L'ajout est une hypothèse calculée à partir du panier connu. Version complète dans l'Observatoire."
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
                f"<b>{SCENARIO_NAME[s]}</b>",
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
        '<div class="eyebrow">Mission NexaRetail · observatoire analytique</div>',
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
        show(chart_exposure_waterfall(d))
        st.caption(
            "Le total est hypothétique : il ne doit pas être présenté comme un CA mesuré."
        )
    with b:
        h3("Couverture des montants par scénario")
        show(chart_coverage(allm, scenario))
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
    show(chart_sensitivity(allm, scenario, low_ratio, high_ratio))
    st.info(
        f"Scénario {SCENARIO_NAME[scenario]} : sous ces hypothèses, le CA non vérifiable se situe entre {eur_m(d['missing'] * d['basket'] * low_ratio)} "
        f"et {eur_m(d['missing'] * d['basket'] * high_ratio)}. Ce n'est pas un intervalle de confiance statistique."
    )
    l, r = st.columns([1, 1], gap="large")
    with l:
        h3("Empreinte de qualité")
        show(chart_quality_radar(allm, scenario))
        st.caption(
            "Vue descriptive : trois axes distincts (couverture, ponctualité, indice pédagogique). Ce n'est pas une certification."
        )
    with r:
        h3("Décision et points d'attention")
        st.markdown(
            f'<div class="ops-banner"><b>Statut simulé :</b> {esc(VERDICT[gate(d, TH)["overall"]][0])}<br><br>Les seuils se règlent dans la Porte de décision. La part de montants absents varie entre scénarios ; le taux de retard reste identique dans les références utilisées.</div>',
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
            )
            .to_csv(index=False, sep=";", decimal=",")
            .encode("utf-8-sig"),
            file_name="consultai_observatoire.csv",
            mime="text/csv",
        )

elif page == "Investigation":
    page_head(
        "Investigation",
        "Examiner les anomalies, formuler des hypothèses et préparer des contrôles vérifiables.",
    )
    st.markdown(
        '<div class="eyebrow">Diagnostic · observation ≠ causalité</div>',
        unsafe_allow_html=True,
    )
    l, r = st.columns([1.2, 1], gap="large")
    with l:
        h3("Carte de risques des scénarios")
        show(plot_matrix(allm, scenario))
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
        "Laboratoire de scénarios",
        "Fais varier les hypothèses pour estimer l’exposition possible liée aux montants absents. Les résultats restent des simulations.",
    )
    c1, c2 = st.columns([1, 1.7], gap="large")
    with c1:
        rate = st.slider(
            "Part de commandes sans montant (%)",
            0,
            100,
            int(round(d["missing_pct"])),
            key=f"rate_{scenario}",
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
    observed_rev = d[
        "known_rev"
    ]  # la valeur observée ne change pas quand on déplace le curseur
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
                textfont=dict(color=TXT),
                increasing_marker_color=AMBER,
                totals_marker_color=COBALT,
                connector_line_color=MIST,
            )
        )
        plot_style(fig, 300).update_yaxes(title="M€")
        show(fig)

    h3("Sensibilité : quel panier pour les commandes sans montant ?")
    xs = [0.5 + i * 0.05 for i in range(21)]
    fig2 = go.Figure()
    for s, col in zip(SCENARIOS, (MINT, AMBER, CORAL)):
        fig2.add_trace(
            go.Scatter(
                x=xs,
                y=[allm[s]["missing"] * allm[s]["basket"] * x / 1e6 for x in xs],
                name=SCENARIO_NAME[s],
                mode="lines",
                line=dict(color=col, width=3),
            )
        )
    fig2.add_vline(x=ratio, line_dash="dot", line_color=TXT)
    plot_style(fig2, 320).update_layout(
        xaxis_title="Panier des commandes sans montant (× panier connu)",
        yaxis_title="CA non vérifiable (M€)",
    )
    show(fig2)
    st.caption(
        "Plus il manque de montants, plus l'hypothèse de panier pèse sur le total."
    )

    h3("Monte Carlo : une fourchette plutôt qu'un chiffre")
    sigma = (
        st.slider(
            "Dispersion log-normale du panier inconnu (sigma × 100)", 5, 50, 15, 5
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
    show(fig3)
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
        json.dumps(simulation, indent=2, ensure_ascii=False, default=float),
        file_name=f"consultai_simulation_{scenario}.json",
        mime="application/json",
    )

elif page == "Decision Gate":
    page_head(
        "Porte de décision",
        "Définis les seuils de contrôle. Le verdict est recalculé pour le scénario sélectionné.",
    )
    raw = st.session_state["th"]
    for k, w in TH_WIDGETS.items():
        st.session_state.setdefault(
            w, float(raw[k])
        )  # les widgets non affichés sont purgés par Streamlit : on les ré-initialise

    def _reset_th() -> None:
        for k, w in TH_WIDGETS.items():
            st.session_state[w] = DEFAULT_TH[k]
            st.session_state["th"][k] = DEFAULT_TH[k]

    t1, t2, t3, t4 = st.columns(4)
    raw["m_warn"] = t1.number_input(
        "Montants absents : réserves au-delà de (%)",
        0.0,
        50.0,
        step=0.5,
        key=TH_WIDGETS["m_warn"],
    )
    raw["m_fail"] = t2.number_input(
        "Montants absents : blocage au-delà de (%)",
        0.0,
        50.0,
        step=0.5,
        key=TH_WIDGETS["m_fail"],
    )
    raw["l_warn"] = t3.number_input(
        "Retards : réserves au-delà de (%)",
        0.0,
        100.0,
        step=1.0,
        key=TH_WIDGETS["l_warn"],
    )
    raw["l_fail"] = t4.number_input(
        "Retards : blocage au-delà de (%)",
        0.0,
        100.0,
        step=1.0,
        key=TH_WIDGETS["l_fail"],
    )
    st.button("Réinitialiser les seuils", on_click=_reset_th)
    if raw["m_warn"] > raw["m_fail"] or raw["l_warn"] > raw["l_fail"]:
        st.error(
            "Seuils incohérents : le seuil de réserve doit être inférieur ou égal au seuil de blocage. Les seuils par défaut restent appliqués dans les autres pages."
        )
    else:
        TH = raw
        g = gate(d, TH)
        h3(f"Contrôles · scénario {SCENARIO_NAME[scenario]}")
        st.caption(
            "Le point indique le résultat observé. Les repères verticaux montrent le seuil de réserve et le seuil de blocage."
        )
        decision_meter(
            "Montants absents",
            d["missing_pct"],
            TH["m_warn"],
            TH["m_fail"],
            g["checks"][0][2],
        )
        decision_meter(
            "Livraisons en retard",
            d["late_pct"],
            TH["l_warn"],
            TH["l_fail"],
            g["checks"][1][2],
        )
        h3("Verdict par scénario")
        table(
            ["Scénario", "Montants absents", "Retards", "Décision"],
            [
                [
                    f"<b>{SCENARIO_NAME[s]}</b>",
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
            data=memo_markdown(d, scenario, g, hs, recommendations(d, TH)),
            file_name=f"note_decision_{scenario}.md",
            mime="text/markdown",
            type="primary",
        )

elif page == "Data Lineage":
    page_head(
        "Traçabilité des données",
        "Retrouver l’origine des indicateurs et comprendre les étapes de calcul avant leur affichage.",
    )
    st.markdown(
        """<div class="pipe">
      <div class="pnode"><b>Source</b><span>PostgreSQL en lecture seule, ou référence figée</span></div><div class="plink"></div>
      <div class="pnode"><b>Calcul</b><span>kpi.py : overview() et delivery()</span></div><div class="plink"></div>
      <div class="pnode"><b>Règles</b><span>Seuils, verdict, priorisation des actions</span></div><div class="plink"></div>
      <div class="pnode"><b>Simulations Python</b><span>Hypothèses, Monte Carlo et résolution de seuils</span></div><div class="plink"></div>
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
            textfont=dict(color=TXT, size=12),
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
    show(fig)
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
                "60 % × max(0, 100 − 5 × % absents) + 40 % × max(0, 100 − 2 × % retards)",
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

elif page == "Atelier d’analyse":
    render_workshop(d, allm, TH, scenario)

else:
    page_head(
        "Assistant IA",
        "Pose une question sur les indicateurs, compare les scénarios et consulte les éléments qui justifient chaque réponse.",
    )
    models, model_status = local_models()
    st.caption(model_status)
    preferences = st.columns([1.2, 1, 1])
    engine = preferences[0].selectbox(
        "Moteur de réponse",
        ["Automatique", "Outils vérifiés", "Modèle local"],
        key="chat_engine",
    )
    response_style = preferences[1].selectbox(
        "Format de réponse",
        ["Conversation", "Synthèse", "Analyse détaillée"],
        key="response_style",
    )
    if models:
        preferred = os.getenv("CONSULTAI_OLLAMA_MODEL", "llama3.2:1b")
        preferences[2].selectbox(
            "Modèle installé",
            models,
            index=models.index(preferred) if preferred in models else 0,
            key="chat_model",
        )
    elif engine == "Modèle local":
        st.warning(
            "Aucun modèle local accessible. Les outils vérifiés répondent ; lance Ollama pour activer la rédaction IA."
        )
    use_model = bool(models) and engine != "Outils vérifiés"
    with st.expander("Méthode et garde-fous · SQL → Python → IA", expanded=False):
        st.caption(
            "Les calculs sont réalisés par des fonctions autorisées. Les réponses indiquent leurs preuves et les hypothèses. Ollama est optionnel et ne calcule pas les KPI."
        )
    chat = st.session_state.setdefault("chat", [])
    ctx = st.session_state.setdefault("ctx", {})
    suggestions = [
        "Analyse complète du scénario",
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
            "Où se trouve la Porte de décision ?",
            "À quoi sert PostgreSQL dans le projet ?",
            "Comment fonctionne le copilote ?",
        ],
        "⚖️ Décision & risques": [
            "Que faire en priorité ?",
            "À partir de quel taux faut-il bloquer ?",
            "Rédige une note de décision",
            "Quelles sont les limites des simulations ?",
        ],
    }
    n_ideas = sum(len(v) for v in question_groups.values())
    st.markdown(
        '<div class="copilot-capabilities"><span>Comprend les fautes de frappe</span><span>Connaît les pages du projet</span><span>Cite ses preuves</span><span>Simule sans inventer</span></div>',
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
        f"🧠 Bibliothèque de questions · {n_ideas} idées à explorer",
        expanded=not bool(chat),
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
    pending = st.session_state.pop("pending_q", None)
    q = typed_q or pending
    if q:
        q = q.strip()[:3000]
        if ctx.get("selected_scope") != scenario:
            ctx.clear()
            ctx["selected_scope"] = scenario
        chat.append({"role": "user", "content": q})
        res = conversational_answer(
            q, scenario, allm, TH, ctx, chat[:-1], response_style
        )
        res["verified"] = res["text"]
        if use_model:
            try:
                with st.spinner("Rédaction locale en cours..."):
                    res = ollama_answer(q, allm, chat[:-1], res)
            except Exception as exc:
                res["text"] = (
                    f"Ollama n'a pas répondu ({type(exc).__name__}). Voici les résultats des outils, sans rédaction :\n\n"
                    + res["text"]
                )
        st.session_state["animate_reply"] = True
        chat.append(
            {
                "verified": res.get("verified", ""),
                "engine": "Modèle local"
                if use_model and "+ ollama" in res["intent"]
                else "Outils vérifiés",
                "role": "assistant",
                "content": res["text"],
                "evidence": res["evidence"],
                "intent": res["intent"],
                "kind": res["kind"],
                "scenario": res["scenario"],
                "followups": res["followups"],
            }
        )
        del chat[
            :-MAX_CHAT
        ]  # historique borné : la session ne grossit plus indéfiniment
    if not chat:
        st.markdown(
            '<div class="chat-empty fx"><b>Prêt pour une investigation</b><span>Sélectionnez une question ci-dessus ou utilisez la barre de saisie. Les réponses distinguent faits, simulations et recommandations.</span></div>',
            unsafe_allow_html=True,
        )
    for m in chat:
        with st.chat_message(m["role"]):
            if m["role"] == "assistant":
                cls = {
                    "Hypothèse": "hyp",
                    "Information": "info",
                    "Définition": "info",
                }.get(m.get("kind", ""), "")
                st.markdown(
                    f'<span class="tag {cls}">{esc(m.get("kind", ""))}</span><span class="tag info">scénario {esc(SCENARIO_NAME.get(m.get("scenario", ""), m.get("scenario", "")))}</span>',
                    unsafe_allow_html=True,
                )
                fresh = m is chat[-1] and st.session_state.pop("animate_reply", False)
                if (
                    fresh
                    and st.session_state.get("motion_level") != "Arrêt"
                    and hasattr(st, "write_stream")
                ):

                    def response_chunks():
                        import time

                        pieces = re.split(r"(\s+)", m["content"])
                        for i in range(0, len(pieces), 12):
                            yield "".join(pieces[i : i + 12])
                            time.sleep(0.012)

                    st.write_stream(response_chunks())
                else:
                    st.markdown(m["content"])
                st.caption(m.get("engine", "Outils vérifiés"))
                if m.get("verified") and m["verified"] != m["content"]:
                    with st.expander("Consulter le résultat vérifié avant rédaction"):
                        st.markdown(m["verified"])
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
        exports = st.columns(3)
        exports[0].download_button(
            "Exporter l’échange (JSON)",
            json.dumps(chat, ensure_ascii=False, indent=2),
            "conversation_consultai.json",
            "application/json",
        )
        markdown = "\n\n---\n\n".join(
            f"### {'Vous' if item['role'] == 'user' else 'ConsultAI'}\n\n{item['content']}"
            for item in chat
        )
        exports[1].download_button(
            "Exporter l’échange (Markdown)",
            markdown,
            "conversation_consultai.md",
            "text/markdown",
        )
        exports[2].button(
            "Nouvelle conversation",
            on_click=lambda: st.session_state.update(
                chat=[], ctx={}, pending_q=None, animate_reply=False
            ),
        )
        if hasattr(st, "feedback"):
            st.feedback("thumbs", key=f"feedback_{len(chat)}")

st.markdown(
    '<div class="foot">CONSULTAI 360 / NEXARETAIL · ENVIRONNEMENT SYNTHÉTIQUE · SQL → PYTHON → CONTRÔLES → IA OPTIONNELLE · AUCUNE DÉCISION AUTOMATIQUE</div>',
    unsafe_allow_html=True,
)
