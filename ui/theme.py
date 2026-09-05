"""Theme state and CSS tokens for the RecoverAI frontend."""

import streamlit as st


THEME = {
    "background": "#F4F6FA",
    "card": "#FFFFFF",
    "elevated": "#F8FAFC",
    "text": "#111827",
    "secondary": "#667085",
    "border": "#D9E1EA",
    "accent": "#2563EB",
    "success": "#22C55E",
    "warning": "#F59E0B",
    "danger": "#EF4444",
    "sidebar": "#102B49",
    "chart_grid": "#E5EAF0",
}


def apply_theme():
    colors = THEME
    st.markdown(f"""
    <style>
    :root {{
      --bg:{colors['background']}; --card:{colors['card']}; --elevated:{colors['elevated']};
      --text:{colors['text']}; --muted:{colors['secondary']}; --border:{colors['border']};
      --accent:{colors['accent']}; --success:{colors['success']}; --warning:{colors['warning']};
      --danger:{colors['danger']}; --sidebar:{colors['sidebar']}; --grid:{colors['chart_grid']};
    }}
    .stApp, [data-testid="stAppViewContainer"] {{ background:var(--bg); color:var(--text); }}
    [data-testid="stHeader"] {{ background:transparent; }}
    [data-testid="stSidebar"] {{ background:var(--sidebar); }}
    [data-testid="stSidebar"] * {{ color:#E8EEF7; }}
    h1,h2,h3,h4,p,span,label,div {{ color:var(--text); }}
    [data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,[data-testid="stSidebar"] span,[data-testid="stSidebar"] label {{ color:#E8EEF7; }}
    .stMarkdown, .stCaption {{ color:var(--muted); }}
    .ui-card {{ background:var(--card); border:1px solid var(--border); border-radius:14px; padding:20px; box-shadow:0 8px 28px rgba(0,0,0,.08); }}
    .ui-card--elevated {{ background:var(--elevated); }}
    .ui-kicker {{ color:var(--accent) !important; font-size:12px; font-weight:700; letter-spacing:.14em; text-transform:uppercase; }}
    .ui-title {{ color:var(--text) !important; font-family:'Space Grotesk',sans-serif; font-size:40px; font-weight:700; line-height:1.08; margin:5px 0 8px; }}
    .ui-subtitle {{ color:var(--muted) !important; font-size:15px; }}
    .ui-kpi {{ background:var(--card); border:1px solid var(--border); border-radius:14px; padding:17px; min-height:112px; }}
    .ui-kpi-label {{ color:var(--muted) !important; font-size:13px; font-weight:600; }}
    .ui-kpi-value {{ color:var(--text) !important; font-family:'Space Grotesk',sans-serif; font-size:29px; font-weight:700; margin-top:12px; }}
    .ui-kpi-note {{ color:var(--muted) !important; font-size:12px; margin-top:5px; }}
    .ui-status {{ display:inline-block; background:color-mix(in srgb, var(--accent) 14%, transparent); color:var(--accent) !important; border-radius:999px; padding:4px 9px; font-size:12px; font-weight:700; }}
    .ui-status-success {{ background:color-mix(in srgb, var(--success) 14%, transparent); color:var(--success) !important; }}
    .ui-status-warning {{ background:color-mix(in srgb, var(--warning) 15%, transparent); color:var(--warning) !important; }}
    .ui-status-danger {{ background:color-mix(in srgb, var(--danger) 14%, transparent); color:var(--danger) !important; }}
    .ui-decision {{ border-left:4px solid var(--accent); background:color-mix(in srgb, var(--accent) 10%, var(--card)); border-radius:8px; padding:14px 16px; }}
    .ui-timeline {{ border-left:2px solid var(--border); margin:8px 0 0 8px; padding-left:20px; }}
    .ui-timeline-item {{ position:relative; padding:0 0 16px; }}
    .ui-timeline-item:before {{ content:''; position:absolute; width:8px; height:8px; border-radius:50%; background:var(--accent); left:-25px; top:5px; }}
    .ui-timeline-label {{ color:var(--muted) !important; font-size:12px; }}
    .ui-timeline-value {{ color:var(--text) !important; font-weight:600; }}
    div[data-testid="stMetric"], [data-testid="stDataFrame"] {{ background:var(--card); border-color:var(--border); }}
    [data-baseweb="input"], [data-baseweb="select"] > div, textarea {{ background:var(--card) !important; color:var(--text) !important; border-color:var(--border) !important; }}
    [data-baseweb="tag"] {{ background:#E8F0FF !important; border:1px solid #BBD0FF !important; border-radius:999px !important; color:#173B7A !important; }}
    [data-baseweb="tag"] span, [data-baseweb="tag"] div {{ color:#173B7A !important; }}
    [data-baseweb="tag"] svg {{ fill:#173B7A !important; color:#173B7A !important; }}
    [data-baseweb="select"] input {{ color:var(--text) !important; }}
    .stButton > button {{ border-radius:9px; border-color:var(--border); background:var(--card); color:var(--text); }}
    [data-testid="stSidebar"] .stButton > button {{ color:#000000 !important; }}
    [data-testid="stFormSubmitButton"] button {{ background:#FFFFFF !important; border:1px solid #D9E1EA !important; color:#111827 !important; }}
    .stButton > button[kind="primary"] {{ background:var(--accent); border-color:var(--accent); color:white; }}
    @media (max-width:700px) {{ .ui-title {{ font-size:31px; }} .ui-kpi-value {{ font-size:25px; }} }}
    </style>
    """, unsafe_allow_html=True)
