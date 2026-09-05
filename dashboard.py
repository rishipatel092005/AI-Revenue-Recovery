"""RecoverAI Streamlit control center.

Presentation-only frontend. Existing Supabase reads, outcome tracking, and
pipeline commands remain the source of truth for behavior.
"""

import subprocess
import sys
from datetime import datetime

import pandas as pd
import streamlit as st

import config
import db
import recovery.decision_engine as decision_engine
import recovery.outcome_tracker as outcome_tracker
from ui.assistant import render as render_assistant
from ui.components import timeline as render_timeline
from ui.theme import apply_theme


st.set_page_config(page_title="RecoverAI Control Center", page_icon=":material/monitoring:", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root { --ink:#16283d; --muted:#687789; --line:#d9e1ea; --paper:#f8f9fb; --navy:#102b49; --blue:#2563eb; --teal:#087f72; }
.stApp { background:var(--paper); color:var(--ink); font-family:'DM Sans', sans-serif; font-size:15px; }
h1,h2,h3 { font-family:'Space Grotesk', sans-serif !important; color:var(--ink) !important; letter-spacing:0 !important; }
[data-testid="stSidebar"] { background:#102d3c; }
[data-testid="stSidebar"] * { color:#e8f0f2; }
[data-testid="stSidebar"] .stRadio label { padding:8px 10px; border-radius:7px; }
[data-testid="stSidebar"] .stRadio label:hover { background:#1d4658; }
[data-testid="stSidebar"] button { color:#000000 !important; }
.brand { font-family:'Space Grotesk', sans-serif; font-size:22px; font-weight:700; color:white; margin:8px 0 2px; }
.brand-mark { display:inline-flex; align-items:center; justify-content:center; width:30px; height:30px; margin-right:8px; border-radius:8px; background:#2563eb; color:white; font-size:17px; font-weight:700; vertical-align:middle; }
.brand-sub { color:#a9c2ca; font-size:14px; margin-bottom:28px; }
.sidebar-group { color:#8fa6bb; font-size:11px; font-weight:700; letter-spacing:.12em; margin:14px 0 7px; }
.eyebrow { text-transform:uppercase; letter-spacing:.12em; color:var(--blue); font-size:13px; font-weight:700; }
.page-title { font-family:'Space Grotesk',sans-serif; font-size:40px; font-weight:700; margin:4px 0 2px; }
.page-subtitle { color:var(--muted); margin-bottom:22px; }
.kpi { background:white; border:1px solid var(--line); border-radius:10px; padding:17px 18px; min-height:112px; box-shadow:0 2px 8px rgba(19,44,59,.04); }
.kpi-label { color:var(--muted); font-size:14px; font-weight:600; }
.kpi-value { font-family:'Space Grotesk',sans-serif; font-size:32px; font-weight:700; margin-top:12px; color:var(--ink); }
.kpi-note { color:var(--muted); font-size:13px; margin-top:4px; }
.panel { background:white; border:1px solid var(--line); border-radius:14px; padding:20px; margin-bottom:16px; box-shadow:0 5px 18px rgba(16,43,73,.035); }
.panel-title { font-family:'Space Grotesk',sans-serif; font-size:20px; font-weight:700; margin-bottom:3px; }
.panel-copy { color:var(--muted); font-size:14px; margin-bottom:14px; }
.status { display:inline-block; border-radius:999px; padding:4px 9px; font-size:13px; font-weight:700; background:#e8f4f2; color:#0f766e; }
.status-warn { background:#fff4e5; color:#9a4d00; }
.status-danger { background:#ffebe9; color:#a32118; }
.status-neutral { background:#edf1f3; color:#53616c; }
.decision-box { border-left:4px solid var(--blue); background:#eff5ff; padding:13px 15px; border-radius:8px; }
.mini-label { color:var(--muted); font-size:13px; text-transform:uppercase; letter-spacing:.08em; font-weight:700; }
.mini-value { font-weight:700; margin-top:3px; }
div[data-testid="stMetric"] { background:white; border:1px solid var(--line); border-radius:10px; padding:12px; }
@media (max-width: 700px) { .page-title { font-size:32px; } .kpi-value { font-size:27px; } }
</style>
""", unsafe_allow_html=True)
apply_theme()


TIER_LABELS = {"auto_retry": "Retry", "whatsapp": "WhatsApp", "voice_call": "Voice"}
ACTION_LABELS = {"auto_retry": "Silent retry", "whatsapp": "WhatsApp nudge", "voice_call": "Voice call"}


@st.cache_data(ttl=15, show_spinner="Syncing recovery data...")
def load_all():
    sb = db.get_supabase()
    return {
        "metrics": db.recovery_metrics(sb=sb),
        "transactions": sb.table("transactions").select("*, customers(name, segment, ltv_tier, phone)").order("amount", desc=True).execute().data,
        "interventions": sb.table("interventions").select("*").order("fired_at", desc=True).execute().data,
        "audit": sb.table("audit_log").select("*").order("created_at", desc=True).limit(1000).execute().data,
    }


def money(value, decimals=0):
    return f"₹{float(value or 0):,.{decimals}f}"


def masked_phone(value):
    digits = "".join(character for character in str(value or "") if character.isdigit())
    return f"{digits[:4]}XXXX" if digits else "Not available"


def customer(txn):
    return txn.get("customers") or {}


def latest_interventions(rows):
    result = {}
    for row in sorted(rows, key=lambda item: item.get("fired_at") or ""):
        result[row["transaction_id"]] = row
    return result


def audit_payload(row):
    return row.get("payload") or {}


def audit_reason(audit, txn_id):
    for row in audit:
        if row.get("transaction_id") == txn_id and row["event_type"] == "decision_made":
            return audit_payload(row).get("reason", "Decision recorded by policy engine")
    return "Decision recorded by policy engine"


def derived_frames(data):
    latest = latest_interventions(data["interventions"])
    rows = []
    for txn in data["transactions"]:
        iv = latest.get(txn["id"], {})
        cust = customer(txn)
        tier = iv.get("tier", "")
        rows.append({
            "Payment ID": txn["id"][:8], "_id": txn["id"], "Customer": cust.get("name", "Unknown"),
            "Amount": float(txn["amount"]), "Failure reason": (txn.get("failure_reason_code") or "Unknown").replace("_", " ").title(),
            "Failure code": txn.get("failure_reason_code") or "unknown",
            "AI diagnosis": (txn.get("diagnosis_category") or "Unclassified").replace("_", " ").title(),
            "Action": ACTION_LABELS.get(tier, "Pending analysis"), "Tier": tier,
            "Policy status": "Approved" if tier else "Awaiting analysis", "Outcome": iv.get("outcome", "Pending").title(),
            "Status": txn.get("status", "failed").title(), "Segment": cust.get("segment", "Unknown").replace("_", " ").title(),
            "LTV tier": cust.get("ltv_tier", "Unknown").title(), "Phone": cust.get("phone", ""),
            "Attempts": txn.get("attempt_count", 0), "Reason": audit_reason(data["audit"], txn["id"]),
        })
    return pd.DataFrame(rows)


def page_header(kicker, title, subtitle):
    st.markdown(f'<div class="eyebrow">{kicker}</div><div class="page-title">{title}</div><div class="page-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def kpi(label, value, note=""):
    st.markdown(f'<div class="kpi"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div><div class="kpi-note">{note}</div></div>', unsafe_allow_html=True)


def run_command(command, success_message):
    with st.spinner("Running safe demo action..."):
        result = subprocess.run([sys.executable, *command], capture_output=True, text=True, cwd=".")
    if result.returncode == 0:
        load_all.clear()
        st.success(success_message)
        st.rerun()
    else:
        st.error(result.stderr[-500:] or result.stdout[-500:] or "Action failed")


def overview(data, frame):
    m = data["metrics"]
    recovered = m["total_recovered"]
    at_risk = m["total_at_risk"]
    executed = sum(iv.get("outcome") == "success" for iv in data["interventions"])
    escalations = sum(iv.get("tier") == "voice_call" for iv in data["interventions"])
    page_header("RecoverAI / Control center", "Revenue recovery, under control", "Live operating view of failed payments, policy decisions and recovered revenue.")
    cols = st.columns(6)
    values = [("Revenue at risk", money(at_risk), "Current failed batch"), ("Revenue recovered", money(recovered), "Confirmed or simulated"), ("Recovery rate", f"{m['recovery_rate_pct']:.1f}%", "By payment count"), ("Payments analyzed", str(m["total_transactions"]), "Across the current batch"), ("Interventions executed", str(executed), "Policy actions completed"), ("Escalations", str(escalations), "Voice tier selected")]
    for col, (label, value, note) in zip(cols, values):
        with col: kpi(label, value, note)
    left, right = st.columns([1.1, 1])
    with left:
        st.markdown('<div class="panel"><div class="panel-title">Recovery funnel</div><div class="panel-copy">From a failed payment to a verified outcome.</div>', unsafe_allow_html=True)
        funnel = pd.DataFrame({"Stage": ["At risk", "Diagnosed", "Eligible", "Actioned", "Recovered"], "Payments": [len(frame), len(frame[frame["AI diagnosis"] != "Unclassified"]), len(frame[frame["Tier"] != ""]), len(data["interventions"]), m["recovered_count"]]}).set_index("Stage")
        st.bar_chart(funnel, color="#0f766e", height=245)
        st.markdown('</div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="panel"><div class="panel-title">Revenue exposure</div><div class="panel-copy">At-risk value compared with recovered value.</div>', unsafe_allow_html=True)
        st.bar_chart(pd.DataFrame({"Amount": [at_risk, recovered]}, index=["At risk", "Recovered"]), color="#153447", height=245)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel"><div class="panel-title">Failure reason breakdown</div><div class="panel-copy">Actual failure codes from the transactions table, with count and monetary exposure.</div>', unsafe_allow_html=True)
    breakdown = frame.groupby("Failure code", as_index=False).agg(Count=("_id", "count"), Exposure=("Amount", "sum")).sort_values("Exposure", ascending=False)
    st.dataframe(breakdown, width="stretch", hide_index=True, column_config={"Exposure": st.column_config.NumberColumn(format="₹%.2f")})
    st.markdown('</div>', unsafe_allow_html=True)
    recent = frame[frame["Status"] == "Recovered"].head(5) if not frame.empty else frame
    st.markdown('<div class="panel"><div class="panel-title">Recent recovery activity</div><div class="panel-copy">The latest customer-facing outcome signals.</div>', unsafe_allow_html=True)
    table = recent if not recent.empty else frame.head(5)
    st.dataframe(table[["Payment ID", "Customer", "Amount", "Action", "Outcome"]], width="stretch", hide_index=True, column_config={"Amount": st.column_config.NumberColumn(format="₹%.2f")})
    st.markdown('</div>', unsafe_allow_html=True)


def show_recovery_panel(data, selected):
    txn = next(item for item in data["transactions"] if item["id"] == selected["_id"])
    cust = customer(txn)
    st.markdown('<div class="panel"><div class="panel-title">Recovery detail</div><div class="panel-copy">Structured policy fields only. Private chain-of-thought is never displayed.</div>', unsafe_allow_html=True)
    a, b, c, d = st.columns(4)
    a.metric("Payment", money(txn["amount"]))
    b.metric("Diagnosis", selected["AI diagnosis"])
    c.metric("Recovery probability", "Not modeled")
    d.metric("Expected value", "Not modeled")
    st.markdown(f'<div class="panel-copy"><strong>{cust.get("name", "Unknown")}</strong> · {selected["Segment"]} · {selected["LTV tier"]} · {masked_phone(cust.get("phone"))}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="decision-box"><div class="mini-label">Recommended action</div><div class="mini-value">{selected["Action"]}</div><div style="margin-top:8px;color:#53616c">{selected["Reason"]}</div></div>', unsafe_allow_html=True)
    st.markdown("#### Policy gate")
    gate = pd.DataFrame([{"Gate": "Retry limit", "Value": f"{selected['Attempts']} attempts recorded", "Result": "Review" if selected["Attempts"] >= decision_engine.MAX_CONTACT_ATTEMPTS else "Pass"}, {"Gate": "Customer status", "Value": selected["Status"], "Result": "Block" if selected["Status"] != "Failed" else "Pass"}, {"Gate": "Fraud flag", "Value": "Detected" if txn.get("diagnosis_category") == "fraud_risk" else "Not detected", "Result": "Block" if txn.get("diagnosis_category") == "fraud_risk" else "Pass"}, {"Gate": "Final policy decision", "Value": selected["Action"], "Result": selected["Policy status"]}])
    st.dataframe(gate, width="stretch", hide_index=True)
    st.markdown("#### Recovery timeline")
    render_timeline([
        ("Payment failed", selected["Failure reason"]),
        ("Diagnosis", selected["AI diagnosis"]),
        ("Decision", selected["Reason"]),
        ("Intervention", selected["Action"]),
        ("Outcome", selected["Outcome"]),
    ])
    x, y, z = st.columns(3)
    with x:
        if st.button("Mark as paid", type="primary", icon=":material/payments:", key=f"pay_{selected['_id']}"):
            ok, msg = outcome_tracker.mark_recovered(selected["_id"], source="dashboard")
            load_all.clear(); st.toast(msg, icon=":material/check_circle:" if ok else ":material/error:"); st.rerun()
    with y:
        if st.button("View audit", icon=":material/receipt_long:", key=f"audit_{selected['_id']}"):
            st.session_state["nav"] = "Audit Trail"; st.rerun()
    with z: st.caption("Actions remain in protected simulation mode.")
    st.markdown('</div>', unsafe_allow_html=True)


def queue_page(data, frame):
    page_header("Operations / Recovery queue", "Recovery queue", "Filter the batch, inspect a payment, and use only existing safe demo actions.")
    f1, f2, f3, f4 = st.columns(4)
    with f1: status = st.multiselect("Status", sorted(frame["Status"].unique()), default=[])
    with f2: actions = st.multiselect("Action", sorted(frame["Action"].unique()), default=[])
    with f3: reasons = st.multiselect("Failure reason", sorted(frame["Failure reason"].unique()), default=[])
    with f4: segment = st.multiselect("Customer segment", sorted(frame["Segment"].unique()), default=[])
    view = frame.copy()
    for column, selected in (("Status", status), ("Action", actions), ("Failure reason", reasons), ("Segment", segment)):
        if selected: view = view[view[column].isin(selected)]
    st.markdown(f'<div class="panel"><div class="panel-title">{len(view)} payments in view</div><div class="panel-copy">Select a row below to open the recovery panel.</div>', unsafe_allow_html=True)
    st.dataframe(view[["Payment ID", "Customer", "Amount", "Failure reason", "AI diagnosis", "Action", "Policy status", "Outcome"]], width="stretch", hide_index=True, on_select="rerun", selection_mode="single-row", key="queue_table", column_config={"Amount": st.column_config.NumberColumn(format="₹%.2f")})
    st.markdown('</div>', unsafe_allow_html=True)
    selected_rows = st.session_state.get("queue_table", {}).get("selection", {}).get("rows", [])
    if selected_rows: show_recovery_panel(data, view.iloc[selected_rows[0]].to_dict())


def decisions_page(data, frame):
    page_header("Intelligence / Policy engine", "AI decisions", "A transparent decision surface built from the existing deterministic rules.")
    choice = st.selectbox("Select payment", frame["Payment ID"].tolist())
    show_recovery_panel(data, frame[frame["Payment ID"] == choice].iloc[0].to_dict())


def customers_page(frame):
    page_header("Accounts / Customer health", "Customers", "Customer-level exposure with phone numbers masked in the interface.")
    grouped = frame.groupby(["Customer", "Segment", "LTV tier"], dropna=False).agg({"Payment ID": "count", "Amount": "sum", "Attempts": "sum"}).reset_index().rename(columns={"Payment ID": "Failed payments", "Amount": "At risk", "Attempts": "Recovery attempts"})
    recovered = frame[frame["Status"] == "Recovered"].groupby("Customer")["Amount"].sum()
    grouped["Recovered amount"] = grouped["Customer"].map(recovered).fillna(0)
    grouped["Current state"] = grouped["Customer"].map(frame.groupby("Customer")["Status"].apply(lambda values: "Recovered" if all(value == "Recovered" for value in values) else "At risk"))
    st.dataframe(grouped, width="stretch", hide_index=True, column_config={"At risk": st.column_config.NumberColumn(format="₹%.2f"), "Recovered amount": st.column_config.NumberColumn(format="₹%.2f")})


def audit_page(data):
    page_header("Governance / Evidence", "Audit trail", "Chronological evidence for every decision, action, stopping rule, and recovery.")
    rows = []
    for item in data["audit"]:
        payload = audit_payload(item)
        rows.append({"Timestamp": pd.to_datetime(item["created_at"]), "Payment": (item.get("transaction_id") or "")[:8], "Event": item["event_type"].replace("_", " ").title(), "AI diagnosis": payload.get("reason", payload.get("failure_reason_code", "Recorded")), "Policy result": "Blocked" if item["event_type"] == "intervention_skipped" else "Approved" if item["event_type"] == "decision_made" else "Recorded", "Action": TIER_LABELS.get(payload.get("tier") or payload.get("attributed_tier"), "System"), "Outcome": "Recovered" if item["event_type"] == "payment_recovered" else "Simulated" if "dry_run" in item["event_type"] else "Recorded", "Recovered amount": float(payload.get("amount", 0) or 0) if item["event_type"] == "payment_recovered" else 0})
    audit = pd.DataFrame(rows)
    if audit.empty: st.info("No audit events yet.")
    else: st.dataframe(audit, width="stretch", hide_index=True, height=540, column_config={"Timestamp": st.column_config.DatetimeColumn(format="DD MMM HH:mm:ss"), "Recovered amount": st.column_config.NumberColumn(format="₹%.2f")})
    if not audit.empty: st.download_button("Export audit CSV", audit.to_csv(index=False).encode("utf-8"), "recoverai-audit.csv", "text/csv", icon=":material/download:")


def health_page(data):
    page_header("Reliability / Safety", "2 AM Safety Center", "A compact operational view of the services and guardrails protecting the recovery loop.")
    services = pd.DataFrame([{ "Service": "Database", "State": "Operational", "Evidence": "Supabase metrics and audit data loaded"}, {"Service": "AI provider", "State": "Not configured", "Evidence": "Deterministic rules engine is active"}, {"Service": "Recovery engine", "State": "Operational", "Evidence": "Pipeline decisions present"}, {"Service": "Razorpay sandbox", "State": "Simulation only", "Evidence": "No gateway credentials or live calls"}, {"Service": "WhatsApp simulator", "State": "Operational", "Evidence": "Simulated events recorded"}, {"Service": "Voice simulator", "State": "Operational", "Evidence": "Simulated provider selected"}])
    st.dataframe(services, width="stretch", hide_index=True)
    failures = [row for row in data["audit"] if "failed" in row["event_type"] or row["event_type"] == "intervention_skipped"]
    a, b, c = st.columns(3)
    with a: kpi("API failures", sum("failed" in row["event_type"] for row in failures), "Recorded provider errors")
    with b: kpi("Fallback events", 0, "No fallback required")
    with c: kpi("Stopped interventions", sum(row["event_type"] == "intervention_skipped" for row in failures), "Policy blocks")
    st.markdown('<div class="panel"><div class="panel-title">Latest safety signal</div><div class="panel-copy">No unsafe provider failure is present in the current run.</div><div class="decision-box">Fallback and stop rules remain active. Any unavailable provider action stays simulated or blocked by policy.</div></div>', unsafe_allow_html=True)


def settings_page():
    page_header("Workspace / Configuration", "Settings", "Read-only runtime configuration for this demo workspace.")
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.write("Runtime mode", "Protected simulation" if config.DRY_RUN else "Live mode")
    st.write("Voice provider", config.voice_provider())
    st.write("Payment link base", config.PAYMENT_LINK_BASE)
    st.warning("Protected simulation prevents real messages, calls, and payments from being sent.")
    st.markdown('</div>', unsafe_allow_html=True)


data = load_all()
frame = derived_frames(data)

from ui.components import top_header

with st.sidebar:
    st.markdown('<div class="brand"><span class="brand-mark">✦</span>RecoverAI</div><div class="brand-sub">Revenue Recovery Control Center<br>Track 03 • Razorpay Buildathon</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-group">WORKSPACE</div>', unsafe_allow_html=True)
    nav_items = ["Overview", "Revenue at Risk", "Recovery Queue", "AI Decisions", "AI Recovery Assistant", "Transactions", "Customers", "Audit Trail", "System Health"]
    if st.session_state.get("nav") not in nav_items: st.session_state["nav"] = "Overview"
    selected_page = st.radio("Workspace", nav_items, index=nav_items.index(st.session_state["nav"]), label_visibility="collapsed")
    st.session_state["nav"] = selected_page
    st.caption("PROTECTED WORKSPACE")
    st.markdown('<span class="status">DRY RUN</span>', unsafe_allow_html=True)
    if st.button("Run recovery analysis", icon=":material/refresh:", width="stretch"):
        run_command(["decision_engine.py"], "Recovery analysis completed")
    if st.button("Simulate recovery", icon=":material/play_arrow:", width="stretch"):
        run_command(["run_pipeline.py"], "Safe recovery simulation completed")
    if st.button("Reset demo", icon=":material/restart_alt:", width="stretch"):
        run_command(["reset_demo.py", "--yes"], "Demo reset completed")

top_header(selected_page)

if selected_page == "Overview": overview(data, frame)
elif selected_page == "Revenue at Risk":
    page_header("Portfolio / Exposure", "Revenue at risk", "Ranked failed payments and their current policy disposition.")
    risk_view = frame.sort_values("Amount", ascending=False).copy()
    risk_view["Phone"] = risk_view["Phone"].map(masked_phone)
    st.dataframe(risk_view[["Payment ID", "Customer", "Phone", "Amount", "Failure reason", "AI diagnosis", "Attempts", "Action", "Status"]], width="stretch", hide_index=True, column_config={"Amount": st.column_config.NumberColumn(format="₹%.2f")})
elif selected_page == "Recovery Queue": queue_page(data, frame)
elif selected_page == "AI Decisions": decisions_page(data, frame)
elif selected_page == "AI Recovery Assistant": render_assistant(data, frame)
elif selected_page == "Transactions":
    page_header("Operations / Transactions", "Transactions", "Every payment record currently loaded in the recovery workspace.")
    st.dataframe(frame[["Payment ID", "Customer", "Amount", "Failure code", "AI diagnosis", "Attempts", "Status", "Outcome"]], width="stretch", hide_index=True, column_config={"Amount": st.column_config.NumberColumn(format="₹%.2f")})
elif selected_page == "Customers": customers_page(frame)
elif selected_page == "Audit Trail": audit_page(data)
elif selected_page == "System Health": health_page(data)

_, foot_b = st.columns([4, 1])
with foot_b:
    if st.button("Refresh now", icon=":material/refresh:", width="stretch"):
        load_all.clear(); st.rerun()