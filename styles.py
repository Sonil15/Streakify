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
    "primary":        "#6C63FF",   # soft purple
    "primary_light":  "#EDE9FF",
    "accent":         "#FF6B9D",   # bubblegum pink
    "accent_light":   "#FFE4EE",
    "mint":           "#4ECDC4",
    "mint_light":     "#E0F7F6",
    "yellow":         "#FFD166",
    "yellow_light":   "#FFF8E1",
    "peach":          "#FF8A65",
    "peach_light":    "#FBE9E7",
    "bg":             "#F8F7FF",
    "card_bg":        "#FFFFFF",
    "text_main":      "#2D2D3A",
    "text_muted":     "#9E9E9E",
    "border":         "#E8E8F0",
    "success":        "#66BB6A",
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
        @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Nunito', sans-serif;
        }}

        .stApp {{
            background: {COLORS["bg"]};
        }}

        /* ── Sidebar ─────────────────────────────────────────────────── */
        section[data-testid="stSidebar"] {{
            background: #FFFFFF;
            border-right: 1px solid {COLORS["border"]};
        }}

        /* ── Buttons ─────────────────────────────────────────────────── */
        .stButton > button {{
            border-radius: 20px !important;
            font-weight: 700 !important;
            letter-spacing: 0.3px;
            transition: all 0.2s ease;
            border: none !important;
        }}

        .stButton > button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(108, 99, 255, 0.25);
        }}

        /* Primary button colour override */
        .stButton > button[kind="primary"] {{
            background: linear-gradient(135deg, {COLORS["primary"]}, {COLORS["accent"]}) !important;
            color: white !important;
        }}

        /* ── Tabs ─────────────────────────────────────────────────────── */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
            background: transparent;
        }}

        .stTabs [data-baseweb="tab"] {{
            border-radius: 20px !important;
            padding: 8px 18px !important;
            font-weight: 700 !important;
            background: {COLORS["primary_light"]} !important;
            color: {COLORS["primary"]} !important;
            border: none !important;
        }}

        .stTabs [aria-selected="true"] {{
            background: {COLORS["primary"]} !important;
            color: white !important;
        }}

        /* ── Input fields ─────────────────────────────────────────────── */
        .stTextInput > div > div > input,
        .stSelectbox > div > div,
        .stTextArea > div > div > textarea {{
            border-radius: 12px !important;
            border: 1.5px solid {COLORS["border"]} !important;
            background: #FAFAFA !important;
        }}

        .stTextInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus {{
            border-color: {COLORS["primary"]} !important;
            box-shadow: 0 0 0 3px {COLORS["primary_light"]} !important;
        }}

        /* ── Progress bars ────────────────────────────────────────────── */
        .stProgress > div > div > div > div {{
            background: linear-gradient(90deg, {COLORS["primary"]}, {COLORS["accent"]});
            border-radius: 10px;
        }}

        /* ── Metric cards ─────────────────────────────────────────────── */
        [data-testid="stMetric"] {{
            background: {COLORS["card_bg"]};
            border-radius: 16px;
            padding: 16px;
            border: 1px solid {COLORS["border"]};
            box-shadow: 0 2px 12px rgba(0,0,0,0.05);
        }}

        /* ── Expanders ───────────────────────────────────────────────── */
        .streamlit-expanderHeader {{
            border-radius: 12px !important;
            background: {COLORS["primary_light"]} !important;
            font-weight: 700 !important;
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
            background: white;
            border-radius: 20px;
            padding: 20px 24px;
            margin-bottom: 16px;
            border: 1.5px solid {COLORS["border"]};
            box-shadow: 0 4px 20px rgba(0,0,0,0.06);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}

        .streak-card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 8px 28px rgba(0,0,0,0.10);
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
            background: {COLORS["mint_light"]};
            color: #00897B;
            border-radius: 20px;
            padding: 4px 12px;
            font-size: 0.9rem;
            font-weight: 700;
            margin-top: 6px;
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
            font-size: 1.4rem;
            font-weight: 800;
            color: {COLORS["text_main"]};
            margin-bottom: 0.5rem;
        }}

        .page-title {{
            font-size: 2rem;
            font-weight: 900;
            background: linear-gradient(135deg, {COLORS["primary"]}, {COLORS["accent"]});
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        .divider {{
            border: none;
            border-top: 1.5px solid {COLORS["border"]};
            margin: 16px 0;
        }}

        /* Heatmap tooltip */
        .heatmap-tooltip {{
            background: white;
            border-radius: 10px;
            padding: 8px 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.12);
            font-size: 0.85rem;
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
        </style>
        """,
        unsafe_allow_html=True,
    )
