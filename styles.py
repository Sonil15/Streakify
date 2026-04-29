"""
styles.py
All custom CSS injected via st.markdown.
Pastel/cute palette, rounded cards, soft shadows.
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------

COLORS = {
    "primary":        "#4FAF1A",
    "primary_light":  "#EAFAD9",
    "accent":         "#1CB0F6",
    "accent_light":   "#E5F6FF",
    "mint":           "#58CC02",
    "mint_light":     "#EAFAD9",
    "yellow":         "#FFC800",
    "yellow_light":   "#FFF6CC",
    "peach":          "#FF4B4B",
    "peach_light":    "#FFE7E7",
    "bg":             "#F7FAF2",
    "card_bg":        "#FFFFFF",
    "text_main":      "#24333E",
    "text_muted":     "#7A8B95",
    "border":         "#DCE7CF",
    "success":        "#3F8E1A",
    "danger":         "#EF5350",
    "streak_cold":    "#B0BEC5",
    "streak_warm":    "#FFD54F",
    "streak_hot":     "#FF8A65",
    "streak_fire":    "#EF5350",
}


# ---------------------------------------------------------------------------
# CSS injection
# ---------------------------------------------------------------------------

def inject_custom_css():
    st.markdown(
        f"""
        <style>
        /* ── Global ─────────────────────────────────────────────────── */
        @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@500;600;700;800;900&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Nunito', sans-serif;
        }}

        .stApp {{
            background: radial-gradient(circle at top right, #F5FFD9 0%, {COLORS["bg"]} 42%, #F9FFF1 100%);
        }}

        #MainMenu, footer, header {{
            visibility: hidden;
        }}

        /* ── Sidebar ─────────────────────────────────────────────────── */
        section[data-testid="stSidebar"] {{
            background: #FFFFFF;
            border-right: 2px solid {COLORS["border"]};
        }}

        /* ── Buttons ─────────────────────────────────────────────────── */
        .stButton > button {{
            border-radius: 16px !important;
            font-weight: 800 !important;
            letter-spacing: 0.2px;
            transition: all 0.2s ease;
            border: 2px solid transparent !important;
            padding: 0.58rem 1rem !important;
        }}

        .stButton > button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 0 rgba(36, 51, 62, 0.08);
        }}

        /* Primary button colour override */
        .stButton > button[kind="primary"] {{
            background: linear-gradient(180deg, #6ACB35, {COLORS["primary"]}) !important;
            color: white !important;
            border-color: #3F8E1A !important;
            box-shadow: 0 4px 0 #3F8E1A;
        }}

        .stButton > button[kind="primary"]:active {{
            transform: translateY(2px);
            box-shadow: 0 2px 0 #3F8E1A;
        }}

        /* ── Tabs ─────────────────────────────────────────────────────── */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
            background: transparent;
        }}

        .stTabs [data-baseweb="tab"] {{
            border-radius: 999px !important;
            padding: 8px 18px !important;
            font-weight: 800 !important;
            background: #FFFFFF !important;
            color: {COLORS["text_muted"]} !important;
            border: 2px solid {COLORS["border"]} !important;
        }}

        .stTabs [aria-selected="true"] {{
            background: {COLORS["primary"]} !important;
            color: white !important;
            border-color: #46A302 !important;
        }}

        /* ── Input fields ─────────────────────────────────────────────── */
        .stTextInput > div > div > input,
        .stSelectbox > div > div,
        .stTextArea > div > div > textarea {{
            border-radius: 14px !important;
            border: 1.5px solid {COLORS["border"]} !important;
            background: #FFFFFF !important;
        }}

        .stTextInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus {{
            border-color: {COLORS["primary"]} !important;
            box-shadow: 0 0 0 3px {COLORS["primary_light"]} !important;
        }}

        /* ── Progress bars ────────────────────────────────────────────── */
        .stProgress > div > div > div > div {{
            background: linear-gradient(90deg, #6CCB39, {COLORS["primary"]});
            border-radius: 10px;
        }}

        /* ── Metric cards ─────────────────────────────────────────────── */
        [data-testid="stMetric"] {{
            background: #FFFFFF;
            border-radius: 18px;
            padding: 16px;
            border: 2px solid {COLORS["border"]};
            box-shadow: 0 6px 0 rgba(36, 51, 62, 0.05);
        }}

        /* ── Expanders ───────────────────────────────────────────────── */
        .streamlit-expanderHeader {{
            border-radius: 14px !important;
            background: #FFFFFF !important;
            border: 2px solid {COLORS["border"]} !important;
            font-weight: 800 !important;
        }}

        /* ── Alerts / info boxes ──────────────────────────────────────── */
        .stAlert {{
            border-radius: 12px !important;
        }}

        /* ── Checkboxes ──────────────────────────────────────────────── */
        .stCheckbox > label {{
            font-weight: 600;
        }}

        /* ── Custom card component ───────────────────────────────────── */
        .streak-card {{
            background: linear-gradient(180deg, #FFFFFF 0%, #F8FFF0 100%);
            border-radius: 18px;
            padding: 20px 24px;
            margin-bottom: 16px;
            border: 2px solid {COLORS["border"]};
            box-shadow: 0 6px 0 rgba(36, 51, 62, 0.06);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}

        .streak-card:nth-of-type(2n) {{
            background: linear-gradient(180deg, #FFFFFF 0%, #EEF8FF 100%);
        }}

        .streak-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 0 rgba(36, 51, 62, 0.08);
        }}

        .streak-number {{
            font-size: 2.8rem;
            font-weight: 900;
            line-height: 1;
        }}

        .streak-label {{
            font-size: 0.85rem;
            font-weight: 600;
            color: {COLORS["text_muted"]};
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .freeze-badge {{
            display: inline-block;
            background: {COLORS["accent_light"]};
            color: {COLORS["accent"]};
            border-radius: 20px;
            padding: 4px 12px;
            font-size: 0.9rem;
            font-weight: 700;
            margin-top: 6px;
            border: 2px solid #BEE8FF;
        }}

        .pill {{
            display: inline-block;
            border-radius: 20px;
            padding: 4px 14px;
            font-size: 0.85rem;
            font-weight: 700;
        }}

        .pill-purple {{
            background: {COLORS["primary_light"]};
            color: {COLORS["primary"]};
        }}

        .pill-pink {{
            background: {COLORS["accent_light"]};
            color: #C2185B;
        }}

        .pill-mint {{
            background: {COLORS["mint_light"]};
            color: #00695C;
        }}

        .section-header {{
            font-size: 1.25rem;
            font-weight: 900;
            color: {COLORS["text_main"]};
            margin: 0.2rem 0 0.65rem 0;
            text-align: center;
        }}

        .page-title {{
            font-size: 2.1rem;
            font-weight: 900;
            background: linear-gradient(135deg, {COLORS["primary"]}, #72C83A);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-align: center;
        }}

        .duo-hero {{
            background: linear-gradient(180deg, #68C43A 0%, {COLORS["primary"]} 100%);
            color: white;
            border-radius: 20px;
            border: 2px solid #3F8E1A;
            box-shadow: 0 8px 0 rgba(63, 142, 26, 0.36);
            padding: 18px 20px;
            margin: 10px 0 16px 0;
            text-align: center;
        }}

        .duo-hero-title {{
            font-size: 1.9rem;
            font-weight: 900;
            line-height: 1.15;
        }}

        .duo-hero-sub {{
            font-size: 0.96rem;
            font-weight: 700;
            opacity: 0.95;
            margin-top: 6px;
        }}

        .duo-chip-row {{
            display: flex;
            justify-content: center;
            gap: 10px;
            margin-top: 10px;
            flex-wrap: wrap;
        }}

        .duo-chip {{
            background: #FFFFFF;
            color: #3B4B57;
            border: 2px solid #DCE7CF;
            border-radius: 999px;
            font-size: 0.8rem;
            font-weight: 800;
            padding: 4px 10px;
        }}

        .duo-date-pill {{
            display: inline-block;
            margin: 4px auto 12px auto;
            background: #FFFFFF;
            border: 2px solid {COLORS["border"]};
            border-radius: 999px;
            padding: 6px 14px;
            font-weight: 800;
            color: {COLORS["text_main"]};
        }}

        .duo-auth-hero {{
            text-align: center;
            padding: 1.2rem 0 0.6rem;
        }}

        .duo-auth-hero h1 {{
            margin: 0;
            font-size: 2.45rem;
            font-weight: 900;
            color: {COLORS["primary"]};
            line-height: 1.05;
        }}

        .duo-auth-hero p {{
            color: {COLORS["text_muted"]};
            font-size: 1rem;
            font-weight: 700;
            margin-top: 0.4rem;
        }}

        .divider {{
            border: none;
            border-top: 1.5px solid {COLORS["border"]};
            margin: 16px 0;
        }}

        /* Center key content blocks for a balanced layout */
        .main .block-container {{
            max-width: 1050px;
            margin: 0 auto;
        }}

        .main .block-container p,
        .main .block-container .stCaption,
        .main .block-container h3 {{
            text-align: center;
        }}

        .stTabs [data-baseweb="tab-list"] {{
            justify-content: center;
        }}

        [data-testid="stMetric"] * {{
            text-align: center !important;
        }}

        .streak-card {{
            text-align: center;
        }}

        /* Heatmap tooltip */
        .heatmap-tooltip {{
            background: white;
            border-radius: 10px;
            padding: 8px 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.12);
            font-size: 0.85rem;
        }}

        .heatmap-card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
            background: linear-gradient(135deg, #F8FFF0, #EEF9FF);
            border: 2px solid {COLORS["border"]};
            border-bottom: none;
            border-radius: 16px 16px 0 0;
            padding: 8px 12px;
            margin-top: 8px;
        }}

        .heatmap-title {{
            font-weight: 900;
            color: {COLORS["text_main"]};
            font-size: 0.95rem;
            text-align: left !important;
        }}

        .heatmap-stat {{
            background: #FFFFFF;
            border: 2px solid #DCE7CF;
            border-radius: 999px;
            padding: 3px 10px;
            font-size: 0.78rem;
            font-weight: 800;
            color: #3F4F5A;
            white-space: nowrap;
        }}

        /* Accountability read-only banner */
        .readonly-banner {{
            background: linear-gradient(135deg, {COLORS["yellow_light"]}, {COLORS["peach_light"]});
            border-radius: 12px;
            padding: 10px 16px;
            border-left: 4px solid {COLORS["yellow"]};
            font-weight: 700;
            color: #5D4037;
            margin-bottom: 12px;
        }}

        div[data-testid="stExpander"] {{
            background: #FFFFFF;
            border: 2px solid {COLORS["border"]};
            border-radius: 16px;
            padding: 6px 8px;
            box-shadow: 0 5px 0 rgba(36, 51, 62, 0.04);
            margin-bottom: 10px;
        }}

        div[data-testid="stExpander"]:nth-of-type(3n+1) {{ background: #F8FFF0; }}
        div[data-testid="stExpander"]:nth-of-type(3n+2) {{ background: #F3FAFF; }}
        div[data-testid="stExpander"]:nth-of-type(3n+3) {{ background: #FFFDF2; }}
        </style>
        """,
        unsafe_allow_html=True,
    )
