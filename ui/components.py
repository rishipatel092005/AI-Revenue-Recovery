"""Small reusable presentation components."""

import streamlit as st

def top_header(page_name):
    left, search, actions = st.columns([1.1, 2.8, 1.1], vertical_alignment="center")
    with left:
        st.markdown('<div class="ui-kicker">RECOVERAI</div><div style="font-size:18px;font-weight:700">Control Center</div>', unsafe_allow_html=True)
    with search:
        st.text_input("Search", placeholder="Search payments, customers, or cases...", label_visibility="collapsed", key="global_search")
    with actions:
        a, b = st.columns(2)
        with a:
            if st.button("✦ AI Assistant", key="header_assistant"):
                st.session_state["nav"] = "AI Recovery Assistant"
                st.rerun()
        with b:
            st.markdown('<span class="ui-status ui-status-warning">TEST MODE</span>', unsafe_allow_html=True)
    st.caption(page_name)


def page_header(kicker, title, subtitle):
    st.markdown(f'<div class="ui-kicker">{kicker}</div><div class="ui-title">{title}</div><div class="ui-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def kpi(label, value, note=""):
    st.markdown(f'<div class="ui-kpi"><div class="ui-kpi-label">{label}</div><div class="ui-kpi-value">{value}</div><div class="ui-kpi-note">{note}</div></div>', unsafe_allow_html=True)


def status(text, tone=""):
    return f'<span class="ui-status ui-status-{tone}">{text}</span>' if tone else f'<span class="ui-status">{text}</span>'


def timeline(items):
    html = '<div class="ui-timeline">'
    for label, value in items:
        html += f'<div class="ui-timeline-item"><div class="ui-timeline-label">{label}</div><div class="ui-timeline-value">{value}</div></div>'
    st.markdown(html + '</div>', unsafe_allow_html=True)
